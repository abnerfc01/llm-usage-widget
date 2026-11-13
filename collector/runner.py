from __future__ import annotations

import multiprocessing as mp
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import default_snapshot_path, load_config
from .contract import (
    atomic_write_json,
    default_provider_entry,
    freshness_state,
    normalize_provider_data,
    now_utc,
    origin_signature,
    parse_iso,
    read_snapshot,
    safe_error,
    to_iso,
)
from .providers import get_provider


def _test_mode_enabled() -> bool:
    return os.environ.get("LLM_USAGE_WIDGET_TEST_MODE", "").lower() in {"1", "true", "yes"}


def _provider_timeout_seconds(cfg: Dict[str, Any]) -> int:
    return int(cfg.get("timeout_seconds") or min(20, max(10, int(cfg.get("collection_interval_seconds") or 600) // 2)))


def _parse_iso_safe(v: Optional[str]) -> Optional[datetime]:
    if not v:
        return None
    try:
        return parse_iso(v)
    except Exception:
        return None


def _compute_next_attempt(now: datetime, interval_seconds: int, ok: bool) -> str:
    interval = max(int(interval_seconds or 600), 30)
    if ok:
        delta = interval
    else:
        # backoff: shorter retry, capped by interval
        delta = min(interval, max(120, interval // 3))
    return to_iso(now + timedelta(seconds=delta))  # type: ignore[arg-type]


def _expand_path(value: str) -> Path:
    """Expand env vars and home, require absolute path (B3)."""
    if not isinstance(value, str):
        raise ValueError(f"path must be string, got {type(value).__name__}")
    expanded = os.path.expandvars(os.path.expanduser(value))
    p = Path(expanded)
    if not p.is_absolute():
        raise ValueError(f"path must be absolute after expansion: {value}")
    return p


def _resolve_provider_fn(plugin_name: str, cfg: Dict[str, Any]):
    # Test hook: importable "module:attr" provider (used only by tests when test mode active).
    test_spec = cfg.get("_test_provider")
    if isinstance(test_spec, str) and ":" in test_spec:
        if not _test_mode_enabled():
            return None
        mod_name, attr = test_spec.split(":", 1)
        if not mod_name.startswith("tests."):
            return None
        import importlib
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)

    # Dynamic plugin loading (B6): plugin may be "module:attr" for built-in or user modules.
    if isinstance(plugin_name, str) and ":" in plugin_name:
        mod_name, attr = plugin_name.split(":", 1)
        import importlib
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)

    return get_provider(plugin_name)


def _mp_worker(plugin_name: str, cfg: Dict[str, Any], prev: Optional[Dict[str, Any]], q: mp.Queue) -> None:
    try:
        provider_fn = _resolve_provider_fn(plugin_name, cfg)
        if provider_fn is None:
            q.put({"ok": False, "error": safe_error("unsupported", "unknown_plugin"), "data": None})
            return
        result = provider_fn(cfg, prev)
        q.put(result)
    except Exception:
        q.put({"ok": False, "error": safe_error("provider_unavailable", "exception"), "data": None})


def _run_isolated(plugin_name: str, cfg: Dict[str, Any], prev: Optional[Dict[str, Any]], timeout: int) -> Dict[str, Any]:
    ctx = mp.get_context("spawn")
    q: mp.Queue = ctx.Queue()
    p = ctx.Process(target=_mp_worker, args=(plugin_name, cfg, prev, q), daemon=False)
    p.start()
    p.join(timeout)
    if p.is_alive():
        try:
            p.terminate()
        except Exception:
            pass
        p.join(2)
        if p.is_alive():
            try:
                p.kill()
            except Exception:
                pass
            p.join(1)
        try:
            q.close()
            q.join_thread()
        except Exception:
            pass
        return {"ok": False, "error": safe_error("timeout", "timeout"), "data": None}
    try:
        if not q.empty():
            res = q.get_nowait()
            if isinstance(res, dict):
                return res
    except Exception:
        pass
    finally:
        try:
            q.close()
            q.join_thread()
        except Exception:
            pass
    return {"ok": False, "error": safe_error("provider_unavailable", "exception"), "data": None}


def _attach_budget(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    budget_cfg = cfg.get("budget")
    if not isinstance(budget_cfg, dict) or not isinstance(data.get("money"), dict):
        return data
    money = data["money"]
    bcur = budget_cfg.get("currency")
    mcur = money.get("currency")
    if not isinstance(bcur, str) or not bcur or mcur != bcur:
        return data
    period = budget_cfg.get("period")
    if not isinstance(period, dict) or "id" not in period or "label" not in period:
        return data
    b = {
        "amount": str(budget_cfg["amount"]).strip(),
        "currency": bcur,
        "period": {"id": str(period["id"]), "label": str(period["label"])},
        "source": str(budget_cfg.get("source") or "local_config"),
    }
    scope = budget_cfg.get("scope")
    if isinstance(scope, dict):
        b["scope"] = {k: str(scope[k]) for k in ("type", "id", "label") if k in scope}
    money["budget"] = b
    return data


def run_provider(cfg: Dict[str, Any], previous: Optional[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
    entry = default_provider_entry(cfg)
    prev = previous or {}
    sig = entry["origin_signature"]
    prev_sig = prev.get("origin_signature")

    # preserve state from previous snapshot entry only if origin identity matches (B4)
    if prev.get("id") == entry["id"] and prev_sig == sig:
        for k in ("last_success_at", "last_attempt_at", "last_attempt_result", "error", "next_attempt_at"):
            if k in prev:
                entry[k] = prev.get(k)
        if prev.get("data") is not None:
            entry["data"] = prev.get("data")
        # keep previous kind/freshness fields as base; will recompute
        if prev.get("kind") in ("quota", "metered", "mixed"):
            entry["kind"] = prev.get("kind")

    interval = int(cfg.get("collection_interval_seconds") or entry.get("collection_interval_seconds") or 600)
    entry["collection_interval_seconds"] = interval

    # Disabled: do not call plugin, do not forge last_attempt_at, no alert (M7)
    if not cfg.get("enabled", True):
        entry["error"] = None
        entry["next_attempt_at"] = None
        entry["state"] = "disabled"
        if entry.get("last_attempt_result") not in ("success", "error", "never"):
            entry["last_attempt_result"] = "never"
        entry["freshness"] = freshness_state(_parse_iso_safe(entry.get("last_success_at")), interval, now)
        return entry

    # Scheduling: skip if before next_attempt_at
    next_at = _parse_iso_safe(entry.get("next_attempt_at"))
    if next_at and now < next_at:
        # no attempt; preserve previous attempt/result/error/data, recompute freshness only
        entry["freshness"] = freshness_state(_parse_iso_safe(entry.get("last_success_at")), interval, now)
        return entry

    plugin_name = cfg.get("plugin") or cfg.get("id")
    provider_fn = _resolve_provider_fn(str(plugin_name), cfg)
    if provider_fn is None:
        attempt_at = now
        entry["last_attempt_at"] = to_iso(attempt_at)
        entry["last_attempt_result"] = "error"
        entry["error"] = safe_error("unsupported", "unknown_plugin")
        entry["next_attempt_at"] = _compute_next_attempt(now, interval, False)
        entry["freshness"] = freshness_state(_parse_iso_safe(entry.get("last_success_at")), interval, now)
        return entry

    timeout = _provider_timeout_seconds(cfg)
    attempt_at = now
    result = _run_isolated(str(plugin_name), cfg, prev if prev.get("id") == entry["id"] else None, timeout)
    entry["last_attempt_at"] = to_iso(attempt_at)

    if result and result.get("ok"):
        raw_data = result.get("data") or {"quotas": []}
        try:
            data = normalize_provider_data(raw_data, cfg)
            if data is None:
                data = {"quotas": []}
            data = _attach_budget(data, cfg)
            if result.get("kind") in ("quota", "metered", "mixed"):
                entry["kind"] = result["kind"]
            entry["data"] = data
            entry["error"] = None
            entry["last_attempt_result"] = "success"
            entry["last_success_at"] = to_iso(now_utc())  # success time is after return (M6)
            entry["next_attempt_at"] = _compute_next_attempt(now, interval, True)
        except Exception as exc:
            # Isolated invalid payload: only this provider fails; others are unaffected (B2)
            entry["last_attempt_result"] = "error"
            entry["error"] = safe_error("invalid_response", "invalid_response")
            entry["next_attempt_at"] = _compute_next_attempt(now, interval, False)
    else:
        entry["last_attempt_result"] = "error"
        err = (result or {}).get("error") or safe_error("provider_unavailable")
        if not isinstance(err, dict) or "code" not in err:
            err = safe_error("provider_unavailable")
        entry["error"] = err
        entry["next_attempt_at"] = _compute_next_attempt(now, interval, False)
    entry["freshness"] = freshness_state(_parse_iso_safe(entry.get("last_success_at")), interval, now)
    return entry


def collect_once(config_path: Optional[str] = None, snapshot_path: Optional[str] = None) -> Dict[str, Any]:
    cfg = load_config(Path(config_path) if config_path else None)
    raw_snap_path = snapshot_path or cfg.get("snapshot_path")
    if not raw_snap_path:
        raise ValueError("snapshot_path missing")
    snap_path = _expand_path(str(raw_snap_path))

    # validate unique provider IDs in config (B7)
    seen_ids = set()
    for pcfg in (cfg.get("providers") or []):
        pid = pcfg.get("id")
        if not pid:
            raise ValueError("provider missing id")
        if pid in seen_ids:
            raise ValueError(f"duplicate provider id in config: {pid}")
        seen_ids.add(pid)

    previous_snapshot = read_snapshot(snap_path) or {"providers": []}
    # validate no duplicates in previous snapshot (B7)
    prev_ids = set()
    for p in (previous_snapshot.get("providers") or []):
        pid = p.get("id")
        if pid in prev_ids:
            raise ValueError(f"duplicate provider id in previous snapshot: {pid}")
        prev_ids.add(pid)
    prev_by_id = {p.get("id"): p for p in (previous_snapshot.get("providers") or []) if isinstance(p, dict)}

    now = now_utc()
    providers_out: List[Dict[str, Any]] = []
    for pcfg in (cfg.get("providers") or []):
        pid = pcfg.get("id")
        if not pid:
            continue
        prev = prev_by_id.get(pid)
        providers_out.append(run_provider(pcfg, prev, now))

    snapshot = {
        "schema_version": "1.0",
        "generated_at": to_iso(now_utc()),  # publication time after collection (M6)
        "providers": providers_out,
    }
    # Propagate write/validation failures: previous snapshot file remains untouched on failure.
    atomic_write_json(snap_path, snapshot)
    return snapshot
