# Installation and execution contract

`Requires-Python` is `>=3.12.13,<3.14`. Stable Python 3.12.12 and 3.14 are rejected;
3.12.13, later 3.12 patches and 3.13 patches are accepted.

Package metadata, lockfile and maintained setup guidance agree. Optional native
dependencies impose their own driver/platform requirements. On Linux, both direct
and queued native work retain the existing pidfd/subreaper/proc capability preflight.
Changing a queued job's interpreter or installation requires resubmission.

The development interpreter remains Python 3.12. Command names, configuration,
dataset formats, scientific outputs and dependency source revisions are unchanged.
