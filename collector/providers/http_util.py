from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple


def get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Tuple[Optional[Dict[str, Any]], Optional[int], Optional[str]]:
    """Return (json_obj, status_code, error_kind). Never returns raw body in error."""
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            raw = resp.read()
        try:
            obj = json.loads(raw.decode("utf-8", errors="replace"))
            if isinstance(obj, dict):
                return obj, status, None
            return None, status, "invalid_response"
        except Exception:
            return None, status, "invalid_response"
    except urllib.error.HTTPError as e:
        code = getattr(e, "code", None)
        if code in (401, 403):
            return None, code, "auth_expired"
        if code == 404:
            return None, code, "invalid_response"
        if code and 500 <= int(code) <= 599:
            return None, code, "provider_unavailable"
        return None, code, "provider_unavailable"
    except urllib.error.URLError:
        return None, None, "network"
    except TimeoutError:
        return None, None, "timeout"
    except Exception:
        return None, None, "network"

