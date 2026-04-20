# -*- coding: utf8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
#****************************************************************************
#*                                                                          *
#*   Printed Circuit Board Workbench for FreeCAD             PCB            *
#*                                                                          *
#*   Copyright (c) 2013-2019                                                *
#*   marmni <marmni@onet.eu>
#*                                                                          *
#*   Copyright (c) 2026                                                     *
#*   Comfac-Global-Group (CGG R&D)                                          *                                                *
#*                                                                          *
#*                                                                          *
#*   This program is free software; you can redistribute it and/or modify   *
#*   it under the terms of the GNU Affero General Public License (AGPL)     *
#*   as published by the Free Software Foundation; either version 3 of      *
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
from PySide6 import QtCore, QtGui, QtWidgets
from PCBmainModule import modelPreviewMain, modelGenerateGUIMain, modelPictureDim, autVariable

__fcstdFile__ = "diodeSmdSodMelf.FCStd"
__desc__ = "SOD/MELF"


class modelPreview(modelPreviewMain):
     def __init__(self, parent=None):
        modelPreviewMain.__init__(self, "diodeSmdSodMelf.png", __desc__, parent)
    

class modelGenerateGUI(modelGenerateGUIMain):
    def __init__(self, parent=None):
        modelGenerateGUIMain.__init__(self, __desc__, parent)
        #
        self.diameter = QtWidgets.QDoubleSpinBox()
        self.diameter.setValue(1.1)
        self.diameter.setMinimum(0.5)
        self.diameter.setSingleStep(0.5)
        self.diameter.setSuffix("mm")
        #
        self.totalLen = autVariable()
        #
        self.len_1 = QtWidgets.QDoubleSpinBox()
        self.len_1.setValue(0.4)
        self.len_1.setSuffix("mm")
        self.len_1.setMinimum(0.2)
        self.len_1.setSingleStep(0.2)
        self.connect(self.len_1, QtCore.SIGNAL("valueChanged (double)"), self.updateTotalLen)
        #
        self.len_2 = QtWidgets.QDoubleSpinBox()
        self.len_2.setMinimum(0.5)
        self.len_2.setSuffix("mm")
        self.len_2.setSingleStep(0.5)
        self.connect(self.len_2, QtCore.SIGNAL("valueChanged (double)"), self.updateTotalLen)
        self.len_2.setValue(1.2)
        #
        self.addMainImageDim("diodeSmdSodMelfDim.png")
        self.mainFormLay.addRow(QtWidgets.QLabel("d"), self.diameter)
        self.mainFormLay.addRow(QtWidgets.QLabel("k"), self.len_1)
        self.mainFormLay.addRow(QtWidgets.QLabel("l"), self.len_2)
        self.mainFormLay.addRow(QtWidgets.QLabel("l1 = l + k * 2      "), self.totalLen)
    
    def updateTotalLen(self, dummy):
        try:
            self.totalLen.setValue(round(self.len_1.value() * 2. + self.len_2.value(), 2))
        except Exception as e:
            FreeCAD.Console.PrintError(str(e) + "\n")
def modelGenerate(doc, widget):
    doc.Spreadsheet.set('B1', str(widget.len_1.value()))
    doc.Spreadsheet.set('B2', str(widget.diameter.value()))
    doc.Spreadsheet.set('B3', str(widget.len_2.value()))
    doc.recompute()
