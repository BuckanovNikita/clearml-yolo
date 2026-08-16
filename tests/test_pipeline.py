"""Pipeline stage configs must resolve to plain Python before reaching third parties."""

from __future__ import annotations

import pickle
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import instantiate, store, zen
from omegaconf import OmegaConf

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo import run_identity
from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.gpu import DeviceSelection
from clearml_yolo.run_identity import LATEST_LINK_NAME, RUNS_ROOT
from clearml_yolo.tasks import pipeline as pipeline_module
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, NoBaselineModelError
from clearml_yolo.tasks.metrics import DASHBOARD_PREFIX
from clearml_yolo.tasks.pipeline import (
    METRICS_DIR,
    PREDICTIONS_NAME,
    _as_dict,
    _resolve_run_directories,
    run_compare_stage,
    run_pipeline,
    run_predict_stage,
    stage_configs,
)
from clearml_yolo.tasks.train import _inference_device

STAGES = ["train", "predict", "metrics", "report", "compare"]
RUN_DIR = Path("runs/exp-here")
PREVIOUS_RUN_DIR = Path("runs/exp-before")


class _ReachedTrainingError(Exception):
    """Raised in place of training, so a test can assert a run got past every check.

    A pre-flight check that exempts a config is only proven by the run reaching the work
    it guards. Asserting some other check's error instead proves nothing: the checks run
    in order, and an earlier one raising would satisfy that assertion whether or not the
    check under test was ever reached.
    """


def _reached_training(**_: object) -> None:
    raise _ReachedTrainingError


def _recording_training(seen: list[dict[str, object]]) -> Callable[..., None]:
    """Keep what training was asked to do, then stand in for doing it."""

    def run_training(**kwargs: object) -> None:
        seen.append(kwargs)
        raise _ReachedTrainingError

    return run_training


def _train_project(kwargs: dict[str, object]) -> str:
    params: dict[str, Any] = kwargs["ultralytics"]  # type: ignore[assignment]
    return str(params["project"])


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


def _stage_configs(
    skip_predict: bool = False, skip_metrics: bool = False
) -> dict[str, dict[str, object]]:
    """Compose the pipeline and build each stage's kwargs the way run_pipeline does.

    Composing alone proves nothing about what a stage receives: the shared values are not
    in the stage blocks at all, they are handed over by ``stage_configs``.

    The skip flags are part of that: a stage this run does not run wrote nothing into this
    run's directory, so what its consumer is handed depends on them.
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
        run_dir=RUN_DIR,
        previous_run_dir=PREVIOUS_RUN_DIR,
        skip_predict=skip_predict,
        skip_metrics=skip_metrics,
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


def test_scoring_at_a_resolution_this_run_does_not_train_at_is_rejected_before_training(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The checkpoint the predict stage's own warning compares against does not exist until
    training has finished, so without this the mismatch costs the whole training run — and
    a model measured at a scale it was never shown is not a measurement of that model."""
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                "train.ultralytics.imgsz=640",
                "predict.ultralytics.imgsz=1280",
                "clearml.enabled=false",
            ],
        )

    with pytest.raises(ValueError, match="imgsz=1280"):
        zen(run_pipeline)(config)


