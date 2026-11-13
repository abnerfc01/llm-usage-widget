from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..contract import safe_error
from .http_util import get_json


def _read_auth() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    path = Path(os.path.expanduser("~")) / ".codex" / "auth.json"
    if not path.exists():
        return None, "missing_credential"
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        tokens = obj.get("tokens") if isinstance(obj, dict) else None
        if not isinstance(tokens, dict):
            # some setups may use OPENAI_API_KEY only (no chatgpt usage quota endpoint applicable)
            if isinstance(obj, dict) and obj.get("OPENAI_API_KEY"):
                return None, "unsupported"
            return None, "missing_credential"
        at = tokens.get("access_token")
        if not isinstance(at, str) or not at.strip():
            return None, "missing_credential"
        return tokens, None
    except Exception:
        return None, "invalid_response"


def _iso_or_none(v: Any) -> Optional[str]:
    if not v:
        return None
    if isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.astimezone().isoformat(timespec="seconds")
        except Exception:
            return None
    if isinstance(v, (int, float)):
        try:
            val = float(v)
            if val > 10_000_000_000:
                dt = datetime.fromtimestamp(val / 1000.0, tz=timezone.utc).astimezone()
            else:
                dt = datetime.fromtimestamp(val, tz=timezone.utc).astimezone()
            return dt.isoformat(timespec="seconds")
        except Exception:
            return None
    return None


def _quota(qid: str, scope: Dict[str, str], wid: str, wlabel: str, used: Any, resets_at: Any, duration_seconds: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if used is None:
        return None
    try:
        used_f = float(used)
    except Exception:
        return None
    window: Dict[str, Any] = {"id": wid, "label": wlabel}
    if duration_seconds:
        window["duration_seconds"] = duration_seconds
    r = _iso_or_none(resets_at)
    if r:
        window["reset_at"] = r
    return {"id": qid, "scope": scope, "window": window, "used_percent": max(0.0, used_f)}


def _extract_percent(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return obj
    if isinstance(obj, dict):
        for k in ("used_percent", "usedPercent", "utilization", "usage_percent", "percent_used"):
            if k in obj:
                return obj[k]
        # sometimes remaining_percent given
        for k in ("remaining_percent", "remainingPercent"):
            if k in obj:
                try:
                    return max(0.0, 100.0 - float(obj[k]))
                except Exception:
                    pass
    return None


def _extract_reset(obj: Any) -> Any:
    if not isinstance(obj, dict):
        return None
    for k in ("resets_at", "reset_at", "resetsAt", "resetAt", "reset_time", "expires_at"):
        if obj.get(k) is not None:
            return obj.get(k)
    return None


def _extract_duration_seconds(obj: Any) -> Optional[int]:
    """Return positive duration in seconds if the source informs it, else None (B5)."""
    if not isinstance(obj, dict):
        return None
    for k in ("limit_window_seconds", "window_seconds", "duration_seconds", "windowMinutes", "window_minutes"):
        v = obj.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            try:
                secs = float(v)
                if k in ("windowMinutes", "window_minutes"):
                    secs = secs * 60.0
                if 0 < secs < 10_000_000_000:
                    return int(secs)
            except Exception:
                continue
    return None


def _window_id_label(duration_seconds: Optional[int], default_wid: str = "window", default_label: str = "Janela") -> Tuple[str, str, Optional[int]]:
    """Identify known windows by actual duration; use neutral label when unknown (B5)."""
    if duration_seconds is None:
        return default_wid, default_label, None
    # tolerance 5 minutes
    five_hours = 5 * 3600
    one_week = 7 * 24 * 3600
    one_hour = 3600
    if abs(duration_seconds - five_hours) <= 300:
        return "rolling_5h", "5 horas", duration_seconds
    if abs(duration_seconds - one_week) <= 600:
        return "week", "Semana", duration_seconds
    if abs(duration_seconds - one_hour) <= 120:
        return "rolling_1h", "1 hora", duration_seconds
    return default_wid, default_label, duration_seconds


def _map_usage(obj: Dict[str, Any]) -> Dict[str, Any]:
    quotas: List[Dict[str, Any]] = []
    acc = {"type": "account", "id": "account", "label": "Conta"}
    # ChatGPT/Codex wham usage shapes vary; try common keys
    # primary/secondary windows
    primary = obj.get("rate_limit") or obj.get("rate_limits") or obj
    if isinstance(primary, dict):
        # primary window
        pw = primary.get("primary_window") or primary.get("primary") or primary.get("session")
        if isinstance(pw, dict):
            dur = _extract_duration_seconds(pw)
            wid, wlabel, _ = _window_id_label(dur, "rolling_primary", "Janela primária")
            q = _quota("account_primary", acc, wid, wlabel, _extract_percent(pw), _extract_reset(pw), dur)
            if q:
                quotas.append(q)
        sw = primary.get("secondary_window") or primary.get("secondary") or primary.get("weekly")
        if isinstance(sw, dict):
            dur = _extract_duration_seconds(sw)
            wid, wlabel, _ = _window_id_label(dur, "secondary", "Janela secundária")
            q = _quota("account_secondary", acc, wid, wlabel, _extract_percent(sw), _extract_reset(sw), dur)
            if q:
                quotas.append(q)
    # top-level fallbacks
    if not quotas:
        for key, qid, default_wid, default_label in [
            ("primary_window", "account_primary", "rolling_primary", "Janela primária"),
            ("secondary_window", "account_secondary", "secondary", "Janela secundária"),
        ]:
            v = obj.get(key)
            if isinstance(v, dict):
                dur = _extract_duration_seconds(v)
                wid, wlabel, _ = _window_id_label(dur, default_wid, default_label)
                q = _quota(qid, acc, wid, wlabel, _extract_percent(v), _extract_reset(v), dur)
                if q:
                    quotas.append(q)
    return {"quotas": quotas}


def collect_direct(cfg: Dict[str, Any]) -> Dict[str, Any]:
    tokens, err = _read_auth()
    if err:
        return {"ok": False, "error": safe_error(err, err)}
    token = (tokens or {}).get("access_token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "llm-usage-widget/1.0",
    }
    acc_id = (tokens or {}).get("account_id")
    if isinstance(acc_id, str) and acc_id:
        headers["ChatGPT-Account-Id"] = acc_id
    obj, status, herr = get_json("https://chatgpt.com/backend-api/wham/usage", headers=headers, timeout=15)
    if herr:
        return {"ok": False, "error": safe_error(herr, herr)}
    data = _map_usage(obj or {})
    if not data.get("quotas"):
        return {"ok": False, "error": safe_error("invalid_response", "unrecognized_usage_response")}
    return {"ok": True, "kind": "quota", "data": data, "source": "codex_wham"}
