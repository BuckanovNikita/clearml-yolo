# Paired release verification, 2026-10-30

## Current released sources

The latest default branches were fetched and inspected. Current CY is **0.44.3**,
commit `02e2d50ad9f3dd6ea619f69adfe5ffc45c32f361`; current cy-queue is **0.1.5**,
commit `397753c123f379ade50f06a2babf5e4b1476b9d2`.
Queue's declared CY range is `>=0.38,<0.45`, which includes the proposed performance
patch version 0.44.4. No queue source or dependency bound has been changed.

Verification uses isolated source checkouts and a physically copied environment.
Normal editable installation includes both source projects and the existing approved
external packages, without `--no-deps`; no operational installation is modified.
Copied console entrypoints were relocated before execution, and installed origins,
source versions and distribution metadata were explicitly matched to these checkouts.
Digital-metrics remains at approved revision
`6e801be1564dce458294eb23592cc1aa0939c4d9`; report-generator remains at
`d10aa395d08f738e92e04e076cee93b3a993bf8f`.

Executed from the queue checkout using the isolated CY environment:

```bash
UV_LINK_MODE=copy uv pip install --python ../paired-env/bin/python \
  -e ../paired-cy-current -e . \
  -e ../repo/external/digital-metrics -e ../repo/external/report-generator
uv pip check --python ../paired-env/bin/python
CUDA_VISIBLE_DEVICES= uv run --frozen --no-sync --project ../paired-cy-current python -m pytest -q
uv run --frozen --no-sync --project ../paired-cy-current python -m ruff check .
uv run --frozen --no-sync --project ../paired-cy-current python -m ruff format --check .
uv run --frozen --no-sync --project ../paired-cy-current python -m mypy .
uv run --frozen --no-sync --project ../paired-cy-current lint-imports
CUDA_VISIBLE_DEVICES= uv run --frozen --no-sync --project ../paired-cy-current cy-queue --help
```

Normal resolution and pip consistency passed. Ruff and formatting passed (90 files),
strict mypy passed (69 source files), and both import contracts passed. The full queue
suite passed **518 tests**, with **7 physical-GPU cases deselected** and 19 existing
Pydantic deprecation warnings, in 132.71 seconds. Help and explicit source/installed
metadata checks passed. These are CPU/process/integration outcomes, not physical GPU
scheduling evidence.

## Proposed release sources

The integrated application source was copied after the parent's source freeze,
including the new `worker_pool.py` and `batch_estimate_worker.py` modules. The
snapshot changes only the root version tokens in `pyproject.toml` and `uv.lock`
to the hook-confirmed performance patch **0.44.4**. Queue remains the unchanged
latest **0.1.5** source above. No dependency bound change is necessary.

The copied snapshot contains 826 repository files. Its 342 runtime source files
have the aggregate SHA-256
`3b2b7b2888067c950749d5b068f33dba629a2c77f82b47d6764911caab9443fc`.
The 558 runtime, test, verification-script and static/import configuration files
have aggregate SHA-256
`bbe7b4ea5b1670d09eb41aead1893108c596f5a9a684fa0772fcd6ae75267096`.
Each aggregate hashes the JSON serialization of the sorted path-to-SHA-256 map;
symlinks hash the `symlink:` prefix and link text. The untracked task evidence
`pair-proposed-source-inventory.json` retains every individual source/snapshot
hash. `pair-source-verify.py` compares implementation, tests, check tooling and
root metadata, also detecting added code/test/script files. Its pre-version
comparison passed for all 560 selected files with no differences.

Executed from the queue checkout, against the same isolated copied environment:

```bash
UV_LINK_MODE=copy uv pip install --python ../paired-env/bin/python \
  -e ../paired-cy-proposed -e . \
  -e ../repo/external/digital-metrics -e ../repo/external/report-generator
uv pip check --python ../paired-env/bin/python
CUDA_VISIBLE_DEVICES= uv run --frozen --no-sync --project ../paired-cy-proposed python -m pytest -q
uv run --frozen --no-sync --project ../paired-cy-proposed python -m ruff check .
uv run --frozen --no-sync --project ../paired-cy-proposed python -m ruff format --check .
uv run --frozen --no-sync --project ../paired-cy-proposed python -m mypy .
uv run --frozen --no-sync --project ../paired-cy-proposed lint-imports
CUDA_VISIBLE_DEVICES= uv run --frozen --no-sync --project ../paired-cy-proposed cy-queue --help
python3 ../pair-source-verify.py ../repo --before-version-commit
```

Normal dependency resolution passed with installed CY **0.44.4** and queue
**0.1.5**, and pip consistency passed for 286 installed packages. Explicit checks
matched source versions, distribution versions, editable origins and imported
modules to the two isolated checkouts; both external revisions remain unchanged.
Ruff and formatting passed (90 files), strict mypy passed (69 source files), and
both import contracts passed. The full queue suite passed **518 tests**, with
**7 physical-GPU cases deselected** and 19 existing Pydantic deprecation warnings,
in 138.10 seconds. Help passed. This is the proposed-version pair acceptance;
physical multi-GPU execution remains unverified.

