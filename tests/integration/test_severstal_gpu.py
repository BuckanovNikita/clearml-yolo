"""Explicitly authorized native Kaggle acceptance for every registered preset."""

from collections.abc import Callable
from dataclasses import replace

import pytest

from severstal_harness import MODEL_SELECTIONS, VARIANTS, SeverstalOptions, run_scenario

pytestmark = pytest.mark.severstal_gpu


@pytest.fixture
def stand_options(severstal_options: SeverstalOptions, stand_project: Callable[[str], str]) -> SeverstalOptions:
    """Publish ``--severstal-clearml-project`` to its run-tagged project on the shared stand."""
    return replace(severstal_options, project=stand_project(severstal_options.project))


@pytest.mark.parametrize("selection", MODEL_SELECTIONS)
@pytest.mark.parametrize("variant", VARIANTS)
def test_native_severstal_smoke(stand_options: SeverstalOptions, selection: str, variant: str) -> None:
    run_scenario(stand_options, selection, variant)
