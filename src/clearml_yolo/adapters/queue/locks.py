"""Small host-global lock records retain quarantine after process death."""

import fcntl
import hashlib
import os
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from clearml_yolo.adapters.queue.coordination import (
    host_directory,
    host_transaction,
    shared_descriptor,
)
from clearml_yolo.adapters.queue.storage import atomic_write
from clearml_yolo.core.queue import (
    QUEUE_COMPATIBILITY,
    GPUHold,
    GuardianClaim,
    WorkerIdentity,
    claim_token,
)

_MAX_RECORD_BYTES = 65536
_CONTROL_COMPATIBILITY = "shared-cy-queue-gpu-controls-v1"
_CONTROL_FENCE = "gpu-controls.claim.json"


def _read_claim(path: Path) -> GuardianClaim | None:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(status.st_mode) or status.st_size > _MAX_RECORD_BYTES:
        raise RuntimeError("Host-local GPU claim is not a bounded regular record")
    try:
        claim = GuardianClaim.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise RuntimeError("Host-local GPU claim protocol is corrupt; admission refused") from error
    if status.st_uid != claim.owner_uid or stat.S_IMODE(status.st_mode) & 0o022:
        raise PermissionError("GPU claim ownership does not match its filesystem record")
    return claim


def _write_claim(path: Path, claim: GuardianClaim | None) -> None:
    if claim is None:
        path.unlink(missing_ok=True)
        return
    payload = claim.model_dump_json()
    if len(payload.encode()) > _MAX_RECORD_BYTES:
        raise RuntimeError("Host-local GPU lock record exceeds its bounded size")
    atomic_write(path, payload)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class GPULease:
    """Only explicit verified cleanup clears records; close releases OS handles alone."""

    def __init__(
        self,
        pool: "LocalGPULocks",
        descriptors: dict[str, int],
        claim: GuardianClaim,
        *,
        recovering: bool = False,
    ) -> None:
        self.pool = pool
        self.descriptors = descriptors
        self.claim = claim
        self.recovering = recovering

    def persist(self, claim: GuardianClaim) -> None:
        if claim.job_id != self.claim.job_id or claim.devices != self.claim.devices:
            raise ValueError("A guardian cannot replace the identity or devices of its lease")
        with self.pool.transaction():
            for uuid in self.descriptors:
                _write_claim(self.pool.claim_path(uuid), claim)
        self.claim = claim

    def release_verified(self) -> None:
        with self.pool.transaction():
            self.release_in_transaction()

    def release_in_transaction(self) -> None:
        """Clear pinned metadata after verification/audit in the caller's transaction."""
        for uuid in self.descriptors:
            current = _read_claim(self.pool.claim_path(uuid))
            if current is None and self.recovering:
                continue
            if current is None or claim_token(current) != claim_token(self.claim):
                raise RuntimeError("GPU cleanup record changed before verified release")
        for uuid in self.descriptors:
            _write_claim(self.pool.claim_path(uuid), None)
        _sync_directory(self.pool.root)

    def close(self) -> None:
        descriptors, self.descriptors = self.descriptors, {}
        for descriptor in descriptors.values():
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


