# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import logging
import os
import sys
from importlib import resources

from qtpy.QtCore import QTimer, Qt
from qtpy.QtGui import QIcon, QFont
from qtpy.QtWidgets import QApplication

import mne_pipeline_hd
from mne_pipeline_hd.gui.gui_utils import StdoutStderrStream, UncaughtHook
from mne_pipeline_hd.gui.welcome_window import WelcomeWindow
from mne_pipeline_hd.pipeline.legacy import legacy_import_check
from mne_pipeline_hd.pipeline.pipeline_utils import ismac, islin, QS

# Check for changes in required packages
legacy_import_check()

import qdarktheme  # noqa: E402


def main():
    app_name = "mne-pipeline-hd"
    organization_name = "marsipu"
    domain_name = "https://github.com/marsipu/mne-pipeline-hd"

    qdarktheme.enable_hi_dpi()

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
        print("pyqt-Version is < 5.12")

    # Avoid file-dialog-problems with custom file-managers in linux
    if islin:
        app.setAttribute(Qt.AA_DontUseNativeDialogs, True)

    # Mac-Workarounds
    if ismac:
        # Workaround for not showing with PyQt < 5.15.2
        os.environ["QT_MAC_WANTS_LAYER"] = "1"

    # ToDo: MP
    # # Set multiprocessing method to spawn
    # multiprocessing.set_start_method('spawn')

    # Redirect stdout to capture it later in GUI
    sys.stdout = StdoutStderrStream("stdout")
    # Redirect stderr to capture it later in GUI
    sys.stderr = StdoutStderrStream("stderr")

    # Initialize Logger (root)
    logger = logging.getLogger()
    logger.setLevel(QS().value("log_level", defaultValue=logging.INFO))
    formatter = logging.Formatter(
        "%(asctime)s: %(message)s", datefmt="%Y/%m/%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.info("Starting MNE-Pipeline HD")

    # Initialize Exception-Hook
    if os.environ.get("MNEPHD_DEBUG", False) == "true":
        print("Debug-Mode is activated")
    else:
        qt_exception_hook = UncaughtHook()
        # this registers the exception_hook() function
        # as hook with the Python interpreter
        sys.excepthook = qt_exception_hook.exception_hook

    # Initialize Layout
    font_family = QS().value("app_font")
    font_size = QS().value("app_font_size")
    app.setFont(QFont(font_family, font_size))

    # Set Style and Window-Icon
    app_style = QS().value("app_style")

    # Legacy 20230717
    if app_style not in ["dark", "light", "auto"]:
        app_style = "auto"

    if app_style == "dark":
        qdarktheme.setup_theme("dark")
        icon_name = "mne_pipeline_icon_dark.png"
    elif app_style == "light":
        qdarktheme.setup_theme("light")
        icon_name = "mne_pipeline_icon_light.png"
    else:
        qdarktheme.setup_theme("auto")
        st = qdarktheme.load_stylesheet("auto")
        if "background:rgba(32, 33, 36, 1.000)" in st:
            icon_name = "mne_pipeline_icon_dark.png"
        else:
            icon_name = "mne_pipeline_icon_light.png"

    icon_path = resources.files(mne_pipeline_hd.extra) / icon_name
    app_icon = QIcon(str(icon_path))
    app.setWindowIcon(app_icon)

    # Initiate WelcomeWindow
    WelcomeWindow()

    # Redirect stdout to capture it later in GUI
    sys.stdout = StdoutStderrStream("stdout")
    # Redirect stderr to capture it later in GUI
    sys.stderr = StdoutStderrStream("stderr")

    # Command-Line interrupt with Ctrl+C possible
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    # For Spyder to make console accessible again
    app.lastWindowClosed.connect(app.quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    # Todo: Make Exception-Handling for PyQt-Start working (from event-loop?)
    main()
