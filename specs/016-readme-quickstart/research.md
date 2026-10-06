# Research decisions

- Decision: center the main cy invocation and use table-only manual comparison.
  Rationale: explicit user choice. Rejected: a second full CLI/Python tutorial.
- Decision: show clone/submodule setup with local source overrides and locked sync.
  Rationale: committed metadata omits overrides while uv.lock pins editable submodules.
  Rejected: inventing a package registry location or advancing dependency revisions.
- Decision: link maintained contracts for internal details. Rationale: preserve a short
  onboarding path without changing contract authority. Rejected: keeping the long
  release and GPU queue explanations in the quickstart.
