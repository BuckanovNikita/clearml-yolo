# Local live environment

The lifecycle uses the `docker-desktop` context and records ownership in
`tests/integration/.run-tag`. Services are reached through loopback port-forwards, with no
ClearML web UI or ClearML Agent. Use the recorded endpoints; user-owned host services are
unrelated. The local cy-queue workflow is available for selected queue checks.

Check pcboard capacity before GPU work. Choose native devices from the current generated
configuration. Publishers sharing a FiftyOne database must share its lock directory; the
lifecycle exports a default and honors an explicit `FIFTYONE_DATABASE_DIR` override. Keep
database ownership separate from local output ownership.

For a failed run, preserve logs and inspect the lifecycle error and the owned record
first. An unavailable endpoint may mean a stopped forward or an expired environment.
Recover only owned resources through lifecycle commands, and never replace a live record
to get past an ownership refusal. A vanished environment prevents fresh remote readback
even when local logs remain. Leave credentials and host configuration untouched.
