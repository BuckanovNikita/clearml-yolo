# Data Model

No new persistent application model or database schema is introduced.

| Entity | Fields and relationships | Constraints |
|---|---|---|
| Example set | One path/content pair per registered execution command plus two native group paths | Ten files total; command names match console commands; defaults and required inputs preserved |
| Destination | Directory plus overwrite flag | Expand user home; create missing parents; preserve unrelated files; force applies only to regular example files |
| Configuration content | Usage comments, unresolved command YAML, full shared native defaults, and explicit prediction overrides | No credentials, environment probes, or execution outputs; upstream comments are preserved |
| Release record | Version, source commit, tag, notes, distributions, SHA-256 hashes | Published assets must match verified packages and tag must identify the pushed commit |

Generation transitions from destination validation to configuration composition, directory
creation, and file writes. A detected collision fails before writes. Filesystem errors during
writing fail the command; no transaction or rollback is promised for mid-write I/O failures.
