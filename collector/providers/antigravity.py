from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..contract import safe_error

ENDPOINT_QUOTA_SUMMARY = "https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary"
ENDPOINT_LOAD_CODE_ASSIST = "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
WINCRED_TARGET = "gemini:antigravity"
_CRED_TYPE_GENERIC = 1


class _CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wt.DWORD),
        ("Type", wt.DWORD),
        ("TargetName", wt.LPWSTR),
        ("Comment", wt.LPWSTR),
        ("LastWritten", wt.FILETIME),
        ("CredentialBlobSize", wt.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wt.DWORD),
        ("AttributeCount", wt.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wt.LPWSTR),
        ("UserName", wt.LPWSTR),
    ]


def _parse_expiry(val: Any) -> Optional[datetime]:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        try:
            v = float(val)
            if v > 10_000_000_000:
                v /= 1000.0
            return datetime.fromtimestamp(v, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


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
            if v > 10_000_000_000:
                v /= 1000.0
            return datetime.fromtimestamp(v, tz=timezone.utc).astimezone().isoformat(timespec="seconds")
        except Exception:
            return None
    return None


def _extract_token_from_obj(obj: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not isinstance(obj, dict):
        return None, "invalid_response"
    tok = obj.get("token") if isinstance(obj.get("token"), dict) else obj
    if not isinstance(tok, dict):
        return None, "missing_credential"
    access_token = tok.get("access_token") or tok.get("accessToken")
    if not isinstance(access_token, str) or not access_token.strip():
        return None, "missing_credential"
    for exp_key in ("expiry", "expires_at", "expiresAt", "expiry_date"):
        exp_dt = _parse_expiry(tok.get(exp_key))
        if exp_dt is not None and exp_dt <= datetime.now(timezone.utc):
            return None, "auth_expired"
    return {"access_token": access_token.strip()}, None


def _read_wincred_blob(target: str = WINCRED_TARGET) -> Optional[bytes]:
    if sys.platform != "win32":
        return None
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    cred_read = advapi32.CredReadW
    cred_read.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.POINTER(ctypes.POINTER(_CREDENTIAL))]
    cred_read.restype = wt.BOOL
    cred_free = advapi32.CredFree
    cred_free.argtypes = [ctypes.c_void_p]
    cred_free.restype = None

    pcred = ctypes.POINTER(_CREDENTIAL)()
    ok = cred_read(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(pcred))
    if not ok or not pcred:
        return None
    try:
        c = pcred.contents
        if not c.CredentialBlob or c.CredentialBlobSize <= 0 or c.CredentialBlobSize > 1024 * 1024:
            return None
        return ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
    finally:
        cred_free(pcred)


def _decode_cred_json(raw: bytes) -> Optional[Dict[str, Any]]:
    for enc in ("utf-8", "utf-16-le"):
        try:
            obj = json.loads(raw.decode(enc))
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


def _resolve_credentials(cfg: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Read-only credential resolution. Never refreshes tokens."""
    explicit = cfg.get("credentials_path") or cfg.get("antigravity_credentials_path")
    if isinstance(explicit, str) and explicit.strip():
        p = Path(os.path.expandvars(os.path.expanduser(explicit.strip())))
        if not p.exists():
            return None, "missing_credential"
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None, "invalid_response"
        return _extract_token_from_obj(obj)

    raw = _read_wincred_blob(WINCRED_TARGET)
    if raw is None:
        return None, "missing_credential"
    obj = _decode_cred_json(raw)
    if obj is None:
        return None, "invalid_response"
    return _extract_token_from_obj(obj)


def _post_json(
    url: str,
    body: Dict[str, Any],
    headers: Dict[str, str],
    timeout: int = 15,
) -> Tuple[Optional[Dict[str, Any]], Optional[int], Optional[str]]:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    for k, v in headers.items():
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
        return None, code, "provider_unavailable"
    except urllib.error.URLError:
        return None, None, "network"
    except TimeoutError:
        return None, None, "timeout"
    except Exception:
        return None, None, "network"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:40]


def _explicit_duration_seconds(bucket: Dict[str, Any]) -> Optional[int]:
    for key, mult in (
        ("duration_seconds", 1.0),
        ("durationSeconds", 1.0),
        ("window_seconds", 1.0),
        ("windowSeconds", 1.0),
        ("windowMinutes", 60.0),
        ("window_minutes", 60.0),
    ):
        val = bucket.get(key)
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            continue
        secs = float(val) * mult
        if math.isfinite(secs) and 0 < secs < 10_000_000_000:
            return int(secs)
    return None


def _classify_window(bucket: Dict[str, Any]) -> Tuple[str, str, Optional[int], int]:
    """Classify window using explicit identifiers/durations only; keep unknown windows distinct."""
    w_raw = str(bucket.get("window") or "").strip().lower()
    bid = str(bucket.get("bucketId") or bucket.get("id") or "").strip()
    dname = str(bucket.get("displayName") or bucket.get("name") or "").strip()
    duration_s = _explicit_duration_seconds(bucket)

    if w_raw in ("5h", "5_hours", "five_hour", "rolling_5h") or duration_s == 5 * 3600:
        return "rolling_5h", "5 horas", duration_s if duration_s is not None else 5 * 3600, 0
    if w_raw in ("weekly", "week") or duration_s == 7 * 24 * 3600:
        return "week", "Semana", duration_s if duration_s is not None else 7 * 24 * 3600, 1
    if w_raw in ("monthly", "month"):
        return "month", "Mês", duration_s, 2

    wid = _slug(w_raw or bid or dname or "window") or "window"
    wlabel = dname or w_raw or bid or "Janela"
    return wid, wlabel, duration_s, 3


def _map_bucket(
    bucket: Dict[str, Any],
    scope: Dict[str, str],
    prefix: str,
    seen_ids: set[str],
) -> Optional[Tuple[int, Dict[str, Any]]]:
    if not isinstance(bucket, dict) or bucket.get("disabled") is True:
        return None

    rem = bucket.get("remainingFraction")
    if rem is None:
        rem = bucket.get("remaining_fraction")
    if isinstance(rem, bool) or not isinstance(rem, (int, float)):
        return None
    rem_f = float(rem)
    if not math.isfinite(rem_f) or rem_f < 0.0 or rem_f > 1.0:
        return None

    used_pct = round((1.0 - rem_f) * 100.0, 2)
    wid, wlabel, duration_s, sort_rank = _classify_window(bucket)

    window: Dict[str, Any] = {"id": wid, "label": wlabel}
    if duration_s is not None:
        window["duration_seconds"] = duration_s
    reset_at = _iso_or_none(bucket.get("resetTime") or bucket.get("reset_time"))
    if reset_at:
        window["reset_at"] = reset_at

    base_id = f"{prefix}_{wid}" if prefix else wid
    qid = base_id
    idx = 2
    while qid in seen_ids:
        qid = f"{base_id}_{idx}"
        idx += 1
    seen_ids.add(qid)

    return sort_rank, {
        "id": qid,
        "scope": scope,
        "window": window,
        "used_percent": used_pct,
    }


def _map_quota_summary(obj: Dict[str, Any]) -> Dict[str, Any]:
    ranked: List[Tuple[int, int, Dict[str, Any]]] = []
    seen_ids: set[str] = set()
    seq = 0

    groups = obj.get("groups")
    if isinstance(groups, list):
        for gi, grp in enumerate(groups):
            if not isinstance(grp, dict):
                continue
            glabel = str(grp.get("displayName") or grp.get("name") or f"Grupo {gi + 1}").strip()
            gid = _slug(glabel) or f"group_{gi}"
            scope = {"type": "model_group", "id": gid, "label": glabel}
            buckets = grp.get("buckets")
            if not isinstance(buckets, list):
                continue
            for b in buckets:
                mapped = _map_bucket(b, scope, gid, seen_ids)
                if mapped is not None:
                    rank, q = mapped
                    ranked.append((rank, seq, q))
                    seq += 1

    if not ranked and isinstance(obj.get("buckets"), list):
        acc = {"type": "account", "id": "account", "label": "Conta"}
        for b in obj["buckets"]:
            mapped = _map_bucket(b, acc, "account", seen_ids)
            if mapped is not None:
                rank, q = mapped
                ranked.append((rank, seq, q))
                seq += 1

    ranked.sort(key=lambda item: (item[0], item[1]))
    return {"quotas": [item[2] for item in ranked]}


def collect_direct(cfg: Dict[str, Any]) -> Dict[str, Any]:
    creds, cerr = _resolve_credentials(cfg)
    if cerr or not creds:
        code = cerr or "missing_credential"
        return {"ok": False, "error": safe_error(code, code)}

    headers = {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json",
        "User-Agent": "antigravity/1.0",
    }

    obj, status, err = _post_json(ENDPOINT_QUOTA_SUMMARY, {}, headers, timeout=15)
    needs_project = (
        (err == "provider_unavailable" and status == 400)
        or (err is None and isinstance(obj, dict) and not obj.get("groups") and not obj.get("buckets"))
    )
    if needs_project:
        lca, _, lca_err = _post_json(
            ENDPOINT_LOAD_CODE_ASSIST,
            {"metadata": {"ideType": "ANTIGRAVITY"}},
            headers,
            timeout=15,
        )
        proj = (lca or {}).get("cloudaicompanionProject") if not lca_err and isinstance(lca, dict) else None
        if isinstance(proj, str) and proj.strip():
            obj, status, err = _post_json(
                ENDPOINT_QUOTA_SUMMARY,
                {"project": proj.strip()},
                headers,
                timeout=15,
            )

    if err or not isinstance(obj, dict):
        code = err or "invalid_response"
        return {"ok": False, "error": safe_error(code, code)}

    data = _map_quota_summary(obj)
    if not data.get("quotas"):
        return {"ok": False, "error": safe_error("invalid_response", "unrecognized_usage_response")}
    return {"ok": True, "data": data}


def collect(cfg: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Read-only Antigravity usage collection independent of Orca and CLI.
    No token refresh, no paid generation.
    """
    try:
        return collect_direct(cfg)
    except Exception:
        return {"ok": False, "error": safe_error("provider_unavailable", "exception")}
