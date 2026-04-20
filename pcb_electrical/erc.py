# SPDX-License-Identifier: MIT
# Copyright (c) 2016–2021 Dave Vandenbout
# Ported to FreeCAD-PCB under AGPLv3 by Comfac-Global-Group (CGG R&D), 2026

"""Electrical Rule Checking (ERC)."""


def dflt_circuit_erc(circuit):
    """Perform electrical rules check on an entire circuit."""
    circuit.merge_net_names()
    checked = set()
    for net in circuit.nets:
        if net.name not in checked:
            net.ERC()
            checked.add(net.name)
    for part in circuit.parts:
        part.ERC()


def dflt_part_erc(part):
    """Perform electrical rules check on a specific part."""
    from .pin import pin_types, pin_drives

    if not part.do_erc:
        return
    for pin in part.pins:
        if not pin.do_erc:
            continue
        if pin.net is None:
            if pin.func != pin_types.NOCONNECT:
                print(f"WARNING: Unconnected pin: {pin.erc_desc()}.")
        elif pin.net.drive != pin_drives.NOCONNECT:
            if pin.func == pin_types.NOCONNECT:
                print(
                    f"WARNING: Incorrectly connected pin: {pin.erc_desc()} should not be connected to a net ({pin.net.name})."
                )


def dflt_net_erc(net):
    """Perform electrical rules check on a specific net."""
    from .pin import pin_drives, pin_info

    net.test_validity()
    if not net.do_erc:
        return

    pins = net.pins
    num_pins = len(pins)
    if num_pins == 0:
        print(f"WARNING: No pins attached to net {net.name}.")
    elif num_pins == 1:
        print(
            f"WARNING: Only one pin ({pins[0].erc_desc()}) attached to net {net.name}."
        )
    else:
        for i in range(num_pins):
            for j in range(i + 1, num_pins):
                pins[i].chk_conflict(pins[j])

    net_drive = max([p.drive for p in pins] + [net.drive])
    if net_drive <= pin_drives.NONE:
        print(f"WARNING: No drivers for net {net.name}.")
    for p in pins:
        if pin_info[p.func]["min_rcv"] > net_drive:
            print(
                f"WARNING: Insufficient drive current on net {net.name} for pin {p.erc_desc()}."
            )
