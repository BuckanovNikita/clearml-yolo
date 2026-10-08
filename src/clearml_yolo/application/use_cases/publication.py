"""Backend-neutral publication lifecycle shared by eligible command owners."""

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import JsonValue

from clearml_yolo.application.ports import Publisher, TaskHandle, WorkflowDependencies
from clearml_yolo.core import artifact_names
from clearml_yolo.core.publication import FiftyOneConfig, PublicationReceipt, PublicationRequest

PublisherFactory = Callable[[FiftyOneConfig | None], Publisher]


def prepare_publisher(
    task: TaskHandle | None,
    config: FiftyOneConfig | None,
    *,
    factory: PublisherFactory | None = None,
    deps: WorkflowDependencies,
) -> Publisher:
    """Preflight optional visualization; disable it with a warning if unavailable."""
    factory = factory if factory is not None else deps.publisher_factory
    selected = config if task is not None else FiftyOneConfig(enabled=False)
    operation = "factory"
    try:
        publisher = factory(selected)
        operation = "preflight"
        publisher.preflight()
    except Exception as error:  # noqa: BLE001 - optional backends must not fail computation
        deps.resources.log_exception(
            "FiftyOne visualization setup failed; continuing without visualization",
            error,
            context={"operation": operation},
        )
        return deps.disabled_publisher
    return publisher


def publish_results(
    publisher: Publisher,
    task: TaskHandle | None,
    *,
    output_dir: str | Path,
    ground_truth: str | Path,
    source_ground_truth: str | Path | None = None,
    predictions: str | Path | None = None,
    prediction_splits: list[str] | None = None,
    prediction_image_name: Literal["name", "stem", "path"] = "name",
    evaluations: dict[str, Path] | None = None,
    metadata: dict[str, JsonValue] | None = None,
    deps: WorkflowDependencies,
) -> PublicationReceipt | None:
    """Publish optional visualization without failing the computation on backend errors."""
    if not publisher.enabled:
        return None
    operation = "prepare_request"
    context: dict[str, object] = {"ground_truth": ground_truth, "output_dir": output_dir}
    try:
        if task is None:
            raise ValueError("Enabled publication requires an owning task")  # noqa: TRY301
        context["task_id"] = str(task.id)
        request = PublicationRequest(
            task_id=str(task.id),
            ground_truth=Path(ground_truth),
            source_ground_truth=Path(source_ground_truth)
            if source_ground_truth is not None
            else None,
            predictions=Path(predictions) if predictions is not None else None,
            prediction_splits=prediction_splits,
            prediction_image_name=prediction_image_name,
            evaluations=evaluations or {},
            metadata=metadata or {},
        )
        operation = "publish"
        receipt = publisher.publish(request)
        if receipt is None:
            deps.resources.log_exception(
                "FiftyOne visualization publication failed; continuing task",
                RuntimeError("backend returned no receipt"),
                context={**context, "operation": operation},
            )
            return None
        operation = "write_receipt"
        destination = Path(output_dir)
        receipt_path = destination / artifact_names.FIFTYONE_PUBLICATION_FILE
        context["path"] = receipt_path
        deps.storage.mkdir(destination, parents=True, exist_ok=True)
        deps.storage.write_text(receipt_path, receipt.model_dump_json(indent=2), encoding="utf-8")
        operation = "record_configuration"
        deps.tracking.record_run_configuration(
            task,
            {
                "fiftyone_result": {
                    "dataset_name": receipt.dataset_name,
                    "run_key": receipt.run_key,
                    "dataset_reused": receipt.dataset_reused,
                    "sample_count": receipt.sample_count,
                    "fields": receipt.fields,
                    "evaluation_keys": receipt.evaluation_keys,
                }
            },
        )
    except Exception as error:  # noqa: BLE001 - optional backends must not fail computation
        deps.resources.log_exception(
            "FiftyOne visualization publication failed; continuing task",
            error,
            context={**context, "operation": operation},
        )
        return None
    return receipt
