# ADR-0401 · Build the approved scientific dependencies into a worktree-local wheelhouse

CY contributors need the approved sources of digital-metrics and report-generator. The local bootstrap builds source distributions from the supplied checkouts, places them under the ignored wheelhouse and configures uv to find them. The lock records package identity and the wheelhouse registry. It cannot establish which source revisions were used to build its contents.

A contributor checks both revisions before building. Existing uv settings are preserved and checked for the required lookup path. This permits a portable tracked package definition while keeping the external repositories independently owned. [Dependency reference](../DOCS.md#installation-and-dependencies) · [Bootstrap](../Taskfile.ops.yml) · [Local configuration validation](../scripts/check_local_uv.py) · [Lock](../uv.lock)
