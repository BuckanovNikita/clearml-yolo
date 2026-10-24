# Research — 2026-10-24

- Decision: preserve the existing release helper's parent/path/version/changelog/ownership checks and extend it with receipt mapping. Inspection shows current hooks independently repeat pytest. Alternatives: bypassing hooks or trusting commit messages would lose evidence and are rejected.
- Decision: use [safetensors safe_open](https://huggingface.co/docs/safetensors/index) with NumPy and translate format errors. Current validator requires a tensor key but permits zero-element tensor shapes; retain that distinction. Authentication, bootstrap, process ownership and workbook recovery stay unchanged.
- Decision: use [mutmut](https://mutmut.readthedocs.io/en/latest/) 3.8.x, explicit core selection and offline tests. Function/module glob selection and incremental execution support bounded acceptance; exit status alone is insufficient. No covered-lines filter hides untested mutants.
- Decision: configured import-linter rules become the sole authority for supported layering/peer/SDK ownership. Augment graphs with statically resolvable dynamic edges; retain AST-only effects/initializers/targets/allowlists and use graphlib for all cycles.
- Decision: content identity includes installed file bytes and editable source bytes, not just versions or RECORD metadata. Fingerprint cost is measured separately; stale evidence always reruns checks.
