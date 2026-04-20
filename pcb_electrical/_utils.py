# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""Helper functions ported from SKiDL utilities.py."""

import collections
import re

INDEX_SEPARATOR = re.compile("[, \t]+")


class Rgx(str):
    """String subclass that represents a regular expression."""

    def __init__(self, s):
        str.__init__(s)


def to_list(x):
    if isinstance(x, (list, tuple, set)):
        return x
    return [x]


def list_or_scalar(lst):
    if isinstance(lst, (list, tuple)):
        if len(lst) > 1:
            return lst
        if len(lst) == 1:
            return list(lst)[0]
        return None
    return lst


def flatten(nested_list):
    lst = []
    for item in nested_list:
        if isinstance(item, (list, tuple, set)):
            lst.extend(flatten(item))
        else:
            lst.append(item)
    return lst


def set_attr(objs, attr, value):
    for o in to_list(objs):
        setattr(o, attr, value)


def rmv_attr(objs, attrs):
    for o in to_list(objs):
        for a in to_list(attrs):
            try:
                delattr(o, a)
            except AttributeError:
                pass


def from_iadd(objs):
    try:
        for o in objs:
            if getattr(o, "iadd_flag", False):
                return True
        return False
    except TypeError:
        return getattr(objs, "iadd_flag", False)


def set_iadd(objs, value):
    set_attr(objs, "iadd_flag", value)


def rmv_iadd(objs):
    rmv_attr(objs, "iadd_flag")


def add_unique_attr(obj, name, value, check_dup=False):
    try:
        getattr(obj, name)
        if check_dup:
            print(
                f"Warning: Unable to create attribute {name} because one already exists in {obj}"
            )
        else:
            setattr(obj, name, value)
    except AttributeError:
        setattr(obj, name, value)


name_heap = set([None])
prefix_counts = collections.Counter()


def reset_get_unique_name():
    global name_heap, prefix_counts
    name_heap = set([None])
    prefix_counts = collections.Counter()


def get_unique_name(lst, attrib, prefix, initial=None):
    lst_id = f"{id(lst)}:"
    name = initial

    if prefix[-1].isdigit():
        prefix += "_"

    if not name:
        probe_name = prefix + str(prefix_counts[lst_id + prefix] + 1)
        if lst_id + probe_name not in name_heap:
            name_heap.add(lst_id + probe_name)
            prefix_counts[lst_id + prefix] += 1
            return probe_name
    else:
        if isinstance(name, int):
            probe_name = prefix + str(name)
        else:
            probe_name = name
        if lst_id + probe_name not in name_heap:
            name_heap.add(lst_id + probe_name)
            return name

    unique_names = set([str(getattr(l, attrib, None)) for l in lst])
    unique_names -= {None}

    if not name:
        prefix_names = {n for n in unique_names if str(n).startswith(prefix)}
        next_avail_num = max(
            [int(n[len(prefix) :]) for n in prefix_names if n[len(prefix) :].isdigit()],
            default=0,
        ) + 1
        name = prefix + str(next_avail_num)
        name_heap.add(lst_id + name)
        prefix_counts[lst_id + prefix] = next_avail_num
        return name

    elif isinstance(name, int):
        name = prefix + str(name)

    if name not in unique_names:
        name_heap.add(lst_id + name)
        prefix_counts[lst_id + prefix] += 1
        return name

    if name[-1].isdigit():
        name = name + "_"
    name_conflicts = {n for n in unique_names if n.startswith(name)}
    next_avail_num = max(
        [int(n[len(name) :]) for n in name_conflicts if n[len(name) :].isdigit()],
        default=0,
    ) + 1
    name = name + str(next_avail_num)
    name_heap.add(lst_id + name)
    prefix_counts[lst_id + prefix] = next_avail_num
    return name


def rmv_unique_name(lst, attrib, name):
    lst_id = str(id(lst))
    try:
        name_heap.remove(lst_id + str(name))
    except KeyError:
        pass


