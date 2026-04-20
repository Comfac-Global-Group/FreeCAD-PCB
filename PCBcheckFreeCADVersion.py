# -*- coding: utf8 -*-
#****************************************************************************
#*                                                                          *
#*   Printed Circuit Board Workbench for FreeCAD             PCB            *
#*                                                                          *
#*   Copyright (c) 2013-2019                                                *
#*   marmni <marmni@onet.eu>                                                *
#*                                                                          *
#*   Copyright (c) 2026                                                     *
#*   Comfac-Global-Group (CGG R&D)                                          *
#*                                                                          *
#*   This program is free software; you can redistribute it and/or modify   *
#*   it under the terms of the GNU Affero General Public License v3.0       *
#*   as published by the Free Software Foundation.                          *
#*                                                                          *
#****************************************************************************
import sys
import FreeCAD

__scriptVersion__ = 7.0
__pythonVersion__ = 3.10
__requiredFreeCADVersion__ = (0.21, None)  # (min, max) — None means no upper bound


def currentFreeCADVersion():
    data = FreeCAD.Version()
    # data[1] may contain '18' or '18.4'. In case of '18.4', just keep the '18' part
    return float(data[0] + '.' + (data[1][:data[1].index('.')] if '.' in data[1] else data[1]))


def checkCompatibility():
    '''InitGui -> Initialize()'''
    currentFCVersion = currentFreeCADVersion()
    currentPyVersion = float("{0}.{1}".format(sys.version_info[0], sys.version_info[1]))
    ok = True

    # Check Python version
    if currentPyVersion < __pythonVersion__:
        FreeCAD.Console.PrintError(
            "PCB Workbench: Error\n\t"
            "Python {0}+ is required. You are running {1}.\n"
            "\tPlease upgrade Python or use a newer FreeCAD build.\n"
            .format(__pythonVersion__, currentPyVersion)
        )
        ok = False

    # Check FreeCAD minimum version
    if currentFCVersion < __requiredFreeCADVersion__[0]:
        FreeCAD.Console.PrintError(
            "PCB Workbench: Error\n\t"
            "FreeCAD >= {0} is required. You are running {1}.\n"
            "\tPlease upgrade FreeCAD to continue.\n"
            .format(__requiredFreeCADVersion__[0], currentFCVersion)
        )
        ok = False

    # Check FreeCAD maximum version (if set)
    if __requiredFreeCADVersion__[1] is not None and currentFCVersion > __requiredFreeCADVersion__[1]:
        FreeCAD.Console.PrintWarning(
            "PCB Workbench: Warning\n\t"
            "FreeCAD {0} is newer than the tested maximum ({1}).\n"
            "\tThe workbench may not function correctly.\n"
            .format(currentFCVersion, __requiredFreeCADVersion__[1])
        )

    return [ok]


def setDefaultValues():
    ''' InitGui -> Initialize() '''
    data = {
        "scriptVersion": ['f', __scriptVersion__]
    }

    for i, j in data.items():
        if j[0] == 'f' and FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/PCB").GetFloat(i, 0.0) == 0.0:
            FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/PCB").SetFloat(i, float(j[1]))
