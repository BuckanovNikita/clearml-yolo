# Acceptance guide

Generate ordinary `cy-init-config` examples and execute direct `cy --help` and sequential
`cy -m`. Install the queue UI extra only for `cy-queue tui`. Submit with
`cy-queue submit --gpus 1 -- ground_truth=/path/to/input.csv` and run
`cy-queue worker` independently. Use `list` for stable IDs and observed wait reasons.

Test pending reorder/cancel and conflicting native selectors before live training.
Use isolated task-owned projects and the environment skill for native verification.
Record direct and queued settings, versions, physical GPU mapping, original traceback,
remote console/scalar visibility while active, final publication and cleanup. Repeat
on one/five GPUs eager/compiled and two real users/hosts on shared NFS. Do not substitute
CPU/mocked results for these acceptance gates. Preserve all original failure evidence.
