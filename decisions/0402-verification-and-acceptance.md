# ADR-0402 · Match verification evidence to the change and execution environment

The repository checks every change against whole-tree contracts, then selects tests for the affected behavior. A result belongs to the revision, inputs and environment that produced it. Acceptance adds live evidence when the change depends on a real service, GPU or sibling package.

## Whole-tree checks and test selection

`task verify` first checks hygiene, lock freshness, Ruff, formatting, import architecture, strict types, unused code and dependencies. Hygiene can apply whitespace fixes and fail for inspection. Automatic selection examines the staged diff, then working changes, then the last commit. Prose takes the static route. A product change selects affected unit tests. A test-only change uses bounded selection and can report a gap if a helper has no recorded dependents. Review the entire branch diff when the final commit covers only part of it.

The affected unit suite uses testmon history and an environment fingerprint. A full unit run refreshes that history. Only the full branch-coverage task establishes the coverage floor. Distributed CPU and process-capability scenarios also have explicit marker runs. Mutation analysis separately asks whether the tests distinguish changes to product functions. Its advisory report lists survivors and unreached functions for disposition. Strict failure and tool errors have distinct meanings. [Verification tasks](../Taskfile.yml) · [Change selector](../scripts/verification.py)

<details>
<summary>Sources and verification</summary>

- Apply the same whole-tree static checks to each change — [Static analysis contract](../DOCS.md#static-analysis) · [Hygiene implementation](../scripts/hygiene.py)
- Route verification by the change set — [Bounded collection](../scripts/verification_collection.py)
- Select affected unit tests with testmon — [Environment fingerprint](../scripts/testmon_environment.py) · [Pytest configuration](../pyproject.toml) · [Operating instructions](../AGENTS.md#checks)
- Report mutation outcomes for changed product functions — [Selector and report](../scripts/mutation.py)

</details>

## Live services and owned resources

Live integration creates a namespaced environment with session credentials, tagged resources and an ownership record. The CPU smoke scenario invokes CY and queries the resulting ClearML task. FiftyOne scenarios exercise publication, evaluation and panel behavior. Preflight distinguishes invalid configuration from an unavailable cluster. Teardown checks ownership, and an operator who retains an environment can later clean it up by identifier.

These observations apply to the paths exercised. Agent replay, browser behavior and multi-host operation each need evidence from the corresponding environment. [Lifecycle and operating guide](../tests/integration/lifecycle.py)

<details>
<summary>Sources and verification</summary>

- Give each integration run an owned test environment — [Task entry points](../Taskfile.ops.yml) · [Live fixtures](../tests/integration/conftest.py)
- Run live service checks with isolated credentials and tagged resources — [CPU ClearML scenario](../tests/integration/test_cpu_stand_smoke.py) · [FiftyOne service scenarios](../tests/integration/fiftyone) · [Environment contract](../DOCS.md#live-test-environment)

</details>

## Native detector scenarios

The Severstal corpus tool derives detection boxes from connected mask components in an existing local download. It writes full and smoke ground truth tables and a manifest that binds the splits, source identities and hashes. Verification checks the manifest and CSV bytes and can verify the selected images.

With that corpus, a specified GPU and an explicit ClearML destination, the native scenario performs short training, checkpoint reload, inference and publication checks. Its result establishes execution of the selected configuration. Accuracy benchmarking and multi-GPU validation require different observations. [Corpus builder](../scripts/severstal.py) · [Native scenario](../tests/integration/test_severstal_gpu.py)

<details>
<summary>Sources and verification</summary>

- Derive a reproducible detection corpus from Severstal masks — [Native scenario contract](../DOCS.md#live-test-environment)
- Exercise the native detector lifecycle on one GPU — [Scenario harness](../tests/severstal_harness.py)

</details>

## Change acceptance and paired releases

Change acceptance starts from a clean committed tip, runs the checks, preflights the integration environment, measures coverage and exercises live integration. It verifies the tip and clean state again at the end. An unavailable required environment defers acceptance until it runs or the user waives it.

Release validation extends this with the native GPU scenarios and FiftyOne checks. Release acceptance also installs CY and cy-queue together in a temporary environment, verifies their editable versions and source locations, then runs the queue's own checks, tests and help. The queue checkout must be clean and contain its fetched default branch. Both repositories' source identities are checked again at exit. [Acceptance and pairing tasks](../Taskfile.ops.yml)

<details>
<summary>Sources and verification</summary>

- Tie change and release acceptance to identified inputs — [Live requirements](../DOCS.md#live-test-environment) · [Status definitions](../AGENTS.md#checks)
- Verify CY and cy-queue together before an interface or dependency release — [Metadata checks](../scripts/paired_metadata.py)

</details>
