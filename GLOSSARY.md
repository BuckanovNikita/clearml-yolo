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

**Change acceptance**: Verification of a clean committed tip, including the complete suite and the live checks run on CPU against a test environment the run deploys itself. Documentation-only changes need no live part.

**Test environment**: One Kubernetes namespace `cy-it-<id>` that the project creates for live tests or an agent run, with its own quota, its own ClearML server and its own FiftyOne database, reached through `kubectl port-forward` and deleted by whoever created it. No shared stand is involved.

**Release acceptance**: Change acceptance plus GPU checks, the real-run gate and the paired release check, required before a version is delivered.

**Deferred verification**: A required check that could not run because a resource was temporarily unavailable, such as an unavailable cluster or a busy GPU. It blocks acceptance, integration and release until it runs.

**Waived verification**: A check the user explicitly excused for this environment. It never blocks and is reported as waived, not as passed or deferred.

**Release-commit check**: The reduced checks applied only to the version commit that carries the new version, changelog and lock entry.

**Paired release check**: Verification that the CY and cy-queue versions proposed for delivery install and pass the queue suite together. It is distinct from the release-commit check; the bare phrase "release check" is not used.
