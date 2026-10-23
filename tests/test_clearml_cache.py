"""Controller cache identity uses the installed SDK's actual hashing callback path."""

import json
from collections.abc import Callable
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from clearml_yolo.adapters.clearml.cache import normalize_task_hash

# These tests intentionally exercise the installed SDK's vendored legacy parser.
pytestmark = pytest.mark.filterwarnings("ignore::pyparsing.PyparsingDeprecationWarning")

IDENTITY = "a" * 64


def _run(root: str = "/cache/one", device: Any = None) -> dict[str, Any]:
    return {
        "ground_truth": "/inputs/truth.csv",
        "dataset_format": "ndjson",
        "dataset_cache_dir": root,
        "run_id": root,
        "run_dir": root + "/outputs",
        "clearml": {"task_name": root, "project_name": root, "tags": [root], "output_uri": root},
        "prepared_dataset": {"cache_identity": IDENTITY, "root": root},
        "ultralytics": {
            "device": [0, 1] if device is None else device,
            "project": root,
            "name": root,
            "save_dir": root,
            "exist_ok": False,
            "data": root + "/data.yaml",
            "model": "/weights/model.pt",
            "epochs": 2,
            "batch": 4,
        },
        "ultralytics_predict": {"device": "0,1", "conf": 0.1},
        "training_data_overrides": {
            "data": {"requested": None, "effective": root + "/data.yaml"},
            "classes": {"requested": [0], "effective": None},
        },
        "display_names": {"requested": root, "effective": root},
        "fiftyone_result": {"dataset_name": root, "run_key": root, "sample_count": 2},
        "prediction_result": {
            "native_normalization": {"imgsz": {"requested": 63, "effective": 64}}
        },
    }


def _representation(root: str = "/cache/one", device: Any = None) -> dict[str, Any]:
    return {
        "script": {"entry_point": "-m clearml_yolo.entrypoints.train", "version_num": "abc123"},
        "hyper_params": {
            "General/device": "[0, 1]" if device is None else device,
            "General/name": root,
            "General/project": root,
            "General/data": root + "/data.yaml",
            "General/epochs": "2",
        },
        "configs": {
            "run": json.dumps(_run(root, device)),
            "dataset": yaml.safe_dump({"path": root, "train": "images/train", "names": {0: "cat"}}),
            "unknown": "untouched: literal text\n",
        },
        "docker": {"image": "image:1", "arguments": "--ipc=host"},
    }


@pytest.fixture
def sdk_hash(monkeypatch: pytest.MonkeyPatch) -> Callable[..., str]:
    from clearml.automation.job import ClearmlJob
    from clearml.backend_api.session import Session

    monkeypatch.setattr(ClearmlJob, "_hashing_callback", None)
    monkeypatch.setattr(Session, "check_min_api_version", lambda _: True)
    ClearmlJob.register_hashing_callback(normalize_task_hash)

    def hash_task(representation: dict[str, Any], **overrides: Any) -> str:
        task: Any = SimpleNamespace(
            data=SimpleNamespace(
                script=SimpleNamespace(to_dict=lambda: representation["script"]),
                container=representation.get("docker", {}),
            ),
            get_parameters=lambda: representation["hyper_params"],
            get_configuration_objects=lambda: representation["configs"],
        )
        digest = ClearmlJob._create_task_hash(
            task,
            explicit_docker_image=representation.get("docker", {}).get("image"),
            **overrides,
        )
        assert isinstance(digest, str)
        return digest

    return hash_task


def test_sdk_hash_ignores_routing_and_cuda_indices(sdk_hash: Callable[..., str]) -> None:
    first = _representation()
    second = _representation("/different/cache", [2, 3])
    assert sdk_hash(first) == sdk_hash(second)
    assert sdk_hash(
        first, params_override=second["hyper_params"], configurations_override=second["configs"]
    ) == sdk_hash(first)


@pytest.mark.parametrize("device", [[2, 3], "2,3", "[2, 3]", ["2", "3"], "cuda:2,cuda:3"])
def test_cuda_selector_spellings_share_identity(device: Any, sdk_hash: Callable[..., str]) -> None:
    assert sdk_hash(_representation(device=device)) == sdk_hash(_representation())


