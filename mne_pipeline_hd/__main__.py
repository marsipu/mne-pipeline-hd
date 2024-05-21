# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import os
import sys
from importlib import resources
from os.path import join

import darkdetect
import qtpy
from qtpy.QtCore import QTimer, Qt
from qtpy.QtGui import QIcon, QFont
from qtpy.QtWidgets import QApplication

import mne_pipeline_hd
from mne_pipeline_hd.gui.gui_utils import StdoutStderrStream, UncaughtHook
from mne_pipeline_hd.gui.welcome_window import WelcomeWindow
from mne_pipeline_hd.pipeline.legacy import legacy_import_check
from mne_pipeline_hd.pipeline.pipeline_utils import (
    ismac,
    islin,
    QS,
    init_logging,
    logger,
)

# Check for changes in required packages
legacy_import_check()


def init_streams():
    # Redirect stdout and stderr to capture it later in GUI
    sys.stdout = StdoutStderrStream("stdout")
    sys.stderr = StdoutStderrStream("stderr")


def main():
    app_name = "mne-pipeline-hd"
    organization_name = "marsipu"
    domain_name = "https://github.com/marsipu/mne-pipeline-hd"

    # Enable High-DPI
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setApplicationName(app_name)
    app.setOrganizationName(organization_name)
    app.setOrganizationDomain(domain_name)
    # For Spyder to make console accessible again
    app.lastWindowClosed.connect(app.quit)

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

    init_streams()

    debug_mode = os.environ.get("MNEPHD_DEBUG", False) == "true"
    init_logging(debug_mode)

    logger().info("Starting MNE-Pipeline HD")

    # Show Qt-binding
    if any([qtpy.PYQT5, qtpy.PYQT6]):
        qt_version = qtpy.PYQT_VERSION
    else:
        qt_version = qtpy.PYSIDE_VERSION
    logger().info(f"Using {qtpy.API_NAME} {qt_version}")

    # Initialize Exception-Hook
    if debug_mode:
        logger().info("Debug-Mode is activated")
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

    # Detect system theme
    if app_style == "auto":
        system_theme = darkdetect.theme().lower()
        if system_theme is None:
            logger().info("System theme detection failed. Using light theme.")
            system_theme = "light"
        app_style = system_theme
    if app_style == "dark":
        stylesheet_path = join(
            str(resources.files(mne_pipeline_hd.extra)), "dark_stylesheet.txt"
        )
    else:
        stylesheet_path = join(
            str(resources.files(mne_pipeline_hd.extra)), "light_stylesheet.txt"
        )

    with open(stylesheet_path, "r") as f:
        stylesheet = f.read()

    app.setStyleSheet(stylesheet)

    if app_style == "dark":
        icon_name = "mne_pipeline_icon_dark.png"
    else:
        icon_name = "mne_pipeline_icon_light.png"

    icon_path = join(str(resources.files(mne_pipeline_hd.extra)), icon_name)
    app_icon = QIcon(str(icon_path))
    app.setWindowIcon(app_icon)

    # Initiate WelcomeWindow
    WelcomeWindow()

    # Command-Line interrupt with Ctrl+C possible
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    sys.exit(app.exec())


if __name__ == "__main__":
    # Todo: Make Exception-Handling for PyQt-Start working (from event-loop?)
    main()
