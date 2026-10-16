# Research decisions

- Existing PublicJob carries label and host-wide submission_sequence, but CLI/TUI print
  raw identity and submission does not populate labels. Reuse these fields.
- Persist archive outside public.json to keep the existing strict durable schema readable.
  Full job replay and submission-number allocation must include archived history.
- CY_QUEUE_ROOT exists but silently falls back to a project directory. Require one shared
  TOML selected by CY_QUEUE_CONFIG. Keep the file store and Unix ownership guarantees.
- Store transactions currently omit the explicitly passed runtime coordination root.
  Inject one resolved root into storage, runtime and guardian construction.
- Console mirror copies bytes directly; publisher splits chunks independently. Human
  formatting therefore needs bounded streaming handling while capture stays byte-exact.
- Full source task IDs are required by old report banners. Explicit user intent supersedes
  display requirements while original identity metadata remains unchanged.
- Temporary real accounts are explicitly authorized. Root access was verified read-only;
  actual provision/test/cleanup results belong in dated verification, not this design.
