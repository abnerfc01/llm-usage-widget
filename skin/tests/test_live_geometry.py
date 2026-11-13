"""Regressão de geometria dinâmica, reflow sem refresh e período de orçamento.

Executa Lua 5.1 real via Lupa utilizando o Harness isolado de runtime_qa,
verificando transições ao vivo de coordenadas, monitores negativos,
persistência de estado de interação (páginas e gaveta fixada) e formatação
correta de períodos de orçamento (ex: 'Novembro').
"""

from __future__ import annotations

import unittest
from skin.tests.runtime_qa import Harness, snapshot, provider, quota


class LiveGeometryTests(unittest.TestCase):
    def setUp(self):
        self.secondary = (1080, 40, 2560, 1040)
        self.providers_8 = [
            provider(f"prov_{i}", quotas=[quota(pct=10 * i)]) for i in range(1, 9)
        ]

    def test_move_to_150px_without_refresh(self):
        """Mover de posição segura para 150px úteis reconfigura para 3 linhas sem !Refresh."""
        h = Harness(
            snapshot(self.providers_8),
            secondary_workarea=self.secondary,
            config_x=1400,
            config_y=120,
        )
        h.call("Initialize")
        self.assertEqual(h.variables.get("SkinHeight"), "186")

        # Simula movimentação para Y=930 (150px disponíveis até Y=1080)
        h.variables["CURRENTCONFIGY"] = "930"
        h.call("Update")

        self.assertEqual(h.variables.get("SkinHeight"), "136")
        self.assertEqual(h.height(), 136)
        self.assertEqual(h.overflowing(150), [])
        self.assertTrue(h.visible("Row1Name"))
        self.assertTrue(h.visible("Row3Name"))
        self.assertFalse(h.visible("Row4Name"))
        self.assertFalse(h.visible("Row5Name"))

    def test_move_to_50px_without_refresh(self):
        """Mover de posição segura para 50px úteis colapsa corpo sem !Refresh."""
        h = Harness(
            snapshot(self.providers_8),
            secondary_workarea=self.secondary,
            config_x=1400,
            config_y=120,
        )
        h.call("Initialize")

        # Simula movimentação para Y=1030 (50px disponíveis até Y=1080)
        h.variables["CURRENTCONFIGY"] = "1030"
        h.call("Update")

        self.assertEqual(h.variables.get("SkinHeight"), "34")
        self.assertEqual(h.height(), 34)
        self.assertEqual(h.overflowing(50), [])
        self.assertEqual(h.option("MeterTitle", "Text"), "USO DE IA (recolhido)")
        for i in range(1, 6):
            self.assertFalse(h.visible(f"Row{i}Name"))

    def test_return_from_bottom_to_safe_position(self):
        """Retornar da borda inferior para posição aberta restaura as 5 linhas completas."""
        h = Harness(
            snapshot(self.providers_8),
            secondary_workarea=self.secondary,
            config_x=1400,
            config_y=1030,
        )
        h.call("Initialize")
        self.assertEqual(h.variables.get("SkinHeight"), "34")

        # Retorna para posição segura
        h.variables["CURRENTCONFIGY"] = "120"
        h.call("Update")

        self.assertEqual(h.variables.get("SkinHeight"), "186")
        self.assertEqual(h.height(), 186)
        self.assertEqual(h.overflowing(960), [])
        for i in range(1, 6):
            self.assertTrue(h.visible(f"Row{i}Name"))

    def test_negative_monitor_detection(self):
        """Detecta geometria em monitor secundário com coordenadas virtuais negativas."""
        h = Harness(snapshot(self.providers_8), config_x=100, config_y=120)
        h.call("Initialize")

        # Monitor 2 à esquerda do primário (X: -1920..0, Y: 0..1080)
        h.variables["WORKAREAX@2"] = "-1920"
        h.variables["WORKAREAY@2"] = "0"
        h.variables["WORKAREAWIDTH@2"] = "1920"
        h.variables["WORKAREAHEIGHT@2"] = "1080"

        # Posiciona no monitor 2 rente à base (150px livres)
        h.variables["CURRENTCONFIGX"] = "-1000"
        h.variables["CURRENTCONFIGY"] = "930"
        h.call("Update")

        self.assertEqual(h.variables.get("SkinHeight"), "136")
        self.assertEqual(h.overflowing(150), [])
        self.assertTrue(h.visible("Row3Name"))
        self.assertFalse(h.visible("Row4Name"))

    def test_page_consistency_on_move(self):
        """Página corrente 2 é preservada durante movimentações sem reset indevido."""
        h = Harness(
            snapshot(self.providers_8),
            secondary_workarea=self.secondary,
            config_x=1400,
            config_y=120,
        )
        h.call("Initialize")
        self.assertEqual(h.option("MeterPageText", "Text"), "1 / 2")

        # Navega para página 2 (prov_6 .. prov_8)
        h.call("NextPage")
        self.assertEqual(h.option("MeterPageText", "Text"), "2 / 2")
        self.assertEqual(h.option("Row1Name", "Text"), "prov_6")

        # Move para Y=930 (3 itens por página -> página 2 cobre prov_4 .. prov_6)
        h.variables["CURRENTCONFIGY"] = "930"
        h.call("Update")
        self.assertEqual(h.option("MeterPageText", "Text"), "2 / 3")
        self.assertEqual(h.option("Row1Name", "Text"), "prov_4")

        # Move para Y=1030 (corpo recolhido)
        h.variables["CURRENTCONFIGY"] = "1030"
        h.call("Update")

        # Retorna para posição segura (5 itens por página -> página 2 cobre prov_6..prov_8)
        h.variables["CURRENTCONFIGY"] = "120"
        h.call("Update")
        self.assertEqual(h.option("MeterPageText", "Text"), "2 / 2")
        self.assertEqual(h.option("Row1Name", "Text"), "prov_6")

    def test_pinned_drawer_consistency_on_move(self):
        """Gaveta fixada recolhe temporariamente em espaço restrito e reabre na volta."""
        h = Harness(
            snapshot(self.providers_8),
            secondary_workarea=self.secondary,
            config_x=1400,
            config_y=120,
        )
        h.call("Initialize")

        # Fixa gaveta na linha 1
        h.call("OnRowClick", 1)
        self.assertTrue(h.visible("DrawerTitle"))
        self.assertGreater(h.height(), 186)

        # Move para Y=930 (150px disponíveis: sem espaço para gaveta)
        h.variables["CURRENTCONFIGY"] = "930"
        h.call("Update")
        self.assertEqual(h.variables.get("SkinHeight"), "136")
        self.assertFalse(h.visible("DrawerTitle"))
        self.assertEqual(h.overflowing(150), [])

        # Retorna para Y=120: a gaveta deve reabrir automaticamente
        h.variables["CURRENTCONFIGY"] = "120"
        h.call("Update")
        self.assertTrue(h.visible("DrawerTitle"))
        self.assertGreater(h.height(), 186)

    def test_budget_period_label_novembro(self):
        """Verifica que o label de período 'Novembro' é exibido no tooltip e na gaveta."""
        money = {
            "currency": "USD",
            "spend": [{"amount": "12.40", "period": {"id": "2026-11", "label": "Novembro"}}],
            "budget": {
                "amount": "20.00",
                "currency": "USD",
                "period": {"id": "2026-11", "label": "Novembro"},
                "source": "local_config",
            },
        }
        p = provider("deepseek", money=money)
        h = Harness(snapshot([p]))
        h.call("Initialize")

        # Tooltips da linha compacta
        tooltip_col1 = h.option("Row1Col1Text", "ToolTipText") or ""
        tooltip_col3 = h.option("Row1Col3Text", "ToolTipText") or ""
        tooltip_hitbox = h.option("Row1Hitbox", "ToolTipText") or ""

        self.assertIn("Novembro", tooltip_col1)
        self.assertIn("Novembro", tooltip_col3)
        self.assertIn("Novembro", tooltip_hitbox)
        self.assertNotIn("mês", tooltip_col1)

        # Gaveta de detalhes
        h.call("OnRowClick", 1)
        drawer_reset = h.option("DrawerWin3Reset", "Text") or ""
        self.assertIn("Novembro", drawer_reset)
        self.assertNotIn("mês", drawer_reset)

    def test_stationary_update_emits_no_redraw(self):
        """Verifica que quando o widget permanece parado, Update() não dispara redraws desnecessários."""
        h = Harness(
            snapshot(self.providers_8),
            secondary_workarea=self.secondary,
            config_x=1400,
            config_y=120,
        )
        h.call("Initialize")

        # Limpa bangs anteriores
        h.bangs.clear()

        # Chama Update sem alterar posição
        h.call("Update")

        # Não deve haver !Redraw nem !UpdateMeter BackgroundBody
        redraw_bangs = [b for b in h.bangs if b[0] in ("!Redraw", "!UpdateMeter")]
        self.assertEqual(redraw_bangs, [])


if __name__ == "__main__":
    unittest.main()
