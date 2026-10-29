"""Composition is useful without invoking datasets, resolvers or application effects."""

import builtins
import io
from pathlib import Path
from typing import Any

import pytest
from hydra._internal.core_plugins.basic_sweeper import BasicSweeper
from hydra.core.override_parser.overrides_parser import OverridesParser
from omegaconf import OmegaConf

from clearml_yolo.core.documentation import PreviewRequest
from clearml_yolo.entrypoints.documentation.preview import preview


def test_preview_preserves_environment_and_missing_inputs() -> None:
    result = preview(PreviewRequest(overrides=["clearml.task_name=${oc.env:PRIVATE_VALUE}"]))
    assert not result.errors
    assert "${oc.env:PRIVATE_VALUE}" in result.jobs[0].yaml
    assert "ground_truth" in result.jobs[0].unresolved
    assert "clearml.task_name" in result.jobs[0].unresolved
    assert result.deferred


def test_preview_named_documents_and_ordered_overrides() -> None:
    result = preview(
        PreviewRequest(
            documents={"example.yaml": "defaults:\n- train\n- _self_\nground_truth: absent.csv\n"},
            overrides=["ultralytics.epochs=2", "ultralytics.epochs=3"],
        )
    )
    assert not result.errors
    assert result.jobs[0].values["ultralytics.epochs"] == 3


def test_preview_sweep_is_bounded_before_cartesian_expansion() -> None:
    result = preview(
        PreviewRequest(overrides=["ultralytics.epochs=range(1,1000000000)"], sweep=True)
    )
    assert result.errors
    assert "100" in result.errors[0]


def test_preview_rejects_search_path_before_composition() -> None:
    result = preview(
        PreviewRequest(
            documents={"example.yaml": "defaults:\n- train\nhydra:\n  searchpath: [file:///etc]\n"}
        )
    )
    assert result.errors
    assert "searchpath" in result.errors[0]


def test_preview_never_loads_an_augmentation_file() -> None:
    result = preview(
        PreviewRequest(
            overrides=["transforms=albumentations", "transforms.pipeline_file=/does/not/exist.json"]
        )
    )
    assert not result.errors
    assert not result.jobs[0].errors


@pytest.mark.parametrize(
    "document",
    [
        "defaults:\n- /../../etc/private\n",
        "# @package hydra\nsearchpath: [file:///etc]\n",
        "defaults:\n- train\n- override hydra/launcher: external\n",
        "defaults:\n- ${oc.env:PRIVATE_VALUE}\n",
    ],
)
def test_untrusted_defaults_cannot_change_sources_or_plugins(document: str) -> None:
    result = preview(PreviewRequest(documents={"example.yaml": document}))
    assert result.errors


def test_custom_resolver_is_never_called() -> None:
    def forbidden() -> str:
        pytest.fail("Preview called a custom resolver")

    OmegaConf.register_new_resolver("docs_forbidden", forbidden)
    try:
        result = preview(PreviewRequest(overrides=["clearml.task_name=${docs_forbidden:}"]))
        assert not result.errors
        assert "${docs_forbidden:}" in result.jobs[0].yaml
    finally:
        OmegaConf.clear_resolver("docs_forbidden")


def test_sweep_materialization_helpers_are_rejected_before_parsing() -> None:
    result = preview(
        PreviewRequest(sweep=True, overrides=["ultralytics.epochs=shuffle(range(1,1000000000))"])
    )
    assert result.errors


def test_packaged_group_override_cannot_evaluate_a_resolver() -> None:
    called = []

    def forbidden() -> str:
        called.append(True)
        return "ultralytics"

    OmegaConf.register_new_resolver("docs_group_probe", forbidden)
    try:
        result = preview(PreviewRequest(overrides=["+model@extra=${docs_group_probe:}"]))
        assert result.errors
        assert called == []
    finally:
        OmegaConf.clear_resolver("docs_group_probe")


@pytest.mark.parametrize(
    "package", ["hydra.launcher", "_global_.hydra.launcher", "_global_._cy_schemas"]
)
def test_package_directives_cannot_replace_hydra_or_schema(package: str) -> None:
    request = PreviewRequest(
        documents={
            "example.yaml": "defaults:\n- train\n- custom\n- _self_\n",
            "custom.yaml": f"# @package {package}\n_target_: fake.external.Launcher\n",
        }
    )
    assert preview(request).errors


