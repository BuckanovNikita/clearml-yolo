"""Detector training, evaluation, comparison and export workflows tracked in ClearML.

Keep this root inert: it imports nothing and performs no startup work, so importing
``clearml_yolo`` never loads scientific libraries, frameworks or SDKs. Runtime code lives in
four layers that import only inward: ``entrypoints`` -> ``adapters`` -> ``application`` ->
``core``. The import contracts classify the children of the root, ``adapters``,
``application`` and ``entrypoints`` exhaustively, so every new package must be added there.
"""
