# ADR-0014 · Keep native comparison diagnostics in a local archive

Re-inference can produce backend settings and diagnostic tables alongside source-derived media. CY can gather native CSV, JSON, text and YAML files under relative names in a role- and split-specific ZIP. It parses and sanitizes structured JSON and YAML before writing them. Image files stay out of the archive.

The archive gives a reviewer a local account of native execution while keeping the main [comparison](0140-comparison.md) inputs and publications independently identifiable. [Archive writer](../src/clearml_yolo/adapters/storage/native_archive.py) · [Comparison caller](../src/clearml_yolo/application/use_cases/compare.py) · [Archive cases](../tests/test_comparison_assemble.py) · [Containment cases](../tests/test_project_output_containment.py)
