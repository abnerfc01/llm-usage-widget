"""Offline Lua 5.1 runtime QA for the staging skin.

Run with Lupa installed only in a TEMP target on PYTHONPATH. The tests use
collector.contract.atomic_write_json with synthetic data, but never invoke
providers, Rainmeter, real snapshots, credentials, or network access.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from collector.contract import atomic_write_json, origin_signature

MAIN = ROOT / "skin/@Resources/Scripts/main.lua"
JSON_LUA = ROOT / "skin/@Resources/Scripts/json.lua"
INI = ROOT / "skin/LLMUsage.ini"
STYLES_INC = ROOT / "skin/@Resources/Styles.inc"
START = int(datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc).timestamp())
FAKE_LOCAL = "Q:\\QA_LOCAL"
FAKE_RESOURCES = "Q:\\QA_RES\\"
FAKE_CUSTOM_SNAPSHOT = "Q:\\QA_ISOLATED\\snapshot.json"


def read_source(path):
    """Read source for the Lua stub, including Rainmeter's UTF-16 LE files."""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if len(raw) > 1 and raw[1] == 0:
        return raw.decode("utf-16-le")
    return raw.decode("utf-8-sig")


def parse_sections(path):
    sections = {}
    section = None
    for raw in read_source(path).splitlines():
        line = raw.strip()
        m = re.match(r"^\[([^]]+)\]$", line)
        if m:
            section = m.group(1)
            sections[section] = {}
        elif section and "=" in line and not line.startswith(";"):
            key, value = line.split("=", 1)
            sections[section][key.strip()] = value.strip()
    return sections


def parse_meters():
    return {name: opts for name, opts in parse_sections(INI).items() if "Meter" in opts}


METERS = parse_meters()
STYLES = parse_sections(STYLES_INC)


def provider(pid="demo", *, quotas=None, money=None, freshness="fresh", error=None):
    data = {"quotas": quotas or []}
    if money is not None:
        data["money"] = money
    return {
        "id": pid,
        "display_name": pid,
        "kind": "metered" if money else "quota",
        "enabled": True,
        "visible": True,
        "collection_interval_seconds": 600,
        "last_attempt_at": "2026-11-12T09:00:00Z",
        "last_attempt_result": "success",
        "last_success_at": "2026-11-12T09:00:00Z",
        "freshness": {"state": freshness, "stale_after": "2026-11-12T09:30:00Z"},
        "error": error,
        "data": data,
    }


def quota(qid="q", *, pct=35, scope_type="account", scope_id="account",
          scope_label="Conta", wid="rolling_5h", label="5 horas",
          duration=18000, reset="2026-11-12T09:05:00Z"):
    window = {"id": wid, "label": label}
    if duration is not None:
        window["duration_seconds"] = duration
    if reset is not None:
        window["reset_at"] = reset
    return {
        "id": qid,
        "scope": {"type": scope_type, "id": scope_id, "label": scope_label},
        "window": window,
        "used_percent": pct,
    }


def snapshot(providers, version="1.0"):
    # Compact helper for focused Lua behavior tests. The collector-to-parser
    # bridge below deliberately uses atomic_write_json's formatted bytes.
    return json.dumps({
        "schema_version": version,
        "generated_at": "2026-11-12T09:00:00Z",
        "providers": providers,
    }, ensure_ascii=False)


