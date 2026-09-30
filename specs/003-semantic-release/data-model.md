# Data Model: Local Release Transaction

- **Candidate**: source SHA and semantic version, derived from reachable tagged history.
- **Attempt**: JSON record in the worktree Git directory with source SHA and next version.
  It records ownership before any tracked write and persists until successful tagging.
  After preparation it also records the generated changelog SHA-256; missing or changed
  checksums block tag recovery.
- **Lock**: exclusive directory in the common Git directory, shared by linked worktrees;
  contains owner PID and worktree path for manual diagnosis, never auto-stolen.
- **Release commit**: direct child of the recorded source; exact generated subject;
  only pyproject.toml, uv.lock and CHANGELOG.md change; parsed metadata differs only in
  project version. Changelog content matches the recorded preparation checksum.
- **Tag**: annotated vX.Y.Z reference pointing at the checked release commit.

Transitions: eligible → locked → prepared → committed → tagged → complete. Failures retain
attempt metadata and local files; retries may finish an already checked release commit
(after re-running checks) or restart from an unchanged clean source. Unrelated HEAD or
metadata changes are rejected. Tags are immutable.
