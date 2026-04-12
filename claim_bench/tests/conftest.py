"""Configure test paths for fixtures and sibling test imports."""

import sys
from pathlib import Path

# Add tests/ to sys.path so fixtures/ and sibling test modules are importable
TESTS_DIR = str(Path(__file__).resolve().parent)
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)
