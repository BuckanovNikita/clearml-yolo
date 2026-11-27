# ADR-0408 · Derive a reproducible detection corpus from Severstal masks

The native acceptance scenarios require identifiable images, detection boxes and reproducible splits. The corpus tool reads an existing local Severstal download, turns connected mask components into boxes, and writes full and smoke ground truth tables plus a manifest. Records include source identities and hashes. The derived boxes are CY's interpretation of the masks.

Verification checks the manifest, CSV bytes and, when requested, the selected image bytes. Preparing fixtures alone makes no claim about execution or model quality. [Corpus builder and verifier](../scripts/severstal.py) · [Consumer](../tests/integration/test_severstal_gpu.py) · [Native scenario contract](../DOCS.md#live-test-environment)
