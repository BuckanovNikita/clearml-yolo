"""Independent completed-task download/readback for the live acceptance harness."""

import csv
import hashlib
import json
import os
from pathlib import Path

from clearml import Task

root = Path(os.environ.get("CY_ACCEPT_EVIDENCE", str(Path(__file__).resolve().parent)))
summary = json.loads((root / "summary.json").read_text())
output = {}
for run in summary["runs"]:
    if run.get("status") != "completed":
        continue
    task = Task.get_task(task_id=run["task_id"])
    assert task.get_project_name() == summary["project"]
    assert summary["tag"] in task.get_tags()
    truth = Path(task.artifacts["gt_csv"].get_local_copy(force_download=True))
    with truth.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 8
    assert {row["image_name"] for row in rows} == {
        "train-0.PNG", "train-1.PNG", "train-2.PNG", "train-3.PNG",
        "val-0.PNG", "val-1.PNG", "test-0.PNG", "test-1.PNG",
    }
    model = task.models["output"][0]
    downloaded = Path(model.get_local_copy(force_download=True, raise_on_error=True))
    digest = hashlib.sha256(downloaded.read_bytes()).hexdigest()
    assert digest == run["model"]["sha256"]
    output[run["name"]] = {
        "task_id": task.id, "gt_rows": len(rows),
        "empty_backgrounds": sum(not row["instance_label"] for row in rows),
        "source_names_preserved": True, "model_forced_download_sha256": digest,
        "artifact_names": sorted(task.artifacts),
        "project_and_tag_verified": True,
    }
(root / "independent-readback.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(output, indent=2))