def test_a_run_that_only_compares_still_reaches_the_resolution_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_comparison_inference` copies the predict block's resolution, so the comparison is
    the second stage that can score this run's own checkpoint at the wrong scale — and it
    runs last, which is the most expensive place to find out."""
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                "train.ultralytics.imgsz=640",
                "predict.ultralytics.imgsz=1280",
                "skip_predict=true",
                "skip_metrics=true",
                "report.baseline.task_id=abc123",
                "clearml.enabled=false",
            ],
        )

    with pytest.raises(ValueError, match="imgsz=1280"):
        zen(run_pipeline)(config)


@pytest.mark.parametrize(
    "resolutions",
    [
        pytest.param([], id="predict_reads_it_from_the_checkpoint"),
        pytest.param(["predict.ultralytics.imgsz=640"], id="named_and_agreeing"),
    ],
)
def test_a_resolution_that_cannot_disagree_reaches_training(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, resolutions: list[str]
) -> None:
    """Null is the answer rather than the problem — it is filled from the checkpoint, which
    cannot disagree with the weights it describes — and a named resolution matching the one
    being trained is the case this check exists to leave alone.

    Reaching training is the assertion, for the reason `_ReachedTrainingError` documents.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", _reached_training)
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_path,split\na.png,test\n")
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                "train.ultralytics.imgsz=640",
                f"ground_truth={truth}",
                "skip_compare=true",
                "clearml.enabled=false",
                *resolutions,
            ],
        )

    with pytest.raises(_ReachedTrainingError):
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
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", _reached_training)
    missing = tmp_path / "nowhere.csv"
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                f"ground_truth={missing}",
                "skip_predict=true",
                "skip_metrics=true",
                # The report is skipped as well because a run that scores nothing has no
                # dashboard of its own to report on, which is a different refusal than the
                # one under test here — see
                # `test_a_run_that_skips_scoring_with_no_dashboards_is_refused_up_front`.
                "skip_report=true",
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
    monkeypatch.chdir(tmp_path)
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


def _run_alone(overrides: list[str]) -> None:
    """Compose and run the pipeline the way the CLI does, up to training."""
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                "clearml.enabled=false",
                "skip_predict=true",
                "skip_metrics=true",
                "skip_report=true",
                "skip_compare=true",
                *overrides,
            ],
        )
    zen(run_pipeline)(config)


def test_two_runs_in_one_folder_never_train_into_the_same_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """This is the destructive case, not merely a confusing one: both runs used to train
    into `runs/detect/<task_name>` with ultralytics' `exist_ok` set, and its DDP launcher
    clears that directory before spawning its children — so starting the second run
    deletes the first one's checkpoints.

    Both runs are started in the same second, so the pid is the only thing separating
    them here, which is exactly the case a stamp alone would not cover.
    """
    monkeypatch.chdir(tmp_path)
    seen: list[dict[str, object]] = []
    monkeypatch.setattr(pipeline_module, "run_training", _recording_training(seen))
    pid = {"value": 4001}
    monkeypatch.setattr(run_identity, "_host_and_pid", lambda: ("box", pid["value"]))

    for value in (4001, 4002):
        pid["value"] = value
        with pytest.raises(_ReachedTrainingError):
            _run_alone(["clearml.task_name=kitti"])

    first, second = (_train_project(kwargs) for kwargs in seen)
    assert first != second
    # The link names the run that started last, so `ls runs/latest/metrics` keeps working.
    assert str((tmp_path / "runs" / LATEST_LINK_NAME).resolve()) == str(Path(second).parent)


def test_a_named_run_directory_is_where_everything_that_run_writes_goes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Naming it is how two runs share a directory on purpose — a rerun landing beside an
    earlier one — and it has to move the whole run, not the checkpoints alone."""
    monkeypatch.chdir(tmp_path)
    seen: list[dict[str, object]] = []
    monkeypatch.setattr(pipeline_module, "run_training", _recording_training(seen))
    chosen = tmp_path / "sweeps" / "07"

    with pytest.raises(_ReachedTrainingError):
        _run_alone([f"run_dir={chosen}"])

    assert _train_project(seen[0]) == str(chosen / "detect")


def test_a_run_that_skips_training_with_nothing_to_load_is_refused_up_front(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """In a folder no run has finished in, `runs/latest` is not there, so the checkpoint a
    skipped training stage would load is a path to nothing. Left to ultralytics it reads
    as a failed download of a pretrained model, naming neither the link nor the key that
    would have pointed the run at a real one."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_prediction", lambda **kwargs: pytest.fail("ran"))
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_name,image_path,instance_label,split\n")

    with pytest.raises(FileNotFoundError, match=r"latest/detect/.*/weights/best\.pt"):
        _run_alone(["skip_train=true", "skip_predict=false", f"ground_truth={truth}"])


def _previous_run(root: Path) -> Path:
    """A finished run for ``latest`` to name, which is where a skipped stage's input is.

    Built through ``point_latest_at`` rather than by writing a symlink here, because the
    link is the mechanism under test on the reading side too: a run reads it before it
    repoints it.
    """
    directory = (root / RUNS_ROOT / "before").resolve()
    directory.mkdir(parents=True, exist_ok=True)
    run_identity.point_latest_at(RUNS_ROOT, directory)
    return directory


def test_a_run_that_skips_inference_scores_what_the_run_before_it_wrote() -> None:
    """This run's directory is minted empty, so the only thing that could ever write the
    predictions inside it is the inference stage the flag just skipped — and the metrics
    stage opens that path unguarded. Skipping inference means scoring the last run's."""
    own = _stage_configs()["metrics"]["predictions"]
    inherited = _stage_configs(skip_predict=True)["metrics"]["predictions"]

    assert own == str(RUN_DIR / PREDICTIONS_NAME)
    assert inherited == str(PREVIOUS_RUN_DIR / PREDICTIONS_NAME)


def test_a_run_that_skips_scoring_reports_on_what_the_run_before_it_wrote() -> None:
    """Same directory, same reason: pointed at this run's own empty metrics directory the
    report finds no dashboard, and builds nothing while exiting 0."""
    own = _stage_configs()["report"]["metrics_dir"]
    inherited = _stage_configs(skip_metrics=True)["report"]["metrics_dir"]

    assert own == str(RUN_DIR / METRICS_DIR)
    assert inherited == str(PREVIOUS_RUN_DIR / METRICS_DIR)


def test_a_run_that_skips_inference_with_nothing_to_score_is_refused_up_front(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reached through ``latest``, the predictions of a folder where no run has inferred are
    a path to nothing, and the metrics stage runs after training: left to pandas the run
    trains for its whole duration to arrive at a bare filename that names neither the flag
    that redirected it nor the run that was supposed to have written it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_name,image_path,instance_label,split\n")

    with pytest.raises(FileNotFoundError, match="skip_predict=true"):
        _run_alone(["skip_metrics=false", f"ground_truth={truth}"])


def test_a_run_that_skips_inference_scores_the_previous_predictions_when_they_are_there(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The case the flag exists for, and the one a refusal must leave alone.

    Reaching training is the assertion, for the reason ``_ReachedTrainingError`` documents.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", _reached_training)
    (_previous_run(tmp_path) / PREDICTIONS_NAME).write_text("image_name,label,score\n")
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_name,image_path,instance_label,split\n")

    with pytest.raises(_ReachedTrainingError):
        _run_alone(["skip_metrics=false", f"ground_truth={truth}"])


def test_a_run_that_skips_scoring_with_no_dashboards_is_refused_up_front(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The silent one: with no dashboard to read, ``build_reports`` has no split to resolve
    a baseline for and warns about the baseline instead — a cause that is not the one — then
    returns an empty result and lets the run exit 0 having written no workbook."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))

    with pytest.raises(FileNotFoundError, match="skip_metrics=true"):
        _run_alone(["skip_report=false"])


def test_a_run_that_skips_scoring_reports_the_previous_dashboards_when_they_are_there(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """One split's dashboard is enough to have something to report on, which is the same
    bar ``discover_dashboards`` sets for the run itself."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", _reached_training)
    dashboards = _previous_run(tmp_path) / METRICS_DIR
    dashboards.mkdir()
    (dashboards / f"{DASHBOARD_PREFIX}_test.xlsx").write_bytes(b"")

    with pytest.raises(_ReachedTrainingError):
        _run_alone(["skip_report=false"])


@pytest.mark.parametrize(
    ("run_id", "run_dir", "reads"),
    [
        (None, "sweeps/07", Path("sweeps/07")),
        ("sweep-07", None, RUNS_ROOT / "sweep-07"),
    ],
)
def test_a_run_told_which_run_it_is_reads_its_own_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    run_id: str | None,
    run_dir: str | None,
    reads: Path,
) -> None:
    """A caller who names the directory or the id is re-entering a run that already exists
    — rebuilding its report, rescoring the predictions it wrote earlier — so the stages it
    skips have that same directory's own outputs to read.

    Read through ``latest`` instead, those stages take whichever run finished last, and the
    result is written into the named directory as if it were that run's own: a report built
    from another model's dashboards, silently, because the other run's files do exist.
    """
    monkeypatch.chdir(tmp_path)
    _previous_run(tmp_path)

    directory, previous = _resolve_run_directories(ClearMLConfig(enabled=False), run_id, run_dir)

    assert directory == (tmp_path / reads).resolve()
    assert previous == directory


def test_a_run_that_was_not_told_which_run_it_is_reads_the_run_before_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The default run's own directory is minted empty, so the only outputs a stage it
    skips can read are the last finished run's, and ``latest`` is what names that run."""
    monkeypatch.chdir(tmp_path)
    previous_run = _previous_run(tmp_path)

    directory, previous = _resolve_run_directories(ClearMLConfig(enabled=False), None, None)

    assert previous == previous_run
    assert directory != previous


def test_a_named_directory_is_not_rescued_by_another_runs_predictions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The refusal has to fire on the path the run actually scores. With the check reading
    ``latest`` while the run reads its own directory, a peer run's CSV passes a check for a
    file the named run never wrote."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    (_previous_run(tmp_path) / PREDICTIONS_NAME).write_text("image_name,label,score\n")
    named = tmp_path / "sweeps" / "07"
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_name,image_path,instance_label,split\n")

    with pytest.raises(FileNotFoundError, match=r"sweeps/07/predictions\.csv"):
        _run_alone([f"run_dir={named}", "skip_metrics=false", f"ground_truth={truth}"])


def test_a_named_directory_scores_the_predictions_it_holds_itself(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The case the naming exists for: re-entering a directory to score what it holds, with
    ``latest`` pointing at some other run that has nothing to offer it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", _reached_training)
    _previous_run(tmp_path)
    named = tmp_path / "sweeps" / "07"
    named.mkdir(parents=True)
    (named / PREDICTIONS_NAME).write_text("image_name,label,score\n")
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_name,image_path,instance_label,split\n")

    with pytest.raises(_ReachedTrainingError):
        _run_alone([f"run_dir={named}", "skip_metrics=false", f"ground_truth={truth}"])


def test_a_refused_run_leaves_latest_naming_the_run_before_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A run that refuses writes nothing, so it must not have moved the link either: every
    default that reads what the last run produced — the checkpoint, the predictions, the
    dashboards — follows ``latest``, and a refusing run that repointed it at its own empty
    directory would take the next run down with it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline_module, "run_training", lambda **kwargs: pytest.fail("trained"))
    previous = _previous_run(tmp_path)
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_name,image_path,instance_label,split\n")

    with pytest.raises(FileNotFoundError, match="skip_predict=true"):
        _run_alone(["skip_metrics=false", f"ground_truth={truth}"])

    root = tmp_path / RUNS_ROOT
    assert (root / LATEST_LINK_NAME).resolve() == previous
    assert [entry.name for entry in root.iterdir() if not entry.is_symlink()] == [previous.name]


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
