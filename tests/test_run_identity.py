"""Run identity: the id, the private run directory, and the ``latest`` symlink."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from loguru import logger

from clearml_yolo import run_identity
from clearml_yolo.run_identity import (
    LATEST_LINK_NAME,
    point_latest_at,
    resolve_run_dir,
    resolve_run_id,
)

HOST = "box"
PID = 4242
NOON = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)


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
def test_an_explicit_run_id_is_used_exactly_as_given() -> None:
    """Naming an id is how a rerun deliberately lands beside an earlier one."""
    assert resolve_run_id("yolo-run", "handmade", NOON) == "handmade"


@pytest.mark.usefixtures("fixed_identity")
@pytest.mark.parametrize("part", ["yolo-run", HOST, "20260816-120000", str(PID)])
def test_a_generated_run_id_carries_the_task_the_host_the_stamp_and_the_pid(part: str) -> None:
    """Drop any one of the four and two runs somewhere can still land in one directory."""
    assert part in resolve_run_id("yolo-run", None, NOON)


@pytest.mark.usefixtures("fixed_identity")
def test_two_runs_a_second_apart_on_one_machine_get_different_ids() -> None:
    """A pid is reused after a reboot, and ultralytics still trains with exist_ok=True, so
    without the stamp the second run would silently overwrite the first one's directory."""
    later = NOON.replace(second=1)

    assert resolve_run_id("yolo-run", None, NOON) != resolve_run_id("yolo-run", None, later)


def test_an_explicit_run_dir_wins_over_the_one_the_id_would_name(tmp_path: Path) -> None:
    """A run pointed at a scratch disk must write there and not under the workspace."""
    elsewhere = tmp_path / "scratch" / "somewhere"

    assert resolve_run_dir(tmp_path / "runs", "yolo-run-box", elsewhere) == elsewhere.resolve()


def test_a_run_dir_is_named_after_the_run_id_beneath_the_root(tmp_path: Path) -> None:
    """The directory is what makes two runs in one folder stop overwriting each other."""
    assert resolve_run_dir(tmp_path, "yolo-run-box-20260816-120000-4242", None) == (
        tmp_path / "yolo-run-box-20260816-120000-4242"
    ).resolve()


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
def test_no_temporary_link_is_left_beside_the_run_dirs(tmp_path: Path) -> None:
    """The rename that makes the swap atomic must consume the link it renamed."""
    run_dir = tmp_path / "run-a"
    run_dir.mkdir()

    point_latest_at(tmp_path, run_dir)

    assert sorted(entry.name for entry in tmp_path.iterdir()) == [LATEST_LINK_NAME, "run-a"]


@pytest.mark.usefixtures("fixed_identity")
def test_a_regular_file_named_latest_is_left_untouched_and_reported(tmp_path: Path) -> None:
    """Renaming a symlink over a plain file succeeds on Linux, so only an explicit refusal
    keeps a run from destroying whatever a user put at that name."""
    occupied = tmp_path / LATEST_LINK_NAME
    occupied.write_text("mine", encoding="utf-8")
    run_dir = tmp_path / "run-a"
    run_dir.mkdir()

    warnings = _warnings_from(lambda: point_latest_at(tmp_path, run_dir))

    assert not occupied.is_symlink()
    assert occupied.read_text(encoding="utf-8") == "mine"
    assert any(LATEST_LINK_NAME in warning for warning in warnings)


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
