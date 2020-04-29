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
from PyQt5.QtWidgets import QApplication

from gui import main_window
from gui.qt_utils import ErrorDialog
from pipeline_functions import ismac

# import matplotlib
# if ismac:
#     matplotlib.use('macosx')


def main():
    app_name = 'mne_pipeline_hd'
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
        mw = main_window.MainWindow()
        mw.center()
        mw.show()
    except:
        traceback.print_exc()
        traceback_str = traceback.format_exc(limit=-10)
        exctype, value = sys.exc_info()[:2]
        ErrorDialog(None, (exctype, value, traceback_str))

    # Make Command-line Ctrl + C possible
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)

    # For Spyder to make console accessible again
    app.lastWindowClosed.connect(app.quit)
    sys.exit(app.exec_())



if __name__ == '__main__':
    main()
