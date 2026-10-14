"""Bounded generated checks with independent semantic and durable-state oracles."""

import json
import os
import sys
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, override

import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule
from omegaconf import OmegaConf

from clearml_yolo.adapters.evaluation.scoring import (
    compute_evaluation,
    filter_invalid_prediction_boxes,
)
from clearml_yolo.adapters.queue.coordination import host_transaction
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.adapters.yolo.reinfer import reinfer_split
from clearml_yolo.core.identity import ModelIdentity
from clearml_yolo.core.queue import JobSnapshot, JobState, WorkerIdentity
from clearml_yolo.entrypoints.hydra.config_resolution import resolve_config_document

_LEXICAL = st.sampled_from(["0001", "10", "ёж", "猫", "e\u0301", "é", "001,猫"])
_CONFIDENCE = st.sampled_from([0.0, 0.2, 0.5, 0.700000000000003, 1.0])
_BOUNDS = settings(max_examples=24, deadline=None, derandomize=True, database=None)
_BOX_COLUMNS = ["bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]
_PRED_COLUMNS = ["image_name", "instance_label", *_BOX_COLUMNS, "confidence"]


@_BOUNDS
@given(label=_LEXICAL, image=_LEXICAL, confidence=_CONFIDENCE, enabled=st.booleans())
def test_resolved_yaml_json_snapshot_preserves_lexical_identity_and_types(
    label: str, image: str, confidence: float, enabled: bool
) -> None:
    """Saved configs must preserve string identities and exact primitive values."""
    identity = ModelIdentity(model_name=label, training_task_id="00001234")
    document = {
        "identity": identity.model_dump(mode="json"),
        "image_name": image,
        "threshold": confidence,
        "enabled": enabled,
        "device": None,
        "copy": "${identity.model_name}",
        "nested": ["${threshold}", "${enabled}", "${device}"],
    }
    saved = OmegaConf.create(OmegaConf.to_yaml(OmegaConf.create(document)))
    resolved = resolve_config_document(saved)
    snapshot = JobSnapshot(
        command="metrics",
        config_json=json.dumps(resolved, ensure_ascii=False),
        project_root="/project",
        cwd="/project",
        interpreter="/python",
        package_version="1",
        package_identity="source",
    )
    loaded = json.loads(JobSnapshot.model_validate_json(snapshot.model_dump_json()).config_json)
    assert loaded["image_name"] == image
    assert loaded["identity"]["model_name"] == loaded["copy"] == label
    assert loaded["identity"]["training_task_id"] == "00001234"
    assert loaded["nested"] == [confidence, enabled, None]
    assert type(loaded["nested"][0]) is float
    assert type(loaded["nested"][1]) is bool
    assert ModelIdentity.model_validate(loaded["identity"]) == identity


@_BOUNDS
@given(label=_LEXICAL, image=_LEXICAL, confidence=_CONFIDENCE)
@example(label="0001", image="0010", confidence=0.700000000000003)
@example(label="e\u0301", image="é", confidence=0.5)
def test_real_prediction_cache_roundtrip_preserves_lexical_and_float_values(
    label: str, image: str, confidence: float
) -> None:
    with TemporaryDirectory(prefix="cy-quality-cache-", dir=os.environ["CY_HOME"]) as temporary:
        root = Path(temporary)
        path = root / "image.jpg"
        path.write_bytes(b"model effects are replaced")
        truth = pd.DataFrame(
            {
                "image_name": [image],
                "image_path": [str(path)],
                "instance_label": [label],
                "split": ["test"],
            }
        )
        calls: list[list[str]] = []

        def predictor(_weights: object, paths: list[str], **_kwargs: Any) -> pd.DataFrame:
            calls.append(paths)
            return pd.DataFrame([(image, label, 0, 0, 10, 10, confidence)], columns=_PRED_COLUMNS)

        arguments: dict[str, Any] = {
            "conf": 0.001,
            "iou": 0.7,
            "imgsz": 64,
            "batch": 1,
            "device": "cpu",
            "image_name": "stem",
            "native_project": root / "native",
            "native_name": "test",
            "predictor": predictor,
            "class_names": lambda _: {0: label},
        }
        output = root / "cache.csv"
        reinfer_split(root / "best.pt", truth, "test", output, **arguments)
        original = output.read_bytes()
        cached, vocabulary = reinfer_split(root / "best.pt", truth, "test", output, **arguments)
        assert calls == [[str(path)]]
        assert output.read_bytes() == original
        assert cached["image_name"].tolist() == [image]
        assert cached["instance_label"].tolist() == [label]
        assert cached["confidence"].tolist() == [confidence]
        assert vocabulary.model_classes == [label]
        assert vocabulary.unknown_to_model == []


@_BOUNDS
@given(
    label=_LEXICAL,
    threshold=_CONFIDENCE,
    detections=st.lists(st.tuples(st.booleans(), _CONFIDENCE), min_size=1, max_size=5),
    invalid=st.booleans(),
)
@example(label="0001", threshold=0.5, detections=[(False, 0.5)], invalid=False)
@example(label="ёж", threshold=0.5, detections=[(True, 0.5)], invalid=True)
def test_fixed_threshold_counts_match_disjoint_scene_reference(
    label: str, threshold: float, detections: list[tuple[bool, float]], invalid: bool
) -> None:
    """Each image has one GT and optionally one exact TP and one disjoint FP."""
    gt_rows = []
    prediction_rows = []
    for index, (detected, confidence) in enumerate(detections):
        name = f"{index:04}"
        gt_rows.append((name, label, 0, 0, 10, 10, "test"))
        if detected:
            prediction_rows.extend(
                [
                    (name, label, 0, 0, 10, 10, confidence),
                    (name, label, 20, 20, 30, 30, confidence),
                ]
            )
        if invalid:
            prediction_rows.append((name, label, 0, 0, 0, 10, 1.0))
    truth = pd.DataFrame(gt_rows, columns=[*_PRED_COLUMNS[:-1], "split"])
    predictions = pd.DataFrame(prediction_rows, columns=_PRED_COLUMNS)
    original = predictions.copy(deep=True)
    valid = filter_invalid_prediction_boxes(predictions)
    computed = compute_evaluation(
        truth,
        valid,
        valid,
        split="test",
        classes=[label],
        thresholds={label: threshold},
        required_classes=[label],
        iou_threshold=0.5,
        matching_strategy="iou_prior",
        ap_method="interp",
        skip_cohen_kappa=True,
    )
    expected_hits = sum(detected and confidence >= threshold for detected, confidence in detections)
    counts = computed.outcome.counts[label]
    assert (counts.tp, counts.fp, counts.fn) == (
        expected_hits,
        expected_hits,
        len(detections) - expected_hits,
    )
    assert computed.thresholds == {label: threshold}
    assert computed.image_names == [f"{index:04}" for index in range(len(detections))]
    assert len(computed.evaluation_payload.ground_truth) == len(detections)
    pd.testing.assert_frame_equal(predictions, original)


class DurableQueueSequences(RuleBasedStateMachine):
    """Compare real private/public records against a tiny independent state ledger."""

    def __init__(self) -> None:
        super().__init__()
        self.temporary = TemporaryDirectory(prefix="cy-quality-queue-")
        self.root = Path(self.temporary.name)
        self.patch = pytest.MonkeyPatch()
        self.patch.setattr(
            "clearml_yolo.adapters.queue.storage.host_transaction",
            partial(host_transaction, root=self.root / "coordination"),
        )
        self.store = NFSQueueStore(
            self.root / "queue",
            WorkerIdentity(owner_uid=os.geteuid(), host_id="quality", boot_id="boot"),
        )
        self.order: list[str] = []
        self.states: dict[str, JobState] = {}
        self.configurations: dict[str, str] = {}

    @rule(label=_LEXICAL)
    def submit(self, label: str) -> None:
        configuration = json.dumps({"label": label, "device": None}, ensure_ascii=False)
        snapshot = JobSnapshot(
            command="train",
            label=label,
            config_json=configuration,
            project_root=str(self.root),
            cwd=str(self.root),
            interpreter=sys.executable,
            package_version="1",
            package_identity="source",
        )
        job = self.store.submit((snapshot,))[0]
        self.order.append(job.id)
        self.states[job.id] = "pending"
        self.configurations[job.id] = configuration

    @precondition(lambda self: bool(self.order))
    @rule(index=st.integers(min_value=0, max_value=20))
    def cancel(self, index: int) -> None:
        identifier = self.order[index % len(self.order)]
        old = self.states[identifier]
        self.store.cancel(identifier)
        if old == "pending":
            self.states[identifier] = "cancelled"
        elif old in {"starting", "running"}:
            self.states[identifier] = "cancelling"

    @precondition(
        lambda self: any(
            value in {"starting", "running", "cancelling"} for value in self.states.values()
        )
    )
    @rule(index=st.integers(min_value=0, max_value=20))
    def advance(self, index: int) -> None:
        active = [
            identifier
            for identifier in self.order
            if self.states[identifier] in {"starting", "running", "cancelling"}
        ]
        identifier = active[index % len(active)]
        old = self.states[identifier]
        transitions: dict[str, JobState] = {
            "starting": "running",
            "running": "completed",
            "cancelling": "cancelled",
        }
        next_state = transitions[old]
        self.store.update(identifier, next_state, expected_state=old)
        self.states[identifier] = next_state

    @precondition(lambda self: "pending" in self.states.values())
    @rule(index=st.integers(min_value=0, max_value=20), to_front=st.booleans())
    def reorder(self, index: int, to_front: bool) -> None:
        pending = [identifier for identifier in self.order if self.states[identifier] == "pending"]
        identifier = pending[index % len(pending)]
        anchor = pending[0] if to_front else pending[-1]
        revision = self.store.view().revision
        self.store.move(identifier, "top" if to_front else "bottom", revision)
        if identifier != anchor:
            self.order.remove(identifier)
            self.order.insert(self.order.index(anchor) + int(not to_front), identifier)
            with pytest.raises(RuntimeError, match="revision"):
                self.store.move(identifier, "top", revision)

    @precondition(lambda self: bool(self.order))
    @rule(index=st.integers(min_value=0, max_value=20))
    def start(self, index: int) -> None:
        identifier = self.order[index % len(self.order)]
        should_start = self.states[identifier] == "pending"
        assert self.store.prepare_start(identifier, ("GPU-a", "GPU-b"), "original") == should_start
        if should_start:
            self.states[identifier] = "starting"
            assert not self.store.prepare_start(identifier, ("GPU-c",), "replacement")
            guardian = self.store.snapshot_path(identifier).parent / "guardian.json"
            assert guardian.read_text(encoding="utf-8") == "original"

    @invariant()
    def public_state_and_private_snapshot_match_reference(self) -> None:
        view = self.store.view()
        assert [job.id for job in view.jobs] == self.order
        assert {job.id: job.state for job in view.jobs} == self.states
        for job in view.jobs:
            assert self.store.load_snapshot(job.id).config_json == self.configurations[job.id]
            if job.state in {"starting", "running", "cancelling", "completed"}:
                assert job.devices == ("GPU-a", "GPU-b")

    @override
    def teardown(self) -> None:
        self.patch.undo()
        self.temporary.cleanup()


TestDurableQueueSequences = DurableQueueSequences.TestCase
TestDurableQueueSequences.settings = settings(
    max_examples=16,
    stateful_step_count=18,
    deadline=None,
    derandomize=True,
    database=None,
)
