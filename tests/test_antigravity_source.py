import ctypes
import json
import math
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from collector.contract import normalize_provider_data
from collector.providers import antigravity


def _cred_payload(expired: bool = False, nested: bool = True) -> str:
    delta = timedelta(hours=-1) if expired else timedelta(hours=1)
    expiry = (datetime.now(timezone.utc) + delta).isoformat()
    tok = {
        "access_token": "ya29.test-token-do-not-leak",
        "refresh_token": "1//test-refresh-token",
        "token_type": "Bearer",
        "expiry": expiry,
    }
    if nested:
        return json.dumps({"auth_method": "consumer", "token": tok})
    return json.dumps(tok)


def _sample_summary() -> dict:
    return {
        "description": "Quota summary",
        "groups": [
            {
                "displayName": "Claude and GPT models",
                "description": "Models within this group",
                "buckets": [
                    {
                        "bucketId": "3p-weekly",
                        "displayName": "Weekly Limit Remaining",
                        "window": "weekly",
                        "resetTime": "2026-11-20T23:39:43Z",
                        "remainingFraction": 0.75,
                    },
                    {
                        "bucketId": "3p-5h",
                        "displayName": "Five Hour Limit Remaining",
                        "window": "5h",
                        "resetTime": "2026-11-14T04:39:43Z",
                        "remainingFraction": 0.6,
                    },
                ],
            }
        ],
    }


