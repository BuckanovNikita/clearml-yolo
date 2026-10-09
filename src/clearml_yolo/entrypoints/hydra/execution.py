"""Translate GPU availability selections into native settings without a job queue."""

from copy import deepcopy

from omegaconf import DictConfig, open_dict

from clearml_yolo.adapters.runtime.gpu_resources import device_count


def effective_configuration(config: DictConfig, devices: tuple[int, ...]) -> DictConfig:
    """Use selected inherited CUDA indices without rewriting requested provenance."""
    effective = deepcopy(config)
    if not devices:
        return effective
    with open_dict(effective):
        for group, limit in (("ultralytics", len(devices)), ("ultralytics_predict", 1)):
            if group in effective:
                count = min(device_count(effective[group].get("device")), limit)
                if count:
                    effective[group].device = list(devices[:count])
    return effective
