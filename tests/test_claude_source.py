import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from collector.providers.claude_direct import collect_direct, _resolve_credentials


def _cred_json(expired=False):
    exp = 1 if expired else 9999999999999
    return json.dumps({"claudeAiOauth": {"accessToken": "tok", "refreshToken": "rtok", "expiresAt": exp}})


class ClaudeSourceTests(unittest.TestCase):
    def test_explicit_credentials_path_used(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cred.json"
            p.write_text(_cred_json(expired=False), encoding="utf-8")
            oauth, err = _resolve_credentials({"credentials_path": str(p)})
            self.assertIsNone(err)
            self.assertEqual(oauth.get("accessToken"), "tok")
            with mock.patch("collector.providers.claude_direct.get_json", return_value=({"five_hour": {"utilization": 10, "resets_at": "2030-01-01T00:00:00Z"}}, 200, None)):
                res = collect_direct({"credentials_path": str(p)})
            self.assertTrue(res.get("ok"))
            self.assertEqual(len(res["data"]["quotas"]), 1)

    def test_fallback_to_orca_managed_profile_when_default_expired(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            (home / ".claude").mkdir(parents=True)
            (home / ".claude" / ".credentials.json").write_text(_cred_json(expired=True), encoding="utf-8")
            appdata = Path(td) / "appdata"
            managed = appdata / "orca" / "claude-profiles" / "p1" / "home"
            managed.mkdir(parents=True)
            (managed / ".credentials.json").write_text(_cred_json(expired=False), encoding="utf-8")
            with mock.patch.dict(os.environ, {"APPDATA": str(appdata)}):
                with mock.patch("collector.providers.claude_direct.Path.expanduser", return_value=str(home)):
                    oauth, err = _resolve_credentials({})
            self.assertIsNone(err)
            self.assertIsNotNone(oauth)

    def test_no_token_refresh_attempted(self):
        # collect_direct only does GET usage; absence of refresh logic is structural, ensure no network refresh URL
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cred.json"
            p.write_text(_cred_json(expired=False), encoding="utf-8")
            calls = []
            def fake_get(url, headers=None, timeout=15):
                calls.append(url)
                return ({"five_hour": {"utilization": 5}}, 200, None)
            with mock.patch("collector.providers.claude_direct.get_json", side_effect=fake_get):
                collect_direct({"credentials_path": str(p)})
            self.assertEqual(len(calls), 1)
            self.assertIn("/api/oauth/usage", calls[0])


if __name__ == "__main__":
    unittest.main()

