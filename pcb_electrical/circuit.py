# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""Circuit management."""

import functools

from ._base import SkidlBaseObject
from ._utils import flatten, reset_get_unique_name
from .net import NCNet
from .erc import dflt_circuit_erc

default_circuit = None
_circuit_stack = []


class Circuit(SkidlBaseObject):
    """Container for an entire electronic circuit design."""

    erc_list = [dflt_circuit_erc]

    def __init__(self, **attrs):
        super().__init__()
        self.name = ""
        self.parts = []
        self.nets = []
        self.buses = []
        self.NC = None
        self.reset()
        for k, v in list(attrs.items()):
            setattr(self, k, v)

    def __iadd__(self, *stuff):
        return self.add_stuff(*stuff)

    def __isub__(self, *stuff):
        return self.rmv_stuff(*stuff)

    def __enter__(self):
        global default_circuit
        _circuit_stack.append(default_circuit)
        default_circuit = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global default_circuit
        default_circuit = _circuit_stack.pop()
        return False

    def reset(self):
        reset_get_unique_name()
        self.name = ""
        self.parts = []
        self.nets = []
        self.buses = []
        self.NC = NCNet(name="__NOCONNECT", circuit=self)

    def add_parts(self, *parts):
        for part in parts:
            if part.circuit != self:
                if part.is_movable():
                    if isinstance(part.circuit, Circuit):
                        part.circuit -= part
                    part.circuit = self
                    part.ref = part.ref
                    self.parts.append(part)
                else:
                    raise ValueError(
                        f"Can't add unmovable part {part.ref} to this circuit."
                    )

    def rmv_parts(self, *parts):
        for part in parts:
            part.disconnect()
            if part.is_movable():
                if part.circuit == self and part in self.parts:
                    part.circuit = None
                    self.parts.remove(part)
                else:
                    print(
                        f"WARNING: Removing non-existent part {part.ref} from this circuit."
                    )
            else:
                raise ValueError(
                    f"Can't remove part {part.ref} from this circuit."
                )

    def add_nets(self, *nets):
        for net in nets:
            if net.circuit != self:
                if net.is_movable():
                    if isinstance(net.circuit, Circuit):
                        net.circuit -= net
                    net.circuit = self
                    net.name = net.name
                    self.nets.append(net)
                else:
                    raise ValueError(
                        f"Can't add unmovable net {net.name} to this circuit."
                    )

    def rmv_nets(self, *nets):
        for net in nets:
            if net.is_movable():
                if net.circuit == self and net in self.nets:
                    net.circuit = None
                    self.nets.remove(net)
                else:
                    print(
                        f"WARNING: Removing non-existent net {net.name} from this circuit."
                    )
            else:
                raise ValueError(
                    f"Can't remove unmovable net {net.name} from this circuit."
                )

    def add_buses(self, *buses):
        for bus in buses:
            if bus.circuit != self:
                if bus.is_movable():
                    if isinstance(bus.circuit, Circuit):
                        bus.circuit -= bus
                    bus.circuit = self
                    bus.name = bus.name
                    self.buses.append(bus)
                    for net in bus.nets:
                        self += net
                else:
                    raise ValueError(
                        f"Can't add unmovable bus {bus.name} to this circuit."
                    )

    def rmv_buses(self, *buses):
        for bus in buses:
            if bus.is_movable():
                if bus.circuit == self and bus in self.buses:
                    bus.circuit = None
                    self.buses.remove(bus)
                    for net in bus.nets:
                        self -= net
                else:
                    print(
                        f"WARNING: Removing non-existent bus {bus.name} from this circuit."
                    )
            else:
                raise ValueError(
                    f"Can't remove unmovable bus {bus.name} from this circuit."
                )

    def add_stuff(self, *stuff):
        for thing in flatten(stuff):
            from .part import Part
            from .net import Net
            from .bus import Bus
            if isinstance(thing, Part):
                self.add_parts(thing)
            elif isinstance(thing, Net):
                self.add_nets(thing)
            elif isinstance(thing, Bus):
                self.add_buses(thing)
            else:
                raise ValueError(
                    f"Can't add a {type(thing)} to a Circuit object."
                )
        return self

    def rmv_stuff(self, *stuff):
        for thing in flatten(stuff):
            from .part import Part
            from .net import Net
            from .bus import Bus
            if isinstance(thing, Part):
                self.rmv_parts(thing)
            elif isinstance(thing, Net):
                self.rmv_nets(thing)
            elif isinstance(thing, Bus):
                self.rmv_buses(thing)
            else:
                raise ValueError(
                    f"Can't remove a {type(thing)} from a Circuit object."
                )
        return self

    def get_nets(self):
        distinct_nets = []
        for net in self.nets:
            if net is self.NC:
                continue
            if not net.pins:
                continue
            for n in distinct_nets:
                if net.is_attached(n):
                    break
            else:
                distinct_nets.append(net)
        return distinct_nets

    def merge_net_names(self):
        for net in self.nets:
            if len(net.nets) > 1:
                net.merge_names()

    def ERC(self, *args, **kwargs):
        self.merge_net_names()
        for f in self.erc_list:
            f(self, *args, **kwargs)
        super().ERC(*args, **kwargs)

    def cull_unconnected_parts(self):
        for part in self.parts[:]:
            if not part.is_connected():
                self -= part


default_circuit = Circuit()


def subcircuit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with default_circuit:
            return func(*args, **kwargs)
    return wrapper
