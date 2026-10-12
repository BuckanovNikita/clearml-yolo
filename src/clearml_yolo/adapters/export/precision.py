"""Private Float accumulation for selected Half-rounded backbone products."""

from typing import Any

from clearml_yolo.adapters.export.attention_precision import float_attention_outputs

_FLOAT_DETECTOR_PREFIXES = (
    "model.backbone.fpn.",
    "model.rpn.head.",
    "model.roi_heads.box_head.",
    "model.roi_heads.box_predictor.",
)
_WEIGHT_INPUT = 1
_BIAS_INPUT = 2
_POINTWISE_RANK = 4
_SPATIAL_AXES = (2, 3)
_SLICE_END = 9223372036854775807


def _attributes(node: Any, onnx: Any) -> dict[str, Any]:
    return {value.name: onnx.helper.get_attribute_value(value) for value in node.attribute}


def _pointwise_strides(node: Any, weight: Any, onnx: Any) -> tuple[int, int] | None:
    dimensions = tuple(weight.dims)
    if len(dimensions) != _POINTWISE_RANK or dimensions[2:] != (1, 1):
        return None
    attrs = _attributes(node, onnx)
    supported = (
        attrs.get("group", 1) == 1,
        tuple(attrs.get("kernel_shape", (1, 1))) == (1, 1),
        tuple(attrs.get("pads", (0, 0, 0, 0))) == (0, 0, 0, 0),
        attrs.get("auto_pad", b"NOTSET") in (b"NOTSET", "NOTSET"),
        tuple(attrs.get("dilations", (1, 1))) == (1, 1),
    )
    strides = tuple(attrs.get("strides", (1, 1)))
    if not all(supported) or len(strides) != len(_SPATIAL_AXES) or min(strides) <= 0:
        return None
    return int(strides[0]), int(strides[1])


def _weighted_nodes(graph: Any, onnx: Any) -> list[Any]:
    float_attention = float_attention_outputs(graph, onnx)
    initializers = {value.name: value for value in graph.initializer}
    float_weights = {
        name for name, value in initializers.items() if value.data_type == onnx.TensorProto.FLOAT
    }
    selected = []
    for node in graph.node:
        if node.domain not in ("", "ai.onnx"):
            continue
        if node.op_type in ("Conv", "Gemm"):
            if len(node.input) <= _WEIGHT_INPUT or node.input[_WEIGHT_INPUT] not in float_weights:
                raise ValueError("FP16 detector lowering requires direct FP32 initializer weights")
            parameters = [node.input[_WEIGHT_INPUT]]
        elif node.op_type == "MatMul":
            parameters = [name for name in node.input if name in float_weights]
        else:
            continue
        if (
            not parameters
            or any(name.startswith(_FLOAT_DETECTOR_PREFIXES) for name in parameters)
            or node.output[0] in float_attention
        ):
            continue
        if (
            node.op_type == "Conv"
            and _pointwise_strides(node, initializers[node.input[_WEIGHT_INPUT]], onnx) is None
        ):
            continue
        selected.append(node)
    if not selected:
        raise ValueError("FP16 detector graph has no supported weighted operations")
    return selected


class _GraphBuilder:
    """Build auxiliary nodes without modifying original declarations or parameters."""

    def __init__(self, graph: Any, onnx: Any) -> None:
        self.onnx = onnx
        self.nodes: list[Any] = []
        self.counter = 0
        self.occupied = {
            name for node in graph.node for name in (*node.input, *node.output, node.name)
        }
        self.occupied.update(value.name for value in graph.initializer)
        self.occupied.update(
            value.name for value in (*graph.input, *graph.output, *graph.value_info)
        )
        self.occupied.update(value.values.name for value in graph.sparse_initializer)
        self.occupied.update(value.indices.name for value in graph.sparse_initializer)

    def fresh(self) -> str:
        while (name := f"_cy_fp16_{self.counter}") in self.occupied:
            self.counter += 1
        self.counter += 1
        self.occupied.add(name)
        return name

    def emit(
        self,
        operation: str,
        inputs: list[str],
        output: str | None = None,
        name: str | None = None,
        **attributes: Any,
    ) -> str:
        target = output if output is not None else self.fresh()
        self.nodes.append(
            self.onnx.helper.make_node(
                operation, inputs, [target], name=name or self.fresh(), **attributes
            )
        )
        return target

    def vector(self, values: tuple[int, ...]) -> str:
        value = self.onnx.helper.make_tensor(
            self.fresh(), self.onnx.TensorProto.INT64, [len(values)], values
        )
        return self.emit("Constant", [], value=value)

    def scalar(self, value: float) -> str:
        tensor = self.onnx.helper.make_tensor(
            self.fresh(), self.onnx.TensorProto.FLOAT, [], [value]
        )
        return self.emit("Constant", [], value=tensor)

    def quantized_float(self, source: str) -> str:
        half = self.emit("Cast", [source], to=self.onnx.TensorProto.FLOAT16)
        return self.emit("Cast", [half], to=self.onnx.TensorProto.FLOAT)

    def product(self, left: str, right: str, name: str) -> str:
        operands = [self.quantized_float(value) for value in (left, right)]
        product = self.emit("MatMul", operands, name=name)
        # These upcasts must be private, and the immediate Half cast must be the
        # product's sole consumer. TensorRT then selects Half operands with Float
        # accumulation. Exposing the Float product would prevent that fusion.
        return self.quantized_float(product)


