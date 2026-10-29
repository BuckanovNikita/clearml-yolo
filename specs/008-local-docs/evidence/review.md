# Independent review — 2026-10-29

## First integrated review

After parent verification passed (4,344 ordinary tests, ten browser cases,
documentation checks, separate installation and native evidence), two independent
native agents reviewed fresh contexts with no write ownership or further delegation.
No model/effort override was requested; actual runtime settings were not observable.

`final_review` inspected the full feature, architecture, tutorial and portable-skill
scope and returned **fix-first**. `preview_final_review` independently inspected
containment, HTTP and process ownership and also returned **fix-first**. Reviewers
used source inspection and bounded reproductions; they did not claim to rerun the
parent's complete suite or native pipelines.

## Findings and implementation response

| Finding | Response and verification |
| --- | --- |
| Interpolated `hydra` container can execute a resolver or expose an external search path before an eventual merge error | Reproduced both failing observations; one test uses a positive-controlled file-open observer. Preview now rejects submitted Hydra runtime blocks/overrides and Hydra package defaults before composition. Application resolver expressions remain unresolved. Controls are documented as terminal-only. |
| SIGKILL leaves child-owned submitted YAML directories behind | Five tests reproduced failures. Parent now retains a per-worker temporary root, passes a copied child temp environment, kills/reaps then removes the root, and synchronously performs the same idempotent cleanup during close. |
| Mapping/nested declaration examples become string assignments | Example rendering now recognizes full nested and relative declaration override keys. Added browser clicks and actual composition for `clearml`, `compare.q`, `metrics.calibration_split`. |
| `.yml` accepted despite Hydra loading only `.yaml` | Reject unsupported suffix with an explicit `.yaml` requirement before composition; covered by regression and updated guidance. |
| Native batch reference says null starts measurement | Corrected Russian reference to saved compatible `cy-batch-estimate` lookup and failure when unavailable, matching runtime and tutorial behavior. |

A sweep-order concern was adjudicated against installed Hydra BasicSweeper.
Its repeated-key handling itself produces the reported difference between a
single run and a sweep. Changing only preview would disagree with the exported
terminal command. The broader reviewer independently withdrew that finding.
Added a comparison against actual `BasicSweeper.split_arguments` and documented
the behavior; ordinary non-sweep overrides still retain every occurrence in order.

The modified preview suite passed 30 tests; worker/isolation remediation passed
56 tests. Parent verification then reran the complete canonical suite (4,358 passed,
30 skipped, 81 deselected, all static/import checks passed), all 11 browser cases,
documentation checks and the installed snapshot with actual temp-directory cleanup.
Final read-only review of these changes remains required; the first-round verdicts
are not represented as approval.

## Ownership and release boundary

Feature 007 and independent corp-skills edits predate this work. The first reviewer
confirmed the architecture placement and reviewed feature scope otherwise looked
sound, but explicitly did not approve releasing 007 or waive the proposed-version
paired release check. Review acceptance of 008 cannot silently include those files.

## Catalog metadata closure

Fresh `acceptance_review` independently inspected the corrected feature and the
companion seven-path source candidate. It approved the companion source commit and
found no remaining blocker in preview isolation, cleanup, examples, `.yaml`, sweep
compatibility or architecture placement. It confirmed a parent-observed catalog
default issue and additionally identified its input-shape counterpart: implicit
argparse flags appeared as strings with null defaults.

The parent captured the failing catalog assertion, then changed only the option
projection and its regression: use `parser_for(command).get_default(destination)`
and flag action shapes. Parser implementations/behavior were unchanged. Six focused
catalog tests, full canonical verification (4,359 passed; 30 skipped; 81 deselected;
all static/import checks), 11 browser cases, documentation and fresh installed
catalog/worker checks passed. `catalog_closure_review` receives this exact final
source in another fresh read-only context for the closing verdict.

## Final implementation verdict

`catalog_closure_review` returned **ship for feature 008 implementation closure**,
with no blocking findings. It independently checked all 24 option declarations
across five utilities against inert argparse defaults/destinations, including the
five implicit false boolean defaults. It confirmed canonical log hashes and final
4,359/30/81 counts, all static/import checks, the 11-case browser log, coverage
467/156/8 and the matching latest 337-file installed package digest.

The final reviewer found the correction consistent with the assembly/options
responsibilities and dependency/effect ownership, and validated a completed
architecture record in memory. Together with the broader `acceptance_review`,
this closes implementation/architecture review of the task-owned feature. Review
was read-only and fresh-context; neither reviewer claimed to rerun native workloads
or approve a release version.

Parent reconciliation includes new documentation entrypoints/adapters/records,
named declarations and metadata, utility parser refactors, packaged HTML/CSS/JS and
tutorials, maintenance renderer, coverage/compatibility/fault/browser tests, exact
import owners, dev browser dependency and affected guidance. There are no removed
or renamed runtime paths. The captured 007 changes are excluded except the planned
additive parser refactor and shared-file additions; the 14 nonshared pre-existing
tracked paths remained byte-identical. Companion source commit `80ec2a0` includes
only the separately reviewed seven paths and preserves all prior working contents.

No runtime-source changes followed final canonical verification. The parent persists
this acceptance in architecture.json and runs its acceptance validator plus refreshed
documentation checks. [Delivery limitations](delivery.md), including the unaccepted
007 prerequisite and proposed-version paired check, remain explicit and separate.

## Fresh integrated release review

After the parent integrated 008 onto released 007 and obtained a stable canonical
receipt, fresh native read-only agent `release_final_review` returned **ship**.
No blocking runtime, compatibility, integration or architecture findings remained.
The reviewer used no further delegation and did not claim to rerun full suites,
browsers or native workloads.

It independently compared all 337 package files with the earlier reviewed 008
snapshot: only the two native-cache modules differ, each identical to released
007. The six modified public-model modules retain identical non-documentation AST
when field descriptions/examples/schema metadata are removed. It inspected parser
and composition compatibility, inward imports, preview guards, injected worker
interfaces, parent-owned process cleanup and file confinement. Canonical receipt
log hashes, all 52 import contracts and the 4,373/30/81 test outcome were verified,
along with the documentation log hash, installed 337-file manifest, browser/native
and proposed-version pairing records. Architecture acceptance and whitespace checks
passed independently.

The reviewer identified one minor evidence-link correction in the final installed
0.43.0 appendix: reference `release-pair.md`, which contains the proposed-version
checks, instead of the earlier `paired.md`. The parent corrected that link and
passed its Markdown/local-link check. This changes no runtime or verification input.

`release_companion_review` separately approved the queue's two-line 0.1.4/version
bound update and the eight-path collection 0.6.2 guidance candidate after their
parent checks. Final native release hooks, actual committed-version pairing and
verified remote delivery remain T023; neither review substitutes for those steps.
