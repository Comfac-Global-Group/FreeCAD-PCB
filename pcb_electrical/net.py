# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""Network connection management."""

import collections
from collections.abc import Iterable
from copy import copy as copy_fn

from ._base import SkidlBaseObject
from ._utils import (
    expand_buses,
    expand_indices,
    find_num_copies,
    flatten,
    from_iadd,
    get_unique_name,
    rmv_iadd,
    set_iadd,
)

NET_PREFIX = "N$"
Traversal = collections.namedtuple("Traversal", ["nets", "pins"])


class NetPinList(list):
    """Specialized list for handling collections of nets and pins."""

    def __iadd__(self, *nets_pins_buses):
        from ._utils import expand_buses, flatten, set_iadd
        from .pin import Pin

        nets_pins_a = expand_buses(self)
        len_a = len(nets_pins_a)

        nets_pins_b = expand_buses(flatten(nets_pins_buses))
        allowed = (Pin, Net)
        for np in nets_pins_b:
            if not isinstance(np, allowed):
                raise ValueError(
                    f"Can't make connections to a {type(np)} ({getattr(np, '__name__', '')})."
                )
        len_b = len(nets_pins_b)

        if len_a != len_b:
            if len_a > 1 and len_b > 1:
                raise ValueError(f"Connection mismatch {len_a} != {len_b}!")
            if len_b == 1:
                nets_pins_b = [nets_pins_b[0] for _ in range(len_a)]
                len_b = len(nets_pins_b)
            elif len_a == 1:
                nets_pins_a = [nets_pins_a[0] for _ in range(len_b)]
                len_a = len(nets_pins_a)

        assert len_a == len_b

        for npa, npb in zip(nets_pins_a, nets_pins_b):
            npa += npb

        set_iadd(self, True)
        return self


from .erc import dflt_net_erc


