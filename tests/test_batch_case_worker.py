"""Case receipts bind complete search evidence to one isolated invocation."""

from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.application.training_workers import BatchCaseRequest, BatchCaseResult
from clearml_yolo.core.batch_estimation import SearchSettings, SyntheticWorkload, estimate_key
from clearml_yolo.entrypoints import batch_estimate_worker
from test_batch_estimate_workflow import RecordingProbe, sample_profile


def request_for(tmp_path: Path) -> BatchCaseRequest:
    profile = sample_profile().model_copy(
        update={"gpus": (sample_profile().gpus[0].model_copy(update={"uuid": "GPU-test"}),)}
    )
    workload, settings = SyntheticWorkload(), SearchSettings(max_global_batch=4)
    return BatchCaseRequest(
        token=uuid4().hex,
        estimate_key=estimate_key(profile, workload, settings),
        profile=profile,
        workload=workload,
        settings=settings,
        catalogue_path=tmp_path / "catalogue.json",
        output=tmp_path / "case",
    )


def test_case_worker_writes_validated_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = request_for(tmp_path)
    request.output.mkdir()
    path = request.output / "request.json"
    path.write_text(request.model_dump_json())
    probe = RecordingProbe()
    monkeypatch.setattr(batch_estimate_worker, "_make_probe", lambda: probe)
    assert batch_estimate_worker.run(path) == 0
    result = BatchCaseResult.model_validate_json((request.output / "result.json").read_text())
    assert result.token == request.token
    assert result.estimate_key == request.estimate_key
    assert result.case.usable
    assert result.case.profile.gpus == request.profile.gpus
    # Usable evidence remains only in the receipt until the parent checks exit
    # and descendant cleanup, so interruption cannot publish an unaccepted case.
    assert not FileBatchEstimateStore(request.catalogue_path).read().cases[0].usable
    assert not (request.output / "result.json.pending").exists()


def test_request_rejects_mismatched_identity(tmp_path: Path) -> None:
    raw = request_for(tmp_path).model_dump(mode="json")
    raw["estimate_key"] = "0" * 64
    with pytest.raises(ValidationError, match="key"):
        BatchCaseRequest.model_validate(raw)


def test_request_requires_one_identified_gpu(tmp_path: Path) -> None:
    raw = request_for(tmp_path).model_dump(mode="json")
    raw["profile"]["gpus"][0]["uuid"] = None
    with pytest.raises(ValidationError, match="GPU"):
        BatchCaseRequest.model_validate(raw)
