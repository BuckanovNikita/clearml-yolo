"""Resolve configuration files against detached effective command inputs."""

import os
import re
from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, NoReturn, cast

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException
from omegaconf.grammar.gen.OmegaConfGrammarParser import OmegaConfGrammarParser
from omegaconf.grammar_parser import parse

from clearml_yolo.adapters.clearml.session import ResolvedConfigFile, configuration_secrets
from clearml_yolo.adapters.observability.diagnostics import (
    exception_summary,
    log_exception,
    redact_text,
)

_REFERENCE = re.compile(r"\$\{([^{}:]+)\}\Z")


def _context_data(command_config: DictConfig | Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(command_config, DictConfig):
        return cast(dict[str, Any], OmegaConf.to_container(command_config, resolve=False))
    return deepcopy(dict(command_config or {}))


def _reference_target(
    root: Mapping[str, Any], key: str, path: tuple[str, ...]
) -> tuple[Any, tuple[str, ...]]:
    relative = len(key) - len(key.lstrip("."))
    prefix = path[:-relative] if relative else ()
    parts = tuple(part for part in re.split(r"[.\[\]]+", key.lstrip(".")) if part)
    target_path = prefix + parts
    value: Any = root
    for part in target_path:
        numeric = isinstance(value, (list, tuple)) or (
            isinstance(value, Mapping) and part not in value and part.lstrip("-").isdigit()
        )
        value = value[int(part)] if numeric else value[part]
    return value, target_path


def _follow_reference(
    source: Any, path: tuple[str, ...], root: Mapping[str, Any]
) -> tuple[Any, tuple[str, ...], bool]:
    visited: set[tuple[str, ...]] = set()
    sensitive = False
    while path not in visited:
        visited.add(path)
        sensitive |= any(configuration_secrets({part: "secret-probe"}) for part in path)
        match = _REFERENCE.fullmatch(source) if isinstance(source, str) else None
        if match is None:
            break
        source, path = _reference_target(root, match.group(1), path)
    return source, path, sensitive


def _syntax_references(source: str) -> tuple[list[tuple[str, bool]], list[tuple[int, int]]]:
    references: list[tuple[str, bool]] = []
    resolver_spans: list[tuple[int, int]] = []

    def walk(node: Any, *, inside_resolver: bool = False) -> None:
        # The generated ANTLR tree is an opaque third-party interface. Inspect its
        # syntax only; visiting a resolver must never execute registered user code.
        if isinstance(node, OmegaConfGrammarParser.InterpolationResolverContext):
            inside_resolver = True
            resolver_spans.append((node.start.start, node.stop.stop))
        if isinstance(node, OmegaConfGrammarParser.InterpolationNodeContext):
            expression = node.getText()[2:-1]
            if "${" in expression:
                # A computed target cannot be traced safely without reevaluating
                # registered code; reject it before any configuration is published.
                raise ValueError("Configuration values could not be resolved")
            references.append((expression, inside_resolver))
        for index in range(node.getChildCount()):
            walk(node.getChild(index), inside_resolver=inside_resolver)

    walk(parse(source))
    return references, resolver_spans


def _source_provenance(
    source: Any,
    path: tuple[str, ...],
    root: Mapping[str, Any],
    visited: frozenset[tuple[str, ...]] = frozenset(),
) -> tuple[Counter[str], bool, dict[tuple[str, ...], Any]]:
    literals: Counter[str] = Counter()
    sensitive = False
    reached: dict[tuple[str, ...], Any] = {}
    if not isinstance(source, str) or "${" not in source or path in visited:
        return literals, sensitive, reached
    references, spans = _syntax_references(source)
    for match in re.finditer(r"(\\+)\$\{([^{}]*)\}", source):
        inside_resolver = any(start <= match.start() <= end for start, end in spans)
        if len(match.group(1)) % 2 and not inside_resolver:
            literals[f"${{{match.group(2)}}}"] += 1
    for reference, inside_resolver in references:
        value, target_path = _reference_target(root, reference, path)
        value, target_path, target_sensitive = _follow_reference(value, target_path, root)
        nested_literals, nested_sensitive, nested_reached = _source_provenance(
            value, target_path, root, visited | {path}
        )
        if not inside_resolver:
            literals.update(nested_literals)
        sensitive |= target_sensitive or nested_sensitive
        reached[target_path] = value
        reached.update(nested_reached)
    return literals, sensitive, reached


def _literal_output(value: str, allowed: Counter[str]) -> bool:
    expressions = Counter(re.findall(r"\$\{[^{}]*\}", value))
    return expressions.total() == value.count("${") and not (expressions - allowed)


def _validate_result(
    value: Any,
    source: Any,
    path: tuple[str, ...],
    root: Mapping[str, Any],
    secrets: set[str],
    captured: dict[tuple[str, ...], tuple[Any, Any]],
) -> Any:
    source, path, sensitive = _follow_reference(source, path, root)
    captured[path] = (source, value)
    literals, embedded_sensitive, reached = _source_provenance(source, path, root)
    captured.update({target: (raw, value) for target, raw in reached.items()})
    if sensitive or embedded_sensitive:
        secrets.update(configuration_secrets({"password": value}))
    if isinstance(value, Mapping):
        return {
            key: _validate_result(
                item,
                source.get(key) if isinstance(source, Mapping) else None,
                (*path, str(key)),
                root,
                secrets,
                captured,
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            _validate_result(
                item,
                source[index] if isinstance(source, (list, tuple)) else None,
                (*path, str(index)),
                root,
                secrets,
                captured,
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, str) and (
        value == "???" or ("${" in value and not _literal_output(value, literals))
    ):
        raise ValueError("Configuration values could not be resolved")
    if not isinstance(value, (str, bool, int, float, type(None))):
        raise TypeError("Configuration values could not be resolved")
    return value


def _resolved_value(root: DictConfig, key: str) -> Any:
    value = root[key]
    if OmegaConf.is_config(value):
        return OmegaConf.to_container(value, resolve=True, throw_on_missing=True)
    return deepcopy(value)


def _document_fields(document: Any, context: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    if OmegaConf.is_config(document):
        document = OmegaConf.to_container(document, resolve=False)
    if isinstance(document, Mapping):
        return deepcopy(dict(document)), "mapping"
    if isinstance(document, (list, tuple)):
        return {str(index): deepcopy(value) for index, value in enumerate(document)}, "list"
    scalar_key = "_config_document"
    while scalar_key in context:
        scalar_key += "_"
    return {scalar_key: deepcopy(document)}, "scalar"


def _context_secrets(
    source: Any,
    root: Mapping[str, Any],
    captured: Mapping[tuple[str, ...], tuple[Any, Any]],
    path: tuple[str, ...] = (),
    *,
    sensitive: bool = False,
) -> set[str]:
    if isinstance(source, Mapping):
        return {
            secret
            for key, value in source.items()
            for secret in _context_secrets(
                value,
                root,
                captured,
                (*path, str(key)),
                sensitive=sensitive or bool(configuration_secrets({key: "secret-probe"})),
            )
        }
    if isinstance(source, (list, tuple)):
        return {
            secret
            for index, value in enumerate(source)
            for secret in _context_secrets(
                value, root, captured, (*path, str(index)), sensitive=sensitive
            )
        }
    if not sensitive or source == "???":
        return configuration_secrets(source)
    value = _context_sensitive_value(source, path, root, captured)
    return configuration_secrets({"password": value})


def _context_sensitive_value(
    source: Any,
    path: tuple[str, ...],
    root: Mapping[str, Any],
    captured: Mapping[tuple[str, ...], tuple[Any, Any]],
) -> Any:
    if not isinstance(source, str) or "${" not in source:
        return source
    cached = captured.get(path)
    if cached is not None and cached[0] == source:
        return cached[1]
    # Inventory concrete values and already-consumed references. Unused registered
    # resolvers are executable code, so metadata collection must not evaluate them.
    try:
        value = _follow_reference(source, path, root)[0]
    except (KeyError, IndexError):
        return None
    return None if isinstance(value, str) and "${" in value else value


def _resolve_file(
    document: Any, command_config: DictConfig | Mapping[str, Any] | None, *, provenance: bool
) -> ResolvedConfigFile:
    context = _context_data(command_config)
    fields, kind = _document_fields(document, context)
    sources = context | fields
    root = OmegaConf.create(sources)
    secrets: set[str] = set()
    captured: dict[tuple[str, ...], tuple[Any, Any]] = {}
    resolved = {
        key: _validate_result(
            _resolved_value(root, key), source, (key,), sources, secrets, captured
        )
        for key, source in fields.items()
    }
    if provenance:
        secrets.update(_context_secrets(context, context, captured))
        # This private redaction inventory covers computed environment names
        # without parsing them or reevaluating any registered resolver.
        secrets.update(configuration_secrets(dict(os.environ)))
    values: Any = resolved
    if kind == "list":
        values = list(resolved.values())
    elif kind == "scalar":
        values = next(iter(resolved.values()))
    return ResolvedConfigFile(values=values, secrets=frozenset(secrets))


def resolve_config_document(
    document: Any, command_config: DictConfig | Mapping[str, Any] | None = None
) -> Any:
    """Resolve original file fields once, preserving native resolver arguments."""
    try:
        return _resolve_file(document, command_config, provenance=False).values
    except (OmegaConfBaseException, KeyError, IndexError, TypeError, ValueError) as error:
        _resolution_failure(error)


def resolve_config_file(
    document: Any, command_config: DictConfig | Mapping[str, Any] | None = None
) -> ResolvedConfigFile:
    """Resolve file values and retain credential provenance only for sanitization."""
    try:
        return _resolve_file(document, command_config, provenance=True)
    except (OmegaConfBaseException, KeyError, IndexError, TypeError, ValueError) as error:
        _resolution_failure(error)


def _resolution_failure(error: BaseException) -> NoReturn:
    # Resolver messages and arguments may contain private values.
    context: dict[str, object] = {}
    if isinstance(error, OmegaConfBaseException) and isinstance(error.full_key, str):
        context["field"] = error.full_key
    log_exception(
        "Configuration values could not be resolved",
        error,
        level="DEBUG",
        context=context,
        include_message=False,
    )
    field = f" (field {redact_text(str(context['field']))})" if context else ""
    raise ValueError(
        "Configuration values could not be resolved: "
        + exception_summary(error, include_message=False)
        + field
    ) from None
