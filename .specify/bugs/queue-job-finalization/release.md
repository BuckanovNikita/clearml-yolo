# Queue finalization release verification

Date: 2026-10-15. Outcome: application **0.30.2** and portable guidance **0.2.4**
published through annotated Git tags. No deployment, GitHub Release object,
package publication or release-asset upload was performed.

## Application delivery

- Source commit: `427781f549dd64ec540a48867aa40226fcc9bd5d`.
- Checked version commit: `a22157dc787d91b1324551892d311706bc8572c6`.
- Annotated `v0.30.2` object: `ad2a496976fde7f3bf614e1f2797632b5ed12921`.
- Atomic push published `master` and `v0.30.2`; remote branch, tag object and peeled
  commit matched local refs. Subsequent evidence-only commits do not move the tag.

The source commit and automatic version commit passed their mandatory hooks,
including full pytest, Ruff, strict mypy, Vulture and import contracts. The earlier
parent suite and independent/native checks are detailed in [test.md](test.md) and
[review.md](review.md). No production source changed after that review.

Built both wheel and sdist from a clean archive of `v0.30.2`. Each installed into a
fresh environment outside the checkout, reported version 0.30.2 from its own
site-packages, passed all 12 command helps and Linux supervision/new-module probes.
These application installs reuse the prepared locked dependencies. Temporary
build and install environments were removed. Release metadata comparison confirmed
only the root version changed in pyproject/lock metadata; dependencies and approved
external sources are unchanged.

The exact local `[tool.uv.sources]` block was preserved, absent throughout commits
and hooks, and restored unstaged. The unrelated grid-search document and concurrent
training-guide/queue-logging history were preserved.

## Companion guidance delivery

- Collection commit: `ce33ce5ef1ba1fa6470399d028835f295b90f389`.
- Annotated `v0.2.4` object: `7b8a221cfee04c79c9f19661e248ffaec5ba1697`.
- Atomic push published `main` and `v0.2.4`; remote branch, tag object and peeled
  commit matched local refs. The configured corp-skills remote redirected to its
  renamed custom-opencode-skills repository without a ref mismatch.

Six task-owned paths cover usage/evaluation, architecture/evidence and collection
version/changelog. Markdown, metadata, discovery, links, no-impact architecture and
fresh behavioral evaluation passed; the integrated independent review found no
blocking issue. Installed skill copies were not changed. See the companion
verification record dated 2026-10-15 for its initial and final checkpoints.

## Operational scope and limits

Upgrade the installation and restart queue workers before submitting jobs with the
new behavior. Existing frozen queue snapshots require resubmission after an
installation change. Historical failed tasks were not altered.

Completed queued tasks now finalize independently of guardian cleanup. Training
uses the allocated GPUs; acknowledged training completion releases all reservations
except the first inference GPU. Uncertain relevant cleanup keeps remaining capacity
quarantined. Required computation/publication failures retain their failure status.

Real CPU and queued single-GPU training, publication, forced downloads, model reload
and cleanup passed. Physical multi-GPU contraction/NCCL and two-user/two-host NFS
were not exercised. Real synthetic-GPU lock tests cover reservation concurrency;
they do not establish physical multi-GPU timing. The original remote incident was
not rerun. Metrics/report/comparison and compiled execution were outside the scoped
native acceptance, and target OpenCode/DeepSeek execution was not available.
