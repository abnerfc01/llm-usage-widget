from __future__ import annotations

from typing import Any, Dict, Optional

from ..contract import safe_error


def collect(cfg: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Independent Antigravity usage source not verified in this environment without Orca.
    Read-only, no token refresh. Publishes safe unsupported state until a direct source is verified.
    """
    return {"ok": False, "error": safe_error("unsupported", "independent_source_unverified")}



