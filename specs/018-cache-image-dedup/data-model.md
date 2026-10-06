# Internal data model

No persistent schema or cache migration is introduced. Image candidates carry their
path and stat snapshot for identity/change detection. Matching uses basename, size,
device and streamed content fingerprints with final byte verification.

DedupResult carries scanned, duplicates, reflinked, skipped and failures integer counts
plus issues (diagnostic strings). CLI formats these as a summary and diagnostics;
failures determines the operational exit status. Dry-run duplicates are candidates,
not a claim of filesystem support or recoverable physical bytes.