class Harness:
    def __init__(self, text=None, *, fixture=None, use_fixture=False, available=1000,
                 secondary_workarea=None, monitors=None, config_x=0, config_y=None,
                 custom_snapshot_text=None, explicit_snapshot_path=False):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.now = START
        self.snapshot_text = text
        self.custom_snapshot_text = custom_snapshot_text
        self.fixture_text = fixture
        self.opened = []
        self.bangs = []
        self.unknown = []
        self.meters = {
            name: {"visible": opts.get("Hidden") != "1", "opts": dict(opts),
                   "groups": {part.strip() for part in opts.get("Group", "").split("|") if part.strip()}}
            for name, opts in METERS.items()
        }
        self.variables = {
            "@": FAKE_RESOURCES,
            "UseSyntheticFixture": "1" if use_fixture else "0",
            "WORKAREAHEIGHT": "1000",
            "WORKAREAY": "0",
            "CURRENTCONFIGX": str(config_x),
            "CURRENTCONFIGY": str(1000 - available if config_y is None else config_y),
            "SkinHeight": "186",
        }
        if explicit_snapshot_path:
            self.variables["SnapshotPath"] = FAKE_CUSTOM_SNAPSHOT
        self.secondary_workarea = secondary_workarea
        self.monitors = dict(monitors) if monitors else {}
        if secondary_workarea is not None:
            self.monitors.setdefault(1, (62, 0, 1018, 1920))
            self.monitors.setdefault(2, secondary_workarea)
            # Rainmeter without AutoSelectScreen exposes the primary work area
            # through unqualified WORKAREA* even when this skin is on screen 2.
            self.variables.update({
                "WORKAREAHEIGHT": "1920", "WORKAREAY": "0",
                "WORKAREAX": "62", "WORKAREAWIDTH": "1018",
                "WORKAREAHEIGHT@2": str(secondary_workarea[3]),
                "WORKAREAY@2": str(secondary_workarea[1]),
                "WORKAREAX@2": str(secondary_workarea[0]),
                "WORKAREAWIDTH@2": str(secondary_workarea[2]),
            })
        if self.monitors:
            for m_idx, rect in self.monitors.items():
                self.variables.update({
                    f"WORKAREAX@{m_idx}": str(rect[0]),
                    f"WORKAREAY@{m_idx}": str(rect[1]),
                    f"WORKAREAWIDTH@{m_idx}": str(rect[2]),
                    f"WORKAREAHEIGHT@{m_idx}": str(rect[3]),
                })
        if parse_sections(INI).get("Rainmeter", {}).get("AutoSelectScreen") == "1":
            self.select_current_screen()
        skin = self.lua.table()
        skin.GetVariable = lambda _self, key: self.variables.get(str(key))
        skin.Bang = self.bang
        self.lua.globals().SKIN = skin
        original_time = self.lua.eval("os.time")
        self.lua.globals().os.time = lambda arg=None: original_time(arg) if arg is not None else self.now
        self.lua.globals().os.getenv = lambda key: FAKE_LOCAL if key == "LOCALAPPDATA" else None
        self.lua.globals().io.open = self.open_file
        self.lua.globals().dofile = self.load_json_module
        self.lua.execute(read_source(MAIN))

    def select_current_screen(self):
        if not self.monitors and self.secondary_workarea is None:
            return
        x = int(self.variables["CURRENTCONFIGX"])
        y = int(self.variables.get("CURRENTCONFIGY", "0"))
        matched = None
        if self.monitors:
            for rect in self.monitors.values():
                left, top, width, height = rect
                if left <= x < left + width and top <= y < top + height:
                    matched = rect
                    break
                elif left <= x < left + width:
                    matched = rect
        if matched is None and self.secondary_workarea is not None:
            left, top, width, height = self.secondary_workarea
            if left <= x < left + width:
                matched = self.secondary_workarea
            else:
                matched = (62, 0, 1018, 1920)
        if matched is not None:
            left, top, width, height = matched
            self.variables.update({"WORKAREAX": str(left), "WORKAREAY": str(top),
                                   "WORKAREAWIDTH": str(width), "WORKAREAHEIGHT": str(height)})

    def move_to(self, config_x=None, config_y=None):
        if config_x is not None:
            self.variables["CURRENTCONFIGX"] = str(config_x)
        if config_y is not None:
            self.variables["CURRENTCONFIGY"] = str(config_y)
        if parse_sections(INI).get("Rainmeter", {}).get("AutoSelectScreen") == "1":
            self.select_current_screen()

    def load_json_module(self, path):
        if str(path) != FAKE_RESOURCES + "Scripts\\json.lua":
            raise AssertionError("unexpected dofile: " + str(path))
        return self.lua.execute(read_source(JSON_LUA))

    def open_file(self, path, mode="r"):
        path = str(path)
        self.opened.append(path)
        if path == FAKE_LOCAL + "\\LLMUsageWidget\\snapshot.json":
            content = self.snapshot_text
        elif path == FAKE_CUSTOM_SNAPSHOT:
            content = self.custom_snapshot_text
        elif path == FAKE_RESOURCES + "Fixtures\\snapshot-synthetic.json":
            content = self.fixture_text
        elif path.startswith(FAKE_RESOURCES + "Icons\\"):
            content = None
        else:
            raise AssertionError("unexpected io.open: " + path)
        if content is None:
            return None
        file_table = self.lua.table()
        file_table.read = lambda *_args: content
        file_table.close = lambda *_args: None
        return file_table

    def bang(self, _self, action, *args):
        action = str(action)
        args = tuple(str(x) for x in args)
        self.bangs.append((action, *args))
        if action in ("!ShowMeter", "!HideMeter"):
            name = args[0]
            if name not in self.meters:
                self.unknown.append((action, name))
            else:
                self.meters[name]["visible"] = action == "!ShowMeter"
        elif action in ("!ShowMeterGroup", "!HideMeterGroup"):
            group = args[0]
            matched = False
            for meter in self.meters.values():
                if group in meter["groups"]:
                    matched = True
                    meter["visible"] = action == "!ShowMeterGroup"
            if not matched:
                self.unknown.append((action, group))
        elif action == "!SetOption":
            name, key, value = args
            if name not in self.meters:
                self.unknown.append((action, name))
            else:
                self.meters[name]["opts"][key] = value
        elif action == "!SetVariable":
            self.variables[args[0]] = args[1]
        elif action == "!AutoSelectScreen" and args and args[0] == "1":
            self.select_current_screen()

    def call(self, func, *args):
        return getattr(self.lua.globals(), func)(*args)

    def update(self, ticks):
        for _ in range(ticks):
            self.call("Update")

    def option(self, meter, key="Text"):
        return self.meters[meter]["opts"].get(key)

    def visible(self, meter):
        return self.meters[meter]["visible"]

    def height(self):
        return int(float(self.variables["SkinHeight"]))

    def overflowing(self, available):
        overflow = []
        for name, meter in self.meters.items():
            if not meter["visible"]:
                continue
            opts = meter["opts"]
            y = opts.get("Y", "0")
            h = opts.get("H", "14" if opts.get("Meter") == "String" else "1")
            try:
                bottom = float(y) + float(h)
            except ValueError:
                continue
            if bottom > available:
                overflow.append((name, bottom))
        return overflow


