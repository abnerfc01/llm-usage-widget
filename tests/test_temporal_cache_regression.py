import copy
import tempfile
import unittest
from pathlib import Path

from collector.contract import atomic_write_json, default_provider_entry, read_snapshot, validate_snapshot


class TemporalCacheRegressionTests(unittest.TestCase):
    def setUp(self):
        self.provider = default_provider_entry({"id": "example"})
        self.snapshot = {"schema_version": "1.0", "generated_at": "2026-11-12T12:10:00+00:00", "providers": [self.provider]}

    def test_failure_retains_old_cache_across_atomic_publication(self):
        self.provider.update(last_attempt_result="error", last_attempt_at="2026-11-12T12:00:00+00:00", last_success_at="2026-11-10T09:00:00+00:00", error={"code": "network"}, data={"quotas": []}, freshness={"state": "stale", "stale_after": "2026-11-10T09:30:00+00:00"})
        expected = copy.deepcopy(self.snapshot)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            atomic_write_json(path, self.snapshot)
            self.assertEqual(read_snapshot(path), expected)
            self.assertEqual(self.snapshot, expected)

    def test_success_can_complete_after_attempt_before_generation(self):
        self.provider.update(last_attempt_result="success", last_attempt_at="2026-11-12T09:00:00-03:00", last_success_at="2026-11-12T12:05:00+00:00", data={"quotas": []})
        validate_snapshot(self.snapshot)

    def test_error_without_prior_success_and_never_are_valid(self):
        self.provider.update(last_attempt_result="error", last_attempt_at="2026-11-12T12:00:00+00:00", error={"code": "network"})
        validate_snapshot(self.snapshot)
        self.provider.update(last_attempt_result="never", last_attempt_at=None, error=None)
        validate_snapshot(self.snapshot)
        self.provider.update(enabled=False, state="disabled")
        validate_snapshot(self.snapshot)

    def test_disabled_preserves_previous_failure_and_cache(self):
        self.provider.update(enabled=False, state="disabled", last_attempt_result="error", last_attempt_at="2026-11-12T12:00:00+00:00", last_success_at="2026-11-10T09:00:00+00:00", data={"quotas": []})
        validate_snapshot(self.snapshot)

    def test_rejects_inconsistent_temporal_states(self):
        cases = [
            ("success before attempt", {"last_attempt_result": "success", "last_attempt_at": "2026-11-12T12:00:00+00:00", "last_success_at": "2026-11-12T11:00:00+00:00"}),
            ("error success after attempt", {"last_attempt_result": "error", "last_attempt_at": "2026-11-12T12:00:00+00:00", "last_success_at": "2026-11-12T12:05:00+00:00"}),
            ("attempt after publication", {"last_attempt_result": "error", "last_attempt_at": "2026-11-12T12:11:00+00:00"}),
            ("success after publication", {"last_attempt_result": "success", "last_attempt_at": "2026-11-12T12:00:00+00:00", "last_success_at": "2026-11-12T12:11:00+00:00"}),
            ("never with attempt", {"last_attempt_result": "never", "last_attempt_at": "2026-11-12T12:00:00+00:00"}),
            ("never with success", {"last_attempt_result": "never", "last_success_at": "2026-11-10T09:00:00+00:00"}),
            ("success without attempt", {"last_attempt_result": "success", "last_success_at": "2026-11-12T12:00:00+00:00"}),
            ("success without success time", {"last_attempt_result": "success", "last_attempt_at": "2026-11-12T12:00:00+00:00"}),
            ("error without attempt", {"last_attempt_result": "error"}),
            ("attempt without timezone", {"last_attempt_result": "error", "last_attempt_at": "2026-11-12T12:00:00"}),
            ("invalid success timestamp", {"last_attempt_result": "error", "last_attempt_at": "2026-11-12T12:00:00+00:00", "last_success_at": "invalid"}),
        ]
        for name, changes in cases:
            with self.subTest(name=name):
                snapshot = copy.deepcopy(self.snapshot)
                snapshot["providers"][0].update(changes)
                with self.assertRaises(ValueError):
                    validate_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
