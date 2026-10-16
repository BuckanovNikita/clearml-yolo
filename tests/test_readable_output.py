"""Human presentation hides opaque references without changing provenance."""

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from clearml_yolo.core.identity import ModelIdentity

TASK = "0123456789abcdef" * 2
CHECKSUM = "abcdef0123456789" * 4
REFERENCE = "42a495f8-014d-4a7e-abda-6bcb4897099e"


def test_identity_caption_keeps_names_and_exact_private_provenance() -> None:
    identity = ModelIdentity(
        model_name="Detection model", training_task_id=TASK, checkpoint_sha256=CHECKSUM
    )
    assert identity.label == "Detection model"
    assert TASK not in identity.caption
    assert CHECKSUM not in identity.caption
    assert identity.model_dump()["training_task_id"] == TASK
    assert identity.model_dump()["checkpoint_sha256"] == CHECKSUM


def test_human_text_prefers_names_and_preserves_ordinary_numbers() -> None:
    from clearml_yolo.core.presentation import human_text

    source = f"Failed task {TASK}; checkpoint={CHECKSUM}; job {REFERENCE}; loss=0.125 epoch=12"
    result = human_text(source, {TASK: "Detection model", REFERENCE: "Job 17"})
    assert "Detection model" in result
    assert "Job 17" in result
    assert "loss=0.125 epoch=12" in result
    for opaque in (TASK, CHECKSUM, REFERENCE):
        assert opaque not in result
    assert human_text("/tmp/checkpoint.pt E111 https://host/help") == (
        "/tmp/checkpoint.pt E111 https://host/help"
    )


@pytest.mark.parametrize("opaque", [TASK, CHECKSUM, REFERENCE])
def test_stream_handles_every_split_and_unicode_progress(opaque: str) -> None:
    from clearml_yolo.core.presentation import HumanTextStream, human_text

    text = f"猫 progress\rTask={opaque} done\npartial \u03b1"
    for split in range(len(text) + 1):
        stream = HumanTextStream()
        result = stream.feed(text[:split]) + stream.feed(text[split:]) + stream.feed("", final=True)
        assert result == human_text(text)
        assert opaque not in result


def test_stream_bounds_unterminated_tokens() -> None:
    from clearml_yolo.core.presentation import HumanTextStream

    stream = HumanTextStream()
    result = "".join(stream.feed("a" * 1000) for _ in range(100))
    assert len(stream.pending) <= 4096
    result += stream.feed(" done\n", final=True)
    assert "done" in result
    assert "a" * 32 not in result


def test_ansi_formatting_cannot_split_a_visible_identifier() -> None:
    from clearml_yolo.core.presentation import HumanTextStream, human_text

    text = f"task={TASK[:16]}\x1b[31m{TASK[16:]}\x1b[0m\n"
    assert TASK not in human_text(text).replace("\x1b[31m", "").replace("\x1b[0m", "")
    stream = HumanTextStream()
    rendered = "".join(stream.feed(character) for character in text)
    rendered += stream.feed("", final=True)
    assert TASK not in rendered.replace("\x1b[31m", "").replace("\x1b[0m", "")


def test_publication_checkpoint_hides_continuations_without_stalling() -> None:
    from clearml_yolo.core.presentation import HumanTextStream

    stream = HumanTextStream()
    prefix = stream.feed(f"task={TASK[:9]}") + stream.checkpoint()
    assert TASK[:9] not in prefix
    assert stream.pending == ""
    rendered = prefix + stream.feed(TASK[9:] + " complete\n")
    assert TASK[9:] not in rendered
    assert "complete" in rendered


@pytest.mark.parametrize("prefix", ["task[", "id-", "name_", "name.", "task="])
@pytest.mark.parametrize("opaque", [TASK, CHECKSUM, REFERENCE])
def test_checkpoints_cannot_reconstruct_references_across_punctuation(
    prefix: str,
    opaque: str,
) -> None:
    from clearml_yolo.core.presentation import HumanTextStream

    for split in range(1, len(opaque)):
        stream = HumanTextStream()
        rendered = stream.feed(prefix + opaque[:split]) + stream.checkpoint()
        rendered += stream.feed(opaque[split:] + " completed\n")
        rendered += stream.checkpoint()
        assert opaque not in rendered
        assert opaque[:split] not in rendered.removeprefix(prefix)
        assert "completed" in rendered


def test_checkpoint_ansi_and_prior_complete_reference_cannot_expose_tail() -> None:
    from clearml_yolo.core.presentation import HumanTextStream

    stream = HumanTextStream()
    rendered = stream.feed(f"{TASK}/id_{CHECKSUM[:15]}\x1b[31m") + stream.checkpoint()
    rendered += stream.feed(CHECKSUM[15:] + "\x1b[0m done\n")
    assert TASK not in rendered
    assert CHECKSUM[:15] not in rendered
    assert CHECKSUM[15:] not in rendered
    assert "done" in rendered


