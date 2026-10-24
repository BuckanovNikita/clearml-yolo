# Verification records

A successful receipt identifies its schema/check kind, exact input fingerprint, successful command results and private log references. It is written atomically only if every check succeeds and a second input snapshot matches. Missing/malformed evidence cannot authorize reuse. Application and documentation receipts are independent.

A release attempt binds source HEAD, expected next version and expected release-file contents. Reuse requires a validated attempt and exact generated release child; existing lock/ownership/tag checks retain authority.

Mutation evidence identifies selected source/test/dependency state, outcomes and each survivor's reviewed disposition. Incomplete execution never becomes accepted evidence.