def split_unquoted(pattern, string, maxsplit=0, flags=0):
    result = []
    current = []
    in_quote = None
    escaped = False
    splits_done = 0
    i = 0
    while i < len(string):
        char = string[i]
        if escaped:
            current.append(char)
            escaped = False
            i += 1
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            i += 1
            continue
        if char in ('"', "'"):
            if in_quote is None:
                in_quote = char
            elif in_quote == char:
                in_quote = None
            i += 1
            continue
        if in_quote is not None:
            current.append(char)
            i += 1
            continue
        if maxsplit == 0 or splits_done < maxsplit:
            match = re.match(pattern, string[i:], flags=flags)
            if match:
                if current or result:
                    result.append("".join(current))
                    current = []
                splits_done += 1
                i += len(match.group(0))
                continue
        current.append(char)
        i += 1
    if current or result:
        result.append("".join(current))
    return result


def fullmatch(regex, string, flags=0):
    return re.match("(?:" + regex + r")\Z", string, flags=flags)


def filter_list(lst, **criteria):
    def strmatch(a, b, flags):
        return a.lower() == b.lower()

    if criteria.pop("do_str_match", False):
        compare_func = strmatch
    else:
        compare_func = fullmatch

    extract = []
    for item in lst:
        for k, v in list(criteria.items()):
            try:
                attr_val = to_list(getattr(item, k))
            except AttributeError:
                break
            if isinstance(v, Rgx):
                for val in attr_val:
                    if fullmatch(
                        str(v),
                        str(val),
                        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
                    ):
                        break
                else:
                    break
            elif isinstance(v, (int, str)):
                for val in attr_val:
                    if compare_func(
                        str(v),
                        str(val),
                        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
                    ):
                        break
                else:
                    break
            else:
                if v not in attr_val:
                    break
        else:
            extract.append(item)
    return extract


def expand_indices(slice_min, slice_max, match_regex, *indices):
    def expand_slice(slc):
        start, stop, step = slc.indices(slice_max)
        start = min(max(start, slice_min), slice_max)
        stop = min(max(stop, slice_min), slice_max)
        if start > stop:
            if slc.start and slc.start > slice_max:
                raise IndexError(f"Index out of range ({slc.start} > {slice_max})!")
            stop = stop - step
            step = -step
        else:
            if slc.stop and slc.stop > slice_max:
                raise IndexError(f"Index out of range ({slc.stop} > {slice_max})!")
            stop += step
        return list(range(start, stop, step))

    def explode(bus_str):
        bus = re.match(r"^(.+)\[([0-9]+):([0-9]+)\](.*)$", bus_str)
        if not bus:
            return [bus_str]
        beg_bus_name = bus.group(1)
        begin_num = int(bus.group(2))
        end_num = int(bus.group(3))
        end_bus_name = bus.group(4)
        direction = [1, -1][int(begin_num > end_num)]
        bus_pin_nums = list(range(begin_num, end_num + direction, direction))
        if match_regex:
            if beg_bus_name[0:1].isalpha():
                non_alphanum = "((?<=[^0-9a-zA-Z])|^)"
            else:
                non_alphanum = ""
        else:
            non_alphanum = ""
        if match_regex:
            non_num = "(?=[^0-9]|$)"
        else:
            non_num = ""
        return [
            non_alphanum + beg_bus_name + str(n) + non_num + end_bus_name
            for n in bus_pin_nums
        ]

    ids = []
    for indx in flatten(indices):
        if isinstance(indx, slice):
            ids.extend(expand_slice(indx))
        elif isinstance(indx, int):
            ids.append(indx)
        elif isinstance(indx, Rgx):
            for id_ in split_unquoted(INDEX_SEPARATOR, indx):
                ids.extend((Rgx(i) for i in explode(id_.strip())))
        elif isinstance(indx, str):
            for id_ in split_unquoted(INDEX_SEPARATOR, indx):
                ids.extend(explode(id_.strip()))
        else:
            raise TypeError(f"Unknown type in index: {type(indx)}.")
    return ids


def expand_buses(pins_nets_buses):
    pins_nets = []
    for pnb in pins_nets_buses:
        pins_nets.extend(pnb)
    return pins_nets


def find_num_copies(**attribs):
    num_copies = set()
    for k, v in list(attribs.items()):
        if isinstance(v, (list, tuple)):
            num_copies.add(len(v))
        else:
            num_copies.add(1)
    num_copies = list(num_copies)
    if len(num_copies) > 2:
        raise ValueError(f"Mismatched lengths of attributes: {num_copies}!")
    elif len(num_copies) > 1 and min(num_copies) > 1:
        raise ValueError(f"Mismatched lengths of attributes: {num_copies}!")
    try:
        return max(num_copies)
    except ValueError:
        return 0
