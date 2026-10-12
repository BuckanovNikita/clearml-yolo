"""Local torchvision compatibility subclasses retaining native DEIM augmentation.

The upstream custom transforms implement the pre-0.22 private hook. Only these
objects are reconstructed as local subclasses; upstream classes and source stay intact.
"""

from typing import Any


def _transform(self: Any, inpt: Any, params: dict[str, Any]) -> Any:
    return self._transform(inpt, params)


def bridge_transforms(compose: Any) -> None:
    for index, transform in enumerate(compose.transforms):
        name = type(transform).__name__
        if name not in {"ConvertPILImage", "ConvertBoxes"}:
            continue
        # Identical names preserve the native Compose policy's type-name selection.
        bridge = type(name, (type(transform),), {"transform": _transform})
        if name == "ConvertPILImage":
            replacement = bridge(dtype=transform.dtype, scale=transform.scale)
        else:
            replacement = bridge(fmt=transform.fmt, normalize=transform.normalize)
        compose.transforms[index] = replacement
