# Automatic task grouping

Each effective Hydra MULTIRUN launch adds one shared `multirun-<UUID4 hex>` ClearML
tag, including a one-job multirun. Direct stage commands and `cy` share this behavior.
`cy-queue submit -- -m ...` and saved MULTIRUN submissions freeze the group tag in
every job snapshot; execution retains it. Every new launch/submission gets a new tag.
User tags, including per-job overrides, are preserved. Ordinary RUN adds no tag.
No option or environment variable is required. Existing user-supplied tags that begin
with `multirun-` are preserved as ordinary tags rather than removed or reused.

This groups locally created direct and queue tasks. Remote ClearML replay attaches
an existing task and retains its task metadata; it does not define a new grouping policy.