def _lower_matmul(node: Any, builder: _GraphBuilder) -> None:
    product = builder.product(node.input[0], node.input[1], node.name)
    builder.emit("Identity", [product], output=node.output[0])


def _lower_gemm(node: Any, builder: _GraphBuilder) -> None:
    attrs = _attributes(node, builder.onnx)
    left, right = node.input[:2]
    if attrs.get("transA", 0):
        left = builder.emit("Transpose", [left], perm=[1, 0])
    if attrs.get("transB", 0):
        right = builder.emit("Transpose", [right], perm=[1, 0])
    product = builder.product(left, right, node.name)
    alpha = float(attrs.get("alpha", 1))
    if alpha != 1:
        product = builder.emit("Mul", [product, builder.scalar(alpha)])
    bias = node.input[_BIAS_INPUT] if len(node.input) > _BIAS_INPUT else ""
    if bias:
        beta = float(attrs.get("beta", 1))
        if beta != 1:
            bias = builder.emit("Mul", [bias, builder.scalar(beta)])
        builder.emit("Add", [product, bias], output=node.output[0])
    else:
        builder.emit("Identity", [product], output=node.output[0])


def _sample_pointwise_input(source: str, strides: tuple[int, int], builder: _GraphBuilder) -> str:
    if strides == (1, 1):
        return source
    return builder.emit(
        "Slice",
        [
            source,
            builder.vector((0, 0)),
            builder.vector((_SLICE_END, _SLICE_END)),
            builder.vector(_SPATIAL_AXES),
            builder.vector(strides),
        ],
    )


def _pointwise_output_shape(shape: str, channels: int, builder: _GraphBuilder) -> str:
    batch = builder.emit("Gather", [shape, builder.vector((0,))], axis=0)
    spatial = builder.emit("Gather", [shape, builder.vector(_SPATIAL_AXES)], axis=0)
    return builder.emit("Concat", [batch, builder.vector((channels,)), spatial], axis=0)


def _lower_pointwise(node: Any, weight: Any, builder: _GraphBuilder) -> None:
    strides = _pointwise_strides(node, weight, builder.onnx)
    if strides is None:
        raise ValueError("Unsupported pointwise convolution")
    output_channels, input_channels = (int(value) for value in weight.dims[:2])
    source = _sample_pointwise_input(node.input[0], strides, builder)
    shape = builder.emit("Shape", [source])
    flattened = builder.emit("Reshape", [source, builder.vector((0, input_channels, -1))])
    kernel = builder.emit(
        "Reshape", [node.input[1], builder.vector((1, output_channels, input_channels))]
    )
    product = builder.product(kernel, flattened, node.name)
    output_shape = _pointwise_output_shape(shape, output_channels, builder)
    bias = node.input[_BIAS_INPUT] if len(node.input) > _BIAS_INPUT else ""
    output = builder.emit(
        "Reshape", [product, output_shape], output=None if bias else node.output[0]
    )
    if bias:
        broadcast = builder.emit("Reshape", [bias, builder.vector((1, output_channels, 1, 1))])
        builder.emit("Add", [output, broadcast], output=node.output[0])


def fp16_weighted_graph(model: Any, onnx: Any) -> int:
    """Lower eligible backbone products with Half rounding and private Float accumulation.

    Direct weighted MatMul/Gemm and unpadded, ungrouped 1x1 convolutions use
    Half-rounded operands/products. Biases and Gemm coefficients stay Float.
    FPN/heads, spatial convolutions, combined QKV projections, dynamic attention
    and geometry remain Float. Selection validates supported attention layouts
    and all Conv/Gemm initializer weights before mutating the model.
    """
    graph = model.graph
    selected = _weighted_nodes(graph, onnx)
    selected_ids = {id(node) for node in selected}
    initializers = {value.name: value for value in graph.initializer}
    builder = _GraphBuilder(graph, onnx)
    for node in graph.node:
        if id(node) not in selected_ids:
            builder.nodes.append(node)
        elif node.op_type == "Conv":
            _lower_pointwise(node, initializers[node.input[_WEIGHT_INPUT]], builder)
        elif node.op_type == "Gemm":
            _lower_gemm(node, builder)
        else:
            _lower_matmul(node, builder)
    del graph.node[:]
    graph.node.extend(builder.nodes)
    return len(selected)
