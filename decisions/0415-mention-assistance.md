# ADR-0415 · Dispatch repository assistance on explicit Claude mentions

The repository also declares a GitHub workflow for issue and review interactions. It evaluates the event body or issue title for an explicit Claude mention before invoking the configured action. This is distinct from the automatic [PR review](0414-pr-review.md) and from the [release workflow](0412-code-release.md).

Operators can inspect the event filter and job permissions to determine which interactions qualify. A successful invocation depends on GitHub Actions configuration and available authentication. [Event and permission declarations](../.github/workflows/claude.yml)
