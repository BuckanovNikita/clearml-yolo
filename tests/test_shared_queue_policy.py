"""Scheduling skips absent owners and unavailable complete allocations."""

import pytest
from pydantic import ValidationError


def test_earliest_runnable_skips_absent_owner_and_preserves_exact_order() -> None:
    from clearml_yolo.core.queue import (
        GPUObservation,
        PublicJob,
        ResourceRequest,
        earliest_runnable,
    )

    def job(identifier: str, owner: int, request: ResourceRequest) -> PublicJob:
        return PublicJob(
            id=identifier,
            owner_uid=owner,
            host_id="host",
            boot_id="boot",
            command="train",
            request=request,
            submitted_at=1,
        )

    jobs = (
        job("absent", 10, ResourceRequest(gpus=1)),
        job("too-large", 20, ResourceRequest(gpus=3)),
        job("exact", 20, ResourceRequest(devices=("GPU-b", "GPU-a"))),
        job("later", 20, ResourceRequest(gpus=1)),
    )
    cards = (
        GPUObservation(uuid="GPU-a", available=True),
        GPUObservation(uuid="GPU-b", available=True),
    )
    allocation = earliest_runnable(jobs, cards, {20})
    assert allocation is not None
    assert allocation.job_id == "exact"
    assert allocation.devices == ("GPU-b", "GPU-a")
    follower = earliest_runnable(jobs, cards, {20}, reserved={"GPU-b"})
    assert follower is not None
    assert follower.job_id == "later"


@pytest.mark.parametrize(
    "values",
    [
        {"gpus": 0},
        {"gpus": True},
        {"gpus": 1.5},
        {"devices": ()},
        {"devices": ("GPU-a", "GPU-a")},
        {"devices": ("MIG-a",)},
        {"gpus": 2, "devices": ("GPU-a",)},
    ],
)
def test_invalid_resource_requests_fail_before_storage(values: dict[str, object]) -> None:
    from clearml_yolo.core.queue import ResourceRequest

    with pytest.raises(ValidationError):
        ResourceRequest.model_validate(values)


def test_snapshot_is_immutable_and_requires_mapping_configuration() -> None:
    from clearml_yolo.core.queue import JobSnapshot, ResourceRequest

    values = {
        "command": "train",
        "config_json": '{"device": 0}',
        "project_root": "/project",
        "cwd": "/project",
        "interpreter": "/python",
        "package_version": "1",
        "package_identity": "source-hash",
        "request": ResourceRequest(gpus=1),
    }
    snapshot = JobSnapshot.model_validate(values)
    with pytest.raises(ValidationError):
        snapshot.command = "predict"
    with pytest.raises(ValidationError):
        JobSnapshot.model_validate(values | {"config_json": "[]"})


def test_owner_specific_visibility_does_not_starve_runnable_later_owner() -> None:
    from clearml_yolo.core.queue import (
        GPUObservation,
        PublicJob,
        ResourceRequest,
        earliest_runnable,
    )

    jobs = tuple(
        PublicJob(
            id=str(uid),
            owner_uid=uid,
            host_id="h",
            boot_id="b",
            command="train",
            request=ResourceRequest(gpus=1),
            submitted_at=0,
        )
        for uid in (10, 20)
    )
    own = (GPUObservation(uuid="GPU-b", available=True),)
    inventories = {10: (GPUObservation(uuid="GPU-a", available=False),), 20: own}
    allocation = earliest_runnable(jobs, own, {10, 20}, owner_observations=inventories)
    assert allocation is not None
    assert allocation.job_id == "20"
    assert allocation.devices == ("GPU-b",)