class RuntimeSkinQA(unittest.TestCase):
    def test_explicit_snapshot_path_reads_only_isolated_file(self):
        h = Harness(snapshot([provider("default")]), explicit_snapshot_path=True,
                    custom_snapshot_text=snapshot([provider("isolated")]))
        h.call("Initialize")
        self.assertEqual(h.option("Row1Name"), "isolated")
        self.assertNotIn(FAKE_LOCAL + "\\LLMUsageWidget\\snapshot.json", h.opened)

    def test_missing_explicit_snapshot_path_does_not_fall_back_to_user_cache(self):
        h = Harness(snapshot([provider("default")]), explicit_snapshot_path=True,
                    custom_snapshot_text=None)
        h.call("Initialize")
        self.assertTrue(h.visible("MeterEmptyNotice"))
        self.assertNotIn(FAKE_LOCAL + "\\LLMUsageWidget\\snapshot.json", h.opened)

    def test_collector_atomic_writer_bytes_parse_without_compaction(self):
        p = provider("bridge", quotas=[quota(pct=12)])
        p["display_name"] = "Bridge QA"
        p["origin_signature"] = origin_signature({"id": "bridge", "plugin": "synthetic"})
        never = provider("never")
        never.update({
            "origin_signature": origin_signature({"id": "never", "plugin": "synthetic"}),
            "last_attempt_at": None, "last_attempt_result": "never",
            "last_success_at": None, "freshness": {"state": "never", "stale_after": None},
            "data": None,
        })
        envelope = {"schema_version": "1.0", "generated_at": "2026-11-12T09:00:00Z",
                    "providers": [p, never]}
        with tempfile.TemporaryDirectory(prefix="llm-skin-bridge-") as td:
            path = Path(td) / "snapshot.json"
            atomic_write_json(path, envelope)
            emitted = path.read_bytes()
            self.assertIn(b'"stale_after": null\n', emitted)
            self.assertIn(b'"data": null,', emitted)
            for label, raw in (("LF", emitted), ("CRLF", emitted.replace(b"\n", b"\r\n"))):
                with self.subTest(newline=label):
                    h = Harness(raw.decode("utf-8"))
                    h.call("Initialize")
                    self.assertFalse(h.visible("MeterEmptyNotice"), label)
                    self.assertEqual(h.option("Row1Name"), "Bridge QA")
                    self.assertEqual(h.option("Row1Col1Text"), "12%")

    def assert_json_lua_whitespace(self, literals):
        lua = LuaRuntime(unpack_returned_tuples=True)
        decoder = lua.execute(read_source(JSON_LUA))
        for literal in literals:
            for label, whitespace in (("LF", "\n"), ("CRLF", "\r\n"),
                                      ("tab", "\t"), ("space", " ")):
                with self.subTest(literal=literal, whitespace=label):
                    parsed = decoder.decode('{"value":' + literal + whitespace + '}')
                    self.assertIsNotNone(parsed)

    def test_json_lua_accepts_whitespace_after_null(self):
        self.assert_json_lua_whitespace(("null",))

    def test_json_lua_accepts_whitespace_after_booleans(self):
        self.assert_json_lua_whitespace(("true", "false"))

    def test_json_lua_accepts_whitespace_after_numbers(self):
        self.assert_json_lua_whitespace(("123", "1.25"))

    def test_secondary_monitor_workarea_at_bottom_positions(self):
        # Real Rainmeter without AutoSelectScreen supplies primary WORKAREA*
        # (1920/0) to a skin on the 1040-high secondary (top=40).
        secondary = (1080, 40, 2560, 1040)
        for y, available in ((930, 150), (1030, 50)):
            with self.subTest(y=y, available=available):
                h = Harness(snapshot([provider(quotas=[quota()])]),
                            secondary_workarea=secondary, config_x=1400, config_y=y)
                h.call("Initialize")
                self.assertLessEqual(h.height(), available, "compact viewport")
                self.assertEqual(h.overflowing(available), [], "compact meters")
                h.call("OnRowClick", 1)
                self.assertLessEqual(h.height(), available, "drawer viewport")
                self.assertEqual(h.overflowing(available), [], "drawer meters")

    def test_rainmeter_source_with_unicode_uses_utf16le(self):
        # Rainmeter's official Unicode guidance for .ini/.inc/.lua source.
        for path in (INI, ROOT / "skin/@Resources/Variables.inc",
                     STYLES_INC, MAIN, JSON_LUA):
            with self.subTest(path=path.name):
                raw = path.read_bytes()
                if any(ord(c) > 127 for c in read_source(path)):
                    utf16le = raw.startswith(b"\xff\xfe") or (len(raw) > 1 and raw[1] == 0)
                    self.assertTrue(utf16le, f"Unicode source is not UTF-16 LE: {path}")

    def test_compact_money_text_does_not_enter_provider_name_box(self):
        money = {
            "currency": "USD",
            "spend": [{"amount": "12.40", "period": {"id": "2026-11"}}],
            "budget": {"amount": "20.00", "currency": "USD",
                       "period": {"id": "2026-11"}, "source": "local_config"},
        }
        h = Harness(snapshot([provider("deepseek", money=money)]))
        h.call("Initialize")
        name = h.meters["Row1Name"]["opts"]
        name_left = float(name["X"])
        name_right = name_left + float(name["W"])
        name_top = float(name["Y"])
        name_bottom = name_top + float(name["H"])
        money_meters = []
        for meter_name, meter in h.meters.items():
            if not meter["visible"] or meter["opts"].get("Meter") != "String":
                continue
            text = meter["opts"].get("Text", "")
            if "US$" not in text:
                continue
            opts = dict(STYLES.get(meter["opts"].get("MeterStyle", ""), {}))
            opts.update(meter["opts"])
            money_meters.append((meter_name, text, opts))
        self.assertTrue(money_meters, "monetary amount has no visible meter")
        for meter_name, text, opts in money_meters:
            with self.subTest(meter=meter_name):
                top = float(opts["Y"])
                bottom = top + float(opts.get("H", 14))
                if top >= name_bottom or bottom <= name_top:
                    continue  # a dedicated second line is safe from name overlap
                x = float(opts["X"])
                align = opts.get("StringAlign", "Left")
                clipped = opts.get("ClipString") == "1" and opts.get("W")
                # A conservative four pixels per character is only a static
                # guard. Native glyph width still needs visual validation.
                width = float(opts["W"]) if clipped else len(text) * 4
                left = x - width if align == "Right" else x - width / 2 if align == "Center" else x
                right = left + width
                self.assertTrue(right <= name_left or left >= name_right,
                                (meter_name, text, (left, right), (name_left, name_right)))

    def test_no_snapshot_requires_explicit_demo_flag(self):
        h = Harness(None, fixture=snapshot([provider()]))
        h.call("Initialize")
        self.assertFalse(h.visible("MeterDemoBanner"))
        self.assertTrue(h.visible("MeterEmptyNotice"))
        self.assertEqual(h.option("MeterFooterSnapshot"), "Instantâneo: sem dados")
        h.variables["UseSyntheticFixture"] = "1"
        h.call("RefreshSnapshot")
        self.assertTrue(h.visible("MeterDemoBanner"))
        self.assertFalse(h.visible("MeterEmptyNotice"))

    def test_iso_offsets_equivalent_in_real_lua(self):
        values = []
        for reset in ("2026-11-12T09:05:00Z", "2026-11-12T06:05:00-03:00",
                      "2026-11-12T11:05:00+02:00"):
            h = Harness(snapshot([provider(quotas=[quota(reset=reset)])]))
            h.call("Initialize")
            h.call("OnRowClick", 1)
            values.append(h.option("DrawerWin1Reset"))
        self.assertEqual(values, ["reinicia em 5min"] * 3)

    def test_polling_refresh_and_hover_click_scroll(self):
        models = [quota(f"m{i}", pct=i * 10, scope_type="model", scope_id=f"m{i}",
                        scope_label=f"Modelo {i}", wid="week", label="Semana", duration=604800)
                  for i in range(6)]
        h = Harness(snapshot([provider(quotas=[quota(pct=10), *models])]))
        h.call("Initialize")
        h.call("OnRowMouseEnter", 1)
        h.update(8)
        self.assertTrue(h.visible("DrawerTitle"))
        self.assertEqual(h.option("DrawerSlot1Name"), "Modelo 0")
        h.call("OnScrollDown")
        self.assertEqual(h.option("DrawerSlot1Name"), "Modelo 1")
        h.call("OnRowClick", 1)
        h.call("OnSkinMouseLeave")
        h.update(9)
        self.assertTrue(h.visible("DrawerTitle"))
        h.snapshot_text = snapshot([provider(quotas=[quota(pct=20), *models])])
        h.update(200)
        self.assertEqual(h.option("Row1Col1Text"), "20%")
        h.call("OnRowClick", 1)
        self.assertFalse(h.visible("DrawerTitle"))

    def test_freshness_advances_without_new_publication(self):
        h = Harness(snapshot([provider(quotas=[quota()])]))
        h.call("Initialize")
        h.now = START + 31 * 60
        h.update(20)
        self.assertIn("alerta", h.option("MeterFooterAlert", "Text") or "")

    def test_bad_version_types_and_null_keep_last_valid(self):
        good = snapshot([provider(quotas=[quota(pct=35)])])
        bads = [
            snapshot([provider(quotas=[quota(pct=99)])], version="2.0"),
            "{broken-json",
            json.dumps({"schema_version": "1.0", "generated_at": "x", "providers": "wrong"}),
            json.dumps({"schema_version": "1.0", "generated_at": "x", "providers": None}),
            json.dumps({"schema_version": "1.0", "generated_at": "x", "providers": [None]}),
        ]
        for bad in bads:
            with self.subTest(bad=bad[:70]):
                h = Harness(good)
                h.call("Initialize")
                h.snapshot_text = bad
                h.call("RefreshSnapshot")
                self.assertEqual(h.option("Row1Col1Text"), "35%")
                self.assertIn("Leitura falhou", h.option("MeterFooterAlert") or "")

    def test_malformed_quota_type_does_not_crash_refresh(self):
        h = Harness(snapshot([provider(quotas=[quota(pct=35)])]))
        h.call("Initialize")
        bad = provider()
        bad["data"]["quotas"] = "wrong"
        h.snapshot_text = snapshot([bad])
        h.call("RefreshSnapshot")
        self.assertEqual(h.option("Row1Col1Text"), "35%")

    def test_null_percent_is_not_rendered_as_zero(self):
        q = quota()
        q["used_percent"] = None
        h = Harness(snapshot([provider(quotas=[q])]))
        h.call("Initialize")
        self.assertNotEqual(h.option("Row1Col1Text"), "0%")

    def test_bad_v1_version_is_rejected(self):
        for version in ("1.not-a-version", 1.0):
            with self.subTest(version=version):
                h = Harness(snapshot([provider(quotas=[quota()])], version=version))
                h.call("Initialize")
                self.assertTrue(h.visible("MeterEmptyNotice"))

    def test_missing_snapshot_after_valid_preserves_last_valid(self):
        h = Harness(snapshot([provider(quotas=[quota(pct=35)])]))
        h.call("Initialize")
        h.snapshot_text = None
        h.call("RefreshSnapshot")
        self.assertTrue(h.visible("Row1Col1Text"))
        self.assertEqual(h.option("Row1Col1Text"), "35%")
        self.assertIn("Leitura falhou", h.option("MeterFooterAlert") or "")

    def test_budget_without_matching_period_has_no_percent(self):
        money = {
            "currency": "USD",
            "spend": [{"amount": "12.40", "period": {"id": "2026-11"}}],
            "budget": {"amount": "20.00", "currency": "USD", "period": {}, "source": "local_config"},
        }
        h = Harness(snapshot([provider(money=money)]))
        h.call("Initialize")
        self.assertNotEqual(h.option("Row1Col3Text"), "62%")

    def test_budget_matching_period_shows_percent(self):
        money = {
            "currency": "USD",
            "spend": [{"amount": "12.40", "period": {"id": "2026-11"}}],
            "budget": {"amount": "20.00", "currency": "USD",
                       "period": {"id": "2026-11"}, "source": "local_config"},
        }
        h = Harness(snapshot([provider(money=money)]))
        h.call("Initialize")
        self.assertEqual(h.option("Row1Col3Text"), "62%")

    def test_budget_same_id_different_end_rejected(self):
        money = {
            "currency": "USD",
            "spend": [{"amount": "12.40", "period": {"id": "2026-11",
                       "starts_at": "2026-11-01T00:00:00Z", "ends_at": "2026-12-01T00:00:00Z"}}],
            "budget": {"amount": "20.00", "currency": "USD",
                       "period": {"id": "2026-11", "starts_at": "2026-11-01T00:00:00Z",
                                  "ends_at": "2026-12-02T00:00:00Z"}, "source": "local_config"},
        }
        h = Harness(snapshot([provider(money=money)]))
        h.call("Initialize")
        self.assertNotEqual(h.option("Row1Col3Text"), "62%")

    def test_old_budget_percent_is_cleared_when_period_stops_matching(self):
        money = {
            "currency": "USD",
            "spend": [{"amount": "12.40", "period": {"id": "2026-11"}}],
            "budget": {"amount": "20.00", "currency": "USD",
                       "period": {"id": "2026-11"}, "source": "local_config"},
        }
        h = Harness(snapshot([provider(money=money)]))
        h.call("Initialize")
        self.assertEqual(h.option("Row1Col3Text"), "62%")
        money["budget"]["period"] = {}
        h.snapshot_text = snapshot([provider(money=money)])
        h.call("RefreshSnapshot")
        self.assertFalse(h.visible("Row1Col3Text"))

    def test_metered_without_budget_has_compact_money_value(self):
        money = {"currency": "USD", "balance": "4.20", "spend": []}
        h = Harness(snapshot([provider(money=money)]))
        h.call("Initialize")
        texts = [h.option(f"Row1Col{i}Text") or "" for i in (1, 2, 3)]
        self.assertTrue(any("4.20" in value for value in texts), texts)

    def test_error_with_cached_data_preserves_visible_quota(self):
        p = provider(quotas=[quota(pct=35)], error={"code": "network"})
        p["last_attempt_result"] = "error"
        h = Harness(snapshot([p]))
        h.call("Initialize")
        self.assertEqual(h.option("Row1Col1Text"), "35%")
        self.assertTrue(h.visible("Row1Col1Text"))

    def test_stale_quota_has_stale_visual_state(self):
        h = Harness(snapshot([provider(quotas=[quota(pct=35)], freshness="stale")]))
        h.call("Initialize")
        self.assertEqual(h.option("Row1Col1Text", "FontColor"), "255,255,255,150")

    def test_bar_change_uses_intermediate_animation_frames(self):
        h = Harness(snapshot([provider(quotas=[quota(pct=10)])]))
        h.call("Initialize")
        old_width = int(h.option("Row1Col1Bar", "W"))
        h.snapshot_text = snapshot([provider(quotas=[quota(pct=90)])])
        h.bangs.clear()
        h.update(205)
        widths = [int(b[3]) for b in h.bangs if len(b) >= 4 and b[:3] ==
                  ("!SetOption", "Row1Col1Bar", "W")]
        new_width = int(h.option("Row1Col1Bar", "W"))
        self.assertTrue(any(old_width < width < new_width for width in widths),
                        (old_width, new_width, widths))

    def test_small_viewports_contain_every_visible_meter(self):
        for available in (0, 50, 150, 300, 450, 600):
            with self.subTest(available=available):
                h = Harness(snapshot([provider(quotas=[quota()])]), available=available)
                h.call("Initialize")
                h.call("OnRowClick", 1)
                self.assertLessEqual(h.height(), available)
                self.assertEqual(h.overflowing(available), [])

    def test_15h_does_not_enter_5h_column(self):
        h = Harness(snapshot([provider(quotas=[quota(wid="custom_15h", label="15h", duration=None)])]))
        h.call("Initialize")
        self.assertNotEqual(h.option("Row1Col1Text"), "35%")
        h.call("OnRowClick", 1)
        self.assertEqual(h.option("DrawerSlot1Name"), "15h")

    def test_model_reset_expires_individually(self):
        h = Harness(snapshot([provider(quotas=[
            quota(reset="2026-11-12T09:01:00Z"),
            quota("model", pct=70, scope_type="model", scope_id="m", scope_label="Modelo",
                  wid="week", label="Semana", duration=604800,
                  reset="2026-11-12T09:01:00Z"),
        ])]))
        h.call("Initialize")
        h.call("OnRowClick", 1)
        h.now = START + 120
        h.update(20)
        self.assertEqual(h.option("DrawerWin1Val"), "…")
        self.assertEqual(h.option("DrawerSlot1Val"), "…")

    def test_every_bang_meter_target_exists_in_ini(self):
        h = Harness(snapshot([provider(quotas=[quota()])]))
        h.call("Initialize")
        h.call("OnRowClick", 1)
        self.assertEqual(h.unknown, [])

    def test_icon_id_cannot_escape_icon_directory(self):
        h = Harness(snapshot([provider("..\\..\\QA_ESCAPE", quotas=[quota()])]))
        h.call("Initialize")
        attempted = [p for p in h.opened if "QA_ESCAPE" in p]
        self.assertEqual(attempted, [])

    def test_ini_includes_callbacks_and_json_license(self):
        ini = read_source(INI)
        code = read_source(MAIN)
        parser = read_source(JSON_LUA)
        self.assertIn("@includeVariables=#@#Variables.inc", ini)
        self.assertIn("@includeStyles=#@#Styles.inc", ini)
        self.assertTrue((ROOT / "skin/@Resources/Variables.inc").is_file())
        self.assertTrue((ROOT / "skin/@Resources/Styles.inc").is_file())
        self.assertIn("Permission is hereby granted, free of charge", parser)
        for name in re.findall(r'!CommandMeasure MeasureLua "([A-Za-z_]+)\(', ini):
            self.assertRegex(code, rf"function\s+{re.escape(name)}\s*\(")

    def test_move_without_refresh_updates_geometry_and_safe_return(self):
        # Secondary monitor: left=1080, top=40, width=2560, height=1040 (bottom=1080).
        # Tests that changing CURRENTCONFIGX/Y after Initialize() and calling Update()
        # without RefreshSnapshot() dynamically adjusts geometry for 150px and 50px
        # available viewports, and safely restores full compact layout on safe return.
        secondary = (1080, 40, 2560, 1040)
        h = Harness(snapshot([provider(quotas=[quota()])]),
                    secondary_workarea=secondary, config_x=1400, config_y=120)
        h.call("Initialize")
        self.assertEqual(h.height(), 186, "initial height at safe position")

        # 1. Move to Y=930 (150px remaining: 1080 - 930 = 150px) without refresh
        h.move_to(config_y=930)
        h.call("Update")
        self.assertLessEqual(h.height(), 150, "compact height contained in 150px on move without refresh")
        self.assertEqual(h.overflowing(150), [], "no compact meters overflow 150px on move without refresh")

        # 2. Move to Y=1030 (50px remaining: 1080 - 1030 = 50px) without refresh
        h.move_to(config_y=1030)
        h.call("Update")
        self.assertLessEqual(h.height(), 50, "compact height contained in 50px on move without refresh")
        self.assertEqual(h.overflowing(50), [], "no compact meters overflow 50px on move without refresh")

        # 3. Safe return: move back to safe position (Y=120, 960px remaining) without refresh
        h.move_to(config_y=120)
        h.call("Update")
        self.assertEqual(h.height(), 186, "full compact height restored on safe return")
        self.assertEqual(h.overflowing(960), [], "no meters overflow safe return area")
        self.assertTrue(h.visible("Row1Col1Text"), "row 1 visible on safe return")

    def test_negative_monitor_coordinates_geometry(self):
        # Multi-monitor setup with secondary monitor to the left (negative X).
        # Monitor 1 (primary): 62, 0, 1018, 1920
        # Monitor 2 (left): -1920, 0, 1920, 1080 (bottom = 1080)
        monitors = {
            1: (62, 0, 1018, 1920),
            2: (-1920, 0, 1920, 1080),
        }
        h = Harness(snapshot([provider(quotas=[quota()])]),
                    monitors=monitors, config_x=-1400, config_y=120)
        h.call("Initialize")
        self.assertEqual(h.height(), 186, "initial height on negative monitor")

        # Move to 150px remaining (Y=930) without refresh
        h.move_to(config_y=930)
        h.call("Update")
        self.assertLessEqual(h.height(), 150, "negative monitor 150px viewport")
        self.assertEqual(h.overflowing(150), [], "negative monitor 150px meters")

        # Move to 50px remaining (Y=1030) without refresh
        h.move_to(config_y=1030)
        h.call("Update")
        self.assertLessEqual(h.height(), 50, "negative monitor 50px viewport")
        self.assertEqual(h.overflowing(50), [], "negative monitor 50px meters")

        # Safe return on negative monitor
        h.move_to(config_y=120)
        h.call("Update")
        self.assertEqual(h.height(), 186, "negative monitor safe return height")
        self.assertEqual(h.overflowing(960), [], "negative monitor safe return meters")

    def test_budget_matching_period_shows_specific_month_label(self):
        # When budget period specifies November (e.g. 2026-11 with label 'Novembro'),
        # tooltips and drawer detail must present 'Novembro' rather than generic 'mês'.
        money = {
            "currency": "USD",
            "spend": [{"amount": "12.40", "period": {"id": "2026-11", "label": "Novembro"}}],
            "budget": {"amount": "20.00", "currency": "USD",
                       "period": {"id": "2026-11", "label": "Novembro"}, "source": "local_config"},
        }
        h = Harness(snapshot([provider("deepseek", money=money)]))
        h.call("Initialize")

        # Compact row tooltip
        col1_tooltip = h.option("Row1Col1Text", "ToolTipText") or ""
        self.assertIn("Novembro", col1_tooltip, "compact col1 tooltip must mention Novembro")
        self.assertNotIn("(mês)", col1_tooltip, "compact col1 tooltip must not show generic '(mês)'")

        # Drawer budget detail
        h.call("OnRowClick", 1)
        drawer_detail = h.option("DrawerWin3Reset", "Text") or ""
        self.assertIn("Novembro", drawer_detail, "drawer budget detail must mention Novembro")
        self.assertNotIn("(mês)", drawer_detail, "drawer budget detail must not show generic '(mês)'")

    def test_budget_specific_month_derived_from_period_id(self):
        # Even without explicit 'label', period id 'YYYY-MM' (e.g. '2026-03')
        # must resolve to the Portuguese month name ('Março'), not generic 'mês'.
        money = {
            "currency": "USD",
            "spend": [{"amount": "5.00", "period": {"id": "2026-03"}}],
            "budget": {"amount": "10.00", "currency": "USD",
                       "period": {"id": "2026-03"}, "source": "local_config"},
        }
        h = Harness(snapshot([provider("api_mar", money=money)]))
        h.call("Initialize")

        col1_tooltip = h.option("Row1Col1Text", "ToolTipText") or ""
        self.assertIn("Março", col1_tooltip, "tooltip must resolve period 2026-03 to Março")
        self.assertNotIn("(mês)", col1_tooltip, "tooltip must not fall back to generic '(mês)'")

        h.call("OnRowClick", 1)
        drawer_detail = h.option("DrawerWin3Reset", "Text") or ""
        self.assertIn("Março", drawer_detail, "drawer detail must resolve period 2026-03 to Março")
        self.assertNotIn("(mês)", drawer_detail, "drawer detail must not fall back to generic '(mês)'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
