"""Fixed-corpus native versus engine verification with explicit scientific evidence."""

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from clearml_yolo.adapters.export.metadata import sha256
from clearml_yolo.adapters.export.preprocessing import postprocess, preprocess
from clearml_yolo.adapters.export.quality import evaluate_detections, evaluator_identity
from clearml_yolo.adapters.export.runtime import TensorRTRunner
from clearml_yolo.adapters.storage.dataset_records import validate_ground_truth
from clearml_yolo.core.datasets import ImageRecord
from clearml_yolo.core.export import ExportMetadata
from clearml_yolo.core.export_quality import match_detections, quality_gate
from clearml_yolo.core.export_requests import ExportRequest, ExportResult, gpu_device_index

_PREPROCESS_ATOL = 0.0001
_PREPROCESS_RTOL = 0.00001
_MATCH_IOU = 0.99


def verification_cases() -> tuple[tuple[int, int, int], ...]:
    """Batch/H/W endpoints, interior dimensions and repeated profile transitions."""
    endpoints = tuple(
        (batch, height, width)
        for height, width in ((608, 960), (736, 960), (128, 1536), (256, 1920))
        for batch in (1, 2, 3, 4)
    )
    interiors = tuple(
        (batch, height, width) for batch in (1, 2, 4) for height, width in ((672, 960), (192, 1728))
    )
    return endpoints + interiors


