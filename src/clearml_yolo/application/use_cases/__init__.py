"""Application workflows with explicit ports and project-owned contracts.

Every workflow takes a keyword-only ``deps: WorkflowDependencies`` and performs SDK,
filesystem, rendering and process effects only through its typed ports; it never constructs
adapters or finds them through a cache, locator or global setter. Importing this package or
a use-case module initializes no storage, constructs no services and leaves the caller's
logging configuration unchanged. Workflows compose inward only: ``pipeline``; ``val`` and
``report``; ``metrics``; the single-stage commands; ``publication``. A direct call does not
record the full resolved input snapshot; an embedding caller supplies it to the invocation
owner as ``resolved_config``. Command names, Hydra overrides, CSV formats and published
artifacts are the external contract, not these Python signatures.
"""
