# Quickstart: own test environment

After implementation (not available on this commit):

```bash
uv run --locked task --exit-code infra-check   # read-only: cluster, context, permission
uv run --locked task --exit-code integration   # creates, uses and deletes cy-it-<id>

L=(uv run --locked python -m tests.integration.lifecycle)
"${L[@]}" up                     # manual environment; record in tests/integration/.run-tag
eval "$("${L[@]}" env)"          # CLEARML_* and FIFTYONE_DATABASE_URI for manual tools
uv run --locked pytest tests/integration  # this shell exports INTEGRATION_RUN_TAG: the session adopts the environment and leaves it
"${L[@]}" stop                   # delete the namespace; proven absent

kubectl --context docker-desktop get ns -l app.kubernetes.io/part-of=clearml-yolo-tests
```

Without the `eval` line (or after the recorded namespace was swept) a live pytest session
creates and deletes an environment of its own; with a live recorded environment and no
matching export it refuses and names `stop` (spec FR-014).

Validation of the feature: [tasks.md](tasks.md), phase "Acceptance".
