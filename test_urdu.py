"""Run Person C's Urdu helper checks from the repo root."""

from __future__ import annotations

import os
import runpy
import sys

_PROJECT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wheat-advisor")
sys.path.insert(0, _PROJECT)
runpy.run_path(os.path.join(_PROJECT, "test_urdu.py"), run_name="__main__")
