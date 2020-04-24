# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import sys
import traceback

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

from gui.qt_utils import ErrorDialog
from pipeline_functions import ismac
from gui import main_win

# import matplotlib
# if ismac:
#     matplotlib.use('macosx')

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

try:
    win = main_win.MainWindow()
    win.show()
    win.center()
    win.raise_win()
except:
    traceback.print_exc()
    traceback_str = traceback.format_exc(limit=-10)
    exctype, value = sys.exc_info()[:2]
    err_dlg = ErrorDialog(None, (exctype, value, traceback_str))

# Make Command-line Ctrl + C possible
timer = QTimer()
timer.timeout.connect(lambda: None)
timer.start(100)

# For Spyder to make console accessible again
app.lastWindowClosed.connect(app.quit)
sys.exit(app.exec_())
