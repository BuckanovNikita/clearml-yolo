"""Config files Hydra composes from the installed package, not from Python.

The ultralytics parameter sets live here as YAML rather than in the hydra-zen store
because their comments are the point: every key carries upstream's own one-line
explanation, and a store entry rendered back out through ``OmegaConf.to_yaml`` would
lose all of them. Hydra reaches this directory through ``hydra.searchpath``, declared as
``pkg://clearml_yolo.conf`` in each primary config, and ``cy-init-config`` copies the
files out verbatim so an edited copy keeps them too.

This module is empty and importable on purpose: ``pkg://`` resolves through
``importlib.resources``, and without ``__init__.py`` Hydra reports the provider as
unavailable and falls through to composing nothing.
"""

from __future__ import annotations
