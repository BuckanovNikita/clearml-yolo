# Controller integration

Register before creating/running cached jobs in an external task-based controller:

```python
from clearml.automation.job import ClearmlJob
from clearml_yolo.adapters.clearml.cache import normalize_task_hash

ClearmlJob.register_hashing_callback(normalize_task_hash)
```

Then use the controller's existing `cache_executed_step=True` setting. If the
controller already installs a callback, compose its result with normalize_task_hash
instead of replacing it. Registration affects that process's job class and must occur
after any framework registration and before job creation. Do not register from a worker.

For changed `run` configuration, pass JSON text through `configuration_overrides`,
using `json.dumps(full_run_config, ensure_ascii=False)` after importing `json`.
Dictionary overrides become JSON with default ASCII escaping in the installed SDK;
explicit text preserves Unicode through its replay parser.

Full settings remain in Configuration Objects. A hit returns the previous task's
remote artifacts/models, rather than creating files in a newly selected output folder.
Input files and references retain the project's existing immutability requirements.
