# ADR-0304 · Restore executable settings from the Agent task snapshot

A cloned task can run on another host with different launch arguments and output roots. The command needs a stable view before it starts work.

**Decision.** Read the Agent task configuration and parameters once, restore the canonical `run` settings, and apply the command's validation and [workspace containment](0309-workspace-containment.md) to the effective settings. YOLO also handles native `General` parameters, preserving `batch=null` for machine-local lookup and compatibility with historical tasks.

**Consequences.** An invalid saved `run` fails validation. A missing legacy `run` can fall back to composed settings. The technical reference calls `run` the only replay input. Ground-truth conversion and report generation can also read [Agent-supplied configuration attachments](0326-configuration-attachments.md); training prohibits remote replacement of its prepared dataset file. Display-only differences and asset provenance do not reconstruct the command. [Contract discrepancy SIP-354](https://linear.app/sip-ds-team/issue/SIP-354). Tests that simulate Agent state exercise CY's mapping and validation; operational replay requires an actual Agent.

[Snapshot, replay and compatibility](../src/clearml_yolo/adapters/clearml/session.py) · [Direct command integration](../src/clearml_yolo/entrypoints/hydra/common.py) · [Agent scenarios](../tests/test_agent_replay.py) · [Replay contract](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/2e4b5f2fa3c3e9dc90920af75fe3edb8e346bcd0)
