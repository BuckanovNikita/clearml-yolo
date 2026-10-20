# Data model

No stored data or public configuration changes. The adapter receives the launch
`Path`, observes Git command status/output and emits at most one advisory diagnostic.
Working-tree membership requires exit zero and exact stripped output `true`.
All other outcomes remain unverified and do not change the workload's exit status.
