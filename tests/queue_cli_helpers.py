"""Real queue entrypoint with only the host binding isolated from production."""

import json
import os
import sys
from pathlib import Path

import pytest


def queue_environment(root: Path) -> dict[str, str]:
    config = root / "queue.toml"
    config.write_text(
        f'[queue]\nname = "Test queue"\nroot = {json.dumps(str(root / "queue"))}\n'
        f"coordination_root = {json.dumps(str(root / 'locks'))}\n"
    )
    environment = dict(os.environ, CY_HOME=str(root), CY_QUEUE_CONFIG=str(config))
    environment.pop("CY_QUEUE_ROOT", None)
    return environment


def queue_command(root: Path) -> list[str]:
    # Test-only injection of the existing binding seam; production has no bypass.
    script = """
from pathlib import Path
from clearml_yolo.adapters.queue import coordination
from clearml_yolo.entrypoints.queue import main
bind = coordination.bind_coordination_root
coordination.bind_coordination_root = lambda host, root: bind(
    host, root, bootstrap_root=Path(BOOTSTRAP)
)
main()
""".replace("BOOTSTRAP", repr(str(root / "bootstrap")))
    return [sys.executable, "-c", script]


def configure_queue(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.adapters.queue import coordination

    environment = queue_environment(root)
    monkeypatch.setenv("CY_QUEUE_CONFIG", environment["CY_QUEUE_CONFIG"])
    monkeypatch.delenv("CY_QUEUE_ROOT", raising=False)
    bind = coordination.bind_coordination_root
    monkeypatch.setattr(
        coordination,
        "bind_coordination_root",
        lambda host, location: bind(host, location, bootstrap_root=root / "bootstrap"),
    )
