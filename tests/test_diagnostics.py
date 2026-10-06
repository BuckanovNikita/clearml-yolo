"""Safe diagnostic output retains actionable evidence without exception payload leaks."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import override

import pytest
from loguru import logger

from clearml_yolo.diagnostics import exception_summary, log_exception, redact_text


@contextmanager
def captured(level: str) -> Iterator[list[str]]:
    messages: list[str] = []
    handle = logger.add(
        lambda message: messages.append(str(message)), level=level, format="{message}"
    )
    try:
        yield messages
    finally:
        logger.remove(handle)


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("connect mongodb://alice:secret@host/db failed E111", "mongodb://"),
        ("connect mongodb://alice:secret@[broken failed E111", "secret"),
        ("download https://host/file?access_token=abc failed E111", "abc"),
        ('password="two words" failed E111', "two words"),
        ("{'api_key': 'two words', 'code': 'E111'}", "two words"),
        ("token=two words; code=E111", "two words"),
        ("Authorization: Bearer abc.def\nE111", "abc.def"),
        ("Cookie: session=abc; refresh=xyz\nE111", "abc"),
    ],
)
def test_redaction_removes_credentials_but_preserves_error_code(text: str, forbidden: str) -> None:
    result = redact_text(text)
    assert forbidden not in result
    assert "E111" in result
    assert "<redacted>" in result


def test_redaction_preserves_ordinary_locations() -> None:
    assert redact_text("failed /tmp/model.pt errno=13 https://host/help") == (
        "failed /tmp/model.pt errno=13 https://host/help"
    )


def test_summary_preserves_messages_causes_empty_types_and_cycles() -> None:
    cause = OSError("checkpoint.pt missing")
    error = RuntimeError("publication failed")
    error.__cause__ = cause
    cause.__cause__ = error
    result = exception_summary(error)
    assert "RuntimeError: publication failed" in result
    assert "OSError: checkpoint.pt missing" in result
    assert result.count("RuntimeError") == 1
    assert exception_summary(OSError()) == "OSError"


def test_summary_respects_suppressed_context() -> None:
    error = RuntimeError("visible")
    error.__context__ = ValueError("hidden")
    assert "hidden" in exception_summary(error)
    error.__suppress_context__ = True
    assert "hidden" not in exception_summary(error)


def test_exception_with_broken_string_does_not_mask_original_failure() -> None:
    class BrokenError(Exception):
        @override
        def __str__(self) -> str:
            raise ValueError("broken formatting")

    assert "BrokenError" in exception_summary(BrokenError())


def raised_error() -> OSError:
    local_value = "unique-local-secret"
    try:
        raise OSError("checkpoint.pt unavailable E111 password=hidden-payload")  # noqa: TRY301
    except OSError as error:
        assert local_value
        return error


def test_info_is_concise_and_debug_has_frames_without_locals_or_source() -> None:
    error = raised_error()
    with captured("INFO") as info, captured("DEBUG") as debug:
        log_exception("Publication failed", error, context={"path": "checkpoint.pt"})
    info_output = "".join(info)
    debug_output = "".join(debug)
    assert "OSError: checkpoint.pt unavailable E111" in info_output
    assert "raised_error" not in info_output
    assert "test_diagnostics.py" in debug_output
    assert "raised_error" in debug_output
    assert "raise OSError" not in debug_output
    assert "unique-local-secret" not in debug_output
    assert "hidden-payload" not in debug_output


def test_context_secrets_and_message_are_redacted() -> None:
    with captured("DEBUG") as output:
        log_exception(
            "Failed token=message-secret; read checkpoint",
            OSError("connection mongodb://user:password@host/db refused"),
            context={
                "api_key": "context-secret",
                "path": "https://user:context-password@host/model.pt",
                "operation": "upload",
            },
        )
    result = "".join(output)
    for secret in ("message-secret", "context-secret", "context-password", "mongodb://"):
        assert secret not in result
    assert "upload" in result
    assert "checkpoint" in result


def test_opaque_payload_suppression_applies_to_causes_and_debug() -> None:
    error = raised_error()
    error.__cause__ = ValueError("opaque unlabelled secret")
    with captured("DEBUG") as output:
        log_exception("Configuration failed", error, include_message=False)
    result = "".join(output)
    assert "OSError" in result
    assert "ValueError" in result
    assert "test_diagnostics.py" in result
    assert "checkpoint.pt" not in result
    assert "opaque unlabelled secret" not in result


def test_log_records_never_attach_an_exception_for_sink_rendering() -> None:
    attached: list[object] = []
    handle = logger.add(lambda message: attached.append(message.record["exception"]), level="DEBUG")
    try:
        log_exception("Publication failed", raised_error())
    finally:
        logger.remove(handle)
    assert attached
    assert all(value is None for value in attached)


def test_explicit_cause_takes_precedence_over_implicit_context() -> None:
    error = RuntimeError("failed")
    error.__context__ = OSError("unrelated implicit failure")
    error.__cause__ = ValueError("explicit failure")
    result = exception_summary(error)
    assert "explicit failure" in result
    assert "unrelated implicit failure" not in result


@pytest.mark.parametrize("key", ["sig", "bearer"])
def test_signature_and_bearer_assignments_are_redacted(key: str) -> None:
    result = redact_text(f"{key}=unique-credential; E111")
    assert "unique-credential" not in result
    assert "E111" in result


def test_debug_level_diagnostic_emits_one_record_with_frames() -> None:
    with captured("DEBUG") as output:
        log_exception("Optional cache check failed", raised_error(), level="DEBUG")
    assert len(output) == 1
    assert "OSError" in output[0]
    assert "raised_error" in output[0]


def test_credential_uri_with_whitespace_password_is_removed_whole() -> None:
    result = redact_text("connect mongodb://user:two words@host/db failed E111")
    assert "mongodb://" not in result
    assert "two words" not in result
    assert "host/db" not in result
    assert "E111" in result


def test_escaped_quote_inside_dict_secret_does_not_expose_remainder() -> None:
    result = redact_text("{'password': 'two\\' words', 'code': 'E111'}")
    assert "two" not in result
    assert "words" not in result
    assert "E111" in result


@pytest.mark.parametrize("password", ["pa'ssword", 'pa"ssword', "pa<ssword"])
def test_malformed_uri_userinfo_with_delimiters_is_removed(password: str) -> None:
    result = redact_text(f"connection mongodb://user:{password}@host/db refused E111")
    assert "mongodb://" not in result
    assert password not in result
    assert "host/db" not in result
    assert "E111" in result


@pytest.mark.parametrize(
    "text",
    [
        "{'password': {'value': 'secret1', 'backup': 'secret2'}, 'code': 'E111'}",
        "password=['secret1','secret2']; code=E111",
        "password={'a': ['secret1', {'b': 'secret2'}]}; code=E111",
        "password={'a': 'secret1}\\'still', 'b': 'secret2'}; code=E111",
    ],
)
def test_entire_sensitive_composite_is_redacted(text: str) -> None:
    result = redact_text(text)
    assert "secret1" not in result
    assert "secret2" not in result
    assert "E111" in result
    assert "<redacted>" in result


def test_unbalanced_sensitive_composite_suppresses_remainder() -> None:
    result = redact_text("password={'value': 'secret1', 'backup': ['secret2'; unsafe remainder")
    assert "secret1" not in result
    assert "secret2" not in result
    assert "unsafe remainder" not in result


@pytest.mark.parametrize("suffix", ["", " host/db failed E111", "<host>/db failed E111"])
def test_malformed_credential_uri_without_valid_host_is_redacted(suffix: str) -> None:
    result = redact_text("connect mongodb://user:pa'ssword@" + suffix)
    assert "pa'ssword" not in result
    assert "mongodb://" not in result
    assert "<redacted>" in result
