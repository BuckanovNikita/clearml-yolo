# Validation scenarios

1. Configure a test-owned shared root and host-local coordination directory in TOML;
   export CY_QUEUE_CONFIG in each participating process. Run `cy-queue config` and help.
2. Submit labeled test workloads from two private workspaces under different Unix users.
   Confirm both list the same jobs and use stable job-number references.
3. Reorder pending work; verify stale revision rejection and owner-only restricted actions.
4. Archive finished jobs, inspect archive/all views, restore and restart both clients.
5. Verify restrictive-umask public access and denial of other-user private snapshot/log reads.
6. Check console chunks, errors, reports and TUI contain no opaque identifiers while JSON,
   provenance and retained original bytes remain exact.
7. Run the acceptance commands in [plan.md](plan.md), record evidence and remove only
   test-owned processes, accounts/groups and resources.
