"""Pipeline stage configs must resolve to plain Python before reaching third parties."""

from __future__ import annotations

import pickle
from collections.abc import Callable
from pathlib import Path

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import instantiate, store, zen
from omegaconf import OmegaConf

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.gpu import DeviceSelection
from clearml_yolo.tasks import pipeline as pipeline_module
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, NoBaselineModelError
from clearml_yolo.tasks.pipeline import (
    _as_dict,
    run_compare_stage,
    run_pipeline,
    run_predict_stage,
    stage_configs,
)
from clearml_yolo.tasks.train import _inference_device

STAGES = ["train", "predict", "metrics", "report", "compare"]


@pytest.fixture(scope="module", autouse=True)
def hydra_store() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


def _recording_prediction(seen: dict[str, object]) -> Callable[..., Path]:
    """Stand in for the predict task, keeping the keyword arguments it was called with."""

    def run_prediction(**kwargs: object) -> Path:
        seen.update(kwargs)
        return Path("out.csv")

    return run_prediction


def _stage_config(stage: str) -> dict:  # type: ignore[type-arg]
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline")
    return _as_dict(config[stage])


def _stage_configs() -> dict[str, dict[str, object]]:
    """Compose the pipeline and build each stage's kwargs the way run_pipeline does.

    Composing alone proves nothing about what a stage receives: the shared values are not
    in the stage blocks at all, they are handed over by ``stage_configs``.
    """
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline")
    return stage_configs(
        train=config.train,
        predict=config.predict,
        metrics=config.metrics,
        report=config.report,
        compare=config.compare,
        clearml=instantiate(config.clearml),
        auto_gpu=instantiate(config.auto_gpu),
        ground_truth=config.ground_truth,
        splits=config.splits,
        weights=config.get("weights"),
    )


@pytest.mark.parametrize("stage", STAGES)
def test_no_omegaconf_containers_survive(stage: str) -> None:
    for key, value in _stage_configs()[stage].items():
        assert not OmegaConf.is_config(value), f"{stage}.{key} is still {type(value)}"


def test_ultralytics_params_are_picklable() -> None:
    """Ultralytics pickles trainer.args when saving a checkpoint, so the whole parameter
    block must survive pickling — a DictConfig backed by a generated dataclass does not."""
    params = _stage_config("train")["ultralytics"]

    assert isinstance(params, dict)
    pickle.loads(pickle.dumps(params))


@pytest.mark.parametrize("stage", STAGES)
def test_whole_stage_config_is_picklable(stage: str) -> None:
    config = _stage_configs()[stage]
    # The pydantic sub-configs are ours and pickle fine; this guards the rest.
    plain = {k: v for k, v in config.items() if not hasattr(v, "model_dump")}

    pickle.loads(pickle.dumps(plain))


def test_training_names_its_first_device_for_inference() -> None:
    on_gpus = DeviceSelection(devices=[2, 3], batch=32, batch_per_gpu=16)
    on_cpu = DeviceSelection(devices="cpu", batch=16, batch_per_gpu=16)

    assert _inference_device(on_gpus) == "2"
    assert _inference_device(on_cpu) is None


