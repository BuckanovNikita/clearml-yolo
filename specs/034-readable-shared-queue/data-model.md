# Data model

- Job reference: `job-N`, where N is persisted submission_sequence within root and host.
  Internal UUID remains the durable key. Existing labels remain immutable submission data.
- Archive record: owner-written sidecar with job identity, archived state, revision and
  timestamp. Missing means unarchived. JobState and public.json remain compatible.
- Queue view: full revision plus archive identity set. Filtering is separate from durable
  replay. Recovery-required state overrides archived visibility.
- Queue settings: queue name, absolute metadata and coordination paths and source path.
  Resolved once at composition; process payloads carry resolved paths.
- Human text: pure presentation of names/context with safe generic references when no
  name is known. It never overwrites raw IDs, source model identities or captured bytes.
- Workbook presentation: an optional versioned envelope retains the original workbook
  bytes and a source-label/display-alias mapping. Existing model-identity metadata keeps
  its schema. Readers unwrap both envelopes and validate fingerprints before recovering
  the exact original class keys, metric values and layout. Distinct source labels receive
  distinct display aliases; ordinary readable workbooks need no presentation envelope.
