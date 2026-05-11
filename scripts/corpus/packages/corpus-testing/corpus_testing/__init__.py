"""Test utilities for downstream consumers of corpus-core.

Importing nothing at module load — fixtures are imported on-demand from the
submodules. corpus-core itself imports zero testing frameworks; this package
is the carve-out for them (per plan §J.4).
"""
