# Data model: Configuration publication

- **Source document**: Original YAML/JSON fields, values and YAML comments; source bytes are immutable during preparation.
- **Command context**: Current composed command mapping, read at publication time after replay and routing updates.
- **Resolution root**: Detached command context with file root keys replacing command root keys as whole values. Strict resolution supports nested structures and registered resolvers.
- **Resolved document**: Projection of original file fields only, preserving typed values; used for an unredacted execution copy when needed.
- **Upload document**: Resolved document with credential sanitization and existing comment protection; distinct from execution data.
- **Invocation state**: Existing task/publication lifecycle plus optional `Callable[[Any], Any]` resolver callback. No SDK ownership changes.

## State transitions and invariants

Source → resolve with current context → project original fields → execution copy and sanitized upload copy → connect/upload → existing verification/finalization.

Any resolution, serialization or publication failure transitions through existing invocation failure handling. No unresolved active document reaches the ClearML publication boundary. Original files survive failures. Files requiring no interpolation transformation retain the existing original-return-path contract, even when credential sanitation creates a separate upload copy.