class Net(SkidlBaseObject):
    """Represents an electrical connection between component pins."""

    erc_list = [dflt_net_erc]

    def __init__(self, name=None, circuit=None, *pins_nets_buses, **attribs):
        from .pin import pin_drives

        super().__init__()

        self._valid = True
        self.do_erc = True
        self._drive = pin_drives.NONE
        self._pins = []
        self.circuit = None
        self.code = None
        self._stub = False
        self._stub_explicit = False
        self._name = name

        from .circuit import default_circuit
        circuit = circuit or default_circuit
        circuit += self

        self.connect(pins_nets_buses)
        del self.iadd_flag

        for k, v in list(attribs.items()):
            setattr(self, k, v)

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    def __str__(self):
        self.test_validity()
        pins = self.pins
        return (
            self.name + ": " + ", ".join([p.__str__() for p in sorted(pins, key=str)])
        )

    __repr__ = __str__

    def __iadd__(self, *pins_nets_buses):
        return self.connect(*pins_nets_buses)

    def __and__(self, obj):
        return self.connect(obj)

    def __rand__(self, obj):
        return self.connect(obj)

    def __or__(self, obj):
        return self.connect(obj)

    def __ror__(self, obj):
        return self.connect(obj)

    def __len__(self):
        self.test_validity()
        return len(self.pins)

    def __getitem__(self, *ids):
        indices = list(set(expand_indices(0, self.width - 1, False, *ids)))
        if indices is None or len(indices) == 0:
            return None
        if len(indices) > 1:
            raise ValueError("Can't index a net with multiple indices.")
        if indices[0] != 0:
            raise ValueError("Can't use a non-zero index for a net.")
        return self

    def __setitem__(self, ids, *pins_nets_buses):
        if from_iadd(pins_nets_buses):
            rmv_iadd(pins_nets_buses)
            return
        raise TypeError("Can't assign to a Net! Use the += operator.")

    def __iter__(self):
        return (self[i] for i in [0])

    def __call__(self, num_copies=None, circuit=None, **attribs):
        return self.copy(num_copies=num_copies, circuit=circuit, **attribs)

    def __mul__(self, num_copies):
        if num_copies is None:
            num_copies = 0
        return self.copy(num_copies=num_copies)

    __rmul__ = __mul__

    def copy(self, num_copies=None, circuit=None, **attribs):
        self.test_validity()

        num_copies_attribs = find_num_copies(**attribs)
        return_list = (num_copies is not None) or (num_copies_attribs > 1)
        if num_copies is None:
            num_copies = max(1, num_copies_attribs)

        if not isinstance(num_copies, int):
            raise ValueError(
                "Can't make a non-integer number "
                f"({num_copies}) of copies of a net!"
            )
        if num_copies < 0:
            raise ValueError(
                "Can't make a negative number "
                f"({num_copies}) of copies of a net!"
            )

        from .circuit import default_circuit
        circuit = circuit or self.circuit or default_circuit
        name = attribs.pop("name", self.name)

        if self._pins:
            raise ValueError(
                "Can't make copies of a net that already has pins attached to it!"
            )

        skip_attrs = ("circuit", "traversal", "_name", "_aliases")

        copies = []
        for i in range(num_copies):
            cpy = Net(name=name, circuit=circuit)
            for k, v in self.__dict__.items():
                if k in skip_attrs:
                    continue
                if isinstance(v, Iterable) and not isinstance(v, str):
                    setattr(cpy, k, copy_fn(v))
                else:
                    setattr(cpy, k, v)
            copies.append(cpy)

        if return_list:
            return copies
        return copies[0]

    def get_pins(self):
        self.test_validity()
        return self._traverse().pins

    def get_nets(self):
        self.test_validity()
        return self._traverse().nets

    def is_attached(self, pin_net_bus):
        if isinstance(pin_net_bus, Net):
            return pin_net_bus in self.nets
        if isinstance(pin_net_bus, Pin):
            return pin_net_bus.is_attached(self)
        from .bus import Bus
        if isinstance(pin_net_bus, Bus):
            for net in pin_net_bus[:]:
                if self.is_attached(net):
                    return True
            return False
        raise TypeError(f"Nets can't be attached to {type(pin_net_bus)}!")

    def is_movable(self):
        from .circuit import Circuit
        return not isinstance(self.circuit, Circuit) or not self._pins

    def is_implicit(self):
        from .bus import BUS_PREFIX
        import re

        self.test_validity()
        prefix_re = f"({re.escape(NET_PREFIX)}|{re.escape(BUS_PREFIX)})+"
        return bool(re.match(prefix_re, self.name or ""))

    def connect(self, *pins_nets_buses):
        from .pin import PhantomPin, Pin

        def join(net):
            if isinstance(self, NCNet):
                raise ValueError(f"Can't join with a no-connect net {self.name}!")
            if isinstance(net, NCNet):
                raise ValueError(f"Can't join with a no-connect net {net.name}!")
            if self == net:
                return
            if self._pins:
                self._pins[0].nets.append(net)
                net._pins.append(self._pins[0])
            elif net._pins:
                net._pins[0].nets.append(self)
                self._pins.append(net._pins[0])
            else:
                p = PhantomPin()
                self._pins.append(p)
                p.nets.append(self)
                self._pins[0].nets.append(net)
                net._pins.append(self._pins[0])
            self.drive = net.drive
            net.drive = self.drive

        def connect_pin(pin):
            if pin not in self._pins:
                if not pin.is_connected():
                    pin.disconnect()
                self._pins.append(pin)
                pin.nets.append(self)
                pin.stub = self.stub

        self.test_validity()

        for pn in expand_buses(flatten(pins_nets_buses)):
            if isinstance(pn, Net):
                if pn.circuit == self.circuit:
                    join(pn)
                else:
                    raise ValueError(
                        f"Can't attach nets in different circuits ({pn.circuit.name}, {self.circuit.name})!"
                    )
            elif isinstance(pn, Pin):
                if not pn.part or pn.part.circuit == self.circuit:
                    connect_pin(pn)
                elif not pn.part.circuit:
                    print(
                        f"WARNING: Attaching part template Pin {pn.name} to a Net {self.name}."
                    )
                    connect_pin(pn)
                else:
                    raise ValueError(
                        f"Can't attach a part to a net in different circuits ({pn.part.circuit.name}, {self.circuit.name})!"
                    )
            else:
                raise TypeError(
                    f"Cannot attach non-Pin/non-Net {type(pn)} to Net {self.name}."
                )

        try:
            del self.traversal
        except AttributeError:
            pass
        self._traverse()
        self.circuit += self
        set_iadd(self, True)
        return self

    def disconnect(self, pin):
        try:
            self._pins.remove(pin)
        except ValueError:
            return
        try:
            del self.traversal
        except AttributeError:
            pass

    def merge_names(self):
        def select_name(nets):
            if len(nets) == 0:
                return None
            if len(nets) == 1:
                return nets[0]
            if len(nets) == 2:
                name0 = getattr(nets[0], "name")
                name1 = getattr(nets[1], "name")
                fixed0 = getattr(nets[0], "fixed_name", False)
                fixed1 = getattr(nets[1], "fixed_name", False)
                if not name1:
                    return nets[0]
                if not name0:
                    return nets[1]
                if fixed0 and not fixed1:
                    return nets[0]
                if fixed1 and not fixed0:
                    return nets[1]
                if fixed0 and fixed1:
                    raise ValueError(
                        f"Cannot merge two nets with fixed names: {name0} and {name1}."
                    )
                if nets[1].is_implicit():
                    return nets[0]
                if nets[0].is_implicit():
                    return nets[1]
                if name0 != name1:
                    print(
                        f"WARNING: Merging two named nets ({name0} and {name1}) into {name0}."
                    )
                return nets[0]
            mid_point = len(nets) // 2
            return select_name(
                [select_name(nets[0:mid_point]), select_name(nets[mid_point:])]
            )

        nets = self.nets
        selected_name = getattr(select_name(nets), "name", None)
        for net in nets:
            net._name = selected_name

    def _traverse(self):
        try:
            return self.traversal
        except AttributeError:
            pass
        from .pin import PhantomPin

        self.test_validity()
        prev_nets = set([self])
        nets = set([self])
        prev_pins = set([])
        pins = set(self._pins)
        while pins != prev_pins:
            for pin in pins - prev_pins:
                if pin.is_connected():
                    nets |= set(pin.nets)
            prev_pins = copy_fn(pins)
            for net in nets - prev_nets:
                pins |= set(net._pins)
            prev_nets = copy_fn(nets)
        pins = set([p for p in pins if not isinstance(p, PhantomPin)])
        self.traversal = Traversal(nets=list(nets), pins=list(pins))
        for n in self.traversal.nets:
            n.traversal = self.traversal
        return self.traversal

    @property
    def width(self):
        return 1

    @property
    def name(self):
        return super().name

    @name.setter
    def name(self, name):
        self.test_validity()
        del self.name
        SkidlBaseObject.name.fset(
            self, get_unique_name(self.circuit.nets, "name", NET_PREFIX, name)
        )

    @name.deleter
    def name(self):
        self.test_validity()
        SkidlBaseObject.name.fdel(self)

    @property
    def pins(self):
        return self.get_pins()

    @property
    def nets(self):
        return self.get_nets()

    @property
    def drive(self):
        self.test_validity()
        nets = self.nets
        max_drive = max(nets, key=lambda n: n._drive)._drive
        return max_drive

    @drive.setter
    def drive(self, drive):
        self.test_validity()
        nets = self.nets
        max_drive = max(nets, key=lambda n: n._drive)._drive
        max_drive = max(drive, max_drive)
        for n in nets:
            n._drive = max_drive

    @drive.deleter
    def drive(self):
        self.test_validity()
        nets = self.nets
        for n in nets:
            del n._drive

    @property
    def stub(self):
        return self._stub

    @stub.setter
    def stub(self, val):
        self._stub = val
        self._stub_explicit = True
        for pin in self.get_pins():
            pin.stub = val

    @property
    def valid(self):
        return self._valid

    @valid.setter
    def valid(self, val):
        self.test_validity()
        self._valid = val

    def test_validity(self):
        if self.valid:
            return
        raise ValueError(f"Net {self.name} is no longer valid. Do not use it!")


class NCNet(Net):
    """Specialized Net subclass for explicitly marking pins as not connected."""

    def __init__(self, name=None, circuit=None, *pins_nets_buses, **attribs):
        from .pin import pin_drives

        super().__init__(name=name, circuit=circuit, *pins_nets_buses, **attribs)
        self._drive = pin_drives.NOCONNECT
        self.do_erc = False

    @property
    def drive(self):
        return self._drive
