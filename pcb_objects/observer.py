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
import Part
import Draft
from pivy.coin import *
from math import sqrt, atan2, degrees, sin, cos, radians, pi, hypot
try:
    import OpenSCAD2Dgeom
except:
    pass
from PySide6 import QtGui, QtWidgets
import unicodedata
import random
#
from PCBboard import cutToBoardShape, getPCBheight, PCBboardObject, viewProviderPCBboardObject
from PCBfunctions import mathFunctions
from PCBconf import *

# SPDX-License-Identifier: AGPL-3.0-or-later
class DocumentObserver:
    def slotDeletedObject(self, obj):
        if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "Type") and obj.Proxy.Type in ["PCBpart", "PCBpart_E"]:
            try:
                FreeCAD.ActiveDocument.removeObject(obj.PartName.Name)
            except:
                pass
            
            try:
                FreeCAD.ActiveDocument.removeObject(obj.PartValue.Name)
            except:
                pass


FreeCAD.addDocumentObserver(DocumentObserver())
