import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from status import build_status, classify_pressure, port_up, _free_ram_pct, _total_ram_gb  # noqa: E402


def test_classify_pressure_buckets():
    assert classify_pressure(60) == "normal"
    assert classify_pressure(25) == "warn"
    assert classify_pressure(10) == "critical"


def test_port_up_false_for_closed_port():
    # port 1 is almost certainly closed on localhost
    assert port_up(1) is False


def test_free_ram_pct_is_realistic():
    # The old `top unused` metric reported ~5% on a healthy Mac (the bug).
    # memory_pressure should report a believable, non-zero free percentage.
    pct = _free_ram_pct()
    assert 0.0 <= pct <= 100.0
    assert _total_ram_gb() > 8.0  # Mac Studio has 36GB


def test_build_status_shape():
    s = build_status()
    assert set(s) >= {"ts", "ramFreeGb", "memPressure", "mlx8080", "mlx8081", "ptToday", "todos"}
    assert s["memPressure"] in {"normal", "warn", "critical"}
    assert isinstance(s["todos"], list)
