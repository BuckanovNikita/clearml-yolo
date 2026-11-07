# Feature 036 evidence preservation

Archive date: 2026-10-20. Private source baseline:
`9cea557d73b428ad014129f2ac5fe47a4cd2642a` (`v0.7.0`).

## Scope and architecture

Preserve the contents of 37 received files: 285,964 bytes of dated observations,
acceptance records and reproduction helpers. The 18 raw logs are stored as
lossless `.log.gz` files; their decompressed contents reproduce the original
137,393 bytes. All other received files retain their original bytes. No
credentials, weights, model artifacts or runtime caches are included. The task
adds this archive note, the [no-impact architecture record](architecture.json),
`log-archives.json`, and `SHA256SUMS`; it changes no active skill instructions or
helper behavior. The unrelated queue-finalization evidence is excluded.

The Python and shell files document the historical run. They are not wired into
the current skill, tests, import contracts or runtime. Their effectful execution
is outside this archival task. A future explicitly requested reproduction must
read the current stand guidance, use a new evidence-output directory, and treat
the saved machine paths and SDK details as historical observations. Preserve
these original files rather than overwriting them with a new run.

The [acceptance report](acceptance.md) owns the run interpretation. Successful
plain and diagnostic miss/hit/scientific-miss sequences and direct single-GPU
execution are retained alongside the failed first attempts. The unexplained
initial output-model reopening failure is not reclassified as repaired. This
archive does not establish full PipelineController deployment, compiled GPU
execution, physical multi-GPU behavior or model accuracy.

## Validation and review

The archive author inspected all reproduction source and scanned every received
text file for private-key material, credential assignments, URL userinfo, known
API-token forms and bearer values. A recursive JSON check also looked for
credential-bearing keys. Neither scan found candidates; no redaction was needed.
These checks and source inspection are evidence of review, not a guarantee about
all possible secret encodings.

Read-only validation passed:

- All nine received JSON documents parse; all three Python files parse with
  `ast.parse`; `bash -n run.sh` passes. The Python files were not imported or run.
- Markdown parsing, closed fences and local targets pass.
- Successful cache sequences agree with acceptance-checks, terminal statuses,
  task identities, dataset identity reuse, the scientific override and readback.
- All five cleanup records name their exact run tag and report zero remaining
  tagged tasks/projects and removal of the corresponding local workspace.
- The failed initial clone remains a nonzero result, separate from later success.

The initial staged `git diff --check` exited 2 for 300 trailing-whitespace
observations in 12 raw Ultralytics log files. The archival representation was
changed to lossless gzip rather than altering the logs' progress output or table
padding. `log-archives.json` records each original path/SHA-256 and its compressed
path/SHA-256. Round-trip byte comparison and the full staged whitespace check
passed after compression; no hook or configuration was changed. The final
archive has 41 files and 40 checksum entries, including 11 parseable JSON files.
The documented extraction example was executed in a temporary directory and
reproduced all 18 original hashes; that temporary extraction was removed.

The parent inspected `acceptance.md` and the portable live results independently
of this archive author. The dated observations are preserved rather than rerun.
The [architecture record](architecture.json) is validated at planning and
acceptance; its no-impact result is structural validation, not product acceptance.

README release checks from the immediately preceding unchanged source apply:
102 offline tests passed in 17.65s, the module-plan example passed, five maintained
shell helpers passed syntax checks, all 11 existing skill headers parsed, and
15 prior archive checksums passed. Only this dated evidence directory is added;
those executable paths and `cleanup-code` source/installed bytes are unchanged.

## Integrity and delivery

`SHA256SUMS` includes every file in this directory except itself, with paths
relative to the directory. Validate it without running any workload:

```bash
sha256sum -c SHA256SUMS
```

The log paths in [acceptance.md](acceptance.md) name the original uncompressed
files. Their stored representations append `.gz`. To extract and verify the
original log bytes in a separate, previously nonexistent directory, run this
from the archive directory after replacing the destination:

```python
import gzip
import hashlib
import json
from pathlib import Path

destination = Path("/path/to/new-extraction-directory")
destination.mkdir()
for entry in json.loads(Path("log-archives.json").read_text())["logs"]:
    content = gzip.decompress(Path(entry["compressed_path"]).read_bytes())
    assert hashlib.sha256(content).hexdigest() == entry["original_sha256"]
    output = destination / entry["original_path"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
```

Before committing, validate this record, the final archive formats, all manifest
entries, the exact staged path set and whitespace. Publish a documentation commit
and the next Git-only patch tag (`v0.7.1`) after review, then verify the remote
commit and peeled tag. No installation or GitHub Release is part of this archival
delivery. The actual commit/tag is returned in the task handoff; this note
precedes its own commit.
