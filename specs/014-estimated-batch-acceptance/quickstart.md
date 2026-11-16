# Validation guide

Run focused product tests for batch profiles, probe requests/execution, search and
backend probes, followed by project static checks. Use real JSON snapshots and CPU
synthetic samples to verify pipeline execution without claiming GPU capacity.

For live validation, adopt the coordinator-owned environment using the native
lifecycle exports without logging credentials. Use the frozen prepared 160/40/40
corpus, explicit project/tags and a new output directory. Run one selected native
Severstal GPU scenario through the existing pytest options only after host admission.
Keep the scenario's existing timeout and optional 8 GiB reserve; retain capacity,
canonical inputs, optimizer observations, downloaded checkpoint/artifact hashes and
readback evidence. Clean disposable outputs only after downstream consumers finish.
