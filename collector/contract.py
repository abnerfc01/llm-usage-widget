from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"
ALLOWED_ERROR_CODES = {
    "missing_credential",
    "auth_expired",
    "network",
    "timeout",
    "provider_unavailable",
    "unsupported",
    "invalid_response",
}
ALLOWED_MESSAGE_KEYS = {
    "disabled",
    "unknown_plugin",
    "timeout",
    "exception",
    "no_verified_source",
    "orca_unavailable",
    "auth_expired",
    "missing_credential",
    "network",
    "provider_unavailable",
    "unsupported",
    "invalid_response",
    "independent_source_unverified",
    "unrecognized_usage_response",
    "not_implemented",
}
ALLOWED_ATTEMPT_RESULTS = {"success", "error", "never"}
ALLOWED_KINDS = {"quota", "metered", "mixed"}
ALLOWED_FRESHNESS = {"fresh", "stale", "never"}

# Allowlist for provider data payload (B1)
ALLOWED_DATA_TOP_KEYS = {"quotas", "money"}
ALLOWED_QUOTA_KEYS = {"id", "scope", "window", "used_percent"}
ALLOWED_SCOPE_KEYS = {"type", "id", "label"}
ALLOWED_WINDOW_KEYS = {"id", "label", "duration_seconds", "reset_at"}
ALLOWED_MONEY_KEYS = {"currency", "balance", "spend", "budget"}
ALLOWED_SPEND_KEYS = {"period", "amount"}
ALLOWED_PERIOD_KEYS = {"id", "label"}
ALLOWED_BUDGET_KEYS = {"amount", "currency", "period", "source", "scope"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="seconds")


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def parse_iso_strict(value: Optional[str]) -> Optional[datetime]:
    """Require explicit timezone per contract v1 (M1)."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt
    except Exception:
        return None


def freshness_state(last_success_at: Optional[datetime], collection_interval_seconds: int, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or now_utc()
    if last_success_at is None:
        return {"state": "never", "stale_after": None}
    interval = max(int(collection_interval_seconds or 0), 0)
    stale_delta = max(3 * interval, 1800)
    stale_after = last_success_at + timedelta(seconds=stale_delta)
    state = "fresh" if now <= stale_after else "stale"
    return {"state": state, "stale_after": to_iso(stale_after)}


def safe_error(code: str, message_key: Optional[str] = None) -> Dict[str, str]:
    if code not in ALLOWED_ERROR_CODES:
        code = "provider_unavailable"
    err: Dict[str, str] = {"code": code}
    if message_key:
        if message_key in ALLOWED_MESSAGE_KEYS:
            err["message_key"] = message_key
        elif code in ALLOWED_MESSAGE_KEYS:
            err["message_key"] = code
        else:
            err["message_key"] = "provider_unavailable"
    return err


def sanitize_text(value: Any, max_len: int = 200) -> str:
    if value is None:
        return ""
    s = str(value)
    s = re.sub(r"[\x00-\x1f\x7f]+", " ", s).strip()
    s = re.sub(r"(sk-[A-Za-z0-9]{10,}|sess-[A-Za-z0-9]{10,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}|Bearer\s+[A-Za-z0-9._\-]+)", "[redacted]", s)
    return s[:max_len]


def _finite_decimal_string(v: Any) -> bool:
    if not isinstance(v, str):
        return False
    v = v.strip()
    if not v:
        return False
    try:
        f = float(v)
    except ValueError:
        return False
    return math.isfinite(f)


def _is_iso4217_currency(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 3 and v.isalpha() and v.isupper()


def origin_signature(cfg: Dict[str, Any]) -> str:
    """Stable identity of the provider source (no secrets). Used to invalidate cache (B4)."""
    parts = [
        str(cfg.get("plugin") or cfg.get("id") or ""),
        str(cfg.get("credential_ref") or ""),
        str(cfg.get("credentials_path") or ""),
        str(cfg.get("credential_source") or ""),
    ]
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return h


def default_provider_entry(cfg: Dict[str, Any]) -> Dict[str, Any]:
    interval = int(cfg.get("collection_interval_seconds") or 600)
    return {
        "id": cfg["id"],
        "display_name": cfg.get("display_name") or cfg["id"],
        "kind": cfg.get("kind") or "quota",
        "enabled": bool(cfg.get("enabled", True)),
        "visible": bool(cfg.get("visible", True)),
        "collection_interval_seconds": interval,
        "last_attempt_at": None,
        "last_attempt_result": "never",
        "last_success_at": None,
        "freshness": {"state": "never", "stale_after": None},
        "error": None,
        "data": None,
        "origin_signature": origin_signature(cfg),
    }


def normalize_provider_data(data: Any, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Strict allowlist normalization of plugin data payload (B1/B2/M1). Returns dict or raises ValueError."""
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("data must be object")

    # Reject unknown top-level keys (e.g. raw_token)
    unknown = set(data.keys()) - ALLOWED_DATA_TOP_KEYS
    if unknown:
        raise ValueError(f"unknown data keys: {sorted(unknown)}")

    out: Dict[str, Any] = {}
    quotas: List[Dict[str, Any]] = []
    for q in (data.get("quotas") or []):
        if not isinstance(q, dict):
            raise ValueError("quota must be object")
        bad_keys = set(q.keys()) - ALLOWED_QUOTA_KEYS
        if bad_keys:
            raise ValueError(f"unknown quota keys: {sorted(bad_keys)}")
        for k in ("id", "scope", "window", "used_percent"):
            if k not in q:
                raise ValueError(f"quota missing {k}")
        scope = q["scope"]
        if not isinstance(scope, dict):
            raise ValueError("scope must be object")
        for k in ("type", "id", "label"):
            if k not in scope:
                raise ValueError(f"scope missing {k}")
        if set(scope.keys()) - ALLOWED_SCOPE_KEYS:
            raise ValueError("scope has unknown keys")
        window = q["window"]
        if not isinstance(window, dict):
            raise ValueError("window must be object")
        for k in ("id", "label"):
            if k not in window:
                raise ValueError(f"window missing {k}")
        if set(window.keys()) - ALLOWED_WINDOW_KEYS:
            raise ValueError("window has unknown keys")
        up = q["used_percent"]
        if isinstance(up, bool) or not isinstance(up, (int, float)) or not math.isfinite(up) or up < 0:
            raise ValueError("used_percent must be finite non-negative number")
        nq: Dict[str, Any] = {
            "id": str(q["id"]),
            "scope": {k: str(scope[k]) for k in ALLOWED_SCOPE_KEYS},
            "window": {
                "id": str(window["id"]),
                "label": str(window["label"]),
            },
            "used_percent": float(up),
        }
        if "duration_seconds" in window:
            ds = window["duration_seconds"]
            if isinstance(ds, bool) or not isinstance(ds, (int, float)) or not math.isfinite(ds) or ds <= 0:
                raise ValueError("duration_seconds must be positive number")
            nq["window"]["duration_seconds"] = int(ds)
        if "reset_at" in window:
            if parse_iso_strict(window["reset_at"]) is None:
                raise ValueError("reset_at must be ISO 8601 with timezone")
            nq["window"]["reset_at"] = str(window["reset_at"])
        quotas.append(nq)
    out["quotas"] = quotas

    money = data.get("money")
    if money is not None:
        if not isinstance(money, dict):
            raise ValueError("money must be object")
        if set(money.keys()) - ALLOWED_MONEY_KEYS:
            raise ValueError("money has unknown keys")
        if not _is_iso4217_currency(money.get("currency")):
            raise ValueError("money.currency must be ISO 4217 3-letter uppercase")
        nmoney: Dict[str, Any] = {"currency": money["currency"]}
        if "balance" in money and money["balance"] is not None:
            if not _finite_decimal_string(money["balance"]):
                raise ValueError("money.balance must be finite decimal string")
            nmoney["balance"] = str(money["balance"]).strip()
        spend_out: List[Dict[str, Any]] = []
        for s in (money.get("spend") or []):
            if not isinstance(s, dict):
                raise ValueError("spend item must be object")
            if set(s.keys()) - ALLOWED_SPEND_KEYS:
                raise ValueError("spend item has unknown keys")
            if "amount" not in s or not _finite_decimal_string(s["amount"]):
                raise ValueError("spend.amount must be finite decimal string")
            ns = {"amount": str(s["amount"]).strip()}
            period = s.get("period")
            if period is not None:
                if not isinstance(period, dict) or set(period.keys()) - ALLOWED_PERIOD_KEYS:
                    raise ValueError("spend.period invalid")
                for k in ("id", "label"):
                    if k not in period:
                        raise ValueError("spend.period missing id/label")
                ns["period"] = {"id": str(period["id"]), "label": str(period["label"])}
            spend_out.append(ns)
        nmoney["spend"] = spend_out
        budget = money.get("budget")
        if budget is not None:
            if not isinstance(budget, dict) or set(budget.keys()) - ALLOWED_BUDGET_KEYS:
                raise ValueError("budget invalid")
            if "amount" not in budget or "currency" not in budget or "period" not in budget:
                raise ValueError("budget missing amount/currency/period")
            if not _finite_decimal_string(budget["amount"]):
                raise ValueError("budget.amount must be finite decimal string")
            if not _is_iso4217_currency(budget["currency"]):
                raise ValueError("budget.currency must be ISO 4217 3-letter uppercase")
            period = budget["period"]
            if not isinstance(period, dict) or "id" not in period or "label" not in period:
                raise ValueError("budget.period invalid")
            nbudget = {
                "amount": str(budget["amount"]).strip(),
                "currency": budget["currency"],
                "period": {"id": str(period["id"]), "label": str(period["label"])},
                "source": str(budget.get("source") or "local_config"),
            }
            scope = budget.get("scope")
            if scope is not None:
                if not isinstance(scope, dict) or set(scope.keys()) - ALLOWED_SCOPE_KEYS:
                    raise ValueError("budget.scope invalid")
                nbudget["scope"] = {k: str(scope[k]) for k in ALLOWED_SCOPE_KEYS if k in scope}
            nmoney["budget"] = nbudget
        out["money"] = nmoney

    return out


