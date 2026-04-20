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
class modelTypes(QtWidgets.QDialog):
    def __init__(self, modelName, paths, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle(u'Choose model')
        #
        self.modelsList = QtWidgets.QListWidget()
        for i in paths:
            item = QtWidgets.QListWidgetItem(i[0])
            item.setData(QtCore.Qt.UserRole, i[1])
            
            self.modelsList.addItem(item)
        
        self.modelsList.setCurrentRow(0)
        #
        buttons = QtGui.QDialogButtonBox()
        buttons.setOrientation(QtCore.Qt.Vertical)
        buttons.addButton("Cancel", QtGui.QDialogButtonBox.RejectRole)
        buttons.addButton("Choose", QtGui.QDialogButtonBox.AcceptRole)
        self.connect(buttons, QtCore.SIGNAL("accepted()"), self, QtCore.SLOT("accept()"))
        self.connect(buttons, QtCore.SIGNAL("rejected()"), self, QtCore.SLOT("reject()"))
        #
        lay = QtWidgets.QGridLayout(self)
        lay.addWidget(QtWidgets.QLabel(u"Choose one of available models for part:"), 0, 0, 1, 1)
        lay.addWidget(QtWidgets.QLabel(u"<div style='font-weight:bold;'>{0}</div>".format(modelName)), 1, 0, 1, 1, QtCore.Qt.AlignHCenter)
        lay.addWidget(self.modelsList, 2, 0, 1, 1)
        lay.addWidget(buttons, 2, 1, 1, 1)
