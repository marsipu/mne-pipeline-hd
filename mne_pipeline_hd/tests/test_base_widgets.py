# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
from mne_pipeline_hd.tests._test_utils import click_view_checkbox


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

    # Test check by clicking
    click_view_checkbox(0, qtbot, cl.view)
    assert checked == ["a"]


def test_timed_messagebox(qtbot):
    """Test TimedMessageBox."""
    from mne_pipeline_hd.gui.base_widgets import TimedMessageBox
    from mne_pipeline_hd.pipeline.pipeline_utils import iswin

    # Test text and countdown
    timed_messagebox = TimedMessageBox(2, text="Test")
    qtbot.addWidget(timed_messagebox)
    timed_messagebox.show()

    qtbot.wait(1100)
    # For some reason Windows-CI seems to fail here,
    # maybe timed_messagebox.show() is blocking there
    if not iswin:
        assert timed_messagebox.text() == "Test\nTimeout: 1"

    # Test messagebox properly closes
    qtbot.wait(2100)
    assert timed_messagebox.isHidden()

    # Test static methods
    # Test setting default button
    ans = TimedMessageBox.question(1, defaultButton=TimedMessageBox.Yes)
    qtbot.wait(1100)
    assert ans == TimedMessageBox.Yes

    # Test setting buttons
    ans = TimedMessageBox.critical(
        1,
        buttons=TimedMessageBox.Save | TimedMessageBox.Cancel,
        defaultButton=TimedMessageBox.Cancel,
    )
    qtbot.wait(1100)
    assert ans == TimedMessageBox.Cancel

    # Test setting no default button
    ans = TimedMessageBox.information(
        1, buttons=TimedMessageBox.Cancel, defaultButton=TimedMessageBox.NoButton
    )
    qtbot.wait(1100)
    assert ans is None
