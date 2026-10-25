# Release delivery — 2026-10-24

Local release completed through the existing hooks after final verification,
independent **ship** review, architecture acceptance and documentation validation.

| Artifact | Identity |
| --- | --- |
| Contributor commit | `35dd11c8105b8b3ba97d51a6bb2edabeb8e5996b` |
| Generated version commit | `4edd0cb1366c1b5817cbe8050076f608a7f03700` |
| Annotated Git tag | `v0.40.0` |
| Tag object | `c69f04a5757f46a472de3f0998b92e528599282d` |

The version commit has the contributor commit as its exact parent and changes only
`pyproject.toml`, `uv.lock` and generated `CHANGELOG.md`. Byte comparisons confirmed
that both TOML changes replace only the root version with `0.40.0`; dependency bytes
remain unchanged. The annotated tag resolves to the version commit. No distributions,
GitHub Release objects, release assets or registry packages were created.

The contributor and generated version hooks passed. The application-check log inventory
was identical before and after both commits, proving that neither reran Ruff, mypy,
Vulture, import-linter or pytest. Both reused the completed ninth canonical run
([verification](verification.md)). The receipt retained the validated physical release
identity after the release-attempt record was removed. A subsequent no-force command
reused it in **14.51 seconds**, again executing no checks. Private logs:
`.tmp/cy005-release-commit.log`, `.tmp/cy005-release-observation.json` and
`.tmp/cy005-post-tag-reuse.log`.

The exact original local `[tool.uv.sources]` section was restored unstaged after the
contributor command and all automatic-release hooks finished. It was compared with the
saved private section and confirmed to be the only working-tree change. It was then
temporarily removed again for the documentation evidence commit; the same restoration
procedure applies after that command and its hooks.

## Remote delivery deferred on 2026-10-24

The authorized atomic push of `master` and `v0.40.0` failed because GitHub was unreachable.
SSH port 22 and SSH port 443 timed out. Authenticated HTTPS push and ref inspection
both failed to connect to port 443. An authenticated API read also timed out; a bounded
HTTPS check from the Windows host did too. No credentials or persistent remote settings
were changed, and no unrelated services were restarted. All stalled attempts exited.
The earlier preflight observed remote `master` at the original baseline, but current
remote refs could not be reverified. Local tag creation is not evidence of remote delivery.

T017 remained pending after those attempts; they did not establish remote delivery.

This documentation-only follow-up records executed evidence and delivery status. It
changes no runtime module, interface, import contract or effect owner. The accepted
[architecture record](../architecture.json) covers these paths; Markdown/local links
and architecture structure are revalidated before its commit.

## Remote delivery completed — 2026-10-25

The authorized retry atomically pushed `master` and `v0.40.0` through the existing
SSH remote. A separate remote-ref query confirmed:

| Remote ref | Verified object |
| --- | --- |
| `refs/heads/master` | `d0a47a657e71ea8d818403c8a1b63909455c1c73` |
| `refs/tags/v0.40.0` | `c69f04a5757f46a472de3f0998b92e528599282d` |
| `refs/tags/v0.40.0^{}` | `4edd0cb1366c1b5817cbe8050076f608a7f03700` |

T017 is complete. The following documentation-only commit records this verified
delivery and ledger closure; it changes no application or checking behavior. The
original local dependency overrides remain excluded from commits and are restored
exactly after hooks. The existing accepted architecture record covers the evidence,
ledger and generated changelog paths; no interface, dependency or effect owner changes.