## Queue threshold follow-up

The user's additional queue threshold request produced compatible queue **0.1.6**.
Before commits, normal resolution paired its frozen source with the proposed CY
0.44.4 snapshot. That pair passed **544 tests**, with seven physical-GPU cases
deselected and 19 existing Pydantic warnings, in 133.74 seconds. Ruff/format, strict
mypy, both import contracts, help, package consistency and explicit source/installed
origins and versions passed. Queue's 73 source/test/check/metadata files have aggregate
SHA-256 `144e304da02e2b14fc2e9b25f38c7742a89b72c7eaf35bdae732be622c203af6`.
The final queue commit preserves those files exactly; subsequent changes were dated
documentation and acceptance records.

## Final committed versions and source checks

The CY hook produced release **0.44.4**, commit
`fb2c6ff4bb5bbad936958e3651712b05b8c11a9a`, from contributor commit
`80615fe4e090beb915950cdc9972e72e04959086`. The annotated `v0.44.4` tag object is
`969f800b4a7de8541c75ff49fa4479214fb6adeb`. Queue **0.1.6** is committed at
`2fbaed25fa7c572757d30cb9b1b343d22e645e3a`. Both source versions, installed
versions, editable origins and imported module locations match the actual release
checkouts. Queue retains `clearml-yolo>=0.38,<0.45`; approved external revisions
listed above remain unchanged.

After the CY version commit, the parent updated queue guidance, including packaged
`operations.md` and `operations.html` tutorial assets. The old proposed inventory
comparison correctly reports those **two documentation asset differences**; the
other 558 selected source/test/check/metadata files match exactly. This is not an
exact match to the earlier complete source/assets snapshot. No Python runtime,
test or verification-script source changed. The final check includes the updated
assets before the documentation follow-up commit.

The fresh inventory captures 830 repository files, including 560 selected
source/test/check/metadata files with aggregate SHA-256
`b0cc692d911b1cc0d9c7e0a5b408ac868bf444fc575996192ba8d236640ad849`.
The runtime/source-assets aggregate is
`7e8fd4c9df2f103b5ff359b4ce22699768e23e636a2e3e4039e0213fbfbf9938`.
Task-local `paired-env/evidence/final-cy-source-inventory.json` and
`queue016-source-inventory.json` retain individual hashes. Their verification helpers
passed all 560 CY and 73 queue selected files with zero differences after installation.

Executed from the committed queue checkout, using the isolated environment explicitly:

```bash
UV_LINK_MODE=copy uv pip install --python ../paired-env/bin/python \
  -e ../repo -e . \
  -e ../repo/external/digital-metrics -e ../repo/external/report-generator
uv pip check --python ../paired-env/bin/python
export UV_PROJECT_ENVIRONMENT=../paired-env
CUDA_VISIBLE_DEVICES= uv run --frozen --no-sync --project ../repo python -m pytest -q
uv run --frozen --no-sync --project ../repo python -m ruff check .
uv run --frozen --no-sync --project ../repo python -m ruff format --check .
uv run --frozen --no-sync --project ../repo python -m mypy .
uv run --frozen --no-sync --project ../repo lint-imports
CUDA_VISIBLE_DEVICES= uv run --frozen --no-sync --project ../repo cy-queue --help
../paired-env/bin/python ../paired-env/evidence/verify_final_pair.py
../paired-env/bin/python ../paired-env/evidence/verify_final_cy_source.py
../paired-env/bin/python ../paired-env/evidence/verify_queue_source.py
```

Final normal resolution and pip consistency passed for 286 installed packages.
Ruff/format passed (93 files), strict mypy passed (69 source files), and both import
contracts passed. The full queue suite passed **544 tests**, with **7 physical-GPU
cases deselected** and 19 existing Pydantic warnings, in **131.87 seconds**. Help,
explicit installed/source identities and both source inventories passed. Logs and
identity JSON are retained under task-local `paired-env/evidence/final-pair-*`.
The main verification environment, queue source and approved external source checkouts
were not modified by this companion refresh.

The committed-version pairing gate is satisfied. The parent still owns canonical
CY acceptance, the documentation follow-up commit, release publication and
verification of public release refs. These CPU/process/integration checks do not close native single-GPU
confirmation/timing or physical multi-GPU verification gaps documented separately.

CY master was subsequently pushed and remotely verified at
`ffd294c3ac3240a282f87b76b7f40fa6dd963a44`, with the annotated version tag and peeled
release commit above. Queue main was remotely verified at its recorded 0.1.6 commit.
The final selected source inventories remained unchanged through these commits and
pushes. The later release-record closure changes only task evidence and the ledger.
