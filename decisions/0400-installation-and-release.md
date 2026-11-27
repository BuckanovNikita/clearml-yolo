# ADR-0400 · Install reproducible inputs and release from reviewed source

A CY release identifies code, its version and its dependency declarations. The runtime is installed before an experiment starts. Scientific dependencies and redistributable model weights have their own source and publication rules.

## Runtime and scientific dependencies

The package defines the supported Python range, Linux runtime and console commands. Experiment commands need ClearML with remote storage. Tools such as configuration export have narrower requirements. A contributor prepares the approved digital-metrics and report-generator checkouts, builds their distributions into the worktree-local wheelhouse and uses the locked environment. The bootstrap preserves existing uv settings and checks the wheelhouse lookup path.

The lock identifies the distributions but cannot prove which source checkouts produced the local archives. Git installs can resolve different versions within the declared ranges. When a direct dependency floor changes, check a lowest-direct installation on each supported Python minor as well as the locked environment. The Hydra floor change illustrates why an actual API consumer belongs in that check. [Installation guide](../docs/installation.md) · [Hydra floor decision](https://linear.app/sip-ds-team/issue/SIP-335)

CY requires digital-metrics 0.7.0 or newer for the evaluation APIs it imports, and requests 2.32.4 or newer for host-scoped netrc credentials. These minimums apply to installations from Git as well as to the contributor environment. [Evaluation dependency](https://linear.app/sip-ds-team/issue/SIP-337) · [HTTP dependency](https://linear.app/sip-ds-team/issue/SIP-338)

<details>
<summary>Sources and verification</summary>

- Install the experiment runtime before launching a command — [Distribution metadata and scripts](../pyproject.toml) · [Process capability tests](../tests/test_process_capabilities.py)
- Build the approved scientific dependencies into a worktree-local wheelhouse — [Dependency reference](../DOCS.md#installation-and-dependencies) · [Bootstrap](../Taskfile.ops.yml) · [Local configuration validation](../scripts/check_local_uv.py) · [Lock](../uv.lock)
- Verify advertised dependency floors separately from locked versions — [Consumer](../src/clearml_yolo/entrypoints/hydra/validation.py)

</details>

## Review and change delivery

A Linear issue tracks the change, verification and review evidence. Its identifier appears in the task branch's PR title. A human merges accepted work into master. The repository declares a GitHub Actions review job for opening, updating, reopening and marking a PR ready. A separate workflow handles explicit Claude mentions on supported issue and review events.

The operating instructions say that no CI check runs on PRs, while the checked-in review workflow declares an automatic job. The project's test and acceptance tasks run separately. An individual Actions run provides evidence of what actually executed. [Review workflow](../.github/workflows/claude-code-review.yml) · [Tracked discrepancy](https://linear.app/sip-ds-team/issue/SIP-351)

<details>
<summary>Sources and verification</summary>

- Track a change from Linear through human merge — [Delivery agreement](../AGENTS.md#delivery-and-release) · [Release trigger](../.github/workflows/release.yml) · [Triage decision](https://linear.app/sip-ds-team/issue/SIP-234)
- Dispatch repository assistance on explicit Claude mentions — [Event and permission declarations](../.github/workflows/claude.yml)

</details>

## Version and tag publication

A merged PR triggers the serialized semantic-release workflow on master. Conventional Commit headers determine whether to release a version. For a version change, the runner checks the base, limits the generated commit to release metadata, verifies its annotated tag and pushes the commit and tag atomically. A changed remote base or an existing tag blocks publication. A documentation change can finish without a version bump.

The release records a source revision. GPU compatibility requires its own [verification](0402-verification-and-acceptance.md#native-detector-scenarios), and model archives use a separate [weight release](0213-model-assets.md#preparing-and-publishing-the-catalogue). [Release runner](../scripts/release.py)

<details>
<summary>Sources and verification</summary>

- Publish a version commit and annotated tag together — [Release contract](../DOCS.md#release) · [Workflow](../.github/workflows/release.yml) · [Lock guard](../scripts/release_lock_guard.py)

</details>
