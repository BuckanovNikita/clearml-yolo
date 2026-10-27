"""Explicitly authorized native Kaggle acceptance for every registered preset."""

import pytest

from severstal_harness import MODEL_SELECTIONS, VARIANTS, SeverstalOptions, run_scenario

pytestmark = pytest.mark.severstal_gpu


@pytest.mark.parametrize("selection", MODEL_SELECTIONS)
@pytest.mark.parametrize("variant", VARIANTS)
def test_native_severstal_smoke(
    severstal_options: SeverstalOptions, selection: str, variant: str
) -> None:
    run_scenario(severstal_options, selection, variant)
