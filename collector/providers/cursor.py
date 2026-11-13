from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ..contract import safe_error


def _has_cursor_auth_state() -> bool:
    # Read-only heuristic: presence of local Cursor app state DB indicates install; token validity unknown without API.
    candidates = [
        Path.home() / "AppData/Roaming/Cursor/User/globalStorage/state.vscdb",
        Path.home() / "AppData/Roaming/Cursor/User/globalStorage/storage.json",
    ]
    for p in candidates:
        try:
            if p.exists() and p.stat().st_size > 0:
                return True
        except Exception:
            pass
    return False


def collect(cfg: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Independent Cursor usage source not verified without a confirmed read-only endpoint.
    KANBAN notes Cursor sign-in expired; we do not probe/refresh tokens. Publishes safe state.
    """
    # Do not claim credentials missing if app state exists; report unsupported/unverified to avoid guessing.
    if _has_cursor_auth_state():
        return {"ok": False, "error": safe_error("unsupported", "independent_source_unverified")}
    return {"ok": False, "error": safe_error("missing_credential", "missing_credential")}



