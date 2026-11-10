# Data model

`BatchSizeTable` holds a content digest, validated entries and no-capacity failures. Entries contain GPU label/name/precise bytes, positive square size, canonical model and positive per-GPU batch. Selection records target hardware and exact/fallback provenance.

Measurement cases retain existing profile/workload/settings/trials and key identity. New search strategy adds low integer candidates without migrating historical cases.

Publication transitions: accepted success replaces selected entry and clears its failure; accepted no-capacity removes entry and sets failure; other failures leave the table unchanged. A manual exact entry takes precedence over a failure. Default population fills only missing exact entries.