@pytest.mark.parametrize("device", [[0], "cpu", "mps", "cuda", -1, "-1,-1", "", [0, 0], True])
def test_device_types_counts_and_unresolved_selectors_differ(
    device: Any, sdk_hash: Callable[..., str]
) -> None:
    assert sdk_hash(_representation(device=device)) != sdk_hash(_representation())


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("ultralytics", "epochs"), 3),
        (("ultralytics", "batch"), 8),
        (("ultralytics", "model"), "/other/model.pt"),
        (("ultralytics_predict", "conf"), 0.2),
        (("prepared_dataset", "cache_identity"), "b" * 64),
        (("ground_truth",), "/other/truth.csv"),
        (("dataset_format",), "coco"),
        (("training_data_overrides", "classes", "requested"), [1]),
        (("prediction_result", "native_normalization", "imgsz", "effective"), 96),
        (("unknown_result",), {"name": "scientific", "device": 7, "path": "/cache/one"}),
    ],
)
def test_semantic_and_unknown_run_settings_remain_sensitive(
    path: tuple[str, ...], value: Any, sdk_hash: Callable[..., str]
) -> None:
    first = _representation()
    second = deepcopy(first)
    run = json.loads(second["configs"]["run"])
    target = run
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    second["configs"]["run"] = json.dumps(run)
    assert sdk_hash(first) != sdk_hash(second)


@pytest.mark.parametrize("section", ["script", "docker", "hyper_params", "configs"])
def test_code_container_and_unknown_fields_remain_sensitive(
    section: str, sdk_hash: Callable[..., str]
) -> None:
    first = _representation()
    second = deepcopy(first)
    second[section]["unknown"] = "changed"
    assert sdk_hash(first) != sdk_hash(second)


def test_projection_is_detached_deterministic_and_idempotent() -> None:
    original = _representation()
    snapshot = deepcopy(original)
    projected = normalize_task_hash(original)
    assert original == snapshot
    assert projected is not original
    assert normalize_task_hash(projected) == projected
    assert projected["script"] == original["script"]
    assert projected["docker"] == original["docker"]
    assert projected["configs"]["unknown"] == original["configs"]["unknown"]
    run = json.loads(original["configs"]["run"])
    original["configs"]["run"] = json.dumps(dict(reversed(list(run.items()))), indent=4)
    assert normalize_task_hash(original) == projected
    projected["script"]["version_num"] = "new"
    assert original["script"] == snapshot["script"]


@pytest.mark.parametrize(
    "entry_point",
    [
        "train.py",
        "-m cy_queue.entrypoints.queue",
        "-m other.train",
        "-m clearml_yolo.entrypoints.train --unknown",
        None,
    ],
)
def test_only_canonical_execution_modules_are_normalized(entry_point: Any) -> None:
    original = _representation()
    original["script"]["entry_point"] = entry_point
    assert normalize_task_hash(original) == original
    assert normalize_task_hash(original) is not original


@pytest.mark.parametrize(
    "document",
    [
        "ultralytics {device = [0, 1]}",
        "{",
        "[]",
        "null",
        '{"x":NaN}',
        '{"x":1,"x":2}',
        '{"ultralytics": {"device": [0,1]}, "output":"a", "output":"b"}',
    ],
)
def test_unsupported_run_documents_are_preserved(document: str) -> None:
    representation = _representation()
    representation["configs"]["run"] = document
    normalized = normalize_task_hash(representation)
    assert normalized["configs"]["run"] == document
    assert normalized["configs"]["dataset"] == representation["configs"]["dataset"]


@pytest.mark.parametrize(
    "document",
    [
        "path: /cache/one\npath: /other\n",
        "x: &self [*self]\n",
        "date: 2026-10-16\n",
        "!!python/object:unsafe {}",
        "null",
        "[a, b]",
    ],
)
def test_unsupported_dataset_documents_are_preserved(document: str) -> None:
    representation = _representation()
    representation["configs"]["dataset"] = document
    assert normalize_task_hash(representation)["configs"]["dataset"] == document


def test_dataset_class_key_types_and_split_semantics_remain_sensitive(
    sdk_hash: Callable[..., str],
) -> None:
    first = _representation()
    second = deepcopy(first)
    second["configs"]["dataset"] = yaml.safe_dump(
        {"path": "/cache/one", "train": "images/train", "names": {"0": "cat"}}
    )
    assert sdk_hash(first) != sdk_hash(second)
    second["configs"]["dataset"] = yaml.safe_dump(
        {"path": "/cache/one", "train": "images/val", "names": {0: "cat"}}
    )
    assert sdk_hash(first) != sdk_hash(second)


