from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Any, Dict, Optional, Tuple

_CACHE: Dict[str, Any] = {"ts": 0.0, "value": None, "err": None}
_TTL_SECONDS = 30.0


def _fetch_uncached() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    exe = shutil.which("orca") or shutil.which("orca.exe")
    if not exe:
        return None, "provider_unavailable"
    try:
        # orca CLI returns JSON; avoid shell, capture stdout only
        p = subprocess.run(
            [exe, "account", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        if p.returncode != 0:
            return None, "provider_unavailable"
        out = (p.stdout or "").strip()
        if not out:
            return None, "invalid_response"
        obj = json.loads(out)
        rl = ((obj.get("result") or {}).get("rateLimits")) if isinstance(obj, dict) else None
        if not isinstance(rl, dict):
            if isinstance(obj, dict) and "rateLimits" in obj and isinstance(obj["rateLimits"], dict):
                rl = obj["rateLimits"]
        if not isinstance(rl, dict):
            return None, "invalid_response"
        return rl, None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception:
        return None, "invalid_response"


def fetch_orca_rate_limits(force: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return (rateLimits dict, error_code_if_any). Read-only local CLI call, cached briefly."""
    now = time.monotonic()
    if not force and (now - float(_CACHE.get("ts") or 0.0)) < _TTL_SECONDS:
        return _CACHE.get("value"), _CACHE.get("err")
    value, err = _fetch_uncached()
    _CACHE["ts"] = now
    _CACHE["value"] = value
    _CACHE["err"] = err
    return value, err




def ms_to_iso(ms: Any) -> Optional[str]:
    try:
        if ms is None:
            return None
        v = float(ms)
        if v <= 0:
            return None
        # orca uses ms timestamps in observed data
        from datetime import datetime, timezone
        # heuristic: ms if large
        if v > 10_000_000_000:
            dt = datetime.fromtimestamp(v / 1000.0, tz=timezone.utc).astimezone()
        else:
            dt = datetime.fromtimestamp(v, tz=timezone.utc).astimezone()
        return dt.isoformat(timespec="seconds")
    except Exception:
        return None

