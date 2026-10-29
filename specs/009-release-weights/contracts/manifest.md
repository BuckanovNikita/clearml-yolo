# Weight bundle manifest v1

The UTF-8 JSON object has `schema_version: 1`, `repository: "BuckanovNikita/clearml-yolo"`, `release_tag: "weights-2026-10-29"`, `archives` and `assets` arrays. Reject unknown fields and duplicate identifiers. Never accept arbitrary repository or traversal-bearing paths from remote content; package data is the source of this manifest.

An archive has `name` (single .tar filename), `size` (positive bytes below 2 GiB), `sha256` (64 lowercase hex).

An asset has `identity` (AssetSpec.identity), `backend`, `preset`, `filename` (original requested filename), `source_url` (original canonical URL), `source_revision` (string or null), `kind` (`weights` or `deim-source`), `archive` (archive name), `member` (safe relative POSIX path), `size`, `sha256`, and `hub` (null or metadata below). `member` stores the actual native representation. Assets sharing identical request identity are deduplicated. Retain original request source, not the mirror URL, as provenance.

Hub metadata has `repository`, `revision` (requested ref), `commit` (40 hex), `filename` (actual safetensors/bin representation), `etag` (40 or 64 hex), and `config` with `member`, `size`, `sha256`, `etag`. The config belongs to the SAME snapshot commit. Archive contents store ordinary files; restoration creates native blob/snapshot/ref entries from real metadata. Never invent commit IDs from weight hashes.

Archive members use `assets/<identity>/<actual filename>` and `assets/<identity>/config.json`. Notices can be added under `LICENSES/`. Each asset and its Hub config remain in the same independent tar. No symlinks, hardlinks, special files, unsafe paths or duplicate member names are permitted. Validate archive hash/size before parsing; member hash/size before publication. Tar headers use deterministic metadata. Each archive stays below 2 GiB including padding and licence files.

The maintainer script accepts `--output`, `--tag`, `--max-archive-bytes` (default 1900000000), and optional `--notices` directory. It produces `manifest.json`, `SHA256SUMS`, and all tar files, failing on any unresolved catalogue entry. No network upload or automatic manifest replacement occurs. The pinned runtime resource is `adapters/assets/weights-manifest.json`.
