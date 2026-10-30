"""Prepare the maintained catalogue in native caches with coordinated attempt receipts."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from filelock import FileLock
from loguru import logger
from pydantic import ValidationError

from clearml_yolo.adapters.assets.bundles import (
    BundlePreparationError,
    load_manifest,
    seed_bundle_asset,
)
from clearml_yolo.adapters.assets.resolver import (
    AssetResolutionError,
    asset_destination,
    resolve_asset,
)
from clearml_yolo.adapters.assets.sources import existing_source, extract_resolved_source
from clearml_yolo.adapters.deim.assets import backbone_asset as deim_backbone_asset
from clearml_yolo.adapters.deim.assets import source_asset as deim_source_asset
from clearml_yolo.adapters.observability.diagnostics import exception_summary, redact_text
from clearml_yolo.adapters.rfdetr.assets import pretrained_asset as rfdetr_asset
from clearml_yolo.adapters.storage.filesystem import cy_home, write_path
from clearml_yolo.adapters.torchvision.assets import pretrained_asset as torchvision_asset
from clearml_yolo.adapters.yolo.assets import pretrained_asset as yolo_asset
from clearml_yolo.core.assets import (
    AssetSpec,
    PreparationFailure,
    PreparationResult,
    ResolvedAsset,
)
from clearml_yolo.core.batch_estimation import ModelVariant, model_catalogue


def _failure(selection: str, operation: str, error: Exception) -> PreparationFailure:
    # Opaque SDK errors can contain bare credentials, beyond recognizable URL/auth
    # patterns. Report their type only; the selected model retains normal handling.
    if isinstance(error, (AssetResolutionError, BundlePreparationError)):
        # Only the resolver-owned outer report is public. Even its explicit or
        # implicit causes may retain opaque transport messages.
        message = redact_text(str(error)).strip()
        name = type(error).__name__
        details = f"{name}: {message}" if message else name
    else:
        details = exception_summary(error, include_message=False)
    return PreparationFailure(selection=selection, message=f"{operation}: {details}")


def _request(variant: ModelVariant) -> AssetSpec:
    if variant.backend == "ultralytics":
        return yolo_asset(variant.architecture)
    if variant.backend == "deimv2":
        return deim_backbone_asset(variant.preset)
    if variant.backend == "rfdetr":
        return rfdetr_asset(variant.preset)
    return torchvision_asset(variant.preset, backend=variant.backend)


def _location(spec: AssetSpec) -> Path:
    return asset_destination(spec).resolve()


def _discover() -> tuple[
    str, tuple[Path, ...], tuple[tuple[str, AssetSpec], ...], tuple[PreparationFailure, ...]
]:
    variants = tuple(
        variant
        for variant in model_catalogue()
        if not (
            (variant.backend == "deimv2" and variant.preset in {"l", "x"})
            or variant.preset == "dinov3_small"
        )
    )
    requests: list[tuple[str, AssetSpec]] = []
    failures: list[PreparationFailure] = []
    identities: list[dict[str, object]] = []
    locations: set[Path] = set()
    unique: set[tuple[str, str]] = set()

    def discover(selection: str, spec: AssetSpec) -> None:
        location = _location(spec)
        hub = (
            (spec.hub.repository, spec.hub.revision, spec.hub.filename)
            if spec.hub is not None
            else None
        )
        identity = json.dumps((spec.identity, spec.kind, hub))
        identities.append({"selection": selection, "asset": identity, "location": str(location)})
        locations.add(location)
        key = (identity, str(location))
        if key not in unique:
            unique.add(key)
            requests.append((selection, spec))

    for variant in variants:
        try:
            discover(variant.selection, _request(variant))
        except Exception as error:  # noqa: BLE001 - per-SDK discovery failure boundary
            failures.append(_failure(variant.selection, "Asset discovery failed", error))
            identities.append({"selection": variant.selection, "discovery": "unavailable"})
    if any(variant.backend == "deimv2" for variant in variants):
        try:
            discover("deimv2/source", deim_source_asset())
        except Exception as error:  # noqa: BLE001 - source discovery is independent of weights
            failures.append(_failure("deimv2/source", "Asset discovery failed", error))
            identities.append({"selection": "deimv2/source", "discovery": "unavailable"})
    try:
        manifest = load_manifest()
        manifest_identity = manifest.identity if manifest is not None else "unavailable"
    except (OSError, ValueError):
        manifest_identity = "invalid"
    identities.append(
        {"selection": "weight-bundle", "manifest": manifest_identity, "policy": "release-only-v1"}
    )
    payload = json.dumps(
        sorted(identities, key=lambda item: str(item["selection"])),
        sort_keys=True,
        separators=(",", ":"),
    )
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()
    return fingerprint, tuple(sorted(locations)), tuple(requests), tuple(failures)


def _read_receipt(path: Path, fingerprint: str) -> PreparationResult | None:
    try:
        result = PreparationResult.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (ValidationError, UnicodeError):
        return None
    if result.fingerprint != fingerprint:
        return None
    return result.model_copy(update={"skipped": True})


def _write_receipt(path: Path, result: PreparationResult) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(result.model_dump_json())
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _resolve(spec: AssetSpec) -> ResolvedAsset:
    if spec.kind != "deim-source":
        return resolve_asset(spec, local_only=True)
    existing = existing_source(spec)
    if existing is not None:
        return existing
    extract_resolved_source(resolve_asset(spec, local_only=True))
    prepared = existing_source(spec)
    if prepared is None:
        raise RuntimeError("Extracted DEIM source is unavailable")
    return prepared


def _prepare_asset(spec: AssetSpec) -> ResolvedAsset:
    try:
        return _resolve(spec)
    except AssetResolutionError:
        # A cache miss may be repaired only by the pinned project release. The
        # standalone resolver retains upstream behavior; bulk preparation never uses it.
        pass
    failure = seed_bundle_asset(spec)
    if failure is not None:
        raise BundlePreparationError(failure)
    return _resolve(spec)


def _prepare(*, automatic: bool) -> PreparationResult:
    fingerprint, locations, requests, discovery_failures = _discover()
    assets: list[ResolvedAsset] = []
    failures = list(discovery_failures)
    try:
        directory = write_path(cy_home() / ".cache" / "clearml-yolo" / "preparation")
        directory.mkdir(parents=True, exist_ok=True)
        receipt = write_path(directory / f"{fingerprint}.json")
        lock = write_path(directory / f"{fingerprint}.lock")
        with FileLock(str(lock), timeout=86400):
            if automatic and (completed := _read_receipt(receipt, fingerprint)) is not None:
                return completed
            # A retry owns completion from here. Even when an older completed
            # attempt exists, interruption must leave this pass unfinished.
            receipt.unlink(missing_ok=True)
            for selection, spec in requests:
                try:
                    record = _prepare_asset(spec)
                    assets.append(record)
                    logger.info("Prepared model asset {} at {}", selection, record.path)
                except Exception as error:  # noqa: BLE001 - continue independent model assets
                    failures.append(_failure(selection, "Asset preparation failed", error))
            result = PreparationResult(
                fingerprint=fingerprint,
                locations=locations,
                assets=tuple(assets),
                failures=tuple(failures),
            )
            _write_receipt(receipt, result)
            return result
    except Exception as error:  # noqa: BLE001 - receipt storage must not stop actual execution
        failures.append(_failure("catalogue", "Preparation state unavailable", error))
        return PreparationResult(
            fingerprint=fingerprint,
            locations=locations,
            assets=tuple(assets),
            failures=tuple(failures),
        )


def prepare_catalogue(*, automatic: bool) -> PreparationResult:
    """Prepare eligible native assets; manual calls retry, automatic calls reuse attempts.

    Individual ordinary failures are detached results. Interruptions propagate and
    cannot publish completed receipts. Only this explicitly invoked boundary owns
    discovery, network, native cache publication and durable preparation state.
    """
    try:
        result = _prepare(automatic=automatic)
    except Exception as error:  # noqa: BLE001 - automatic discovery is best effort
        result = PreparationResult(
            fingerprint="unavailable",
            failures=(_failure("catalogue", "Catalogue discovery failed", error),),
        )
    if automatic:
        for failure in result.failures:
            logger.warning("Model preparation {}: {}", failure.selection, failure.message)
    return result
