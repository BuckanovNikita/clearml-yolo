"""Pure native hyperparameter projection; full replay settings remain separate.

``General`` excludes execution routing (``device``, ``project``, ``name``, ``save_dir``,
``exist_ok``) and the CSV-generated ``data``. The projection is detached and unsanitized; the
session adds sanitization. The tracking session and the controller cache projection share
``NATIVE_EXECUTION_KEYS``, so changing it changes cache identity as well. This module must
not import ClearML or any execution SDK.
"""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

NATIVE_EXECUTION_KEYS = frozenset({"device", "project", "name", "save_dir", "exist_ok", "data"})


def project_native_parameters(values: Mapping[str, Any]) -> dict[str, Any]:
    """Detach scientific native settings without removing nested semantic names/paths."""
    return deepcopy({key: value for key, value in values.items() if key not in NATIVE_EXECUTION_KEYS})
