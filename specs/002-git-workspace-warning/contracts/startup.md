# Startup warning contract

The nine experiment commands listed in [the specification](../spec.md) call the
shared launch boundary, including help/config inspection. A read-only
`git -C DIRECTORY rev-parse --is-inside-work-tree` probe receives no inherited
`GIT_*` overrides and has a five-second timeout. Only a successful `true` response
suppresses this warning. Missing Git, timeout, OS errors, nonzero exit and other
responses emit one warning explaining unverified Git control and how to version
configuration. Raw Git stderr is not exposed. Git state is never written.

The warning belongs on stderr and in existing captured logs. It precedes Hydra
composition/chdir and all multirun jobs. It is independent of CY_HOME, repository
cleanliness, commits, remotes and the installed package's source. Queue administration,
config export, deduplication and programmatic workflow calls do not acquire this
warning; queued pipeline processes use their recorded launch cwd normally.
