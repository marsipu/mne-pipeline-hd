# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""


def test_timed_messagebox(qtbot):
    """Test TimedMessageBox."""
    from gui.base_widgets import TimedMessageBox

    # Test text and countdown
    timed_messagebox = TimedMessageBox(2)
    timed_messagebox.setText("Test")
    qtbot.addWidget(timed_messagebox)
    timed_messagebox.show()

    qtbot.wait(1000)
    qtbot.waitSignal(timed_messagebox.timer.timeout)
    assert timed_messagebox.text() == "Test\nTimeout: 1"

    # Test messagebox properly closes
    qtbot.wait(2100)
    assert timed_messagebox.isHidden()

    # Test static methods
    ans = TimedMessageBox.question(1, defaultButton=TimedMessageBox.Yes)
    qtbot.wait(1100)
    assert ans == TimedMessageBox.Yes

    ans = TimedMessageBox.critical(
        1,
        buttons=TimedMessageBox.Save | TimedMessageBox.Cancel,
        defaultButton=TimedMessageBox.Cancel,
    )
    qtbot.wait(1100)
    assert ans == TimedMessageBox.Cancel