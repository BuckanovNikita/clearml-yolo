"""Run identity: the id, the private run directory, and the ``latest`` symlink."""

from collections.abc import Callable
from pathlib import Path

import pytest
from loguru import logger

from clearml_yolo.adapters.storage import run_identity
from clearml_yolo.adapters.storage.run_identity import (
    LATEST_LINK_NAME,
    point_latest_at,
    resolve_run_dir,
)

HOST = "box"
PID = 4242


@pytest.fixture
def fixed_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the two facts a run has no control over, so an id is reproducible."""
    monkeypatch.setattr(run_identity, "_host_and_pid", lambda: (HOST, PID))


def _warnings_from(action: Callable[[], None]) -> list[str]:
    collected: list[str] = []
    handle = logger.add(lambda message: collected.append(str(message)), level="WARNING")
    try:
        action()
    finally:
        logger.remove(handle)
    return collected


@pytest.mark.usefixtures("fixed_identity")
def test_an_explicit_run_dir_wins_over_the_one_the_id_would_name(tmp_path: Path) -> None:
    """A run pointed at a scratch disk must write there and not under the workspace."""
    elsewhere = tmp_path / "scratch" / "somewhere"

    assert resolve_run_dir(tmp_path / "runs", "yolo-run-box", elsewhere) == elsewhere.resolve()


def test_a_run_dir_is_named_after_the_run_id_beneath_the_root(tmp_path: Path) -> None:
    """The directory is what makes two runs in one folder stop overwriting each other."""
    assert (
        resolve_run_dir(tmp_path, "yolo-run-box-20260816-120000-4242", None)
        == (tmp_path / "yolo-run-box-20260816-120000-4242").resolve()
    )


@pytest.mark.parametrize("explicit", [None, Path("runs/handmade")])
def test_a_resolved_run_dir_is_absolute(explicit: Path | None) -> None:
    """Hydra runs with chdir=False while ultralytics resolves its project path against the
    working directory, so a relative path would mean two different places."""
    assert resolve_run_dir(Path("runs"), "yolo-run-box", explicit).is_absolute()


@pytest.mark.usefixtures("fixed_identity")
def test_latest_points_at_the_run_dir_it_was_given(tmp_path: Path) -> None:
    """``ls runs/latest/metrics`` is the habit the per-run directories would otherwise break."""
    run_dir = tmp_path / "yolo-run-box-20260816-120000-4242"
    run_dir.mkdir()

    point_latest_at(tmp_path, run_dir)

    assert (tmp_path / LATEST_LINK_NAME).resolve() == run_dir.resolve()


@pytest.mark.usefixtures("fixed_identity")
def test_latest_is_repointed_at_the_newer_run(tmp_path: Path) -> None:
    """Every run repoints it, so the symlink has to survive already existing."""
    first = tmp_path / "run-a"
    second = tmp_path / "run-b"
    first.mkdir()
    second.mkdir()

    point_latest_at(tmp_path, first)
    point_latest_at(tmp_path, second)

    assert (tmp_path / LATEST_LINK_NAME).resolve() == second.resolve()


@pytest.mark.usefixtures("fixed_identity")
def test_a_run_outside_the_workspace_leaves_latest_where_it_was(tmp_path: Path) -> None:
    """An agent's run in a scratch directory is deleted by its cleanup, and a link pointing
    there would dangle; the workspace's shortcut keeps naming the last run that landed in
    the workspace."""
    root = tmp_path / "workspace" / "runs"
    here = root / "run-here"
    here.mkdir(parents=True)
    elsewhere = tmp_path / "scratch" / "run-elsewhere"
    elsewhere.mkdir(parents=True)
    point_latest_at(root, here)

    point_latest_at(root, elsewhere)

    assert (root / LATEST_LINK_NAME).resolve() == here.resolve()
    assert [entry.name for entry in root.iterdir()] == sorted([LATEST_LINK_NAME, "run-here"])


@pytest.mark.usefixtures("fixed_identity")
def test_a_run_beside_the_runs_root_is_still_the_workspaces_own(tmp_path: Path) -> None:
    """``run_dir=sweeps/07`` is inside the workspace even though it is outside ``runs/``."""
    root = tmp_path / "runs"
    beside = tmp_path / "sweeps" / "07"
    beside.mkdir(parents=True)

    point_latest_at(root, beside)

    assert (root / LATEST_LINK_NAME).resolve() == beside.resolve()


@pytest.mark.usefixtures("fixed_identity")
def test_no_temporary_link_is_left_beside_the_run_dirs(tmp_path: Path) -> None:
    """The rename that makes the swap atomic must consume the link it renamed."""
    run_dir = tmp_path / "run-a"
    run_dir.mkdir()

    point_latest_at(tmp_path, run_dir)

    assert sorted(entry.name for entry in tmp_path.iterdir()) == [LATEST_LINK_NAME, "run-a"]


DISPLACED_NAME = f"{LATEST_LINK_NAME}-displaced-{HOST}-{PID}"


@pytest.mark.usefixtures("fixed_identity")
def test_a_regular_file_named_latest_is_moved_aside_rather_than_written_over(
    tmp_path: Path,
) -> None:
    """Renaming a symlink over a plain file succeeds on Linux, so whatever a user put at
    that name survives only because the run moves it instead of replacing it."""
    occupied = tmp_path / LATEST_LINK_NAME
    occupied.write_text("mine", encoding="utf-8")
    run_dir = tmp_path / "run-a"
    run_dir.mkdir()

    point_latest_at(tmp_path, run_dir)

    assert (tmp_path / DISPLACED_NAME).read_text(encoding="utf-8") == "mine"
    assert (tmp_path / LATEST_LINK_NAME).resolve() == run_dir.resolve()


@pytest.mark.usefixtures("fixed_identity")
def test_a_directory_left_at_latest_is_moved_aside_so_the_link_can_be_taken_back(
    tmp_path: Path,
) -> None:
    """A standalone stage in a fresh workspace writes *through* the name and so creates it
    as an ordinary directory; leaving that alone would freeze the link for every run after."""
    (tmp_path / LATEST_LINK_NAME).mkdir()
    run_dir = tmp_path / "run-a"
    run_dir.mkdir()

    point_latest_at(tmp_path, run_dir)

    assert (tmp_path / LATEST_LINK_NAME).is_symlink()
    assert (tmp_path / LATEST_LINK_NAME).resolve() == run_dir.resolve()
    assert (tmp_path / DISPLACED_NAME).is_dir()


@pytest.mark.usefixtures("fixed_identity")
def test_a_stage_output_under_latest_survives_the_move_intact(tmp_path: Path) -> None:
    """The directory that gets moved is one a stage already wrote into, so the move has to
    carry what it holds rather than merely free the name."""
    written = tmp_path / LATEST_LINK_NAME / "reports" / "report.html"
    written.parent.mkdir(parents=True)
    written.write_text("mine", encoding="utf-8")
    run_dir = tmp_path / "run-a"
    run_dir.mkdir()

    point_latest_at(tmp_path, run_dir)

    assert (tmp_path / DISPLACED_NAME / "reports" / "report.html").read_text(
        encoding="utf-8"
    ) == "mine"


@pytest.mark.usefixtures("fixed_identity")
def test_moving_a_directory_off_latest_reports_what_moved_and_where(tmp_path: Path) -> None:
    """Nothing else tells the user their outputs are now under another name."""
    (tmp_path / LATEST_LINK_NAME).mkdir()
    run_dir = tmp_path / "run-a"
    run_dir.mkdir()

    warnings = _warnings_from(lambda: point_latest_at(tmp_path, run_dir))

    assert any(
        str(tmp_path / LATEST_LINK_NAME) in warning and str(tmp_path / DISPLACED_NAME) in warning
        for warning in warnings
    )


@pytest.mark.usefixtures("fixed_identity")
def test_a_filesystem_that_refuses_symlinks_costs_a_warning_and_not_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The symlink is a convenience; a training hour must not be lost to its absence."""

    def refuse(*_: object, **__: object) -> None:
        raise OSError(1, "Operation not permitted")

    monkeypatch.setattr(Path, "symlink_to", refuse)
    run_dir = tmp_path / "run-a"
    run_dir.mkdir()

    warnings = _warnings_from(lambda: point_latest_at(tmp_path, run_dir))

    assert not (tmp_path / LATEST_LINK_NAME).exists()
    assert any("Operation not permitted" in warning for warning in warnings)


