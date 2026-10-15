# Architecture contract

Allowed directions: entrypoints -> adapters/application/core; adapters -> application.ports/application.contracts/core; application.use_cases -> application.ports/application.contracts/core; core -> standard library and approved scientific validation stack. Declare peer adapter bridges explicitly. No adapters import application.use_cases or entrypoints. Every immediate child of the shipped package is classified; the retired Hydra launcher root is absent. Root/package imports have no application side effects. Old module paths are removed, not re-exported.

The [maintained module diagram](../../../docs/module-architecture.md) describes effect
ownership; [import boundaries](../../../docs/import-boundaries.md) maps current adapter
peers and SDK owners to executable contracts. The original feature's completed tasks
remain historical evidence, not an inventory of current adapters or worker targets.