@pytest.mark.parametrize("identity", [None, "", "not-a-digest"])
def test_unproven_generated_paths_remain_sensitive(
    identity: Any, sdk_hash: Callable[..., str]
) -> None:
    values = []
    for root in ("/cache/one", "/cache/two"):
        representation = _representation(root)
        run = json.loads(representation["configs"]["run"])
        run["prepared_dataset"]["cache_identity"] = identity
        representation["configs"]["run"] = json.dumps(run)
        values.append(representation)
    assert sdk_hash(values[0]) != sdk_hash(values[1])


def test_only_proven_dataset_paths_are_rewritten() -> None:
    representation = _representation()
    run = json.loads(representation["configs"]["run"])
    run["ultralytics"]["model"] = "/cache/one/model.pt"
    run["unknown"] = {"path": "/cache/one/input.bin"}
    representation["configs"]["run"] = json.dumps(run)
    normalized = json.loads(normalize_task_hash(representation)["configs"]["run"])
    assert normalized["ultralytics"]["model"] == "/cache/one/model.pt"
    assert normalized["unknown"] == run["unknown"]
    assert normalized["ultralytics"]["data"] != "/cache/one/data.yaml"


def test_safe_yaml_aliases_are_detached_and_deterministic() -> None:
    representation = _representation()
    representation["configs"]["dataset"] = (
        "path: /cache/one\ntrain: &split [images/train]\nval: *split\nnames: {0: cat}\n"
    )
    normalized = normalize_task_hash(representation)
    document = yaml.safe_load(normalized["configs"]["dataset"])
    assert document["train"] == document["val"] == ["images/train"]
    assert document["names"] == {0: "cat"}


@pytest.mark.parametrize(
    "path",
    [
        ("model", "train"),
        ("model", "predict"),
        ("export",),
        ("inference",),
        ("inference", "ultralytics"),
        ("compare", "inference"),
        ("comparison", "inference"),
    ],
)
def test_devices_in_known_model_and_inference_groups(
    path: tuple[str, ...], sdk_hash: Callable[..., str]
) -> None:
    values = []
    for device in ("0", [2], "cpu"):
        representation = _representation()
        run = json.loads(representation["configs"]["run"])
        target = run
        for key in path:
            target = target.setdefault(key, {})
        if path == ("export",):
            target["operation"] = "build"
        target["device"] = device
        target["unknown"] = {"name": "science", "path": "/input"}
        representation["configs"]["run"] = json.dumps(run)
        values.append(representation)
    assert sdk_hash(values[0]) == sdk_hash(values[1])
    assert sdk_hash(values[0]) != sdk_hash(values[2])
    normalized = json.loads(normalize_task_hash(values[0])["configs"]["run"])
    target = normalized
    for key in path:
        target = target[key]
    assert target["unknown"] == {"name": "science", "path": "/input"}


@pytest.mark.parametrize(
    "path", [("training_normalization",), ("prediction_result", "native_normalization")]
)
def test_recorded_native_normalization_preserves_science_and_normalizes_routing(
    path: tuple[str, ...], sdk_hash: Callable[..., str]
) -> None:
    values = []
    for root, device in (("/cache/one", [0, 1]), ("/other/cache", [2, 3])):
        representation = _representation(root)
        run = json.loads(representation["configs"]["run"])
        target = run
        for key in path:
            target = target.setdefault(key, {})
        target.update(
            device={"requested": device, "effective": device},
            project={"requested": root, "effective": root},
            name={"requested": root, "effective": root},
            imgsz={"requested": 63, "effective": 64},
        )
        representation["configs"]["run"] = json.dumps(run)
        values.append(representation)
    assert sdk_hash(values[0]) == sdk_hash(values[1])


@pytest.mark.parametrize("field", ["script", "hyper_params", "configs"])
@pytest.mark.parametrize("value", [None, [], "unknown"])
def test_unknown_representation_shapes_are_preserved(field: str, value: Any) -> None:
    representation = _representation()
    representation[field] = value
    assert normalize_task_hash(representation)[field] == value


@pytest.mark.parametrize("entrypoint", [[], {}])
def test_non_scalar_entrypoints_remain_unchanged(entrypoint: Any) -> None:
    representation = _representation()
    representation["script"]["entry_point"] = entrypoint
    assert normalize_task_hash(representation) == representation