def test_task_output_root_encodes_names_and_retains_task_id(tmp_path: Path) -> None:
    from clearml_yolo.adapters.storage.run_identity import task_run_dir

    root = task_run_dir(tmp_path, "team/project", "../task\\name", "abc123")
    assert root == tmp_path / "team%2Fproject" / "%2E%2E%2Ftask%5Cname-abc123"
    assert task_run_dir(tmp_path, "team/project", "../task\\name", "def456") != root


@pytest.mark.parametrize("name", ["..", ".", "CON", "NUL", "a/b", "a\\b", "a: ", "кот"])
def test_task_output_components_are_portable(tmp_path: Path, name: str) -> None:
    from clearml_yolo.adapters.storage.run_identity import task_run_dir

    root = task_run_dir(tmp_path, name, name, "id")
    assert root.parent.parent == tmp_path
    assert root.parent.name not in {".", "..", "CON", "NUL"}
    assert all(character not in root.parent.name for character in '/\\:<>"|?* ')


def test_task_identity_adapter_reads_active_values() -> None:
    from types import SimpleNamespace

    from clearml_yolo.adapters.clearml.session import task_identity

    task = SimpleNamespace(
        id="active-id", name="actual task", get_project_name=lambda: "actual/project"
    )
    assert task_identity(task) == ("actual/project", "actual task", "active-id")


@pytest.mark.parametrize("existing_latest", [False, True])
def test_latest_project_does_not_collide_with_convenience_link(
    tmp_path: Path, existing_latest: bool
) -> None:
    from clearml_yolo.adapters.storage.run_identity import task_run_dir

    root = tmp_path / "runs"
    root.mkdir()
    previous = root / "previous"
    if existing_latest:
        previous.mkdir()
        (root / LATEST_LINK_NAME).symlink_to(previous, target_is_directory=True)
    directory = task_run_dir(root, "latest", "task", "id")
    directory.mkdir(parents=True)
    point_latest_at(root, directory)
    assert directory.parent.parent == root
    (directory / "artifact.json").write_text("{}")
    assert (root / LATEST_LINK_NAME).resolve() == directory
    assert directory.parent.name != LATEST_LINK_NAME
    if existing_latest:
        assert list(previous.iterdir()) == []
