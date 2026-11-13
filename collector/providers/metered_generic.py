from __future__ import annotations

from typing import Any, Dict, Optional

from ..contract import safe_error


def collect(cfg: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Template for future metered (API spend/balance) providers.
    No endpoints are called here without verified implementation/configuration.
    """
    if not cfg.get("credential_ref") and not cfg.get("endpoint"):
        return {"ok": False, "error": safe_error("missing_credential", "missing_credential")}
    return {"ok": False, "error": safe_error("unsupported", "not_implemented")}

