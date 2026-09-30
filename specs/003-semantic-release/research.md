# Research: Local Semantic Release

## Decisions

- **Decision**: Python Semantic Release 10.x configured in pyproject.toml.
  **Rationale**: Native project metadata support without a Node toolchain.
  **Alternative**: Node semantic-release plus Python-specific plugins adds machinery.
- **Decision**: Explicit `allow_zero_version = true`, `major_on_zero = false`, master
  only, Conventional Commits. Features/breaking changes bump minor; fixes/perf bump patch.
  **Rationale**: Matches approved 0.x policy. Default v10 policy would otherwise force 1.0.
- **Decision**: PSR computes/stamps; ordinary Git creates commits and tags.
  **Rationale**: Allows lockfile validation between stamping and checked commits, and
  precise recovery. PSR's no-commit mode still stages version files; preflight must ensure
  an initially clean index. `--print` returns the existing version for a no-op.
- **Decision**: Reject shallow repositories before invoking PSR and use offline lock refresh.
  **Rationale**: PSR can automatically fetch shallow history. `--no-push` alone is insufficient
  to guarantee no remote operations. No hook needs a remote token.
- **Decision**: Recovery metadata and a common Git-directory lock.
  **Rationale**: Post-commit cannot reject the original commit, and metadata may be dirty
  after failure. A recorded source/version allows safe tag-only retries; locking shared
  Git metadata protects multiple worktrees. Never infer ownership solely from a commit title.

## Review-driven refinements

- pre-commit's standard post-commit launcher temporarily stashes unstaged changes.
  A reproduced partial-commit failure showed that the helper then saw a false clean
  tree. Use an owned launcher with `--all-files`, installed by `--install-hooks`;
  this changes installation, not the approved release behavior. Existing custom
  launchers must be preserved, not silently replaced.
- Git removes some operation markers before post-commit. An amend reproduction
  released rewritten history; automatic calls also inspect the current reflog action.
- A concurrent staging reproduction included an unrelated file in an unrestricted
  release commit. Use `git commit --only` for the two owned metadata paths and
  require a clean tree before tagging, leaving unrelated index entries intact.
  The 2026-09-30 changelog amendment extends the owned paths to include CHANGELOG.md.

## Changelog amendment (2026-09-30)

- Use PSR's full-history `init` mode for reproducible regeneration and complete
  historical release entries. Exclude generated release subjects and retain initial
  release details. Release preparation renders the source commit under its new version.
- PSR requires a matching release branch even for changelog-only rendering. The helper
  uses a temporary configuration allowing the current named branch only for that
  command; tracked configuration and master-only versioning are preserved. Detached
  HEAD refresh is skipped. Temporary configuration is removed after rendering.
- pre-commit does not detect newly created untracked files as modified output. The
  helper compares changelog bytes and explicitly exits 1 on changed output, without
  staging it. Subsequent unchanged invocations exit 0.
- A release guard or recovery record prevents refresh from replacing an untagged
  prepared version section. Persist its SHA-256 before attempting the checked commit;
  verify it before tagging, including manual recovery.

## Sources

- [PSR CLI](https://python-semantic-release.readthedocs.io/en/latest/api/commands.html)
- [PSR configuration](https://python-semantic-release.readthedocs.io/en/latest/configuration/configuration.html)
- [pre-commit hook stages](https://pre-commit.com/#supported-git-hooks)

No unresolved research decisions. Runtime behavior is validated against the locked
PSR version in temporary repositories rather than inferred solely from documentation.
