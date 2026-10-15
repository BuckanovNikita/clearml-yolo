"""GPU output never exposes the private persistent UUID."""


def test_gpu_diagnostics_replace_ids_without_changing_internal_values() -> None:
    from clearml_yolo.core.gpu_identity import identity_label, redact_gpu_ids

    identifier = "GPU-12345678-1234-1234-1234-123456789012"
    text = f"Unavailable {identifier}; retry {identifier}"
    assert redact_gpu_ids(text, {identifier: "GPU 2"}) == "Unavailable GPU 2; retry GPU 2"
    assert identifier not in redact_gpu_ids(text)
    assert identity_label(identifier) in redact_gpu_ids(text)
    assert redact_gpu_ids("GPU 2: memory unavailable") == "GPU 2: memory unavailable"
