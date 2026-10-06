"""Backend-neutral publication lifecycle shared by eligible command owners."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from loguru import logger
from pydantic import JsonValue

from clearml_yolo import artifact_names
from clearml_yolo.clearml_session import record_run_configuration
from clearml_yolo.publishing import NoOpPublisher, Publisher, create_publisher
from clearml_yolo.publishing.models import (
    FiftyOneConfig,
    PublicationReceipt,
    PublicationRequest,
)

PublisherFactory = Callable[[FiftyOneConfig | None], Publisher]


def prepare_publisher(
    task: Any,
    config: FiftyOneConfig | None,
    *,
    factory: PublisherFactory = create_publisher,
) -> Publisher:
    """Preflight optional visualization; disable it with a warning if unavailable."""
    selected = config if task is not None else FiftyOneConfig(enabled=False)
    try:
        publisher = factory(selected)
        publisher.preflight()
    except Exception as error:  # noqa: BLE001 - optional backends have varied exception types
        # Backend error messages can contain credential-bearing database URIs.
        logger.warning(
            "FiftyOne visualization setup failed; continuing without visualization: {}",
            type(error).__name__,
        )
        return NoOpPublisher()
    return publisher


def publish_results(
    publisher: Publisher,
    task: Any,
    *,
    output_dir: str | Path,
    ground_truth: str | Path,
    source_ground_truth: str | Path | None = None,
    predictions: str | Path | None = None,
    prediction_splits: list[str] | None = None,
    prediction_image_name: Literal["name", "stem", "path"] = "name",
    evaluations: dict[str, Path] | None = None,
    metadata: dict[str, JsonValue] | None = None,
) -> PublicationReceipt | None:
    """Publish optional visualization without failing the computation on backend errors."""
    if not publisher.enabled:
        return None
    try:
        request = PublicationRequest(
            task_id=str(task.id),
            ground_truth=Path(ground_truth),
            source_ground_truth=(
                Path(source_ground_truth) if source_ground_truth is not None else None
            ),
            predictions=Path(predictions) if predictions is not None else None,
            prediction_splits=prediction_splits,
            prediction_image_name=prediction_image_name,
            evaluations=evaluations or {},
            metadata=metadata or {},
        )
        receipt = publisher.publish(request)
        if receipt is None:
            logger.warning(
                "FiftyOne visualization publication failed; continuing task: "
                "backend returned no receipt"
            )
            return None
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        receipt_path = destination / artifact_names.FIFTYONE_PUBLICATION_FILE
        receipt_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
        record_run_configuration(
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
    except Exception as error:  # noqa: BLE001 - visualization failures must not fail computation
        logger.warning(
            "FiftyOne visualization publication failed; continuing task: {}",
            type(error).__name__,
        )
        return None
    return receipt
