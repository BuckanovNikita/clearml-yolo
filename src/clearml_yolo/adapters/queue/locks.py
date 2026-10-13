"""Small host-global lock records retain quarantine after process death."""

import fcntl
import hashlib
import os
import stat
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
from clearml_yolo.core.queue import QUEUE_COMPATIBILITY, GuardianClaim, WorkerIdentity

_MAX_RECORD_BYTES = 65536


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
            for uuid in self.descriptors:
                current = _read_claim(self.pool.claim_path(uuid))
                if current is None and self.recovering:
                    continue
                if current is None or current.job_id != self.claim.job_id:
                    raise RuntimeError("GPU cleanup record changed before verified release")
            for uuid in self.descriptors:
                _write_claim(self.pool.claim_path(uuid), None)

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

    def _acquire(self, claim: GuardianClaim, *, recovery: bool) -> GPULease | None:
        acquired: dict[str, int] = {}
        succeeded = False
        with self.transaction():
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
        if (current.job_id, current.owner_uid, current.queue_root) != (
            claim.job_id,
            claim.owner_uid,
            claim.queue_root,
        ):
            raise RuntimeError("GPU recovery claim does not own the quarantined device")
        return True

    def _claims(self, *, check_compatibility: bool = True) -> tuple[GuardianClaim, ...]:
        claims: list[GuardianClaim] = []
        for path in self.root.glob("gpu-*.claim.json"):
            claim = _read_claim(path)
            if claim is not None:
                if claim.host_id != self.identity.host_id:
                    raise RuntimeError("GPU claim belongs to a different host namespace")
                if check_compatibility and claim.compatibility != QUEUE_COMPATIBILITY:
                    raise RuntimeError("An incompatible active guardian stops GPU admission")
                claims.append(claim)
        return tuple(claims)

    def reserved(self) -> set[str]:
        reserved: set[str] = set()
        with self.transaction():
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
