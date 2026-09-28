# Data Model

No new persistent application model or database schema is introduced.

| Entity | Fields and relationships | Constraints |
|---|---|---|
| Example set | One path/content pair per registered execution command | Eight files; names match console commands; defaults and required inputs preserved |
| Destination | Directory plus overwrite flag | Expand user home; create missing parents; preserve unrelated files; force applies only to regular example files |
| Configuration content | Usage comments and unresolved YAML representation | No credentials, environment probes, exhaustive native defaults, or execution outputs |
| Release record | Version, source commit, tag, notes, distributions, SHA-256 hashes | Published assets must match verified packages and tag must identify the pushed commit |

Generation transitions from destination validation to configuration composition, directory
creation, and file writes. A detected collision fails before writes. Filesystem errors during
writing fail the command; no transaction or rollback is promised for mid-write I/O failures.
