from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..contract import safe_error
from .http_util import get_json

ENDPOINT_USAGE = "https://opencode.ai/zen/go/v1/usage"


def _candidate_auth_paths(cfg: Dict[str, Any]) -> List[Path]:
    explicit = cfg.get("credentials_path") or cfg.get("opencode_credentials_path") or cfg.get("auth_path")
    if isinstance(explicit, str) and explicit.strip():
        return [Path(os.path.expandvars(os.path.expanduser(explicit.strip())))]

    paths: List[Path] = []
    xdg = os.environ.get("XDG_DATA_HOME")
    if isinstance(xdg, str) and xdg.strip():
        paths.append(Path(os.path.expandvars(os.path.expanduser(xdg.strip()))) / "opencode" / "auth.json")
    paths.append(Path(os.path.expanduser("~")) / ".local" / "share" / "opencode" / "auth.json")
    appdata = os.environ.get("APPDATA")
    if isinstance(appdata, str) and appdata.strip():
        paths.append(Path(appdata.strip()) / "opencode" / "auth.json")
    return paths


def _read_auth_file(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return None, "missing_credential"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, "invalid_response"
    if not isinstance(obj, dict):
        return None, "invalid_response"
    entry = obj.get("opencode-go")
    if not isinstance(entry, dict):
        entry = obj.get("opencode_go")
    if not isinstance(entry, dict):
        return None, "missing_credential"
    key = entry.get("key")
    if not isinstance(key, str) or not key.strip():
        return None, "missing_credential"
    return {"api_key": key.strip()}, None


def _resolve_credentials(cfg: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Read-only local credential resolution from OpenCode auth.json. Never refreshes tokens."""
    last_err: Optional[str] = None
    for path in _candidate_auth_paths(cfg):
        creds, err = _read_auth_file(path)
        if creds and not err:
            return creds, None
        if err == "invalid_response":
            last_err = err
        elif last_err is None:
            last_err = err
    return None, last_err or "missing_credential"


def _iso_or_none(val: Any) -> Optional[str]:
    if not val or isinstance(val, bool):
        return None
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().isoformat(timespec="seconds")
        except Exception:
            return None
    if isinstance(val, (int, float)):
        try:
            v = float(val)
            if not math.isfinite(v) or v <= 0:
                return None
            if v > 10_000_000_000:
                v /= 1000.0
            return datetime.fromtimestamp(v, tz=timezone.utc).astimezone().isoformat(timespec="seconds")
        except Exception:
            return None
    return None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def _classify_window(key: str, slot: Dict[str, Any]) -> Tuple[str, str, Optional[int], int]:
    k = key.strip().lower()
    if k == "rolling":
        return "rolling_5h", "5 horas", 5 * 3600, 0
    if k == "weekly":
        return "week", "Semana", 7 * 24 * 3600, 1
    if k == "monthly":
        return "month", "Mês", None, 2
    wid = _slug(k) or "window"
    return wid, key.strip() or "Janela", None, 3


def _map_usage(obj: Dict[str, Any]) -> Dict[str, Any]:
    usage = obj.get("usage")
    if not isinstance(usage, dict):
        return {"quotas": []}

    acc = {"type": "account", "id": "account", "label": "Conta"}
    ranked: List[Tuple[int, int, Dict[str, Any]]] = []
    seen_ids: set[str] = set()

    for seq, (key, slot) in enumerate(usage.items()):
        if not isinstance(slot, dict):
            continue
        pct = slot.get("percent")
        if isinstance(pct, bool) or not isinstance(pct, (int, float)):
            continue
        pct_f = float(pct)
        if not math.isfinite(pct_f) or pct_f < 0.0 or pct_f > 100.0:
            continue

        wid, wlabel, duration_s, sort_rank = _classify_window(str(key), slot)
        window: Dict[str, Any] = {"id": wid, "label": wlabel}
        if duration_s is not None:
            window["duration_seconds"] = duration_s
        reset_at = _iso_or_none(slot.get("resetsAt") or slot.get("reset_at"))
        if reset_at:
            window["reset_at"] = reset_at

        base_id = f"account_{wid}"
        qid = base_id
        idx = 2
        while qid in seen_ids:
            qid = f"{base_id}_{idx}"
            idx += 1
        seen_ids.add(qid)

        ranked.append((
            sort_rank,
            seq,
            {
                "id": qid,
                "scope": acc,
                "window": window,
                "used_percent": round(pct_f, 2),
            },
        ))

    ranked.sort(key=lambda item: (item[0], item[1]))
    return {"quotas": [item[2] for item in ranked]}


def collect_direct(cfg: Dict[str, Any]) -> Dict[str, Any]:
    creds, cerr = _resolve_credentials(cfg)
    if cerr or not creds:
        code = cerr or "missing_credential"
        return {"ok": False, "error": safe_error(code, code)}

    headers = {
        "Authorization": f"Bearer {creds['api_key']}",
        "Accept": "application/json",
        "User-Agent": "opencode/1.0",
    }
    obj, _, err = get_json(ENDPOINT_USAGE, headers=headers, timeout=15)
    if err or not isinstance(obj, dict):
        code = err or "invalid_response"
        return {"ok": False, "error": safe_error(code, code)}

    data = _map_usage(obj)
    if not data.get("quotas"):
        return {"ok": False, "error": safe_error("invalid_response", "unrecognized_usage_response")}
    return {"ok": True, "data": data}


def collect(cfg: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Read-only OpenCode Go usage collection independent of Orca and CLI.
    No token refresh, no paid generation.
    """
    try:
        return collect_direct(cfg)
    except Exception:
        return {"ok": False, "error": safe_error("provider_unavailable", "exception")}
