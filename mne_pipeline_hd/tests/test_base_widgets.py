# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

from mne_pipeline_hd.tests._test_utils import toggle_checked_list_model


# ToDo: Test all base widgets


def test_checklist(qtbot):
    from mne_pipeline_hd.gui.base_widgets import CheckList

    data = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    checked = list()
    cl = CheckList(data=data, checked=checked)
    qtbot.addWidget(cl)

    # Test check all
    cl.select_all()
    assert checked == data
    cl.clear_all()
    assert checked == []

    # ToDo: Simulate actually clicking the checkboxes

    # Test check by changing the model
    toggle_checked_list_model(cl.model, value=1, row=0)
    assert checked == ["a"]


def test_timed_messagebox(qtbot):
    """Test TimedMessageBox."""
    from mne_pipeline_hd.gui.base_widgets import TimedMessageBox

    # Test text and countdown
    timed_messagebox = TimedMessageBox(timeout=2, step_length=100, text="Test")
    qtbot.addWidget(timed_messagebox)

    qtbot.waitForWindowShown(timed_messagebox)
    # For some reason Windows-CI seems to fail here,
    # maybe timed_messagebox.show() is blocking there
    assert timed_messagebox.text() == "Test\nTimeout: 2"

    # Test messagebox properly closes
    qtbot.wait(250)
    assert timed_messagebox.isHidden()

    # Test static methods
    # Test setting default button
    ans = TimedMessageBox.question(1, defaultButton=TimedMessageBox.Yes)
    qtbot.wait(150)
    assert ans == TimedMessageBox.Yes

    # Test setting buttons
    ans = TimedMessageBox.critical(
        1,
        buttons=TimedMessageBox.Save | TimedMessageBox.Cancel,
        defaultButton=TimedMessageBox.Cancel,
    )
    qtbot.wait(150)
    assert ans == TimedMessageBox.Cancel

    # Test setting no default button
    ans = TimedMessageBox.information(
        1, buttons=TimedMessageBox.Cancel, defaultButton=TimedMessageBox.NoButton
    )
    qtbot.wait(150)
    assert ans is None