def test_unknown_fields_in_known_result_records_remain_sensitive(
    sdk_hash: Callable[..., str],
) -> None:
    first = _representation()
    second = deepcopy(first)
    run = json.loads(second["configs"]["run"])
    run["fiftyone_result"]["future_scientific_setting"] = 4
    second["configs"]["run"] = json.dumps(run)
    assert sdk_hash(first) != sdk_hash(second)


@pytest.mark.parametrize("root", ["/", "relative", "/tmp/../cache"])
def test_ambiguous_dataset_roots_do_not_authorize_normalization(root: str) -> None:
    representation = _representation(root)
    original = representation["configs"]["dataset"]
    assert normalize_task_hash(representation)["configs"]["dataset"] == original


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("script", "version_num", "new-revision"),
        ("script", "diff", "+ scientific_code_change()"),
        ("docker", "image", "image:2"),
        ("docker", "arguments", "--other-argument"),
        ("hyper_params", "General/epochs", "3"),
        ("hyper_params", "Unknown/device", "[2, 3]"),
    ],
)
def test_sdk_semantic_overrides_invalidate_cache(
    section: str, field: str, value: str, sdk_hash: Callable[..., str]
) -> None:
    first = _representation()
    second = deepcopy(first)
    second[section][field] = value
    assert sdk_hash(first) != sdk_hash(second)


def test_dataset_class_names_are_scientific(sdk_hash: Callable[..., str]) -> None:
    first = _representation()
    second = deepcopy(first)
    dataset = yaml.safe_load(second["configs"]["dataset"])
    dataset["names"][0] = "dog"
    second["configs"]["dataset"] = yaml.safe_dump(dataset)
    assert sdk_hash(first) != sdk_hash(second)


def test_new_policy_cannot_silently_replace_existing_representation_data() -> None:
    representation = _representation()
    representation["_clearml_yolo_cache_policy"] = "unknown-policy"
    assert normalize_task_hash(representation) == representation


@pytest.mark.parametrize(
    ("device", "malformed"),
    [([0, 1], {"type": "cuda", "count": 2}), ("cpu", {"type": "cpu"})],
)
@pytest.mark.parametrize("location", ["General", "run"])
def test_invalid_device_mappings_cannot_impersonate_normalized_selectors(
    device: Any, malformed: dict[str, Any], location: str, sdk_hash: Callable[..., str]
) -> None:
    valid = _representation(device=device)
    invalid = deepcopy(valid)
    if location == "General":
        invalid["hyper_params"]["General/device"] = malformed
    else:
        run = json.loads(invalid["configs"]["run"])
        run["ultralytics"]["device"] = malformed
        invalid["configs"]["run"] = json.dumps(run)
    assert sdk_hash(valid) != sdk_hash(invalid)
    assert normalize_task_hash(invalid) == invalid
    assert normalize_task_hash(invalid) is not invalid


@pytest.mark.parametrize("location", ["General", "run", "dataset"])
def test_raw_dataset_placeholders_cannot_impersonate_generated_paths(
    location: str, sdk_hash: Callable[..., str]
) -> None:
    valid = _representation()
    invalid = deepcopy(valid)
    if location == "General":
        invalid["hyper_params"]["General/data"] = f"clearml-yolo-dataset://{IDENTITY}/data.yaml"
    elif location == "run":
        run = json.loads(invalid["configs"]["run"])
        run["ultralytics"]["data"] = f"clearml-yolo-dataset://{IDENTITY}/data.yaml"
        invalid["configs"]["run"] = json.dumps(run)
    else:
        dataset = yaml.safe_load(invalid["configs"]["dataset"])
        dataset["path"] = f"clearml-yolo-dataset://{IDENTITY}/."
        invalid["configs"]["dataset"] = yaml.safe_dump(dataset)
    assert sdk_hash(valid) != sdk_hash(invalid)
    assert normalize_task_hash(invalid) == invalid


