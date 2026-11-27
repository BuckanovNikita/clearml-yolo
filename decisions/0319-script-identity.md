# ADR-0319 · Publish the package checkout as ClearML execution metadata

The launch directory may contain experiment inputs while the installed package comes from a different checkout. Raw arguments and an uncommitted diff could disclose local information.

**Decision.** For a local SDK task CY writes the command module as its entry point, a relative working directory and an empty diff. If the installed package comes from a source checkout, CY also reads its sanitized origin, branch and commit. It checks publication by fresh SDK readback. A remote Agent retains its supplied script.

**Consequences.** A wheel installation can have a usable entry point without repository identity. Missing or changed fields after a local write cause a failure. The separate [launch directory warning](0325-launch-checkout.md) does not supply the recorded package identity.

[Source lookup and readback](../src/clearml_yolo/adapters/clearml/script.py) · [Checkout metadata cases](../tests/test_clearml_script.py) · [Execution metadata](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/5d89443b8e1a8e63d21b3c318b2cab0242c4e418)