def test_inference_reuses_the_card_training_just_used(monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-surveying here would wait for a device this very process still holds."""
    seen: dict[str, object] = {}
    monkeypatch.setattr(pipeline_module, "run_prediction", _recording_prediction(seen))

    config = _stage_config("predict") | {"clearml": ClearMLConfig(enabled=False)}
    run_predict_stage(config, "best.pt", "1")

    assert seen["ultralytics"]["device"] == "1"  # type: ignore[index]


def test_a_card_named_in_the_config_still_wins_over_training(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reusing training's card is what an unset device means, not what it overrides."""
    seen: dict[str, object] = {}
    monkeypatch.setattr(pipeline_module, "run_prediction", _recording_prediction(seen))

    config = _stage_config("predict") | {"clearml": ClearMLConfig(enabled=False)}
    config["ultralytics"] = {**_stage_config("predict")["ultralytics"], "device": "3"}
    run_predict_stage(config, "best.pt", "1")

    assert seen["ultralytics"]["device"] == "3"  # type: ignore[index]


def test_comparison_scores_the_model_this_run_just_built(monkeypatch: pytest.MonkeyPatch) -> None:
    """The candidate comes from the run, not from config, which could name another model."""
    seen: dict[str, object] = {}
    monkeypatch.setattr(pipeline_module, "run_comparison", lambda **kwargs: seen.update(kwargs))

    # run_compare_stage is only ever called with a block that has gone through
    # stage_configs, so this is what its caller actually hands it — not a bare composed
    # stage block, which no longer carries ground_truth at all.
    config = _stage_configs()["compare"] | {"clearml": ClearMLConfig(enabled=False)}
    run_compare_stage(config, "runs/detect/train/weights/best.pt", {"test": {"car": 0.4}})

    candidate = seen["candidate_model"]
    assert isinstance(candidate, ModelRef)
    assert candidate.source == "local"
    assert candidate.weights == Path("runs/detect/train/weights/best.pt")
    assert candidate.thresholds == {"car": 0.4}
    # The comparison reads the ground truth the run handed every stage, so the three
    # cannot drift apart.
    assert seen["ground_truth"] == "ground_truth.csv"


def test_the_comparison_reuses_the_card_training_just_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same hazard the predict stage documents: surveying here would wait on a card this
    very process still holds. Both models still go on one card, which is why
    `_comparison_inference` never copies `device` from the predict stage."""
    seen: dict[str, object] = {}
    monkeypatch.setattr(pipeline_module, "run_comparison", lambda **kwargs: seen.update(kwargs))

    config = _stage_config("compare") | {"clearml": ClearMLConfig(enabled=False)}
    run_compare_stage(config, "best.pt", {"test": {"car": 0.4}}, "1")

    inference = seen["inference"]
    assert isinstance(inference, InferenceConfig)
    assert inference.device == "1"


def test_a_split_no_stage_scores_is_rejected_before_training_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The split list reaches every stage from the run, but singling one out of it is not,
    so this is the one cross-stage mismatch config alone cannot rule out."""
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=["splits=[train,val]", "clearml.enabled=false"],
        )

    with pytest.raises(ValueError, match=r"compare\.split"):
        zen(run_pipeline)(config)


def test_a_named_checkpoint_without_skip_train_is_rejected_before_training_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """weights names a checkpoint for a run that is about to train its own; training would
    silently overwrite it with the model it just built, so the mismatch must be caught
    before an hour of training rather than after."""
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=["weights=runs/old/best.pt", "clearml.enabled=false"],
        )

    with pytest.raises(ValueError, match="weights"):
        zen(run_pipeline)(config)


def test_a_run_without_calibrated_thresholds_skips_rather_than_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skipping metrics leaves no thresholds; that must not fail a run with valid results."""
    monkeypatch.setattr(
        pipeline_module, "run_comparison", lambda **kwargs: pytest.fail("should not run")
    )

    config = _stage_config("compare") | {"clearml": ClearMLConfig(enabled=False)}
    assert run_compare_stage(config, "best.pt", {}) is None


def test_a_first_run_with_nothing_to_compare_against_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty project is the normal first-run case, not an error."""

    def _no_baseline(**_: object) -> None:
        raise NoBaselineModelError("No completed task tagged ['prod'] in project 'fresh'")

    monkeypatch.setattr(pipeline_module, "run_comparison", _no_baseline)

    config = _stage_config("compare") | {"clearml": ClearMLConfig(enabled=False)}
    assert run_compare_stage(config, "best.pt", {"test": {"car": 0.4}}) is None


def test_an_explicit_device_still_wins_over_training(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(pipeline_module, "run_prediction", _recording_prediction(seen))
    config = _stage_config("predict") | {"device": "0", "clearml": ClearMLConfig(enabled=False)}

    run_predict_stage(config, "best.pt", "1")

    assert seen["device"] == "0"
