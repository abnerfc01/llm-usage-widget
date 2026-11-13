import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from collector.contract import normalize_provider_data
from collector.providers import opencode_go


def _auth_json(key: str = "sk-opencode-test-key") -> str:
    return json.dumps({"opencode-go": {"type": "api", "key": key}})


def _sample_usage() -> dict:
    return {
        "usage": {
            "monthly": {"percent": 12, "resetsAt": "2026-12-01T00:00:00Z", "status": "ok"},
            "weekly": {"percent": 34.5, "resetsAt": "2026-11-20T00:00:00Z", "status": "ok"},
            "rolling": {"percent": 8, "resetsAt": "2026-11-14T01:00:00Z", "status": "ok"},
        }
    }


class OpenCodeGoSourceTests(unittest.TestCase):
    def test_mapping_windows_order_and_contract_validation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "auth.json"
            p.write_text(_auth_json(), encoding="utf-8")

            with mock.patch("collector.providers.opencode_go.get_json", return_value=(_sample_usage(), 200, None)):
                res = opencode_go.collect({"id": "opencode_go", "credentials_path": str(p)}, None)

            self.assertTrue(res.get("ok"))
            quotas = res["data"]["quotas"]
            self.assertEqual(len(quotas), 3)

            # Ordered: rolling_5h, week, month
            self.assertEqual([q["window"]["id"] for q in quotas], ["rolling_5h", "week", "month"])
            self.assertEqual(quotas[0]["window"]["duration_seconds"], 18000)
            self.assertEqual(quotas[1]["window"]["duration_seconds"], 604800)
            # Monthly must not invent 30d duration_seconds
            self.assertNotIn("duration_seconds", quotas[2]["window"])
            self.assertAlmostEqual(quotas[0]["used_percent"], 8.0)
            self.assertAlmostEqual(quotas[1]["used_percent"], 34.5)
            self.assertAlmostEqual(quotas[2]["used_percent"], 12.0)

            normalized = normalize_provider_data(res["data"], {"id": "opencode_go"})
            self.assertEqual(len(normalized["quotas"]), 3)

    def test_unknown_windows_distinct_and_invalid_percents_rejected(self):
        payload = {
            "usage": {
                "custom_a": {"percent": 15},
                "custom_b": {"percent": 25},
                "bad_neg": {"percent": -1},
                "bad_over": {"percent": 100.1},
                "bad_nan": {"percent": float("nan")},
                "bad_inf": {"percent": float("inf")},
                "bad_bool": {"percent": True},
            }
        }
        mapped = opencode_go._map_usage(payload)
        quotas = mapped["quotas"]
        self.assertEqual(len(quotas), 2)
        self.assertEqual([q["window"]["id"] for q in quotas], ["custom_a", "custom_b"])
        self.assertNotIn("duration_seconds", quotas[0]["window"])
        self.assertNotIn("duration_seconds", quotas[1]["window"])

    def test_xdg_data_home_auth_resolution_and_no_cli(self):
        with tempfile.TemporaryDirectory() as td:
            xdg = Path(td) / "xdg"
            auth_dir = xdg / "opencode"
            auth_dir.mkdir(parents=True)
            (auth_dir / "auth.json").write_text(_auth_json("sk-xdg-secret"), encoding="utf-8")

            calls = []

            def fake_get(url, headers=None, timeout=15):
                calls.append((url, headers))
                return (_sample_usage(), 200, None)

            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(xdg)}):
                with mock.patch("collector.providers.opencode_go.get_json", side_effect=fake_get):
                    with mock.patch("subprocess.run", side_effect=AssertionError("must not call CLI")):
                        res = opencode_go.collect({"id": "opencode_go"}, None)

            self.assertTrue(res.get("ok"))
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], opencode_go.ENDPOINT_USAGE)
            self.assertEqual(calls[0][1]["Authorization"], "Bearer sk-xdg-secret")

    def test_missing_and_corrupt_auth_files(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing.json"
            res_missing = opencode_go.collect({"id": "opencode_go", "credentials_path": str(missing)}, None)
            self.assertFalse(res_missing.get("ok"))
            self.assertEqual(res_missing["error"]["code"], "missing_credential")

            no_entry = Path(td) / "other.json"
            no_entry.write_text(json.dumps({"anthropic": {"key": "k"}}), encoding="utf-8")
            res_no_entry = opencode_go.collect({"id": "opencode_go", "credentials_path": str(no_entry)}, None)
            self.assertFalse(res_no_entry.get("ok"))
            self.assertEqual(res_no_entry["error"]["code"], "missing_credential")

            corrupt = Path(td) / "bad.json"
            corrupt.write_text("{bad json", encoding="utf-8")
            res_corrupt = opencode_go.collect({"id": "opencode_go", "credentials_path": str(corrupt)}, None)
            self.assertFalse(res_corrupt.get("ok"))
            self.assertEqual(res_corrupt["error"]["code"], "invalid_response")

    def test_http_and_network_errors_are_safe_and_never_leak_key(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "auth.json"
            p.write_text(_auth_json("sk-opencode-super-secret"), encoding="utf-8")

            cases = [
                (urllib.error.HTTPError(opencode_go.ENDPOINT_USAGE, 401, "Unauthorized", {}, None), "auth_expired"),
                (urllib.error.HTTPError(opencode_go.ENDPOINT_USAGE, 403, "Forbidden", {}, None), "auth_expired"),
                (urllib.error.HTTPError(opencode_go.ENDPOINT_USAGE, 404, "Not Found", {}, None), "invalid_response"),
                (urllib.error.HTTPError(opencode_go.ENDPOINT_USAGE, 503, "Unavailable", {}, None), "provider_unavailable"),
                (urllib.error.URLError("dns error"), "network"),
                (TimeoutError("timed out"), "timeout"),
            ]
            for exc, expected_code in cases:
                with self.subTest(expected_code=expected_code):
                    with mock.patch("urllib.request.urlopen", side_effect=exc):
                        res = opencode_go.collect({"id": "opencode_go", "credentials_path": str(p)}, None)
                    self.assertFalse(res.get("ok"))
                    self.assertEqual(res["error"]["code"], expected_code)
                    self.assertNotIn("sk-opencode-super-secret", json.dumps(res))

    def test_empty_usage_returns_invalid_response(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "auth.json"
            p.write_text(_auth_json(), encoding="utf-8")
            with mock.patch("collector.providers.opencode_go.get_json", return_value=({"usage": {}}, 200, None)):
                res = opencode_go.collect({"id": "opencode_go", "credentials_path": str(p)}, None)
            self.assertFalse(res.get("ok"))
            self.assertEqual(res["error"]["code"], "invalid_response")
            self.assertEqual(res["error"]["message_key"], "unrecognized_usage_response")


if __name__ == "__main__":
    unittest.main()
