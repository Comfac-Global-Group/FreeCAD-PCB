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
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide6 import QtCore, QtGui, QtWidgets
#
import re
from functools import partial
#
import PCBrc
from PCBobjects import *
from PCBboard import getPCBheight
from PCBpartManaging import partsManaging
from PCBdataBase import dataBase
from command.PCBassignModel import dodajElement
from command.PCBexplode import *
from command.PCBexport import exportPCB_Gui
from command.PCBexportBOM import exportBOM_Gui, createCentroid_Gui
from command.PCBexportHoles import exportHoles_Gui, exportHolesReport_Gui
from command.PCBexportDrillingMap import exportDrillingMap_Gui
from command.PCBgroups import *
from command.PCBupdateParts import updateParts
from command.PCBDownload import downloadModelW
from command.PCBaddModel import addModel
from command.PCBcreateBoard import createPCB
from command.PCBlayers import layersSettings
from command.PCBannotations import createAnnotation_Gui, PCBannotation, viewProviderPCBannotation
from command.PCBexportKerkythea import exportToKerkytheaGui
from command.PCBexportPovRay import exportObjectToPovRayGui
from command.PCBboundingBox import boundingBox, boundingBoxFromSelection
from command.PCBglue import createGlueGui
from command.PCBassembly import createAssemblyGui, updateAssembly, exportAssemblyAll, exportAssemblySel, exportAssemblyPCB
from command.PCBdrill import createDrillcenter_Gui
from command.PCBcollision import checkCollisionsGuiALL, checkCollisionsGuiPCB
from command.PCBconstraintAreas import createConstraintArea
from command.PCBsections import createSectionsGui
from command.PCBgenerateModel import generateModelGui
from command.PCBcreateSimplifiedModel import createSimplifiedModel

# SPDX-License-Identifier: AGPL-3.0-or-later
import os
class pcbToolBarMain(QtWidgets.QToolBar):
    def __init__(self, text, parent=None):
        QtWidgets.QToolBar.__init__(self, text, parent)
        self.setVisible(False)
        self.toggleViewAction().setVisible(False)
        
    def show(self):
        self.draftWidget.setVisible(True)
        self.setVisible(True)

    def hide(self):
        self.draftWidget.setVisible(False)
        self.setVisible(True)

    def Activated(self):
        self.setVisible(True)
        self.toggleViewAction().setVisible(True)

    def Deactivated(self):
        self.setVisible(False)
        self.toggleViewAction().setVisible(False)
        
    def createAction(self, text, tooltip, icon):
        action = QtGui.QAction(text, self)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        action.setIcon(QtGui.QIcon(icon))
        #action.setIcon(QtGui.QIcon(__currentPath__ + "/data/img/" + icon))
        return action
        
    #def getMainWindow(self):
        #toplevel = QtGui.qApp.topLevelWidgets()
        #for i in toplevel:
            #if i.metaObject().className() == "Gui::MainWindow":
                #return i
                
    def addToolBar(self, toolBar):
        self.mainWindow = FreeCADGui.getMainWindow()
        self.mainWindow.addToolBar(QtCore.Qt.TopToolBarArea, toolBar)


