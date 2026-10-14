"""Audited operator GPU controls over host-wide identity, holds and whole leases."""

import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from clearml_yolo.adapters.queue.identity import process_birth
from clearml_yolo.adapters.queue.locks import LocalGPULocks
from clearml_yolo.adapters.queue.storage import NFSQueueStore, _read, atomic_write
from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory
from clearml_yolo.adapters.runtime.process_tree import (
    LinuxProcessTree,
    UnverifiableProcessTreeError,
    defer_interruptions,
)
from clearml_yolo.core.queue import (
    GPUControlStatus,
    GPUHold,
    GPUReleaseAudit,
    GuardianClaim,
    claim_token,
)

# One bounded guardian claim plus the reason and audit envelope.
_MAX_AUDIT_BYTES = 131072
_MAX_REASON_LENGTH = 2048


def _full_uuid(selector: str) -> bool:
    if not selector.startswith("GPU-"):
        return False
    try:
        return str(UUID(selector[4:])) == selector[4:]
    except ValueError:
        return False


def _merge_claims(claims: tuple[GuardianClaim, ...]) -> GuardianClaim:
    first = claims[0]
    if any(claim_token(claim) != claim_token(first) for claim in claims):
        raise RuntimeError("GPU claim has inconsistent whole-allocation ownership")
    latest = max(claims, key=lambda claim: (claim.child_pid is not None, len(claim.identities)))
    children = {
        (claim.child_pid, claim.child_born) for claim in claims if claim.child_pid is not None
    }
    if len(children) > 1:
        raise RuntimeError("GPU claim has conflicting child process evidence")
    identities = dict(latest.identities)
    for claim in claims:
        for pid, born in claim.identities:
            if pid in identities and identities[pid] != born:
                raise RuntimeError("GPU claim has conflicting process birth evidence")
            identities[pid] = born
    return latest.model_copy(update={"identities": tuple(sorted(identities.items()))})


