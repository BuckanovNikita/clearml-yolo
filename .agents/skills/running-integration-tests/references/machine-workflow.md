# Local live environment

The lifecycle uses the `docker-desktop` context and records ownership in
`tests/integration/.run-tag`. Services use loopback port-forwards, with no ClearML web
UI or ClearML Agent. Use the recorded endpoints; user-owned host services are unrelated.
The local cy-queue workflow remains available for selected queue checks.

Check pcboard capacity before GPU work. Choose native devices from current generated
configuration. Publishers sharing a FiftyOne database must share its lock directory;
lifecycle exports the default and honors an explicit override. Keep database ownership
separate from local output ownership.

For a failed run, preserve logs and inspect the lifecycle error and owned record first.
An unavailable endpoint may reflect a stopped forward or expired environment. Recover
only owned resources through lifecycle commands. Never replace a live record to bypass
ownership refusal. A vanished environment prevents fresh remote readback even when
local logs remain. Preserve credentials and host configuration.

For historical audits only, use
`.agents/skills/clearml-yolo-environment/references/evidence-archive.md`.
