"""Repro mínimo do parser da skin; não acessa contas nem rede."""

from pathlib import Path

from lupa.lua51 import LuaRuntime


root = Path(__file__).resolve().parents[2]
lua = LuaRuntime(unpack_returned_tuples=True)
lua.globals().parser_path = str(root / "skin/@Resources/Scripts/json.lua")
decoder = lua.execute("return dofile(parser_path)")

for label, source in (
    ("compacto", '{"x":null}'),
    ("formatado", '{"x":null\n}'),
):
    try:
        decoder.decode(source)
        print(f"{label}: aceito")
    except Exception as exc:
        print(f"{label}: rejeitado ({type(exc).__name__})")