class AntigravitySourceTests(unittest.TestCase):
    def test_mapping_distinguishes_5h_and_weekly_windows_and_validates_contract(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cred.json"
            p.write_text(_cred_payload(expired=False), encoding="utf-8")

            with mock.patch("collector.providers.antigravity._post_json", return_value=(_sample_summary(), 200, None)):
                res = antigravity.collect({"id": "antigravity", "credentials_path": str(p)}, None)

            self.assertTrue(res.get("ok"))
            quotas = res["data"]["quotas"]
            self.assertEqual(len(quotas), 2)

            # 5h window sorted before weekly window
            q5h, qwk = quotas[0], quotas[1]
            self.assertEqual(q5h["window"]["id"], "rolling_5h")
            self.assertEqual(q5h["window"]["label"], "5 horas")
            self.assertEqual(q5h["window"]["duration_seconds"], 18000)
            self.assertAlmostEqual(q5h["used_percent"], 40.0)
            self.assertIn("reset_at", q5h["window"])

            self.assertEqual(qwk["window"]["id"], "week")
            self.assertEqual(qwk["window"]["label"], "Semana")
            self.assertEqual(qwk["window"]["duration_seconds"], 604800)
            self.assertAlmostEqual(qwk["used_percent"], 25.0)
            self.assertEqual(qwk["scope"]["type"], "model_group")
            self.assertEqual(qwk["scope"]["label"], "Claude and GPT models")

            normalized = normalize_provider_data(res["data"], {"id": "antigravity"})
            self.assertEqual(len(normalized["quotas"]), 2)

    def test_disabled_buckets_skipped_and_duplicate_ids_disambiguated(self):
        payload = {
            "groups": [
                {
                    "displayName": "Pool A",
                    "buckets": [
                        {"bucketId": "b1", "window": "5h", "remainingFraction": 1.0, "disabled": True},
                        {"bucketId": "b2", "window": "5h", "remainingFraction": 0.9},
                        {"bucketId": "b3", "window": "5h", "remainingFraction": 0.5},
                    ],
                }
            ]
        }
        mapped = antigravity._map_quota_summary(payload)
        ids = [q["id"] for q in mapped["quotas"]]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)

    def test_expired_token_returns_auth_expired_without_refresh_or_network(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cred.json"
            p.write_text(_cred_payload(expired=True), encoding="utf-8")

            with mock.patch("collector.providers.antigravity._post_json", side_effect=AssertionError("must not call network when expired")):
                res = antigravity.collect({"id": "antigravity", "credentials_path": str(p)}, None)

            self.assertFalse(res.get("ok"))
            self.assertEqual(res["error"]["code"], "auth_expired")

    def test_missing_and_corrupt_credentials(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "nope.json"
            res_missing = antigravity.collect({"id": "antigravity", "credentials_path": str(missing)}, None)
            self.assertFalse(res_missing.get("ok"))
            self.assertEqual(res_missing["error"]["code"], "missing_credential")

            corrupt = Path(td) / "bad.json"
            corrupt.write_text("{not json", encoding="utf-8")
            res_corrupt = antigravity.collect({"id": "antigravity", "credentials_path": str(corrupt)}, None)
            self.assertFalse(res_corrupt.get("ok"))
            self.assertEqual(res_corrupt["error"]["code"], "invalid_response")

    def test_wincred_resolution_and_no_oauth_refresh_url(self):
        blob = _cred_payload(expired=False, nested=True).encode("utf-8")
        calls = []

        def fake_post(url, body, headers, timeout=15):
            calls.append(url)
            return (_sample_summary(), 200, None)

        with mock.patch("collector.providers.antigravity._read_wincred_blob", return_value=blob):
            with mock.patch("collector.providers.antigravity._post_json", side_effect=fake_post):
                with mock.patch("subprocess.run", side_effect=AssertionError("must not invoke CLI")):
                    res = antigravity.collect({"id": "antigravity"}, None)

        self.assertTrue(res.get("ok"))
        self.assertEqual(calls, [antigravity.ENDPOINT_QUOTA_SUMMARY])

    def test_wincred_missing_returns_missing_credential(self):
        with mock.patch("collector.providers.antigravity._read_wincred_blob", return_value=None):
            res = antigravity.collect({"id": "antigravity"}, None)
        self.assertFalse(res.get("ok"))
        self.assertEqual(res["error"]["code"], "missing_credential")

    def test_project_fallback_via_load_code_assist(self):
        blob = _cred_payload(expired=False).encode("utf-8")
        calls = []

        def fake_post(url, body, headers, timeout=15):
            calls.append((url, body))
            if url == antigravity.ENDPOINT_QUOTA_SUMMARY and not body:
                return ({"groups": []}, 200, None)
            if url == antigravity.ENDPOINT_LOAD_CODE_ASSIST:
                return ({"cloudaicompanionProject": "proj-123"}, 200, None)
            if url == antigravity.ENDPOINT_QUOTA_SUMMARY and body == {"project": "proj-123"}:
                return (_sample_summary(), 200, None)
            raise AssertionError(f"unexpected call {url} {body}")

        with mock.patch("collector.providers.antigravity._read_wincred_blob", return_value=blob):
            with mock.patch("collector.providers.antigravity._post_json", side_effect=fake_post):
                res = antigravity.collect({"id": "antigravity"}, None)

        self.assertTrue(res.get("ok"))
        self.assertEqual(len(calls), 3)

    def test_http_and_network_failures_are_safe(self):
        blob = _cred_payload(expired=False).encode("utf-8")
        cases = [
            (urllib.error.HTTPError(antigravity.ENDPOINT_QUOTA_SUMMARY, 401, "Unauthorized", {}, None), "auth_expired"),
            (urllib.error.HTTPError(antigravity.ENDPOINT_QUOTA_SUMMARY, 404, "Not Found", {}, None), "invalid_response"),
            (urllib.error.HTTPError(antigravity.ENDPOINT_QUOTA_SUMMARY, 503, "Unavailable", {}, None), "provider_unavailable"),
            (urllib.error.URLError("dns fail"), "network"),
            (TimeoutError("timed out"), "timeout"),
        ]
        for exc, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with mock.patch("collector.providers.antigravity._read_wincred_blob", return_value=blob):
                    with mock.patch("urllib.request.urlopen", side_effect=exc):
                        res = antigravity.collect({"id": "antigravity"}, None)
                self.assertFalse(res.get("ok"))
                self.assertEqual(res["error"]["code"], expected_code)
                # Ensure no secret leaks into error payload
                self.assertNotIn("ya29.", json.dumps(res))

    def test_empty_groups_returns_invalid_response(self):
        blob = _cred_payload(expired=False).encode("utf-8")
        with mock.patch("collector.providers.antigravity._read_wincred_blob", return_value=blob):
            with mock.patch("collector.providers.antigravity._post_json", return_value=({"groups": []}, 200, None)):
                res = antigravity.collect({"id": "antigravity"}, None)
        self.assertFalse(res.get("ok"))
        self.assertEqual(res["error"]["code"], "invalid_response")
        self.assertEqual(res["error"]["message_key"], "unrecognized_usage_response")

    def test_window_classification_no_vague_inference_and_no_30d_month_guess(self):
        payload = {
            "groups": [
                {
                    "displayName": "Mixed",
                    "buckets": [
                        # Vague names without explicit window/duration must NOT be inferred as 5h/week/month
                        {"bucketId": "promo_5h_special", "displayName": "Five Hour Special", "remainingFraction": 0.9},
                        {"bucketId": "custom_alpha", "displayName": "Custom Alpha", "remainingFraction": 0.8},
                        # Monthly without explicit duration must NOT invent 30d duration_seconds
                        {"bucketId": "m1", "window": "monthly", "displayName": "Monthly Limit", "remainingFraction": 0.5},
                    ],
                }
            ]
        }
        mapped = antigravity._map_quota_summary(payload)
        quotas = mapped["quotas"]
        self.assertEqual(len(quotas), 3)

        by_id = {q["window"]["id"]: q for q in quotas}
        self.assertIn("month", by_id)
        self.assertNotIn("duration_seconds", by_id["month"]["window"])

        self.assertIn("promo_5h_special", by_id)
        self.assertNotIn("duration_seconds", by_id["promo_5h_special"]["window"])

        self.assertIn("custom_alpha", by_id)
        self.assertNotIn("duration_seconds", by_id["custom_alpha"]["window"])

    def test_out_of_range_and_non_finite_fractions_rejected_not_clamped(self):
        for bad_rem in (-0.1, 1.01, float("nan"), float("inf"), float("-inf"), True):
            with self.subTest(bad_rem=bad_rem):
                payload = {
                    "groups": [
                        {
                            "displayName": "Pool",
                            "buckets": [{"bucketId": "b1", "window": "5h", "remainingFraction": bad_rem}],
                        }
                    ]
                }
                mapped = antigravity._map_quota_summary(payload)
                self.assertEqual(mapped["quotas"], [])

        blob = _cred_payload(expired=False).encode("utf-8")
        bad_payload = {
            "groups": [
                {
                    "displayName": "Pool",
                    "buckets": [{"bucketId": "b1", "window": "5h", "remainingFraction": 1.5}],
                }
            ]
        }
        with mock.patch("collector.providers.antigravity._read_wincred_blob", return_value=blob):
            with mock.patch("collector.providers.antigravity._post_json", return_value=(bad_payload, 200, None)):
                res = antigravity.collect({"id": "antigravity"}, None)
        self.assertFalse(res.get("ok"))
        self.assertEqual(res["error"]["code"], "invalid_response")
        self.assertEqual(res["error"]["message_key"], "unrecognized_usage_response")

    @unittest.skipUnless(sys.platform == "win32", "Windows-specific CredReadW FFI test")
    def test_wincred_ffi_calls_credfree_on_success_and_skips_on_missing(self):
        raw_bytes = b'{"token":{"access_token":"tok"}}'
        buf = (ctypes.c_ubyte * len(raw_bytes))(*raw_bytes)
        cred_struct = antigravity._CREDENTIAL()
        cred_struct.CredentialBlobSize = len(raw_bytes)
        cred_struct.CredentialBlob = buf

        freed = []

        def fake_cred_read(target, ctype, flags, pcred_ptr):
            addr = ctypes.c_void_p(ctypes.addressof(cred_struct))
            ctypes.memmove(ctypes.addressof(pcred_ptr._obj), ctypes.byref(addr), ctypes.sizeof(ctypes.c_void_p))
            return 1

        def fake_cred_free(ptr):
            freed.append(ptr)

        fake_adv = mock.MagicMock()
        fake_adv.CredReadW = mock.MagicMock(side_effect=fake_cred_read)
        fake_adv.CredFree = mock.MagicMock(side_effect=fake_cred_free)

        with mock.patch("ctypes.WinDLL", return_value=fake_adv):
            out = antigravity._read_wincred_blob("gemini:antigravity")
        self.assertEqual(out, raw_bytes)
        self.assertEqual(len(freed), 1)

        freed.clear()
        fake_adv_missing = mock.MagicMock()
        fake_adv_missing.CredReadW = mock.MagicMock(return_value=0)
        fake_adv_missing.CredFree = mock.MagicMock(side_effect=fake_cred_free)
        with mock.patch("ctypes.WinDLL", return_value=fake_adv_missing):
            out_missing = antigravity._read_wincred_blob("gemini:antigravity")
        self.assertIsNone(out_missing)
        self.assertEqual(len(freed), 0)


if __name__ == "__main__":
    unittest.main()
