# Data model

| Entity | Data and relationships | Validation |
|---|---|---|
| Native template | Installed YAML text, ordered native keys, values, comments and license header | Every key has train/predict applicability; no model runtime import |
| Shared settings | Full `ultralytics` mapping composed from defaults, selected group and CLI | Native names/types; non-null `cfg` forbidden |
| Prediction settings | `ultralytics_predict` inherited values plus explicit overrides | Explicit null/default values retained; usable prediction batch |
| Effective stage settings | Applicable values plus actual checkpoint, mode, source and output | Pipeline ownership and conflicting explicit references checked |
| Replay record | Commented resolved YAML, persistent source manifest, stage/split/role identity | No Hydra interpolation; active settings match native invocation |
| ClearML replay record | Canonical sanitized run Configuration Object plus native General training parameters | Existing single owner; no native-YAML artifact; credentials excluded |

Composition transitions from shared defaults/group/CLI to prediction inheritance/explicit
overrides, then stage filtering and owned execution inputs. Local export follows resolution.
Failed computation or publication retains local records and fails the existing task lifecycle.
