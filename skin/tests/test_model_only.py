"""Regressão em Lua 5.1 real para contas com cotas exclusivas de modelo/model_group.

Valida agregação independente de ordem em duas passagens no ProcessProvider,
exibição em linha compacta com marcador e tooltip de escopo, preservação na
gaveta, tratamento de expiração, null vs zero, e estado de erro/stale.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from skin.tests.runtime_qa import Harness, START, provider, quota, snapshot


class ModelOnlyQuotaTests(unittest.TestCase):
    def test_model_group_only_5h_week_visible(self):
        """Conta estilo Antigravity com apenas 2 quotas model_group (5h e week) fica visível."""
        q_5h = quota(
            "ag_5h",
            pct=25,
            scope_type="model_group",
            scope_id="grp_claude_gpt",
            scope_label="Claude / GPT-4o",
            wid="rolling_5h",
            label="5 horas",
            duration=18000,
        )
        q_week = quota(
            "ag_week",
            pct=40,
            scope_type="model_group",
            scope_id="grp_gemini",
            scope_label="Gemini Pro",
            wid="week",
            label="Semana",
            duration=604800,
        )
        h = Harness(snapshot([provider("antigravity", quotas=[q_5h, q_week])]))
        h.call("Initialize")

        self.assertTrue(h.visible("Row1Col1Text"))
        self.assertTrue(h.visible("Row1Col2Text"))
        self.assertFalse(h.visible("Row1Col3Text"))

        self.assertEqual(h.option("Row1Col1Text", "Text"), "25%•")
        self.assertEqual(h.option("Row1Col2Text", "Text"), "40%•")

        tip1 = h.option("Row1Col1Text", "ToolTipText") or ""
        tip2 = h.option("Row1Col2Text", "ToolTipText") or ""
        tip_hit = h.option("Row1Hitbox", "ToolTipText") or ""
        self.assertIn("grupo de modelos", tip1)
        self.assertIn("Claude / GPT-4o", tip1)
        self.assertIn("Gemini Pro", tip2)
        self.assertIn("Claude / GPT-4o", tip_hit)
        self.assertIn("Gemini Pro", tip_hit)

        h.call("OnRowClick", 1)
        self.assertEqual(h.option("DrawerWin1Val", "Text"), "25%")
        self.assertEqual(h.option("DrawerWin2Val", "Text"), "40%")
        self.assertIn("Claude / GPT-4o", h.option("DrawerWin1Reset", "Text") or "")
        self.assertIn("Gemini Pro", h.option("DrawerWin2Reset", "Text") or "")
        self.assertEqual(h.option("DrawerSlot1Name", "Text"), "Claude / GPT-4o")
        self.assertEqual(h.option("DrawerSlot2Name", "Text"), "Gemini Pro")

    def test_higher_model_before_and_after_account_is_order_independent(self):
        """Maior cota válida vence independentemente da ordem no array (antes ou depois de account)."""
        q_acc = quota("acc_5h", pct=30, scope_type="account", wid="rolling_5h", duration=18000)
        q_mod = quota(
            "mod_5h",
            pct=85,
            scope_type="model",
            scope_id="opus",
            scope_label="Claude Opus",
            wid="rolling_5h",
            duration=18000,
        )

        for label, order in (("model_before_account", [q_mod, q_acc]), ("account_before_model", [q_acc, q_mod])):
            with self.subTest(order=label):
                h = Harness(snapshot([provider("claude", quotas=order)]))
                h.call("Initialize")

                self.assertEqual(h.option("Row1Col1Text", "Text"), "85%•")
                tip = h.option("Row1Col1Text", "ToolTipText") or ""
                self.assertIn("Claude Opus", tip)

                h.call("OnRowClick", 1)
                self.assertEqual(h.option("DrawerWin1Val", "Text"), "85%")
                self.assertIn("Claude Opus", h.option("DrawerWin1Reset", "Text") or "")
                self.assertEqual(h.option("DrawerSlot1Name", "Text"), "Claude Opus")

    def test_expired_model_quota_is_ignored_when_valid_exists(self):
        """Cota de modelo expirada (95%) é ignorada quando existe cota válida não expirada (20%)."""
        past_iso = datetime.fromtimestamp(START - 600, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        q_acc = quota("acc_5h", pct=20, scope_type="account", wid="rolling_5h", duration=18000)
        q_mod_exp = quota(
            "mod_exp",
            pct=95,
            scope_type="model",
            scope_id="sonnet",
            scope_label="Sonnet Expirado",
            wid="rolling_5h",
            duration=18000,
        )
        q_mod_exp["window"]["reset_at"] = past_iso

        h = Harness(snapshot([provider("claude", quotas=[q_mod_exp, q_acc])]))
        h.call("Initialize")

        self.assertEqual(h.option("Row1Col1Text", "Text"), "20%")
        self.assertEqual(h.option("Row1Col1Text", "ToolTipText") or "", "")

        h.call("OnRowClick", 1)
        self.assertEqual(h.option("DrawerWin1Val", "Text"), "20%")
        self.assertEqual(h.option("DrawerSlot1Name", "Text"), "Sonnet Expirado")
        self.assertEqual(h.option("DrawerSlot1Val", "Text"), "…")

    def test_valid_model_quota_wins_over_expired_account_quota(self):
        """Se cota geral está expirada, cota válida de modelo assume a coluna com seu próprio reset."""
        past_iso = datetime.fromtimestamp(START - 300, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        q_acc_exp = quota(
            "acc_exp",
            pct=20,
            scope_type="account",
            wid="rolling_5h",
            duration=18000,
        )
        q_acc_exp["window"]["reset_at"] = past_iso
        q_mod = quota(
            "mod_ok",
            pct=45,
            scope_type="model_group",
            scope_id="flash",
            scope_label="Gemini Flash",
            wid="rolling_5h",
            duration=18000,
        )

        h = Harness(snapshot([provider("antigravity", quotas=[q_acc_exp, q_mod])]))
        h.call("Initialize")

        self.assertEqual(h.option("Row1Col1Text", "Text"), "45%•")
        h.call("OnRowClick", 1)
        reset_txt = h.option("DrawerWin1Reset", "Text") or ""
        self.assertNotIn("atualizando…", reset_txt)
        self.assertIn("Gemini Flash", reset_txt)

    def test_empty_account_and_null_vs_zero(self):
        """Conta sem cotas e cota null ficam ocultas; zero explícito exibe 0%•."""
        q_null = quota(
            "mod_null",
            pct=None,
            scope_type="model_group",
            scope_id="g1",
            scope_label="Grupo Null",
            wid="rolling_5h",
            duration=18000,
        )
        q_zero = quota(
            "mod_zero",
            pct=0,
            scope_type="model_group",
            scope_id="g2",
            scope_label="Grupo Zero",
            wid="week",
            duration=604800,
        )
        p_empty = provider("empty_prov", quotas=[])
        p_vals = provider("antigravity", quotas=[q_null, q_zero])

        h = Harness(snapshot([p_empty, p_vals]))
        h.call("Initialize")

        # Linha 1 (sem cotas): todas colunas ocultas
        self.assertFalse(h.visible("Row1Col1Text"))
        self.assertFalse(h.visible("Row1Col2Text"))
        self.assertFalse(h.visible("Row1Col3Text"))

        # Linha 2 (null em 5h, 0 explícito em week): 5h oculta, week mostra 0%•
        self.assertFalse(h.visible("Row2Col1Text"))
        self.assertTrue(h.visible("Row2Col2Text"))
        self.assertEqual(h.option("Row2Col2Text", "Text"), "0%•")
        self.assertIn("Grupo Zero", h.option("Row2Col2Text", "ToolTipText") or "")

    def test_windows_do_not_mix_5h_week_month(self):
        """Janelas 5h, week e month de modelos distintos não se misturam."""
        q_5h = quota("m5h", pct=15, scope_type="model_group", scope_label="G5H", wid="rolling_5h", duration=18000)
        q_wk = quota("mwk", pct=55, scope_type="model", scope_label="MWK", wid="week", duration=604800)
        q_mo = quota("mmo", pct=75, scope_type="model", scope_label="MMO", wid="month", duration=2592000)

        h = Harness(snapshot([provider("antigravity", quotas=[q_mo, q_wk, q_5h])]))
        h.call("Initialize")

        self.assertEqual(h.option("Row1Col1Text", "Text"), "15%•")
        self.assertEqual(h.option("Row1Col2Text", "Text"), "55%•")
        self.assertEqual(h.option("Row1Col3Text", "Text"), "75%•")

        h.call("OnRowClick", 1)
        self.assertIn("G5H", h.option("DrawerWin1Reset", "Text") or "")
        self.assertIn("MWK", h.option("DrawerWin2Reset", "Text") or "")
        self.assertIn("MMO", h.option("DrawerWin3Reset", "Text") or "")

    def test_error_with_cached_model_only_preserves_muted_quota(self):
        """Erro transitório com cache somente-modelo preserva exibição em cor esmaecida."""
        q_mod = quota(
            "ag_5h",
            pct=60,
            scope_type="model_group",
            scope_id="grp",
            scope_label="Grupo Cache",
            wid="rolling_5h",
            duration=18000,
        )
        p = provider("antigravity", quotas=[q_mod], error={"code": "network"})
        p["last_attempt_result"] = "error"

        h = Harness(snapshot([p]))
        h.call("Initialize")

        self.assertTrue(h.visible("Row1Col1Text"))
        self.assertEqual(h.option("Row1Col1Text", "Text"), "60%•")
        self.assertEqual(h.option("Row1Col1Text", "FontColor"), "255,255,255,150")


if __name__ == "__main__":
    unittest.main()
