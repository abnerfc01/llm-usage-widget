from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .antigravity import collect as antigravity_collect
from .claude import collect as claude_collect
from .codex import collect as codex_collect
from .cursor import collect as cursor_collect
from .metered_generic import collect as metered_generic_collect
from .opencode_go import collect as opencode_go_collect

ProviderFn = Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]

_REGISTRY: Dict[str, ProviderFn] = {
    "claude": claude_collect,
    "codex": codex_collect,
    "antigravity": antigravity_collect,
    "opencode_go": opencode_go_collect,
    "cursor": cursor_collect,
    "metered_generic": metered_generic_collect,
}


def get_provider(name: str) -> Optional[ProviderFn]:
    return _REGISTRY.get(name)