class LocalGPULocks:
    """Global per-host UUID coordination across queue roots and mount aliases."""

    def __init__(self, identity: WorkerIdentity, root: Path | None = None) -> None:
        self.identity = identity
        self.local_root = root
        self.root = host_directory(identity.host_id, root)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with host_transaction(
            self.identity.host_id, name="gpu-transaction.lock", root=self.local_root
        ):
            yield

    def ensure_control_fence(self) -> None:
        """Fence legacy admission, preserving normal completion of existing leases."""
        with self.transaction():
            self._ensure_control_fence()

    def _ensure_control_fence(self) -> None:
        path = self.root / _CONTROL_FENCE
        existing = _read_claim(path)
        if existing is not None:
            self._validate_fence(existing)
            return
        _write_claim(
            path,
            GuardianClaim(
                compatibility=_CONTROL_COMPATIBILITY,
                job_id="gpu-controls-fence",
                owner_uid=os.geteuid(),
                host_id=self.identity.host_id,
                boot_id="persistent-control",
                queue_root="",
                devices=(),
                marker="gpu-controls-fence",
                guardian_pid=0,
                guardian_born=0,
            ),
        )

    def _validate_fence(self, claim: GuardianClaim) -> None:
        expected = GuardianClaim(
            compatibility=_CONTROL_COMPATIBILITY,
            job_id="gpu-controls-fence",
            owner_uid=claim.owner_uid,
            host_id=self.identity.host_id,
            boot_id="persistent-control",
            queue_root="",
            devices=(),
            marker="gpu-controls-fence",
            guardian_pid=0,
            guardian_born=0,
        )
        if claim != expected:
            raise RuntimeError("GPU control admission fence is corrupt")

    def hold_path(self, uuid: str, uid: int) -> Path:
        return self.root / f"hold-{hashlib.sha256(uuid.encode()).hexdigest()}-{uid}.json"

    def _holds(self) -> tuple[GPUHold, ...]:
        holds: list[GPUHold] = []
        for path in self.root.glob("hold-*.json"):
            status = path.lstat()
            if not stat.S_ISREG(status.st_mode) or status.st_size > _MAX_RECORD_BYTES:
                raise RuntimeError("GPU hold is not a bounded regular record")
            try:
                hold = GPUHold.model_validate_json(path.read_bytes())
            except ValidationError as error:
                raise RuntimeError("GPU hold protocol is corrupt; admission refused") from error
            if (
                status.st_uid != hold.owner_uid
                or stat.S_IMODE(status.st_mode) & 0o022
                or hold.host_id != self.identity.host_id
                or path != self.hold_path(hold.uuid, hold.owner_uid)
            ):
                raise PermissionError("GPU hold ownership or identity differs from its record")
            holds.append(hold)
        return tuple(holds)

    def holds(self) -> tuple[GPUHold, ...]:
        with self.transaction():
            return self._holds()

    def disable(self, uuid: str, reason: str) -> GPUHold:
        if self.identity.owner_uid != os.geteuid():
            raise PermissionError("Only the effective owner may disable GPUs")
        hold = GPUHold(
            uuid=uuid,
            owner_uid=os.geteuid(),
            host_id=self.identity.host_id,
            reason=reason.strip(),
            created_at=time.time(),
        )
        with self.transaction():
            self._ensure_control_fence()
            self._holds()
            atomic_write(self.hold_path(uuid, hold.owner_uid), hold.model_dump_json())
        return hold

    def enable(self, uuid: str) -> None:
        if self.identity.owner_uid != os.geteuid():
            raise PermissionError("GPU control identity must match the effective owner")
        with self.transaction():
            self._ensure_control_fence()
            self._holds()
            self.hold_path(uuid, os.geteuid()).unlink(missing_ok=True)
            _sync_directory(self.root)

    def _path(self, uuid: str) -> Path:
        return self.root / f"gpu-{hashlib.sha256(uuid.encode()).hexdigest()}.lock"

    def claim_path(self, uuid: str) -> Path:
        return self._path(uuid).with_suffix(".claim.json")

    def acquire(self, claim: GuardianClaim) -> GPULease | None:
        return self._acquire(claim, recovery=False)

    def acquire_recovery(self, claim: GuardianClaim) -> GPULease:
        if claim.owner_uid != os.geteuid():
            raise PermissionError("Only the effective owner may recover GPU capacity")
        lease = self._acquire(claim, recovery=True)
        if lease is None:
            raise RuntimeError("GPU guardian still owns its locks; recovery refused")
        return lease

    def transaction_claims(self) -> tuple[GuardianClaim, ...]:
        """Inspect current claims while the caller holds the host transaction."""
        return self._claims(check_compatibility=False)

    def transaction_recovery(self, claim: GuardianClaim) -> GPULease:
        """Pin a complete recovery allocation within an existing transaction."""
        if claim.owner_uid != os.geteuid():
            raise PermissionError("Only the effective owner may release GPU capacity")
        acquired: dict[str, int] = {}
        try:
            self._take_recovery_locks(claim, acquired)
        except BaseException:
            for descriptor in acquired.values():
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
            raise
        return GPULease(self, acquired, claim, recovering=True)

    def _take_recovery_locks(self, claim: GuardianClaim, acquired: dict[str, int]) -> None:
        for uuid in sorted(claim.devices):
            if not self._take_lock(uuid, claim, True, acquired):
                raise RuntimeError("GPU guardian still owns its locks; release refused")

    def _acquire(self, claim: GuardianClaim, *, recovery: bool) -> GPULease | None:
        acquired: dict[str, int] = {}
        succeeded = False
        with self.transaction():
            if not recovery and any(hold.uuid in claim.devices for hold in self._holds()):
                return None
            if not recovery and any(
                set(existing.devices).intersection(claim.devices) for existing in self._claims()
            ):
                return None
            try:
                for uuid in sorted(claim.devices):
                    if not self._take_lock(uuid, claim, recovery, acquired):
                        return None
                if not recovery:
                    for uuid in acquired:
                        _write_claim(self.claim_path(uuid), claim)
                succeeded = True
                return GPULease(self, acquired, claim, recovering=recovery)
            finally:
                if not succeeded:
                    for descriptor in acquired.values():
                        fcntl.flock(descriptor, fcntl.LOCK_UN)
                        os.close(descriptor)

    def _take_lock(
        self, uuid: str, claim: GuardianClaim, recovery: bool, acquired: dict[str, int]
    ) -> bool:
        descriptor = shared_descriptor(self._path(uuid))
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            return False
        acquired[uuid] = descriptor
        current = _read_claim(self.claim_path(uuid))
        if current is None:
            return True
        if not recovery:
            return False
        if claim_token(current) != claim_token(claim):
            raise RuntimeError("GPU recovery claim does not own the quarantined device")
        return True

    def _claims(self, *, check_compatibility: bool = True) -> tuple[GuardianClaim, ...]:
        claims: list[GuardianClaim] = []
        for path in self.root.glob("gpu-*.claim.json"):
            claim = _read_claim(path)
            if claim is not None:
                if path.name == _CONTROL_FENCE:
                    self._validate_fence(claim)
                    continue
                if claim.host_id != self.identity.host_id:
                    raise RuntimeError("GPU claim belongs to a different host namespace")
                if check_compatibility and claim.compatibility != QUEUE_COMPATIBILITY:
                    raise RuntimeError("An incompatible active guardian stops GPU admission")
                claims.append(claim)
        return tuple(claims)

    def reserved(self) -> set[str]:
        reserved: set[str] = set()
        with self.transaction():
            reserved.update(hold.uuid for hold in self._holds())
            for claim in self._claims():
                reserved.update(claim.devices)
        return reserved

    def claim_for(self, job_id: str) -> GuardianClaim | None:
        with self.transaction():
            claims = [
                claim for claim in self._claims(check_compatibility=False) if claim.job_id == job_id
            ]
        if not claims:
            return None
        first = claims[0]
        stable = first.model_dump(exclude={"child_pid", "child_born", "identities"})
        if any(
            claim.model_dump(exclude={"child_pid", "child_born", "identities"}) != stable
            for claim in claims
        ):
            raise RuntimeError("GPU recovery evidence has inconsistent ownership")
        latest = max(claims, key=lambda claim: (claim.child_pid is not None, len(claim.identities)))
        identities: dict[int, int] = {}
        for claim in claims:
            for pid, born in claim.identities:
                identities[pid] = max(identities.get(pid, 0), born)
        return latest.model_copy(update={"identities": tuple(sorted(identities.items()))})
