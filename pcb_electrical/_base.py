# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""Minimal SkidlBaseObject with ERROR/OK/WARNING constants."""

import inspect
from copy import deepcopy
from collections import namedtuple

__all__ = ["OK", "WARNING", "ERROR", "SkidlBaseObject", "Alias"]

OK, WARNING, ERROR = range(3)


class Alias:
    """Minimal alias container replacing skidl.alias.Alias."""

    def __init__(self, name_or_list):
        self._items = set()
        if name_or_list:
            self += name_or_list

    def __iadd__(self, other):
        if isinstance(other, (list, tuple, set)):
            self._items.update(str(i) for i in other if i is not None)
        elif other is not None:
            self._items.add(str(other))
        return self

    def discard(self, item):
        try:
            self._items.discard(str(item))
        except Exception:
            pass

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __contains__(self, item):
        return str(item) in self._items

    def __eq__(self, other):
        return str(other) in self._items

    def __repr__(self):
        return repr(self._items)


class SkidlBaseObject:
    """Base class for all SKiDL objects."""

    erc_list = list()
    erc_assertion_list = list()

    def __init__(self):
        self.fields = {}

    def __getattr__(self, key):
        try:
            return self.__getattribute__("fields")[key]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        if key == "fields" or key not in self.fields:
            super().__setattr__(key, value)
        else:
            self.fields[key] = value

    def copy(self):
        cpy = SkidlBaseObject()
        cpy.fields = deepcopy(self.fields)
        try:
            cpy.aliases = deepcopy(self.aliases)
        except AttributeError:
            pass
        try:
            cpy.notes = deepcopy(self.notes)
        except AttributeError:
            pass
        return cpy

    def ERC(self, *args, **kwargs):
        self._exec_erc_functions(*args, **kwargs)
        self._eval_erc_assertions()

    def add_erc_function(self, func):
        self.erc_list.append(func)

    def add_erc_assertion(self, assertion, fail_msg="FAILED", severity=ERROR):
        EvalTuple = namedtuple(
            "EvalTuple",
            "stmnt fail_msg severity filename lineno function globals locals",
        )
        assertion_frame, filename, lineno, function, _, _ = inspect.stack()[1]
        self.erc_assertion_list.append(
            EvalTuple(
                assertion,
                fail_msg,
                severity,
                filename,
                lineno,
                function,
                assertion_frame.f_globals,
                assertion_frame.f_locals,
            )
        )

    def _eval_erc_assertions(self):
        for evtpl in self.erc_assertion_list:
            if eval(evtpl.stmnt, evtpl.globals, evtpl.locals) == False:
                msg = f"{evtpl.stmnt} {evtpl.fail_msg} in {evtpl.filename}:{evtpl.lineno}:{evtpl.function}."
                if evtpl.severity == ERROR:
                    print("ERROR:", msg)
                elif evtpl.severity == WARNING:
                    print("WARNING:", msg)

    def _exec_erc_functions(self, *args, **kwargs):
        for f in self.erc_list:
            f(self, *args, **kwargs)

    @property
    def name(self):
        return getattr(self, "_name", None)

    @name.setter
    def name(self, nm):
        del self.name
        if not hasattr(self, "_aliases"):
            self._aliases = Alias([])
        self._aliases += nm
        self._name = nm

    @name.deleter
    def name(self):
        try:
            if hasattr(self, "_aliases"):
                self._aliases.discard(getattr(self, "_name", None))
            self._name = None
        except AttributeError:
            pass

    @property
    def aliases(self):
        try:
            return self._aliases
        except AttributeError:
            return Alias([])

    @aliases.setter
    def aliases(self, name_or_list):
        if not name_or_list:
            return
        self._aliases = Alias(name_or_list)

    @aliases.deleter
    def aliases(self):
        try:
            del self._aliases
        except AttributeError:
            pass
