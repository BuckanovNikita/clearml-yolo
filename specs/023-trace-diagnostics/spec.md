# Readable TRACE diagnostics

Status: implementation in progress. Requested 2026-10-10.

## User scenarios and testing

1. An operator enables `LOGURU_LEVEL=TRACE` and captures Bash output. Each expensive
   operation identifies its stage, parent, elapsed time and outcome. Existing default
   DEBUG/INFO output and caller sinks retain their behavior.
2. A command appears stalled during native execution or publication. Every 30 seconds
   the operator sees each thread's deepest active operation and parent stage. Every
   60 seconds changed thread-stack snapshots reveal location without locals or source.
3. A failure or interruption occurs. Diagnostics retain the original exception and
   completion semantics; monitoring lasts through task closure and cleanup.

## Requirements

- FR-001: Opt-in concise START/DONE/FAILED/INTERRUPTED events include monotonic duration,
  short operation/parent IDs, PID and task ID when known. Summaries allow stages, splits,
  artifacts, sanitized destinations, counts/dimensions, cache decisions and devices.
- FR-002: Exclude configurations, rows, tensors, secrets, arbitrary representations,
  locals and source text. Aggregate loop progress; never trace every image/detection.
- FR-003: One lazy process-local daemon monitor; fork-safe state and bounded shutdown.
  Capture stderr before ClearML interception. Watchdog output bypasses Loguru and takes
  no application locks. Prioritize active-operation threads, group identical stacks,
  suppress unchanged snapshots; cap at eight groups and twelve frames, report truncation.
- FR-004: Cover command/configuration startup, filesystem initialization, GPU waits,
  native imports, task creation, dataset/cache/export, training/prediction/DDP,
  evaluation/calibration/comparison, reports, downloads/uploads and model verification.
- FR-005: Separate post-report spans for FiftyOne preparation, lock acquisition, sample
  writes, evaluation registration; GPU synchronization; final CSV assembly/uploads;
  model-upload waits; ClearML flush/close; completion/failure marking; temporary cleanup.
  Emit `command.return` after application cleanup.
- FR-006: Diagnostics cannot change application exceptions/outcomes. No retries or
  operational timeouts. Scientific core remains logging-free; workflows use a port.
  Normal emission preserves termination signals; terminal logging during exception
  unwinding preserves the original exception over secondary sink failures.
  Mandatory cleanup completes before a diagnostic-emission interruption propagates;
  resource ownership is established before acquisition spans emit their terminal record.
- FR-007: Persist dependency-aware parallel planning/collaboration instructions globally
  and in project guidance, preserving existing content and the CLAUDE.md symlink.

## Success criteria

Controlled blocked-operation and subprocess tests establish readable correlated events,
watchdog survival across intercepted stderr/blocked sinks/stalled SDK closure, bounded
stack output, suppression, sequential invocation cleanup, exception preservation and
default compatibility. Production intervals remain 30/60 seconds. Applicable static,
unit, architecture, documentation and native checks pass before Git-tag-only release.

## Assumptions and limits

This improves diagnosis, not the unconfirmed remote hang. Python scheduling may stop
during native-code stalls. No new logging service or log file is required. Existing
caller sinks are authoritative for ordinary events; watchdog writes directly to the
captured stderr destination. Native checks use the existing approved dependencies.
