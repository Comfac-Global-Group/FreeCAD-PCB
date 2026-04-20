"""Tests for net/pin connection operators."""

import pytest
from pcb_electrical import Part, Pin, Net, Bus, Circuit, default_circuit


@pytest.fixture(autouse=True)
def clean_circuit():
    default_circuit.reset()
    yield
    default_circuit.reset()


def test_net_iadd_pins():
    p = Part(name="P1", pins=[Pin(num=1, name="A"), Pin(num=2, name="B")])
    n = Net("N1")
    n += p[1], p[2]
    assert len(n.pins) == 2


def test_pin_iadd_net():
    p = Part(name="P2", pins=[Pin(num=1, name="A")])
    n = Net("N2")
    p[1] += n
    assert p[1].net is n


def test_pin_iadd_pin_creates_net():
    p = Part(name="P3", pins=[Pin(num=1, name="A"), Pin(num=2, name="B")])
    p[1] += p[2]
    assert p[1].net is not None
    assert p[1].net is p[2].net


def test_net_and_pin():
    p = Part(name="P4", pins=[Pin(num=1, name="A")])
    n = Net("N4")
    result = n & p[1]
    assert p[1].net is n
    assert result is n


def test_net_or_pin():
    p = Part(name="P5", pins=[Pin(num=1, name="A")])
    n = Net("N5")
    result = n | p[1]
    assert p[1].net is n
    assert result is n


def test_pin_and_pin():
    p = Part(name="P6", pins=[Pin(num=1, name="A"), Pin(num=2, name="B")])
    result = p[1] & p[2]
    assert p[1].net is p[2].net
    assert result is p[1]


def test_part_mul():
    p = Part(name="P7", pins=[Pin(num=1, name="A")])
    copies = p * 3
    assert len(copies) == 3
    assert all(isinstance(c, Part) for c in copies)


def test_net_mul():
    n = Net("N7")
    copies = n * 2
    assert len(copies) == 2
    assert all(isinstance(c, Net) for c in copies)


def test_bus_extend_and_index():
    b = Bus("B1", 4)
    assert len(b) == 4
    assert isinstance(b[0], Net)


def test_subcircuit_decorator():
    from pcb_electrical import subcircuit

    @subcircuit
    def my_sub():
        p = Part(name="SUB", pins=[Pin(num=1, name="X")])
        return p

    p = my_sub()
    assert isinstance(p, Part)
    assert p.name == "SUB"
