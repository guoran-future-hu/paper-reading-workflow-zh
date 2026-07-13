#!/usr/bin/env python3
"""Thin wrapper kept for backwards-compatible script paths; logic lives in paper_notes.mineru_extract."""
import sys
from pathlib import Path

try:
    from paper_notes.mineru_extract import main
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from paper_notes.mineru_extract import main

if __name__ == "__main__":
    raise SystemExit(main())
