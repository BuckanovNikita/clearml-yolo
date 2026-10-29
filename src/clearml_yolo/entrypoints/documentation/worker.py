"""Isolated preview entrypoint; disable external plugin discovery before Hydra imports."""

import sys
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import override


class _NoExternalPlugins(MetaPathFinder):
    @override
    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        if fullname == "hydra_plugins" or fullname.startswith("hydra_plugins."):
            raise ModuleNotFoundError(
                "External Hydra plugins are disabled in documentation preview"
            )
        return None


def main() -> int:
    sys.meta_path.insert(0, _NoExternalPlugins())
    from clearml_yolo.adapters.documentation.files import MAX_REQUEST_BYTES
    from clearml_yolo.core.documentation import PreviewRequest, PreviewResult
    from clearml_yolo.entrypoints.documentation.preview import preview

    payload = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if len(payload) > MAX_REQUEST_BYTES:
        result = PreviewResult(errors=["Preview request exceeds 1 MiB"])
    else:
        try:
            result = preview(PreviewRequest.model_validate_json(payload))
        except ValueError as error:
            result = PreviewResult(errors=[str(error)])
    sys.stdout.write(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
