"""Project-owned evaluation records, schemas, payloads and class/threshold policy.

These records hold exact values copied from the evaluation adapter; nothing here computes
matches or AP. Frozen validation thresholds and their precision must survive every round
trip unchanged.
"""
