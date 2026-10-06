# cy-dedup command contract

`cy-dedup [DIRECTORY] [--dry-run]` defaults to `$CY_HOME/.cache`, or the launch working
directory's `.cache`. An explicit directory overrides that default. Help and dry-run
create no application directories and initialize no tracking or model runtime.
Missing/non-directory roots are errors; an empty directory succeeds with zero counts.

The recursive scan excludes symlinks and selects regular files with extensions
`.bmp`, `.dng`, `.jpeg`, `.jpg`, `.mpo`, `.png`, `.tif`, `.tiff`, `.webp`, `.pfm`, `.heic`
(case insensitive). Matching uses the entire exact case-sensitive filename. Equal
contents under different filenames are not candidates. Files are not decoded as images.

Compare size, streamed SHA-256 and bytes; choose sources deterministically. Same-device
identical files may share blocks using Linux FICLONE. Preserve destination permissions,
ownership, atime/mtime and xattrs via temporary sibling and atomic replacement. A new
inode means ctime/birth time may change. Reads may update access times.

Existing hardlinks, cross-device pairs and unsupported reflinks/platforms are reported
skips; no hardlink or plain-copy fallback. Detected file changes prevent replacement.
Unexpected filesystem errors produce diagnostics and nonzero exit; processing may have
already completed other independent replacements. Temporary files are cleaned on errors
and interruptions. Use an idle cache: no coordination with arbitrary writers is provided.

Summary fields: scanned, duplicates, reflinked, skipped, failures. Dry-run identifies
candidates without probing support or modifying files. Successful ioctl operations count
as reflinked; this does not measure physical reclaimed bytes or detect already-shared extents.
Exit 0: success including reported skips. Exit 1: operational failures. Exit 2: usage or
invalid root. Interruptions retain normal nonzero interruption behavior.
