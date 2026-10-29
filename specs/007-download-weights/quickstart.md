# Validation guide

Run `cy-download-weights --help`, then `cy-download-weights` in the intended SDK
environment. A successful pass reports each native destination. Disable network
before exercising ordinary native loader names in a new process; use the same
settings/cache selectors. Preserve relative-path working-directory semantics.

Run a custom pipeline tree with architecture YAML and an explicit pretrained filename.
Verify the architecture and replay inputs remain unchanged and the file is loaded
from weights_dir. Repeated execution should skip the completed automatic pass.
Manual preparation retries after partial failure; interruption requires a new pass.

Use isolated project outputs and explicit ClearML project/tags for real pipeline
acceptance. Follow the repository end-to-end skill; unit tests alone do not prove
training or publication. Dated evidence records actual commands and outcomes.
