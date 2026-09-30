# Configuration file attachment contract

## Interfaces

`resolve_config_document(document: Any, command_config: DictConfig | Mapping[str, Any] | None = None) -> Any` resolves detached data and returns only original fields. This function belongs to the apps layer.

`invocation(..., *, config_resolver: Callable[[Any], Any] | None = None)` supplies resolution to attachment handling without introducing Hydra/OmegaConf imports into clearml_session.

The shared CLI uses `resolve_config_file` with a closure over current composed configuration and returns `ResolvedConfigFile(values: Any, secrets: frozenset[str])`, a frozen adapter result carrying credential provenance. The pure resolver continues to return primitive data. `configuration_secrets` exposes existing discovery behavior. Current context includes replay/app output/output_dir derivation, preserves explicit nulls, and excludes later native normalization/routing performed inside model/task execution. Direct invocation callers without an injected resolver accept concrete files and reject interpolated or mandatory-missing (`???`) inputs with actionable guidance. No CLI or configuration schema additions are required.

## Observable behavior

- Resolve active YAML/JSON values in nested mappings and lists before Configuration Object
  attachment and before sanitation.
- File roots override corresponding command roots as whole values; unrelated command fields never appear in the published file.
- Preserve resolved scalar and collection types, YAML comments, source bytes and original-field topology.
- Preserve comments containing interpolation examples unless existing credential sanitization requires redaction.
- Keep unredacted execution and sanitized storage copies separate with unique paths; replay
  files returned by ClearML obey the same preparation rules. Resolved secrets copied through
  aliases under otherwise innocuous keys must also be redacted. Confidential error categories
  distinguish resolution/preparation failure without printing configuration contents or values.
- Return the original execution input path for files without interpolation even when credential sanitization requires a separate upload copy; retain existing replay behavior.
- Fail on unknown references, cycles, unknown resolvers, missing mandatory values and unavailable
  environment variables; never attach unresolved active content.
- Registered resolvers receive unmodified resolved arguments; escaped literals/direct aliases preserve meaning. Tuple outputs are recursively normalized/validated; unsupported set/object outputs and resolver-emitted active interpolation are rejected. Mixed escaped literals and active references, including embedded aliases, preserve their respective semantics. Computed node targets such as `${${key}}` are rejected confidentially because credential provenance cannot be established safely; nested resolver arguments such as `${oc.env:${variable}}` remain supported.
- Sensitive command-context and environment reference values retain redaction provenance when aliases use innocuous keys. Provenance records the exact value consumed without reevaluating noncached custom resolvers.
- Resolved execution copies live beside their source for relative-path semantics and are uniquely named, tracked and cleaned up.
- Retain existing Configuration Object identifiers, single-task ownership and verified
  completion guarantees. Do not publish configuration files as artifacts.

Editable local exports and historical task files are outside this attachment contract.
