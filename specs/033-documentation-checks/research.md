# Design decisions — 2026-10-15

| Decision | Evidence and rationale | Alternative rejected |
| --- | --- | --- |
| Use markdown-it-py 4.2.0 | Already installed and locked; tokens separate prose, links, headings and examples | Regex-only Markdown parsing misreads code and inline formatting |
| Track scope through Git | Tracked project prose includes historical assessments and bug evidence | Filesystem recursion includes ignored outputs and the unrelated draft |
| Keep checks read-only | Fixed Git listing, file reads and stdout/stderr are sufficient | Autoformatting and external requests exceed the approved contract |
| Keep Mermaid separate | The parser treats Mermaid as a fenced code language | Claiming syntax validation from Markdown parsing would be false |
| Preserve local overrides | Existing tool.uv.sources is unrelated development state | Re-resolving dependencies could alter approved sources |

No material clarification remains; supplied acceptance requirements determine scope.

Anchor collision and Unicode connector handling were checked against the
[github-slugger implementation](https://github.com/Flet/github-slugger/blob/master/index.js)
and its [Unicode fixtures](https://github.com/Flet/github-slugger/blob/master/test/fixtures.json).
The checker retains letters, marks, numbers and connector punctuation, removes other
punctuation/symbols, replaces ASCII spaces, and allocates duplicate suffixes.
