"""Root entry point for Person C's advisor module.

The working project lives in ./wheat-advisor, where results.json is stored.
This wrapper loads that implementation so imports from the repo root also work.
"""

from __future__ import annotations

import importlib.util
import os
import sys

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wheat-advisor", "advisor.py")
_SPEC = importlib.util.spec_from_file_location("_wheat_advisor_impl", _PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load advisor implementation from {_PATH}")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["_wheat_advisor_impl"] = _MOD
_SPEC.loader.exec_module(_MOD)

for _name in dir(_MOD):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_MOD, _name)
