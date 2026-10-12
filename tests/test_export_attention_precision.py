"""Combined QKV stays Float; downstream weighted products retain Half rounding."""

from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from clearml_yolo.adapters.export.precision import fp16_weighted_graph

onnx = pytest.importorskip("onnx")

_INPUT = np.array([[[1.0003, -0.2501], [0.5002, 2.0001]]], dtype=np.float32)
_QKV_WEIGHT = np.array(
    [
        [0.2501, 1.0003, -0.5, 0.7501, 1.0001, 0.1251],
        [-0.7503, 0.3333, 1.25, -0.1251, 0.5003, 1.0003],
    ],
    dtype=np.float32,
)
_OUTPUT_WEIGHT = np.array([[1.0003, 0.2502], [-0.5002, 2.0001]], dtype=np.float32)
_MLP_WEIGHT = np.array([[0.7503, -1.2501], [0.3333, 0.5002]], dtype=np.float32)


def _attention_model(
    *, bias: str = "right", constants: bool = False, named: bool = False
) -> tuple[Any, dict[str, str]]:
    """Two tokens, one head, two channels: a complete QK -> Softmax -> AV graph."""
    helper = onnx.helper
    roles = (
        "x",
        "weight",
        "bias",
        "shape",
        "split_sizes",
        "axes",
        "product",
        "biased",
        "reshape",
        "layout",
        "q_slice",
        "k_slice",
        "v_slice",
        "q",
        "k",
        "v",
        "kt",
        "scores",
        "probability",
        "context",
        "out_weight",
        "out",
        "mlp_weight",
        "mlp",
    )
    names = {role: f"unrelated_{i * 7 + 3}" if named else f"t{i}" for i, role in enumerate(roles)}
    if named:
        # A non-QKV parameter deliberately claims to be QKV; names cannot classify it.
        names["out_weight"] = "attention.qkv.weight"
    nodes: list[Any] = []
    initializers: list[Any] = []

    def emit(operation: str, inputs: list[str], outputs: list[str], **attrs: Any) -> None:
        nodes.append(
            helper.make_node(
                operation,
                [names[key] for key in inputs],
                [names[key] for key in outputs],
                name=f"operator_{len(nodes)}" if named else "",
                **attrs,
            )
        )

    parameters = {"weight": _QKV_WEIGHT, "out_weight": _OUTPUT_WEIGHT, "mlp_weight": _MLP_WEIGHT}
    if bias != "none":
        parameters["bias"] = np.arange(1, 7, dtype=np.float32) * np.float32(0.0001)
    initializers.extend(
        onnx.numpy_helper.from_array(value, names[key]) for key, value in parameters.items()
    )
    for role, values in (("shape", [1, 2, 3, 1, 2]), ("split_sizes", [1, 1, 1]), ("axes", [0])):
        tensor = onnx.numpy_helper.from_array(np.array(values, dtype=np.int64), names[role])
        if constants:
            emit("Constant", [], [role], value=tensor)
        else:
            initializers.append(tensor)
    emit("MatMul", ["x", "weight"], ["product"])
    if named:
        nodes[-1].name = "feed_forward/not_an_attention_scope"
    projected = "product"
    if bias != "none":
        operands = ["bias", "product"] if bias == "left" else ["product", "bias"]
        emit("Add", operands, ["biased"])
        projected = "biased"
    emit("Reshape", [projected, "shape"], ["reshape"])
    emit("Transpose", ["reshape"], ["layout"], perm=[2, 0, 3, 1, 4])
    emit("Split", ["layout", "split_sizes"], ["q_slice", "k_slice", "v_slice"], axis=0)
    for branch in ("q", "k", "v"):
        emit("Squeeze", [f"{branch}_slice", "axes"], [branch])
    emit("Transpose", ["k"], ["kt"], perm=[0, 1, 3, 2])
    emit("MatMul", ["q", "kt"], ["scores"])
    emit("Softmax", ["scores"], ["probability"], axis=-1)
    emit("MatMul", ["probability", "v"], ["context"])
    emit("MatMul", ["context", "out_weight"], ["out"])
    emit("MatMul", ["x", "mlp_weight"], ["mlp"])
    outputs = [
        ("product", [1, 2, 6]),
        ("context", [1, 1, 2, 2]),
        ("out", [1, 1, 2, 2]),
        ("mlp", [1, 2, 2]),
    ]
    if bias != "none":
        outputs.append(("biased", [1, 2, 6]))
    model = helper.make_model(
        helper.make_graph(
            nodes,
            "anonymous_attention",
            [helper.make_tensor_value_info(names["x"], onnx.TensorProto.FLOAT, [1, 2, 2])],
            [
                helper.make_tensor_value_info(names[role], onnx.TensorProto.FLOAT, shape)
                for role, shape in outputs
            ],
            initializers,
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    return model, names


def _producer(model: Any, output: str) -> Any:
    return next(node for node in model.graph.node if output in node.output)


def _evaluate(model: Any, inputs: dict[str, NDArray[np.float32]]) -> list[Any]:
    from onnx.reference import ReferenceEvaluator

    onnx.checker.check_model(model, full_check=True)
    evaluated = ReferenceEvaluator(model).run(None, inputs)
    assert isinstance(evaluated, list)
    return evaluated


def _rounded_product(left: NDArray[np.float32], right: NDArray[np.float32]) -> NDArray[np.float32]:
    product = left.astype(np.float16).astype(np.float32) @ right.astype(np.float16).astype(
        np.float32
    )
    return product.astype(np.float16).astype(np.float32)


@pytest.mark.parametrize(
    ("bias", "constants", "named"),
    [("none", False, False), ("none", True, True), ("right", False, True), ("left", True, False)],
)
def test_qkv_is_float_by_value_branch_while_output_projection_and_mlp_round(
    bias: str, constants: bool, named: bool
) -> None:
    model, names = _attention_model(bias=bias, constants=constants, named=named)
    feeds = {names["x"]: _INPUT}
    original = _evaluate(model, feeds)
    initializers = [value.SerializeToString() for value in model.graph.initializer]
    external_io = [value.SerializeToString() for value in (*model.graph.input, *model.graph.output)]
    protected = [_producer(model, names["product"]).SerializeToString()]
    if bias != "none":
        protected.append(_producer(model, names["biased"]).SerializeToString())

    selected = fp16_weighted_graph(model, onnx)
    actual = _evaluate(model, feeds)

    np.testing.assert_array_equal(actual[0], original[0])
    np.testing.assert_array_equal(actual[1], original[1])
    if bias != "none":
        np.testing.assert_array_equal(actual[4], original[4])
    expected_output = _rounded_product(original[1], _OUTPUT_WEIGHT)
    expected_mlp = _rounded_product(_INPUT, _MLP_WEIGHT)
    assert not np.array_equal(expected_output, original[2])
    assert not np.array_equal(expected_mlp, original[3])
    np.testing.assert_array_equal(actual[2], expected_output)
    np.testing.assert_array_equal(actual[3], expected_mlp)
    assert selected == 2
    assert all(
        node in [value.SerializeToString() for value in model.graph.node] for node in protected
    )
    assert [value.SerializeToString() for value in model.graph.initializer] == initializers
    assert [
        value.SerializeToString() for value in (*model.graph.input, *model.graph.output)
    ] == external_io


def _replace_initializer(model: Any, name: str, array: NDArray[Any]) -> None:
    value = next(value for value in model.graph.initializer if value.name == name)
    value.CopyFrom(onnx.numpy_helper.from_array(array, name))


def _assert_rejected_without_mutation(model: Any) -> None:
    original = model.SerializeToString()
    with pytest.raises(ValueError, match=r".+"):
        fp16_weighted_graph(model, onnx)
    assert model.SerializeToString() == original


@pytest.mark.parametrize(
    "damage",
    ["split_sizes", "split_axis", "layout", "value_index", "squeeze_axis", "unknown_value"],
)
def test_unsupported_attention_value_layout_rejects_atomically(damage: str) -> None:
    model, names = _attention_model()
    if damage == "split_sizes":
        _replace_initializer(model, names["split_sizes"], np.array([1, 1, 2], dtype=np.int64))
    elif damage == "split_axis":
        _producer(model, names["v_slice"]).attribute[0].i = 1
    elif damage == "layout":
        _producer(model, names["layout"]).attribute[0].ints[:] = [0, 2, 3, 1, 4]
    elif damage == "value_index":
        _producer(model, names["v"]).input[0] = names["q_slice"]
    elif damage == "squeeze_axis":
        _replace_initializer(model, names["axes"], np.array([1], dtype=np.int64))
    else:
        _producer(model, names["context"]).input[1] = names["x"]
    _assert_rejected_without_mutation(model)


@pytest.mark.parametrize("damage", ["dynamic", "missing", "half", "rank", "width"])
def test_qkv_requires_direct_float_channel_by_three_channels_weight(damage: str) -> None:
    model, names = _attention_model()
    if damage in ("dynamic", "missing"):
        weight = next(value for value in model.graph.initializer if value.name == names["weight"])
        model.graph.initializer.remove(weight)
        if damage == "dynamic":
            model.graph.input.append(
                onnx.helper.make_tensor_value_info(names["weight"], onnx.TensorProto.FLOAT, [2, 6])
            )
    elif damage == "half":
        _replace_initializer(model, names["weight"], _QKV_WEIGHT.astype(np.float16))
    elif damage == "rank":
        _replace_initializer(model, names["weight"], _QKV_WEIGHT.reshape(1, 2, 6))
    else:
        _replace_initializer(model, names["weight"], _QKV_WEIGHT[:, :5])
    _assert_rejected_without_mutation(model)


@pytest.mark.parametrize("shape", [(1, 6), (5,)])
def test_qkv_bias_requires_exact_channel_vector(shape: tuple[int, ...]) -> None:
    model, names = _attention_model()
    _replace_initializer(model, names["bias"], np.zeros(shape, dtype=np.float32))
    _assert_rejected_without_mutation(model)


@pytest.mark.parametrize("constants", [False, True])
def test_attention_axes_require_int64_tensor_controls(constants: bool) -> None:
    model, names = _attention_model(constants=constants)
    replacement = onnx.numpy_helper.from_array(np.array([0], dtype=np.int32), names["axes"])
    if constants:
        _producer(model, names["axes"]).attribute[0].t.CopyFrom(replacement)
    else:
        _replace_initializer(model, names["axes"], np.array([0], dtype=np.int32))
    _assert_rejected_without_mutation(model)


def test_duplicate_value_producer_is_ambiguous_and_rejects_atomically() -> None:
    model, names = _attention_model()
    # Both producers claim the V tensor; choosing either silently is unsafe.
    model.graph.node.append(onnx.helper.make_node("Identity", [names["x"]], [names["v"]]))
    _assert_rejected_without_mutation(model)


def test_isolated_softmax_does_not_protect_qkv_shaped_or_named_projection() -> None:
    helper = onnx.helper
    model = helper.make_model(
        helper.make_graph(
            [
                helper.make_node("MatMul", ["x", "qkv.weight"], ["qkv"], name="attention/qkv"),
                helper.make_node("Softmax", ["qkv"], ["probabilities"], axis=-1),
            ],
            "no_attention_value_product",
            [helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, [1, 2, 2])],
            [
                helper.make_tensor_value_info(name, onnx.TensorProto.FLOAT, [1, 2, 6])
                for name in ("qkv", "probabilities")
            ],
            [onnx.numpy_helper.from_array(_QKV_WEIGHT, "qkv.weight")],
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    original = _evaluate(model, {"x": _INPUT})
    assert fp16_weighted_graph(model, onnx) == 1
    actual = _evaluate(model, {"x": _INPUT})
    expected = _rounded_product(_INPUT, _QKV_WEIGHT)
    assert not np.array_equal(expected, original[0])
    np.testing.assert_array_equal(actual[0], expected)


def test_static_probability_projection_is_not_an_attention_value_product() -> None:
    helper = onnx.helper
    model = helper.make_model(
        helper.make_graph(
            [
                helper.make_node("Softmax", ["x"], ["probabilities"], axis=-1),
                helper.make_node("MatMul", ["probabilities", "weight"], ["out"]),
            ],
            "probability_projection",
            [helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, [1, 2])],
            [helper.make_tensor_value_info("out", onnx.TensorProto.FLOAT, [1, 2])],
            [onnx.numpy_helper.from_array(_OUTPUT_WEIGHT, "weight")],
        ),
        opset_imports=[helper.make_opsetid("", 17)],
    )
    assert fp16_weighted_graph(model, onnx) == 1
    onnx.checker.check_model(model, full_check=True)
