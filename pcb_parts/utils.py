# -*- coding: utf8 -*-
#****************************************************************************
#*                                                                          *
#*   Printed Circuit Board Workbench for FreeCAD             PCB            *
#*                                                                          *
#*   Copyright (c) 2013-2019                                                *
#*   marmni <marmni@onet.eu>                                                *
#*                                                                          *
#*                                                                          *
#*   This program is free software; you can redistribute it and/or modify   *
#*   it under the terms of the GNU Lesser General Public License (LGPL)     *
#*   as published by the Free Software Foundation; either version 2 of      *
#*   the License, or (at your option) any later version.                    *
#*   for detail see the LICENCE text file.                                  *
#*                                                                          *
#*   This program is distributed in the hope that it will be useful,        *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of         *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          *
#*   GNU Library General Public License for more details.                   *
#*                                                                          *
#*   You should have received a copy of the GNU Library General Public      *
#*   License along with this program; if not, write to the Free Software    *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307   *
#*   USA                                                                    *
#*                                                                          *
#****************************************************************************

import FreeCAD
import FreeCADGui
import Part
import os
import re
import builtins
import glob
import unicodedata
import ImportGui
from PySide6 import QtCore, QtGui, QtWidgets
#
from PCBdataBase import dataBase
from PCBconf import *
from PCBboard import getPCBheight
from PCBobjects import partObject, viewProviderPartObject, partObject_E, viewProviderPartObject_E, viewProviderPartObjectExternal
from PCBfunctions import wygenerujID, mathFunctions
from command.PCBgroups import *
from command.PCBannotations import createAnnotation

# SPDX-License-Identifier: AGPL-3.0-or-later
def partExistPath(filePos):
    #if filePos.startswith('/'):
        #filePos = filePos[1:]
    filePos = filePos.strip()
    #
    if FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/PCB").GetString("partsPaths", "").strip() != '':
        pathsToModels = partPaths + FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/PCB").GetString("partsPaths", "").split(',')
    else:
        pathsToModels = partPaths
    #
    if filePos.endswith((".igs", ".IGS", ".Igs", ".stp", "STEP", "step", "STP")):
        if len(glob.glob(filePos)):  # absolute path
            return [True, glob.glob(filePos)[0]]
        else:  # relative path - path def in partPaths (conf.py file)
            for i in pathsToModels:
                if i.strip() != '' and len(glob.glob(os.path.join(i.strip(), filePos))):
                    return [True, glob.glob(os.path.join(i, filePos))[0]]
            return [False, False]
    else:
        if len(glob.glob(filePos + ".[i,I]*")):  # absolute path
            return [True, glob.glob(filePos + ".[i,I]*")[0]]
        elif len(glob.glob(filePos + ".[s,S]*")):  # absolute path
            return [True, glob.glob(filePos + ".[s,S]*")[0]]
        else:  # relative path - path def in partPaths (conf.py file)
            for i in pathsToModels:
                if i.strip() != '':
                    if len(glob.glob(os.path.join(i, filePos) + ".[i,I]*")):
                        return [True, glob.glob(os.path.join(i, filePos) + ".[i,I]*")[0]]
                    elif len(glob.glob(os.path.join(i, filePos) + ".[s,S]*")):
                        return [True, glob.glob(os.path.join(i, filePos) + ".[s,S]*")[0]]
            return [False, False]
    #
    return [False, False]


def getExtensionInfo(info, name):
    if len(info)==9 and \
        isinstance(info[8], dict) and \
        name in info[8]:
        return info[8][name]
    return None

