# Design decisions

- Decision: Retain old strategy dispatch and add a new named strategy. Rationale: persisted trials are replay-validated and estimate keys include strategy. Alternative rejected: changing the old strategy in place.
- Decision: Separate editable selection from strict measurement profiles. Rationale: recipe and dataset gates contradict direct table control. Alternative rejected: weakening the JSON evidence compatibility function globally.
- Decision: Publish in the parent receipt acceptance path. Rationale: workers cannot establish their own successful exit and descendant cleanup.
- Decision: Embed internal precise-capacity/failure metadata as a reserved YAML comment. Rationale: one atomic replacement updates table and metadata consistently while keeping the public mapping readable. Alternative rejected: two-file publication with torn metadata states.
- Decision: Preserve exact entries on default runs and force measurements with explicit model filters. Rationale: matches the approved freshness contract; fallback is never exact coverage.
