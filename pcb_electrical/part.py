# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""Handles parts in a circuit."""

import copy as copy_module
from collections.abc import Iterable

from ._base import SkidlBaseObject
from ._utils import (
    add_unique_attr,
    find_num_copies,
    flatten,
    from_iadd,
    get_unique_name,
    list_or_scalar,
    rmv_iadd,
    rmv_unique_name,
    to_list,
)


class PinNumberSearch:
    """Restrict part pin indexing to only pin numbers."""

    def __init__(self, part):
        self.part = part

    def get_pins(self, *pin_ids, **criteria):
        criteria["only_search_numbers"] = True
        return self.part.get_pins(*pin_ids, **criteria)

    __getitem__ = get_pins

    def __setitem__(self, ids, *pins_nets_buses):
        self.part.__setitem__(ids, *pins_nets_buses)


class PinNameSearch:
    """Restrict part pin indexing to only pin names."""

    def __init__(self, part):
        self.part = part

    def get_pins(self, *pin_ids, **criteria):
        criteria["only_search_names"] = True
        return self.part.get_pins(*pin_ids, **criteria)

    __getitem__ = get_pins

    def __setitem__(self, ids, *pins_nets_buses):
        self.part.__setitem__(ids, *pins_nets_buses)


class PinMixin:
    """Mixin class that adds pin-related methods."""

    def __init__(self):
        self.pins = []
        self._match_pin_regex = False

    def __iadd__(self, *pins):
        return self.add_pins(*pins)

    def __getitem__(self, *pin_ids, **criteria):
        return self.get_pins(*pin_ids, **criteria)

    def __setitem__(self, ids, *pins_nets_buses):
        if from_iadd(pins_nets_buses):
            rmv_iadd(pins_nets_buses)
            return
        raise TypeError("Can't assign to a part! Use the += operator.")

    def __getattr__(self, attr):
        from .net import NetPinList
        pins = [pin for pin in self if pin.aliases == attr]
        if pins:
            if len(pins) == 1:
                return pins[0]
            return NetPinList(pins)
        return SkidlBaseObject.__getattr__(self, attr)

    def __iter__(self):
        self_pins = object.__getattribute__(self, "pins")
        return (p for p in self_pins)

    def associate_pins(self):
        for p in self:
            p.part = self

    def add_pins(self, *pins):
        for pin in flatten(pins):
            pin.part = self
            self.pins.append(pin)
        return self

    def create_pins(self, base_name, pin_count=None, connections=None):
        from .net import NetPinList
        from .pin import Pin, PhantomPin

        if connections is not None:
            connections = NetPinList(connections)

        if pin_count is None:
            if connections is None or len(connections) == 1:
                indices = [None]
            else:
                indices = range(1, len(connections) + 1)
        elif isinstance(pin_count, int):
            indices = range(1, pin_count + 1)
        elif isinstance(pin_count, (range, slice, list, tuple)):
            if isinstance(pin_count, slice):
                start = pin_count.start if pin_count.start is not None else 1
                stop = pin_count.stop
                step = pin_count.step if pin_count.step is not None else 1
                indices = range(start, stop, step)
            else:
                indices = pin_count
        else:
            print(
                f"ERROR: pin_count must be int, range, slice, or None, got {type(pin_count)}"
            )
            return self

        if connections is not None:
            if len(connections) != len(indices):
                print(
                    f"ERROR: Number of connections ({len(connections)}) must match "
                    f"number of pins created ({len(indices)})"
                )
                return self

        if type(self).__name__ == "Part":
            pin_class = Pin
        else:
            pin_class = PhantomPin

        created_pins = []
        for index in indices:
            pin_num = len(self.pins) + 1
            if index is None:
                pin_name = base_name
            else:
                pin_name = f"{base_name}{index}"
            pin = pin_class(num=pin_num, name=pin_name, part=self)
            self.add_pins(pin)
            created_pins.append(pin)

        if connections:
            connections += created_pins

        return self

    def rmv_pins(self, *pin_ids):
        import sys
        from ._utils import expand_indices

        pin_ids = list(set(expand_indices(0, sys.maxsize, False, *pin_ids)))
        pin_ids = [str(pin_id) for pin_id in pin_ids]
        for i, pin in reversed(tuple(enumerate(self))):
            pin_id = set((pin.num, *pin.aliases))
            if not pin_id.isdisjoint(pin_ids):
                del self.pins[i]

    def swap_pins(self, pin_id1, pin_id2):
        pin_id1 = str(pin_id1)
        pin_id2 = str(pin_id2)
        pins = self.pins
        i1, i2 = None, None
        for i, pin in enumerate(pins):
            pin_num_name = (pin.num, *pin.aliases)
            if pin_id1 in pin_num_name:
                i1 = i
            elif pin_id2 in pin_num_name:
                i2 = i
            if i1 is not None and i2 is not None:
                pins[i1].num, pins[i1].name, pins[i2].num, pins[i2].name = (
                    pins[i2].num,
                    pins[i2].name,
                    pins[i1].num,
                    pins[i1].name,
                )
                return

    def rename_pin(self, pin_id, new_pin_name):
        pin_id = str(pin_id)
        for pin in self:
            if pin_id in (pin.num, *pin.aliases):
                pin.name = new_pin_name
                return

    def renumber_pin(self, pin_id, new_pin_num):
        pin_id = str(pin_id)
        for pin in self:
            if pin_id in (pin.num, *pin.aliases):
                pin.num = new_pin_num
                return

    def get_pins(self, *pin_ids, **criteria):
        from .net import NetPinList
        from ._utils import expand_indices, filter_list, Rgx

        silent = criteria.pop("silent", False)
        only_search_numbers = criteria.pop("only_search_numbers", False)
        only_search_names = criteria.pop("only_search_names", False)
        match_regex = criteria.pop("match_regex", False) or self.match_pin_regex

        if not pin_ids:
            pin_ids = [Rgx(".*")]

        if "min_pin" not in dir(self) or "max_pin" not in dir(self):
            self.min_pin, self.max_pin = self._find_min_max_pins()

        pins = NetPinList()
        for p_id in expand_indices(self.min_pin, self.max_pin, match_regex, *pin_ids):
            if not only_search_names:
                tmp_pins = filter_list(
                    self.pins, num=str(p_id), do_str_match=True, **criteria
                )
                if tmp_pins:
                    pins.extend(tmp_pins)
                    continue
            if not only_search_numbers:
                tmp_pins = filter_list(
                    self.pins, aliases=p_id, do_str_match=True, **criteria
                )
                if tmp_pins:
                    pins.extend(tmp_pins)
                    continue
                tmp_pins = filter_list(
                    self.pins, name=p_id, do_str_match=True, **criteria
                )
                if tmp_pins:
                    pins.extend(tmp_pins)
                    continue
                if not match_regex:
                    continue
                tmp_pins = filter_list(self.pins, aliases=Rgx(p_id), **criteria)
                if tmp_pins:
                    pins.extend(tmp_pins)
                    continue
                tmp_pins = filter_list(self.pins, name=Rgx(p_id), **criteria)
                if tmp_pins:
                    pins.extend(tmp_pins)
                    continue
        if not pins and not silent:
            print(
                f"ERROR: No pins found using {self.name}:{getattr(self, 'ref', '?')}[{pin_ids}]"
            )
        return list_or_scalar(pins)

    def disconnect(self):
        for pin in self:
            pin.disconnect()

    def split_pin_names(self, delimiters):
        if delimiters:
            for pin in self:
                pin.split_name(delimiters)

    def _find_min_max_pins(self):
        pin_nums = []
        try:
            for p in self:
                try:
                    pin_nums.append(int(p.num))
                except ValueError:
                    pass
        except AttributeError:
            pass
        try:
            return min(pin_nums), max(pin_nums)
        except ValueError:
            return 0, 0

    @property
    def ordered_pins(self):
        return sorted(self)

    @property
    def match_pin_regex(self):
        return self._match_pin_regex

    @match_pin_regex.setter
    def match_pin_regex(self, flag):
        self._match_pin_regex = flag

    @match_pin_regex.deleter
    def match_pin_regex(self):
        del self._match_pin_regex


