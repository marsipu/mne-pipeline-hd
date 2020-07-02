# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QWidget

# Enable start from command-line (via setup.py-entry_point when pip-installed) and from __main__.py-script
try:
    from mne_pipeline_hd.src.gui import main_window
    from mne_pipeline_hd.src.gui.qt_utils import ErrorDialog, OutputStream, get_exception_tuple
    from mne_pipeline_hd.src.pipeline_functions import ismac
except ModuleNotFoundError:
    from src.gui import main_window
    from src.gui.qt_utils import ErrorDialog, OutputStream, get_exception_tuple
    from src.pipeline_functions import ismac

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
    mw.raise_win()

    # Redirect stdout to capture it later in GUI
    sys.stdout = OutputStream()

    # Command-Line interrupt with Ctrl+C possible
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    # For Spyder to make console accessible again
    app.lastWindowClosed.connect(app.quit)
    sys.exit(app.exec_())


if __name__ == '__main__':
    # Todo: Make Exception-Handling for PyQt-Start working (from event-loop?)
    try:
        main()
    except:
        exc_tuple = get_exception_tuple()
        ErrorDialog(QWidget(), exc_tuple,
                    title=f'Error while Main-Window-Inititialization')
