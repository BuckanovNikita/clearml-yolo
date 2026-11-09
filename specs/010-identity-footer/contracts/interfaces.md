# Interface Contracts: Identity Footer

## report-generator `report_generator.v2.annotate_workbook` (additive)

```python
def annotate_workbook(
    path: str | Path,
    *,
    banner_lines: Sequence[str],
    metadata_texts: Mapping[str, str],
    format: MetadataFormat,
    validate: MetadataValidator | None = None,
    placement: Literal["top", "bottom"] = "top",
    banner_links: Sequence[str | None] | None = None,
    page_footer: str | None = None,
) -> None
```

- `placement="top"` with no new arguments behaves exactly as before. With `"top"`,
  passing `banner_links` or `page_footer` raises `ValueError`.
- `placement="bottom"`: no coordinates move. Lines start at R2's footer row on every
  worksheet. `banner_lines` may be empty (metadata only). `banner_links` has the same
  length as `banner_lines`. Each non-None entry must be an absolute http(s) URL; it
  becomes an external hyperlink on that line's cell. `page_footer` becomes the escaped,
  ≤255-character left `oddFooter`. No `_xlnm.Print_Titles` is added. An existing
  `_xlnm.Print_Area` is extended to the last footer row.
- The original bytes, metadata envelope, fingerprint and `original_workbook`
  recovery are unchanged in every mode.

## clearml-yolo ports (application/ports.py)

```python
class TrackingSession(Protocol):
    def identity_links(self, task: TaskHandle | None, identity: ModelIdentity) -> IdentityLinks: ...

class ReportRenderer(Protocol):
    def annotate_workbook(
        self, path: str | Path, identities: Mapping[str, ModelIdentity],
        *, links: Mapping[str, IdentityLinks] | None = None,
    ) -> None: ...
    def write_evaluation_workbook(
        self, path: Path, evaluated: EvaluatedSplit, *, methodology: dict[str, Any],
        links: IdentityLinks | None = None,
    ) -> dict[str, Path]: ...

class EvaluationWriter(Protocol):
    def render_evaluation(..., links: IdentityLinks | None = None) -> EvaluationArtifacts: ...
```

- `links=None`, or a role missing from the mapping, renders plain text.
- `identity_links` never raises. It returns `IdentityLinks()` when the invocation task is
  None or the identity has no source identifiers (no SDK call), or when URL building fails
  (DEBUG log).