@pytest.mark.parametrize(
    ("escaped", "other"),
    [
        (r'"\u043a\u043e\u0442"', '"кот"'),
        (r'"a\/b"', '"a/b"'),
        (r'"a\bb"', r'"a\u0008b"'),
        (r'"a\fb"', r'"a\u000cb"'),
        (r'"\\\u0061"', r'"\\a"'),
    ],
)
def test_sdk_incompatible_json_escape_spellings_cannot_share_identity(
    escaped: str, other: str, sdk_hash: Callable[..., str]
) -> None:
    from clearml.utilities.config import text_to_config_dict

    documents = []
    for token in (escaped, other):
        representation = _representation()
        run = json.loads(representation["configs"]["run"])
        run["ground_truth"] = "REPLACE_INPUT_STRING"
        document = json.dumps(run, ensure_ascii=False).replace('"REPLACE_INPUT_STRING"', token)
        representation["configs"]["run"] = document
        documents.append(representation)
    first, second = [item["configs"]["run"] for item in documents]
    assert json.loads(first) == json.loads(second)
    assert text_to_config_dict(first)["ground_truth"] != text_to_config_dict(second)["ground_truth"]
    assert sdk_hash(documents[0]) != sdk_hash(documents[1])
    assert normalize_task_hash(documents[0]) == documents[0]
    assert normalize_task_hash(documents[0]) is not documents[0]


def test_sdk_incompatible_json_key_escape_preserves_entire_representation(
    sdk_hash: Callable[..., str],
) -> None:
    from clearml.utilities.config import text_to_config_dict

    literal = _representation()
    escaped = deepcopy(literal)
    escaped["configs"]["run"] = literal["configs"]["run"].replace(
        '"ground_truth"', r'"\u0067round_truth"'
    )
    assert json.loads(literal["configs"]["run"]) == json.loads(escaped["configs"]["run"])
    assert text_to_config_dict(literal["configs"]["run"]) != text_to_config_dict(
        escaped["configs"]["run"]
    )
    assert sdk_hash(literal) != sdk_hash(escaped)
    assert normalize_task_hash(escaped) == escaped


@pytest.mark.parametrize("value", [r"\u0061", r"\/", r"\b", r"\f", 'quoted " text ' + r"\u0061"])
def test_literal_backslash_sequences_remain_normalizable(
    value: str, sdk_hash: Callable[..., str]
) -> None:
    from clearml.utilities.config import text_to_config_dict

    representations = []
    for root in ("/cache/one", "/cache/two"):
        representation = _representation(root)
        run = json.loads(representation["configs"]["run"])
        run["scientific_literal"] = value
        representation["configs"]["run"] = json.dumps(run, ensure_ascii=False)
        assert text_to_config_dict(representation["configs"]["run"])["scientific_literal"] == value
        normalized = normalize_task_hash(representation)
        assert normalized["_clearml_yolo_cache_policy"] == 1
        assert json.loads(normalized["configs"]["run"])["scientific_literal"] == value
        assert normalize_task_hash(normalized) == normalized
        representations.append(representation)
    assert sdk_hash(representations[0]) == sdk_hash(representations[1])


def test_normalized_run_keeps_literal_unicode_under_sdk_replay() -> None:
    from clearml.utilities.config import text_to_config_dict

    representation = _representation()
    run = json.loads(representation["configs"]["run"])
    run["ground_truth"] = "/данные/кот.csv"
    representation["configs"]["run"] = json.dumps(run, ensure_ascii=False)
    normalized = normalize_task_hash(representation)
    assert text_to_config_dict(normalized["configs"]["run"])["ground_truth"] == run["ground_truth"]


def _workflow_representation(command: str, run: dict[str, Any]) -> dict[str, Any]:
    return {
        "script": {
            "entry_point": f"-m clearml_yolo.entrypoints.{command}",
            "version_num": "abc123",
        },
        "hyper_params": {},
        "configs": {"run": json.dumps(run, ensure_ascii=False)},
    }


@pytest.mark.parametrize(
    ("command", "selectors"),
    [
        ("compare", {"baseline_model": {}, "candidate_model": {"task_id": "candidate"}}),
        ("compare", {"baseline_model": {"task_id": "baseline"}, "candidate_model": {}}),
        (
            "compare",
            {"baseline_model": {"project_name": ""}, "candidate_model": {"task_id": "candidate"}},
        ),
        ("pipeline", {"compare": {"baseline_model": {}}}),
        ("pipeline", {"compare": {}}),
        ("pipeline", {}),
    ],
)
def test_tracking_project_remains_scientific_for_fallback_model_lookup(
    command: str, selectors: dict[str, Any], sdk_hash: Callable[..., str]
) -> None:
    from clearml_yolo.application.contracts import ModelRef

    values = deepcopy(selectors)
    if command == "compare":
        for key in ("baseline_model", "candidate_model"):
            values[key] = ModelRef.model_validate(values[key]).model_dump(mode="json")
    elif "baseline_model" in values.get("compare", {}):
        values["compare"]["baseline_model"] = ModelRef.model_validate(
            values["compare"]["baseline_model"]
        ).model_dump(mode="json")
    representations = [
        _workflow_representation(
            command,
            {
                "ground_truth": "/input/truth.csv",
                "clearml": {"project_name": project},
                **values,
            },
        )
        for project in ("science-a", "science-b")
    ]
    assert sdk_hash(representations[0]) != sdk_hash(representations[1])


