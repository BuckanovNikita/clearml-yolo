"""Strict file resolution with an isolated effective command context."""

from collections.abc import Iterator
from copy import deepcopy
from typing import Any

import pytest
from omegaconf import OmegaConf


@pytest.fixture
def typed_resolver() -> Iterator[None]:
    OmegaConf.register_new_resolver("config_upload_double", lambda value: value * 2)
    yield
    OmegaConf.clear_resolver("config_upload_double")


def test_file_values_resolve_nested_lists_relative_references_and_types() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    document = {
        "count": 3,
        "enabled": False,
        "nothing": None,
        "settings": {"size": 960, "copy": "${.size}", "parent_count": "${..count}"},
        "items": ["${count}", "${enabled}", "${nothing}", {"size": "${settings.size}"}],
        "description": "size=${settings.size}",
        "copied_settings": "${settings}",
    }
    original = deepcopy(document)

    assert resolve_config_document(document) == {
        "count": 3,
        "enabled": False,
        "nothing": None,
        "settings": {"size": 960, "copy": 960, "parent_count": 3},
        "items": [3, False, None, {"size": 960}],
        "description": "size=960",
        "copied_settings": {"size": 960, "copy": 960, "parent_count": 3},
    }
    assert document == original


@pytest.mark.parametrize("as_omegaconf", [False, True])
def test_file_roots_replace_context_wholesale_and_only_file_roots_are_returned(
    as_omegaconf: bool,
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    document = {"settings": {"size": 960}, "size": "${settings.size}", "path": "${run_dir}"}
    context: Any = {
        "settings": {"size": 320, "context_only": True},
        "run_dir": "/effective/output",
        "unused": "???",
        "unused_cycle": "${unused_cycle}",
    }
    if as_omegaconf:
        context = OmegaConf.create(context)
    original = (
        OmegaConf.to_container(context, resolve=False) if as_omegaconf else deepcopy(context)
    )

    assert resolve_config_document(document, context) == {
        "settings": {"size": 960},
        "size": 960,
        "path": "/effective/output",
    }
    assert (
        OmegaConf.to_container(context, resolve=False) if as_omegaconf else context
    ) == original


def test_context_containers_referenced_by_file_values_keep_their_contained_fields() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    assert resolve_config_document(
        {"native": "${ultralytics}"},
        {"ultralytics": {"batch": 8, "device": [0, 1], "amp": True}, "extra": 99},
    ) == {"native": {"batch": 8, "device": [0, 1], "amp": True}}


def test_root_list_resolves_local_indexes_and_command_values() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    document = [{"size": 960}, "${0.size}", {"output": "${run_dir}", "size": "${..0.size}"}]

    assert resolve_config_document(document, {"run_dir": "/current/output", "unused": "???"}) == [
        {"size": 960},
        960,
        {"output": "/current/output", "size": 960},
    ]


def test_numeric_yaml_mapping_keys_are_preserved_alongside_string_numeric_references() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    assert resolve_config_document(
        {"names": {0: "box"}, "string_names": {"0": "package"}, "label": "${string_names.0}"}
    ) == {
        "names": {0: "box"},
        "string_names": {"0": "package"},
        "label": "package",
    }


@pytest.mark.parametrize(
    ("document", "expected"),
    [(None, None), (False, False), (19, 19), ("plain", "plain"), ("${batch}", 8)],
)
def test_scalar_document_preserves_its_resolved_type(document: Any, expected: Any) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    assert resolve_config_document(document, {"batch": 8}) == expected


def test_environment_and_registered_resolvers_resolve_once(
    monkeypatch: pytest.MonkeyPatch, typed_resolver: None
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    monkeypatch.setenv("CY_CONFIG_UPLOAD_TEST_VALUE", "private-fixture-value")

    assert resolve_config_document(
        {
            "environment": "${oc.env:CY_CONFIG_UPLOAD_TEST_VALUE}",
            "number": "${config_upload_double:4}",
            "literal": r"\${not_a_reference}",
        }
    ) == {"environment": "private-fixture-value", "number": 8, "literal": "${not_a_reference}"}


@pytest.mark.parametrize("environment_value", ["${base}", "???"])
def test_environment_cannot_introduce_unresolved_active_values(
    monkeypatch: pytest.MonkeyPatch, environment_value: str
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    monkeypatch.setenv("CY_NESTED_UPLOAD_TEST", environment_value)

    with pytest.raises(ValueError, match="could not be resolved"):
        resolve_config_document({"base": 7, "copy": "${oc.env:CY_NESTED_UPLOAD_TEST}"})


@pytest.mark.parametrize("resolver_value", ["${base}", {"nested": ["${base}"]}])
def test_registered_resolver_cannot_introduce_interpolation_or_be_evaluated_twice(
    resolver_value: Any,
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    calls = 0

    def nested() -> Any:
        nonlocal calls
        calls += 1
        return resolver_value

    OmegaConf.register_new_resolver("config_upload_nested", nested)
    try:
        with pytest.raises(ValueError, match="could not be resolved"):
            resolve_config_document({"base": 7, "copy": "${config_upload_nested:}"})
    finally:
        OmegaConf.clear_resolver("config_upload_nested")

    assert calls == 1


def test_escaped_literal_survives_file_and_command_aliases() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    assert resolve_config_document(
        {
            "literal": r"\${missing}",
            "alias": "${literal}",
            "context_alias": "${context_literal}",
            "three_slashes": r"\\\${missing}",
        },
        {"context_literal": r"\${other_missing}"},
    ) == {
        "literal": "${missing}",
        "alias": "${missing}",
        "context_alias": "${other_missing}",
        "three_slashes": r"\${missing}",
    }


@pytest.mark.parametrize("argument", ["${literal}", r'"\${missing}"'])
def test_registered_resolver_receives_native_literal_argument(argument: str) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    OmegaConf.register_new_resolver("config_upload_length", len)
    try:
        assert resolve_config_document(
            {"literal": r"\${missing}", "length": f"${{config_upload_length:{argument}}}"}
        ) == {"literal": "${missing}", "length": 10}
    finally:
        OmegaConf.clear_resolver("config_upload_length")


def test_transformed_literal_resolver_output_fails_safely() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    OmegaConf.register_new_resolver("config_upload_upper", str.upper)
    try:
        with pytest.raises(ValueError, match="could not be resolved"):
            resolve_config_document(
                {"literal": r"\${missing}", "upper": "${config_upload_upper:${literal}}"}
            )
    finally:
        OmegaConf.clear_resolver("config_upload_upper")


@pytest.mark.parametrize("resolver_value", [("${base}",), ("???",)])
def test_tuple_resolver_outputs_are_checked_recursively(resolver_value: Any) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    OmegaConf.register_new_resolver("config_upload_tuple", lambda: resolver_value)
    try:
        with pytest.raises(ValueError, match="could not be resolved"):
            resolve_config_document({"base": 7, "values": "${config_upload_tuple:}"})
    finally:
        OmegaConf.clear_resolver("config_upload_tuple")


def test_concrete_tuple_resolver_output_is_a_primitive_list() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    OmegaConf.register_new_resolver("config_upload_tuple", lambda: (3, False, None))
    try:
        assert resolve_config_document({"values": "${config_upload_tuple:}"}) == {
            "values": [3, False, None]
        }
    finally:
        OmegaConf.clear_resolver("config_upload_tuple")


def test_file_metadata_tracks_context_credentials_without_uploading_context() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    result = resolve_config_file(
        {"copy": "${auth.password}"}, {"auth": {"password": "context-private-value"}}
    )

    assert result.values == {"copy": "context-private-value"}
    secret_inventory_is_correct = "context-private-value" in result.secrets
    assert secret_inventory_is_correct


@pytest.mark.parametrize(
    "expression",
    ["${oc.env:APP_SECRET_KEY}", '${oc.env:"APP_SECRET_KEY"}', "${oc.env:${env_name}}"],
)
def test_file_metadata_tracks_sensitive_environment_aliases(
    monkeypatch: pytest.MonkeyPatch, expression: str
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    monkeypatch.setenv("APP_SECRET_KEY", "environment-private-value")
    result = resolve_config_file({"copy": expression}, {"env_name": "APP_SECRET_KEY"})

    assert result.values == {"copy": "environment-private-value"}
    secret_inventory_is_correct = "environment-private-value" in result.secrets
    assert secret_inventory_is_correct


def test_benign_environment_path_is_not_secret_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    monkeypatch.setenv("CY_DATASET_PATH", "/dataset/images")
    result = resolve_config_file({"dataset": "${oc.env:CY_DATASET_PATH}"})

    assert result.values == {"dataset": "/dataset/images"}
    secret_inventory_is_correct = "/dataset/images" not in result.secrets
    assert secret_inventory_is_correct


def test_sensitive_environment_name_from_resolver_is_inventory_without_reevaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    monkeypatch.setenv("CY_API_SECRET", "dynamic-environment-private-value")
    calls = 0

    def environment_name() -> str:
        nonlocal calls
        calls += 1
        return "CY_API_SECRET"

    OmegaConf.register_new_resolver("config_upload_env_name", environment_name)
    try:
        result = resolve_config_file({"copy": "${oc.env:${config_upload_env_name:}}"})
    finally:
        OmegaConf.clear_resolver("config_upload_env_name")

    assert result.values == {"copy": "dynamic-environment-private-value"}
    secret_inventory_is_correct = "dynamic-environment-private-value" in result.secrets
    assert secret_inventory_is_correct
    assert calls == 1


def test_secret_metadata_does_not_reevaluate_registered_resolver() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    calls = 0

    def credential() -> str:
        nonlocal calls
        calls += 1
        return "resolver-private-value"

    OmegaConf.register_new_resolver("config_upload_credential", credential)
    try:
        result = resolve_config_file(
            {"copy": "${auth.password}"},
            {"auth": {"password": "${config_upload_credential:}"}},
        )
    finally:
        OmegaConf.clear_resolver("config_upload_credential")

    assert result.values == {"copy": "resolver-private-value"}
    secret_inventory_is_correct = "resolver-private-value" in result.secrets
    assert secret_inventory_is_correct
    assert calls == 1


@pytest.mark.parametrize("resolver_value", [{"${missing}"}, object()])
def test_unsupported_resolver_results_cannot_escape_plain_tree_validation(
    resolver_value: Any,
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    OmegaConf.register_new_resolver("config_upload_unsupported", lambda: resolver_value)
    try:
        with pytest.raises(ValueError, match="could not be resolved"):
            resolve_config_document({"value": "${config_upload_unsupported:}"})
    finally:
        OmegaConf.clear_resolver("config_upload_unsupported")


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (
            {"count": 2, "value": r"literal=\${missing}, count=${count}"},
            {"count": 2, "value": "literal=${missing}, count=2"},
        ),
        (
            {"literal": r"\${missing}", "copy": "prefix-${literal}"},
            {"literal": "${missing}", "copy": "prefix-${missing}"},
        ),
    ],
)
def test_mixed_literal_text_and_embedded_reference_provenance(
    document: Any, expected: Any
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    assert resolve_config_document(document) == expected


def test_embedded_secret_reference_is_inventoried_without_second_resolver_call() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    calls = 0

    def credential() -> str:
        nonlocal calls
        calls += 1
        return f"dummy-private-{calls}"

    OmegaConf.register_new_resolver("config_upload_embedded_credential", credential)
    try:
        result = resolve_config_file(
            {"message": "prefix-${auth.password}"},
            {"auth": {"password": "${config_upload_embedded_credential:}"}},
        )
    finally:
        OmegaConf.clear_resolver("config_upload_embedded_credential")

    assert result.values == {"message": "prefix-dummy-private-1"}
    assert calls == 1
    secret_inventory_is_correct = "prefix-dummy-private-1" in result.secrets
    assert secret_inventory_is_correct


def test_unused_context_resolver_is_not_executed_for_secret_inventory() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    def unused() -> str:
        pytest.fail("Unused registered code must not run for redaction metadata")

    OmegaConf.register_new_resolver("config_upload_unused_secret", unused)
    try:
        result = resolve_config_file(
            {"plain": 7}, {"auth": {"password": "${config_upload_unused_secret:}"}}
        )
    finally:
        OmegaConf.clear_resolver("config_upload_unused_secret")

    assert result.values == {"plain": 7}


def test_transformed_secret_still_inventories_concrete_context_credentials() -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    OmegaConf.register_new_resolver("config_upload_sensitive_length", len)
    try:
        result = resolve_config_file(
            {"length": "${config_upload_sensitive_length:${auth.password}}"},
            {"auth": {"password": "clear-private-value"}},
        )
    finally:
        OmegaConf.clear_resolver("config_upload_sensitive_length")

    secret_inventory_is_correct = "clear-private-value" in result.secrets
    assert secret_inventory_is_correct


@pytest.mark.parametrize(
    "document",
    [
        {"value": "${missing_private_reference}"},
        {"value": "${value}"},
        {"value": "${unknown_private_resolver:private-fixture-value}"},
        {"value": "${oc.env:CY_CONFIG_UPLOAD_ABSENT_SECRET}"},
        {"value": "???"},
        {"values": [1, "???"]},
        {"nested": {"value": "???"}},
        {"value": "${settings.context_only}", "settings": {"size": 960}},
    ],
)
def test_resolution_failure_is_confidential_and_does_not_modify_inputs(
    document: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_document

    monkeypatch.delenv("CY_CONFIG_UPLOAD_ABSENT_SECRET", raising=False)
    original = deepcopy(document)
    context = {"settings": {"context_only": "private-fixture-value"}}

    with pytest.raises(ValueError, match="could not be resolved") as raised:
        resolve_config_document(document, context)

    assert "could not be resolved" in str(raised.value)
    assert "private" not in str(raised.value)
    assert "CY_CONFIG" not in str(raised.value)
    assert raised.value.__suppress_context__
    assert document == original
    assert context == {"settings": {"context_only": "private-fixture-value"}}


@pytest.mark.parametrize("reference", ["${${key}}", "prefix-${${key}}"])
def test_dynamic_node_references_fail_before_publication(reference: str) -> None:
    from clearml_yolo.apps.config_resolution import resolve_config_file

    OmegaConf.register_new_resolver("config_upload_dynamic_secret", lambda: "dynamic-private-value")
    try:
        with pytest.raises(ValueError, match="could not be resolved"):
            resolve_config_file(
                {"copy": reference},
                {"key": "auth.password", "auth": {"password": "${config_upload_dynamic_secret:}"}},
            )
    finally:
        OmegaConf.clear_resolver("config_upload_dynamic_secret")


@pytest.mark.parametrize("function_name", ["resolve_config_document", "resolve_config_file"])
def test_resolution_failure_reports_type_without_private_payload(
    monkeypatch: pytest.MonkeyPatch,
    function_name: str,
) -> None:
    from loguru import logger

    from clearml_yolo.apps import config_resolution

    def failed_resolution(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("opaque-private-resolver-input")

    monkeypatch.setattr(config_resolution, "_resolve_file", failed_resolution)
    messages: list[str] = []
    sink = logger.add(messages.append, level="DEBUG", format="{message}")
    try:
        with pytest.raises(ValueError, match="could not be resolved") as caught:
            getattr(config_resolution, function_name)({"copy": "${secret}"})
    finally:
        logger.remove(sink)
    output = "".join(messages)
    assert "ValueError" in str(caught.value)
    assert "ValueError" in output
    assert "opaque-private-resolver-input" not in output + str(caught.value)
    assert caught.value.__suppress_context__
