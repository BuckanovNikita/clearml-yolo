"""The agent shell scripts: identity from the stand, one tag per run, cleanup, and the report.

The k8s-infra helpers and ``curl`` are replaced by fakes that record their arguments, so
the tests check what the scripts ask for and how they react to a refusal, with no cluster.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
TAG = "clearml-yolo-claude-20260905-smoke-ab12"
CLUSTER_API = "http://api.clearml.k8s.localhost"
HOST_STAND_API = "http://localhost:8008"
GOOD_PAIR = "stand-key:stand-secret"
BASH = shutil.which("bash") or "/bin/bash"
# The pair the fake stand hands out, as the environment the SDK reads it from.
STAND_CREDENTIALS = {
    "CLEARML_API_ACCESS_KEY": "stand-key",
    "CLEARML_API_SECRET_KEY": "stand-secret",
}
STALE_CREDENTIALS = {
    "CLEARML_API_ACCESS_KEY": "stale-key",
    "CLEARML_API_SECRET_KEY": "stale-secret",
}

FAKE_INFRA_PY = """#!/usr/bin/env python3
import os, sys
with open(os.environ['FAKE_LOG'], 'a') as log:
    log.write('infra.py ' + ' '.join(sys.argv[1:]) + '\\n')
command = sys.argv[1]
if command == 'room':
    status = int(os.environ.get('FAKE_ROOM_STATUS', '0'))
    print('verdict ' + ('WAIT' if status == 3 else 'GO'))
    sys.exit(status)
if command == 'newtag':
    if os.environ.get('FAKE_NEWTAG_FAIL'):
        print('infra.py: newtag refused by the fake', file=sys.stderr)
        sys.exit(1)
    slug = sys.argv[sys.argv.index('--slug') + 1]
    print('clearml-yolo-claude-20260905-' + slug + '-ab12')
    sys.exit(0)
sys.exit(2)
"""

FAKE_CLEARML_PY = f"""#!/usr/bin/env python3
import os, sys
with open(os.environ['FAKE_LOG'], 'a') as log:
    log.write('clearml.py ' + ' '.join(sys.argv[1:]) + '\\n')
command = sys.argv[3] if len(sys.argv) > 3 else ''
if command == 'env':
    if os.environ.get('FAKE_ENV_FAIL'):
        print('clearml.py: secret clearml/clearml-clearml-yolo-access not found', file=sys.stderr)
        sys.exit(1)
    print('export CLEARML_API_HOST={CLUSTER_API}')
    print('export CLEARML_WEB_HOST=http://clearml.k8s.localhost')
    print('export CLEARML_FILES_HOST=http://files.clearml.k8s.localhost')
    print('export CLEARML_API_ACCESS_KEY=stand-key')
    print('export CLEARML_API_SECRET_KEY=stand-secret')
    print('export CLEARML_QUEUE=agents')
    sys.exit(0)
if command == 'cleanup':
    print('1 project(s), 0 standalone task(s) deleted')
    sys.exit(0)
if command == 'ls':
    print('0 project(s), 0 task(s) with prefix ' + sys.argv[-1])
    sys.exit(0)
sys.exit(2)
"""

# The fake answers `debug.ping` for any host but FAKE_UNREACHABLE and `auth.login` with
# result_code 200 only for the pair the stand hands out.
FAKE_CURL = f"""#!/usr/bin/env bash
pair=""
url=""
while (( $# > 0 )); do
    case "$1" in
        -u) pair="$2"; shift 2 ;;
        -m) shift 2 ;;
        http*) url="$1"; shift ;;
        *) shift ;;
    esac
done
if [[ -n "${{FAKE_UNREACHABLE:-}}" && "$url" == "${{FAKE_UNREACHABLE}}"* ]]; then
    exit 7
fi
case "$url" in
    */debug.ping) exit 0 ;;
    */auth.login)
        if [[ "$pair" == "{GOOD_PAIR}" ]]; then
            echo '{{"meta":{{"result_code":200}}}}'
        else
            echo '{{"meta":{{"result_code":401}}}}'
        fi
        exit 0 ;;
