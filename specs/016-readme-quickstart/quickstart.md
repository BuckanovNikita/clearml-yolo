# Documentation validation

From the repository root, inspect each README Bash block with `bash -n`. For execution
examples, append `--cfg job --resolve` and use the existing environment without syncing
dependencies. Generate editable YAML in a task-owned temporary directory to validate
the configuration example. Do not execute training, tracking or publication.

Parse Markdown and check local link targets and anchors, including inbound README
anchors. Parse the Mermaid diagram with an available Mermaid parser. Review the tables
against current configs and pipeline code. Run `git diff --check` and inspect the full
diff, preserving the pre-existing pyproject.toml change.

An independent reviewer must accept factual accuracy and the approved quickstart scope.
Record actual commands and limitations in dated verification evidence; installation
inspection does not establish a clean-machine installation or live ClearML execution.
