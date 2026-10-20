"""Pure native hyperparameter projection; full replay settings remain separate."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

NATIVE_EXECUTION_KEYS = frozenset({"device", "project", "name", "save_dir", "exist_ok", "data"})


def project_native_parameters(values: Mapping[str, Any]) -> dict[str, Any]:
    """Detach scientific native settings without removing nested semantic names/paths."""
    return deepcopy(
        {key: value for key, value in values.items() if key not in NATIVE_EXECUTION_KEYS}
    )
