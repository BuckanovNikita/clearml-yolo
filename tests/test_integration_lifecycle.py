"""Live-run lifecycle against substituted k8s-infra helpers, kubectl and curl."""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from integration import lifecycle

_FAKE = """
import os
import sys
import time
from pathlib import Path

name = Path(sys.argv[0]).stem
state = Path(os.environ["FAKE_STAND"])
with (state / "calls.log").open("a", encoding="utf-8") as log:
    log.write(" ".join([name, *sys.argv[1:]]) + "\\n")
args = [value for value in sys.argv[1:] if value not in {"--project", "clearml-yolo"}]
key = name if name in {"kubectl", "curl"} else f"{name}-{args[0]}"
for suffix, action in (
    ("sleep", lambda text: time.sleep(float(text))),
    ("out", sys.stdout.write),
    ("err", sys.stderr.write),
):
    path = state / f"{key}.{suffix}"
    if path.exists():
        action(path.read_text(encoding="utf-8"))
code = state / f"{key}.code"
sys.exit(int(code.read_text(encoding="utf-8")) if code.exists() else 0)
"""
TAG = "clearml-yolo-claude-20261109-integration-ab12"
EMPTY_LISTING = f"0 project(s), 0 task(s) with prefix '{TAG}'\n"


@dataclass
class FakeStand:
    """Scripted stand helpers; each records its argument vector in ``calls.log``."""

    state: Path
    repo: Path

    def answer(self, key: str, *, out: str | None = None, err: str | None = None, code: int | None = None) -> None:
        for suffix, value in (("out", out), ("err", err), ("code", None if code is None else str(code))):
            if value is not None:
                (self.state / f"{key}.{suffix}").write_text(value, encoding="utf-8")

    def delay(self, key: str, seconds: float) -> None:
        (self.state / f"{key}.sleep").write_text(str(seconds), encoding="utf-8")

    def calls(self) -> list[str]:
        log = self.state / "calls.log"
        return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    @property
    def tag_file(self) -> Path:
        return self.repo / "tests" / "integration" / ".run-tag"

    def main(self, command: str) -> int:
        return lifecycle.main(["--repo-root", str(self.repo), command], on_signal=lambda *_: None)


