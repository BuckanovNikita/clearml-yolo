"""ClearML tracking: the invocation-owned task, models, datasets, reports and replay.

One invocation owns one task and its terminal status; workers never create tasks or publish.
``parameters`` and ``cache`` are pure projections and must not import ClearML, Torch,
Ultralytics or FiftyOne.
"""
