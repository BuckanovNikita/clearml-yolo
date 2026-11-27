# ADR-0400 · Install the experiment runtime before launching a command

The package declares one Linux experiment environment with a supported Python range and console entry points. Installation resolves native and Python dependencies up front. Process supervision requires Linux capabilities, and experiment commands need ClearML with remote storage. Configuration export and other no-task tools have their own requirements.

The dependency ranges used for an installation from Git can resolve different versions from the contributor lock. A successful locked installation therefore establishes one environment. An operator can consult the installation page for environment setup and weight preparation. [Installation guide](../docs/installation.md) · [Distribution metadata and scripts](../pyproject.toml) · [Process capability tests](../tests/test_process_capabilities.py)
