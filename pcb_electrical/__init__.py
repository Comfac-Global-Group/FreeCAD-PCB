# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""pcb_electrical — standalone electrical graph for FreeCAD-PCB."""

from ._base import ERROR, OK, WARNING, SkidlBaseObject
from ._utils import Rgx, to_list, flatten, expand_buses
from .pin import Pin, pin_types, pin_drives, pin_info, conflict_matrix
from .net import Net, NCNet
from .part import Part
from .bus import Bus
from .circuit import Circuit, default_circuit, subcircuit
from .erc import dflt_circuit_erc, dflt_part_erc, dflt_net_erc

__all__ = [
    "Part",
    "Pin",
    "Net",
    "Bus",
    "Circuit",
    "ERC",
    "pin_types",
    "pin_drives",
    "pin_info",
    "conflict_matrix",
    "default_circuit",
    "subcircuit",
    "NCNet",
]


def ERC(circuit=None):
    """Run Electrical Rule Check on a circuit (default circuit if None)."""
    circuit = circuit or default_circuit
    circuit.ERC()
