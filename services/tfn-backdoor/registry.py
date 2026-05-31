"""Action registry: map action keys -> handler functions that return speech."""
from __future__ import annotations

import logging
from typing import Callable

REGISTRY: dict[str, Callable] = {}
log = logging.getLogger("tfn.registry")


def register(key: str):
    def deco(fn: Callable):
        REGISTRY[key] = fn
        return fn

    return deco


def dispatch(action: str, intent) -> str:
    """Run the handler for `action`; always return a speakable string."""
    fn = REGISTRY.get(action)
    if fn is None:
        log.warning("no handler for action=%s", action)
        return "I don't have a handler for that, sir."
    try:
        return fn(intent)
    except Exception as exc:  # noqa: BLE001 — handlers must never crash the loop
        log.exception("handler %s failed", action)
        return f"That action failed, sir. {type(exc).__name__}."