from .erc import dflt_part_erc


class Part(PinMixin, SkidlBaseObject):
    """A class for storing a definition of a schematic part."""

    erc_list = [dflt_part_erc]

    def __init__(self, name=None, ref_prefix="U", ref=None, circuit=None, pins=None, **kwargs):
        SkidlBaseObject.__init__(self)
        PinMixin.__init__(self)
        self.do_erc = True
        self.unit = {}
        self.p = PinNumberSearch(self)
        self.n = PinNameSearch(self)
        self.name = name or ""
        self._ref = ""
        self.circuit = None
        self.ref_prefix = ref_prefix or "U"
        from .circuit import default_circuit
        circuit = circuit or default_circuit
        circuit += self
        if pins:
            self.add_pins(pins)
            self.associate_pins()
        if ref:
            self.ref = ref
        for k, v in list(kwargs.items()):
            setattr(self, k, v)
        self.aliases += self.name

    def __str__(self):
        return "\n {name} ({aliases}): {desc}\n    {pins}".format(
            name=self.name,
            aliases=", ".join(self.aliases),
            desc=getattr(self, "description", ""),
            pins="\n    ".join([p.__str__() for p in self.pins]),
        )

    __repr__ = __str__

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    def __len__(self):
        return len(self.pins)

    def __call__(self, num_copies=None, circuit=None, **attribs):
        return self.copy(num_copies=num_copies, circuit=circuit, **attribs)

    def __mul__(self, num_copies):
        if num_copies is None:
            num_copies = 0
        return self.copy(num_copies=num_copies)

    __rmul__ = __mul__

    def copy(self, num_copies=None, circuit=None, **attribs):
        from .circuit import default_circuit
        from .pin import Pin

        num_copies_attribs = find_num_copies(**attribs)
        return_list = (num_copies is not None) or (num_copies_attribs > 1)
        if num_copies is None:
            num_copies = max(1, num_copies_attribs)
        if not isinstance(num_copies, int):
            raise ValueError(
                f"Can't make a non-integer number ({num_copies}) of copies of a part!"
            )
        if num_copies < 0:
            raise ValueError(
                f"Can't make a negative number ({num_copies}) of copies of a part!"
            )

        copies = []
        for i in range(num_copies):
            cpy = copy_module.copy(self)
            for k, v in self.__dict__.items():
                if isinstance(v, Pin):
                    continue
                if isinstance(v, Iterable) and not isinstance(v, str):
                    setattr(cpy, k, copy_module.copy(v))
            try:
                del cpy.tag
            except AttributeError:
                pass
            rmv_attrs = [
                k for k, v in list(cpy.__dict__.items()) if isinstance(v, Pin)
            ]
            for attr in rmv_attrs:
                delattr(cpy, attr)
            cpy.pins = []
            cpy += [p.copy(part=cpy) for p in self.pins]
            cpy.p = PinNumberSearch(cpy)
            cpy.n = PinNameSearch(cpy)
            cpy.fields = {k: v for k, v in self.fields.items()}
            cpy._ref = None
            cpy.circuit = None
            circuit = circuit or self.circuit or default_circuit
            circuit += cpy
            for k, v in list(attribs.items()):
                if isinstance(v, (list, tuple)):
                    try:
                        v = v[i]
                    except IndexError:
                        raise ValueError(
                            f"{num_copies} copies of part {self.name} were requested, but too few elements in attribute {k}!"
                        )
                setattr(cpy, k, v)
            copies.append(cpy)
        if return_list:
            return copies
        return copies[0]

    def validate(self):
        for pin in self.pins:
            assert pin.part == self

    def is_connected(self):
        if len(self.pins) == 0:
            return True
        for p in self.pins:
            if p.is_connected():
                return True
        return False

    def attached_to(self, nets=None):
        if not nets:
            return False
        for pin in self:
            for net in pin.nets:
                if net in nets:
                    return True
        return False

    def is_movable(self):
        from .circuit import Circuit
        return (
            not isinstance(self.circuit, Circuit)
            or not self.is_connected()
            or not self.pins
        )

    def erc_desc(self):
        return f"{self.name}/{self.ref}"

    def disconnect(self):
        for pin in self:
            pin.disconnect()

    @property
    def ref(self):
        return self._ref

    @ref.setter
    def ref(self, r):
        del self.ref
        self._ref = get_unique_name(self.circuit.parts, "ref", self.ref_prefix, r)

    @ref.deleter
    def ref(self):
        rmv_unique_name(self.circuit.parts, "ref", self._ref)
        self._ref = None

    @property
    def value(self):
        try:
            return self._value
        except AttributeError:
            return self.name

    @value.setter
    def value(self, value):
        self._value = value

    @value.deleter
    def value(self):
        del self._value
