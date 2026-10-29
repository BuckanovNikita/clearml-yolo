# Local site contract

`cy-docs [--port PORT] [--no-browser] [--check]` binds to 127.0.0.1; port 0 selects an
available port. Print URL before optionally opening the browser. `--check` validates assets,
coverage, tutorial links and configurations without opening a listener or browser.

GET `/` and packaged assets; GET `/api/catalog` returns catalog JSON. POST `/api/preview`
accepts a PreviewRequest and returns a PreviewResult. Reject nonlocal Host/Origin, oversized
or malformed JSON and unsupported routes. No CORS. Use restrictive local content policy.
Render submitted/user strings as text; download names are fixed safe basenames.

Each preview owns a fresh subprocess, bounded to 15 seconds, at most 100 jobs, 32 documents
and 1 MiB submitted content. Names are relative YAML paths without traversal or symlinks.
Forbidden search paths/plugins are rejected before composition; Hydra launcher/sweeper/target
replacement cannot execute. Environment/custom resolvers remain unresolved. Runtime checks
such as dataset existence, credentials, devices and augmentation-file validity are deferred.
Submitted Hydra runtime blocks/overrides are rejected before composition, including
interpolated aliases; these controls belong in the terminal. Names require `.yaml`.
Temporary input ownership resides in the parent worker manager, including forced exits.

No launch, target instantiation, model import, dataset/asset access or augmentation loading
occurs. Shutdown terminates and reaps owned workers. Ordinary imports/commands never load
documentation assets, so malformed/missing docs cannot break their operation.
