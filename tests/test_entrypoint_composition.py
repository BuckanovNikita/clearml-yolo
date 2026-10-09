"""Hydra injects capabilities only at invocation, outside the command schema."""

import inspect

import pytest
from omegaconf import OmegaConf

from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.entrypoints import composition
from clearml_yolo.entrypoints.hydra.common import _execute_assigned
from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys
from workflow_dependencies import workflow_dependencies as workflow_dependencies  # noqa: PLC0414


def test_command_invocation_injects_bundle_without_changing_serializable_function(
    monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    observed: list[tuple[int, WorkflowDependencies]] = []

    def workflow(value: int, *, deps: WorkflowDependencies) -> None:
        observed.append((value, deps))

    original_signature = inspect.signature(workflow)
    monkeypatch.setattr(composition, "build_dependencies", lambda: workflow_dependencies)
    _execute_assigned("metrics", OmegaConf.create({"value": 7}), workflow, None, ())

    assert observed == [(7, workflow_dependencies)]
    assert inspect.signature(workflow) == original_signature
    assert workflow.__module__ == __name__


def test_capabilities_cannot_be_supplied_as_a_hydra_override() -> None:
    def workflow(value: int, *, deps: WorkflowDependencies) -> None:
        pass

    with pytest.raises(ValueError, match=r"Unsupported wrapper settings.*deps"):
        validate_wrapper_keys(OmegaConf.create({"value": 7, "deps": {}}), workflow)
