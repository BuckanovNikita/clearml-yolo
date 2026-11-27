# ADR-0418 · Track a change from Linear through human merge

The project ties implementation, verification and release evidence to a Linear issue. A task branch carries the change to a pull request whose title ends with the SIP identifier. A human merges the accepted change into master. Triage status records who can act on an issue, while branch and PR evidence identifies what was actually reviewed.

A maintainer can trace a feature's current ADR to its contract and return to the issue or Git for prior decisions. A merged PR can trigger the [code release](0412-code-release.md). Release evidence belongs to the issue rather than the living feature record. [Delivery agreement](../AGENTS.md#delivery-and-release) · [Release trigger](../.github/workflows/release.yml) · [Triage decision](https://linear.app/sip-ds-team/issue/SIP-234)
