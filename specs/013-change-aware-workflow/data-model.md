# Workflow state

Changes consist of old/new repository-relative paths from a staged or commit diff.
Route ordering is static < tests < product. Prose extensions never become runtime code.
Selections consist of changed eligible unit files and dependency/failed IDs intersected
with current bounded collection, with heavy/live markers removed. Missing history is a
reported verification gap. No selected candidates means no pytest launch.
Release attempts hold expected HEAD/master identities and an OS lock in memory. They
consume a reviewed native verification record and explicit pairing decision, then
progress through integrity checks, fast-forward integration, semantic version preparation,
selected final-pair validation and optional authorized publication. Failures retain prepared
release inputs for manual recovery; no persistent receipt is created.
