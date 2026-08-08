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


class _ReachedTrainingError(Exception):
    """Raised in place of training, so a test can assert a run got past every check.

    A pre-flight check that exempts a config is only proven by the run reaching the work
    it guards. Asserting some other check's error instead proves nothing: the checks run
    in order, and an earlier one raising would satisfy that assertion whether or not the
    check under test was ever reached.
    """


def _reached_training(**_: object) -> None:
    raise _ReachedTrainingError


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
    """One stage's kwargs, from the shape ``zen`` hands ``run_pipeline``.

    ``instantiate`` first, because that is what the CLI does: the block arrives as the
    generated dataclass rather than as a ``DictConfig``, and the two differ in whether
    Hydra's ``defaults`` key is still present.
    """
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline")
    return _as_dict(instantiate(config[stage]))


def _stage_configs() -> dict[str, dict[str, object]]:
    """Compose the pipeline and build each stage's kwargs the way run_pipeline does.

    Composing alone proves nothing about what a stage receives: the shared values are not
    in the stage blocks at all, they are handed over by ``stage_configs``.
    """
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline")
    return stage_configs(
        train=instantiate(config.train),
        predict=instantiate(config.predict),
        metrics=instantiate(config.metrics),
        report=instantiate(config.report),
        compare=instantiate(config.compare),
        clearml=instantiate(config.clearml),
        auto_gpu=instantiate(config.auto_gpu),
        ground_truth=config.ground_truth,
        splits=config.splits,
        weights=config.get("weights"),
    )


@pytest.mark.parametrize("stage", STAGES)
def test_no_composition_key_reaches_a_task(stage: str) -> None:
    """Hydra's `defaults` is composition metadata, not a setting any task takes.

    It is absent from the composed DictConfig and present on the instantiated dataclass,
    so it reaches a task only on the path the CLI actually takes — where it arrives as an
    unexpected keyword argument minutes into a run.
    """
    assert "defaults" not in _stage_configs()[stage]


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


def test_a_missing_ground_truth_is_rejected_before_training_starts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Every stage that scores anything reads this CSV, but the first of them runs after
    training, so a path that does not exist costs the whole training run before pandas
    reports it — as a bare filename, with no hint that `cy-ground-truth` writes it."""
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    missing = tmp_path / "nowhere.csv"
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                f"ground_truth={missing}",
                "skip_compare=true",
                "clearml.enabled=false",
            ],
        )

    with pytest.raises(FileNotFoundError, match="cy-ground-truth"):
        zen(run_pipeline)(config)


def test_a_run_that_scores_nothing_needs_no_ground_truth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Training alone never opens the CSV, so requiring it would reject a valid run.

    Reaching training is the assertion: every pre-flight check has to have passed for the
    run to get that far, so a check that rejected this config could not hide behind an
    earlier one raising first.
    """
    monkeypatch.setattr(pipeline_module, "run_training", _reached_training)
    missing = tmp_path / "nowhere.csv"
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                f"ground_truth={missing}",
                "skip_predict=true",
                "skip_metrics=true",
                "skip_compare=true",
                "clearml.enabled=false",
            ],
        )

    with pytest.raises(_ReachedTrainingError):
        zen(run_pipeline)(config)


def test_a_comparison_that_cannot_reach_its_baseline_is_rejected_before_training_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inside the pipeline the baseline is always a ClearML task, so tracking turned off
    leaves the lookup nothing to search. The comparison is the last stage, so without this
    the run trains, predicts, scores and reports before failing on a lookup that could
    never have succeeded."""
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=["clearml.enabled=false"])

    with pytest.raises(ValueError, match="skip_compare"):
        zen(run_pipeline)(config)


def test_a_baseline_named_outright_survives_tracking_being_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A task id needs no project to search, so it is not the case this check rejects.

    The ground truth is written rather than left to the default: the repo's own
    `ground_truth.csv` is untracked, so a test that leaned on it would pass here and fail
    on a fresh clone.
    """
    monkeypatch.setattr(pipeline_module, "run_training", _reached_training)
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_name,image_path,instance_label,split\n")
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                "clearml.enabled=false",
                "report.baseline.task_id=" + "a" * 32,
                f"ground_truth={truth}",
            ],
        )

    with pytest.raises(_ReachedTrainingError):
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
