# Implementation Plan: Editable batch sizes

Branch: `012-editable-batch-sizes`. Specification: [spec.md](spec.md).

## Summary

Implement the approved user plan with pure versioned search and table selection, storage-owned YAML effects, and training/CLI integration. Preserve JSON replay and internal strict compatibility.

## Technical Context

Python compatibility remains project-declared >=3.12.13,<3.14. Reuse Pydantic records, ruamel.yaml round-trip parsing, native file locks and atomic replacement. No new dependency or upstream source changes. CPU unit tests use isolated stores and injected probes; live evidence remains distinct.

## Constitution Check

Typed interfaces and explicit effects; core owns selection/search, storage owns I/O, integration owns GPU discovery and training resolution. CLI owner publishes only accepted worker results. Existing import boundaries and strict checks remain. No new specification process or release authorization. Rechecked after design: no exceptions required.

## Project Structure

- `core/batch_estimation.py`: versioned small-batch search.
- `core/batch_sizes.py`: table records and exact/fallback selection.
- `adapters/storage/batch_sizes.py`: strict round-trip YAML and atomic updates.
- `adapters/integrations/batch_lookup.py`, `batch_resolution.py`: training lookup/provenance.
- `entrypoints/batch_estimate.py`, `options.py`: freshness/publication/listing and fixed workload.
- `tests/test_batch_*.py`: behavioral evidence.

## Execution

Search, table storage, and training integration are bounded parallel tasks with disjoint write ownership; training depends on table API. Parent implements CLI and documentation. Integration precedes final checks and independent review. No pushes. Deferred required checks block acceptance/delivery.
