"""Workflows and the typed ports and contracts they depend on.

Application code imports only core and its own modules, never adapters, entrypoints,
Loguru, rendering, HTTP or file-lock libraries. Every effect goes through a port in
``WorkflowDependencies`` supplied per invocation. Internal order, outermost first:
``use_cases``; ``evaluation`` and ``ground_truth``; ``ports`` and ``batch_ports``;
``training_workers``; ``contracts``.
"""
