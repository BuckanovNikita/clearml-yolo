"""Small native files exercise maintainer packaging without model SDK loads."""

import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

import pytest
from scripts import package_weights

from clearml_yolo.core.assets import AssetSpec, HubAsset, ResolvedAsset


def _spec(name: str, *, backend: str = "ultralytics") -> AssetSpec:
    return AssetSpec(
        backend=backend,
        preset=name,
        filename=f"{name}.pt",
        canonical_url=f"https://example.test/{name}.pt",
        override="model.weights",
    )


def _checkpoint(path: Path, payload: bytes = b"native tensor bytes") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("checkpoint/data.pkl", payload)


def _record(spec: AssetSpec, path: Path, *, revision: str | None = None) -> ResolvedAsset:
    return ResolvedAsset(
        canonical_url=spec.canonical_url,
        path=path,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        override=spec.override,
        revision=revision,
    )


def test_deterministic_complete_deduplicated_and_noncommercial(tmp_path: Path) -> None:
    specs = (_spec("a"), _spec("b"), _spec("deim", backend="deimv2"))
    records: dict[str, ResolvedAsset] = {}
    for spec in specs:
        path = tmp_path / spec.filename
        _checkpoint(path)
        records[spec.identity] = _record(spec, path)
    notices = tmp_path / "notices"
    notices.mkdir()
    (notices / "LICENSE.txt").write_text("upstream terms", encoding="utf-8")
    output = tmp_path / "first"
    first = package_weights.package_catalogue(
        (*specs, specs[0].model_copy(update={"backend": "torchvision"})),
        output=output,
        tag="weights-test",
        notices=notices,
        resolve=lambda spec: records[spec.identity],
    )
    second_output = tmp_path / "second"
    second = package_weights.package_catalogue(
        tuple(reversed((*specs, specs[0].model_copy(update={"backend": "torchvision"})))),
        output=second_output,
        tag="weights-test",
        notices=notices,
        resolve=lambda spec: records[spec.identity],
    )
    assert first == second
    assert len(first.assets) == 3
    assert len(first.archives) == 2
    assert next(a for a in first.assets if a.backend == "deimv2").archive.startswith(
        "deim-noncommercial"
    )
    for path in output.iterdir():
        assert path.read_bytes() == (second_output / path.name).read_bytes()
    for bundle in first.archives:
        with tarfile.open(output / bundle.name) as archive:
            assert "LICENSES/LICENSE.txt" in archive.getnames()
            assert all(m.isfile() and m.mtime == 0 and m.uid == 0 for m in archive.getmembers())


def test_tar_padding_controls_partitioning(tmp_path: Path) -> None:
    specs = tuple(_spec(str(i)) for i in range(3))
    records: dict[str, ResolvedAsset] = {}
    for spec in specs:
        path = tmp_path / spec.filename
        _checkpoint(path, b"x" * 5000)
        records[spec.identity] = _record(spec, path)
    manifest = package_weights.package_catalogue(
        specs,
        output=tmp_path / "out",
        tag="weights-test",
        max_archive_bytes=10240,
        resolve=lambda spec: records[spec.identity],
    )
    assert len(manifest.archives) == 3
    assert all(a.size == 10240 for a in manifest.archives)


@pytest.mark.parametrize("limit", [0, -1, 2**31, 2**31 + 1, 10239])
def test_invalid_or_impossible_limit_never_publishes_manifest(tmp_path: Path, limit: int) -> None:
    spec = _spec("a")
    path = tmp_path / spec.filename
    _checkpoint(path)
    with pytest.raises(ValueError, match="cap"):
        package_weights.package_catalogue(
            [spec],
            output=tmp_path / "out",
            tag="weights-test",
            max_archive_bytes=limit,
            resolve=lambda request: _record(request, path),
        )
    assert not (tmp_path / "out" / "manifest.json").exists()


def test_one_download_failure_prevents_success_output(tmp_path: Path) -> None:
    first, second = _spec("a"), _spec("b")
    path = tmp_path / first.filename
    _checkpoint(path)

    def resolve(spec: AssetSpec) -> ResolvedAsset:
        if spec.identity == second.identity:
            raise RuntimeError("download unavailable")
        return _record(spec, path)

    with pytest.raises(RuntimeError, match="download unavailable"):
        package_weights.package_catalogue(
            [first, second], output=tmp_path / "out", tag="weights-test", resolve=resolve
        )
    assert not list((tmp_path / "out").iterdir())


def test_revalidation_rejects_corruption_and_resolved_tree(tmp_path: Path) -> None:
    spec = _spec("a")
    path = tmp_path / spec.filename
    path.write_bytes(b"not a checkpoint")
    with pytest.raises(ValueError, match="supported native checkpoint"):
        package_weights.package_catalogue(
            [spec],
            output=tmp_path / "corrupt",
            tag="weights-test",
            resolve=lambda request: _record(request, path),
        )
    with pytest.raises(ValueError, match="original native file"):
        package_weights.package_catalogue(
            [spec.model_copy(update={"kind": "deim-source"})],
            output=tmp_path / "tree",
            tag="weights-test",
            resolve=lambda request: _record(request, path).model_copy(
                update={"content_kind": "source-tree"}
            ),
        )


