# Issue template

This is the source of the Linear issue template `clearml-yolo task` (Team settings →
Templates for team `SIP`). Agents creating an issue apply that template when it exists in
Linear, and otherwise copy the body below.

````markdown
## Outcome

## Scope
In:
Out:

## Acceptance criteria
- [ ]

## Verification
Delete the lines that do not apply. After each kept line write one status when it has
run: passed, failed, deferred, waived or error. Tick a box only for passed, or for
waived by the user. A deferred required check blocks merge.

### Commit gates
- [ ] Staging guard (`task staging-check`)
- [ ] Hygiene (`task hygiene`)
- [ ] Lock freshness (`uv lock --check`)
- [ ] Ruff lint (`ruff check .`)
- [ ] Ruff format (`ruff format --check .`)
- [ ] Import contracts (`lint-imports`)
- [ ] Type check (`mypy .`)
- [ ] Dead code (`vulture`)
- [ ] Dependency declarations (`deptry .`)
- [ ] Routed verification (`task verify`): static, tests or product route
- [ ] Commit messages (Conventional Commits hook)
- [ ] Final pass on the committed tip (`prek run --all-files`, see the commit procedure)

### Offline tests
- [ ] Affected unit tests (`task test`)
- [ ] Full unit suite (`task test-full`)
- [ ] Coverage with the configured floor (`task coverage`)
- [ ] Mutation report for the change (`task mutation`)
- [ ] CPU distributed training suite (`pytest -m ddp_cpu`)
- [ ] Process capability suite (`pytest -m process_capabilities`)
- [ ] Suite on each supported Python minor
- [ ] Lowest-direct dependency resolution

### Live environment
- [ ] Infrastructure preflight (`task infra-check`)
- [ ] Non-GPU live tests (`task integration`)
- [ ] Change acceptance on a clean tip (`task acceptance`)

### Release tier
- [ ] Single-GPU Severstal suite (`pytest -m severstal_gpu`)
- [ ] FiftyOne native database suite (`CY_TEST_FIFTYONE=1`)
- [ ] Paired CY and cy-queue check (`task paired-check`)
- [ ] Release validation (`task release-validation`)
- [ ] Release acceptance (`task release-acceptance`)

### Manual live observations
- [ ] Native execution, direct and queued
- [ ] Publication readback and forced downloads
- [ ] Standalone chart rendering
- [ ] FiftyOne App views
- [ ] Detector and export matrices

### Review and delivery
- [ ] Documentation consistency review
- [ ] Fresh independent review after integrated verification
- [ ] Weight-release verification
- [ ] Release workflow result after merge

## Evidence
Commands, source and environment identities, limitations, links.
````
