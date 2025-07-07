# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
import argparse
import os
import sys

import qtpy
from qtpy.QtCore import QTimer, Qt
from qtpy.QtWidgets import QApplication

from mne_pipeline_hd.gui.gui_utils import (
    StdoutStderrStream,
    UncaughtHook,
    set_app_font,
    set_app_theme,
)
from mne_pipeline_hd.gui.welcome_window import WelcomeWindow
from mne_pipeline_hd.pipeline.legacy import legacy_import_check
from mne_pipeline_hd.pipeline.pipeline_utils import (
    ismac,
    islin,
    init_logging,
    logger,
    gui_mode,
)


def init_streams():
    # Redirect stdout and stderr to capture it later in GUI
    sys.stdout = StdoutStderrStream("stdout")
    sys.stderr = StdoutStderrStream("stderr")


def main():
    app_name = "mne-pipeline-hd"
    organization_name = "marsipu"
    domain_name = "https://github.com/marsipu/mne-pipeline-hd"

    debug_mode = os.environ.get("MNEPHD_DEBUG", False) == "true"
    init_logging(debug_mode)

    logger().info("Starting MNE-Pipeline HD")

    if gui_mode:
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

        # ToDo: Multiprocessing
        # # Set multiprocessing method to spawn
        # multiprocessing.set_start_method('spawn')

        init_streams()

        # Show Qt-binding
        if gui_mode:
            if any([qtpy.PYQT5, qtpy.PYQT6]):
                qt_version = qtpy.PYQT_VERSION
            else:
                qt_version = qtpy.PYSIDE_VERSION
            logger().info(f"Using {qtpy.API_NAME} {qt_version}")

        # Initialize Exception-Hook
        if debug_mode:
            logger().info("Debug-Mode is activated")
        else:
            if gui_mode:
                qt_exception_hook = UncaughtHook()
                sys.excepthook = qt_exception_hook.exception_hook

        # Set style and font
        set_app_theme()
        set_app_font()

        # Initiate WelcomeWindow
        WelcomeWindow()

        # Command-Line interrupt with Ctrl+C possible
        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(500)

        sys.exit(app.exec())
    else:
        # Headless mode (no gui)
        logger().info("Started in headless mode (no gui).")
        # ToDo: Implement headless functionality


if __name__ == "__main__":
    global gui_mode

    # Check for changes in required packages
    legacy_import_check()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="MNE-Nodes", description="A GUI with Nodes for MNE-Python"
    )
    parser.add_argument(
        "--nogui", "-n", action="store_true", help="Run headless without GUI"
    )
    cli_args = parser.parse_args(sys.argv[1:])

    if cli_args.nogui:
        gui_mode = False

    main()
