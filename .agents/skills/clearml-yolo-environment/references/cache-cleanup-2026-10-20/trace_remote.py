"""Observe exceptions swallowed by the installed SDK without changing its behavior."""

import json
import os
import runpy
import sys
from pathlib import Path


def trace(frame, event, argument):
    if not (frame.f_code.co_filename.endswith("/clearml/model.py")
            and frame.f_code.co_name == "__init__"):
        return None
    if event == "exception":
        error_type, error, _ = argument
        record = {
            "file": frame.f_code.co_filename, "line": frame.f_lineno,
            "type": error_type.__name__, "message": str(error),
        }
        with Path(os.environ["CY_ACCEPT_TRACE_OUTPUT"]).open("a") as stream:
            stream.write(json.dumps(record) + "\n")
    return trace


sys.settrace(trace)
try:
    runpy.run_module("clearml_yolo.entrypoints.train", run_name="__main__")
finally:
    sys.settrace(None)
