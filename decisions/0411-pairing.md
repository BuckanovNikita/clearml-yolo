# ADR-0411 · Verify CY and cy-queue together before an interface or dependency release

cy-queue consumes CY's interface and can resolve a different package than the one a maintainer intended to test. The paired check installs both source checkouts into an isolated environment, verifies editable distribution versions and locations, then runs the queue checks, tests and command help. It requires a clean queue checkout containing the fetched default branch.

The check compares the source identities again at exit. Pairing evidence belongs to the tested versions. Running CY alone cannot establish the sibling's compatibility. [Pairing task](../Taskfile.ops.yml) · [Metadata checks](../scripts/paired_metadata.py) · [Queue boundary](0317-queue-boundary.md)
