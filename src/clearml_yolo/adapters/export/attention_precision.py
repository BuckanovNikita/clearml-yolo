"""Recognize exported combined QKV projections that require Float arithmetic."""

from typing import Any

_MATRIX_RANK = 2
_PRODUCT_INPUTS = 2


def _standard(node: Any, operation: str) -> bool:
    return node.op_type == operation and node.domain in ("", "ai.onnx")


class _AttentionPath:
    """Inspect the supported value branch without importing the optional ONNX SDK."""

    def __init__(self, graph: Any, onnx: Any) -> None:
        self.onnx = onnx
        self.parameters = {value.name: value for value in graph.initializer}
        self.producers: dict[str, Any] = {}
        for node in graph.node:
            for output in node.output:
                if not output:
                    continue
                if output in self.producers or output in self.parameters:
                    raise ValueError("Ambiguous producer in attention precision graph")
                self.producers[output] = node

    def attributes(self, node: Any) -> dict[str, Any]:
        return {value.name: self.onnx.helper.get_attribute_value(value) for value in node.attribute}

    def node(self, output: str, operation: str, inputs: int, outputs: int = 1) -> Any:
        node = self.producers.get(output)
        if (
            node is None
            or not _standard(node, operation)
            or len(node.input) != inputs
            or len(node.output) != outputs
        ):
            raise ValueError(f"Unsupported attention value path: expected {operation}")
        return node

    def vector(self, name: str) -> tuple[int, ...]:
        value = self.parameters.get(name)
        if value is None:
            node = self.node(name, "Constant", 0)
            value = self.attributes(node).get("value")
        if (
            not isinstance(value, self.onnx.TensorProto)
            or value.data_type != self.onnx.TensorProto.INT64
            or len(value.dims) != 1
        ):
            raise ValueError("Attention controls require constant INT64 vectors")
        return tuple(int(item) for item in self.onnx.numpy_helper.to_array(value).tolist())

    def projection(self, value: str) -> str:
        squeeze = self.node(value, "Squeeze", 2)
        if self.vector(squeeze.input[1]) != (0,):
            raise ValueError("Unsupported attention value squeeze axis")
        split = self.node(squeeze.input[0], "Split", 2, 3)
        if (
            self.attributes(split).get("axis", 0) != 0
            or self.vector(split.input[1]) != (1, 1, 1)
            or split.output[2] != squeeze.input[0]
        ):
            raise ValueError("Unsupported attention QKV split")
        transpose = self.node(split.input[0], "Transpose", 1)
        if tuple(self.attributes(transpose).get("perm", ())) != (2, 0, 3, 1, 4):
            raise ValueError("Unsupported attention QKV layout")
        reshape = self.node(transpose.input[0], "Reshape", 2)
        projected = reshape.input[0]
        producer = self.producers.get(projected)
        bias = None
        if producer is not None and _standard(producer, "Add"):
            addition = self.node(projected, "Add", 2)
            biases = [name for name in addition.input if name in self.parameters]
            if len(biases) != 1:
                raise ValueError("Attention QKV bias requires a direct Float initializer")
            bias = self.parameters[biases[0]]
            projected = addition.input[1 if addition.input[0] == biases[0] else 0]
        product = self.node(projected, "MatMul", 2)
        weight = self.parameters.get(product.input[1])
        if (
            weight is None
            or weight.data_type != self.onnx.TensorProto.FLOAT
            or len(weight.dims) != _MATRIX_RANK
            or weight.dims[0] <= 0
            or weight.dims[1] != 3 * weight.dims[0]
        ):
            raise ValueError("Attention QKV requires direct Float weights shaped [C, 3*C]")
        if bias is not None and (
            bias.data_type != self.onnx.TensorProto.FLOAT or tuple(bias.dims) != (weight.dims[1],)
        ):
            raise ValueError("Attention QKV bias requires a Float channel vector")
        return str(product.output[0])


def float_attention_outputs(graph: Any, onnx: Any) -> set[str]:
    """Find combined QKV through Softmax/AV dataflow, independently of export names.

    QKV product rounding can amplify through score multiplication and Softmax even
    when those operations are Float. Keep the combined projection Float as well.
    Unknown value layouts at this attention boundary fail before graph mutation.
    """
    path = _AttentionPath(graph, onnx)
    protected = set()
    for node in graph.node:
        if (
            not _standard(node, "MatMul")
            or len(node.input) != _PRODUCT_INPUTS
            or any(value in path.parameters for value in node.input)
        ):
            continue
        probability = path.producers.get(node.input[0])
        if probability is not None and _standard(probability, "Softmax"):
            protected.add(path.projection(node.input[1]))
    return protected
