"""Shared test fixtures for meta scripts.

Handles the two recurring import issues:
1. scripts/ isn't a package — needs sys.path
2. Hyphenated filenames (session-features.py) need importlib
"""

import importlib.util
import sys
from pathlib import Path

# Add scripts/ to path so `from common.paths import ...` works
SCRIPTS_DIR = Path(__file__).parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def import_hyphenated(name: str):
    """Import a hyphenated script by filename (without .py)."""
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
