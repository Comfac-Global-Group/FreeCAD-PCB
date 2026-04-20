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
import os


class modelPreviewMain(QtWidgets.QToolButton):
    def __init__(self, icon, tooltip, parent=None):
        iconDirectory = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../generateModels/data"), icon)
        #
        QtWidgets.QToolButton.__init__(self, parent)
        #
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.setToolTip(tooltip)
        self.setAutoFillBackground(True)
        self.setIcon(QtGui.QIcon(iconDirectory))  # 100x100px
        self.setText(tooltip)
        self.setStyleSheet("QToolButton {background-color: #b2babb; color: #FFFFFF; font-weight: bold; font-size: 10px;} QToolButton:hover:!pressed{border: 1px solid #808080; background-color: #e6e6e6; color: #000000} ")
        self.setIconSize(QtCore.QSize(120, 120))
        self.setFixedSize(QtCore.QSize(128, 128))


class modelGenerateGUIMain(QtWidgets.QWidget):
    def __init__(self, desc, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.errors = False
        #
        showMainWidget = flatButton(":/data/img/previous_16x16.png", "Back", self)
        self.connect(showMainWidget, QtCore.SIGNAL("clicked ()"), parent.showMainWidget)
        #
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)

        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine)
        line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        #
        self.mainFormLay = QtWidgets.QFormLayout()
        #
        self.modelName = QtWidgets.QLabel(desc)
        self.modelName.setStyleSheet("QLabel{font-weight:bold; font-size:15px} ")
        #
        self.errorsList = QtWidgets.QLabel("")
        self.errorsList.setStyleSheet("QLabel{font-weight:bold; font-size:11px; color:#FF0000} ")
        #
        self.mainLayout = QtWidgets.QGridLayout(self)
        self.mainLayout.addWidget(showMainWidget, 0, 0, 1, 1)
        self.mainLayout.addWidget(self.modelName, 0, 1, 1, 5, QtCore.Qt.AlignHCenter)
        self.mainLayout.addWidget(line, 1, 0, 1, 6)
        # ICON
        self.mainLayout.addItem(QtWidgets.QSpacerItem(1, 15), 3, 0, 1, 1)
        self.mainLayout.addLayout(self.mainFormLay, 4, 0, 1, 6)
        self.mainLayout.addItem(QtWidgets.QSpacerItem(1, 15), 5, 0, 1, 1)
        self.mainLayout.addWidget(line2, 6, 0, 1, 6)
        self.mainLayout.addWidget(self.errorsList, 7, 0, 1, 6)
        # errors
        self.mainLayout.setRowStretch(100, 100)
        self.mainLayout.setColumnStretch(5, 100)

    def addMainImageDim(self, icon):
        modelDim = modelPictureDim(icon, self)
        self.mainLayout.addWidget(modelDim, 2, 0, 1, 6, QtCore.Qt.AlignHCenter 	)


class modelPictureDim(QtWidgets.QLabel):
     def __init__(self, icon, parent=None):
        QtWidgets.QLabel.__init__(self, "")
        #
        iconDirectory = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../generateModels/data"), icon)
        #
        img = QtGui.QPixmap(iconDirectory)
        self.setPixmap(img)


class autVariable(QtWidgets.QDoubleSpinBox):
     def __init__(self, value=0.0, parent=None):
        QtWidgets.QDoubleSpinBox.__init__(self)
        self.setValue(value)
        #
        self.setSuffix("mm")
        self.setDisabled(True)


class flatButton(QtWidgets.QPushButton):
    def __init__(self, icon, tooltip, parent=None):
        QtWidgets.QPushButton.__init__(self, QtGui.QIcon(icon), "", parent)
        #
        self.setToolTip(tooltip)
        self.setFlat(True)
        self.setStyleSheet("QPushButton:hover:!pressed{border: 1px solid #808080;} ")
        self.setIconSize(QtCore.QSize(32, 32))
        self.setFixedSize(QtCore.QSize(32, 32))