@pytest.mark.parametrize(
    ("command", "selectors"),
    [
        (
            "compare",
            {
                "baseline_model": {"task_id": "baseline"},
                "candidate_model": {"task_id": "candidate"},
            },
        ),
        (
            "compare",
            {
                "baseline_model": {"project_name": "inputs"},
                "candidate_model": {"project_name": "inputs"},
            },
        ),
        (
            "compare",
            {
                "baseline_model": {
                    "source": "local",
                    "weights": "/input/base.pt",
                    "thresholds": {"cat": 0.5},
                },
                "candidate_model": {
                    "source": "local",
                    "weights": "/input/candidate.pt",
                    "thresholds": {"cat": 0.5},
                },
            },
        ),
        ("pipeline", {"compare": {"baseline_model": {"task_id": "baseline"}}}),
        ("pipeline", {"skip_compare": True}),
    ],
)
def test_tracking_project_is_routing_only_when_model_lookup_is_independent(
    command: str, selectors: dict[str, Any], sdk_hash: Callable[..., str]
) -> None:
    representations = [
        _workflow_representation(
            command,
            {
                "ground_truth": "/input/truth.csv",
                "clearml": {"project_name": project},
                **selectors,
            },
        )
        for project in ("output-a", "output-b")
    ]
    assert sdk_hash(representations[0]) == sdk_hash(representations[1])


@pytest.mark.parametrize(
    "skip", ["skip_train", "skip_predict", "skip_metrics", "skip_compare", "skip_report"]
)
@pytest.mark.parametrize("destination", ["run_dir", "run_id"])
def test_pipeline_reuse_destinations_identify_consumed_inputs(
    skip: str, destination: str, sdk_hash: Callable[..., str]
) -> None:
    representations = [
        _workflow_representation(
            "pipeline",
            {
                "ground_truth": "/input/truth.csv",
                "clearml": {"project_name": "science"},
                skip: True,
                destination: directory,
            },
        )
        for directory in ("/runs/source-a", "/runs/source-b")
    ]
    assert sdk_hash(representations[0]) != sdk_hash(representations[1])


def test_complete_pipeline_output_relocation_remains_equivalent(
    sdk_hash: Callable[..., str],
) -> None:
    representations = [
        _workflow_representation(
            "pipeline",
            {
                "ground_truth": "/input/truth.csv",
                "clearml": {"project_name": "science"},
                "run_dir": directory,
                "run_id": directory,
                "skip_train": False,
                "skip_predict": False,
                "skip_metrics": False,
                "skip_compare": False,
                "skip_report": False,
            },
        )
        for directory in ("/runs/output-a", "/runs/output-b")
    ]
    assert sdk_hash(representations[0]) == sdk_hash(representations[1])


def test_device_list_string_does_not_decode_escaped_unresolved_selectors(
    sdk_hash: Callable[..., str],
) -> None:
    device = r'["\u0030", "\u0031"]'
    representation = _representation(device=device)
    assert sdk_hash(representation) != sdk_hash(_representation())
    normalized = normalize_task_hash(representation)
    assert normalized["hyper_params"]["General/device"] == device
    assert json.loads(normalized["configs"]["run"])["ultralytics"]["device"] == device


def _selector_representation(
    path: tuple[str, ...], device: Any, *, backend: str = "ultralytics", command: str = "train"
) -> dict[str, Any]:
    run: dict[str, Any] = {"model": {"backend": backend}, "export": {"operation": "build"}}
    target = run
    for key in path:
        target = target.setdefault(key, {})
    target["device"] = device
    return _workflow_representation(command, run)


