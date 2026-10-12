"""Tensorized Faster R-CNN inference with embedded proposal, ROI and final NMS.

Torchvision objects and ONNX symbolic graphs are opaque SDK boundaries.
"""

import importlib
from collections.abc import Callable
from typing import Any, cast, override

import torch
from torch import Tensor, nn

MAX_NMS_PROPOSALS = 5000
ROI_MIN_BOX_SIZE = 0.01
LOWEST_PYRAMID_LEVEL = 2


class _ClassNMSMask(torch.autograd.Function):
    @staticmethod
    @override
    def forward(_ctx: Any, boxes: Tensor, scores: Tensor, threshold: float) -> Tensor:
        nms = importlib.import_module("torchvision.ops").nms
        # CPU/native reference. ONNX symbolic below contains no Python batch loop.
        b, c, _n = scores.shape
        result = torch.zeros_like(scores, dtype=torch.bool)
        for i in range(b):
            for j in range(c):
                valid = torch.where(scores[i, j] >= 0)[0]
                selected = nms(boxes[i, j, valid], scores[i, j, valid], threshold)
                result[i, j, valid[selected]] = True
        return result

    @staticmethod
    def symbolic(g: Any, boxes: Any, scores: Any, threshold: float) -> Any:
        def const(v: list[int] | list[float], dtype: torch.dtype = torch.int64) -> Any:
            return g.op("Constant", value_t=torch.tensor(v, dtype=dtype))

        shape = g.op("Shape", scores)
        n = g.op("Gather", shape, const([2]), axis_i=0)
        b = g.op("Gather", shape, const([0]), axis_i=0)
        c = g.op("Gather", shape, const([1]), axis_i=0)
        bc = g.op("Mul", b, c)
        flatshape = g.op("Concat", bc, n, const([4]), axis_i=0)
        flatboxes = g.op("Reshape", boxes, flatshape)
        flatscores = g.op("Reshape", scores, g.op("Concat", bc, const([1]), n, axis_i=0))
        selected = g.op(
            "NonMaxSuppression",
            flatboxes,
            flatscores,
            n,
            const([threshold], torch.float32),
            const([-1.0], torch.float32),
        )
        batchcol = g.op("Gather", selected, const([0]), axis_i=1)
        boxcol = g.op("Gather", selected, const([2]), axis_i=1)
        indices = g.op("Concat", batchcol, boxcol, axis_i=1)
        resultshape = g.op("Concat", bc, n, axis_i=0)
        initial = g.op(
            "ConstantOfShape", resultshape, value_t=torch.tensor([False], dtype=torch.bool)
        )
        num = g.op("Gather", g.op("Shape", selected), const([0]), axis_i=0)
        updates = g.op("ConstantOfShape", num, value_t=torch.tensor([True], dtype=torch.bool))
        scatter = g.op("ScatterND", initial, indices, updates)
        return g.op("Reshape", scatter, shape)


def padded_nms(
    boxes: Tensor,
    scores: Tensor,
    threshold: float,
    limit: int,
) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    apply = cast(Callable[[Tensor, Tensor, float], Tensor], _ClassNMSMask.apply)
    mask = apply(boxes, scores, threshold)
    candidates = torch.where(mask, scores, torch.full_like(scores, -1)).flatten(1)
    selected_scores, index = torch.topk(candidates, limit, dim=1)
    selected_boxes = torch.gather(boxes.flatten(1, 2), 1, index[:, :, None].expand(-1, -1, 4))
    valid = selected_scores >= 0
    count = valid.sum(1)
    selected_boxes = torch.where(
        valid[:, :, None], selected_boxes, torch.zeros_like(selected_boxes)
    )
    return (
        selected_boxes,
        torch.where(valid, selected_scores, torch.zeros_like(selected_scores)),
        index,
        count,
    )


