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

## Final committed pair

The final version commit has not yet occurred. After hooks produce its version,
the final source must match the captured implementation and root metadata, then
normal installation and the final paired check must be refreshed before pushing.
Run the inventory comparison above without `--before-version-commit` for the
committed 0.44.4 metadata. Any implementation difference invalidates this frozen
pair's evidence and requires verification of the changed source.
