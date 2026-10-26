# Bug Fix: latest CY and queue compatibility

- **Slug**: queue-version-compatibility (from assessment context)
- **Fixed**: 2026-10-26
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

The separate queue package is now 0.1.1 with CY `>=0.38,<0.41`. Its tests verify
current source and installed requirements/versions and load the installed entrypoint
outside the checkout. A normal joint editable install refreshed CY to 0.40.0 and
queue to 0.1.1 without changing other dependencies; `uv pip check` passes.

Both repositories now document public source acquisition, joint installation and a
standing paired release acceptance check. CY runtime/dependency metadata is unchanged.
The pre-existing local uv source overrides are preserved through the commit procedure.
The portable usage skill was inspected; its compatible source-install and unchanged
queue CLI examples need no update.

The new regression failed twice before the metadata correction. Afterwards the
complete ordinary queue suite passed (501 tests; 7 opt-in GPU cases deselected),
along with configured Ruff, format, strict mypy and import contracts. Current
pipeline/train augmentation composition and all three CLI help checks passed.
Queue evidence lives in `docs/bugs/queue-version-compatibility/verification.md` in
its repository. No deviation from assessment or runtime code change was needed.

Public remote creation/push and final CY hook checks follow independent review and
acceptance; no package registry, GitHub Release objects or release assets are involved.

## Hook-generated scope addition

The first normal commit attempt regenerated three changelog lines for the already
committed verification-delivery documentation. The parent inspected and staged this
generated update; no manual changelog edit or source change was needed.