esac
exit 22
"""

FAKE_UV = "#!/usr/bin/env bash\necho 'uv 0.0-fake'\n"


@dataclass(frozen=True)
class ShellResult:
    status: int
    stdout: str
    stderr: str
    environment: dict[str, str]
    helper_calls: list[str]


@dataclass(frozen=True)
class Harness:
    skill_dir: Path
    bin_dir: Path
    log: Path
    scratch: Path

    def environment(self, **extra: str) -> dict[str, str]:
        base = {
            "PATH": f"{self.bin_dir}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.scratch / "home"),
            "K8S_INFRA_SKILL_DIR": str(self.skill_dir),
            "INFRA_SCRATCH_DIR": str(self.scratch),
            "FAKE_LOG": str(self.log),
        }
        return {**base, **extra}

    def helper_calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []


def _install(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    skill_dir = tmp_path / "skill"
    (skill_dir / "scripts").mkdir(parents=True)
    _install(skill_dir / "scripts" / "infra.py", FAKE_INFRA_PY)
    _install(skill_dir / "scripts" / "clearml.py", FAKE_CLEARML_PY)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install(bin_dir / "curl", FAKE_CURL)
    _install(bin_dir / "uv", FAKE_UV)
    scratch = tmp_path / "scratch"
    (scratch / "home").mkdir(parents=True)
    return Harness(skill_dir, bin_dir, tmp_path / "helper-calls.log", scratch)


def _source_agent_env(harness: Harness, *args: str, **extra_env: str) -> ShellResult:
    """Source the script in a fresh bash and read back its status and the environment it left."""
    marker = "__ENV__"
    script = (
        f'source {SCRIPTS / "agent_env.sh"} "$@"; status=$?; '
        f"printf '{marker}'; env -0; exit $status"
    )
    completed = subprocess.run(  # noqa: S603  the command is this test's own script
        [BASH, "-c", script, "agent_env", *args],
        check=False,
        capture_output=True,
        text=True,
        env=harness.environment(**extra_env),
        cwd=REPO_ROOT,
    )
    stdout, _, raw_env = completed.stdout.partition(marker)
    environment: dict[str, str] = {}
    for entry in raw_env.split("\0"):
        name, separator, value = entry.partition("=")
        if separator:
            environment[name] = value
    return ShellResult(
        completed.returncode, stdout, completed.stderr, environment, harness.helper_calls()
    )


def _run(
    script: str, harness: Harness, *args: str, **extra_env: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  the command is this test's own script
        [str(SCRIPTS / script), *args],
        check=False,
        capture_output=True,
        text=True,
        env=harness.environment(**extra_env),
        cwd=REPO_ROOT,
    )


# --- agent_env.sh ------------------------------------------------------------------------


def test_sourcing_makes_the_shell_the_project_on_the_stand_with_one_tag_and_one_directory(
    harness: Harness,
) -> None:
    """Everything a run needs is exported: the stand's credentials, the tag, and where to write."""
    result = _source_agent_env(harness, "smoke")

    assert result.status == 0, result.stderr
    env = result.environment
    assert env["INFRA_RUN_TAG"] == TAG
    assert env["CY_RUN_TAG"] == TAG
    assert env["INFRA_PROJECT"] == "clearml-yolo"
    assert env["CLEARML_API_HOST"] == CLUSTER_API
    assert env["CLEARML_API_ACCESS_KEY"] == "stand-key"
    assert env["CY_RUN_DIR"] == str(harness.scratch / TAG)
    assert (harness.scratch / TAG).is_dir()


def test_every_helper_is_asked_as_the_project_before_its_subcommand(harness: Harness) -> None:
    """`--project` is a top-level option of the helpers; after the subcommand it is refused."""
    result = _source_agent_env(harness, "smoke")

    assert result.helper_calls == [
        "infra.py room",
        "clearml.py --project clearml-yolo env",
        "infra.py newtag --project clearml-yolo --slug smoke",
    ]


def test_the_slug_defaults_to_run(harness: Harness) -> None:
    result = _source_agent_env(harness)

    assert "infra.py newtag --project clearml-yolo --slug run" in result.helper_calls
    assert result.environment["CY_RUN_TAG"].endswith("-run-ab12")


