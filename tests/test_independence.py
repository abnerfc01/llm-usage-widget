import os
import unittest
from pathlib import Path
from unittest import mock

from collector.providers import claude, codex, antigravity, opencode_go, cursor


class IndependenceTests(unittest.TestCase):
    def test_productive_plugins_do_not_call_orca_cli(self):
        cfg = {"id": "x", "plugin": "x", "display_name": "X", "collection_interval_seconds": 600}
        with mock.patch("collector.providers.orca_source.fetch_orca_rate_limits", side_effect=AssertionError("orca must not be called")):
            with mock.patch("subprocess.run", side_effect=AssertionError("subprocess.run must not be called by default productive plugins")):
                with mock.patch("subprocess.Popen", side_effect=AssertionError("subprocess.Popen must not be called")):
                    # Make file/wincred/network reads hermetic so no real profile, keyring, or network is touched (M4).
                    with mock.patch("collector.providers.claude_direct._resolve_credentials", return_value=(None, "missing_credential")):
                        with mock.patch("collector.providers.codex_direct._read_auth", return_value=(None, "missing_credential")):
                            with mock.patch("collector.providers.antigravity._read_wincred_blob", side_effect=AssertionError("wincred must not be accessed in independence test")):
                                with mock.patch("collector.providers.antigravity._resolve_credentials", return_value=(None, "missing_credential")):
                                    with mock.patch("collector.providers.cursor._has_cursor_auth_state", return_value=False):
                                        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network must not be called in independence test")):
                                            try:
                                                claude.collect({**cfg, "id": "claude"}, None)
                                            except AssertionError:
                                                raise
                                            except Exception:
                                                pass
                                            try:
                                                codex.collect({**cfg, "id": "codex"}, None)
                                            except AssertionError:
                                                raise
                                            except Exception:
                                                pass
                                            for mod in (antigravity, opencode_go, cursor):
                                                r = mod.collect({**cfg, "id": mod.__name__}, None)
                                                self.assertFalse(r.get("ok"))
                                                self.assertIn(r.get("error", {}).get("code"), {"unsupported", "missing_credential"})

    def test_orca_absent_path_does_not_break_default_collect(self):
        with mock.patch("shutil.which", return_value=None):
            with mock.patch("collector.providers.orca_source.fetch_orca_rate_limits", side_effect=AssertionError("orca must not be called")):
                with mock.patch("subprocess.run", side_effect=AssertionError("subprocess.run must not be called")):
                    with mock.patch("subprocess.Popen", side_effect=AssertionError("subprocess.Popen must not be called")):
                        with mock.patch("collector.providers.antigravity._read_wincred_blob", side_effect=AssertionError("wincred must not be accessed in independence test")):
                            with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network must not be called in independence test")):
                                with mock.patch("collector.providers.antigravity._resolve_credentials", return_value=(None, "missing_credential")):
                                    r_missing = antigravity.collect({"id": "antigravity"}, None)
                                    self.assertFalse(r_missing.get("ok"))
                                    self.assertEqual(r_missing.get("error", {}).get("code"), "missing_credential")

                                summary = {
                                    "groups": [
                                        {
                                            "displayName": "Pool",
                                            "buckets": [{"bucketId": "b5h", "window": "5h", "remainingFraction": 0.8}],
                                        }
                                    ]
                                }
                                with mock.patch("collector.providers.antigravity._resolve_credentials", return_value=({"access_token": "tok"}, None)):
                                    with mock.patch("collector.providers.antigravity._post_json", return_value=(summary, 200, None)):
                                        r_ok = antigravity.collect({"id": "antigravity"}, None)
                                        self.assertTrue(r_ok.get("ok"))
                                        self.assertEqual(len(r_ok["data"]["quotas"]), 1)


if __name__ == "__main__":
    unittest.main()
