# Cache deduplication

`cy-dedup [DIRECTORY] [--dry-run]` is explicit, opt-in maintenance for an idle image
cache. It finds regular image files that share an exact file name and identical bytes and,
on Linux filesystems that support reflinks, replaces later copies with reflinked clones of
the first one. Paths and contents stay the same; the copies share disk blocks until one
of them is written, after which each file changes independently. The command starts no
ClearML task, loads no SDK configuration and creates no application directories.

## Behavior

### Selection

- `DIRECTORY` defaults to `CY_HOME/.cache`; `CY_HOME` defaults to the launch working
  directory. The directory must already exist; it is never created.
- The scan is recursive and does not follow symlinks. A symlink is never a candidate,
  and a symlinked root directory is rejected.
- Only regular files with these suffixes are scanned, compared case-insensitively:
  `.bmp`, `.dng`, `.jpeg`, `.jpg`, `.mpo`, `.png`, `.tif`, `.tiff`, `.webp`, `.pfm`,
  `.heic`. Files are not decoded.
- Two files are duplicates only when their base names match exactly (case-sensitive),
  their sizes match, their streamed SHA-256 digests match and a full byte-by-byte
  comparison matches. Equal digests over different bytes never cause a replacement.
- Files are processed in sorted path order, so the first file of a duplicate group is
  the source for the later ones. A same-device source is preferred over one on another
  device.

### Replacement

For each same-device duplicate the command:

1. creates a temporary sibling named `.cy-dedup-*` in the destination's directory;
2. clones the source into it with the Linux `FICLONE` ioctl and verifies the clone's
   size and bytes against the source;
3. copies the destination's owner, group, mode, exact extended-attribute set, access
   time and modification time onto the temporary file, then flushes it to disk;
4. checks that neither the source nor the destination changed since the scan (device,
   inode, size, modification and change times, mode, owner, group and link count);
5. atomically renames the temporary file over the destination.

The temporary file is removed on every exit path, including errors and interruptions.
The replaced destination keeps its path, bytes, ownership, mode, timestamps and extended
attributes. Its inode, change time and birth time change, and reading files during the
scan may update access times.

### Skips

These candidates are counted as duplicates and as skipped, and the original stays in
place. There is no hardlink or copy fallback.

- The destination already has more than one hard link (`Skipped existing hardlink`).
- Source and destination are on different devices (`Skipped cross-device duplicate`).
- The filesystem or platform does not support `FICLONE` (`Skipped unsupported reflink`).
  On a non-Linux platform the skip happens before any temporary file is created.

### Dry run

`--dry-run` scans, hashes and compares exactly as above but creates, replaces and deletes
nothing. It reports hardlink and cross-device skips, but it does not probe reflink
support, so its `reflinked` count is always zero and its duplicate count is an upper
bound on what a real run can replace.

### Output

Each skip and failure is written as one line to stderr. The summary is one line on
stdout:

```text
scanned=N duplicates=N reflinked=N skipped=N failures=N
```

A dry run prefixes it with `Dry run (candidates only): `. `scanned` counts image files,
`duplicates` counts candidate replacements (including skipped and failed ones), and the
other counts partition those outcomes. Counts describe files; the command does not measure
reclaimed bytes.

With `LOGURU_LEVEL=TRACE` the command emits the `storage.dedup` and `storage.dedup.scan`
operation records and the final `command.return` record described in
[diagnostics](diagnostics.md).

## Configuration

- `DIRECTORY` (optional positional): the cache to scan.
- `--dry-run`: report candidates without creating or replacing files.
- `CY_HOME`: selects the default cache and the workspace that writable selections must
  stay inside.

## Failure behavior

- Exit status 0 means every candidate ended as a replacement or a skip; skips alone do
  not fail the command.
- Exit status 1 means at least one operational failure: an unreadable directory or file,
  a permission error, a failed clone verification, a metadata copy failure, or a file
  that changed during processing (`file changed during deduplication`). The command
  continues with the remaining candidates, so the summary includes every replacement
  made before and after the failure. The affected original is retained.
- Exit status 2 is a usage error or an invalid root: a missing directory, a path that is
  not a directory, a symlinked root, or a writable selection outside `CY_HOME`.
- A selection outside the resolved `CY_HOME` is accepted only with `--dry-run`; without
  it the command fails before scanning and writes nothing.

## Limits

- The cache must be idle. Stat checks detect ordinary writes that happen during the
  run, but the command does not synchronize with other writers and gives no guarantee
  against deliberate filesystem races.
- Space is shared only on Linux filesystems that implement `FICLONE` reflinks. Other
  filesystems and platforms produce skips.
- Only image files are considered, and only identical files with the same base name;
  identical images stored under different names are not deduplicated.
- Only the destination's link count is checked for existing hard links.

## Code and tests

- [entrypoints/dedup.py](../../src/clearml_yolo/entrypoints/dedup.py) — command
  parsing, default directory, summary and exit status.
- [adapters/storage/dedup.py](../../src/clearml_yolo/adapters/storage/dedup.py) —
  scanning, duplicate detection and atomic reflink replacement.
- [tests/test_dedup.py](../../tests/test_dedup.py) — selection, metadata preservation,
  skips, races, interruption and native copy-on-write independence.
- [tests/test_dedup_cli.py](../../tests/test_dedup_cli.py) — default and explicit
  directories, workspace containment, exit status and lightweight startup.
- Native reflink behavior is exercised only where the test filesystem supports
  `FICLONE`; elsewhere those cases establish skip behavior only.