def test_the_printed_run_line_carries_the_deadline_the_gpu_cap_and_the_tagged_project(
    harness: Harness,
) -> None:
    """The line an agent copies must fail rather than block, take one card, and land by tag."""
    result = _source_agent_env(harness, "smoke", CY_QUEUE_WAIT_SECONDS="900")

    assert "auto_gpu.queue.wait_timeout_seconds=900" in result.stdout
    assert "auto_gpu.max_gpus=1" in result.stdout
    assert "run_dir=$CY_RUN_DIR" in result.stdout
    assert 'clearml.project_name="$CY_RUN_TAG clearml-yolo"' in result.stdout
    assert "clearml.tags=[$CY_RUN_TAG]" in result.stdout
    assert "never enqueue" in result.stdout
    assert "stand-secret" not in result.stdout


def test_the_report_at_the_end_names_the_stand_it_authenticated_against(harness: Harness) -> None:
    result = _source_agent_env(harness, "smoke")

    assert (
        f"OK   ClearML {CLUSTER_API} — authenticated "
        "(endpoint from environment, credentials from environment)"
    ) in result.stdout


def test_an_already_exported_tag_is_kept_and_nothing_is_minted(harness: Harness) -> None:
    """An agent that minted its own tag, with --keep say, is not given a second one."""
    kept = "clearml-yolo-codex-20260905-bench-zz01-keep"

    result = _source_agent_env(harness, "smoke", INFRA_RUN_TAG=kept)

    assert result.status == 0, result.stderr
    assert result.environment["CY_RUN_TAG"] == kept
    assert result.environment["CY_RUN_DIR"] == str(harness.scratch / kept)
    assert not any(call.startswith("infra.py newtag") for call in result.helper_calls)


