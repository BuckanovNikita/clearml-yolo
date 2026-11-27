# ADR-0410 · Tie change and release acceptance to identified inputs

Change acceptance starts on a clean committed tip, checks the tree, probes the integration environment, and runs coverage and live integration. It checks cleanliness and tip identity again at completion. An unavailable cluster yields a deferred result that blocks acceptance until run or explicitly waived.

Release validation extends this with the specified [native scenarios](0409-native-validation.md) and FiftyOne checks. Release acceptance also runs the [paired check](0411-pairing.md). PR review, automated tagging and a local static verification each answer different questions from these live stages. [Acceptance tasks](../Taskfile.ops.yml) · [Live requirements](../DOCS.md#live-test-environment) · [Status definitions](../AGENTS.md#checks)
