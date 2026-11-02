# Cleanup delivery — 2026-11-02

**Outcome**: CY 0.44.6 and companion queue 0.1.7 published as verified Git source.

## Published identities

- CY implementation: [9054b960f731f83d336ea242e5dc86ad3b280cbd](https://github.com/BuckanovNikita/clearml-yolo/commit/9054b960f731f83d336ea242e5dc86ad3b280cbd).
- CY native release commit: [6fcc78c08ff9f37b98faf6bdfb1f26285829b7b3](https://github.com/BuckanovNikita/clearml-yolo/commit/6fcc78c08ff9f37b98faf6bdfb1f26285829b7b3).
- Annotated [v0.44.6](https://github.com/BuckanovNikita/clearml-yolo/tree/v0.44.6): tag object 74c9b7e8eec37f0ae01be2b50cc2f00b24d799ed, peeled commit exactly the release commit above.
- Queue implementation 0.1.7: [b976789301d814a4249d3683739b8d6918819a73](https://github.com/BuckanovNikita/cy-queue/commit/b976789301d814a4249d3683739b8d6918819a73); main documentation closure [4e539f227f06e600d95753e27049baf6df517398](https://github.com/BuckanovNikita/cy-queue/commit/4e539f227f06e600d95753e27049baf6df517398).

CY master and the specific version tag were pushed atomically and all three remote
identities (branch, annotated object and peeled commit) were verified. Queue main
pushes and both source/closure identities were verified separately. No history was
rewritten, hook bypassed, code GitHub Release object created, package/asset uploaded
or registry/deployment action performed. The existing model snapshot was retained.

## Acceptance and scope

Native CY hooks passed and generated only the changelog and root version tokens in
pyproject/lock. Parent verified this exact release diff and tag type/target. Before
push, the latest committed pair resolved normally and matched source/installed/import
identity: CY 0.44.6 and queue 0.1.7. Pip consistency, queue Ruff/format, strict mypy,
both import contracts and installed help passed. Full queue integration passed 582
cases, 7 physical opt-ins deselected, in 128.66 seconds. Original admission plus all
38 new deterministic cases separately passed 39 cases in 1.14 seconds.

CY canonical receipt 38ae7edf6f434071b262a7cea5027940 accepted all static/import checks
and 4545 passes, 30 skips, 81 deselections. The unchanged CY source also has 11 browser
passes, successful fresh-cache native restoration/offline DINO loading, and 433 fresh
numerical mutants (430 killed, three reviewed equivalent). Fresh CY and corrected
queue reviews returned ship. Both architecture records passed acceptance; changed
Markdown/links and catalog examples passed. Frozen primary CY verification inputs
were preserved through completion hooks, while a separate normal installation
established the latest source/installed pair. Context and limitations are in
[execution](execution.md), [acceptance](acceptance.md) and [mutation](mutation.md).

CY has 26 fewer collected cases after retaining unique coverage and adding bug
regressions. Quiet release-fixture setup median decreased from 0.21147 to 0.00183
seconds. Overall CY suite time increased from baseline 1142.23 to final 1460.36
seconds: no causal whole-suite speedup is claimed. Queue adds meaningful race
regressions; there is no claim that combined repository test count decreased.

Original dirty workspaces/index/local overrides, approved external sources and
pre-existing services/workloads remain preserved. Only isolated task-owned checks
and package environments were used. Physical GPU, real multiuser, live ClearML and
historical hardware gaps remain explicitly unverified; offline loading/process
checks do not close them. Normal completion documentation follows the release commit
without a further version bump and is verified on master separately.
