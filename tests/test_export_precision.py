"""Explicit mixed precision keeps detector selection and attention in FP32."""

from typing import Any

import numpy as np
import pytest

from clearml_yolo.adapters.export.precision import fp16_weighted_graph

onnx = pytest.importorskip("onnx")


def _model(nodes: list[Any], initializers: list[Any], inputs: list[str], output: str) -> Any:
    helper = onnx.helper
    return helper.make_model(
        helper.make_graph(
            nodes,
            "mixed",
            [
                helper.make_tensor_value_info(name, onnx.TensorProto.FLOAT, [None, 2])
                for name in inputs
            ],
            [helper.make_tensor_value_info(output, onnx.TensorProto.FLOAT, [None, 2])],
            initializers,
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )


@pytest.mark.parametrize("operation", ["MatMul", "Gemm"])
def test_weighted_product_accumulates_float_but_subpixel_geometry_remains_float(
    operation: str,
) -> None:
    from onnx.reference import ReferenceEvaluator

    weight = onnx.numpy_helper.from_array(np.eye(2, dtype=np.float32), "weight")
    offset = onnx.numpy_helper.from_array(np.array([0.0001], dtype=np.float32), "offset")
    model = _model(
        [
            onnx.helper.make_node(operation, ["x", "weight"], ["weighted"], name="projection"),
            onnx.helper.make_node("Add", ["weighted", "offset"], ["geometry"]),
        ],
        [weight, offset],
        ["x"],
        "geometry",
    )
    initializers = [value.SerializeToString() for value in model.graph.initializer]
    assert fp16_weighted_graph(model, onnx) == 1
    onnx.checker.check_model(model, full_check=True)
    value = np.array([[1.0001, 2.0001]], dtype=np.float32)
    evaluated = ReferenceEvaluator(model).run(None, {"x": value})
    assert isinstance(evaluated, list)
    result = evaluated[0]
    expected = value.astype(np.float16).astype(np.float32) + np.float32(0.0001)
    np.testing.assert_array_equal(result, expected)
    assert result.dtype == np.float32
    assert [value.SerializeToString() for value in model.graph.initializer] == initializers
    inferred = onnx.shape_inference.infer_shapes(model)
    types = {value.name: value.type.tensor_type.elem_type for value in inferred.graph.value_info}
    weighted = next(node for node in model.graph.node if node.op_type == "MatMul")
    assert all(types[name] == onnx.TensorProto.FLOAT for name in weighted.input)
    assert types[weighted.output[0]] == onnx.TensorProto.FLOAT
    _assert_private_float_product(model, weighted)
    assert types["weighted"] == onnx.TensorProto.FLOAT


def test_dynamic_attention_product_and_probabilities_are_not_converted() -> None:
    from onnx.reference import ReferenceEvaluator

    weight = onnx.numpy_helper.from_array(np.eye(2, dtype=np.float32), "weight")
    model = _model(
        [
            onnx.helper.make_node("MatMul", ["x", "weight"], ["projected"]),
            onnx.helper.make_node("MatMul", ["projected", "keys"], ["scores"], name="attention"),
            onnx.helper.make_node("Softmax", ["scores"], ["probability"]),
        ],
        [weight],
        ["x", "keys"],
        "probability",
    )
    assert fp16_weighted_graph(model, onnx) == 1
    onnx.checker.check_model(model, full_check=True)
    attention = next(node for node in model.graph.node if node.name == "attention")
    assert list(attention.input) == ["projected", "keys"]
    assert list(attention.output) == ["scores"]
    inferred = onnx.shape_inference.infer_shapes(model)
    types = {value.name: value.type.tensor_type.elem_type for value in inferred.graph.value_info}
    assert types["scores"] == onnx.TensorProto.FLOAT
    # Real DINO score products exceeded FP16's finite range; the operands fit Half.
    values = np.full((2, 2), 2000, dtype=np.float32)
    evaluated = ReferenceEvaluator(model).run(None, {"x": values, "keys": values})
    assert isinstance(evaluated, list)
    np.testing.assert_array_equal(evaluated[0], np.full((2, 2), 0.5, dtype=np.float32))


def test_pointwise_lowering_preserves_bias_and_existing_tensor_names() -> None:
    helper = onnx.helper
    values = {
        "weight": np.ones((2, 1, 1, 1), np.float32),
        "bias": np.zeros(2, np.float32),
        "_cy_fp16_0": np.ones(1, np.int64),
    }
    model = helper.make_model(
        helper.make_graph(
            [helper.make_node("Conv", ["x", "weight", "bias"], ["boxes"], name="regression")],
            "conv",
            [
                helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, [None, 1, None, None]),
                helper.make_tensor_value_info("_cy_fp16_1", onnx.TensorProto.FLOAT, [1]),
            ],
            [helper.make_tensor_value_info("boxes", onnx.TensorProto.FLOAT, [None, 2, None, None])],
            [onnx.numpy_helper.from_array(value, name) for name, value in values.items()],
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    assert fp16_weighted_graph(model, onnx) == 1
    onnx.checker.check_model(model, full_check=True)
    assert not any(node.op_type == "Conv" for node in model.graph.node)
    product = next(node for node in model.graph.node if node.op_type == "MatMul")
    _assert_private_float_product(model, product)
    outputs = [name for node in model.graph.node for name in node.output]
    assert len(outputs) == len(set(outputs))
    assert "_cy_fp16_0" not in outputs
    assert model.graph.output[0].name == "boxes"


def test_dynamic_weighted_convolution_rejects_unsupported_lowering() -> None:
    model = _model(
        [onnx.helper.make_node("Conv", ["x", "weight"], ["output"])], [], ["x", "weight"], "output"
    )
    with pytest.raises(ValueError, match="FP32 initializer weights"):
        fp16_weighted_graph(model, onnx)


@pytest.mark.parametrize(
    ("operation", "head_weight"),
    [
        ("Conv", "model.backbone.fpn.inner_blocks.0.0.weight"),
        ("Conv", "model.backbone.fpn.layer_blocks.0.0.weight"),
        ("Conv", "model.rpn.head.conv.0.0.weight"),
        ("Gemm", "model.roi_heads.box_head.fc6.weight"),
        ("Gemm", "model.roi_heads.box_predictor.bbox_pred.weight"),
        ("MatMul", "model.roi_heads.box_predictor.cls_score.weight"),
    ],
)
def test_fpn_and_detection_heads_preserve_float_arithmetic_after_half_backbone(
    operation: str, head_weight: str
) -> None:
    from onnx.reference import ReferenceEvaluator

    helper = onnx.helper
    weight_shape = (2, 2, 1, 1) if operation == "Conv" else (2, 2)
    image_shape = (1, 2, 1, 1) if operation == "Conv" else (1, 2)
    identity = np.eye(2, dtype=np.float32).reshape(weight_shape)
    feature_weight = "model.backbone.body.projection.weight"
    factor = np.float32(1.0001)
    model = helper.make_model(
        helper.make_graph(
            [
                helper.make_node(operation, ["x", feature_weight], ["features"], name="first"),
                helper.make_node(operation, ["features", head_weight], ["boxes"], name="last"),
            ],
            "detection",
            [helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, image_shape)],
            [helper.make_tensor_value_info("boxes", onnx.TensorProto.FLOAT, image_shape)],
            [
                onnx.numpy_helper.from_array(identity, feature_weight),
                onnx.numpy_helper.from_array(identity * factor, head_weight),
            ],
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    original_weights = [value.SerializeToString() for value in model.graph.initializer]
    assert fp16_weighted_graph(model, onnx) == 1
    onnx.checker.check_model(model, full_check=True)
    head = next(node for node in model.graph.node if node.name == "last")
    assert list(head.input) == ["features", head_weight]
    assert list(head.output) == ["boxes"]
    value = np.array([1.0002, 2.0002], dtype=np.float32).reshape(image_shape)
    evaluated = ReferenceEvaluator(model).run(None, {"x": value})
    assert isinstance(evaluated, list)
    np.testing.assert_array_equal(
        evaluated[0], value.astype(np.float16).astype(np.float32) * factor
    )
    assert [value.SerializeToString() for value in model.graph.initializer] == original_weights


def _assert_private_float_product(model: Any, product: Any) -> None:
    """An exposed Float product prevents the required TensorRT cast fusion."""
    producers = {output: node for node in model.graph.node for output in node.output}
    for operand in product.input:
        upcast = producers[operand]
        assert upcast.op_type == "Cast"
        assert onnx.helper.get_attribute_value(upcast.attribute[0]) == onnx.TensorProto.FLOAT
    consumers = [node for node in model.graph.node if product.output[0] in node.input]
    assert len(consumers) == 1
    downcast = consumers[0]
    assert downcast.op_type == "Cast"
    assert onnx.helper.get_attribute_value(downcast.attribute[0]) == onnx.TensorProto.FLOAT16
    assert product.output[0] not in {value.name for value in model.graph.output}


@pytest.mark.parametrize("batch", [1, 2])
@pytest.mark.parametrize("strides", [(1, 1), (2, 2), (2, 3)])
def test_pointwise_convolution_preserves_dynamic_odd_canvas_stride_and_float_bias(
    batch: int, strides: tuple[int, int]
) -> None:
    from onnx.reference import ReferenceEvaluator

    helper = onnx.helper
    weights = np.array([[1.0003, -0.2501], [0.5002, 2.0001], [-1.0004, 0.7502]], np.float32)
    bias = np.array([0.0001, -0.0002, 0.0003], np.float32)
    model = helper.make_model(
        helper.make_graph(
            [helper.make_node("Conv", ["x", "weight", "bias"], ["y"], strides=list(strides))],
            "pointwise",
            [helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, [None, 2, None, None])],
            [helper.make_tensor_value_info("y", onnx.TensorProto.FLOAT, [None, 3, None, None])],
            [
                onnx.numpy_helper.from_array(weights.reshape(3, 2, 1, 1), "weight"),
                onnx.numpy_helper.from_array(bias, "bias"),
            ],
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    original_initializers = [value.SerializeToString() for value in model.graph.initializer]
    original_io = [value.SerializeToString() for value in (*model.graph.input, *model.graph.output)]
    assert fp16_weighted_graph(model, onnx) == 1
    assert not any(node.op_type == "Conv" for node in model.graph.node)
    onnx.checker.check_model(model, full_check=True)
    _assert_private_float_product(model, next(n for n in model.graph.node if n.op_type == "MatMul"))
    values = (np.arange(batch * 2 * 5 * 7, dtype=np.float32) / 37 + 0.0001).reshape(batch, 2, 5, 7)
    sampled = values[:, :, :: strides[0], :: strides[1]].astype(np.float16).astype(np.float32)
    # Independent spatial formulation: one dot product per sampled pixel.
    product = np.einsum("kc,bchw->bkhw", weights.astype(np.float16).astype(np.float32), sampled)
    expected = product.astype(np.float16).astype(np.float32) + bias.reshape(1, 3, 1, 1)
    evaluated = ReferenceEvaluator(model).run(None, {"x": values})
    assert isinstance(evaluated, list)
    actual = evaluated[0]
    np.testing.assert_array_equal(actual, expected)
    assert [v.SerializeToString() for v in model.graph.initializer] == original_initializers
    assert [v.SerializeToString() for v in (*model.graph.input, *model.graph.output)] == original_io


@pytest.mark.parametrize(
    "attributes",
    [
        {"kernel_shape": [3, 3]},
        {"group": 2},
        {"pads": [1, 0, 1, 0]},
        {"dilations": [2, 2]},
        {"auto_pad": "SAME_UPPER"},
    ],
)
def test_convolutions_without_pointwise_accumulation_support_remain_float(
    attributes: dict[str, Any],
) -> None:
    helper = onnx.helper
    kernel = attributes.get("kernel_shape", [1, 1])
    channels = 2 // attributes.get("group", 1)
    conv = helper.make_node("Conv", ["image", "conv_weight"], ["features"], **attributes)
    original_conv = conv.SerializeToString()
    model = helper.make_model(
        helper.make_graph(
            [conv, helper.make_node("MatMul", ["x", "linear_weight"], ["linear"])],
            "float_spatial",
            [
                helper.make_tensor_value_info("image", onnx.TensorProto.FLOAT, [1, 2, 5, 7]),
                helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, [1, 2]),
            ],
            [helper.make_tensor_value_info("features", onnx.TensorProto.FLOAT, [1, 2, None, None])],
            [
                onnx.numpy_helper.from_array(
                    np.ones((2, channels, *kernel), np.float32), "conv_weight"
                ),
                onnx.numpy_helper.from_array(np.eye(2, dtype=np.float32), "linear_weight"),
            ],
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    assert fp16_weighted_graph(model, onnx) == 1
    assert (
        next(n for n in model.graph.node if n.op_type == "Conv").SerializeToString()
        == original_conv
    )
    onnx.checker.check_model(model, full_check=True)


@pytest.mark.parametrize(("trans_a", "trans_b"), [(0, 0), (1, 0), (0, 1), (1, 1)])
@pytest.mark.parametrize("bias_shape", [(), (3,), (2, 3)])
def test_gemm_preserves_transposes_float_coefficients_and_bias_broadcasting(
    trans_a: int, trans_b: int, bias_shape: tuple[int, ...]
) -> None:
    from onnx.reference import ReferenceEvaluator

    helper = onnx.helper
    a = np.array([[1.0003, 2.0001], [-0.5001, 0.7501]], np.float32)
    b = np.array([[0.2501, 1.0001, -2.0001], [0.7503, -1.0003, 0.5001]], np.float32)
    bias = np.full(bias_shape, 0.0001, np.float32)
    stored_a, stored_b = (a.T.copy() if trans_a else a), (b.T.copy() if trans_b else b)
    model = helper.make_model(
        helper.make_graph(
            [
                helper.make_node(
                    "Gemm",
                    ["x", "weight", "bias"],
                    ["y"],
                    transA=trans_a,
                    transB=trans_b,
                    alpha=0.5,
                    beta=2.0,
                )
            ],
            "gemm",
            [helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, list(stored_a.shape))],
            [helper.make_tensor_value_info("y", onnx.TensorProto.FLOAT, [2, 3])],
            [
                onnx.numpy_helper.from_array(stored_b, "weight"),
                onnx.numpy_helper.from_array(bias, "bias"),
            ],
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    assert fp16_weighted_graph(model, onnx) == 1
    onnx.checker.check_model(model, full_check=True)
    _assert_private_float_product(model, next(n for n in model.graph.node if n.op_type == "MatMul"))
    product = a.astype(np.float16).astype(np.float32) @ b.astype(np.float16).astype(np.float32)
    expected = product.astype(np.float16).astype(np.float32) * np.float32(0.5) + bias * np.float32(
        2
    )
    evaluated = ReferenceEvaluator(model).run(None, {"x": stored_a})
    assert isinstance(evaluated, list)
    np.testing.assert_array_equal(evaluated[0], expected)


@pytest.mark.parametrize("weight_on_left", [False, True])
def test_matmul_keeps_batch_broadcast_and_initializer_operand_order(weight_on_left: bool) -> None:
    from onnx.reference import ReferenceEvaluator

    helper = onnx.helper
    weight = np.array([[1.0003, 0.2502], [-0.5002, 2.0001]], np.float32)
    values = np.arange(12, dtype=np.float32).reshape(3, 2, 2) / 7
    operands = ["weight", "x"] if weight_on_left else ["x", "weight"]
    model = helper.make_model(
        helper.make_graph(
            [helper.make_node("MatMul", operands, ["y"])],
            "broadcast",
            [helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, [None, 2, 2])],
            [helper.make_tensor_value_info("y", onnx.TensorProto.FLOAT, [None, 2, 2])],
            [onnx.numpy_helper.from_array(weight, "weight")],
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    assert fp16_weighted_graph(model, onnx) == 1
    onnx.checker.check_model(model, full_check=True)
    _assert_private_float_product(model, next(n for n in model.graph.node if n.op_type == "MatMul"))
    left, right = (weight, values) if weight_on_left else (values, weight)
    expected = (
        (left.astype(np.float16).astype(np.float32) @ right.astype(np.float16).astype(np.float32))
        .astype(np.float16)
        .astype(np.float32)
    )
    evaluated = ReferenceEvaluator(model).run(None, {"x": values})
    assert isinstance(evaluated, list)
    np.testing.assert_array_equal(evaluated[0], expected)