def _install(path: Path) -> None:
    path.write_text(f"#!{sys.executable}\n{_FAKE}", encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def stand(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeStand:
    state = tmp_path / "state"
    scripts = tmp_path / "skill" / "scripts"
    tools = tmp_path / "bin"
    repo = tmp_path / "repo"
    for directory in (state, scripts, tools, repo / "tests" / "integration"):
        directory.mkdir(parents=True)
    for path in (scripts / "infra.py", scripts / "clearml.py", tools / "kubectl", tools / "curl"):
        _install(path)
    monkeypatch.setenv("FAKE_STAND", str(state))
    monkeypatch.setenv("K8S_INFRA_SKILL_DIR", str(tmp_path / "skill"))
    monkeypatch.setenv("PATH", f"{tools}{os.pathsep}{os.environ['PATH']}")
    for name in ("INFRA_RUN_TAG", "INTEGRATION_RUN_TAG", "INTEGRATION_KEEP_DATA", lifecycle.CHECK_TIMEOUT_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    fake = FakeStand(state, repo)
    fake.answer(
        "clearml-env",
        out=(
            "export CLEARML_API_HOST=https://api.clearml.example\n"
            "export CLEARML_API_ACCESS_KEY=access\n"
            "export CLEARML_API_SECRET_KEY='se cret'\n"
            "export SSL_CERT_FILE=/etc/ca.pem\n"
        ),
    )
    fake.answer("curl", out="200")
    fake.answer("infra-newtag", out=f"{TAG}\n")
    fake.answer("clearml-ls", out=EMPTY_LISTING)
    return fake


def test_check_reports_available_without_minting_or_cleaning(stand: FakeStand) -> None:
    assert stand.main("check") == lifecycle.EXIT_AVAILABLE
    commands = [" ".join(call.split()[:4]) for call in stand.calls()]
    assert not any("newtag" in call or "cleanup" in call for call in commands)
    assert any(call.startswith("infra room") for call in commands)
    assert any(call.startswith("clearml --project clearml-yolo whoami") for call in commands)
    assert not stand.tag_file.exists()


@pytest.mark.parametrize(
    ("key", "answer"),
    [
        ("infra-room", {"code": 3}),
        ("curl", {"code": 7}),
        ("curl", {"out": "503"}),
        ("kubectl", {"code": 1, "err": "dial tcp: connection refused"}),
        (
            "kubectl",
            {
                "code": 1,
                "err": "The connection to the server 127.0.0.1:6443 was refused - "
                "did you specify the right host or port?",
            },
        ),
        (
            "kubectl",
            {
                "code": 1,
                "err": "Unable to connect to the server: dial tcp 127.0.0.1:6443: connectex: "
                "No connection could be made because the target machine actively refused it.",
            },
        ),
        ("clearml-whoami", {"code": 1, "err": "Remote end closed connection"}),
    ],
)
def test_temporary_outages_are_unavailable(stand: FakeStand, key: str, answer: dict[str, object]) -> None:
    stand.answer(key, **answer)  # type: ignore[arg-type]
    assert stand.main("check") == lifecycle.EXIT_UNAVAILABLE
    assert not stand.tag_file.exists()


@pytest.mark.parametrize(
    ("key", "answer"),
    [
        ("curl", {"code": 60}),
        ("curl", {"out": "404"}),
        ("kubectl", {"code": 1, "err": "x509: certificate signed by unknown authority"}),
        (
            "kubectl",
            {
                "code": 1,
                "err": "Unable to connect to the server: getting credentials: exec: executable kubelogin not found",
            },
        ),
        (
            "kubectl",
            {"code": 1, "err": "Unable to connect to the server: x509: certificate signed by unknown authority"},
        ),
        ("clearml-env", {"code": 1, "err": "secret not found"}),
        ("clearml-env", {"out": "export CLEARML_API_HOST=https://api.clearml.example\n"}),
        ("clearml-whoami", {"code": 1, "err": "HTTP 401 Unauthorized"}),
        ("infra-room", {"code": 2}),
    ],
)
def test_permanent_problems_are_errors(stand: FakeStand, key: str, answer: dict[str, object]) -> None:
    stand.answer(key, **answer)  # type: ignore[arg-type]
    assert stand.main("check") == lifecycle.EXIT_ERROR


def test_missing_skill_is_an_error(stand: FakeStand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K8S_INFRA_SKILL_DIR", str(tmp_path / "absent"))
    assert stand.main("check") == lifecycle.EXIT_ERROR


def test_preflight_deadline_bounds_a_hanging_probe(stand: FakeStand, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(lifecycle.CHECK_TIMEOUT_VARIABLE, "0.5")
    stand.delay("infra-room", 30)
    assert stand.main("check") == lifecycle.EXIT_UNAVAILABLE


@pytest.mark.parametrize("value", ["soon", "0", "-1", "inf", "nan"])
def test_invalid_check_timeout_is_an_error(stand: FakeStand, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(lifecycle.CHECK_TIMEOUT_VARIABLE, value)
    assert stand.main("check") == lifecycle.EXIT_ERROR


def test_up_mints_and_records_a_project_tag(stand: FakeStand) -> None:
    assert stand.main("up") == lifecycle.EXIT_AVAILABLE
    assert stand.tag_file.read_text(encoding="utf-8") == f"{TAG}\n"
    assert "infra newtag --project clearml-yolo --slug integration" in stand.calls()
    assert not any("cleanup" in call for call in stand.calls())


def test_up_refuses_while_another_run_tag_is_active(stand: FakeStand, capsys: pytest.CaptureFixture[str]) -> None:
    stand.tag_file.write_text("clearml-yolo-claude-20261108-integration-zz99\n", encoding="utf-8")
    assert stand.main("up") == lifecycle.EXIT_ERROR
    assert "clearml-yolo-claude-20261108-integration-zz99" in capsys.readouterr().err
    assert stand.tag_file.read_text(encoding="utf-8") == "clearml-yolo-claude-20261108-integration-zz99\n"
    assert not any("newtag" in call for call in stand.calls())


def test_up_does_not_mint_when_the_stand_is_unavailable(stand: FakeStand) -> None:
    stand.answer("infra-room", code=3)
    assert stand.main("up") == lifecycle.EXIT_UNAVAILABLE
    assert not any("newtag" in call for call in stand.calls())
    assert not stand.tag_file.exists()


@pytest.mark.parametrize("recorded", [None, TAG])
def test_exported_tag_is_adopted_and_its_leftovers_cleaned(
    stand: FakeStand, monkeypatch: pytest.MonkeyPatch, recorded: str | None
) -> None:
    if recorded is not None:
        stand.tag_file.write_text(f"{recorded}\n", encoding="utf-8")
    monkeypatch.setenv("INFRA_RUN_TAG", TAG)
    assert stand.main("up") == lifecycle.EXIT_AVAILABLE
    calls = stand.calls()
    assert not any("newtag" in call for call in calls)
    assert f"clearml --project clearml-yolo cleanup --prefix {TAG}" in calls
    assert f"clearml --project clearml-yolo ls --prefix {TAG}" in calls


def test_exported_tag_does_not_bypass_another_active_run(
    stand: FakeStand, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    active = "clearml-yolo-claude-20261108-integration-zz99"
    stand.tag_file.write_text(f"{active}\n", encoding="utf-8")
    monkeypatch.setenv("INFRA_RUN_TAG", TAG)
    assert stand.main("up") == lifecycle.EXIT_ERROR
    assert f"INFRA_RUN_TAG={active}" in capsys.readouterr().err
    assert stand.tag_file.read_text(encoding="utf-8") == f"{active}\n"
    calls = stand.calls()
    assert not any("newtag" in call or "cleanup" in call for call in calls)


@pytest.mark.parametrize("content", [b"not a tag!\n", b"", b"\xff\xfe\n"])
def test_corrupt_tag_file_with_an_exported_tag_is_refused(
    stand: FakeStand, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], content: bytes
) -> None:
    stand.tag_file.write_bytes(content)
    monkeypatch.setenv("INFRA_RUN_TAG", TAG)
    assert stand.main("up") == lifecycle.EXIT_ERROR
    err = capsys.readouterr().err
    assert str(stand.tag_file) in err
    assert "remove it" in err
    assert "INFRA_RUN_TAG=?" not in err
    assert stand.tag_file.read_bytes() == content
    assert not any("newtag" in call or "cleanup" in call for call in stand.calls())


def test_env_prefers_the_exported_tag_over_the_tag_file(
    stand: FakeStand, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stand.tag_file.write_text("clearml-yolo-claude-20261108-integration-zz99\n", encoding="utf-8")
    monkeypatch.setenv("INFRA_RUN_TAG", TAG)
    assert stand.main("env") == lifecycle.EXIT_AVAILABLE
    out = capsys.readouterr().out
    assert f"export INTEGRATION_RUN_TAG={TAG}\n" in out
    assert "export CLEARML_API_SECRET_KEY='se cret'\n" in out


def test_env_reads_the_tag_file(stand: FakeStand, capsys: pytest.CaptureFixture[str]) -> None:
    stand.tag_file.write_text(f"{TAG}\n", encoding="utf-8")
    assert stand.main("env") == lifecycle.EXIT_AVAILABLE
    assert f"export INTEGRATION_RUN_TAG={TAG}\n" in capsys.readouterr().out


def test_conflicting_integration_tag_is_refused(stand: FakeStand, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFRA_RUN_TAG", TAG)
    monkeypatch.setenv("INTEGRATION_RUN_TAG", "clearml-yolo-claude-20261108-integration-zz99")
    assert stand.main("env") == lifecycle.EXIT_ERROR


@pytest.mark.parametrize("content", ["", "Not A Tag\n"])
def test_malformed_tag_file_is_refused(stand: FakeStand, content: str) -> None:
    stand.tag_file.write_text(content, encoding="utf-8")
    assert stand.main("stop") == lifecycle.EXIT_ERROR


def test_stop_cleans_exactly_its_tag_and_releases_it(stand: FakeStand) -> None:
    stand.tag_file.write_text(f"{TAG}\n", encoding="utf-8")
    assert stand.main("stop") == lifecycle.EXIT_AVAILABLE
    calls = stand.calls()
    assert f"clearml --project clearml-yolo cleanup --prefix {TAG}" in calls
    assert calls.index(f"clearml --project clearml-yolo cleanup --prefix {TAG}") < calls.index(
        f"clearml --project clearml-yolo ls --prefix {TAG}"
    )
    assert not stand.tag_file.exists()


def test_stop_reports_remaining_objects_and_keeps_the_tag(stand: FakeStand, capsys: pytest.CaptureFixture[str]) -> None:
    stand.tag_file.write_text(f"{TAG}\n", encoding="utf-8")
    stand.answer(
        "clearml-ls",
        out=f"1 project(s), 0 task(s) with prefix '{TAG}'\nproject  {TAG} clearml-yolo  1 task(s)\n",
    )
    assert stand.main("stop") == lifecycle.EXIT_ERROR
    err = capsys.readouterr().err
    assert "1 object row(s) remain" in err
    assert f"INFRA_RUN_TAG={TAG}" in err
    assert stand.tag_file.read_text(encoding="utf-8") == f"{TAG}\n"


@pytest.mark.parametrize("key", ["clearml-cleanup", "clearml-ls"])
def test_stop_failure_keeps_the_tag(stand: FakeStand, key: str) -> None:
    stand.tag_file.write_text(f"{TAG}\n", encoding="utf-8")
    stand.answer(key, code=1)
    assert stand.main("stop") == lifecycle.EXIT_ERROR
    assert stand.tag_file.exists()


def test_stop_without_a_run_is_refused(stand: FakeStand) -> None:
    assert stand.main("stop") == lifecycle.EXIT_ERROR
    assert not any("cleanup" in call for call in stand.calls())


def test_stop_keeps_a_tag_file_naming_another_run(stand: FakeStand, monkeypatch: pytest.MonkeyPatch) -> None:
    stand.tag_file.write_text("clearml-yolo-claude-20261108-integration-zz99\n", encoding="utf-8")
    monkeypatch.setenv("INFRA_RUN_TAG", TAG)
    assert stand.main("stop") == lifecycle.EXIT_AVAILABLE
    assert stand.tag_file.read_text(encoding="utf-8") == "clearml-yolo-claude-20261108-integration-zz99\n"


def test_finish_keeps_data_on_request(stand: FakeStand, monkeypatch: pytest.MonkeyPatch) -> None:
    stand.tag_file.write_text(f"{TAG}\n", encoding="utf-8")
    run = lifecycle.Run(stand.repo)
    monkeypatch.setenv(lifecycle.KEEP_DATA_VARIABLE, "1")
    assert lifecycle.finish(run) == lifecycle.EXIT_AVAILABLE
    assert not any("cleanup" in call for call in stand.calls())
    assert stand.tag_file.exists()


def test_child_env_restores_the_recorded_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/fake/home")
    monkeypatch.setenv("XDG_CACHE_HOME", "/fake/home/.cache")
    monkeypatch.setenv(lifecycle.REAL_ENV_VARIABLE, json.dumps({"HOME": "/real/home", "XDG_CACHE_HOME": None}))
    restored = lifecycle.child_env()
    assert restored["HOME"] == "/real/home"
    assert "XDG_CACHE_HOME" not in restored


def test_skill_is_found_under_the_real_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skill = tmp_path / "home" / ".claude" / "skills" / "k8s-infra"
    (skill / "scripts").mkdir(parents=True)
    (skill / "scripts" / "infra.py").touch()
    monkeypatch.delenv("K8S_INFRA_SKILL_DIR", raising=False)
    monkeypatch.setenv(lifecycle.REAL_ENV_VARIABLE, json.dumps({"HOME": str(tmp_path / "home")}))
    assert lifecycle.find_skill_dir() == skill
