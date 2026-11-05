# Paired-source verification

Date: 2026-11-05.

CY implementation is based on current origin/master 8be76e4, version 0.45.0. Queue uses
current origin/main 694c12f, version 0.1.8, in an isolated clean checkout. Existing sibling
checkout changes were preserved. Isolated environments resolved ordinary editable source
installations with the approved external dependency copies, without --no-deps.

Both current-version and proposed-version checks passed:

- CY 0.45.0 plus queue 0.1.8: normal installation and pip check passed; source/installed
  metadata matched; 583 queue tests passed, seven opt-in tests deselected.
- Proposed CY 0.45.1 plus queue 0.1.8: normal installation and pip check passed;
  source/installed metadata matched; 583 queue tests passed, seven opt-in tests deselected.
- Proposed implementation source was compared byte-for-byte with the task source. Only
  root package version metadata was changed in the isolated proposal.
- Queue Ruff, formatting, strict mypy and both import contracts passed. CLI help passed.

CY's separate canonical suite, final release-version identity and remote Git refs are
recorded after delivery. These checks do not establish physical GPU scheduling.