def validate_snapshot(snapshot: Dict[str, Any]) -> None:
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {snapshot.get('schema_version')}")
    if not isinstance(snapshot.get("generated_at"), str):
        raise ValueError("generated_at must be string")
    if parse_iso_strict(snapshot["generated_at"]) is None:
        raise ValueError("generated_at must be ISO 8601 with timezone")
    providers = snapshot.get("providers")
    if not isinstance(providers, list):
        raise ValueError("providers must be list")
    ids = set()
    for p in providers:
        if not isinstance(p, dict):
            raise ValueError("provider must be object")
        pid = p.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError("provider missing/empty id")
        if pid in ids:
            raise ValueError(f"duplicate provider id: {pid}")
        ids.add(pid)
        for k in ("id", "display_name", "kind", "collection_interval_seconds", "last_attempt_result", "freshness", "origin_signature"):
            if k not in p:
                raise ValueError(f"provider missing {k}")
        if p["kind"] not in ALLOWED_KINDS:
            raise ValueError(f"invalid kind {p['kind']}")
        if p["last_attempt_result"] not in ALLOWED_ATTEMPT_RESULTS:
            raise ValueError(f"invalid last_attempt_result {p['last_attempt_result']}")
        f = p["freshness"]
        if not isinstance(f, dict) or f.get("state") not in ALLOWED_FRESHNESS:
            raise ValueError("invalid freshness")
        err = p.get("error")
        if err is not None:
            if not isinstance(err, dict) or err.get("code") not in ALLOWED_ERROR_CODES:
                raise ValueError("invalid error")
        # Attempt marks the start; success marks its completion or an older cache.
        gen = parse_iso_strict(snapshot["generated_at"])
        times = {}
        for key in ("last_attempt_at", "last_success_at"):
            value = p.get(key)
            parsed = parse_iso_strict(value) if isinstance(value, str) else None
            if value is not None and parsed is None:
                raise ValueError(f"{key} must be ISO 8601 with timezone or null")
            if parsed and gen and parsed > gen:
                raise ValueError(f"{key} cannot be after generated_at")
            times[key] = parsed
        laa = times["last_attempt_at"]
        lsa = times["last_success_at"]
        result = p["last_attempt_result"]
        if result == "never" and (laa or lsa):
            raise ValueError("never cannot have attempt or success timestamps")
        if result != "never" and not laa:
            raise ValueError("attempt timestamp required for success or error")
        if result == "success" and (not lsa or lsa < laa):
            raise ValueError("success timestamp must be at or after attempt")
        if result == "error" and lsa and lsa > laa:
            raise ValueError("cached success cannot be after failed attempt")
        data = p.get("data")
        if data is not None:
            if not isinstance(data, dict):
                raise ValueError("data must be object or null")
            # re-validate through normalizer for strictness
            normalize_provider_data(data, {})


def atomic_write_json(path: Path, snapshot: Dict[str, Any]) -> None:
    validate_snapshot(snapshot)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=False)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass


def read_snapshot(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        validate_snapshot(obj)
        return obj
    except Exception:
        return None
