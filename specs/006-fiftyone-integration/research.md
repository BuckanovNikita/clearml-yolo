# Research: FiftyOne Integration

- **Decision**: Persist a neutral Pydantic `EvaluationPayload` before publication. **Rationale**: exact metrics state remains adapter-independent. **Alternative rejected**: adapter rematching.
- **Decision**: reuse with prefix/schema/effective-GT key plus resolved path validation; retain original GT hash as provenance. **Rationale**: safe media and cleaned-GT identity. **Alternative rejected**: filename-only identity.
- **Decision**: factory returns no-op when disabled; only adapter imports FiftyOne. **Rationale**: disabled runs retain no dependency or state effects.
- **Supplied evidence**: parent reports pre-feature 457 passing tests and a FiftyOne 1.22.0 dependency dry-run for installed Python. This document does not claim execution of either check.
