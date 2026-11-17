# Experiment identity

Terms separate what executes from what was observed or produced.

## Language

**Canonical run**: The complete frozen executable inputs for one experiment, including explicit selectors and null values. It is the replay input, not a summary of observed settings.

**Provenance**: Evidence of input, model and code origin, including resolved assets and hashes. It supplements the canonical run without replacing it.

**Scientific result**: A prediction, metric, comparison or report tied to its source objects, model and evaluation context; publication and visualization are separate outcomes.

**Invocation owner**: The execution responsible for one experiment's task, publications and owned descendant cleanup.

**Identity footer**: The readable model identity and source links placed after a report's data, leaving table headers in place; exact identifiers stay in provenance.

# Verification and release

Terms separate what a check establishes from when it is required.

## Language

**Development verification**: Static checks and the tests affected by a change, run on the current working copy. It establishes nothing about native GPU execution, ClearML publication or the queue.

**Change acceptance**: Verification of a clean, unchanged committed tip: static checks, the complete unit suite with coverage and the non-GPU live tests against a test environment the run creates itself.

**Release acceptance**: Change acceptance plus the single-GPU Severstal suite, the FiftyOne native database tests, a mutation report against `origin/master` and the paired release check.

**Test environment**: An isolated set of ClearML and FiftyOne services that the project creates for live tests and that whoever created it deletes. No shared stand is involved.

**Deferred verification**: A required check that could not run because a resource was temporarily unavailable, such as an unavailable cluster or a busy GPU.

**Waived verification**: A check the user explicitly excused for this environment; it is reported as waived, never as passed or deferred.

**Paired release check**: Verification that the CY and cy-queue versions proposed for delivery install and pass the queue suite together.
_Avoid_: release check
