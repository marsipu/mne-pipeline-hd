# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data
Adapted by Martin Schulz from Lau Møller Andersen
@author: Martin Schulz
@email: martin.schulz@stud.uni-heidelberg.de
@github: marsipu/mne-pipeline-hd
"""
import sys

import matplotlib

from pipeline_functions import ismac

if ismac:
    matplotlib.use('MacOSX')

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from pipeline_functions import main_win

# Todo: Command-Line start not working
#   A line for commands, which can be used for real-time debugging and quick use of the local variables
app_name = 'mne-pipeline-hd'
organization_name = 'marsipu'
app = QApplication(sys.argv)
app.setApplicationName(app_name)
app.setOrganizationName(organization_name)
try:
    app.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
except AttributeError:
    print('pyqt-Version is < 5.12')
if ismac:
    app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
    # Workaround for MAC menu-bar-focusing issue
    app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)
win = main_win.MainWindow()
win.show()

# Make Command-line Ctrl + C possible
timer = QTimer()
timer.timeout.connect(lambda: None)
timer.start(100)

app.lastWindowClosed.connect(app.quit)
sys.exit(app.exec_())
