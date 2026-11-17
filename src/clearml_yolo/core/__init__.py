"""Pure policy, validation and scientific records shared by every layer.

Core imports nothing from the other layers and owns no filesystem, network, process or
environment access, SDK object, rendering library or Loguru. It may use the standard
library, NumPy, pandas, SciPy, Pydantic and Pandera; any other dependency needs review.
Paths in core records are values; adapters resolve and open them. Core functions take
observations and diagnostics as arguments instead of logging or reporting progress.
"""
