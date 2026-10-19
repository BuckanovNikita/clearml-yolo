# Research: Stable ClearML parameter identity

Inspected on 2026-10-16 before implementation.

- Installed `ClearmlJob._create_task_hash` includes script, hyper_params, serialized
  configs and applicable container settings; callback runs before hash creation.
- `ClearmlJob.__init__` hashes before cloning/launching. Worker-only filtering cannot
  fix lookup. The public register_hashing_callback hook supports an external adapter.
- Ultralytics pretrain connects General through the existing owner-local proxy.
  Detector publication has a separate explicit General connection.
- Hydra currently pops ultralytics before run recording and restores General on
  remote training. Full replay storage must be added before excluding device fields.
- PreparedDataset currently carries data/manifest paths; storage completion already
  verifies a versioned identity derived from CSV bytes, resolved media references and
  format. Exposing that key avoids inventing a new fingerprint.
- Existing import-linter and negative architecture tests cover all affected layers.
- Implementation inspection found SDK config_dict serialization uses HOCON. New run
  snapshots instead provide JSON config_text, which the SDK already reads correctly.
  This keeps the controller helper effect-free and avoids a bespoke HOCON parser;
  historical HOCON remains unchanged and may conservatively miss cache reuse.

Alternatives rejected: removing all Configuration Objects loses replay; deleting every
path/name/device risks scientific cache collisions; SDK monkeypatching introduces
global effects and cannot substitute for explicit controller registration.
