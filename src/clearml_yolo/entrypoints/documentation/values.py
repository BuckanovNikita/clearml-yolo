"""Inspect configuration values without invoking any OmegaConf resolver."""

import re

from pydantic import JsonValue

REFERENCE = re.compile(r"\$\{([\w.]+)\}")


def flatten(value: JsonValue, prefix: str = "") -> dict[str, JsonValue]:
    if isinstance(value, dict) and value:
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            result.update(flatten(item, f"{prefix}.{key}" if prefix else key))
        return result
    return {prefix: value}


def selected_values(values: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Resolve only ordinary field references; cycles and function expressions stay literal."""
    result = dict(values)
    for _ in range(len(values) + 1):
        changed = False
        for key, value in result.items():
            if not isinstance(value, str):
                continue
            match = REFERENCE.fullmatch(value)
            if match and match[1] in result:
                replacement = result[match[1]]
                if replacement != value and not unresolved(replacement):
                    result[key] = replacement
                    changed = True
        if not changed:
            break
    return result


def unresolved(value: JsonValue) -> bool:
    if isinstance(value, str):
        return value == "???" or "${" in value
    if isinstance(value, list):
        return any(unresolved(item) for item in value)
    if isinstance(value, dict):
        return any(unresolved(item) for item in value.values())
    return False
