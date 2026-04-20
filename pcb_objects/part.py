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

#####################################
#####################################
#####################################
#####################################
#####################################
#####################################
objectSides = ["TOP", "BOTTOM"]
class partsObject(mathFunctions):
    def __init__(self, obj, typeL):
        self.Type = typeL
        self.oldX = None
        self.oldY = None
        self.oldZ = None
        self.oldROT = 0
        self.offsetZ = 0
        
        #obj.addExtension('App::OriginGroupExtensionPython', self)
        
        obj.addProperty("App::PropertyString", "Package", "PCB", "Package").Package = ""
        obj.addProperty("App::PropertyEnumeration", "Side", "PCB", "Side").Side = 0
        obj.addProperty("App::PropertyDistance", "X", "PCB", "X").X = 0
        obj.addProperty("App::PropertyDistance", "Y", "PCB", "Y").Y = 0
        obj.addProperty("App::PropertyDistance", "Socket", "PCB", "Socket").Socket = 0
        obj.addProperty("App::PropertyAngle", "Rot", "PCB", "Rot").Rot = 0
        obj.addProperty("App::PropertyBool", "KeepPosition", "PCB", "KeepPosition").KeepPosition = False
        # obj.addProperty("App::PropertyString", "Value", "PCB", "Value").Value = ""
        # obj.addProperty("App::PropertyLinkSub", "Thickness", "Part", "Reference to volume of part").Thickness = (FreeCAD.ActiveDocument.Board, 'Thickness')
        
        obj.addProperty("App::PropertyLink", "PartName", "Base", "PartName").PartName = None
        obj.addProperty("App::PropertyLink", "PartValue", "Base", "PartValue").PartValue = None
        # obj.addProperty("App::PropertyLink", "Socket", "Base", "Socket").Socket = None
        
        obj.setEditorMode("Package", 1)
        obj.setEditorMode("Placement", 2)
        obj.setEditorMode("Label", 2)
        obj.setEditorMode("PartName", 1)
        obj.setEditorMode("PartValue", 1)
        #
        obj.Side = objectSides
        obj.Proxy = self
        self.Object = obj
    
    def onChanged(self, fp, prop):
        fp.setEditorMode("Placement", 2)
        fp.setEditorMode("Label", 2)
        fp.setEditorMode("PartName", 1)
        fp.setEditorMode("PartValue", 1)
        fp.setEditorMode("Package", 1)

    def updatePosition_Z(self, fp, thickness, forceUpdate=False):
        try:
            if fp.Side == objectSides[0]:  # TOP
                fp.Placement.Base.z = thickness + self.offsetZ + fp.Socket.Value
            elif fp.Side == objectSides[1] and forceUpdate:
                fp.Placement.Base.z = -self.offsetZ - fp.Socket.Value
        except:
            pass
    
    def rotateZ(self, fp):
        shape = fp.Shape.copy()
        shape.Placement = fp.Placement

        if fp.Side == "TOP":  # TOP
            shape.rotate((fp.X.Value, fp.Y.Value, 0), (0.0, 0.0, 1.0), fp.Rot.Value - self.oldROT)
        else:  # BOTTOM
            shape.rotate((fp.X.Value, fp.Y.Value, 0), (0.0, 0.0, 1.0), -(fp.Rot.Value - self.oldROT))
        
        fp.Placement = shape.Placement
        self.oldROT = fp.Rot.Value
    
    def changeSide(self, fp):
        shape = fp.Shape.copy()
        shape.Placement = fp.Placement
        shape.rotate((fp.X.Value, fp.Y.Value, 0), (0.0, 1.0, 0.0), 180)
        
        fp.Placement = shape.Placement
        self.oldROT = fp.Rot.Value

    def execute(self, fp):
        pass

    def __getstate__(self):
        return [self.Type, self.oldROT, self.oldX, self.oldY, self.offsetZ, self.oldZ]

    def __setstate__(self, state):
        self.loads(state)

    def dumps(self):
        return [self.Type, self.oldROT, self.oldX, self.oldY, self.offsetZ, self.oldZ]

    def loads(self, state):
        if state:
            self.Type = state[0]
            self.oldROT = state[1]
            self.oldX = state[2]
            self.oldY = state[3]
            self.offsetZ = state[4]
            self.oldZ = state[5]


