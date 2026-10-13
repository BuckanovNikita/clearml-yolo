"""Prediction verbosity stays independent of native training and model family."""

from clearml_yolo.adapters.yolo.config import prediction_defaults


def test_prediction_default_is_quiet_without_training_inheritance() -> None:
    assert prediction_defaults()["verbose"] is False
    assert prediction_defaults(inherit=False)["verbose"] is False


def test_native_translation_accepts_quiet_prediction() -> None:
    from clearml_yolo.adapters.integrations.detectors import DetectorRunner

    settings = DetectorRunner._native_prediction({"verbose": False, "conf": 0.001, "device": "cpu"})
    assert settings.conf == 0.001
    assert settings.device == "cpu"
