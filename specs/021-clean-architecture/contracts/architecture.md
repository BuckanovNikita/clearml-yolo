# Architecture contract

Allowed directions: entrypoints -> adapters/application/core; adapters -> application.ports/application.contracts/core; application.use_cases -> application.ports/application.contracts/core; core -> standard library and approved scientific validation stack. Declare peer adapter bridges explicitly. No adapters import application.use_cases or entrypoints. Both shipped roots are linted; every immediate child is classified. Root/package imports have no application side effects. Old module paths are removed, not re-exported.
