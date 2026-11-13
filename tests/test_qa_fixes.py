import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ["LLM_USAGE_WIDGET_TEST_MODE"] = "1"

from collector import runner
from collector.config import load_config
from collector.contract import (
    _finite_decimal_string,
    _is_iso4217_currency,
    normalize_provider_data,
    origin_signature,
    validate_snapshot,
)
from collector.providers.claude_direct import _map_usage
from collector.providers.codex_direct import _map_usage as codex_map_usage


def _base_cfg(snap_path, providers):
    return {"schema_version": 1, "snapshot_path": str(snap_path), "providers": providers}


class QAFixesTests(unittest.TestCase):
    # B1 — allowlist removes arbitrary keys
    def test_arbitrary_key_does_not_leak_into_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "leak", "plugin": "leak", "display_name": "Leak", "kind": "quota", "enabled": True, "visible": True, "order": 1,
                 "collection_interval_seconds": 600, "_test_provider": "tests.helpers:bad_provider_leaks_secret"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap = runner.collect_once(str(cfg_path), str(snap_path))
            p = snap["providers"][0]
            self.assertEqual(p["last_attempt_result"], "error")
            self.assertEqual(p["error"]["code"], "invalid_response")
            self.assertIsNone(p["data"])
            raw = snap_path.read_text(encoding="utf-8")
            self.assertNotIn("FAKE_TEST_SECRET", raw)

    # B2 — invalid payload of one provider does not block others
    def test_invalid_payload_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "bad", "plugin": "bad", "display_name": "Bad", "kind": "quota", "enabled": True, "visible": True, "order": 1,
                 "collection_interval_seconds": 600, "_test_provider": "tests.helpers:bad_provider_invalid_percent"},
                {"id": "good", "plugin": "good", "display_name": "Good", "kind": "quota", "enabled": True, "visible": True, "order": 2,
                 "collection_interval_seconds": 600, "_test_provider": "tests.helpers:ok_provider"},
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap["providers"][0]["error"]["code"], "invalid_response")
            self.assertEqual(snap["providers"][1]["last_attempt_result"], "success")

    # B3 — relative path rejected
    def test_relative_snapshot_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg("LLMUsageWidget\\snapshot.json", [
                {"id": "a", "plugin": "okp", "display_name": "A", "kind": "quota", "enabled": True, "visible": True, "order": 1,
                 "collection_interval_seconds": 600, "_test_provider": "tests.helpers:ok_provider"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaises(ValueError):
                runner.collect_once(str(cfg_path), None)

    # B4 — origin signature invalidates cache
    def test_origin_signature_in_snapshot_and_invalidates(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "same", "plugin": "okp", "display_name": "Same", "kind": "quota", "enabled": True, "visible": True, "order": 1,
                 "collection_interval_seconds": 600, "credential_ref": "old", "_test_provider": "tests.helpers:ok_provider"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap1 = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertIn("origin_signature", snap1["providers"][0])
            # change origin and fail: old data must be discarded (B4)
            cfg["providers"][0]["credential_ref"] = "new"
            cfg["providers"][0]["_test_provider"] = "tests.helpers:fail_network_provider"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap2 = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap2["providers"][0]["last_attempt_result"], "error")
            self.assertIsNone(snap2["providers"][0]["data"])

    # B5 — codex duration real
    def test_codex_3600_maps_to_1h_not_5h(self):
        data = codex_map_usage({"rate_limit": {"primary_window": {"used_percent": 22, "limit_window_seconds": 3600}}})
        q = data["quotas"][0]
        self.assertEqual(q["window"]["duration_seconds"], 3600)
        self.assertEqual(q["window"]["id"], "rolling_1h")
        self.assertNotEqual(q["window"]["id"], "rolling_5h")

    # B6 — dynamic plugin via module:attr
    def test_dynamic_plugin_loading(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "dyn", "plugin": "tests.helpers:ok_provider", "display_name": "Dyn", "kind": "quota", "enabled": True, "visible": True, "order": 1,
                 "collection_interval_seconds": 600}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertEqual(snap["providers"][0]["last_attempt_result"], "success")

    def test_test_provider_not_available_in_production_mode(self):
        with mock.patch.dict(os.environ, {"LLM_USAGE_WIDGET_TEST_MODE": "0"}):
            fn = runner._resolve_provider_fn("okp", {"_test_provider": "tests.helpers:ok_provider"})
            self.assertIsNone(fn)

    # B7 — duplicate IDs rejected
    def test_duplicate_provider_ids_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "dup", "plugin": "okp", "display_name": "A", "kind": "quota", "enabled": True, "visible": True, "order": 1,
                 "collection_interval_seconds": 600, "_test_provider": "tests.helpers:ok_provider"},
                {"id": "dup", "plugin": "okp", "display_name": "B", "kind": "quota", "enabled": True, "visible": True, "order": 2,
                 "collection_interval_seconds": 600, "_test_provider": "tests.helpers:ok_provider"},
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                runner.collect_once(str(cfg_path), str(snap_path))
            self.assertIn("duplicate", str(ctx.exception).lower())

    # M1 — validation helpers
    def test_finite_decimal_string(self):
        self.assertTrue(_finite_decimal_string("12.40"))
        self.assertTrue(_finite_decimal_string("0"))
        self.assertFalse(_finite_decimal_string("NaN"))
        self.assertFalse(_finite_decimal_string("inf"))
        self.assertFalse(_finite_decimal_string(12.4))

    def test_iso4217_currency(self):
        self.assertTrue(_is_iso4217_currency("USD"))
        self.assertFalse(_is_iso4217_currency("US$"))
        self.assertFalse(_is_iso4217_currency("us"))

    def test_validate_rejects_bool_used_percent(self):
        snap = {
            "schema_version": "1.0",
            "generated_at": "2026-11-11T14:00:00-03:00",
            "providers": [{
                "id": "p", "display_name": "P", "kind": "quota", "enabled": True, "visible": True,
                "collection_interval_seconds": 600, "last_attempt_at": None, "last_attempt_result": "never",
                "last_success_at": None, "freshness": {"state": "never", "stale_after": None},
                "error": None, "data": {"quotas": [{"id": "q", "scope": {"type": "account", "id": "a", "label": "A"},
                                                      "window": {"id": "w", "label": "W"}, "used_percent": True}]},
                "origin_signature": origin_signature({"id": "p"}),
            }]
        }
        with self.assertRaises(ValueError):
            validate_snapshot(snap)

    # M2 — zero preserved in extra_usage
    def test_claude_extra_usage_zero_preserved(self):
        data = _map_usage({"extra_usage": [{"name": "extra", "utilization": 0.0}]})
        self.assertEqual(len(data["quotas"]), 1)
        self.assertEqual(data["quotas"][0]["used_percent"], 0.0)

    # M5 — show-snapshot path resolution
    def test_cli_show_snapshot_uses_custom_path(self):
        from collector.__main__ import _resolve_snapshot_path
        import argparse
        args = argparse.Namespace(snapshot="C:\\tmp\\x.json", config=None)
        self.assertEqual(str(_resolve_snapshot_path(args)), "C:\\tmp\\x.json")

    # M6 — generated_at after collection, last_success_at after success
    def test_generated_at_after_provider_success(self):
        with tempfile.TemporaryDirectory() as td:
            snap_path = Path(td) / "snapshot.json"
            cfg = _base_cfg(snap_path, [
                {"id": "a", "plugin": "okp", "display_name": "A", "kind": "quota", "enabled": True, "visible": True, "order": 1,
                 "collection_interval_seconds": 600, "_test_provider": "tests.helpers:ok_provider"}
            ])
            cfg_path = Path(td) / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            snap = runner.collect_once(str(cfg_path), str(snap_path))
            self.assertIsNotNone(snap["generated_at"])
            self.assertEqual(snap["providers"][0]["last_attempt_result"], "success")
            self.assertIsNotNone(snap["providers"][0]["last_success_at"])


if __name__ == "__main__":
    unittest.main()