def test_the_default_run_root_is_the_project_directory_under_tmp(harness: Harness) -> None:
    environment = harness.environment()
    del environment["INFRA_SCRATCH_DIR"]
    expected = Path("/tmp/clearml-yolo-runs") / TAG

    try:
        completed = subprocess.run(  # noqa: S603  the command is this test's own script
            [BASH, "-c", f'source {SCRIPTS / "agent_env.sh"} smoke && printf "%s" "$CY_RUN_DIR"'],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            cwd=REPO_ROOT,
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.endswith(str(expected))
        assert expected.is_dir()
    finally:
        shutil.rmtree(expected, ignore_errors=True)


def test_a_wait_from_room_returns_3_before_anything_is_minted(harness: Harness) -> None:
    result = _source_agent_env(harness, "smoke", FAKE_ROOM_STATUS="3")

    assert result.status == 3
    assert "WAIT" in result.stderr
    assert result.helper_calls == ["infra.py room"]
    assert "CY_RUN_TAG" not in result.environment


def test_a_refused_env_stops_the_run_with_nothing_exported(harness: Harness) -> None:
    """Without the Secret there is no identity, and a tag without one is a run nobody owns."""
    result = _source_agent_env(harness, "smoke", FAKE_ENV_FAIL="1")

    assert result.status == 1
    assert "clearml.py env refused" in result.stderr
    assert "CLEARML_API_HOST" not in result.environment
    assert "INFRA_RUN_TAG" not in result.environment
    assert not any(call.startswith("infra.py newtag") for call in result.helper_calls)


def test_a_refused_mint_exports_no_empty_tag(harness: Harness) -> None:
    """`export VAR=$(...)` would export an empty tag with the status of `export`; this must not."""
    result = _source_agent_env(harness, "smoke", FAKE_NEWTAG_FAIL="1")

    assert result.status == 1
    assert "newtag refused" in result.stderr
    assert "INFRA_RUN_TAG" not in result.environment
    assert "CY_RUN_TAG" not in result.environment
    assert "CY_RUN_DIR" not in result.environment


def test_without_a_skill_the_script_says_where_it_looked(harness: Harness) -> None:
    result = _source_agent_env(
        harness, "smoke", K8S_INFRA_SKILL_DIR=str(harness.scratch / "nowhere")
    )

    assert result.status == 1
    assert "no k8s-infra skill found" in result.stderr
    assert result.helper_calls == []


def test_the_installed_skill_is_found_under_the_agents_home_when_no_override_is_set(
    harness: Harness,
) -> None:
    home = harness.scratch / "home"
    (home / ".agents" / "skills").mkdir(parents=True)
    (home / ".agents" / "skills" / "k8s-infra").symlink_to(harness.skill_dir)
    environment = harness.environment()
    del environment["K8S_INFRA_SKILL_DIR"]

    completed = subprocess.run(  # noqa: S603  the command is this test's own script
        [
            BASH,
            "-c",
            f'source {SCRIPTS / "agent_env.sh"} smoke && printf "%s" "$CY_INFRA_SKILL_DIR"',
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        cwd=REPO_ROOT,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.endswith(str(home / ".agents" / "skills" / "k8s-infra"))


def test_running_the_script_instead_of_sourcing_it_is_refused(harness: Harness) -> None:
    """Executed, its exports would die with the subshell and the agent would believe it has them."""
    completed = _run("agent_env.sh", harness, "smoke")

    assert completed.returncode == 1
    assert "source it" in completed.stderr
    assert harness.helper_calls() == []


# --- agent_cleanup.sh --------------------------------------------------------------------


def test_cleanup_deletes_by_the_run_tag_proves_it_with_ls_and_removes_the_run_directory(
    harness: Harness,
) -> None:
    run_dir = harness.scratch / TAG
    (run_dir / "train").mkdir(parents=True)

    completed = _run("agent_cleanup.sh", harness, CY_RUN_TAG=TAG, CY_RUN_DIR=str(run_dir))

    assert completed.returncode == 0, completed.stderr
    assert harness.helper_calls() == [
        f"clearml.py --project clearml-yolo cleanup --prefix {TAG}",
        f"clearml.py --project clearml-yolo ls --prefix {TAG}",
    ]
    assert not run_dir.exists()
    assert f"removed {run_dir}" in completed.stdout


def test_cleanup_falls_back_to_the_contract_tag_and_explicit_arguments(harness: Harness) -> None:
    run_dir = harness.scratch / TAG
    run_dir.mkdir(parents=True)

    by_env = _run("agent_cleanup.sh", harness, INFRA_RUN_TAG=TAG)
    by_flag = _run("agent_cleanup.sh", harness, "--tag", TAG, "--run-dir", str(run_dir))

    assert by_env.returncode == 0, by_env.stderr
    assert "only the stand was cleaned" in by_env.stdout
    assert by_flag.returncode == 0, by_flag.stderr
    assert not run_dir.exists()


def test_cleanup_refuses_a_directory_not_named_after_the_tag(harness: Harness) -> None:
    """The run directory is <scratch>/<tag>; anything else is not this run's to remove."""
    elsewhere = harness.scratch / "somebody-elses-runs"
    elsewhere.mkdir()

    completed = _run("agent_cleanup.sh", harness, CY_RUN_TAG=TAG, CY_RUN_DIR=str(elsewhere))

    assert completed.returncode == 1
    assert "not named after" in completed.stderr
    assert elsewhere.exists()


def test_cleanup_dry_run_lists_and_keeps_everything(harness: Harness) -> None:
    run_dir = harness.scratch / TAG
    run_dir.mkdir(parents=True)

    completed = _run(
        "agent_cleanup.sh", harness, "--dry-run", CY_RUN_TAG=TAG, CY_RUN_DIR=str(run_dir)
    )

    assert completed.returncode == 0, completed.stderr
    assert harness.helper_calls()[0] == (
        f"clearml.py --project clearml-yolo cleanup --prefix {TAG} --dry-run"
    )
    assert run_dir.exists()
    assert f"would remove {run_dir}" in completed.stdout


def test_cleanup_without_a_tag_asks_for_one(harness: Harness) -> None:
    completed = _run("agent_cleanup.sh", harness)

    assert completed.returncode == 2
    assert "no run tag" in completed.stderr
    assert harness.helper_calls() == []


# --- check_env.sh ------------------------------------------------------------------------


def _write_conf(harness: Harness, api: str, pair: str) -> Path:
    key, _, secret = pair.partition(":")
    conf = harness.scratch / "clearml.conf"
    conf.write_text(
        "api {\n"
        f"    api_server: {api}\n"
        "    web_server: http://localhost:8580\n"
        "    files_server: http://localhost:8081\n"
        "    credentials {\n"
        f'        "access_key" = "{key}"\n'
        f'        "secret_key" = "{secret}"\n'
        "    }\n"
        "}\n"
    )
    return conf


def test_check_env_reads_the_environment_before_the_config_file(harness: Harness) -> None:
    """The SDK does the same, so the report must describe the run the SDK would make."""
    conf = _write_conf(harness, HOST_STAND_API, "conf-key:conf-secret")

    completed = _run(
        "check_env.sh",
        harness,
        CLEARML_CONFIG_FILE=str(conf),
        CLEARML_API_HOST=CLUSTER_API,
        **STAND_CREDENTIALS,
    )

    assert completed.returncode == 0
    assert (
        f"OK   ClearML {CLUSTER_API} — authenticated "
        "(endpoint from environment, credentials from environment)"
    ) in completed.stdout
    assert HOST_STAND_API not in completed.stdout
    assert "WARN ClearML" not in completed.stdout


def test_check_env_falls_back_to_the_config_file_and_warns_about_the_host_stand(
    harness: Harness,
) -> None:
    conf = _write_conf(harness, HOST_STAND_API, GOOD_PAIR)

    completed = _run("check_env.sh", harness, CLEARML_CONFIG_FILE=str(conf))

    assert completed.returncode == 0
    assert (
        f"OK   ClearML {HOST_STAND_API} — authenticated "
        f"(endpoint from {conf}, credentials from {conf})"
    ) in completed.stdout
    assert f"WARN ClearML {HOST_STAND_API} is the user's host stand" in completed.stdout
    assert "agent_env.sh" in completed.stdout


def test_check_env_mixes_an_environment_endpoint_with_file_credentials_and_says_so(
    harness: Harness,
) -> None:
    conf = _write_conf(harness, HOST_STAND_API, GOOD_PAIR)

    completed = _run(
        "check_env.sh", harness, CLEARML_CONFIG_FILE=str(conf), CLEARML_API_HOST=CLUSTER_API
    )

    assert (
        f"OK   ClearML {CLUSTER_API} — authenticated "
        f"(endpoint from environment, credentials from {conf})"
    ) in completed.stdout


def test_check_env_reports_rejected_credentials_against_the_endpoint_it_tried(
    harness: Harness,
) -> None:
    completed = _run(
        "check_env.sh",
        harness,
        CLEARML_CONFIG_FILE=str(harness.scratch / "absent.conf"),
        CLEARML_API_HOST=CLUSTER_API,
        **STALE_CREDENTIALS,
    )

    assert (
        f"FAIL ClearML {CLUSTER_API} (from environment) — reachable but the credentials "
        "from environment are rejected"
    ) in completed.stdout


def test_check_env_warns_about_the_host_stand_even_when_it_is_down(harness: Harness) -> None:
    """An agent pointed at the host stand must learn so whether or not the stand answers."""
    conf = _write_conf(harness, HOST_STAND_API, GOOD_PAIR)

    completed = _run(
        "check_env.sh", harness, CLEARML_CONFIG_FILE=str(conf), FAKE_UNREACHABLE=HOST_STAND_API
    )

    assert f"FAIL ClearML {HOST_STAND_API} (from {conf}) — unreachable" in completed.stdout
    assert f"WARN ClearML {HOST_STAND_API} is the user's host stand" in completed.stdout


def test_check_env_reports_an_unreachable_endpoint_and_where_it_came_from(
    harness: Harness,
) -> None:
    completed = _run(
        "check_env.sh",
        harness,
        CLEARML_CONFIG_FILE=str(harness.scratch / "absent.conf"),
        CLEARML_API_HOST=CLUSTER_API,
        FAKE_UNREACHABLE=CLUSTER_API,
    )

    assert f"FAIL ClearML {CLUSTER_API} (from environment) — unreachable" in completed.stdout


def test_check_env_without_a_file_or_an_endpoint_points_agents_at_agent_env(
    harness: Harness,
) -> None:
    completed = _run(
        "check_env.sh", harness, CLEARML_CONFIG_FILE=str(harness.scratch / "absent.conf")
    )

    assert "FAIL clearml.conf" in completed.stdout
    assert "agent_env.sh" in completed.stdout


def test_check_env_json_carries_the_same_report_for_the_session_hook(harness: Harness) -> None:
    completed = _run(
        "check_env.sh",
        harness,
        "--json",
        CLEARML_CONFIG_FILE=str(harness.scratch / "absent.conf"),
        CLEARML_API_HOST=CLUSTER_API,
        **STAND_CREDENTIALS,
    )

    payload = json.loads(completed.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert f"OK   ClearML {CLUSTER_API} — authenticated" in context
