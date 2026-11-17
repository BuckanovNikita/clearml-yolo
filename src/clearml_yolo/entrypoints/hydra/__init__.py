"""Centralized Hydra and hydra-zen configuration, composition and validation.

Within the product, only this package imports Hydra, hydra-zen and OmegaConf. Local multiruns
use Hydra's sequential BasicSweeper and BasicLauncher; no project launcher plugin exists.
Saved configurations name ``_target_`` classes by their current module paths.
"""
