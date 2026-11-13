from __future__ import annotations

from typing import Any, Dict, List, Optional

from .orca_source import ms_to_iso


def _window_id_from_minutes(minutes: Optional[int], fallback: str) -> str:
    if minutes == 300:
        return "rolling_5h"
    if minutes == 10080:
        return "week"
    if minutes in (43200, 44640, 40320):
        return "month"
    return fallback


def _window_label_from_id(wid: str, default: str) -> str:
    if wid == "rolling_5h":
        return "5 horas"
    if wid == "week":
        return "Semana"
    if wid == "month":
        return "Mês"
    return default


def quota_from_slot(slot: Dict[str, Any], qid: str, scope: Dict[str, str], window_default_id: str, window_default_label: str) -> Optional[Dict[str, Any]]:
    if not isinstance(slot, dict):
        return None
    if slot.get("usedPercent") is None:
        return None
    minutes = slot.get("windowMinutes")
    wid = _window_id_from_minutes(minutes, window_default_id)
    wlabel = _window_label_from_id(wid, window_default_label)
    window: Dict[str, Any] = {"id": wid, "label": wlabel}
    if isinstance(minutes, int) and minutes > 0:
        window["duration_seconds"] = minutes * 60
    reset = ms_to_iso(slot.get("resetsAt"))
    if reset:
        window["reset_at"] = reset
    q = {
        "id": qid,
        "scope": scope,
        "window": window,
        "used_percent": float(slot.get("usedPercent") or 0),
    }
    return q


def map_claude(entry: Dict[str, Any]) -> Dict[str, Any]:
    quotas: List[Dict[str, Any]] = []
    acc = {"type": "account", "id": "account", "label": "Conta"}
    s = quota_from_slot(entry.get("session") or {}, "account_5h", acc, "rolling_5h", "5 horas")
    if s: quotas.append(s)
    w = quota_from_slot(entry.get("weekly") or {}, "account_week", acc, "week", "Semana")
    if w: quotas.append(w)
    # fableWeekly is model-scoped weekly in observed Orca data
    fw = entry.get("fableWeekly")
    if isinstance(fw, dict) and fw.get("usedPercent") is not None:
        q = quota_from_slot(fw, "model_fable_week", {"type": "model", "id": "fable", "label": "Fable"}, "week", "Semana")
        if q: quotas.append(q)
    m = quota_from_slot(entry.get("monthly") or {}, "account_month", acc, "month", "Mês")
    if m: quotas.append(m)
    return {"quotas": quotas}


def map_codex(entry: Dict[str, Any]) -> Dict[str, Any]:
    quotas: List[Dict[str, Any]] = []
    acc = {"type": "account", "id": "account", "label": "Conta"}
    s = quota_from_slot(entry.get("session") or {}, "account_5h", acc, "rolling_5h", "5 horas")
    if s: quotas.append(s)
    w = quota_from_slot(entry.get("weekly") or {}, "account_week", acc, "week", "Semana")
    if w: quotas.append(w)
    # credits not part of quotas/money contract v1; keep in provider-level metadata? contract doesn't define it,
    # but data can hold extra keys under quotas/money? better omit non-contract to be safe. Document in impl notes.
    return {"quotas": quotas}


def map_opencode_go(entry: Dict[str, Any]) -> Dict[str, Any]:
    quotas: List[Dict[str, Any]] = []
    acc = {"type": "account", "id": "account", "label": "Conta"}
    s = quota_from_slot(entry.get("session") or {}, "account_5h", acc, "rolling_5h", "5 horas")
    if s: quotas.append(s)
    w = quota_from_slot(entry.get("weekly") or {}, "account_week", acc, "week", "Semana")
    if w: quotas.append(w)
    m = quota_from_slot(entry.get("monthly") or {}, "account_month", acc, "month", "Mês")
    if m: quotas.append(m)
    data: Dict[str, Any] = {"quotas": quotas}
    extra = entry.get("extraUsage")
    # extraUsage can represent metered/currency info in future; only include if has real monetary values we can map safely
    if isinstance(extra, dict):
        # if spent/balance provided as numbers/strings and currency known, map to money.spend/balance (best-effort, non-invented)
        money: Dict[str, Any] = {}
        cur = extra.get("currencyCode") or "USD"
        if isinstance(cur, str) and len(cur) == 3:
            money["currency"] = cur
        spent = extra.get("spent")
        if spent is not None and money.get("currency"):
            # only include if it's a real value
            try:
                money.setdefault("spend", []).append({"period": {"id": "current", "label": "Atual"}, "amount": str(spent)})
            except Exception:
                pass
        bal = extra.get("balance")
        if bal is not None and money.get("currency"):
            money["balance"] = str(bal)
        if money.get("currency") and (money.get("spend") or money.get("balance")):
            data["money"] = money
    return data


def _bucket_window(bucket: Dict[str, Any]) -> Dict[str, Any]:
    minutes = bucket.get("windowMinutes")
    wname = str(bucket.get("windowName") or "")
    if minutes == 300 or "Five Hour" in wname or "5" in wname and "Hour" in wname:
        wid, wlabel = "rolling_5h", "5 horas"
    elif minutes == 10080 or "Week" in wname:
        wid, wlabel = "week", "Semana"
    elif minutes and minutes >= 43200:
        wid, wlabel = "month", "Mês"
    else:
        wid, wlabel = (str(bucket.get("name") or "window").lower().replace(" ", "_")[:40] or "window"), (wname or "Janela")
    window: Dict[str, Any] = {"id": wid, "label": wlabel}
    if isinstance(minutes, int) and minutes > 0:
        window["duration_seconds"] = minutes * 60
    reset = ms_to_iso(bucket.get("resetsAt"))
    if reset:
        window["reset_at"] = reset
    return window


def map_antigravity(entry: Dict[str, Any]) -> Dict[str, Any]:
    quotas: List[Dict[str, Any]] = []
    acc = {"type": "account", "id": "account", "label": "Conta"}
    s = quota_from_slot(entry.get("session") or {}, "account_5h", acc, "rolling_5h", "5 horas")
    if s: quotas.append(s)
    w = quota_from_slot(entry.get("weekly") or {}, "account_week", acc, "week", "Semana")
    if w: quotas.append(w)
    buckets = entry.get("buckets") or []
    for i, b in enumerate(buckets):
        if not isinstance(b, dict) or b.get("usedPercent") is None:
            continue
        group = str(b.get("group") or b.get("name") or f"group_{i}")
        scope = {"type": "model_group", "id": group, "label": group}
        window = _bucket_window(b)
        qid = f"bucket_{i}_{window.get('id','w')}"
        q = {
            "id": qid,
            "scope": scope,
            "window": window,
            "used_percent": float(b.get("usedPercent") or 0),
        }
        quotas.append(q)
    return {"quotas": quotas}


def map_cursor(entry: Dict[str, Any]) -> Dict[str, Any]:
    quotas: List[Dict[str, Any]] = []
    acc = {"type": "account", "id": "account", "label": "Conta"}
    s = quota_from_slot(entry.get("session") or {}, "account_5h", acc, "rolling_5h", "5 horas")
    if s: quotas.append(s)
    w = quota_from_slot(entry.get("weekly") or {}, "account_week", acc, "week", "Semana")
    if w: quotas.append(w)
    m = quota_from_slot(entry.get("monthly") or {}, "account_month", acc, "month", "Mês")
    if m: quotas.append(m)
    return {"quotas": quotas}

