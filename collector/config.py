from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List


def default_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    return Path(base) / "LLMUsageWidget"


def default_snapshot_path() -> Path:
    return default_data_dir() / "snapshot.json"


def default_config_path() -> Path:
    return default_data_dir() / "config.json"


def _expand_path_str(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def builtin_default_config() -> Dict[str, Any]:
    # Safe defaults: known providers enabled; collection independent of Orca process.
    return {
        "schema_version": 1,
        "snapshot_path": str(default_snapshot_path()),
        "providers": [
            {"id": "claude", "plugin": "claude", "display_name": "Claude", "kind": "quota", "enabled": True, "visible": True, "order": 10, "collection_interval_seconds": 600, "credential_ref": "claude_default"},
            {"id": "codex", "plugin": "codex", "display_name": "Codex", "kind": "quota", "enabled": True, "visible": True, "order": 20, "collection_interval_seconds": 600, "credential_ref": "codex_default"},
            {"id": "antigravity", "plugin": "antigravity", "display_name": "Antigravity", "kind": "quota", "enabled": True, "visible": True, "order": 30, "collection_interval_seconds": 600, "credential_ref": "antigravity_default"},
            {"id": "opencode_go", "plugin": "opencode_go", "display_name": "OpenCode Go", "kind": "quota", "enabled": True, "visible": True, "order": 40, "collection_interval_seconds": 600, "credential_ref": "opencode_go_default"},
            {"id": "cursor", "plugin": "cursor", "display_name": "Cursor", "kind": "quota", "enabled": True, "visible": True, "order": 50, "collection_interval_seconds": 600, "credential_ref": "cursor_default"},
        ],
    }


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    cfg_path = path or default_config_path()
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = builtin_default_config()
    if not isinstance(cfg, dict):
        raise ValueError("config must be object")
    # Expand snapshot_path env vars for validation (B3); runner will re-expand and require absolute.
    if isinstance(cfg.get("snapshot_path"), str):
        cfg["snapshot_path"] = _expand_path_str(cfg["snapshot_path"])
        p = Path(cfg["snapshot_path"])
        if not p.is_absolute():
            raise ValueError(f"snapshot_path must be absolute after expansion: {cfg['snapshot_path']}")
    providers = cfg.get("providers")
    if not isinstance(providers, list):
        raise ValueError("providers must be list")
    seen = set()
    for p in providers:
        if not isinstance(p, dict):
            raise ValueError("provider must be object")
        pid = p.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError("provider missing/empty id")
        if pid in seen:
            raise ValueError(f"duplicate provider id in config: {pid}")
        seen.add(pid)
        if isinstance(p.get("credentials_path"), str):
            p["credentials_path"] = _expand_path_str(p["credentials_path"])
    return cfg


def ensure_config(path: Optional[Path] = None) -> Path:
    cfg_path = path or default_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if not cfg_path.exists():
        with open(cfg_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(builtin_default_config(), f, ensure_ascii=False, indent=2)
            f.write("\n")
    return cfg_path
