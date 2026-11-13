from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..contract import safe_error
from .http_util import get_json


def _credentials_from_path(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[Path]]:
    if not path.exists():
        return None, "missing_credential", path
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        oauth = obj.get("claudeAiOauth") if isinstance(obj, dict) else None
        if not isinstance(oauth, dict):
            return None, "missing_credential", path
        token = oauth.get("accessToken")
        if not isinstance(token, str) or not token.strip():
            return None, "missing_credential", path
        exp = oauth.get("expiresAt")
        if isinstance(exp, (int, float)):
            try:
                exp_dt = datetime.fromtimestamp(float(exp) / 1000.0, tz=timezone.utc)
                if exp_dt <= datetime.now(timezone.utc):
                    return None, "auth_expired", path
            except Exception:
                pass
        return oauth, None, path
    except Exception:
        return None, "invalid_response", path


def _orca_managed_profile_credentials() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    base = os.environ.get("APPDATA")
    if not base:
        return None, "missing_credential"
    pattern = os.path.join(base, "orca", "claude-profiles", "*", "home", ".credentials.json")
    candidates = [Path(p) for p in glob.glob(pattern)]
    if not candidates:
        return None, "missing_credential"
    # Prefer a non-expired credential; if all expired/missing, return auth_expired/missing.
    valid: List[Tuple[Path, Dict[str, Any]]] = []
    saw_auth_expired = False
    for p in candidates:
        oauth, err, _ = _credentials_from_path(p)
        if oauth and not err:
            valid.append((p, oauth))
        elif err == "auth_expired":
            saw_auth_expired = True
    if valid:
        # pick most recently modified valid profile
        valid.sort(key=lambda t: t[0].stat().st_mtime if t[0].exists() else 0, reverse=True)
        return valid[0][1], None
    if saw_auth_expired:
        return None, "auth_expired"
    return None, "missing_credential"


def _resolve_credentials(cfg: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    # 1) Explicit local path from config (reference external/config path, never serialized to snapshot)
    explicit = cfg.get("credentials_path") or cfg.get("claude_credentials_path")
    if isinstance(explicit, str) and explicit.strip():
        p = Path(os.path.expandvars(os.path.expanduser(explicit.strip())))
        oauth, err, _ = _credentials_from_path(p)
        return oauth, err

    # 2) Default user credentials
    default_path = Path(os.path.expanduser("~")) / ".claude" / ".credentials.json"
    oauth, err, _ = _credentials_from_path(default_path)
    if oauth and not err:
        return oauth, None

    # 3) Read-only locally managed profile (e.g. Orca-managed) without requiring Orca process/CLI.
    #    Try when explicitly requested, or as fallback when default is missing/expired to honor
    #    "não peça login antes de verificar opção já disponível somente leitura".
    cred_ref = str(cfg.get("credential_ref") or "")
    prefer_managed = str(cfg.get("credential_source") or "").lower() in {"orca_managed_profile", "managed_profile", "local_managed"}
    if prefer_managed or "orca" in cred_ref.lower() or err in ("auth_expired", "missing_credential", None):
        moauth, merr = _orca_managed_profile_credentials()
        if moauth and not merr:
            return moauth, None
        # if explicit managed requested, return its error; else keep original/default error preference
        if prefer_managed or "orca" in cred_ref.lower():
            return None, merr or err or "missing_credential"

    return None, err or "missing_credential"


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


def _map_usage(obj: Dict[str, Any]) -> Dict[str, Any]:
    quotas: List[Dict[str, Any]] = []
    acc = {"type": "account", "id": "account", "label": "Conta"}
    fh = obj.get("five_hour") if isinstance(obj.get("five_hour"), dict) else None
    if fh:
        q = _quota("account_5h", acc, "rolling_5h", "5 horas", fh.get("utilization"), fh.get("resets_at"), 5 * 3600)
        if q: quotas.append(q)
    sd = obj.get("seven_day") if isinstance(obj.get("seven_day"), dict) else None
    if sd:
        q = _quota("account_week", acc, "week", "Semana", sd.get("utilization"), sd.get("resets_at"), 7 * 24 * 3600)
        if q: quotas.append(q)
    for key, label, mid in [
        ("seven_day_opus", "Opus", "opus"),
        ("seven_day_sonnet", "Sonnet", "sonnet"),
        ("seven_day_fable", "Fable", "fable"),
    ]:
        mv = obj.get(key)
        if isinstance(mv, dict):
            q = _quota(f"model_{mid}_week", {"type": "model", "id": mid, "label": label}, "week", "Semana", mv.get("utilization"), mv.get("resets_at"), 7 * 24 * 3600)
            if q: quotas.append(q)
    extra = obj.get("extra_usage") or obj.get("additional_usage")
    if isinstance(extra, list):
        for i, item in enumerate(extra):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("label") or f"extra_{i}")
            used = item.get("utilization")
            if used is None:
                used = item.get("used_percent")
            q = _quota(f"extra_{i}", {"type": "account", "id": name, "label": name}, "window", name, used, item.get("resets_at"))
            if q: quotas.append(q)
    return {"quotas": quotas}


def collect_direct(cfg: Dict[str, Any]) -> Dict[str, Any]:
    oauth, err = _resolve_credentials(cfg)
    if err:
        return {"ok": False, "error": safe_error(err, err)}
    token = (oauth or {}).get("accessToken")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "llm-usage-widget/1.0",
    }
    obj, status, herr = get_json("https://api.anthropic.com/api/oauth/usage", headers=headers, timeout=15)
    if herr:
        return {"ok": False, "error": safe_error(herr, herr)}
    data = _map_usage(obj or {})
    if not data.get("quotas"):
        return {"ok": False, "error": safe_error("invalid_response", "unrecognized_usage_response")}
    return {"ok": True, "kind": "quota", "data": data, "source": "claude_oauth"}

