import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from collector.contract import (
    SCHEMA_VERSION,
    atomic_write_json,
    freshness_state,
    normalize_provider_data,
    now_utc,
    origin_signature,
    parse_iso_strict,
    read_snapshot,
    safe_error,
    validate_snapshot,
)


def _provider_skeleton(**overrides):
    base = {
        "id": "p",
        "display_name": "P",
        "kind": "quota",
        "enabled": True,
        "visible": True,
        "collection_interval_seconds": 600,
        "last_attempt_at": None,
        "last_attempt_result": "never",
        "last_success_at": None,
        "freshness": {"state": "never", "stale_after": None},
        "error": None,
        "data": None,
        "origin_signature": origin_signature({"id": "p", "plugin": "p"}),
    }
    base.update(overrides)
    return base


class ContractTests(unittest.TestCase):
    def test_freshness_never_and_fresh_stale(self):
        self.assertEqual(freshness_state(None, 600)["state"], "never")
        now = datetime(2026, 11, 11, 14, 0, tzinfo=timezone.utc)
        last = datetime(2026, 11, 11, 13, 40, tzinfo=timezone.utc)
        f = freshness_state(last, 600, now)
        self.assertEqual(f["state"], "fresh")
        now2 = datetime(2026, 11, 11, 14, 11, tzinfo=timezone.utc)
        f2 = freshness_state(last, 600, now2)
        self.assertEqual(f2["state"], "stale")

    def test_safe_error_closed_vocabulary(self):
        self.assertEqual(safe_error("totally_unknown")["code"], "provider_unavailable")
        self.assertEqual(safe_error("timeout")["code"], "timeout")
        e = safe_error("timeout", "arbitrary.user.controlled.text")
        self.assertIn(e.get("message_key"), {None, "timeout", "provider_unavailable"})
        self.assertNotEqual(e.get("message_key"), "arbitrary.user.controlled.text")
        e2 = safe_error("auth_expired", "auth_expired")
        self.assertEqual(e2.get("message_key"), "auth_expired")

    def test_parse_iso_strict_requires_timezone(self):
        self.assertIsNotNone(parse_iso_strict("2026-11-11T14:00:00-03:00"))
        self.assertIsNone(parse_iso_strict("2026-11-11T14:00:00"))

    def test_normalize_provider_data_allowlist(self):
        data = {
            "quotas": [
                {
                    "id": "q",
                    "scope": {"type": "account", "id": "account", "label": "Conta"},
                    "window": {"id": "week", "label": "Semana"},
                    "used_percent": 12.5,
                }
            ],
            "raw_token": "FAKE_TEST_SECRET_DO_NOT_USE",
        }
        with self.assertRaises(ValueError) as ctx:
            normalize_provider_data(data, {})
        self.assertIn("raw_token", str(ctx.exception))

    def test_normalize_provider_data_rejects_invalid_types(self):
        data = {
            "quotas": [
                {
                    "id": "q",
                    "scope": {"type": "account", "id": "account", "label": "Conta"},
                    "window": {"id": "week", "label": "Semana"},
                    "used_percent": True,
                }
            ]
        }
        with self.assertRaises(ValueError):
            normalize_provider_data(data, {})

    def test_normalize_provider_data_money_validation(self):
        data = {
            "money": {
                "currency": "US$",
                "spend": [{"period": {"id": "p", "label": "P"}, "amount": "12.40"}],
            }
        }
        with self.assertRaises(ValueError):
            normalize_provider_data(data, {})

    def test_origin_signature_stable_no_secrets(self):
        s1 = origin_signature({"plugin": "claude", "credential_ref": "a", "credentials_path": "/x", "secret": "nope"})
        s2 = origin_signature({"plugin": "claude", "credential_ref": "a", "credentials_path": "/x"})
        self.assertEqual(s1, s2)
        s3 = origin_signature({"plugin": "claude", "credential_ref": "b", "credentials_path": "/x"})
        self.assertNotEqual(s1, s3)

    def test_atomic_write_and_validate(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "snapshot.json"
            snap = {
                "schema_version": SCHEMA_VERSION,
                "generated_at": "2026-11-11T14:00:00-03:00",
                "providers": [
                    _provider_skeleton(
                        id="p1",
                        display_name="P1",
                        last_attempt_at="2026-11-11T14:00:00-03:00",
                        last_attempt_result="success",
                        last_success_at="2026-11-11T14:00:00-03:00",
                        freshness={"state": "fresh", "stale_after": "2026-11-11T14:30:00-03:00"},
                        data={"quotas": [{"id": "q", "scope": {"type": "account", "id": "account", "label": "Conta"}, "window": {"id": "week", "label": "Semana"}, "used_percent": 12.5}]},
                    )
                ],
            }
            atomic_write_json(path, snap)
            loaded = read_snapshot(path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["schema_version"], "1.0")

    def test_validate_rejects_bad_money_amount_type(self):
        snap = {
            "schema_version": "1.0",
            "generated_at": "2026-11-11T14:00:00-03:00",
            "providers": [_provider_skeleton(
                id="m", display_name="M", kind="metered",
                data={"money": {"currency": "USD", "spend": [{"period": {"id": "p", "label": "P"}, "amount": 12.4}]}}
            )]
        }
        with self.assertRaises(ValueError):
            validate_snapshot(snap)

    def test_validate_rejects_duplicate_ids(self):
        snap = {
            "schema_version": "1.0",
            "generated_at": "2026-11-11T14:00:00-03:00",
            "providers": [
                _provider_skeleton(id="p"),
                _provider_skeleton(id="p"),
            ],
        }
        with self.assertRaises(ValueError) as ctx:
            validate_snapshot(snap)
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_validate_rejects_generated_at_without_timezone(self):
        snap = {
            "schema_version": "1.0",
            "generated_at": "2026-11-11T14:00:00",
            "providers": [_provider_skeleton()],
        }
        with self.assertRaises(ValueError):
            validate_snapshot(snap)

    def test_atomic_write_failure_on_replace_preserves_previous(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "snapshot.json"
            snap = {
                "schema_version": "1.0", "generated_at": "2026-11-11T14:00:00-03:00",
                "providers": [_provider_skeleton()]
            }
            atomic_write_json(path, snap)
            before = path.read_text(encoding="utf-8")
            snap2 = dict(snap)
            snap2["generated_at"] = "2026-11-11T15:00:00-03:00"
            with mock.patch("collector.contract.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    atomic_write_json(path, snap2)
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