@pytest.mark.parametrize("escape_prefix", ["\x1b", "\x1b[", "\x1b[31", "\x1b[31m"])
def test_checkpoint_partial_ansi_cannot_reveal_a_reference(escape_prefix: str) -> None:
    from clearml_yolo.core.presentation import HumanTextStream

    stream = HumanTextStream()
    result = stream.feed("task[" + TASK[:9] + escape_prefix) + stream.checkpoint()
    result += stream.feed(TASK[9:] + " done\n")
    assert TASK[:9] not in result
    assert TASK[9:] not in result
    assert "done" in result


def test_checkpoint_keeps_a_known_complete_reference_readable_name() -> None:
    from clearml_yolo.core.presentation import HumanTextStream

    stream = HumanTextStream({TASK: "Detector"})
    assert stream.feed("task=" + TASK) + stream.checkpoint() == "task=Detector"


def test_raw_terminal_capture_keeps_original_but_mirror_is_readable(tmp_path: Path) -> None:
    code = """
import os, sys, time
from pathlib import Path
from clearml_yolo.adapters.observability.capture import capture_output
root = Path(sys.argv[1])
os.environ['CY_HOME'] = str(root.parent)
with capture_output(root):
    for part in ('模型 task=', sys.argv[2][:9], sys.argv[2][9:], '\\rcomplete\\n'):
        os.write(1, part.encode())
        time.sleep(0.035)
"""
    result = subprocess.run(  # noqa: S603 - fixed source and isolated capture
        [sys.executable, "-c", code, str(tmp_path / "capture"), TASK],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert TASK not in result.stdout
    assert "模型" in result.stdout
    assert "complete" in result.stdout
    assert TASK in (tmp_path / "capture/stdout.log").read_text()


def test_publisher_split_tokens_flush_exact_offsets_without_changing_scalars(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.clearml.console_worker import PublicationState, publish_batch

    paths = {name: tmp_path / name for name in ("stdout", "stderr", "scalars")}
    for path in paths.values():
        path.touch()
    events: list[str] = []
    scalars: list[dict[str, object]] = []

    class Sink:
        def report_text(self, message: str, **_kwargs: object) -> None:
            events.append(message)

        def report_scalar(self, **record: object) -> None:
            scalars.append(record)

        def flush(self, **_kwargs: object) -> bool:
            return True

    offsets = dict.fromkeys(paths, 0)
    state = PublicationState()
    sink = Sink()
    text = f"模型 task={TASK}\rfinished \u03b1".encode()
    for byte in text:
        with paths["stdout"].open("ab") as output:
            output.write(bytes([byte]))
        offsets = publish_batch(paths, offsets, sink, state=state)
    record = {"title": f"model {TASK}", "series": "loss", "value": 0.125, "iteration": 17}
    paths["scalars"].write_text(json.dumps(record) + "\n")
    limits = {name: path.stat().st_size for name, path in paths.items()}
    offsets = publish_batch(paths, offsets, sink, final=True, limits=limits, state=state)
    assert offsets == limits
    assert TASK not in "".join(events)
    assert "\u03b1" in "".join(events)
    assert scalars[0]["value"] == 0.125
    assert scalars[0]["iteration"] == 17
    assert TASK not in str(scalars[0]["title"])
    assert paths["stdout"].read_bytes() == text


def test_real_barrier_acknowledges_partial_tokens_and_retains_unmodified_logs(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.clearml.console import ConsolePublisher
    from clearml_yolo.adapters.observability.capture import OutputCapture

    capture = OutputCapture(tmp_path / "capture")
    capture.prepare()
    offline = tmp_path / "offline"
    offline.mkdir()
    publisher = ConsolePublisher(TASK, capture, timeout=4, offline_folder=offline)
    publisher.start()
    try:
        capture.paths["stdout"].write_text(f"task={TASK[:9]}")
        publisher.barrier()
        with capture.paths["stdout"].open("a") as output:
            output.write(TASK[9:] + " completed\n")
        publisher.barrier()
    finally:
        publisher.finish()
    messages = [
        event["msg"]
        for line in (offline / "log.jsonl").read_text().splitlines()
        for event in json.loads(line)
        if event["type"] == "log"
    ]
    assert TASK[:9] not in "".join(messages)
    assert TASK[9:] not in "".join(messages)
    assert "completed" in "".join(messages)
    assert capture.paths["stdout"].read_text() == f"task={TASK} completed\n"
    receipt = json.loads((publisher.directory / "publisher-receipt.json").read_text())
    assert receipt == capture.offsets()


def test_invalid_utf8_does_not_corrupt_acknowledged_byte_offsets(tmp_path: Path) -> None:
    from clearml_yolo.adapters.clearml.console_worker import PublicationState, publish_batch

    source = tmp_path / "stdout"
    source.write_bytes(b"\xffpartial")
    messages: list[str] = []

    class Sink:
        def report_text(self, message: str, **_kwargs: object) -> None:
            messages.append(message)

        def flush(self, **_kwargs: object) -> bool:
            return True

    state = PublicationState()
    first = publish_batch({"stdout": source}, {"stdout": 0}, Sink(), state=state)
    assert first == {"stdout": 0}
    final = publish_batch({"stdout": source}, first, Sink(), state=state, final=True)
    assert final == {"stdout": source.stat().st_size}
    assert messages == ["\ufffdpartial"]


def test_scalar_journal_keeps_stable_distinct_aliases_across_checkpoint_batches(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.clearml.console_worker import PublicationState, publish_batch

    names = [TASK, "fedcba9876543210" * 2, "[task]", "[task] (2)"]
    path = tmp_path / "scalars.jsonl"
    path.touch()
    events: list[dict[str, object]] = []

    class Sink:
        def report_scalar(self, **record: object) -> None:
            events.append(record)

        def flush(self, **_kwargs: object) -> bool:
            return True

    state = PublicationState()
    offsets = {"scalars": 0}
    raw: list[dict[str, object]] = []
    for iteration, (title, series) in enumerate(
        [
            (names[0], names[0]),
            (names[0], names[1]),
            (names[0], names[0]),
            (names[0], names[2]),
            (names[0], names[3]),
            (names[1], names[0]),
            (names[2], names[0]),
            (names[0], names[1]),
        ]
    ):
        record = {
            "title": title,
            "series": series,
            "value": iteration + 0.125,
            "iteration": iteration,
        }
        raw.append(record)
        with path.open("a") as output:
            output.write(json.dumps(record) + "\n")
        target = {"scalars": path.stat().st_size}
        offsets = publish_batch(
            {"scalars": path},
            offsets,
            Sink(),
            limits=target,
            state=state,
            checkpoint=True,
        )
        assert offsets == target
    assert events[0]["series"] == events[2]["series"]
    assert events[1]["series"] == events[7]["series"]
    assert len({events[index]["series"] for index in (0, 1, 3, 4)}) == 4
    assert len({events[index]["title"] for index in (0, 5, 6)}) == 3
    assert [(event["value"], event["iteration"]) for event in events] == [
        (record["value"], record["iteration"]) for record in raw
    ]
    assert [json.loads(line) for line in path.read_text().splitlines()] == raw
    assert all(name not in str(events) for name in names[:2])


def test_checkpoint_waits_for_partial_utf8_then_reads_only_its_continuation(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.clearml.console_worker import PublicationState, publish_batch

    path = tmp_path / "stdout"
    encoded = "模型 done\n".encode()
    path.write_bytes(encoded[:1])
    events: list[str] = []

    class Sink:
        def report_text(self, message: str, **_kwargs: object) -> None:
            events.append(message)

        def flush(self, **_kwargs: object) -> bool:
            return True

    state = PublicationState()
    target = {"stdout": 1}
    offsets = publish_batch(
        {"stdout": path},
        {"stdout": 0},
        Sink(),
        limits=target,
        state=state,
        checkpoint=True,
    )
    assert offsets == {"stdout": 0}
    assert events == []
    with path.open("ab") as output:
        output.write(encoded[1:])
    offsets = publish_batch(
        {"stdout": path},
        offsets,
        Sink(),
        limits=target,
        state=state,
        checkpoint=True,
    )
    assert offsets == {"stdout": len("模".encode())}
    assert events == ["模"]
    offsets = publish_batch({"stdout": path}, offsets, Sink(), state=state, final=True)
    assert offsets == {"stdout": len(encoded)}
    assert "".join(events) == "模型 done"
    assert path.read_bytes() == encoded


def test_real_barrier_completes_split_utf8_without_claiming_unpublished_bytes(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.clearml.console import ConsolePublisher
    from clearml_yolo.adapters.observability.capture import OutputCapture

    capture = OutputCapture(tmp_path / "capture")
    capture.prepare()
    offline = tmp_path / "offline"
    offline.mkdir()
    publisher = ConsolePublisher(TASK, capture, timeout=5, offline_folder=offline)
    encoded = "模型 done\n".encode()
    capture.paths["stdout"].write_bytes(encoded[:1])

    def complete_character() -> None:
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            if (publisher.directory / "publisher-barrier.json").exists():
                with capture.paths["stdout"].open("ab") as output:
                    output.write(encoded[1:])
                return
            time.sleep(0.01)

    writer = threading.Thread(target=complete_character)
    writer.start()
    publisher.start()
    try:
        publisher.barrier()
    finally:
        writer.join(timeout=5)
        publisher.finish()
    events = [
        event["msg"]
        for line in (offline / "log.jsonl").read_text().splitlines()
        for event in json.loads(line)
        if event["type"] == "log"
    ]
    assert "".join(events) == "模型 done"
    assert capture.paths["stdout"].read_bytes() == encoded
    receipt = json.loads((publisher.directory / "publisher-receipt.json").read_text())
    assert receipt == capture.offsets()
