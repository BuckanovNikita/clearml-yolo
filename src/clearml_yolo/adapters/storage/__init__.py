"""Lexical CSV parsing, filesystem resolution, caches and persistence.

Storage owns lexical interpretation and compatibility diagnostics of source files. Among
adapters it imports only ``observability`` and exact ``runtime`` bootstrap bridges. Invalid
data, hashes or paths fail with context.
"""