@pytest.mark.parametrize("backend", ["deimv2", "rfdetr", "fasterrcnn"])
@pytest.mark.parametrize("stage", ["train", "predict"])
@pytest.mark.parametrize(
    ("valid", "invalid"),
    [("cpu", "CPU"), ("cpu", " cpu "), (0, "[0]"), (0, "CUDA:0"), (0, "0 "), (0, ["0"])],
)
def test_rejected_detector_selectors_cannot_hit_valid_cached_tasks(
    backend: str, stage: str, valid: Any, invalid: Any, sdk_hash: Callable[..., str]
) -> None:
    from clearml_yolo.adapters.deim.backend import _device as deim_device
    from clearml_yolo.adapters.fasterrcnn.inference import execution_device
    from clearml_yolo.adapters.rfdetr.backend import _device as rfdetr_device
    from clearml_yolo.core.models import PredictSettings, TrainSettings

    consumers = {"deimv2": deim_device, "rfdetr": rfdetr_device, "fasterrcnn": execution_device}
    settings = TrainSettings if stage == "train" else PredictSettings
    consumer = consumers[backend]
    assert str(consumer(settings.model_validate({"device": valid}).device)) in {"cpu", "cuda:0"}
    with pytest.raises((ValueError, RuntimeError)):
        consumer(settings.model_validate({"device": invalid}).device)
    representations = [
        _selector_representation(("model", stage), value, backend=backend)
        for value in (valid, invalid)
    ]
    assert sdk_hash(representations[0]) != sdk_hash(representations[1])


@pytest.mark.parametrize("invalid", ["00", "01", "cuda:00"])
def test_fasterrcnn_leading_zero_selectors_remain_distinct(
    invalid: str, sdk_hash: Callable[..., str]
) -> None:
    from clearml_yolo.adapters.fasterrcnn.inference import execution_device

    with pytest.raises(RuntimeError):
        execution_device(invalid)
    valid = _selector_representation(("model", "train"), 0, backend="fasterrcnn")
    rejected = _selector_representation(("model", "train"), invalid, backend="fasterrcnn")
    assert sdk_hash(valid) != sdk_hash(rejected)


@pytest.mark.parametrize(
    ("operation", "valid", "invalid"),
    [
        ("onnx", "cpu", "CPU"),
        ("onnx", "cpu", " cpu "),
        ("build", 0, "[0]"),
        ("build", 0, ["0"]),
        ("build", 0, "CUDA:0"),
        ("build", 0, "0 "),
        ("verify", 0, "[0]"),
    ],
)
def test_rejected_export_selectors_cannot_hit_valid_cached_tasks(
    operation: str, valid: Any, invalid: Any, sdk_hash: Callable[..., str]
) -> None:
    from clearml_yolo.core.export_requests import ExportSettings

    ExportSettings.model_validate({"operation": operation, "device": valid})
    with pytest.raises(ValueError, match=r"device|validation error"):
        ExportSettings.model_validate({"operation": operation, "device": invalid})
    values = [
        _workflow_representation("export", {"export": {"operation": operation, "device": device}})
        for device in (valid, invalid)
    ]
    assert sdk_hash(values[0]) != sdk_hash(values[1])


@pytest.mark.parametrize(
    "path", [("inference",), ("compare", "inference"), ("inference", "ultralytics")]
)
@pytest.mark.parametrize("invalid", ["[0]", "CUDA:0", "0 ", ["0"], "00", "0,1"])
def test_unknown_comparison_backend_uses_conservative_selectors(
    path: tuple[str, ...], invalid: Any, sdk_hash: Callable[..., str]
) -> None:
    values = [_selector_representation(path, value, command="compare") for value in (0, invalid)]
    assert sdk_hash(values[0]) != sdk_hash(values[1])


