# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from mne_pipeline_hd.gui import main_window
from mne_pipeline_hd.pipeline_functions import ismac


def main():
    app_name = 'mne_pipeline_hd'
    organization_name = 'marsipu'
    app = QApplication.instance()
    if not app:
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

    mw = main_window.MainWindow()
    mw.center()
    mw.show()

    # For Spyder to make console accessible again
    app.lastWindowClosed.connect(app.quit)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
