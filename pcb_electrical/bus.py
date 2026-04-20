# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""Bus management."""

import re
from copy import copy as copy_fn
from collections.abc import Iterable

from ._base import SkidlBaseObject
from ._utils import (
    expand_indices,
    find_num_copies,
    flatten,
    from_iadd,
    get_unique_name,
    rmv_iadd,
)

BUS_PREFIX = "B$"


class Bus(SkidlBaseObject):
    """A collection of related nets that can be indexed and connected as a group."""

    def __init__(self, *args, **attribs):
        super().__init__()
        self.nets = []
        self.do_erc = True
        self.circuit = None

        name = attribs.pop("name", None)
        if not name:
            try:
                name = [a for a in args if isinstance(a, (str, type(None)))][0]
                args = list(args)
                args.remove(name)
            except IndexError:
                name = None
        self._name = name

        from .circuit import default_circuit
        circuit = attribs.pop("circuit", default_circuit)
        circuit += self

        for k, v in list(attribs.items()):
            setattr(self, k, v)

        self.extend(args)

    def __str__(self):
        return (self.name or "") + ":\n\t" + "\n\t".join([n.__str__() for n in self.nets])

    __repr__ = __str__

    def __iter__(self):
        return (self[l] for l in range(len(self)))

    def __getitem__(self, *ids):
        from ._utils import filter_list, list_or_scalar
        nets = []
        for ident in expand_indices(0, len(self) - 1, False, *ids):
            if isinstance(ident, int):
                nets.append(self.nets[ident])
            elif isinstance(ident, str):
                nets.extend(filter_list(self.nets, aliases=ident, do_str_match=True))
            else:
                raise TypeError(f"Can't index bus with a {type(ident)}.")
        if len(nets) == 0:
            return None
        if len(nets) == 1:
            return nets[0]
        from .net import NetPinList
        return NetPinList(nets)

    def __setitem__(self, ids, *pins_nets_buses):
        if from_iadd(pins_nets_buses):
            rmv_iadd(pins_nets_buses)
            return
        raise TypeError("Can't assign to a bus! Use the += operator.")

    def __iadd__(self, *pins_nets_buses):
        return self.connect(*pins_nets_buses)

    def __call__(self, num_copies=None, **attribs):
        return self.copy(num_copies=num_copies, **attribs)

    def __mul__(self, num_copies):
        if num_copies is None:
            num_copies = 0
        return self.copy(num_copies=num_copies)

    __rmul__ = __mul__

    def __len__(self):
        return len(self.nets)

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    def insert(self, index, *objects):
        from ._utils import flatten
        from .net import Net
        from .pin import Pin

        for obj in flatten(objects):
            if isinstance(obj, int):
                for _ in range(obj):
                    self.nets.insert(index, Net(circuit=self.circuit))
                index += obj
            elif isinstance(obj, Net):
                self.nets.insert(index, obj)
                index += 1
            elif isinstance(obj, Pin):
                try:
                    self.nets.insert(index, obj.get_nets()[0])
                except IndexError:
                    n = Net(circuit=self.circuit)
                    n += obj
                    self.nets.insert(index, n)
                index += 1
            elif isinstance(obj, Bus):
                for n in reversed(obj.nets):
                    self.nets.insert(index, n)
                index += len(obj)
            else:
                raise ValueError(
                    f"Adding illegal type of object ({type(obj)}) to Bus {self.name}."
                )

        sep = "_" if self.name and self.name[-1].isdigit() else ""
        for i, net in enumerate(self.nets):
            if net.is_implicit():
                net.name = (self.name or "") + sep + str(i)

    def extend(self, *objects):
        self.insert(len(self.nets), objects)

    def copy(self, num_copies=None, circuit=None, **attribs):
        from .circuit import default_circuit

        num_copies_attribs = find_num_copies(**attribs)
        return_list = (num_copies is not None) or (num_copies_attribs > 1)
        if num_copies is None:
            num_copies = max(1, num_copies_attribs)
        if not isinstance(num_copies, int):
            raise ValueError(
                f"Can't make a non-integer number ({num_copies}) of copies of a bus!"
            )
        if num_copies < 0:
            raise ValueError(
                f"Can't make a negative number ({num_copies}) of copies of a bus!"
            )

        circuit = circuit or self.circuit or default_circuit
        name = attribs.pop("name", self.name)
        skip_attrs = ("circuit", "_name", "_aliases")

        copies = []
        for i in range(num_copies):
            cpy = Bus(name=name, circuit=circuit)
            for k, v in self.__dict__.items():
                if k in skip_attrs:
                    continue
                if isinstance(v, Iterable) and not isinstance(v, str):
                    setattr(cpy, k, copy_fn(v))
                else:
                    setattr(cpy, k, v)
            for k, v in list(attribs.items()):
                setattr(cpy, k, v)
            copies.append(cpy)
        if return_list:
            return copies
        return copies[0]

    def get_nets(self):
        return self.nets

    def get_pins(self):
        raise Exception("Can't get the list of pins on a bus!")

    def is_movable(self):
        return all(n.is_movable() for n in self.nets)

    def is_implicit(self):
        prefix_re = f"({re.escape(NET_PREFIX)}|{re.escape(BUS_PREFIX)})+"
        return bool(re.match(prefix_re, self.name or ""))

    def connect(self, *pins_nets_buses):
        from .net import NetPinList
        nets = NetPinList(self.nets)
        nets += pins_nets_buses
        return self

    @property
    def name(self):
        return super().name

    @name.setter
    def name(self, name):
        del self.name
        SkidlBaseObject.name.fset(
            self, get_unique_name(self.circuit.buses, "name", BUS_PREFIX, name)
        )

    @name.deleter
    def name(self):
        SkidlBaseObject.name.fdel(self)

    @property
    def width(self):
        return len(self)

    @property
    def pins(self):
        return self.get_pins()
