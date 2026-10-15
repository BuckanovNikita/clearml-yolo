# Compatibility decisions

- Use the exact requested `>=3.12.13,<3.14` range. The floor is a packaging policy,
  not evidence that every distribution of these versions includes pidfd APIs.
- Keep `.python-version`, Ruff and mypy on 3.12 so development continues to check
  the oldest supported minor. Do not migrate code to 3.13-only syntax or APIs.
- Re-resolve the existing lock without upgrade flags. Review changed package
  versions and preserve approved editable sources/revisions.
- Existing Linux process-supervision checks distinguish missing interpreter APIs
  from failed kernel operations and remain authoritative.
- The current upstream fix for standalone builds is documented in
  [Astral's change](https://github.com/astral-sh/python-build-standalone/pull/1163).
  Actual interpreter probes, rather than version strings alone, establish capability.
- Reuse existing architecture and behavior tests; no new test merely restates the
  configuration. Built distribution metadata and real isolated installs verify it.
