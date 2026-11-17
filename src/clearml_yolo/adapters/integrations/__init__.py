"""Native training, DDP, batch-estimation and export bridges across adapters.

These modules compose detector backends, storage, ClearML ownership and supervised workers.
The invocation owner alone publishes results; ranks use runtime distributed setup and return
typed receipts. Pure search and compatibility logic stays in core.
"""