class GPUControls:
    """Physical selectors never rely on CUDA order or healthy memory telemetry."""

    def __init__(
        self,
        pool: LocalGPULocks,
        *,
        physical_uuids: Callable[[], tuple[str, ...]] | None = None,
    ) -> None:
        self.pool = pool
        self.physical_uuids = physical_uuids or GPUInventory().physical_uuids

    def _resolve(self, selector: str) -> str:
        if re.fullmatch(r"[0-9]+", selector):
            physical = self.physical_uuids()
            index = int(selector)
            if index >= len(physical):
                raise ValueError("GPU physical index is outside the NVML inventory")
            return physical[index]
        if _full_uuid(selector):
            # UUID controls must remain usable when a stale card is absent from NVML.
            return selector
        raise ValueError("GPU selector must be a nonnegative physical index or full GPU UUID")

    def list(self) -> tuple[GPUControlStatus, ...]:
        physical = self.physical_uuids()
        with self.pool.transaction():
            claims = self.pool.transaction_claims()
        holds = self.pool.holds()
        uuids = dict.fromkeys(
            (*physical, *(h.uuid for h in holds), *(u for c in claims for u in c.devices))
        )
        result: list[GPUControlStatus] = []
        for uuid in uuids:
            selected = tuple(claim for claim in claims if uuid in claim.devices)
            claim = _merge_claims(selected) if selected else None
            result.append(
                GPUControlStatus(
                    uuid=uuid,
                    physical_index=physical.index(uuid) if uuid in physical else None,
                    holds=tuple(hold for hold in holds if hold.uuid == uuid),
                    claim=claim,
                    claim_token=claim_token(claim) if claim is not None else None,
                )
            )
        return tuple(result)

    def disable(self, selector: str, *, reason: str) -> GPUHold:
        return self.pool.disable(self._resolve(selector), reason)

    def enable(self, selector: str) -> None:
        self.pool.enable(self._resolve(selector))

    def _audit_path(self, token: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", token):
            raise ValueError("Claim token must be the current 64-character token from gpu list")
        return self.pool.root / f"release-{token}.json"

    def _read_audit(self, path: Path, token: str) -> GPUReleaseAudit | None:
        try:
            if path.lstat().st_size > _MAX_AUDIT_BYTES:
                raise RuntimeError("GPU release audit exceeds its bounded record size")
            audit = GPUReleaseAudit.model_validate_json(_read(path, os.geteuid()))
        except FileNotFoundError:
            return None
        if (
            audit.actor_uid != os.geteuid()
            or audit.claim.owner_uid != os.geteuid()
            or audit.token != token
            or claim_token(audit.claim) != token
            or audit.claim.host_id != self.pool.identity.host_id
        ):
            raise RuntimeError("GPU release audit identity is inconsistent")
        return audit

    def _claim(self, uuid: str, token: str, audit: GPUReleaseAudit | None) -> GuardianClaim:
        claims = self.pool.transaction_claims()
        selected = tuple(claim for claim in claims if uuid in claim.devices)
        if selected:
            claim = _merge_claims(selected)
            if claim_token(claim) != token:
                raise RuntimeError("Stale claim token; refresh gpu list before releasing")
            related = tuple(c for c in claims if set(c.devices).intersection(claim.devices))
            return _merge_claims(related)
        if audit is not None and uuid in audit.claim.devices:
            # An interrupted deletion can leave only another device's claim record.
            related = tuple(c for c in claims if set(c.devices).intersection(audit.claim.devices))
            if any(claim_token(claim) != token for claim in related):
                raise RuntimeError("Stale claim token; allocation has changed since release audit")
            return _merge_claims((*related, audit.claim))
        raise ValueError("Selected GPU has no current owned claim matching that token")

    @staticmethod
    def _guardian_absent(claim: GuardianClaim, *, force: bool) -> bool:
        try:
            if process_birth(claim.guardian_pid) == claim.guardian_born:
                raise RuntimeError("Guardian is still alive; cancel or recover after it exits")
        except PermissionError:
            if not force:
                raise
            return False
        return True

    def _verify_cleanup(self, claim: GuardianClaim, *, force: bool) -> bool:
        if claim.boot_id != self.pool.identity.boot_id:
            return True
        guardian_verified = self._guardian_absent(claim, force=force)
        identities = dict(claim.identities)
        if claim.child_pid is not None and claim.child_born is not None:
            identities[claim.child_pid] = claim.child_born
        tree = LinuxProcessTree(
            0 if force else claim.child_pid or 0,
            claim.marker,
            born=claim.child_born or claim.ownership_since,
            identities=identities,
        )
        if not force:
            tree.terminate()
            return True
        return self._verify_force(tree) and guardian_verified

    @staticmethod
    def _verify_force(tree: LinuxProcessTree) -> bool:
        verified = True
        try:
            verified = not tree.running()
        except (UnverifiableProcessTreeError, PermissionError):
            verified = False
        # Denied evidence must never hide positively identified live descendants.
        for pid, born in tree.identities:
            try:
                if process_birth(pid) == born:
                    raise RuntimeError("Confirmed live owned descendant refuses force release")
            except PermissionError:
                verified = False
        return verified

    @defer_interruptions()
    def release(
        self,
        selector: str,
        *,
        token: str,
        reason: str,
        force: bool = False,
    ) -> GPUReleaseAudit:
        if self.pool.identity.owner_uid != os.geteuid():
            raise PermissionError("GPU control identity must match the effective owner")
        if not reason.strip() or len(reason.strip()) > _MAX_REASON_LENGTH:
            raise ValueError("GPU release requires a nonempty reason of at most 2048 characters")
        uuid = self._resolve(selector)
        path = self._audit_path(token)
        self.pool.ensure_control_fence()
        with self.pool.transaction():
            audit = self._read_audit(path, token)
            claim = self._claim(uuid, token, audit)
            if claim.owner_uid != os.geteuid():
                raise PermissionError("Only the effective owner may release this GPU claim")
        if not Path(claim.queue_root).is_dir():
            raise RuntimeError("Claim queue root is unavailable; release preserves metadata")
        store = NFSQueueStore(Path(claim.queue_root), self.pool.identity)
        # Match existing recovery/completion's NFS -> GPU lock order.
        with store.transaction(), self.pool.transaction():
            audit = self._read_audit(path, token)
            claim = self._claim(uuid, token, audit)
            if claim.owner_uid != os.geteuid():
                raise PermissionError("Only the effective owner may release this GPU claim")
            if audit is not None and audit.finished:
                return audit
            if audit is not None and audit.forced != force:
                raise ValueError("Retry must preserve the release audit's original force mode")
            lease = self.pool.transaction_recovery(claim)
            try:
                verified = self._verify_cleanup(claim, force=force)
                if audit is None:
                    audit = GPUReleaseAudit(
                        token=token,
                        claim=claim,
                        actor_uid=os.geteuid(),
                        reason=reason.strip(),
                        forced=force,
                        cleanup_verified=verified,
                        created_at=time.time(),
                    )
                    atomic_write(path, audit.model_dump_json())
                elif audit.cleanup_verified and not verified:
                    # A retry must not report an earlier verification as current proof.
                    audit = audit.model_copy(update={"cleanup_verified": False})
                    atomic_write(path, audit.model_dump_json())
                # Durable failed status precedes capacity release. Keep snapshots and history.
                store.transaction_update(
                    claim.job_id,
                    "failed",
                    error=(
                        "Manual GPU release: "
                        + (
                            "verified cleanup"
                            if audit.cleanup_verified
                            else "unverified cleanup override"
                        )
                        + "; "
                        + audit.reason
                    ),
                )
                lease.release_in_transaction()
                audit = audit.model_copy(update={"finished": True})
                atomic_write(path, audit.model_dump_json())
                return audit
            finally:
                lease.close()
