"""Compose product configuration from a generated distributed training input."""

import json
import sys
from pathlib import Path

from ddp_gpu_harness import (
    Evidence,
    GPUOptions,
)


def test_generated_inputs_and_native_config_compose_offline(tmp_path: Path) -> None:
    from ddp_gpu_harness import environment_for

    evidence = Evidence(GPUOptions("0,1", "owned-tests", tmp_path), "prepare-only")
    request = {
        "indexes": [0, 1],
        "project": "owned-tests",
        "compiled": False,
        "scenario": "direct-eager",
        "tag": "offline-only",
        "timeout": 1200,
    }
    (evidence.root / "request.json").write_text(json.dumps(request))
    base = environment_for(evidence)
    evidence.helper("prepare", base)
    source = Path(__file__).resolve().parents[1] / "src"
    code = (
        "import os; from pathlib import Path; "
        "from hydra import compose, initialize_config_dir; "
        "import clearml_yolo.entrypoints.hydra.configs; "
        "from hydra_zen import store; "
        "root=Path(os.environ['CY_HOME']); "
        "store.add_to_hydra_store(overwrite_ok=True); "
        "context=initialize_config_dir(config_dir=str(root/'config'),version_base='1.3'); "
        "context.__enter__(); config=compose(config_name='ddp'); "
        "assert 'pretrained' in config.ultralytics; context.__exit__(None,None,None)"
    )
    evidence.command([sys.executable, "-c", code], dict(base, PYTHONPATH=f"{source}:{base['PYTHONPATH']}"))
