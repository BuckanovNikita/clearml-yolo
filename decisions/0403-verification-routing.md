# ADR-0403 · Route verification by the change set

The verifier first runs the whole-tree checks and then classifies the selected diff. Automatic scope chooses staged paths, then working changes, then the latest commit. Prose goes through the static route. Product sources go to the affected unit suite. Changes confined to tests can use bounded selection with recorded dependents.

A missing dependency record can produce a targeted verification gap. A clean-tip run on a final prose commit does not establish coverage of earlier product commits on the same branch. Select additional checks from the merge-base diff when their inputs extend beyond the routed change set. [Verification tasks](../Taskfile.yml) · [Selection algorithm](../scripts/verification.py) · [Bounded collection](../scripts/verification_collection.py)
