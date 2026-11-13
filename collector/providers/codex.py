from __future__ import annotations

from typing import Any, Dict, Optional

from ..contract import safe_error
from .codex_direct import collect_direct


def collect(cfg: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Read-only collection independent of Orca process/CLI. No token refresh, no paid generation."""
    try:
        return collect_direct(cfg)
    except Exception:
        return {"ok": False, "error": safe_error("provider_unavailable", "exception")}



