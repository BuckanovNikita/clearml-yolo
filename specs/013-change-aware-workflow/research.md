# Design decisions

- Use staged paths for hooks and the latest commit for clean post-commit verification;
  branch history would retrigger product work on prose follow-ups.
- Use explicit collection of candidate unit files and filtered node IDs, never testmon's
  implicit fallback for test-only changes. Read dependency history read-only; report
  missing coverage as a gap rather than widening the suite.
- Task owns hygiene and staging; prek remains a serial dispatcher plus commit messages.
- Keep the existing semantic-release pre-commit build boundary for final-version pairing;
  performing pairing before version preparation could validate the wrong metadata.
- Preserve supported live product gates; remove hardware-only obligations explicitly
  named in the approved plan. Temporary outages cannot silently waive supported gates.