def _corpus(request: ExportRequest, destination: Path) -> tuple[list[ImageRecord], Path]:
    if request.ground_truth is None:
        raise ValueError("Verification requires labeled ground truth")
    records = validate_ground_truth(
        request.ground_truth, required_splits=(request.split,), require_training=False
    )
    if records.errors:
        raise ValueError(
            "Export quality corpus contains invalid boxes; correct them before verification"
        )
    images = [image for image in records.images if image.split == request.split]
    if not images or not any(image.boxes for image in images):
        raise ValueError("Export quality corpus requires images with labeled foreground objects")
    manifest = destination / "corpus.json"
    manifest.write_text(
        json.dumps(
            {
                "ground_truth_sha256": records.input_sha256,
                "split": request.split,
                "images": [
                    image.model_dump(mode="json") | {"sha256": sha256(image.path)}
                    for image in images
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return images, manifest


def _read_image(image: ImageRecord) -> NDArray[np.uint8]:
    with Image.open(image.path) as source:
        pixels = np.asarray(source.convert("RGB"), dtype=np.uint8)
    if pixels.shape[:2] != (image.height, image.width):
        raise ValueError(f"Quality corpus image dimensions changed: {image.path}")
    return pixels


def _verify_corpus(request: ExportRequest, manifest: Path) -> None:
    """Fail if any source bytes changed while the fixed-corpus run was in progress."""
    recorded = json.loads(manifest.read_text(encoding="utf-8"))
    if (
        request.ground_truth is None
        or sha256(request.ground_truth) != recorded["ground_truth_sha256"]
    ):
        raise ValueError("Quality ground truth changed during verification")
    for image in recorded["images"]:
        if sha256(Path(image["path"])) != image["sha256"]:
            raise ValueError(f"Quality corpus image changed during verification: {image['path']}")


def _native_rows(predictions: Any) -> list[NDArray[np.float32]]:
    # The native detector returns opaque SDK dictionaries of tensors. Convert at
    # this adapter boundary; all downstream comparison uses the portable Nx6 form.
    return [
        np.concatenate(
            (
                detection["boxes"].detach().cpu().numpy(),
                detection["scores"].detach().cpu().numpy()[:, None],
                detection["labels"].detach().cpu().numpy()[:, None] - 1,
            ),
            axis=1,
        ).astype(np.float32)
        for detection in predictions
    ]


def _case(
    images: list[ImageRecord],
    metadata: ExportMetadata,
    runner: TensorRTRunner,
    detector: Any,
    device: Any,
    case: tuple[int, int, int],
) -> dict[str, Any]:
    import torch

    batch, height, width = case
    canvas = (height, width)
    detector.transform.canvas_size = canvas
    native: dict[str, NDArray[np.float32]] = {}
    exported: dict[str, NDArray[np.float32]] = {}
    agreements = []
    compositions: list[list[str]] = []
    native_seconds, engine_seconds = [], []
    preprocessing_maximum = 0.0
    preprocessing_passed = True
    peak_buffers = 0
    torch.cuda.reset_peak_memory_stats(device)
    with torch.inference_mode():
        for offset in range(0, len(images), batch):
            selected = images[offset : offset + batch]
            # Pad only the final batch with repeated real images. Record the
            # composition and exclude padding from the scientific denominator.
            padded = [selected[index % len(selected)] for index in range(batch)]
            compositions.append([str(image.path) for image in padded])
            pixels = [_read_image(image) for image in padded]
            normalized, sizes = preprocess(
                pixels,
                canvas,
                mean=metadata.descriptor.preprocessing.mean,
                std=metadata.descriptor.preprocessing.std,
            )
            tensors = [
                torch.from_numpy(value.copy()).permute(2, 0, 1).float().div(255).to(device)
                for value in pixels
            ]
            transformed, _ = detector.transform(tensors)
            actual_input = transformed.tensors.cpu().numpy()
            if transformed.image_sizes != [tuple(size) for size in sizes.tolist()]:
                raise ValueError("Native and standalone valid resized dimensions disagree")
            preprocessing_maximum = max(
                preprocessing_maximum, float(np.abs(actual_input - normalized).max())
            )
            preprocessing_passed &= bool(
                np.allclose(
                    actual_input,
                    normalized,
                    atol=_PREPROCESS_ATOL,
                    rtol=_PREPROCESS_RTOL,
                )
            )
            torch.cuda.synchronize(device)
            started = perf_counter()
            reference = _native_rows(detector(tensors))
            torch.cuda.synchronize(device)
            native_seconds.append(perf_counter() - started)
            started = perf_counter()
            detections, counts = runner(normalized, sizes)
            engine_seconds.append(perf_counter() - started)
            peak_buffers = max(peak_buffers, runner.last_buffer_bytes)
            actual = postprocess(
                detections,
                counts,
                [(image.height, image.width) for image in padded],
                sizes,
                class_count=len(metadata.descriptor.class_names),
            )
            if len(reference) != len(padded):
                raise ValueError("Native detector did not return one result per input image")
            for image, expected, observed in zip(
                selected,
                reference[: len(selected)],
                actual[: len(selected)],
                strict=True,
            ):
                key = str(image.path)
                native[key], exported[key] = expected, observed
                agreements.append(
                    match_detections(expected, observed, min_iou=_MATCH_IOU).model_dump()
                )
    native_metrics = evaluate_detections(images, metadata.descriptor.class_names, native)
    exported_metrics = evaluate_detections(images, metadata.descriptor.class_names, exported)
    native_count = sum(len(values) for values in native.values())
    return {
        "batch": batch,
        "canvas_hw": canvas,
        "batch_composition": compositions,
        "padding_policy": "repeat final batch images; count original membership once",
        "reference_detection_count": native_count,
        "exported_detection_count": sum(len(values) for values in exported.values()),
        "preprocessing_max_absolute_error": preprocessing_maximum,
        "preprocessing_passed": preprocessing_passed,
        "native_metrics": native_metrics.model_dump(),
        "exported_metrics": exported_metrics.model_dump(),
        "mAP_loss": native_metrics.mAP - exported_metrics.mAP,
        "quality_passed": quality_gate(
            native_metrics,
            exported_metrics,
            precision=metadata.precision,
            reference_detection_count=native_count,
        ),
        "detection_agreement": agreements,
        "native_batch_seconds": native_seconds,
        "engine_batch_seconds": engine_seconds,
        "latency_scope": "cold/warm calls retained; native input transfer excluded, "
        "engine input transfer and both output readbacks included",
        "native_torch_peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
        "engine_context_bytes": runner.engine_context_bytes,
        "engine_max_io_buffer_bytes": peak_buffers,
        "memory_scope": "Torch allocator peak and TensorRT context/I-O allocations; "
        "not total process GPU peak",
    }


def _rejections(runner: TensorRTRunner) -> dict[str, bool]:
    rejected: dict[str, bool] = {}
    for name, shape in (
        ("batch_five", (5, 3, 128, 1536)),
        ("cross_profile_canvas", (1, 3, 736, 1920)),
        ("below_minimum", (1, 3, 96, 1536)),
    ):
        sizes = np.array([shape[2:]] * shape[0], dtype=np.int64)
        try:
            runner(np.zeros(shape, dtype=np.float32), sizes)
        except ValueError:
            rejected[name] = True
        else:
            rejected[name] = False
    return rejected


def verify_engine(
    request: ExportRequest, metadata: ExportMetadata, destination: Path
) -> ExportResult:
    """Run one serialized engine and its FP32 native reference on identical image bytes."""
    import torch

    from clearml_yolo.adapters.fasterrcnn.model import build_model, checkpoint_state

    if request.engine is None or request.weights is None:
        raise ValueError("Verification requires an engine and native checkpoint")
    images, manifest = _corpus(request, destination)
    evaluator = evaluator_identity()
    index = gpu_device_index(request.device)
    device = torch.device(f"cuda:{index}")
    runner = TensorRTRunner(request.engine, metadata, device=index)
    policy = metadata.inference
    detector = build_model(
        metadata.descriptor.preset,
        len(metadata.descriptor.class_names),
        pretrained=False,
        image_size=(608, 960),
        score_thresh=policy.conf,
        nms_thresh=policy.iou,
        detections_per_img=policy.max_det,
    )
    detector.load_state_dict(checkpoint_state(request.weights), strict=True)
    detector.to(device).float().eval()
    old_matmul, old_cudnn = torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32
    report_path = destination / "verification.json"
    evidence: dict[str, Any] = {
        "operation": "verify",
        "metadata": metadata.model_dump(mode="json"),
        "corpus_sha256": sha256(manifest),
        "evaluator": {
            "name": "pycocotools COCOeval bbox",
            **evaluator,
            "maxDets": [1, 10, 100],
        },
        "runtime": {"torch": torch.__version__, "cuda": torch.version.cuda},
        "native_precision": "FP32; TF32 disabled",
        "detection_match": {"iou": _MATCH_IOU, "class_aware": True, "one_to_one": True},
        "preprocessing_tolerance": {
            "atol": _PREPROCESS_ATOL,
            "rtol": _PREPROCESS_RTOL,
            "rationale": "float32 bilinear operation ordering; "
            "absolute tolerance is less than 0.006 decoded intensity levels",
        },
        "quality_max_mAP_loss": 0.001 if metadata.precision == "fp32" else 0.005,
        "raw_pre_nms_outputs": {
            "status": "not_exposed",
            "reason": "proposals, ROI and NMS are embedded in the compiled graph; "
            "final detections do not establish raw parity",
        },
        "cuda_11_8_target": {
            "status": "not_executed",
            "reason": "local verification alone does not establish deployment target compatibility",
        },
        "cases": [],
        "passed": False,
    }
    try:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        for case in verification_cases():
            evidence["cases"].append(_case(images, metadata, runner, detector, device, case))
            report_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        evidence["rejections"] = _rejections(runner)
        _verify_corpus(request, manifest)
        evidence["corpus_unchanged"] = True
        evidence["passed"] = all(
            value["quality_passed"] and value["preprocessing_passed"] for value in evidence["cases"]
        ) and all(evidence["rejections"].values())
    except Exception as error:
        evidence["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        torch.backends.cuda.matmul.allow_tf32 = old_matmul
        torch.backends.cudnn.allow_tf32 = old_cudnn
        report_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return ExportResult(
        artifacts={"export_verification": report_path, "export_corpus": manifest},
        evidence=evidence,
        passed=evidence["passed"],
    )
