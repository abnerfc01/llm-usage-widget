import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

# Testes de unidade offline para a lógica da Skin Rainmeter (reprodução das regras Lua)

def parse_iso_time(iso_str):
    """Implementação correspondente à do script Lua para validação cruzada."""
    import re
    if not iso_str or not isinstance(iso_str, str):
        return None
    m = re.match(r"(\d+)-(\d+)-(\d+)T(\d+):(\d+):?(\d*)(.*)", iso_str)
    if not m:
        return None
    y, mon, d, h, mi, s, tz = m.groups()
    s = s or "0"
    
    dt_civil = datetime(int(y), int(mon), int(d), int(h), int(mi), int(s))
    base_epoch = int(dt_civil.replace(tzinfo=timezone.utc).timestamp())
    
    iso_tz_offset = 0
    if tz:
        tz = tz.strip()
        if tz in ("Z", "z", ""):
            iso_tz_offset = 0
        else:
            tz_m = re.match(r"([+-])(\d\d):?(\d\d)?", tz)
            if tz_m:
                sign, th, tm = tz_m.groups()
                sec = int(th) * 3600 + (int(tm or 0) * 60)
                iso_tz_offset = -sec if sign == "-" else sec

    target_epoch = base_epoch - iso_tz_offset
    return target_epoch

def classify_window(duration_seconds, window_id, window_label):
    """Implementação idêntica ao classificador Lua corrigido."""
    import re
    dur = int(duration_seconds) if duration_seconds is not None else None
    wid = (window_id or "").lower()
    wlbl = (window_label or "").lower()

    if dur is not None and dur > 0:
        if dur == 18000:
            return "5h"
        elif 600000 <= dur <= 610000:
            return "week"
        elif 2400000 <= dur <= 2700000:
            return "month"
        else:
            return "other"

    if wid in ("rolling_5h", "5h"):
        return "5h"
    elif wid in ("week", "weekly"):
        return "week"
    elif wid in ("month", "monthly"):
        return "month"

    m_h = re.search(r"\b(\d+)\s*h(?:oras?)?\b", wlbl)
    if m_h:
        if int(m_h.group(1)) == 5:
            return "5h"
        else:
            return "other"

    if re.search(r"\bsemana\b", wlbl):
        return "week"
    if re.search(r"\bm[eê]s\b", wlbl):
        return "month"

    return "other"

def periods_match(b_period, s_period):
    """Verifica compatibilidade estrita de períodos: ausência ou dados incompletos rejeitam."""
    if not b_period or not isinstance(b_period, dict) or not s_period or not isinstance(s_period, dict):
        return False

    b_id = b_period.get("id")
    s_id = s_period.get("id")
    has_id = bool(b_id and s_id and str(b_id).strip() and str(s_id).strip())

    b_start = parse_iso_time(b_period.get("starts_at"))
    s_start = parse_iso_time(s_period.get("starts_at"))
    b_end = parse_iso_time(b_period.get("ends_at"))
    s_end = parse_iso_time(s_period.get("ends_at"))

    # Se ambos têm ID mas divergem -> rejeita
    if has_id and b_id != s_id:
        return False

    # Se ambos têm starts_at mas divergem -> rejeita
    if b_start is not None and s_start is not None and b_start != s_start:
        return False

    # Se ambos têm ends_at mas divergem -> rejeita
    if b_end is not None and s_end is not None and b_end != s_end:
        return False

    # Confirmação positiva: IDs válidos coincidentes
    if has_id and b_id == s_id:
        return True

    # Ou ambos starts_at e ends_at coincidem e não são nulos
    if b_start is not None and s_start is not None and b_start == s_start and b_end is not None and s_end is not None and b_end == s_end:
        return True

    return False

def match_budget(money_obj):
    """Correspondência estrita de orçamento: rejeita desconhecido/incompatível."""
    if not money_obj or "budget" not in money_obj:
        return None
    b = money_obj["budget"]
    b_amt = float(b.get("amount", 0))
    if b_amt <= 0:
        return None
    b_curr = (b.get("currency") or money_obj.get("currency") or "").upper()
    if not b_curr:
        return None
    b_period = b.get("period")
    b_scope = b.get("scope", {})

    spends = money_obj.get("spend", [])
    for s in spends:
        s_amt = float(s.get("amount", 0))
        s_curr = (s.get("currency") or money_obj.get("currency") or "").upper()
        s_period = s.get("period")
        s_scope = s.get("scope", {})

        if s_curr != b_curr:
            continue

        b_sc_type = b_scope.get("type", "account")
        b_sc_id = b_scope.get("id", "account")
        s_sc_type = s_scope.get("type", "account")
        s_sc_id = s_scope.get("id", "account")

        if (b_sc_type != s_sc_type) or (b_sc_id != s_sc_id):
            continue

        if periods_match(b_period, s_period):
            pct = int((s_amt / b_amt) * 100)
            return {"spend": s_amt, "budget": b_amt, "pct": pct, "currency": b_curr}

    return None

