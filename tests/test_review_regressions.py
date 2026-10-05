"""Regression coverage for the October 2026 review findings."""

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from clearml_yolo import artifact_names
from clearml_yolo.clearml_models import _anchored
from clearml_yolo.clearml_session import configuration_secrets, sanitize_configuration
from clearml_yolo.comparison.assemble import _verdict
from clearml_yolo.comparison.scoring import EvaluationConfig
from clearml_yolo.comparison.significance import adjust_benjamini_hochberg
from clearml_yolo.filesystem import _fiftyone_inputs
from clearml_yolo.gpu_queue import _Request
from clearml_yolo.ground_truth import _image_size, _parse_label_file
from clearml_yolo.native_runtime import _is_worker


@pytest.mark.parametrize("name", ["alpha-junk", "junk-beta", "alpha\n"])
def test_baseline_pattern_rejects_partial_names(name: str) -> None:
    assert re.search(_anchored("alpha|beta") or "", name) is None


@pytest.mark.parametrize("key", ["X-Amz-Signature", "X-Goog-Signature"])
def test_provider_signature_storage_redaction(key: str) -> None:
    raw = {"url": f"https://example.test/object?{key}=private&safe=yes", key: "private"}
    sanitized = sanitize_configuration(raw)
    assert "private" not in json.dumps(sanitized)
    assert "safe=yes" in sanitized["url"]
    assert "private" in configuration_secrets(raw)
    assert raw[key] == "private"


@pytest.mark.parametrize("q", [-1.0, 2.0, math.nan, math.inf, -math.inf])
def test_significance_rejects_invalid_q(q: float) -> None:
    with pytest.raises(ValueError, match="q"):
        adjust_benjamini_hochberg([0.9], q)
    with pytest.raises(ValueError, match="q"):
        _verdict(0.1, 0.9, q)


@pytest.mark.parametrize(
    "values",
    [
        {"matching_strategy": "typo"},
        {"ap_method": "typo"},
        {"iou_threshold": math.nan},
        {"iou_threshold": math.inf},
        {"iou_threshold": -0.1},
        {"iou_threshold": 1.1},
    ],
)
def test_evaluation_rejects_invalid_options(values: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="validation error"):
        EvaluationConfig.model_validate(values)


@pytest.mark.parametrize("orientation", [6, 8])
def test_ground_truth_uses_native_exif_dimensions(tmp_path: Path, orientation: int) -> None:
    image = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[274] = orientation
    Image.new("RGB", (20, 30)).save(image, exif=exif)
    original = image.read_bytes()
    assert _image_size(image) == (30, 20)
    assert image.read_bytes() == original


@pytest.mark.parametrize(
    "coordinates",
    ["nan 0.5 0.2 0.2", "inf 0.5 0.2 0.2", "2 0.5 0.2 0.2", "-0.1 0.5 0.2 0.2", "0.5 0.5 1.1 0.2"],
)
def test_ground_truth_rejects_invalid_coordinates(tmp_path: Path, coordinates: str) -> None:
    label = tmp_path / "image.txt"
    label.write_text(f"0 {coordinates}\n")
    with pytest.raises(ValueError, match=r"image\.txt:1"):
        _parse_label_file(label, {0: "object"})


@pytest.mark.parametrize("content", ["{malformed", "[]"])
def test_optional_fiftyone_configuration_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    config = tmp_path / "config.json"
    config.write_text(content)
    monkeypatch.setenv("FIFTYONE_CONFIG_PATH", str(config))
    assert _fiftyone_inputs() == {}


def test_ownerless_rank_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CY_CLEARML_OWNER_PID", raising=False)
    monkeypatch.setenv("LOCAL_RANK", "0")
    with pytest.raises(ValueError, match="LOCAL_RANK"):
        _is_worker()


def test_impossible_partial_reservation_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="reservation size"):
        _Request.parse(
            {
                "ticket": 1,
                "count": 3,
                "visible": ["a", "b", "c"],
                "devices": ["a", "b"],
                "state": "active",
            }
        )


def test_split_artifact_component_is_safe_and_collision_free() -> None:
    encoded = artifact_names.per_split("report", "../../../escape/actual")
    assert "/" not in encoded
    assert "\\" not in encoded
    assert encoded != artifact_names.per_split("report", "..%2F..%2F..%2Fescape%2Factual")


@pytest.mark.parametrize("q", [0.0, 1.0])
def test_significance_accepts_probability_endpoints(q: float) -> None:
    result = adjust_benjamini_hochberg([0.0, 1.0], q)
    assert result.q == q
    assert result.rejected == [True, q == 1.0]


@pytest.mark.parametrize(
    "coordinates", ["-0.01 0.5 0.2 0.2", "1.01 0.5 0.2 0.2", "0.5 0.5 1.01 1.01"]
)
def test_ground_truth_preserves_native_coordinate_tolerance(
    tmp_path: Path, coordinates: str,
) -> None:
    label = tmp_path / "image.txt"
    label.write_text(f"0 {coordinates}\n")
    assert len(_parse_label_file(label, {0: "object"})) == 1


@pytest.mark.parametrize(
    ("name", "matched"),
    [("alpha", True), ("beta", True), ("alpha\n", False), ("junk-beta", False)],
)
def test_baseline_whole_name_anchor_with_pcre(name: str, matched: bool) -> None:
    """ClearML passes regexes to MongoDB's PCRE engine, whose end anchor permits a final newline."""
    grep = shutil.which("grep")
    if grep is None:
        pytest.skip("PCRE oracle requires grep with -Pz support")
    probe = subprocess.run(  # noqa: S603 - fixed executable/options, synthetic input only
        [grep, "-Pzq", ""], input=b"probe", capture_output=True, check=False,
    )
    if probe.returncode != 0:
        pytest.skip("grep does not support the PCRE whole-record oracle")
    result = subprocess.run(  # noqa: S603 - fixed executable/options, synthetic input only
        [grep, "-Pzq", _anchored("alpha|beta") or ""],
        input=name.encode(), capture_output=True, check=False,
    )
    assert result.returncode in (0, 1), result.stderr.decode()
    assert (result.returncode == 0) is matched
