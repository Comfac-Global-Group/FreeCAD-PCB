# -*- coding: utf8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
#****************************************************************************
#*                                                                          *
#*   Printed Circuit Board Workbench for FreeCAD             PCB            *
#*   Flexible Printed Circuit Board Workbench for FreeCAD    FPCB           *
#*   Copyright (c) 2013, 2014                                               *
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

# vim:set ts=2 sw=2 sts=2 et:
from rzn.api import Plugin
import os
import glob
import configparser


__currentPath__ = os.path.dirname(os.path.abspath(__file__))


class FreeCADExportPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self, "FreeCAD", Plugin.EXPORT)
        
        self.config = configparser.RawConfigParser()
        self.config.read(os.path.join(__currentPath__, "conf.cfg"))
        
    def main(self, ui):
        self.batchMain(ui.currentTab().project(), {})
        
    def batchMain(self, proj, options):
        systemUzytkownika = os.name
        plikRZP = glob.glob(os.path.join(proj.filename(), "*.rzp"))[0]
        
        if plikRZP:
            if systemUzytkownika == "nt":
                os.popen("cmd.exe /c START \"\" \"\"{0}\"\" \"\"{1}\"\" &".format(self.config.get('option', 'programPath_WIN'), plikRZP))
            elif systemUzytkownika == "posix":
                os.popen("\"{0}\" \"{1}\" &".format(self.config.get('option', 'programPath_LIN'), plikRZP))
            else:
                print('Operating system not recognized.')
        else:
            print('File path issue, incorrect path: `{0}`'.format(proj.filename()))
