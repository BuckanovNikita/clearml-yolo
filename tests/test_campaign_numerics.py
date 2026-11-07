"""Numerical failures remain fatal and identify the native scalar that failed."""

import math
from pathlib import Path
from typing import override

import pytest

from clearml_yolo.adapters.observability.capture import append_scalar


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_scalar_identifies_series_and_iteration_without_journaling(
    value: float, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = tmp_path / "scalars.jsonl"
    journal.write_text("", encoding="utf-8")
    monkeypatch.setenv("CY_SCALAR_JOURNAL", str(journal))

    with pytest.raises(ValueError, match="Native scalar must be finite") as caught:
        append_scalar("val", "val/box_loss", value, 7)

    message = str(caught.value)
    assert message.startswith("Native scalar must be finite")
    assert "title='val'" in message
    assert "series='val/box_loss'" in message
    assert "iteration=7" in message
    assert "value=" in message
    assert journal.read_text(encoding="utf-8") == ""


def test_nonfinite_training_loss_identifies_batch_images_and_components() -> None:
    import torch
    from torch import Tensor, nn
    from torch.utils.data import DataLoader, Dataset

    from clearml_yolo.adapters.torchvision.data import collate_detection
    from clearml_yolo.adapters.torchvision.training import _training_epoch
    from clearml_yolo.core.models import TrainSettings

    class Detector(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.weight = nn.Parameter(torch.tensor(1.0))

        @override
        def forward(self, images: list[Tensor], targets: list[dict[str, Tensor]]) -> dict[str, Tensor]:
            return {
                "classification": self.weight * 2,
                "bbox_regression": self.weight * math.inf,
                "bbox_ctrness": self.weight * 3,
            }

    class Samples(Dataset[tuple[Tensor, dict[str, Tensor]]]):
        @override
        def __getitem__(self, index: int) -> tuple[Tensor, dict[str, Tensor]]:
            return torch.zeros(3, 8, 8), {"image_id": torch.tensor(23)}

        def __len__(self) -> int:
            return 1

    model = Detector()
    loader: DataLoader[tuple[Tensor, dict[str, Tensor]]] = DataLoader(
        Samples(),
        batch_size=1,
        collate_fn=collate_detection,
    )
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    scaler = torch.amp.GradScaler("cuda", enabled=False)
    with pytest.raises(FloatingPointError, match="Torchvision training produced a nonfinite loss") as caught:
        _training_epoch(model, loader, optimizer, scaler, TrainSettings(), torch.device("cpu"), None)

    message = str(caught.value)
    assert "batch=0" in message
    assert "image_ids=[23]" in message
    assert "'classification': 2.0" in message
    assert "'bbox_regression': inf" in message
    assert "'bbox_ctrness': 3.0" in message
    assert model.weight.grad is None
    assert float(model.weight.detach()) == 1.0