def calculate_effective_geometry(work_area_h, work_area_y, skin_y):
    """
    Calcula capacidade vertical e visibilidade de cada elemento por geometria efetiva.
    Sem estourar a tela e sem freeHeight negativo.
    """
    screen_bottom = (work_area_y or 0) + (work_area_h or 1080)
    skin_pos_y = skin_y or 0
    available_h = max(0, screen_bottom - skin_pos_y)

    if available_h < 34:
        # Espaço zero ou insuficiente até para o cabeçalho
        return {
            "items_per_page": 0,
            "compact_h": 34,
            "drawer_allowed": False,
            "visible_slots": 0,
            "skin_h": 34,
            "collapsed": True
        }
    elif available_h < 92:
        # Cabeçalho cabe, mas nenhuma linha compacta cabe com rodapé
        return {
            "items_per_page": 0,
            "compact_h": 34,
            "drawer_allowed": False,
            "visible_slots": 0,
            "skin_h": 34,
            "collapsed": True
        }
    elif available_h < 116:
        items = 1
        compact_h = 92
    elif available_h < 140:
        items = 2
        compact_h = 116
    elif available_h < 164:
        items = 3
        compact_h = 140
    elif available_h < 186:
        items = 4
        compact_h = 164
    else:
        items = 5
        compact_h = 186

    free_for_drawer = available_h - compact_h - 6
    if free_for_drawer < 70:
        return {
            "items_per_page": items,
            "compact_h": compact_h,
            "drawer_allowed": False,
            "visible_slots": 0,
            "skin_h": compact_h,
            "collapsed": False
        }

    # Gaveta permitida: calcula capacidade de slots roláveis
    # Base da gaveta com janelas principais requer ~130px
    remaining_for_slots = free_for_drawer - 130
    visible_slots = 0
    if remaining_for_slots >= 36:
        visible_slots = min(4, remaining_for_slots // 36)

    actual_drawer_h = min(free_for_drawer, 130 + (visible_slots * 36) + 16)
    return {
        "items_per_page": items,
        "compact_h": compact_h,
        "drawer_allowed": True,
        "visible_slots": visible_slots,
        "skin_h": compact_h + actual_drawer_h,
        "collapsed": False
    }


class TestSkinLogic(unittest.TestCase):
    def test_classify_5h_strict(self):
        self.assertEqual(classify_window(18000, "foo", "bar"), "5h")
        self.assertEqual(classify_window(10800, "foo", "5h"), "other")
        self.assertEqual(classify_window(None, None, "5h"), "5h")
        self.assertEqual(classify_window(None, None, "5 horas"), "5h")
        self.assertEqual(classify_window(None, None, "15h"), "other")
        self.assertEqual(classify_window(None, None, "25h"), "other")
        self.assertEqual(classify_window(None, None, "50h"), "other")
        self.assertEqual(classify_window(None, None, "15 horas"), "other")

    def test_parse_iso_time_offsets(self):
        t1 = parse_iso_time("2026-11-12T09:00:00Z")
        t2 = parse_iso_time("2026-11-12T06:00:00-03:00")
        t5 = parse_iso_time("2026-11-12T11:00:00+02:00")
        self.assertEqual(t1, t2)
        self.assertEqual(t1, t5)

    def test_match_budget_strict_periods(self):
        # 1. Ambos com ID coincidente -> válido
        money_valid_id = {
            "currency": "USD",
            "spend": [{"amount": "10.00", "period": {"id": "2026-11"}}],
            "budget": {"amount": "20.00", "currency": "USD", "period": {"id": "2026-11"}}
        }
        res = match_budget(money_valid_id)
        self.assertIsNotNone(res)
        self.assertEqual(res["pct"], 50)

        # 2. Ausência de período no spend ou budget -> REJEITA (ausência não prova compatibilidade)
        money_no_s_period = {
            "currency": "USD",
            "spend": [{"amount": "10.00"}],
            "budget": {"amount": "20.00", "currency": "USD", "period": {"id": "2026-11"}}
        }
        self.assertIsNone(match_budget(money_no_s_period))

        money_no_b_period = {
            "currency": "USD",
            "spend": [{"amount": "10.00", "period": {"id": "2026-11"}}],
            "budget": {"amount": "20.00", "currency": "USD"}
        }
        self.assertIsNone(match_budget(money_no_b_period))

        # 3. IDs divergentes -> REJEITA
        money_diff_id = {
            "currency": "USD",
            "spend": [{"amount": "10.00", "period": {"id": "2026-11-12"}}],
            "budget": {"amount": "20.00", "currency": "USD", "period": {"id": "2026-11"}}
        }
        self.assertIsNone(match_budget(money_diff_id))

        # 4. Sem ID, mas starts_at e ends_at coincidem exatamente -> VÁLIDO
        money_bounds_match = {
            "currency": "USD",
            "spend": [{"amount": "5.00", "period": {"starts_at": "2026-11-01T00:00:00Z", "ends_at": "2026-11-30T23:59:59Z"}}],
            "budget": {"amount": "20.00", "currency": "USD", "period": {"starts_at": "2026-11-01T00:00:00Z", "ends_at": "2026-11-30T23:59:59Z"}}
        }
        res_bounds = match_budget(money_bounds_match)
        self.assertIsNotNone(res_bounds)
        self.assertEqual(res_bounds["pct"], 25)

        # 5. Sem ID e bounds divergem -> REJEITA
        money_bounds_diverge = {
            "currency": "USD",
            "spend": [{"amount": "5.00", "period": {"starts_at": "2026-11-01T00:00:00Z", "ends_at": "2026-11-15T23:59:59Z"}}],
            "budget": {"amount": "20.00", "currency": "USD", "period": {"starts_at": "2026-11-01T00:00:00Z", "ends_at": "2026-11-30T23:59:59Z"}}
        }
        self.assertIsNone(match_budget(money_bounds_diverge))

        # 6. ID coincide mas datas de término divergem -> REJEITA (conflito explícito)
        money_id_ok_dates_bad = {
            "currency": "USD",
            "spend": [{"amount": "5.00", "period": {"id": "2026-11", "ends_at": "2026-11-15T00:00:00Z"}}],
            "budget": {"amount": "20.00", "currency": "USD", "period": {"id": "2026-11", "ends_at": "2026-11-30T00:00:00Z"}}
        }
        self.assertIsNone(match_budget(money_id_ok_dates_bad))

    def test_effective_geometry_zero_and_tight_space(self):
        # 1. Zero espaço (skin fora da tela ou Y >= WorkAreaH)
        g_zero = calculate_effective_geometry(1080, 0, 1080)
        self.assertTrue(g_zero["collapsed"])
        self.assertFalse(g_zero["drawer_allowed"])
        self.assertEqual(g_zero["items_per_page"], 0)
        self.assertEqual(g_zero["skin_h"], 34)

        # 2. Espaço ínfimo (50 px disponível)
        g_50 = calculate_effective_geometry(1080, 0, 1030)
        self.assertTrue(g_50["collapsed"])
        self.assertFalse(g_50["drawer_allowed"])
        self.assertEqual(g_50["skin_h"], 34)

        # 3. Espaço para 1 linha (100 px disponível)
        g_100 = calculate_effective_geometry(1080, 0, 980)
        self.assertFalse(g_100["collapsed"])
        self.assertEqual(g_100["items_per_page"], 1)
        self.assertEqual(g_100["compact_h"], 92)
        self.assertFalse(g_100["drawer_allowed"])
        self.assertTrue(g_100["skin_h"] <= 100)

        # 4. Espaço para 3 linhas sem gaveta (150 px disponível)
        g_150 = calculate_effective_geometry(1080, 0, 930)
        self.assertEqual(g_150["items_per_page"], 3)
        self.assertEqual(g_150["compact_h"], 140)
        self.assertFalse(g_150["drawer_allowed"])
        self.assertTrue(g_150["skin_h"] <= 150)

        # 5. Espaço padrão com gaveta completa (1080p, Y=0)
        g_full = calculate_effective_geometry(1080, 0, 0)
        self.assertEqual(g_full["items_per_page"], 5)
        self.assertEqual(g_full["compact_h"], 186)
        self.assertTrue(g_full["drawer_allowed"])
        self.assertEqual(g_full["visible_slots"], 4)
        self.assertTrue(g_full["skin_h"] <= 1080)

if __name__ == "__main__":
    unittest.main()
