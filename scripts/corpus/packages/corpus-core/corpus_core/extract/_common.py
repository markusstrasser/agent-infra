"""Shared helpers for extractors."""
from __future__ import annotations

import hashlib
import json


def config_md5(config: dict | None) -> str:
    blob = json.dumps(config or {}, sort_keys=True).encode("utf-8")
    return hashlib.md5(blob).hexdigest()