def test_hub_keeps_real_commit_etags_and_same_snapshot_config(tmp_path: Path) -> None:
    commit = "a" * 40
    cache = tmp_path / "hub"
    repo = cache / "models--org--model"
    snapshot = repo / "snapshots" / commit
    snapshot.mkdir(parents=True)
    blobs = repo / "blobs"
    blobs.mkdir()
    source = tmp_path / "native.bin"
    _checkpoint(source)
    weight_etag = hashlib.sha256(source.read_bytes()).hexdigest()
    source.rename(blobs / weight_etag)
    (snapshot / "pytorch_model.bin").symlink_to(blobs / weight_etag)
    config_data = json.dumps({"architecture": "test"}).encode()
    config_etag = hashlib.sha1(
        f"blob {len(config_data)}\0".encode() + config_data, usedforsecurity=False
    ).hexdigest()
    (blobs / config_etag).write_bytes(config_data)
    (snapshot / "config.json").symlink_to(blobs / config_etag)
    spec = _spec("hub").model_copy(
        update={
            "filename": "pytorch_model.bin",
            "hub": HubAsset(repository="org/model", cache_dir=cache),
        }
    )
    output = tmp_path / "out"
    manifest = package_weights.package_catalogue(
        [spec],
        output=output,
        tag="weights-test",
        resolve=lambda request: _record(request, snapshot / "pytorch_model.bin", revision=commit),
    )
    asset = manifest.assets[0]
    assert asset.hub is not None
    assert asset.hub.commit == commit
    assert asset.hub.etag == weight_etag
    assert asset.hub.config.etag == config_etag
    with tarfile.open(output / asset.archive) as archive:
        assert asset.member in archive.getnames()
        assert asset.hub.config.member in archive.getnames()
    assert str(tmp_path) not in (output / "manifest.json").read_text()
    (snapshot / "config.json").unlink()
    (snapshot / "config.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="real blob ETag"):
        package_weights.package_catalogue(
            [spec],
            output=tmp_path / "missing-metadata",
            tag="weights-test",
            resolve=lambda request: _record(
                request, snapshot / "pytorch_model.bin", revision=commit
            ),
        )


def test_notice_links_rejected(tmp_path: Path) -> None:
    spec = _spec("a")
    path = tmp_path / spec.filename
    _checkpoint(path)
    notices = tmp_path / "notices"
    notices.mkdir()
    (notices / "secret").symlink_to(path)
    with pytest.raises(ValueError, match="symlinks"):
        package_weights.package_catalogue(
            [spec],
            output=tmp_path / "out",
            tag="weights-test",
            notices=notices,
            resolve=lambda request: _record(request, path),
        )


def test_deim_packages_verified_pinned_tar_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    from clearml_yolo.adapters.assets import archive as source_archive

    payload = b"# verified source\n"
    monkeypatch.setattr(
        source_archive,
        "source_manifest",
        lambda: {"module.py": hashlib.sha256(payload).hexdigest()},
    )
    path = tmp_path / "source.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("DEIM-pinned/module.py")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    spec = _spec("source", backend="deimv2").model_copy(
        update={"kind": "deim-source", "filename": path.name, "revision": "a" * 40}
    )
    output = tmp_path / "out"
    manifest = package_weights.package_catalogue(
        [spec],
        output=output,
        tag="weights-test",
        resolve=lambda request: _record(request, path, revision=request.revision),
    )
    asset = manifest.assets[0]
    assert asset.source_revision == "a" * 40
    assert asset.archive.startswith("deim-noncommercial")
    with tarfile.open(output / asset.archive) as archive:
        stream = archive.extractfile(asset.member)
        assert stream is not None
        with stream:
            assert stream.read() == path.read_bytes()


def test_discovery_failure_stops_cli_before_packaging(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    from clearml_yolo.core.assets import PreparationFailure

    monkeypatch.setattr(
        sys, "argv", ["package_weights", "--output", "unused", "--tag", "weights-x"]
    )
    monkeypatch.setattr(
        package_weights,
        "_discover",
        lambda: (
            "fingerprint",
            (),
            (),
            (PreparationFailure(selection="unknown", message="failed"),),
        ),
    )
    with pytest.raises(RuntimeError, match="Incomplete catalogue discovery: unknown"):
        package_weights.main()


def test_concurrent_input_change_prevents_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = _spec("a")
    path = tmp_path / spec.filename
    _checkpoint(path)
    original = tarfile.TarFile.addfile

    def replacing_addfile(
        archive: tarfile.TarFile,
        info: tarfile.TarInfo,
        fileobj: object = None,
    ) -> None:
        # Keep its length and valid Torch structure while replacing the bytes
        # after initial validation, immediately before tar's stream read.
        content = path.read_bytes()
        path.write_bytes(content.replace(b"native tensor bytes", b"other  tensor bytes"))
        original(archive, info, fileobj)  # type: ignore[arg-type]

    monkeypatch.setattr(tarfile.TarFile, "addfile", replacing_addfile)
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="changed during packaging"):
        package_weights.package_catalogue(
            [spec],
            output=output,
            tag="weights-test",
            resolve=lambda request: _record(request, path),
        )
    assert not list(output.iterdir())
