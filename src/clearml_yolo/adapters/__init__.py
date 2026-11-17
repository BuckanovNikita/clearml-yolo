"""Concrete effects behind application ports: storage, SDKs, processes, rendering.

Adapters may import core and application ports and contracts, never use cases, application
evaluation or ground-truth orchestration, or entrypoints. Responsibilities are peers: by
default ``augmentation`` and ``observability`` import no other adapter, the storage
consumers (``assets``, ``clearml``, ``integrations``, ``reporting``, ``yolo``) may use
``storage`` and ``observability``, the rest only ``observability``. Every other
cross-adapter edge is an exact, justified import-contract entry.
"""
