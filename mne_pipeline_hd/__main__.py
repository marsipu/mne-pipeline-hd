# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
Copyright © 2011-2019, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import sys
from inspect import getsourcefile
from os.path import abspath
from pathlib import Path

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication

# Enable start also when not installed via pip (e.g. for development)
# Get the package_path and add it, should work across platforms and in spyder
package_parent = str(Path(abspath(getsourcefile(lambda: 0))).parent.parent)
if package_parent not in sys.path:
    sys.path.insert(0, package_parent)

from mne_pipeline_hd.gui import main_window
from mne_pipeline_hd.gui.gui_utils import StderrStream, StdoutStream
from mne_pipeline_hd.pipeline_functions import ismac


def main():
    app_name = 'mne_pipeline_hd'
    organization_name = 'marsipu'
    domain_name = 'https://github.com/marsipu/mne_pipeline_hd'

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setApplicationName(app_name)
    app.setOrganizationName(organization_name)
    app.setOrganizationDomain(domain_name)

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
    mw.raise_win()

    # Redirect stdout to capture it later in GUI
    sys.stdout = StdoutStream()
    # Redirect stderr to capture the output by tdqm
    sys.stderr = StderrStream()

    # Command-Line interrupt with Ctrl+C possible
    timer = QTimer()
    timer.timeout.connect(lambda: mw)
    timer.start(500)

    # For Spyder to make console accessible again
    app.lastWindowClosed.connect(app.quit)

    sys.exit(app.exec())


if __name__ == '__main__':
    # Todo: Make Exception-Handling for PyQt-Start working (from event-loop?)
    main()
