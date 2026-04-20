# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""Handles part pins and their connections to nets."""

import random
import re
import sys
from collections import defaultdict
from collections.abc import Iterable
from copy import copy as copy_fn
from enum import IntEnum
from functools import total_ordering

from ._base import ERROR, OK, WARNING, SkidlBaseObject
from ._utils import (
    expand_buses,
    expand_indices,
    find_num_copies,
    flatten,
    from_iadd,
    rmv_iadd,
    set_iadd,
    to_list,
)


pin_types = IntEnum(
    "pin_types",
    (
        "INPUT",
        "OUTPUT",
        "BIDIR",
        "TRISTATE",
        "PASSIVE",
        "UNSPEC",
        "PWRIN",
        "PWROUT",
        "OPENCOLL",
        "OPENEMIT",
        "PULLUP",
        "PULLDN",
        "NOCONNECT",
        "FREE",
    ),
)

pin_drives = IntEnum(
    "pin_drives",
    (
        "NOCONNECT",
        "NONE",
        "PASSIVE",
        "PULLUPDN",
        "ONESIDE",
        "TRISTATE",
        "PUSHPULL",
        "POWER",
    ),
)

pin_info = {
    pin_types.INPUT: {
        "function": "INPUT",
        "func_str": "INPUT",
        "drive": pin_drives.NONE,
        "max_rcv": pin_drives.POWER,
        "min_rcv": pin_drives.PASSIVE,
    },
    pin_types.OUTPUT: {
        "function": "OUTPUT",
        "func_str": "OUTPUT",
        "drive": pin_drives.PUSHPULL,
        "max_rcv": pin_drives.PASSIVE,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.BIDIR: {
        "function": "BIDIRECTIONAL",
        "func_str": "BIDIR",
        "drive": pin_drives.TRISTATE,
        "max_rcv": pin_drives.POWER,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.TRISTATE: {
        "function": "TRISTATE",
        "func_str": "TRISTATE",
        "drive": pin_drives.TRISTATE,
        "max_rcv": pin_drives.TRISTATE,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.PASSIVE: {
        "function": "PASSIVE",
        "func_str": "PASSIVE",
        "drive": pin_drives.PASSIVE,
        "max_rcv": pin_drives.POWER,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.PULLUP: {
        "function": "PULLUP",
        "func_str": "PULLUP",
        "drive": pin_drives.PULLUPDN,
        "max_rcv": pin_drives.POWER,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.PULLDN: {
        "function": "PULLDN",
        "func_str": "PULLDN",
        "drive": pin_drives.PULLUPDN,
        "max_rcv": pin_drives.POWER,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.UNSPEC: {
        "function": "UNSPECIFIED",
        "func_str": "UNSPEC",
        "drive": pin_drives.NONE,
        "max_rcv": pin_drives.POWER,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.PWRIN: {
        "function": "POWER-IN",
        "func_str": "PWRIN",
        "drive": pin_drives.NONE,
        "max_rcv": pin_drives.POWER,
        "min_rcv": pin_drives.POWER,
    },
    pin_types.PWROUT: {
        "function": "POWER-OUT",
        "func_str": "PWROUT",
        "drive": pin_drives.POWER,
        "max_rcv": pin_drives.PASSIVE,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.OPENCOLL: {
        "function": "OPEN-COLLECTOR",
        "func_str": "OPENCOLL",
        "drive": pin_drives.ONESIDE,
        "max_rcv": pin_drives.TRISTATE,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.OPENEMIT: {
        "function": "OPEN-EMITTER",
        "func_str": "OPENEMIT",
        "drive": pin_drives.ONESIDE,
        "max_rcv": pin_drives.TRISTATE,
        "min_rcv": pin_drives.NONE,
    },
    pin_types.NOCONNECT: {
        "function": "NO-CONNECT",
        "func_str": "NOCONNECT",
        "drive": pin_drives.NOCONNECT,
        "max_rcv": pin_drives.NOCONNECT,
        "min_rcv": pin_drives.NOCONNECT,
    },
    pin_types.FREE: {
        "function": "FREE",
        "func_str": "FREE",
        "drive": pin_drives.NONE,
        "max_rcv": pin_drives.POWER,
        "min_rcv": pin_drives.NOCONNECT,
    },
}


@total_ordering
class Pin(SkidlBaseObject):
    """A class for storing data about pins for electronic parts."""

    MAX_PIN_NUM = sys.maxsize >> 3

    types = pin_types
    funcs = pin_types
    drives = pin_drives

    def __init__(self, **attribs):
        super().__init__()
        self.nets = []
        self.part = None
        self.name = ""
        self.num = ""
        self.stub = False
        self.do_erc = True
        self.func = pin_types.UNSPEC
        self.num = random.randint(self.MAX_PIN_NUM + 1, sys.maxsize)
        for k, v in list(attribs.items()):
            setattr(self, k, v)

    def __str__(self):
        ref = getattr(self.part, "ref", "???")
        num, names, func = self.get_pin_info()
        return f"Pin {ref}/{num}/{names}/{func}"

    __repr__ = __str__

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    def __lt__(self, o):
        if not isinstance(o, type(self)):
            return NotImplemented
        if self.part != o.part:
            raise ValueError("Comparing pins on different parts not supported.")
        return self._normalize_num() < o._normalize_num()

    def __eq__(self, o):
        if not isinstance(o, type(self)):
            return NotImplemented
        return self.part == o.part and self._normalize_num() == o._normalize_num()

    __hash__ = object.__hash__

    def __and__(self, obj):
        return self.connect(obj)

    def __rand__(self, obj):
        return self.connect(obj)

    def __or__(self, obj):
        return self.connect(obj)

    def __ror__(self, obj):
        return self.connect(obj)

    def __call__(self, num_copies=None, **attribs):
        return self.copy(num_copies=num_copies, **attribs)

    def __mul__(self, num_copies):
        if num_copies is None:
            num_copies = 0
        return self.copy(num_copies=num_copies)

    __rmul__ = __mul__

    def __getitem__(self, *ids):
        indices = list(set(expand_indices(0, self.width - 1, False, *ids)))
        if indices is None or len(indices) == 0:
            return None
        if len(indices) > 1:
            raise ValueError("Can't index a pin with multiple indices.")
        if indices[0] != 0:
            raise ValueError("Can't use a non-zero index for a pin.")
        return self

    def __setitem__(self, ids, *pins_nets_buses):
        if from_iadd(pins_nets_buses):
            rmv_iadd(pins_nets_buses)
            return
        raise TypeError("Can't assign to a Pin! Use the += operator.")

    def __iter__(self):
        return (self for i in [0])

    def __iadd__(self, *pins_nets_buses):
        return self.connect(*pins_nets_buses)

    def copy(self, num_copies=None, **attribs):
        num_copies_attribs = find_num_copies(**attribs)
        return_list = (num_copies is not None) or (num_copies_attribs > 1)
        if num_copies is None:
            num_copies = max(1, num_copies_attribs)
        if not isinstance(num_copies, int):
            raise ValueError(
                f"Can't make a non-integer number ({num_copies}) of copies of a pin!"
            )
        if num_copies < 0:
            raise ValueError(
                f"Can't make a negative number ({num_copies}) of copies of a pin!"
            )
        skip_attrs = ("nets", "num")
        copies = []
        for _ in range(num_copies):
            cpy = Pin()
            for k, v in self.__dict__.items():
                if k in skip_attrs:
                    continue
                if isinstance(v, Iterable) and not isinstance(v, str):
                    setattr(cpy, k, copy_fn(v))
                else:
                    setattr(cpy, k, v)
            if self.is_assigned():
                cpy.num = self.num
            for k, v in list(attribs.items()):
                setattr(cpy, k, v)
            if self.nets:
                self.nets[0] += cpy
            copies.append(cpy)
        if return_list:
            return copies
        return copies[0]

    def is_assigned(self):
        return not isinstance(self.num, int) or self.num <= self.MAX_PIN_NUM

    def is_connected(self):
        from .net import NCNet, Net

        if not self.nets:
            return False
        net_types = set([type(n) for n in self.nets])
        if set([NCNet]) == net_types:
            return False
        if set([Net]) == net_types:
            return True
        if set([Net, NCNet]) == net_types:
            raise ValueError(
                f"{self.erc_desc()} is connected to both normal and no-connect nets!"
            )
        raise ValueError(
            f"{self.erc_desc()} is connected to something strange: {self.nets}."
        )

    def is_attached(self, pin_net_bus):
        from .net import Net
        from .bus import Bus

        if not self.is_connected():
            return False
        if isinstance(pin_net_bus, Pin):
            if pin_net_bus.is_connected():
                return pin_net_bus.net.is_attached(self.net)
            return False
        if isinstance(pin_net_bus, Net):
            return pin_net_bus.is_attached(self.net)
        if isinstance(pin_net_bus, Bus):
            for net in pin_net_bus[:]:
                if self.net.is_attached(net):
                    return True
            return False
        raise ValueError(f"Pins can't be attached to {type(pin_net_bus)}!")

    def split_name(self, delimiters):
        import re

        self.aliases += re.split("[" + re.escape(delimiters) + "]", self.name)
        self.aliases.discard("")

    def connect(self, *pins_nets_buses):
        from .net import Net

        for pn in expand_buses(flatten(pins_nets_buses)):
            if isinstance(pn, Pin):
                if self.is_connected():
                    self.nets[0] += pn
                elif pn.is_connected():
                    pn.nets[0] += self
                else:
                    circuit = self.part.circuit if self.part else None
                    Net(circuit=circuit).connect(self, pn)
            elif isinstance(pn, Net):
                pn += self
            else:
                raise TypeError(
                    f"Cannot attach non-Pin/non-Net {type(pn)} to {self.erc_desc()}."
                )
        set_iadd(self, True)
        return self

    def disconnect(self):
        if not self.net:
            return
        for n in self.nets:
            n.disconnect(self)
            n.merge_names()
        self.nets = []

    def move(self, net):
        self.disconnect()
        net += self

    def get_nets(self):
        return self.nets

    def get_pins(self):
        return to_list(self)

    def chk_conflict(self, other_pin):
        if not self.do_erc or not other_pin.do_erc:
            return
        [erc_result, erc_msg] = conflict_matrix[self.func][other_pin.func]
        if erc_result == OK:
            return
        if not erc_msg:
            erc_msg = " ".join(
                (
                    pin_info[self.func]["function"],
                    "connected to",
                    pin_info[other_pin.func]["function"],
                )
            )
        n = self.net.name if self.net else "?"
        p1 = self.erc_desc()
        p2 = other_pin.erc_desc()
        msg = f"Pin conflict on net {n}, {p1} <==> {p2} ({erc_msg})"
        if erc_result == WARNING:
            print("WARNING:", msg)
        else:
            print("ERROR:", msg)

    def erc_desc(self):
        part_desc = self.part.erc_desc() if self.part else "???"
        return "{func} pin {num}/{name} of {part}".format(
            part=part_desc,
            num=self.num,
            name=self.name,
            func=pin_info[self.func]["function"],
        )

    def get_pin_info(self):
        num = getattr(self, "num", "???")
        names = [getattr(self, "name", "???")]
        names.extend(self.aliases)
        names = ",".join(names)
        func = pin_info[self.func]["function"]
        return num, names, func

    def export(self):
        attribs = []
        for k in ["num", "name", "func", "unit"]:
            v = getattr(self, k, None)
            if v:
                if k == "func":
                    v = "pin_types." + pin_info[v]["func_str"]
                else:
                    v = repr(v)
                attribs.append("{}={}".format(k, v))
        return "Pin({})".format(",".join(attribs))

    def _normalize_num(self):
        n = list(re.match(r"(\D*)(.*)", str(self.num)).group(1, 2))
        n[0] = n[0].upper()
        try:
            n[-1] = int(n[-1])
        except ValueError:
            pass
        return n

    @property
    def num(self):
        return self._num

    @num.setter
    def num(self, num):
        del self.num
        num = str(num) if num is not None else ""
        self._num = num
        if num:
            self.aliases += f"p{num}"

    @num.deleter
    def num(self):
        try:
            self.aliases.discard(self._num)
            self._num = None
        except AttributeError:
            pass

    @property
    def pins(self):
        return self.get_pins()

    @property
    def net(self):
        if self.nets:
            return self.nets[0]
        return None

    @property
    def width(self):
        return 1

    @property
    def drive(self):
        try:
            return self._drive
        except AttributeError:
            return pin_info[self.func]["drive"]

    @drive.setter
    def drive(self, drive):
        self._drive = drive

    @drive.deleter
    def drive(self):
        try:
            del self._drive
        except AttributeError:
            pass

    @property
    def ref(self):
        return self.part.ref

    @property
    def circuit(self):
        return self.part.circuit


class PhantomPin(Pin):
    """A pin type that exists solely to tie two pinless nets together."""

    def __init__(self, **attribs):
        super().__init__(**attribs)
        self.nets = []
        self.part = None
        self.do_erc = False


conflict_matrix = defaultdict(lambda: defaultdict(lambda: [OK, ""]))

conflict_matrix[pin_types.OUTPUT][pin_types.OUTPUT] = [ERROR, ""]
conflict_matrix[pin_types.TRISTATE][pin_types.OUTPUT] = [WARNING, ""]
conflict_matrix[pin_types.UNSPEC][pin_types.INPUT] = [WARNING, ""]
conflict_matrix[pin_types.UNSPEC][pin_types.OUTPUT] = [WARNING, ""]
conflict_matrix[pin_types.UNSPEC][pin_types.BIDIR] = [WARNING, ""]
conflict_matrix[pin_types.UNSPEC][pin_types.TRISTATE] = [WARNING, ""]
conflict_matrix[pin_types.UNSPEC][pin_types.PASSIVE] = [WARNING, ""]
conflict_matrix[pin_types.UNSPEC][pin_types.PULLUP] = [WARNING, ""]
conflict_matrix[pin_types.UNSPEC][pin_types.PULLDN] = [WARNING, ""]
conflict_matrix[pin_types.UNSPEC][pin_types.UNSPEC] = [WARNING, ""]
conflict_matrix[pin_types.PWRIN][pin_types.TRISTATE] = [WARNING, ""]
conflict_matrix[pin_types.PWRIN][pin_types.UNSPEC] = [WARNING, ""]
conflict_matrix[pin_types.PWROUT][pin_types.OUTPUT] = [ERROR, ""]
conflict_matrix[pin_types.PWROUT][pin_types.BIDIR] = [WARNING, ""]
conflict_matrix[pin_types.PWROUT][pin_types.TRISTATE] = [ERROR, ""]
conflict_matrix[pin_types.PWROUT][pin_types.UNSPEC] = [WARNING, ""]
conflict_matrix[pin_types.PWROUT][pin_types.PWROUT] = [ERROR, ""]
conflict_matrix[pin_types.OPENCOLL][pin_types.OUTPUT] = [ERROR, ""]
conflict_matrix[pin_types.OPENCOLL][pin_types.BIDIR] = [WARNING, ""]
conflict_matrix[pin_types.OPENCOLL][pin_types.TRISTATE] = [ERROR, ""]
conflict_matrix[pin_types.OPENCOLL][pin_types.UNSPEC] = [WARNING, ""]
conflict_matrix[pin_types.OPENCOLL][pin_types.PWROUT] = [ERROR, ""]
conflict_matrix[pin_types.OPENEMIT][pin_types.OUTPUT] = [ERROR, ""]
conflict_matrix[pin_types.OPENEMIT][pin_types.BIDIR] = [WARNING, ""]
conflict_matrix[pin_types.OPENEMIT][pin_types.TRISTATE] = [ERROR, ""]
conflict_matrix[pin_types.OPENEMIT][pin_types.UNSPEC] = [WARNING, ""]
conflict_matrix[pin_types.OPENEMIT][pin_types.PWROUT] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.INPUT] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.OUTPUT] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.BIDIR] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.TRISTATE] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.PASSIVE] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.PULLUP] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.PULLDN] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.UNSPEC] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.PWRIN] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.PWROUT] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.OPENCOLL] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.OPENEMIT] = [ERROR, ""]
conflict_matrix[pin_types.NOCONNECT][pin_types.NOCONNECT] = [ERROR, ""]
conflict_matrix[pin_types.PULLUP][pin_types.PULLUP] = [
    WARNING,
    "Multiple pull-ups connected.",
]
conflict_matrix[pin_types.PULLDN][pin_types.PULLDN] = [
    WARNING,
    "Multiple pull-downs connected.",
]
conflict_matrix[pin_types.PULLUP][pin_types.PULLDN] = [
    ERROR,
    "Pull-up connected to pull-down.",
]

cols = list(conflict_matrix.keys())
for c in cols:
    for r in list(conflict_matrix[c].keys()):
        conflict_matrix[r][c] = conflict_matrix[c][r]
