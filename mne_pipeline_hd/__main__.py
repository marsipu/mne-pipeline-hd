# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Copyright © 2011-2019, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
import logging
import os
import sys
from importlib import resources
from inspect import getsourcefile
from os.path import abspath
from pathlib import Path

import qdarkstyle
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QApplication
# Enable start also when not installed via pip (e.g. for development)
# Get the package_path and add it at first position to PATH, should work across platforms and in spyder
from qdarkstyle import DarkPalette, LightPalette

from mne_pipeline_hd.pipeline_functions.controller import Controller

package_parent = str(Path(abspath(getsourcefile(lambda: 0))).parent.parent)
if package_parent not in sys.path:
    sys.path.insert(0, package_parent)

from mne_pipeline_hd import QS
from mne_pipeline_hd.gui.welcome_window import show_welcome_window
from mne_pipeline_hd.gui.gui_utils import StdoutStderrStream, UncaughtHook
from mne_pipeline_hd import ismac, islin


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

    # Disable Help-Button
    try:
        app.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
    except AttributeError:
        print('pyqt-Version is < 5.12')

    # Avoid file-dialog-problems with custom file-managers in linux
    if islin:
        app.setAttribute(Qt.AA_DontUseNativeDialogs, True)

    # Mac-Workarounds
    if ismac:
        # Workaround for not showing with PyQt < 5.15.2
        os.environ['QT_MAC_WANTS_LAYER'] = '1'

    # Avoid Mayavi-Issues
    os.environ['ETS_TOOLKIT'] = 'qt4'
    os.environ['QT_API'] = 'pyqt5'

    # ToDo: MP
    # # Set multiprocessing method to spawn
    # multiprocessing.set_start_method('spawn')

    # Redirect stdout to capture it later in GUI
    sys.stdout = StdoutStderrStream('stdout')
    # Redirect stderr to capture it later in GUI
    sys.stderr = StdoutStderrStream('stderr')

    # Initialize Logger
    logger = logging.getLogger()
    logger.setLevel(QS().value('log_level', defaultValue=logging.INFO))
    formatter = logging.Formatter('%(asctime)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.info('Starting MNE-Pipeline HD')

    # Initialize Exception-Hook
    qt_exception_hook = UncaughtHook()
    # this registers the exception_hook() function as hook with the Python interpreter
    sys.excepthook = qt_exception_hook.exception_hook

    # Initialize Layout
    font_family = QS().value('app_font')
    font_size = QS().value('app_font_size')
    app.setFont(QFont(font_family, font_size))

    # Set Style and Window-Icon
    app_style = QS().value('app_style')
    if app_style == 'dark':
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette))
        icon_name = 'mne_pipeline_icon_dark.png'
    else:
        icon_name = 'mne_pipeline_icon_light.png'
        if app_style == 'light':
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette))
        else:
            app.setStyle(app_style)

    with resources.path('mne_pipeline_hd.pipeline_resources', icon_name) as icon_path:
        app_icon = QIcon(str(icon_path))
    app.setWindowIcon(app_icon)
    
    # Initiate WelcomeWindow
    controller = Controller()
    show_welcome_window(controller)

    # Redirect stdout to capture it later in GUI
    sys.stdout = StdoutStderrStream('stdout')
    # Redirect stderr to capture it later in GUI
    sys.stderr = StdoutStderrStream('stderr')

    # Command-Line interrupt with Ctrl+C possible
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    # For Spyder to make console accessible again
    app.lastWindowClosed.connect(app.quit)

    sys.exit(app.exec())


if __name__ == '__main__':
    # Todo: Make Exception-Handling for PyQt-Start working (from event-loop?)
    main()