@pytest.mark.parametrize("invalid", ['["0", "1"]', "\t0,1\t", "0,1\n"])
def test_rejected_native_spellings_remain_distinct(
    invalid: str, sdk_hash: Callable[..., str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import torch
    from ultralytics.utils.torch_utils import parse_device, select_device

    # Only discovery is stubbed; the installed parser/validator execute, without
    # allocating CUDA tensors or making a device-selection call.
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 4)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    assert parse_device([0, 1]) == "0,1"
    assert parse_device(invalid) != "0,1"
    native_selector: Any = select_device  # The installed SDK function has no type annotations.
    with pytest.raises(ValueError, match="Invalid CUDA"):
        native_selector(invalid, verbose=False)
    assert sdk_hash(_representation(device=invalid)) != sdk_hash(_representation())


@pytest.mark.parametrize("path", [("ultralytics",), ("ultralytics_predict",)])
def test_non_yolo_native_override_groups_retain_rejected_spellings(
    path: tuple[str, ...], sdk_hash: Callable[..., str]
) -> None:
    values = [_selector_representation(path, value, backend="rfdetr") for value in ("cpu", "CPU")]
    assert sdk_hash(values[0]) != sdk_hash(values[1])


def test_non_yolo_general_selectors_retain_rejected_spellings(sdk_hash: Callable[..., str]) -> None:
    values = []
    for device in ("cpu", "CPU"):
        representation = _selector_representation(("model", "train"), "cpu", backend="rfdetr")
        representation["hyper_params"]["General/device"] = device
        values.append(representation)
    assert sdk_hash(values[0]) != sdk_hash(values[1])


@pytest.mark.parametrize("backend", ["ultralytics", "deimv2", "rfdetr", "fasterrcnn"])
@pytest.mark.parametrize("stage", ["train", "predict"])
def test_typed_model_groups_preserve_invalid_string_lists(
    backend: str, stage: str, sdk_hash: Callable[..., str]
) -> None:
    from clearml_yolo.core.models import PredictSettings, TrainSettings

    schema = TrainSettings if stage == "train" else PredictSettings
    with pytest.raises(ValueError, match="valid integer"):
        schema.model_validate({"device": ["0"]})
    values = [
        _selector_representation(("model", stage), device, backend=backend)
        for device in ([0], ["0"])
    ]
    assert sdk_hash(values[0]) != sdk_hash(values[1])


@pytest.mark.parametrize("backend", ["deimv2", "rfdetr", "fasterrcnn"])
@pytest.mark.parametrize("device", [2, [2], "2", "cuda:2"])
def test_strict_consumers_still_ignore_valid_gpu_index_changes(
    backend: str, device: Any, sdk_hash: Callable[..., str]
) -> None:
    values = [
        _selector_representation(("model", "train"), value, backend=backend)
        for value in (0, device)
    ]
    assert sdk_hash(values[0]) == sdk_hash(values[1])


@pytest.mark.parametrize("operation", ["onnx", "build", "verify", [], {}])
def test_export_projection_handles_operation_shapes_conservatively(operation: Any) -> None:
    representation = _workflow_representation(
        "export", {"export": {"operation": operation, "device": "CPU"}}
    )
    normalized = normalize_task_hash(representation)
    assert json.loads(normalized["configs"]["run"])["export"] == {
        "operation": operation,
        "device": "CPU",
    }


@pytest.mark.parametrize("document", [None, "model { backend = fasterrcnn }"])
@pytest.mark.parametrize("invalid", ["CPU", "[0]", "0 ", ["0"], "00"])
def test_unparsed_run_keeps_general_selectors_conservative(
    document: str | None, invalid: Any, sdk_hash: Callable[..., str]
) -> None:
    values = []
    for device in ("cpu" if invalid == "CPU" else 0, invalid):
        representation = _workflow_representation("train", {})
        representation["configs"] = {} if document is None else {"run": document}
        representation["hyper_params"]["General/device"] = device
        values.append(representation)
    assert sdk_hash(values[0]) != sdk_hash(values[1])


def test_derived_overrides_do_not_affect_recognized_task_hash(sdk_hash: Callable[..., str]) -> None:
    first = _representation()
    second = deepcopy(first)
    second["configs"]["run_overrides"] = json.dumps({"ultralytics": {"weight_decay": 0.02}})
    assert sdk_hash(first) == sdk_hash(second)
    assert "run_overrides" in second["configs"]
    for value in ("malformed", "{}", None):
        second["configs"]["run_overrides"] = value
        assert normalize_task_hash(first) == normalize_task_hash(second)
    second["script"]["entry_point"] = "unrelated.py"
    assert normalize_task_hash(second) == second


@pytest.mark.parametrize("ambiguous", [True, False])
def test_derived_overrides_stay_informational_when_recognized_projection_is_unsafe(
    ambiguous: bool,
) -> None:
    first = _representation()
    if ambiguous:
        # Installed SDK's HOCON parser and JSON disagree on unicode escapes.
        first["configs"]["run"] = '{"model": "\\u0041"}'
    else:
        run = json.loads(first["configs"]["run"])
        run["ultralytics"]["device"] = {"invalid": "selector"}
        first["configs"]["run"] = json.dumps(run)
    second = deepcopy(first)
    second["configs"]["run_overrides"] = "private derived metadata"
    assert normalize_task_hash(first) == normalize_task_hash(second)
    assert normalize_task_hash(first) == first
    assert "run_overrides" in second["configs"]
