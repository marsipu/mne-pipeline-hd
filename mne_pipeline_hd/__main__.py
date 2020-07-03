# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://www.frontiersin.org/articles/10.3389/fnins.2018.00006/full
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import sys
from pathlib import Path

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QWidget

# Enable start from command-line (module installed via pip, thus mne_pipeline_hd already in sys.path,
# but on the other hand package_dir not in sys.path (import src not working))
# For start from __main__.py-script (for example in IDE), mne_pipeline_hd not in sys.path so it is added
try:
    # if installed via pip, currently always the pip installed package is loaded
    import mne_pipeline_hd
except ModuleNotFoundError:
    top_package_path = str(Path(sys.path[0]).parent)
    sys.path.insert(0, top_package_path)

from mne_pipeline_hd.gui import main_window
from mne_pipeline_hd.gui.qt_utils import ErrorDialog, OutputStream, get_exception_tuple
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
    mw.raise_win()

    # Redirect stdout to capture it later in GUI
    sys.stdout = OutputStream()

    # Command-Line interrupt with Ctrl+C possible
    timer = QTimer()
    timer.timeout.connect(lambda: mw)
    timer.start(500)

    sys.exit(app.exec_())


if __name__ == '__main__':
    # Todo: Make Exception-Handling for PyQt-Start working (from event-loop?)
    main()
