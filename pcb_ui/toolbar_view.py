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
from pcb_ui.toolbar_main import pcbToolBarMain

__currentPath__ = os.path.abspath(os.path.join(os.path.dirname(__file__), ''))

class pcbToolBarView(pcbToolBarMain):
    def __init__(self, parent=None):
        pcbToolBarMain.__init__(self, 'PCB View', parent)
        self.setObjectName("pcbToolBarView")
        
        # przyciski
        scriptCmd_viewShaded = self.createAction(u"Display mode: Shaded", u"Display mode: Shaded", ":/data/img/displayShaded.png")
        par = partial(self.changeDisplayMode, 'Shaded')
        QtCore.QObject.connect(scriptCmd_viewShaded, QtCore.SIGNAL("triggered()"), par)
        
        scriptCmd_viewFlatLines = self.createAction(u"Display mode: Shaded with Edges", u"Display mode: Shaded with Edges", ":/data/img/displayFlatLines.png")
        par = partial(self.changeDisplayMode, 'Flat Lines')
        QtCore.QObject.connect(scriptCmd_viewFlatLines, QtCore.SIGNAL("triggered()"), par)
        
        scriptCmd_viewWireframe = self.createAction(u"Display mode: Wireframe", u"Display mode: Wireframe", ":/data/img/displayWrireFrame.png")
        par = partial(self.changeDisplayMode, 'Wireframe')
        QtCore.QObject.connect(scriptCmd_viewWireframe, QtCore.SIGNAL("triggered()"), par)
        
        scriptCmd_viewInternalView = self.createAction(u"Display mode: Internal View", u"Display mode: Internal View", ":/data/img/displayInternalView.png")
        par = partial(self.changeDisplayMode, 'Internal View')
        QtCore.QObject.connect(scriptCmd_viewInternalView, QtCore.SIGNAL("triggered()"), par)

        scriptCmd_Layers = self.createAction(u"Layers settings", u"Layers settings", ":/data/img/layers_TI.svg")
        QtCore.QObject.connect(scriptCmd_Layers, QtCore.SIGNAL("triggered()"), self.Flayers)
        # Cut to board outline
        scriptCmd_cutToBoardOutlineON = self.createAction(u"Cut to board outline - ON", u"Cut to board outline ON", ":/data/img/cutToBoard.svg")
        QtCore.QObject.connect(scriptCmd_cutToBoardOutlineON, QtCore.SIGNAL("triggered()"), partial(self.cutToBoardOutline, True))
        
        scriptCmd_cutToBoardOutlineON2 = self.createAction(u"Cut to board outline - ON", u"Cut to board outline ON", ":/data/img/cutToBoard.svg")
        QtCore.QObject.connect(scriptCmd_cutToBoardOutlineON2, QtCore.SIGNAL("triggered()"), partial(self.cutToBoardOutline, True))
        
        scriptCmd_cutToBoardOutlineOFF = self.createAction(u"Cut to board outline - OFF", u"Cut to board outline ON", ":/data/img/cutToBoard.svg")
        QtCore.QObject.connect(scriptCmd_cutToBoardOutlineOFF, QtCore.SIGNAL("triggered()"), partial(self.cutToBoardOutline, False))
        
        groupsMenuCTB = QtWidgets.QMenu(self)
        groupsMenuCTB.addAction(scriptCmd_cutToBoardOutlineON2)
        groupsMenuCTB.addAction(scriptCmd_cutToBoardOutlineOFF)
        scriptCmd_cutToBoardOutlineON.setMenu(groupsMenuCTB)
        # show signals ON/OFF
        scriptCmd_showSignals = self.createAction(u"Show signals - ON", u"Show signals ON", ":/data/img/showSignalsON.png")
        QtCore.QObject.connect(scriptCmd_showSignals, QtCore.SIGNAL("triggered()"), partial(self.showSignals, True))
        
        scriptCmd_showSignals2 = self.createAction(u"Show signals - ON", u"Show signals ON", ":/data/img/showSignalsON.png")
        QtCore.QObject.connect(scriptCmd_showSignals2, QtCore.SIGNAL("triggered()"), partial(self.showSignals, True))
        
        scriptCmd_showSignalsOFF = self.createAction(u"Show signals - OFF", u"Show signals OFF", ":/data/img/showSignalsOFF.png")
        QtCore.QObject.connect(scriptCmd_showSignalsOFF, QtCore.SIGNAL("triggered()"), partial(self.showSignals, False))
        
        groupsMenuCTB = QtWidgets.QMenu(self)
        groupsMenuCTB.addAction(scriptCmd_showSignals2)
        groupsMenuCTB.addAction(scriptCmd_showSignalsOFF)
        scriptCmd_showSignals.setMenu(groupsMenuCTB)
        # Cut holes through all layers ON/OFF
        scriptCmd_cutHolesThroughAllLayersON = self.createAction(u"Cut holes through all layers - ON", u"Cut holes through all layers - ON", ":/data/img/layers_TI_Holes.svg")
        QtCore.QObject.connect(scriptCmd_cutHolesThroughAllLayersON, QtCore.SIGNAL("triggered()"), partial(self.cutHolesThroughAllLayers, True))
        
        scriptCmd_cutHolesThroughAllLayersON2 = self.createAction(u"Cut holes through all layers - ON", u"Cut holes through all layers - ON", ":/data/img/layers_TI_Holes.svg")
        QtCore.QObject.connect(scriptCmd_cutHolesThroughAllLayersON2, QtCore.SIGNAL("triggered()"), partial(self.cutHolesThroughAllLayers, True))
        
        scriptCmd_cutHolesThroughAllLayersOFF = self.createAction(u"Cut holes through all layers - OFF", u"Cut holes through all layers - OFF", ":/data/img/layers_TI.svg")
        QtCore.QObject.connect(scriptCmd_cutHolesThroughAllLayersOFF, QtCore.SIGNAL("triggered()"), partial(self.cutHolesThroughAllLayers, False))
        
        groupsMenuCH = QtWidgets.QMenu(self)
        groupsMenuCH.addAction(scriptCmd_cutHolesThroughAllLayersON2)
        groupsMenuCH.addAction(scriptCmd_cutHolesThroughAllLayersOFF)
        scriptCmd_cutHolesThroughAllLayersON.setMenu(groupsMenuCH)
        # rendering
        scriptCmd_ExportToKerkythea = self.createAction(u"3D rendering: export to Kerkythea", u"3D rendering: export to Kerkythea", ":/data/img/kticon.ico")
        QtCore.QObject.connect(scriptCmd_ExportToKerkythea, QtCore.SIGNAL("triggered()"), self.exportToKerkytheaF)
        
        scriptCmd_ExportObjectToPovRay = self.createAction(u"3D rendering: export object to POV-Ray (*.inc)", u"3D rendering: export object to POV-Ray (*.inc)", ":/data/img/povray.ico")
        QtCore.QObject.connect(scriptCmd_ExportObjectToPovRay, QtCore.SIGNAL("triggered()"), self.exportObjectToPovRayF)
        
        # assembly
        scriptCmd_QuickAssembly = self.createAction(u"Add assembly", u"Add assembly", ":/data/img/asmMain.png")
        QtCore.QObject.connect(scriptCmd_QuickAssembly, QtCore.SIGNAL("triggered()"), self.quickAssembly)
        
        scriptCmd_QuickAssembly2 = self.createAction(u"Update assembly", u"Update assembly", ":/data/img/asmUpdate.png")
        QtCore.QObject.connect(scriptCmd_QuickAssembly2, QtCore.SIGNAL("triggered()"), self.quickAssemblyUpdate)
        # collisions
        scriptCmd_CheckForCollisionsALL = self.createAction(u"Detect collisions between objects", u"Detect collisions between objects", ":/data/img/collisions.svg")
        QtCore.QObject.connect(scriptCmd_CheckForCollisionsALL, QtCore.SIGNAL("triggered()"), self.checkForCollisionsFALL)
        
        scriptCmd_CheckForCollisionsPCB = self.createAction(u"Detect collisions with PCB", u"Detect collisions with PCB", ":/data/img/collisions.svg")
        QtCore.QObject.connect(scriptCmd_CheckForCollisionsPCB, QtCore.SIGNAL("triggered()"), self.checkForCollisionsFPCB)
        
        groupsMenu = QtWidgets.QMenu(self)
        groupsMenu.addAction(scriptCmd_CheckForCollisionsALL)
        scriptCmd_CheckForCollisionsPCB.setMenu(groupsMenu)
        # parts groups
        scriptCmd_ungroupParts = self.createAction(u"Ungroup parts", u"Ungroup parts", ":/data/img/ungroup.svg")
        QtCore.QObject.connect(scriptCmd_ungroupParts, QtCore.SIGNAL("triggered()"), self.ungroupParts)
        
        scriptCmd_groupParts = self.createAction(u"Group parts", u"Group parts", ":/data/img/group.svg")
        QtCore.QObject.connect(scriptCmd_groupParts, QtCore.SIGNAL("triggered()"), self.groupParts)
        # instructions
        scriptCmd_openInstruction_0 = self.createAction(u"Open instruction (FC0.19 in progress)", u"Open instruction (FC0.19 in progress)", ":/data/img/info_16x16.png")
        QtCore.QObject.connect(scriptCmd_openInstruction_0, QtCore.SIGNAL("triggered()"), partial(self.openInstruction, "instruction_FC019_inProgress.pdf"))
        
        scriptCmd_openInstruction_1 = self.createAction(u"Open instruction (FC0.19 in progress)", u"Open instruction (FC0.19 in progress)", ":/data/img/info_16x16.png")
        QtCore.QObject.connect(scriptCmd_openInstruction_1, QtCore.SIGNAL("triggered()"), partial(self.openInstruction, "instruction_FC019_inProgress.pdf"))
        
        scriptCmd_openInstruction_2 = self.createAction(u"Open instruction (FC0.18)", u"Open instruction (FC0.18)", ":/data/img/info_16x16.png")
        QtCore.QObject.connect(scriptCmd_openInstruction_2, QtCore.SIGNAL("triggered()"), partial(self.openInstruction, "OLD/instruction_FC018_inProgress_DUMMY.pdf"))
        
        scriptCmd_openInstruction_3 = self.createAction(u"Open instruction (FC0.16)", u"Open instruction (FC0.16)", ":/data/img/info_16x16.png")
        QtCore.QObject.connect(scriptCmd_openInstruction_3, QtCore.SIGNAL("triggered()"), partial(self.openInstruction, "OLD/instruction_FC016.pdf"))
        
        groupsMenuI = QtWidgets.QMenu(self)
        groupsMenuI.addAction(scriptCmd_openInstruction_1)
        groupsMenuI.addAction(scriptCmd_openInstruction_2)
        groupsMenuI.addAction(scriptCmd_openInstruction_3)
        scriptCmd_openInstruction_0.setMenu(groupsMenuI)
        ##########
        self.addAction(scriptCmd_viewShaded)
        self.addAction(scriptCmd_viewFlatLines)
        self.addAction(scriptCmd_viewWireframe)
        self.addAction(scriptCmd_viewInternalView)
        self.addSeparator()
        self.addAction(scriptCmd_Layers)
        self.addSeparator()
        self.addAction(scriptCmd_cutHolesThroughAllLayersON)
        self.addAction(scriptCmd_cutToBoardOutlineON)
        self.addAction(scriptCmd_showSignals)
        self.addAction(scriptCmd_ungroupParts)
        self.addAction(scriptCmd_groupParts)
        self.addAction(scriptCmd_CheckForCollisionsPCB)
        self.addSeparator()
        self.addAction(scriptCmd_ExportToKerkythea)
        self.addAction(scriptCmd_ExportObjectToPovRay)
        self.addSeparator()
        self.addAction(scriptCmd_openInstruction_0)
        self.addAction(scriptCmd_QuickAssembly)
        self.addAction(scriptCmd_QuickAssembly2)
        self.addToolBar(self)
    
    def openInstruction(self, fileName):
        path = os.path.join(__currentPath__, "instructions", fileName)
        if os.path.isfile(path):
            os.startfile(path)
    
    def cutHolesThroughAllLayers(self, value):
        pcb = getPCBheight()
        if pcb[0]:  # board is available
            for i in pcb[2].Group:
                if hasattr(i, "Cut") and not i.Cut == value:
                    i.Cut = value
    
    def showSignals(self, value):
        pcb = getPCBheight()
        if pcb[0]:  # board is available
            colorsList = {}
            
            for i in pcb[2].Group:
                if hasattr(i, "Proxy") and hasattr(i.Proxy, "Type") and isinstance(i.Proxy.Type, list) and "paths" in i.Proxy.Type:
                    if value:
                        colorsList = i.Proxy.colorizePaths(i, colorsList)
                    else:
                        i.Proxy.resetColors(i)
    
    def cutToBoardOutline(self, value):
        pcb = getPCBheight()
        if pcb[0]:  # board is available
            for i in pcb[2].Group:
                if hasattr(i, "CutToBoard") and not i.CutToBoard == value:
                    i.CutToBoard = value
    
    def ungroupParts(self):
        pcb = getPCBheight()
        if pcb[0]:  # board is available
            groupsToDelete = []
            pM = partsManaging()
            
            for i in pcb[2].Group:
                if hasattr(i, "Proxy") and hasattr(i.Proxy, "Type") and i.Proxy.Type in ["PCBpart", "PCBpart_E"]:
                    if not i.getParentGroup().Name in groupsToDelete:
                        groupsToDelete.append(i.getParentGroup().Name)
                    
                    pM.addPartToGroup(False, i)
            
            for i in groupsToDelete:
                if i == "Parts":
                    continue
                
                try:
                    FreeCAD.ActiveDocument.removeObject(i)
                except Exception as e:
                    FreeCAD.Console.PrintWarning("{0} \n".format(e))

    def groupParts(self):
        pcb = getPCBheight()
        if pcb[0]:  # board is available
            pM = partsManaging()
            pM.setDatabase()
            
            for i in pcb[2].Group:
                if hasattr(i, "Proxy") and hasattr(i.Proxy, "Type") and i.Proxy.Type in ["PCBpart", "PCBpart_E"]:
                    pM.addPartToGroup(True, i)

    def quickAssembly(self):
        try:
            if FreeCAD.activeDocument():
                FreeCADGui.Control.showDialog(createAssemblyGui())
        except Exception as e:
            FreeCAD.Console.PrintWarning("{0} \n".format(e))
        
    def quickAssemblyUpdate(self):
        try:
            if FreeCAD.activeDocument():
                updateAssembly()
        except Exception as e:
            FreeCAD.Console.PrintWarning("{0} \n".format(e))
    
    def checkForCollisionsFALL(self):
        try:
            if FreeCAD.activeDocument():
                FreeCADGui.Control.showDialog(checkCollisionsGuiALL())
            else:
                FreeCAD.Console.PrintWarning("File does not exist or is empty\n")
        except Exception as e:
            FreeCAD.Console.PrintWarning("{0} \n".format(e))
    
    def checkForCollisionsFPCB(self):
        try:
            if FreeCAD.activeDocument() and getPCBheight()[0]:
                FreeCADGui.Control.showDialog(checkCollisionsGuiPCB())
            else:
                FreeCAD.Console.PrintWarning("File does not exist or is empty\n")
        except Exception as e:
            FreeCAD.Console.PrintWarning("{0} \n".format(e))
    
    def exportToKerkytheaF(self):
        if FreeCAD.activeDocument():
            FreeCADGui.Control.showDialog(exportToKerkytheaGui())
            
    def exportObjectToPovRayF(self):
        if FreeCAD.activeDocument():
            FreeCADGui.Control.showDialog(exportObjectToPovRayGui())
    
    def Flayers(self):
        pcb = getPCBheight()
        if FreeCAD.activeDocument() and pcb[0]:
            if not FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.showDialog(layersSettings())

    def changeDisplayMode(self, mode):
        hidePCB = False
        if mode == 'Internal View':
            mode = 'Shaded'
            hidePCB = True
        #
        try:
            obj = FreeCAD.ActiveDocument.Objects
        except:
            obj = []
        
        if len(obj):
            for i in obj:
                if mode in i.ViewObject.listDisplayModes():
                    #if hasattr(i, "Proxy") and hasattr(i, "Type") and type(i.Proxy.Type) == list:
                        #if 'tSilk' in i.Proxy.Type or 'bSilk' in i.Proxy.Type or 'tDocu' in i.Proxy.Type or 'bDocu' in i.Proxy.Type:
                            #continue
                    i.ViewObject.DisplayMode = mode
        #
        if hidePCB:
            try:
                FreeCAD.ActiveDocument.Board.ViewObject.DisplayMode = 'Wireframe'
            except Exception as e:
                pass


###########
