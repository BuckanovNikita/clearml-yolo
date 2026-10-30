# Independent review: persistent YOLO weights directory

Date: 2026-10-30. Reviewer: native fresh-context final_review agent, read-only,
with no delegation. Scope: final integrated CY delta from 3636404 and portable
collection delta from c985e12, including untracked tests and workflow evidence.

## Verdict

Ship conditional on remaining execution gates. No blocking code or documentation
finding. The reviewer inspected the full diff, installed SDK implementation,
regressions, architecture record/contracts, documentation and canonical logs.

The settings adapter coherently owns SDK/filesystem effects. It reads the latest
saved mapping under the adjacent lock, uses the public API for weights_dir,
restores unrelated runtime overrides, verifies persistence and synchronizes both
live consumers. Preparation and estimator setup ordering are correct. The exact
import allowance and two negative cases preserve caller/target boundaries.

## Limits and required follow-through

The lock coordinates CY calls, not independent SDK writers. Native SDK writes are
not transactional; readback detects failure but cannot undo a partial write.
Real CPU checkpoint loading proves discovery, not GPU AMP numerical or training/
publication outcomes. The reviewed full suite passed 4482 tests but its verifier
refused a receipt after optional pi_heif installation. Stable canonical acceptance,
final docs/architecture reconciliation and post-hook paired metadata remain required.

## Portable explanation-only evaluation

The reviewer independently answered both newly appended prompts using the changed
usage reference. No commands were executed for those prompt responses; this was
native agent evaluation, not a live OpenCode or DeepSeek run.

Success response covered all ten expected behavior groups: source/installed-version
guard; explicit setup before reuse/worker launch; relative-cwd and retained absolute
selection; one-time original-directory migration; valid-file reuse; selected/AMP
lookup and both live values; lock/readback; idempotence; preserved unrelated settings,
runtime callbacks and files; inert inspection and no inferred GPU success.

Failure response covered all seven expected groups: preserve settings/cache; do not
mask persistence failure by changing cwd; inspect the reported JSON and weights_dir;
check file and parent permissions; correct and retry from original preparation cwd;
retain diagnostics if verification fails; do not treat help as successful setup.

## Parent reconciliation

Only the task delta was applied to an isolated checkout of latest CY master.
Preserved original pending work and unchanged published prerequisites. Scope includes
three runtime adapters, their behavior tests, exact import rule/negative tests,
cache/setup guidance, generated operations HTML and appended historical spec notes.
Portable changes are isolated on latest collection main. No dependencies, public CLI
or report schema, numerical behavior or interruption handling were changed.
Final stable-check results and delivery state are recorded in [test.md](test.md).

## Stable verification follow-through

The unchanged candidate subsequently passed the canonical verifier with a stable
input receipt: 4482 passed, 30 skipped, 81 deselected. This closes the review’s
canonical execution condition. Final paired source/installed metadata and remote
refs are checked after native release hooks and before delivery.
