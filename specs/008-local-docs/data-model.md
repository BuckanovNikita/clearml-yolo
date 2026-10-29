# Documentation data model

`FieldDoc`: stable id, dotted path, Russian description, input shapes, constraints,
applicability, examples, source, required/default behavior, generated/read-only flag.

`ConfigurationDoc`: command, selected model/profile, unresolved YAML, safely selected
values and field entries. Dynamic mappings document their container contract, not arbitrary
user keys. Generated transform snapshots and checkpoint provenance are labeled separately.

`Catalog`: version, commands, models, profiles, fields, defaults, tutorials and scenario
inventory. Browser and checks consume the same records.

`PreviewRequest`: command, documents (name/YAML pairs), ordered overrides, sweep flag.
`PreviewResult`: composed YAML jobs, errors, unresolved paths, deferred runtime checks,
command string. Paths/names/size and plugins/search paths are checked before composition.

`Tutorial`: id, title, generated page, command/group/scenario mappings and preview cases.
Source Markdown must contain prerequisites, examples, expected outputs, failures and checks.
