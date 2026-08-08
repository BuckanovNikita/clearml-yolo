"""The one rule that decides what reaches ultralytics.

Every ultralytics parameter is visible in ``conf/ultralytics/{train,predict}.yaml``,
including the ones this project would otherwise work out for itself — the batch a card
can hold, the device, whether AMP and ``torch.compile`` are on, the run's name. A key
left ``null`` there is one the run decides; a key with a value written against it is
passed to ultralytics verbatim and nothing here overrides it.

That rule replaces two older ones. ``train_kwargs`` used to be spread last so that a run
reproducing older numbers could turn ``amp`` and ``compile`` back off, and the inference
side asked separately whether the caller had already named a precision. Both were
precedence stated at the point of use, where the person editing the config could not see
it. Now it is stated once, here, and again beside every key it governs.

``batch`` and ``device`` are not filled here even though they follow the same rule: the
GPU policy in :mod:`clearml_yolo.gpu` already implements it for them, honouring a number
that was asked for and sizing one that was not, and it has to run anyway to survey the
cards. Passing them through a second precedence step would only give them two.
"""

from __future__ import annotations

from typing import Any


def fill_unset(params: dict[str, Any], **computed: Any) -> dict[str, Any]:
    """Fill each ``computed`` key into ``params`` only where ``params`` left it unset.

    Unset means ``null`` in the config file or absent from it altogether, which are the
    same thing once Hydra has composed the file: both arrive as ``None``.

    >>> fill_unset({"amp": None, "compile": False}, amp=True, compile=True)
    {'amp': True, 'compile': False}
    """
    return {**params, **{key: value for key, value in computed.items() if params.get(key) is None}}
