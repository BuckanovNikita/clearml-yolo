"""The standard installation contains every supported runtime capability."""

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_PACKAGES = {
    "calflops",
    "faster-coco-eval",
    "pycocotools",
    "pytorch-lightning",
    "rfdetr",
    "tensorboard",
    "timm",
    "torch",
    "torchvision",
    "onnx",
    "onnxruntime",
}


def _unbounded_dependencies(requirements: list[str]) -> set[str]:
    return {
        requirement.name
        for text in requirements
        for requirement in [Requirement(text)]
        if not any(specifier.operator in {">=", "==", "~="} for specifier in requirement.specifier)
    }


def test_standard_installation_contains_all_runtime_capabilities() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    assert not project.get("optional-dependencies")
    requirements: dict[str, Requirement] = {
        canonicalize_name(requirement.name): requirement
        for text in project["dependencies"]
        for requirement in [Requirement(text)]
    }
    assert requirements.keys() >= CAPABILITY_PACKAGES
    assert all(requirements[name].marker is None for name in CAPABILITY_PACKAGES)
    assert requirements["rfdetr"].extras == {"train"}
    assert requirements["pandera"].extras == {"pandas"}
    assert not _unbounded_dependencies(project["dependencies"])


@pytest.mark.parametrize("requirement", ["numpy", "numpy<3", "numpy!=2.0", "numpy>1"])
def test_minimum_version_guard_rejects_missing_inclusive_floor(requirement: str) -> None:
    assert _unbounded_dependencies([requirement]) == {"numpy"}


@pytest.mark.parametrize("requirement", ["numpy>=2", "numpy==2.0", "numpy~=2.0"])
def test_minimum_version_guard_accepts_inclusive_floor(requirement: str) -> None:
    assert not _unbounded_dependencies([requirement])


def test_queue_distribution_is_not_a_cy_runtime_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    names = {canonicalize_name(Requirement(text).name) for text in project["dependencies"]}
    assert not names.intersection({"cy-queue", "textual", "nvidia-ml-py"})
    assert "cy-queue" not in project["scripts"]
