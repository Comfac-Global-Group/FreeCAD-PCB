"""Tests for ERC 14×14 conflict matrix."""

import pytest
from pcb_electrical import Part, Pin, Net, pin_types, conflict_matrix, OK, ERROR, WARNING


def all_non_ok_cells():
    cells = []
    for pt1 in pin_types:
        for pt2 in pin_types:
            result, _ = conflict_matrix[pt1][pt2]
            if result != OK:
                cells.append((pt1, pt2, result))
    return cells


@pytest.fixture(autouse=True)
def clean_circuit():
    from pcb_electrical import default_circuit
    default_circuit.reset()
    yield
    default_circuit.reset()


@pytest.mark.parametrize("pt1,pt2,expected", all_non_ok_cells())
def test_erc_conflict_matrix_cell(pt1, pt2, expected, capsys):
    """Every non-OK matrix cell must produce ERC output."""
    p = Part(
        name="TEST",
        pins=[
            Pin(num=1, name="A", func=pt1),
            Pin(num=2, name="B", func=pt2),
        ],
    )
    n = Net("N1")
    n += p[1], p[2]
    n.ERC()
    captured = capsys.readouterr()
    out = captured.out
    assert out, f"Expected ERC output for {pt1.name} vs {pt2.name} but got none"
    if expected == ERROR:
        assert "Pin conflict" in out or "ERROR" in out or "Incorrectly connected" in out
    elif expected == WARNING:
        assert "Pin conflict" in out or "WARNING" in out or "Insufficient drive" in out
