# ADR-0414 · Request automated review on pull request updates

The repository declares a GitHub Actions review job on pull request opening, synchronization, reopening and transition to ready for review. It checks out the repository and invokes the configured review action. Maintainers still need independent review and the applicable CY verification evidence before merge. A workflow definition establishes the intended trigger. Actual service execution needs a run record.

The operating instructions say no CI check runs on PRs, while the review workflow declares an automatic PR job. The project test and acceptance tasks run separately. [Workflow](../.github/workflows/claude-code-review.yml) · [Delivery instructions](../AGENTS.md#delivery-and-release) · [Open discrepancy](https://linear.app/sip-ds-team/issue/SIP-351)
