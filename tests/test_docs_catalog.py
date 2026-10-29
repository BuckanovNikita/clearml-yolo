"""Installed declarations and packaged tutorial coverage must fail closed."""

import pytest

from clearml_yolo.core.documentation import Catalog
from clearml_yolo.entrypoints.documentation.catalog import build_catalog, check_coverage
from clearml_yolo.entrypoints.documentation.checks import check_catalog


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return build_catalog()


def test_installed_catalog_and_tutorial_examples(catalog: Catalog) -> None:
    assert check_catalog(catalog) == []
    assert set(catalog.commands.values()) >= {"cy", "cy-docs", "cy-download-weights"}
    assert any(item.path == "ground_truth.dataset_id" for item in catalog.fields)
    assert any(item.path == "baseline_model.thresholds" for item in catalog.fields)


def test_undocumented_composed_leaf_fails_coverage(catalog: Catalog) -> None:
    broken = catalog.model_copy(
        update={"fields": [item for item in catalog.fields if item.path != "model.train.batch"]}
    )
    with pytest.raises(ValueError, match=r"Undocumented composed field.*model.train.batch"):
        check_coverage(broken)


def test_effective_defaults_keep_expressions_separate(catalog: Catalog) -> None:
    config = next(
        item
        for item in catalog.configurations
        if item.command == "train" and item.model == "ultralytics" and item.profile == "default"
    )
    assert config.expressions["ultralytics_predict.imgsz"] == "${ultralytics.imgsz}"
    assert config.values["ultralytics_predict.imgsz"] == 960
    assert config.values["ground_truth"] == "???"
    assert config.values["ultralytics_predict.batch"] == 1


def test_generated_snapshot_is_not_an_editable_input(catalog: Catalog) -> None:
    generated = [item for item in catalog.fields if item.path.startswith("transforms.snapshot")]
    assert generated
    assert all(item.generated for item in generated)


def test_command_specific_required_values_and_hydra_cli_reference(catalog: Catalog) -> None:
    by_path = {item.path: item for item in catalog.fields}
    assert by_path["ground_truth"].variants["train"].required
    assert not by_path["ground_truth"].variants["export"].required
    assert by_path["predictions"].required
    assert by_path["hydra.--config-dir"].examples
    assert by_path["hydra.--cfg"].commands == list(catalog.commands)[:9]


def test_utility_reference_uses_effective_argparse_defaults(catalog: Catalog) -> None:
    by_path = {item.path: item for item in catalog.fields}
    for path in ("cy-docs.--no-browser", "cy-docs.--check", "cy-dedup.--dry-run"):
        assert "default=False;" in by_path[path].constraints
        assert by_path[path].shapes == "flag (boolean)"
    assert "default=0;" in by_path["cy-docs.--port"].constraints
    assert by_path["cy-docs.--help"].shapes == "flag"
