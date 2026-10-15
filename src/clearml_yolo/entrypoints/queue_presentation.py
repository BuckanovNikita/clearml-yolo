"""Explicit public queue views, independent of storage and GPU discovery."""

import re
from collections.abc import Mapping

from pydantic import JsonValue

from clearml_yolo.core.gpu_identity import identity_label, redact_gpu_ids
from clearml_yolo.core.queue import (
    GPUControlStatus,
    GPUFreeResult,
    GPUHold,
    PublicJob,
    QueueView,
    ResourceRequest,
)
from clearml_yolo.core.redaction import redact_text

_CLAIM_TOKEN = re.compile(r"\b[0-9a-f]{64}\b")


class QueuePresentation:
    """Render local physical indexes and stable short labels for other devices.

    Callers supply identity metadata; presentation never reads GPU memory or queue
    records. Remote host indexes cannot be inferred from the local inventory.
    """

    def __init__(
        self,
        physical_indexes: Mapping[str, int] | None = None,
        *,
        host_id: str | None = None,
    ) -> None:
        self._labels = {uuid: str(index) for uuid, index in (physical_indexes or {}).items()}
        self._host_id = host_id

    def device(self, uuid: str, host_id: str | None = None) -> str:
        if self._host_id is None or host_id is None or host_id == self._host_id:
            return self._labels.get(uuid, identity_label(uuid))
        return identity_label(uuid)

    def devices(self, uuids: tuple[str, ...], host_id: str | None = None) -> tuple[str, ...]:
        return tuple(self.device(uuid, host_id) for uuid in uuids)

    def text(self, value: str, host_id: str | None = None) -> str:
        labels = (
            self._labels
            if self._host_id is None or host_id is None or host_id == self._host_id
            else {}
        )
        return _CLAIM_TOKEN.sub("<redacted>", redact_gpu_ids(redact_text(value), labels))

    def request(self, request: ResourceRequest, host_id: str | None = None) -> str:
        return ",".join(self.devices(request.devices or (), host_id)) or str(request.count)

    def job(self, job: PublicJob) -> dict[str, JsonValue]:
        """Only documented public fields cross the output boundary."""
        return {
            "protocol": job.protocol,
            "id": self.text(job.id, job.host_id),
            "owner_uid": job.owner_uid,
            "host_id": self.text(job.host_id),
            "boot_id": self.text(job.boot_id),
            "command": self.text(job.command, job.host_id),
            "label": self.text(job.label, job.host_id),
            "request": {
                "gpus": job.request.gpus,
                "devices": (
                    list(self.devices(job.request.devices, job.host_id))
                    if job.request.devices is not None
                    else None
                ),
            },
            "submitted_at": job.submitted_at,
            "submission_sequence": job.submission_sequence,
            "updated_at": job.updated_at,
            "state": job.state,
            "revision": job.revision,
            "devices": list(self.devices(job.devices, job.host_id)),
            "error": self.text(job.error, job.host_id) if job.error else job.error,
            "waiting_reason": (
                self.text(job.waiting_reason, job.host_id) if job.waiting_reason else None
            ),
            "progress": (
                self.text(job.progress, job.host_id)
                if isinstance(job.progress, str)
                else job.progress
            ),
            "clearml_url": self.text(job.clearml_url, job.host_id) if job.clearml_url else None,
        }

    def view(self, view: QueueView) -> dict[str, JsonValue]:
        return {
            "protocol": view.protocol,
            "host_id": self.text(view.host_id),
            "revision": view.revision,
            "jobs": [self.job(job) for job in view.jobs],
        }

    def hold(self, hold: GPUHold) -> dict[str, JsonValue]:
        return {
            "gpu": self.device(hold.uuid, hold.host_id),
            "owner_uid": hold.owner_uid,
            "host_id": self.text(hold.host_id),
            "reason": self.text(hold.reason, hold.host_id),
            "created_at": hold.created_at,
        }

    def gpu(self, card: GPUControlStatus) -> dict[str, JsonValue]:
        claim = card.claim
        return {
            "gpu": self.device(card.uuid),
            "physical_index": card.physical_index,
            "holds": [self.hold(hold) for hold in card.holds],
            "claim": (
                {
                    "job_id": self.text(claim.job_id, claim.host_id),
                    "owner_uid": claim.owner_uid,
                    "devices": list(self.devices(claim.devices, claim.host_id)),
                }
                if claim is not None
                else None
            ),
        }

    def freed(self, result: GPUFreeResult) -> dict[str, JsonValue]:
        return {
            "gpu": self.device(result.uuid),
            "actor_uid": result.actor_uid,
            "generation": result.generation,
            "created_at": result.created_at,
        }
