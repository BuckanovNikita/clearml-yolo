"""A disabled publisher has no runtime dependencies or side effects."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store

from test_clearml_report import warnings_log as warnings_log  # noqa: PLC0414 - fixture export


def test_disabled_publisher_does_not_import_fiftyone(tmp_path: Path) -> None:
    code = """
import sys
from pathlib import Path
from clearml_yolo.publishing import create_publisher
from clearml_yolo.publishing.models import FiftyOneConfig, PublicationRequest
publisher = create_publisher(FiftyOneConfig(enabled=False))
publisher.preflight()
request = PublicationRequest(task_id='test', ground_truth=Path('missing.csv'))
assert publisher.publish(request) is None
assert not any(name == 'fiftyone' or name.startswith('fiftyone.') for name in sys.modules)
"""
    result = subprocess.run(  # noqa: S603 - fixed interpreter and test-owned source
        [sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("command", ["pipeline", "predict", "metrics"])
def test_publishing_enabled_by_default_and_can_be_disabled(command: str) -> None:
    import clearml_yolo.configs  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        default = compose(config_name=command)
        disabled = compose(config_name=command, overrides=["fiftyone.enabled=false"])
    assert default.fiftyone.enabled is True
    assert default.fiftyone.dataset_prefix == "clearml-yolo"
    assert disabled.fiftyone.enabled is False


@pytest.mark.parametrize("command", ["train", "val", "compare", "report", "ground_truth"])
def test_other_commands_do_not_enable_publishing(command: str) -> None:
    import clearml_yolo.configs  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=command)
    assert "fiftyone" not in config


def test_fiftyone_receipt_stays_local_and_is_linked_from_run_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import UTC, datetime

    from clearml_yolo.publishing.models import PublicationReceipt
    from clearml_yolo.tasks import publication

    receipt = PublicationReceipt(
        dataset_name="clearml-yolo-fixture",
        task_id="publication-task",
        run_key="publication-task",
        ground_truth_sha256="truth-hash",
        source_ground_truth_sha256="truth-hash",
        dataset_reused=True,
        sample_count=3,
        fields={"predictions": "predictions_publication-task"},
        evaluation_keys={"val": "eval_validation"},
        dataset_complete=True,
        run_complete=True,
        payload_paths={},
        published_at=datetime(2026, 9, 29, tzinfo=UTC),
    )
    recorded: list[dict[str, object]] = []

    class Publisher:
        enabled = True

        def preflight(self) -> None:
            pass

        def publish(self, _request: object) -> PublicationReceipt:
            return receipt

    monkeypatch.setattr(
        publication,
        "record_run_configuration",
        lambda _task, values: recorded.append(values),
    )

    result = publication.publish_results(
        Publisher(),
        type("Task", (), {"id": "publication-task"})(),
        output_dir=tmp_path,
        ground_truth=tmp_path / "ground_truth.csv",
    )

    assert result == receipt
    assert (tmp_path / "fiftyone_publication.json").is_file()
    assert recorded == [
        {
            "fiftyone_result": {
                "dataset_name": "clearml-yolo-fixture",
                "run_key": "publication-task",
                "dataset_reused": True,
                "sample_count": 3,
                "fields": {"predictions": "predictions_publication-task"},
                "evaluation_keys": {"val": "eval_validation"},
            }
        }
    ]


@pytest.mark.parametrize("stage", ["factory", "preflight"])
def test_visualization_setup_failure_warns_and_disables_publication(
    stage: str, warnings_log: list[str]
) -> None:
    from clearml_yolo.publishing.models import FiftyOneConfig
    from clearml_yolo.tasks.publication import prepare_publisher

    class FailingPublisher:
        enabled = True

        def preflight(self) -> None:
            raise RuntimeError("database unavailable")

        def publish(self, _request: object) -> None:
            pytest.fail("failed preflight must disable publication")

    def factory(_config: FiftyOneConfig | None) -> FailingPublisher:
        if stage == "factory":
            raise ImportError("visualization backend unavailable")
        return FailingPublisher()

    result = prepare_publisher(SimpleNamespace(id="task"), FiftyOneConfig(), factory=factory)
    assert result.enabled is False
    assert any("FiftyOne visualization setup failed" in warning for warning in warnings_log)
    expected = "visualization backend unavailable" if stage == "factory" else "database unavailable"
    assert any(expected in warning and f"operation={stage}" in warning for warning in warnings_log)


@pytest.mark.parametrize("failure", [ValueError("invalid box"), OSError("database write failed")])
def test_visualization_publication_failure_warns_without_success_receipt(
    tmp_path: Path, failure: Exception, warnings_log: list[str]
) -> None:
    from clearml_yolo.tasks.publication import publish_results

    class FailingPublisher:
        enabled = True

        def preflight(self) -> None:
            pass

        def publish(self, _request: object) -> None:
            raise failure

    result = publish_results(
        FailingPublisher(), SimpleNamespace(id="task"), output_dir=tmp_path, ground_truth="gt.csv"
    )
    assert result is None
    assert not (tmp_path / "fiftyone_publication.json").exists()
    assert any(type(failure).__name__ in warning for warning in warnings_log)
    assert any(str(failure) in warning for warning in warnings_log)
    assert any("operation=publish" in warning for warning in warnings_log)
    assert any(
        "task_id=task" in warning and "ground_truth=gt.csv" in warning for warning in warnings_log
    )


@pytest.mark.parametrize("stage", ["factory", "preflight", "publication"])
def test_visualization_warnings_do_not_expose_backend_credentials(
    tmp_path: Path, stage: str, warnings_log: list[str]
) -> None:
    from clearml_yolo.publishing.models import FiftyOneConfig
    from clearml_yolo.tasks.publication import prepare_publisher, publish_results

    failure = RuntimeError("mongodb://user:private-password@host/?authSource=admin")

    class FailingPublisher:
        enabled = True

        def preflight(self) -> None:
            if stage == "preflight":
                raise failure

        def publish(self, _request: object) -> None:
            raise failure

    def factory(_config: FiftyOneConfig | None) -> FailingPublisher:
        if stage == "factory":
            raise failure
        return FailingPublisher()

    task = SimpleNamespace(id="task")
    publisher = prepare_publisher(task, FiftyOneConfig(), factory=factory)
    assert publish_results(publisher, task, output_dir=tmp_path, ground_truth="gt.csv") is None
    assert any("RuntimeError" in warning for warning in warnings_log)
    assert all("private-password" not in warning for warning in warnings_log)
    assert all("mongodb://" not in warning for warning in warnings_log)


@pytest.mark.parametrize("failure_stage", ["receipt", "run_configuration", "missing_receipt"])
def test_visualization_receipt_failure_does_not_fail_computation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
    warnings_log: list[str],
) -> None:
    from datetime import UTC, datetime

    from clearml_yolo.publishing.models import PublicationReceipt
    from clearml_yolo.tasks import publication

    receipt = PublicationReceipt(
        dataset_name="visualization",
        task_id="task",
        run_key="run",
        ground_truth_sha256="hash",
        source_ground_truth_sha256="hash",
        dataset_reused=False,
        sample_count=1,
        fields={},
        dataset_complete=True,
        run_complete=True,
        payload_paths={},
        published_at=datetime.now(UTC),
    )

    class Publisher:
        enabled = True

        def preflight(self) -> None:
            pass

        def publish(self, _request: object) -> PublicationReceipt | None:
            return None if failure_stage == "missing_receipt" else receipt

    def fail_record(*_args: Any) -> None:
        raise RuntimeError("visualization link unavailable")

    monkeypatch.setattr(publication, "record_run_configuration", fail_record)
    destination = tmp_path / "output"
    if failure_stage == "receipt":
        destination.write_text("existing file")
    result = publication.publish_results(
        Publisher(), SimpleNamespace(id="task"), output_dir=destination, ground_truth="gt.csv"
    )
    assert result is None
    assert any("FiftyOne visualization publication failed" in warning for warning in warnings_log)
    operation = {
        "receipt": "write_receipt",
        "run_configuration": "record_configuration",
        "missing_receipt": "publish",
    }[failure_stage]
    assert any(f"operation={operation}" in warning for warning in warnings_log)


@pytest.mark.parametrize("stage", ["preflight", "publish"])
def test_visualization_failure_allows_clearml_task_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    import clearml

    from clearml_yolo.clearml_session import ClearMLConfig, invocation, upload_artifact
    from clearml_yolo.publishing.models import FiftyOneConfig
    from clearml_yolo.tasks.publication import prepare_publisher, publish_results
    from test_clearml_session import FakeTask

    task = FakeTask()
    monkeypatch.setattr(clearml.Task, "init", lambda **_kwargs: task)
    monkeypatch.setattr(clearml.Task, "get_task", lambda **_kwargs: task)
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    predictions = tmp_path / "predictions.csv"
    predictions.write_text("image_name\nexample.jpg\n")

    class FailingPublisher:
        enabled = True

        def preflight(self) -> None:
            if stage == "preflight":
                raise RuntimeError("visualization unavailable")

        def publish(self, _request: object) -> None:
            raise ValueError("invalid visualization box")

    with invocation(ClearMLConfig(), "predict") as owner:
        publisher = prepare_publisher(owner, FiftyOneConfig(), factory=lambda _: FailingPublisher())
        upload_artifact(owner, "predictions", predictions)
        assert (
            publish_results(publisher, owner, output_dir=tmp_path, ground_truth="gt.csv") is None
        )
    assert task.failed == []
    assert task.completed == [{"ignore_errors": False, "force": True}]
    assert task.closed is True
    assert [upload["name"] for upload in task.uploads] == ["predictions"]
    assert predictions.is_file()


def test_publication_request_failure_identifies_input_without_calling_backend(
    tmp_path: Path, warnings_log: list[str]
) -> None:
    from clearml_yolo.tasks.publication import publish_results

    class Publisher:
        enabled = True

        def publish(self, _request: object) -> None:
            pytest.fail("invalid request must not reach backend")

        def preflight(self) -> None:
            pass

    assert (
        publish_results(
            Publisher(),
            SimpleNamespace(id=""),
            output_dir=tmp_path,
            ground_truth="gt.csv",
        )
        is None
    )
    assert any(
        "operation=prepare_request" in entry
        and "ground_truth=gt.csv" in entry
        and "ValidationError" in entry
        for entry in warnings_log
    )
