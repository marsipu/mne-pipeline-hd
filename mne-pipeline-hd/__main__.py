# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data
Adapted from Lau Møller Andersen
@author: Martin Schulz
@email: martin.schulz@stud.uni-heidelberg.de
@github: marsipu/mne-pipeline-hd
Adapted to Melody Processing of Kim's data
"""
import sys

import matplotlib

from pipeline_functions import ismac

if ismac:
    matplotlib.use('MacOSX')

from importlib import reload

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from basic_functions import io, operations as op, plot as plot
from custom_functions import kristin as kf, melofix as mff, pinprick as ppf
from pipeline_functions import decorators as decor, main_win, subjects as subs, utilities as ut
from resources import operations_dict as opd


def reload_all():
    reload(io)
    reload(op)
    reload(plot)
    reload(subs)
    reload(ut)
    reload(opd)
    reload(decor)
    reload(main_win)
    reload(ppf)
    reload(mff)
    reload(kf)


reload_all()

# %%============================================================================
# WHICH SUBJECT? (TO SET)
# ==============================================================================
# Which File do you want to run?
# Type in the LINE of the filename in your file_list.py
# Examples:
# '5' (One File)
# '1,7,28' (Several Files)
# '1-5' (From File x to File y)
# '1-4,7,20-26' (The last two combined)
# '1-20,!4-6' (1-20 except 4-6)
# 'all' (All files in file_list.py)
# 'all,!4-6' (All files except 4-6)which
# %%============================================================================
# GUI CALL
# ==============================================================================
# Todo: Call functions from an own module and let the Main-Window stay open while execution
#   Needed: Controller, who takes gui-input (as project-name, paths) and initilializes the project,
#   then a function, which is called on Start which calls the appropriate pipeline-functions
#   plus a line for commands, which can be used for real-time debugging and quick use of the local variables
app_name = 'mne-pipeline-hd'
organization_name = 'marsipu'
app = QApplication(sys.argv)
app.setApplicationName(app_name)
app.setOrganizationName(organization_name)
app.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
if ismac:
    app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
    app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)
win = main_win.MainWindow()
win.show()

# Make Command-line Ctrl + C possible
timer = QTimer()
timer.timeout.connect(lambda: None)
timer.start(100)

# # In Pycharm not working but needed for Spyder
app.lastWindowClosed.connect(app.quit)
app.exec_()
print('Finished')
