# Dependency inspection — 2026-10-24

`uv lock` completed after transient metadata connection timeouts (including a network retry). Existing package versions are unchanged. Root project metadata changed, and markdown-it-py gained the optional linkify dependency selected by the new mutation UI. Added mutmut 3.8.0 and its transitive dependencies; safetensors remains 0.8.0 and is now direct. Parsed digital-metrics and report-generator lock entries are exactly unchanged. No external source tree was modified.

The bounded mutation configuration uses three pure-policy files, source imports and existing offline test helpers/fixtures. Installed environment synchronization uses `uv sync --frozen --dev --inexact` to preserve the separately installed queue package.
