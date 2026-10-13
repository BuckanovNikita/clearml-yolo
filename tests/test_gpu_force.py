"""Forced device scheduling controls are removed from the direct command API."""

import pytest
from omegaconf import OmegaConf

from clearml_yolo.entrypoints.hydra.validation import reject_legacy_controls


@pytest.mark.parametrize("force", [True, False, "true", None])
def test_legacy_force_requires_migration_even_when_disabled(force: object) -> None:
    with pytest.raises(ValueError, match="direct commands preserve native devices"):
        reject_legacy_controls(OmegaConf.create({"autogpu": {"force": force}}))


def test_native_configuration_does_not_require_a_scheduling_policy() -> None:
    reject_legacy_controls(OmegaConf.create({"ultralytics": {"device": [2, 0]}}))
