# Data Model: Identity Footer

## ModelIdentity (existing, unchanged)

`model_name`, `training_task_id?`, `checkpoint_sha256?`, `model_id?`. It is persisted in
the workbook identity metadata (namespace `https://clearml-yolo/model-identity/v1`,
unchanged).

## IdentityLinks (new, core, not persisted)

| Field | Type | Rule |
| --- | --- | --- |
| `model_url` | `str \| None` | Absolute `http`/`https` URL, or None |
| `task_url` | `str \| None` | Absolute `http`/`https` URL, or None |

Frozen and `extra="forbid"`. Construction rejects other schemes. It is built only at
render time and is never written to identity metadata.

## Footer line (presentation, derived)

For each role, in identity order:

| Condition | Line 1 | Line 2 |
| --- | --- | --- |
| `model_url` known | `<Role>: <label>` → `model_url` | — |
| `model_url` unknown | `<Role>: <label>` (plain) | — |
| `training_task_id` and `task_url` | — | `Training task: open in ClearML` → `task_url` |
| `training_task_id`, no `task_url` | — | `Training source: recorded` |
| no `training_task_id` | — | `Training source: unavailable` |

The alias notice follows the role lines when any class label was aliased.

Page footer: `<Role>: <label> · Training source: recorded|unavailable`, joined by ` | `,
escaped, ≤255 characters.

## Workbook states

`unannotated` → `presentation-only` (alias footer) or `identity-annotated` (identity
footer, optionally with a metadata-only presentation envelope inside it). Re-annotation
always restores the authenticated original first. Historical `top-banner` workbooks
remain readable and are re-annotated into the footer layout.