def clip_boxes(boxes: Tensor, image_sizes: Tensor) -> Tensor:
    """Clip each image using its valid resized dimensions, before canvas padding."""
    shape = (image_sizes.shape[0],) + (1,) * (boxes.ndim - 2)
    height = image_sizes[:, 0].to(boxes.dtype).reshape(shape)
    width = image_sizes[:, 1].to(boxes.dtype).reshape(shape)
    return torch.stack(
        (
            torch.minimum(boxes[..., 0].clamp(min=0), width),
            torch.minimum(boxes[..., 1].clamp(min=0), height),
            torch.minimum(boxes[..., 2].clamp(min=0), width),
            torch.minimum(boxes[..., 3].clamp(min=0), height),
        ),
        dim=-1,
    )


class TensorizedDetector(nn.Module):
    def __init__(self, model: Any) -> None:
        super().__init__()
        self.model = model
        self.proposal_limit = int(model.rpn.post_nms_top_n())
        self.pre_limit = int(model.rpn.pre_nms_top_n())
        self.detection_limit = int(model.roi_heads.detections_per_img)
        if max(self.proposal_limit, self.pre_limit) > MAX_NMS_PROPOSALS:
            raise ValueError("TensorRT per-class NMS supports at most 5000 proposals")
        if self.detection_limit > self.proposal_limit * (
            model.roi_heads.box_predictor.cls_score.out_features - 1
        ):
            raise ValueError("Detection limit exceeds the available class proposals")

    @override
    def forward(self, x: Tensor, image_sizes: Tensor) -> tuple[Tensor, Tensor]:
        detection_utils = importlib.import_module("torchvision.models.detection._utils")
        image_list_type = importlib.import_module(
            "torchvision.models.detection.image_list"
        ).ImageList
        b = x.shape[0]
        height = x.shape[2]
        width = x.shape[3]
        features = self.model.backbone(x)
        levels = list(features.values())
        objectness, deltas = self.model.rpn.head(levels)
        anchor_list = self.model.rpn.anchor_generator(
            image_list_type(x[:1], [(height, width)]), levels
        )
        anchors = anchor_list[0]
        offset = 0
        level_boxes = []
        level_scores = []
        for ob, de, feat in zip(objectness, deltas, levels, strict=True):
            score = ob.permute(0, 2, 3, 1).reshape(b, -1)
            delta = (
                de.reshape(b, -1, 4, feat.shape[2], feat.shape[3])
                .permute(0, 3, 4, 1, 2)
                .reshape(b, -1, 4)
            )
            count = score.shape[1]
            top = detection_utils._topk_min(score, self.pre_limit, 1)  # noqa: SLF001
            # Reuse torchvision's export-safe min(K, dynamic anchor count).
            values, idx = score.topk(top, dim=1)
            selected_delta = torch.gather(delta, 1, idx[:, :, None].expand(-1, -1, 4))
            selected_anchors = anchors[offset : offset + count][idx]
            boxes = self.model.rpn.box_coder.decode_single(
                selected_delta.reshape(-1, 4), selected_anchors.reshape(-1, 4)
            ).reshape(b, -1, 4)
            boxes = clip_boxes(boxes, image_sizes)
            probs = values.sigmoid()
            good = (
                (boxes[:, :, 2] - boxes[:, :, 0] >= self.model.rpn.min_size)
                & (boxes[:, :, 3] - boxes[:, :, 1] >= self.model.rpn.min_size)
                & (probs >= self.model.rpn.score_thresh)
            )
            probs = torch.where(good, probs, torch.full_like(probs, -1))
            level_boxes.append(
                torch.nn.functional.pad(boxes, (0, 0, 0, self.pre_limit - boxes.shape[1]))
            )
            level_scores.append(
                torch.nn.functional.pad(probs, (0, self.pre_limit - probs.shape[1]), value=-1)
            )
            offset += count
        rpn_boxes = torch.stack(level_boxes, dim=1)
        rpn_scores = torch.stack(level_scores, dim=1)
        proposals, _, _, proposal_count = padded_nms(
            rpn_boxes, rpn_scores, self.model.rpn.nms_thresh, self.proposal_limit
        )
        flat_boxes = proposals.reshape(-1, 4)
        pooled = self._pool(levels, proposals)
        logits, regression = self.model.roi_heads.box_predictor(
            self.model.roi_heads.box_head(pooled)
        )
        classes = logits.shape[-1]
        boxes = self.model.roi_heads.box_coder.decode_single(regression, flat_boxes).reshape(
            b, self.proposal_limit, classes, 4
        )
        boxes = clip_boxes(boxes, image_sizes)[:, :, 1:, :].permute(0, 2, 1, 3)
        scores = (
            logits.softmax(-1).reshape(b, self.proposal_limit, classes)[:, :, 1:].transpose(1, 2)
        )
        proposal_valid = (
            torch.arange(self.proposal_limit, device=x.device)[None, :] < proposal_count[:, None]
        )
        good = (
            proposal_valid[:, None, :]
            & (scores > self.model.roi_heads.score_thresh)
            & (boxes[:, :, :, 2] - boxes[:, :, :, 0] >= ROI_MIN_BOX_SIZE)
            & (boxes[:, :, :, 3] - boxes[:, :, :, 1] >= ROI_MIN_BOX_SIZE)
        )
        scores = torch.where(good, scores, torch.full_like(scores, -1))
        out_boxes, out_scores, index, out_count = padded_nms(
            boxes, scores, self.model.roi_heads.nms_thresh, self.detection_limit
        )
        labels = index // self.proposal_limit + 1
        valid = torch.arange(self.detection_limit, device=x.device)[None, :] < out_count[:, None]
        labels = torch.where(valid, labels, torch.zeros_like(labels))
        result = torch.cat(
            (out_boxes, out_scores[:, :, None], labels[:, :, None].to(x.dtype)), dim=-1
        )
        return result, out_count

    def _pool(self, levels: list[Tensor], proposals: Tensor) -> Tensor:
        roi_align = importlib.import_module("torchvision.ops").roi_align
        pooler = self.model.roi_heads.box_roi_pool
        output_size = tuple(pooler.output_size)
        sampling_ratio = int(pooler.sampling_ratio)
        flat_boxes = proposals.reshape(-1, 4)
        batch_ids = (
            torch.arange(proposals.shape[0], device=proposals.device)
            .to(proposals.dtype)[:, None]
            .expand(-1, self.proposal_limit)
            .reshape(-1, 1)
        )
        rois = torch.cat((batch_ids, flat_boxes), dim=1)
        areas = (flat_boxes[:, 2] - flat_boxes[:, 0]) * (flat_boxes[:, 3] - flat_boxes[:, 1])
        level = (
            torch.floor(
                pooler.canonical_level
                + torch.log2(torch.sqrt(areas) / pooler.canonical_scale)
                + 1e-6
            )
            .clamp(2, 5)
            .to(torch.int64)
        )
        # Evaluate all proposals at each level; fixed proposal tensors remove empty ROI outputs.
        pooled = (
            roi_align(
                levels[0],
                rois,
                output_size,
                spatial_scale=0.25,
                sampling_ratio=sampling_ratio,
                aligned=False,
            )
            * ((level == LOWEST_PYRAMID_LEVEL).to(proposals.dtype)[:, None, None, None])
        )
        for i, scale in [(1, 0.125), (2, 0.0625), (3, 0.03125)]:
            pooled = (
                pooled
                + roi_align(
                    levels[i],
                    rois,
                    output_size,
                    spatial_scale=scale,
                    sampling_ratio=sampling_ratio,
                    aligned=False,
                )
                * ((level == i + 2).to(proposals.dtype)[:, None, None, None])
            )
        return cast(Tensor, pooled)