def test_nested_defaults_resolver_is_rejected_before_composition() -> None:
    called = []

    def forbidden() -> str:
        called.append(True)
        return "ultralytics"

    OmegaConf.register_new_resolver("docs_nested_probe", forbidden)
    try:
        request = PreviewRequest(
            command="predict",
            documents={
                "entry.yaml": (
                    "defaults:\n- predict\n- selector: docs_nested_probe\n"
                    "- override model: ${${selector}:}\n"
                ),
                "selector/docs_nested_probe.yaml": "# @package _global_\n{}\n",
            },
        )
        assert preview(request).errors
        assert called == []
    finally:
        OmegaConf.clear_resolver("docs_nested_probe")


def test_ordered_override_delete_add_and_replace_are_preserved() -> None:
    result = preview(
        PreviewRequest(
            command="predict",
            overrides=[
                "model_label=first",
                "~model_label",
                "+model_label=second",
                "model_label=last",
            ],
        )
    )
    assert not result.errors
    assert result.jobs[0].values["model_label"] == "last"


@pytest.mark.parametrize(
    "selection",
    [
        "../../../private",
        "/private",
        "ultralytics,../../../private",
        "choice(ultralytics,../../../private)",
    ],
)
def test_group_values_cannot_traverse_outside_preview_inputs(selection: str) -> None:
    result = preview(
        PreviewRequest(command="predict", overrides=[f"model={selection}"], sweep=True)
    )
    assert result.errors
    assert "external group" in result.errors[0]


def test_interpolated_hydra_container_cannot_execute_a_resolver() -> None:
    called = []

    def forbidden() -> dict[str, str]:
        called.append(True)
        return {"output_subdir": "anything"}

    OmegaConf.register_new_resolver("docs_hydra_probe", forbidden)
    try:
        result = preview(
            PreviewRequest(
                documents={
                    "entry.yaml": "defaults:\n- train\n- _self_\nhydra: ${docs_hydra_probe:}\n"
                }
            )
        )
        assert result.errors
        assert called == []
    finally:
        OmegaConf.clear_resolver("docs_hydra_probe")


def test_hydra_alias_cannot_read_an_external_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside.yaml"
    outside.write_text("external_marker: 123\n")
    opened: list[str] = []
    original = builtins.open

    def observed(file: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, (str, Path)) and Path(file) == outside:
            opened.append(str(file))
        return original(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", observed)
    monkeypatch.setattr(io, "open", observed)
    # Positive control proves the observation covers this path before preview.
    assert "external_marker" in outside.read_text()
    assert opened == [str(outside)]
    opened.clear()
    result = preview(
        PreviewRequest(
            documents={
                "entry.yaml": (
                    "defaults:\n- outside\n- _self_\nhydra: ${settings}\n"
                    f"settings:\n  searchpath: [file://{tmp_path}]\n"
                )
            }
        )
    )
    assert result.errors
    assert opened == []


@pytest.mark.parametrize(
    "document",
    [
        "defaults:\n- train\n- _self_\nhydra:\n  run: ${oc.env:PRIVATE_VALUE}\n",
        "defaults:\n- train\n- model@hydra: ultralytics\n",
        "defaults:\n- train\n- model@_global_.hydra: ultralytics\n",
    ],
)
def test_submitted_hydra_runtime_settings_are_terminal_only(document: str) -> None:
    assert preview(PreviewRequest(documents={"entry.yaml": document})).errors


@pytest.mark.parametrize("override", ["hydra.run.dir=${oc.env:PRIVATE_VALUE}", "hydra.job.name=x"])
def test_hydra_runtime_overrides_are_terminal_only(override: str) -> None:
    result = preview(PreviewRequest(overrides=[override]))
    assert result.errors
    assert "terminal" in result.errors[0]


def test_document_extension_reports_hydra_requirement_before_composition() -> None:
    result = preview(PreviewRequest(documents={"entry.yml": "defaults:\n- train\n"}))
    assert result.errors
    assert "must use .yaml" in result.errors[0]


def test_sweep_override_order_matches_native_basic_sweeper() -> None:
    overrides = [
        "model_label=first",
        "~model_label",
        "+model_label=second",
        "model_label=last",
        "ultralytics_predict.batch=1,2",
    ]
    batches = BasicSweeper.split_arguments(
        OverridesParser.create().parse_overrides(overrides), max_batch_size=None
    )
    expected = [
        preview(PreviewRequest(command="predict", overrides=job)).jobs[0].yaml
        for batch in batches
        for job in batch
    ]
    result = preview(PreviewRequest(command="predict", overrides=overrides, sweep=True))
    assert not result.errors
    assert [job.yaml for job in result.jobs] == expected
