# Documentation check records

| Record | Fields and invariant | Owner |
| --- | --- | --- |
| Issue | Repository-relative document, one-based line, diagnostic message | Checker |
| Link | Destination and one-based source line; no URL fetching | Markdown parser |
| Parsed document | Heading/explicit anchors, local/external links and structural issues | Checker cache |

Input files and the Git index are immutable. Findings are sorted for reproducible
CLI output. Parser or filesystem failures become explicit diagnostics; unexpected
programming errors remain visible.
