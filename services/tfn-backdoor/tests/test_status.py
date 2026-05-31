import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from status import classify_pressure, port_up  # noqa: E402


def test_classify_pressure_buckets():
    assert classify_pressure(60) == "normal"
    assert classify_pressure(25) == "warn"
    assert classify_pressure(10) == "critical"


def test_port_up_false_for_closed_port():
    # port 1 is almost certainly closed on localhost
    assert port_up(1) is False
