"""Opt-in diagnostic only: reads Orca CLI account list if available.
NOT used by default collection and MUST NOT be required for independence.
Run explicitly: py -3 scripts/diagnose_orca_import.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.providers.orca_source import fetch_orca_rate_limits  # noqa: E402


def main() -> int:
    rl, err = fetch_orca_rate_limits(force=True)
    out = {"ok": err is None, "error": err, "rateLimits_keys": sorted(list((rl or {}).keys())) if isinstance(rl, dict) else None}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if err is None else 1


if __name__ == "__main__":
    raise SystemExit(main())

