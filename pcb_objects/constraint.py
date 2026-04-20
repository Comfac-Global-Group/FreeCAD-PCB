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
class constraintAreaObject:
    def __init__(self, obj, typeL):
        self.Type = typeL
        self.pcbHeight = 1.5
        
        obj.addProperty("App::PropertyLength", "Height", "Base", "Height of the element").Height = 0.5
        obj.addProperty("App::PropertyLink", "Base", "Draft", "The base object is the wire is formed from 2 objects")
        obj.setEditorMode("Placement", 2)
        
        if self.Type in ['tRestrict', 'bRestrict', 'vRestrict', 'vRouteOutline', 'vPlaceOutline']:
            obj.setEditorMode("Height", 1)
        
        obj.Proxy = self
    
    def updatePosition_Z(self, fp, thickness):
        self.pcbHeight = thickness
        
        if self.Type.startswith('t'):  # top side
            fp.Base.Placement.Base.z = self.pcbHeight
            
            fp.recompute()
            fp.Base.recompute()
            fp.purgeTouched()
            fp.Base.purgeTouched()
        elif self.Type.startswith('v'):  # top and bottom side
            fp.Base.Placement.Base.z = -0.5
            self.execute(fp)
            
            fp.recompute()
            fp.Base.recompute()
            fp.purgeTouched()
            fp.Base.purgeTouched()
        else:  # bottomSide
            fp.Base.Placement.Base.z = 0
 
    def execute(self, fp):
        try:
            if fp.Base:
                if fp.Base.isDerivedFrom("Sketcher::SketchObject"):
                    if fp.Base.Support != None:
                        fp.Base.Support = None
                    
                    d = OpenSCAD2Dgeom.edgestofaces(fp.Base.Shape.Edges)
                    if self.Type.startswith('b'):
                        d = d.extrude(FreeCAD.Base.Vector(0, 0, -fp.Height))
                    elif self.Type.startswith('v'):
                        d = d.extrude(FreeCAD.Base.Vector(0, 0, self.pcbHeight + 1))
                    else:
                        d = d.extrude(FreeCAD.Base.Vector(0, 0, fp.Height))
                    
                    fp.Shape = d
                    
                    fp.recompute()
                    fp.Base.recompute()
                    fp.purgeTouched()
                    fp.Base.purgeTouched()
        except:
            pass

    def onChanged(self, fp, prop):
        if prop in ["Base"]:
            self.execute(fp)
        elif prop == "Height" and fp.Height.Value > 0:
            self.execute(fp)

    def __getstate__(self):
        return [self.Type, self.pcbHeight]

    def __setstate__(self, state):
        self.loads(state)

    def dumps(self):
        return [self.Type, self.pcbHeight]

    def loads(self, state):
        self.Type = state[0]
        self.pcbHeight = state[1]


class viewProviderConstraintAreaObject:
    def __init__(self, obj):
        ''' Set this object to the proxy object of the actual view provider '''
        obj.Proxy = self

    def attach(self, obj):
        ''' Setup the scene sub-graph of the view provider, this method is mandatory '''
        self.Object = obj.Object
    
    def claimChildren(self):
        return [self.Object.Base]

    def updateData(self, fp, prop):
        ''' If a property of the handled feature has changed we have the chance to handle this here '''
        return

    def getDisplayModes(self, obj):
        ''' Return a list of display modes. '''
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        ''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
        return "Shaded"

    def setDisplayMode(self, mode):
        ''' Map the display mode defined in attach with those defined in getDisplayModes.
        Since they have the same names nothing needs to be done. This method is optional.
        '''
        return mode

    def onChanged(self, vp, prop):
        ''' Print the name of the property that has changed '''
        vp.setEditorMode("LineColor", 2)
        vp.setEditorMode("DrawStyle", 2)
        vp.setEditorMode("LineWidth", 2)
        vp.setEditorMode("PointColor", 2)
        vp.setEditorMode("PointSize", 2)
        vp.setEditorMode("Deviation", 2)
        vp.setEditorMode("Lighting", 2)
        vp.setEditorMode("BoundingBox", 2)
        if hasattr(vp, "AngularDeflection"):
            vp.setEditorMode("AngularDeflection", 2)

    def getIcon(self):
        ''' Return the icon in XMP format which will appear in the tree view. This method is optional
        and if not defined a default icon is shown.
        '''
        return ":/data/img/constraintsArea.png"

    def __getstate__(self):
        ''' When saving the document this object gets stored using Python's cPickle module.
        Since we have some un-pickable here -- the Coin stuff -- we must define this method
        to return a tuple of all pickable objects or None.
        '''
        return None

    def __setstate__(self, state):
        ''' When restoring the pickled object from document we have the chance to set some
        internals here. Since no data were pickled nothing needs to be done here.
        '''
        return None

    def dumps(self):
        ''' When saving the document this object gets stored using Python's cPickle module.
        Since we have some un-pickable here -- the Coin stuff -- we must define this method
        to return a tuple of all pickable objects or None.
        '''
        return None

    def loads(self, state):
        ''' When restoring the pickled object from document we have the chance to set some
        internals here. Since no data were pickled nothing needs to be done here.
        '''
        return None


#####################################
#####################################
#####################################