class partObject(partsObject):
    def __init__(self, obj):
        partsObject.__init__(self, obj, "PCBpart")

    def onChanged(self, fp, prop):
        fp.setEditorMode("Placement", 2)
        fp.setEditorMode("Label", 2)
        fp.setEditorMode("PartName", 1)
        fp.setEditorMode("PartValue", 1)
        fp.setEditorMode("Package", 1)
        ################################################################
        if self.oldZ == None:
            self.oldZ = fp.Socket.Value
        ################################################################
        if prop in ['X', 'Y', 'Socket', 'Rot', 'Side']:
            for i in fp.OutList:
                if prop == 'X':
                    try:
                        i.X.Value = i.X.Value + (fp.X.Value - self.oldX)
                    except:
                        pass
                elif prop == 'Y':
                    try:
                        i.Y.Value = i.Y.Value + (fp.Y.Value - self.oldY)
                    except:
                        pass
                elif prop == 'Socket':
                    try:
                        i.Z.Value = i.Z.Value + (fp.Socket.Value - self.oldZ)
                    except:
                        pass
                elif prop == 'Rot':
                    if hasattr(fp, "Side"):
                        if fp.Side == "TOP":  # TOP
                            i.Rot.Value = i.Rot.Value + (fp.Rot.Value - self.oldROT)
                            [x, y] = self.obrocPunkt2([i.X.Value, i.Y.Value], [fp.X.Value, fp.Y.Value], fp.Rot.Value - self.oldROT)
                        else:  # BOTTOM
                            i.Rot.Value = i.Rot.Value + (fp.Rot.Value - self.oldROT)
                            [x, y] = self.obrocPunkt2([i.X.Value, i.Y.Value], [fp.X.Value, fp.Y.Value], -(fp.Rot.Value - self.oldROT))
                        
                        i.X.Value = x
                        i.Y.Value = y
                elif prop == 'Side':
                    if hasattr(i, "Side"):
                        if i.Side == "TOP":
                            i.Side = "BOTTOM"
                        else:
                            i.Side = "TOP"
                        
                        i.X.Value = self.odbijWspolrzedne(i.X.Value, fp.X.Value)  # mirror i.X.Value by Y axis
        ################################################################
        try:
            if prop == "Rot":
                self.rotateZ(fp)
            elif prop == "Side":
                self.changeSide(fp)
                # Draft.rotate([fp], 180, FreeCAD.Vector(fp.X.Value, fp.Y.Value, 0), axis=FreeCAD.Vector(0.0, 1.0, 0.0), copy=False)
                self.updatePosition_Z(fp, getPCBheight()[1], True)
                self.rotateZ(fp)
            elif prop == "Label":
                try:
                    fp.PartName.Proxy.react = False
                    fp.PartName.String = fp.Label
                    fp.PartName.Proxy.react = True
                except:
                    pass
            elif prop == "X":
                if self.oldX == None:
                    self.oldX = fp.X.Value
                
                fp.Placement.Base.x += fp.X.Value - self.oldX
                self.oldX = fp.X.Value
            elif prop == "Y":
                if self.oldY == None:
                    self.oldY = fp.Y.Value
                
                fp.Placement.Base.y += fp.Y.Value - self.oldY
                self.oldY = fp.Y.Value
            elif prop == "Socket":
                self.updatePosition_Z(fp, getPCBheight()[1], True)
                self.oldZ = fp.Socket.Value
        except Exception as e:
            # FreeCAD.Console.PrintWarning("3. {0}\n".format(e))
            pass


