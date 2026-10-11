"""The guarded constants loader redirects hardcoded paths before public SDK imports."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("outward_state", [None, "var", "migrations"])
def test_constants_redirect_precedes_public_import_and_preserves_installed_bin(
    tmp_path: Path, outward_state: str | None,
) -> None:
    package = tmp_path / "fiftyone"
    package.mkdir()
    (package / "__init__.py").write_text(
        "import fiftyone.constants as constants\nfrom fiftyone.__public__ import *\n"
    )
    (package / "constants.py").write_text("""
import os
FIFTYONE_CONFIG_DIR=os.path.join(os.path.expanduser('~'),'.fiftyone')
FIFTYONE_CONFIG_PATH=os.path.join(FIFTYONE_CONFIG_DIR,'config.json')
FIFTYONE_ANNOTATION_CONFIG_PATH=os.path.join(FIFTYONE_CONFIG_DIR,'annotation_config.json')
FIFTYONE_EVALUATION_CONFIG_PATH=os.path.join(FIFTYONE_CONFIG_DIR,'evaluation_config.json')
FIFTYONE_APP_CONFIG_PATH=os.path.join(FIFTYONE_CONFIG_DIR,'app_config.json')
TEAMS_PATH=os.path.join(FIFTYONE_CONFIG_DIR,'var','teams.json')
WELCOME_PATH=os.path.join(FIFTYONE_CONFIG_DIR,'var','welcome.json')
DEFAULT_DB_DIR=os.path.join(FIFTYONE_CONFIG_DIR,'var','lib','mongo')
MIGRATIONS_PATH=os.path.join(FIFTYONE_CONFIG_DIR,'migrations')
MIGRATIONS_HEAD_PATH=os.path.join(MIGRATIONS_PATH,'head.json')
FIFTYONE_DB_BIN_DIR='/installed/binaries'
""")
    (package / "__public__.py").write_text("""
import os
from pathlib import Path
from fiftyone import constants as c
root=Path(os.environ['FIFTYONE_CONFIG_PATH']).parent
assert c.FIFTYONE_CONFIG_DIR == str(root)
assert c.DEFAULT_DB_DIR == os.environ['FIFTYONE_DATABASE_DIR']
assert c.FIFTYONE_DB_BIN_DIR == '/installed/binaries'
for key in ('TEAMS_PATH','WELCOME_PATH','MIGRATIONS_PATH','MIGRATIONS_HEAD_PATH'):
    assert Path(getattr(c,key)).is_relative_to(root)
""")
    env = dict(
        os.environ,
        CY_HOME=str(tmp_path / "project"),
        PYTHONPATH=f"{tmp_path}:{Path('src').resolve()}",
        FIFTYONE_CONFIG_PATH=str(tmp_path / "project" / "config.json"),
        FIFTYONE_DATABASE_DIR=str(tmp_path / "db"),
        TEAMS_PATH=str(tmp_path / "ambient" / "teams.json"),
        WELCOME_PATH=str(tmp_path / "ambient" / "welcome.json"),
        MIGRATIONS_PATH=str(tmp_path / "ambient" / "migrations"),
        MIGRATIONS_HEAD_PATH=str(tmp_path / "ambient" / "head.json"),
    )
    if outward_state is not None:
        (tmp_path / "project").mkdir()
        (tmp_path / "outside").mkdir()
        (tmp_path / "project" / outward_state).symlink_to(
            tmp_path / "outside", target_is_directory=True
        )
    script = (
        "from clearml_yolo.adapters.fiftyone.compatibility import isolated_constants; "
        "import sys; n=len(sys.meta_path);\n"
        "with isolated_constants(): import fiftyone\nassert len(sys.meta_path)==n"
    )
    result = subprocess.run(  # noqa: S603 - test-controlled interpreter
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if outward_state is None:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
        assert "physical project root" in result.stderr
        assert list((tmp_path / "outside").iterdir()) == []
