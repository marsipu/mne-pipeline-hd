"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
from os import mkdir

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QInputDialog

from mne_pipeline_hd.gui.welcome_window import WelcomeWindow


def test_welcome_window(controller, tmpdir, qtbot, monkeypatch):
    welcome_window = WelcomeWindow(controller)
    qtbot.addWidget(welcome_window)

    # add new project
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: ("test2", True))
    qtbot.mouseClick(welcome_window.add_pr_bt, Qt.LeftButton)
    assert controller.pr.name == "test2"

    # make new home-path
    new_home_path = tmpdir.join("TestHome2")
    mkdir(new_home_path)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *args: new_home_path
    )
    qtbot.mouseClick(welcome_window.home_path_bt, Qt.LeftButton)
    new_controller = welcome_window.ct
    assert new_controller.home_path == new_home_path
    assert new_controller.pr is None

    # Change back to old controller
    old_home_path = controller.home_path
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *args: old_home_path
    )
    qtbot.mouseClick(welcome_window.home_path_bt, Qt.LeftButton)
    assert welcome_window.ct.pr.name == "test2"
