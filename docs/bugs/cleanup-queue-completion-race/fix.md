# Companion completion-race fix — 2026-11-02

**Status**: applied and delivered in queue 0.1.7; CY runtime unchanged.

The owning queue storage transaction now compares the observed public revision and
state before recovery. Runtime revalidates the full retained claim after dead
liveness; released or changed claims defer to a fresh observation. Genuine lost
executions and unchanged terminal records with retained dead claims still recover.
Signals, cleanup, leases, deadlines, public protocols and dependency bounds remain.

The [queue implementation](https://github.com/BuckanovNikita/cy-queue/commit/b976789301d814a4249d3683739b8d6918819a73)
and [owning plan/architecture](https://github.com/BuckanovNikita/cy-queue/tree/4e539f227f06e600d95753e27049baf6df517398/docs/bugs/refresh-completion-race)
record both RED stages, minimal source scope and verified acceptance. The original
assessment's stale-publication mechanism was extended for the reviewer-confirmed
same-revision claim-release ordering before final acceptance. Original failed
evidence and the initial fix-first review remain preserved.
