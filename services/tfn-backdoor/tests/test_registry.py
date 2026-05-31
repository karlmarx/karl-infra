import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from registry import REGISTRY, dispatch, register  # noqa: E402


def setup_function():
    REGISTRY.clear()


def test_register_and_dispatch_calls_handler():
    @register("ping")
    def _ping(intent):
        return "pong"

    assert dispatch("ping", intent=None) == "pong"


def test_dispatch_unknown_action_returns_friendly_error():
    msg = dispatch("nope", intent=None)
    assert "don" in msg.lower() or "unknown" in msg.lower()


def test_handler_exception_is_caught_and_phrased():
    @register("boom")
    def _boom(intent):
        raise RuntimeError("kaboom")

    msg = dispatch("boom", intent=None)
    assert "failed" in msg.lower()
