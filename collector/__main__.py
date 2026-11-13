from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .config import default_config_path, default_snapshot_path, ensure_config, load_config
from .contract import read_snapshot
from .runner import collect_once


def _resolve_snapshot_path(args) -> Path:
    snap = getattr(args, "snapshot", None)
    if snap:
        return Path(snap)
    cfg_path = getattr(args, "config", None)
    if cfg_path:
        cfg = load_config(Path(cfg_path))
        p = cfg.get("snapshot_path")
        if p:
            return Path(p)
    return default_snapshot_path()


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM usage collector (contract v1)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_once = sub.add_parser("collect-once", help="Collect once and write snapshot")
    p_once.add_argument("--config", help="Path to config.json")
    p_once.add_argument("--snapshot", help="Path to snapshot.json (overrides config)")

    p_loop = sub.add_parser("collect-loop", help="Collect repeatedly at fixed interval")
    p_loop.add_argument("--config", help="Path to config.json")
    p_loop.add_argument("--snapshot", help="Path to snapshot.json (overrides config)")
    p_loop.add_argument("--interval", type=int, default=300, help="Loop interval seconds (default 300)")

    p_init = sub.add_parser("init-config", help="Create default config in LOCALAPPDATA if missing")
    p_init.add_argument("--config", help="Path to config.json (default LOCALAPPDATA)")

    p_show = sub.add_parser("show-snapshot", help="Print snapshot path contents if valid")
    p_show.add_argument("--config", help="Path to config.json")
    p_show.add_argument("--snapshot", help="Path to snapshot.json (overrides config)")

    args = ap.parse_args()
    if args.cmd == "init-config":
        path = ensure_config(Path(args.config) if args.config else None)
        print(str(path))
        return 0
    if args.cmd == "show-snapshot":
        snap_path = _resolve_snapshot_path(args)
        snap = read_snapshot(snap_path)
        out = {
            "path": str(snap_path),
            "snapshot": snap,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if snap is not None else 1
    if args.cmd == "collect-once":
        try:
            snap = collect_once(getattr(args, "config", None), getattr(args, "snapshot", None))
        except Exception as e:
            print(json.dumps({"ok": False, "error": "write_failed", "message": "snapshot not published"}, ensure_ascii=False))
            return 1
        print(json.dumps({"ok": True, "generated_at": snap.get("generated_at"), "providers": len(snap.get("providers") or [])}, ensure_ascii=False))
        return 0
    if args.cmd == "collect-loop":
        interval = max(30, int(args.interval))
        try:
            while True:
                try:
                    collect_once(getattr(args, "config", None), getattr(args, "snapshot", None))
                except Exception:
                    # preserve previous published snapshot; keep loop alive
                    pass
                time.sleep(interval)
        except KeyboardInterrupt:
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
