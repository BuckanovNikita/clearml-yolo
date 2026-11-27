# ADR-0412 · Publish a version commit and annotated tag together

A PR merged into master triggers the serialized semantic-release workflow. Conventional Commit headers determine whether a new version is due. The release script checks that the source is current, permits only release metadata files in the generated commit, verifies the annotated tag and pushes the commit and tag atomically. A documentation-only change can finish without a version.

A changed remote branch or pre-existing tag blocks publication. The release neither certifies native execution nor publishes a model bundle. [Release contract](../DOCS.md#release) · [Workflow](../.github/workflows/release.yml) · [Release runner](../scripts/release.py) · [Lock guard](../scripts/release_lock_guard.py)
