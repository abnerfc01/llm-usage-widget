import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

os.environ["LLM_USAGE_WIDGET_TEST_MODE"] = "1"

from collector import runner
from collector.contract import read_snapshot, to_iso


def _base_cfg(snap_path, providers):
    return {"schema_version": 1, "snapshot_path": str(snap_path), "providers": providers}


class RunnerTests(unittest.TestCase):
    def test_isolated_failure_preserves_last_success_and_not_forge_on_skip(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "a", "plugin": "okp", "display_name": "A", "kind": "quota", "enabled": True, "visible": True, "order": 1, "collection_interval_seconds": 600, "_test_provider": "tests.helpers:ok_provider"},
                {"id": "b", "plugin": "failp", "display_name": "B", "kind": "quota", "enabled": True, "visible": True, "order": 2, "collection_interval_seconds": 600, "_test_provider": "tests.helpers:fail_provider"},
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap1 = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap1["providers"][0]["last_attempt_result"], "success")
            self.assertIsNotNone(snap1["providers"][0]["data"])
            self.assertIsNotNone(snap1["providers"][0].get("next_attempt_at"))
            self.assertEqual(snap1["providers"][1]["last_attempt_result"], "error")
            self.assertIsNone(snap1["providers"][1]["data"])
            first_success_at = snap1["providers"][0]["last_success_at"]
            first_attempt_at = snap1["providers"][0]["last_attempt_at"]

            # before next_attempt_at -> skip, must not forge last_attempt_at
            snap2 = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap2["providers"][0]["last_attempt_at"], first_attempt_at)
            self.assertEqual(snap2["providers"][0]["last_success_at"], first_success_at)
            self.assertEqual(snap2["providers"][0]["last_attempt_result"], "success")

            # force due: set next_attempt_at in past, provider fails now but previous good data preserved
            prev = read_snapshot(snap_path)
            prev["providers"][0]["next_attempt_at"] = "2000-01-01T00:00:00+00:00"
            from collector.contract import atomic_write_json
            atomic_write_json(snap_path, prev)
            cfg["providers"][0]["_test_provider"] = "tests.helpers:fail_network_provider"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap3 = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap3["providers"][0]["last_attempt_result"], "error")
            self.assertIsNotNone(snap3["providers"][0]["data"], "last good data must be preserved")
            self.assertEqual(snap3["providers"][0]["last_success_at"], first_success_at)

    def test_budget_attached_when_compatible(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "m", "plugin": "mp", "display_name": "M", "kind": "metered", "enabled": True, "visible": True, "order": 1,
                 "collection_interval_seconds": 600, "_test_provider": "tests.helpers:metered_ok_provider",
                 "budget": {"amount": "20.00", "currency": "USD", "period": {"id": "2026-11", "label": "Novembro"}, "source": "local_config"}}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap = runner.collect_once(str(cfg_path), str(snap_path))
            money = snap["providers"][0]["data"]["money"]
            self.assertIn("budget", money)
            self.assertEqual(money["budget"]["amount"], "20.00")

    def test_exception_isolated_and_safe(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "x", "plugin": "boom", "display_name": "X", "kind": "quota", "enabled": True, "visible": True, "order": 1, "collection_interval_seconds": 600, "_test_provider": "tests.helpers:boom_provider"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap["providers"][0]["last_attempt_result"], "error")
            self.assertIn(snap["providers"][0]["error"]["code"], {"provider_unavailable", "timeout", "invalid_response", "unsupported", "missing_credential", "auth_expired", "network"})

    def test_disabled_does_not_forge_attempt_and_no_alert(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "d", "plugin": "okp", "display_name": "D", "kind": "quota", "enabled": False, "visible": True, "order": 1, "collection_interval_seconds": 600, "_test_provider": "tests.helpers:ok_provider"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertIsNone(snap["providers"][0].get("last_attempt_at"))
            self.assertEqual(snap["providers"][0].get("last_attempt_result"), "never")
            self.assertIsNone(snap["providers"][0].get("next_attempt_at"))
            self.assertIsNone(snap["providers"][0].get("error"))
            self.assertEqual(snap["providers"][0].get("state"), "disabled")

    def test_timeout_bounded_for_hanging_provider(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "h", "plugin": "hang", "display_name": "H", "kind": "quota", "enabled": True, "visible": True, "order": 1, "collection_interval_seconds": 600, "timeout_seconds": 1, "_test_provider": "tests.helpers:hang_provider"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            start = time.time()
            snap = runner.collect_once(str(cfg_path), str(snap_path))
            elapsed = time.time() - start
            self.assertLess(elapsed, 8, "collection must not block on hanging provider")
            self.assertEqual(snap["providers"][0]["last_attempt_result"], "error")
            self.assertEqual(snap["providers"][0]["error"]["code"], "timeout")

    def test_write_failure_propagates_and_preserves_previous(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "a", "plugin": "okp", "display_name": "A", "kind": "quota", "enabled": True, "visible": True, "order": 1, "collection_interval_seconds": 600, "_test_provider": "tests.helpers:ok_provider"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            runner.collect_once(str(cfg_path), str(snap_path))
            before = snap_path.read_text(encoding="utf-8")
            with mock.patch("collector.runner.atomic_write_json", side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError):
                    runner.collect_once(str(cfg_path), str(snap_path))
            after = snap_path.read_text(encoding="utf-8")
            self.assertEqual(before, after, "previous snapshot file must remain untouched on write failure")

    def test_origin_signature_change_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "same", "plugin": "okp", "display_name": "Same", "kind": "quota", "enabled": True, "visible": True, "order": 1, "collection_interval_seconds": 600, "credential_ref": "old-account", "_test_provider": "tests.helpers:ok_provider"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap1 = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap1["providers"][0]["last_attempt_result"], "success")
            self.assertIsNotNone(snap1["providers"][0]["data"])
            old_data = snap1["providers"][0]["data"]

            # change credential_ref -> new origin; on subsequent failure, old data must NOT be preserved (B4)
            cfg["providers"][0]["credential_ref"] = "different-account"
            cfg["providers"][0]["_test_provider"] = "tests.helpers:fail_network_provider"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap2 = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap2["providers"][0]["last_attempt_result"], "error")
            self.assertIsNone(snap2["providers"][0]["data"], "cache must be invalidated when origin changes")
            self.assertIsNone(snap2["providers"][0]["last_success_at"])

            # on success with new origin, new data is allowed (force due to skip backoff)
            prev = read_snapshot(snap_path)
            prev["providers"][0]["next_attempt_at"] = "2000-01-01T00:00:00+00:00"
            from collector.contract import atomic_write_json
            atomic_write_json(snap_path, prev)
            cfg["providers"][0]["_test_provider"] = "tests.helpers:ok_provider"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap3 = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap3["providers"][0]["last_attempt_result"], "success")
            self.assertIsNotNone(snap3["providers"][0]["data"])


if __name__ == "__main__":
    unittest.main()