class partObject_E(partsObject):
    def __init__(self, obj):
        partsObject.__init__(self, obj, "PCBpart_E")
        obj.setEditorMode("Placement", 2)
        obj.setEditorMode("Package", 1)
        obj.setEditorMode("Side", 1)
        obj.setEditorMode("X", 1)
        obj.setEditorMode("Y", 1)
        obj.setEditorMode("Rot", 1)
        obj.setEditorMode("Label", 2)
        obj.setEditorMode("Socket", 1)
    
    def onChanged(self, fp, prop):
        fp.setEditorMode("Placement", 2)
        fp.setEditorMode("Package", 1)
        fp.setEditorMode("Side", 1)
        fp.setEditorMode("X", 1)
        fp.setEditorMode("Y", 1)
        fp.setEditorMode("Rot", 1)
        fp.setEditorMode("Label", 2)
        fp.setEditorMode("Socket", 1)
        fp.setEditorMode("Label", 2)
        fp.setEditorMode("PartName", 1)
        fp.setEditorMode("PartValue", 1)
        fp.setEditorMode("Package", 1)
        #######
        if prop in ['Rot']:
            for i in fp.OutList:
                if prop == 'Rot':
                    if hasattr(fp, "Side"):
                        if fp.Side == "TOP":  # TOP
                            i.Rot.Value = i.Rot.Value + (fp.Rot.Value - self.oldROT)
                            [x, y] = self.obrocPunkt2([i.X.Value, i.Y.Value], [fp.X.Value, fp.Y.Value], fp.Rot.Value - self.oldROT)
                        else:  # BOTTOM
                            i.Rot.Value = i.Rot.Value + (fp.Rot.Value - self.oldROT)
                            [x, y] = self.obrocPunkt2([i.X.Value, i.Y.Value], [fp.X.Value, fp.Y.Value], -(fp.Rot.Value - self.oldROT))
                        
                        i.X.Value = x
                        i.Y.Value = y
        #
        try:
            if prop == "Label":
                try:
                    fp.PartName.Proxy.react = False
                    fp.PartName.String = fp.Label
                    fp.PartName.Proxy.react = True
                except:
                    pass
        except:
            pass


class viewProviderPartObject:
    def __init__(self, obj):
        ''' Set this object to the proxy object of the actual view provider '''
        #obj.addExtension("Gui::ViewProviderOriginGroupExtensionPython", self)
        obj.Proxy = self
        self.Object = obj.Object
    
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

    def attach(self, obj):
        ''' Setup the scene sub-graph of the view provider, this method is mandatory '''
        self.Object = obj.Object
    
    def claimChildren(self):
        try:
            return [self.Object.PartName, self.Object.PartValue]
        except AttributeError:
            return []

    def updateData(self, fp, prop):
        ''' If a property of the handled feature has changed we have the chance to handle this here '''
        return

    def getDisplayModes(self, obj):
        ''' Return a list of display modes. '''
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        ''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
        return "Flat Lines"

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
        vp.setEditorMode("ShapeColor", 2)
        if hasattr(vp, "AngularDeflection"):
            vp.setEditorMode("AngularDeflection", 2)
        #vp.setEditorMode("Side", 1)
        #vp.setEditorMode("X", 1)
        #vp.setEditorMode("Y", 1)
        #vp.setEditorMode("Rot", 1)
        
        #if prop == "ShowHeight":
            #self.heightDisplay(vp, vp.ShowHeight)

    def getIcon(self):
        ''' Return the icon in XMP format which will appear in the tree view. This method is optional
        and if not defined a default icon is shown.
        '''
        return ":/data/img/modelOK.svg"


class viewProviderPartObjectExternal(viewProviderPartObject):
    def __init__(self, obj):
        ''' Set this object to the proxy object of the actual view provider '''
        viewProviderPartObject.__init__(self, obj)

    def getIcon(self):
        ''' Return the icon in XMP format which will appear in the tree view. This method is optional
        and if not defined a default icon is shown.
        '''
        return ":/data/img/updateModels.png"


class viewProviderPartObject_E:
    def __init__(self, obj):
        ''' Set this object to the proxy object of the actual view provider '''
        obj.Proxy = self
        self.Object = obj.Object
    
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

    def attach(self, obj):
        ''' Setup the scene sub-graph of the view provider, this method is mandatory '''
        self.Object = obj.Object
    
    def claimChildren(self):
        try:
            return [self.Object.PartName, self.Object.PartValue]
        except AttributeError:
            return []
        
    def updateData(self, fp, prop):
        ''' If a property of the handled feature has changed we have the chance to handle this here '''
        return

    def getDisplayModes(self, obj):
        ''' Return a list of display modes. '''
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        ''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
        return "Flat Lines"

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
        # vp.setEditorMode("BoundingBox", 2)
        vp.setEditorMode("ShapeColor", 2)
        if hasattr(vp, "AngularDeflection"):
            vp.setEditorMode("AngularDeflection", 2)

    def getIcon(self):
        ''' Return the icon in XMP format which will appear in the tree view. This method is optional
        and if not defined a default icon is shown.
        '''
        return ":/data/img/modelNOK.svg"
        
#####################################
#####################################
#####################################

