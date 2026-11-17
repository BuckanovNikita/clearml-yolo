"""Loguru logging, progress, operation tracing and caught-error diagnostics.

Every adapter may depend on it, so it imports other adapters only through exact ``runtime``
bootstrap bridges. Caller logging sinks are preserved; tracing is opt-in and must not change
an operation's outcome.
"""
