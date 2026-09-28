# Decisions and Evidence

## Restore the established initializer interface

**Decision**: Retain `cy-init-config DIRECTORY [--force]` and generate eight command-named
YAML examples from the current registered defaults.
**Rationale**: Git history establishes the interface. Central defaults prevent drift and
preserved the then-current sparse native configuration contract.
**Alternatives**: Static copied templates would require independent maintenance. Restoring
the obsolete exhaustive native parameter tree would revive removed configuration behavior.

**Supersession**: The
[native configuration feature](../003-ultralytics-config-groups/spec.md) retained the eight
command examples and added two native group files. Its shared group intentionally covers the
installed upstream defaults with original comments; its prediction group contains explicit
overrides. That later design supersedes the sparse-native-mapping rationale above without
changing the initializer interface.

## Preserve user data

**Decision**: Check all example destinations before writing, require explicit replacement,
reject symlinks/directories even with force, and preserve unrelated files.
**Rationale**: Existing edits must not be silently replaced or external symlink targets modified.
**Alternative**: Per-file collision checks can leave a partially initialized directory when
an existing example is encountered late in the sequence.

## Remove deferred annotations without weakening types

**Decision**: Remove all first-party future-annotations imports, use `typing.Self` for methods
returning their receiver, and quote self references and pandas generic types when needed.
**Rationale**: Python 3.12 supports the normal type syntax, while pandas Series subscription
exists only in stubs. The first removal attempt reproduced import-time TypeError in report
and re-inference modules; quoting only those runtime-incompatible annotations preserves typing.
**Alternatives**: Reintroducing the future import contradicts the user. Removing type parameters
would lose precision; modifying pandas or other dependencies is unnecessary and unauthorized.

## Publish the pending 0.3.0

**Decision**: Keep the package version and publish `v0.3.0` on the existing GitHub repository.
**Rationale at decision time**: Local and origin master agreed, the package declared 0.3.0,
and the latest GitHub release and tag were v0.2.0. No published 0.3.0 artifact needed replacement.
**Alternatives**: A new 0.3.1 or 0.4.0 would skip the already-prepared unpublished release.

v0.3.0 was subsequently published from the verified source. Later release automation advanced
the version; [pyproject.toml](../../pyproject.toml) is the maintained source. These facts do not
alter the historical version decision.

## Evidence and environment separation

**Decision**: Keep portable results in dated repository evidence; keep credentials, machine
paths, resource identities, and detailed local run logs in the global environment skill.
**Rationale**: Existing instructions separate product contracts from the shared stand.
Historical CPU/GPU evidence is cited with its date and is not presented as a current run.

## Include approved dependency and skill changes

**Decision**: Include the concurrent changes after the user's explicit scope confirmation.
Keep the existing upstream commits as parent-repository gitlinks, use editable paths for
development, and supply exact Git revisions for reproducible release-package installation.
**Rationale**: Editable installs support local dependency development; gitlinks retain the
approved source versions. Wheels do not consume uv source overrides or include submodules.
**Alternative**: Excluding these changes was superseded by the user's confirmation.

**Decision**: Keep one skill tree under `.agents/skills`, linked from `.claude/skills`.
Add host metadata and invocation guidance, and use the actual Spec Kit script JSON fields
and template resolver output.
**Rationale**: Shared instructions avoid divergent host copies; composed template content
preserves active overrides, and read-only analysis must not mutate the feature pointer.
