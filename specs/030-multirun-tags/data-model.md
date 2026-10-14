# Data model

No new schema. `ClearMLConfig.tags` remains a list of strings. A launch-local optional
string holds the generated tag. Queued `JobSnapshot.config_json` persists that same
string within `clearml.tags`; no queue protocol field or migration is required.
