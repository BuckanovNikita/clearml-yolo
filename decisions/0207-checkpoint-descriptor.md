# ADR-0207 · Bind detector identity and class order to checkpoint bytes

A copied non-YOLO checkpoint carries its detector family, preset, ordered classes and preprocessing inside the native archive. CY computes a digest of the resulting bytes and writes a descriptor companion. A reader rebuilds the descriptor from the checkpoint, checks any accompanying descriptor against it, and rejects contradictory model selections. A legacy file without embedded metadata has no inferred descriptor.

The technical reference directs users to keep both the model and identity sidecars with the checkpoint. The model reader can reconstruct the descriptor from a copied checkpoint alone, and the identity reader returns an absent identity when its companion is missing. Downstream consumers can still require a model label or provenance. [Detector contract](../DOCS.md#detector-families) · [Open discrepancy](https://linear.app/sip-ds-team/issue/SIP-345)

[Training output](../docs/commands/cy-train.md) · [Descriptor writer and reader](../src/clearml_yolo/adapters/storage/checkpoint.py) · [Identity companion](../src/clearml_yolo/adapters/storage/identity.py) · [Copy, tampering and compatibility cases](../tests/test_checkpoint_descriptor.py)

See [weight selection for prediction](0111-weight-selection.md).
