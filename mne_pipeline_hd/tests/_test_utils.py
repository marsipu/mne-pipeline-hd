# -*- coding: utf-8 -*-
import pytest
import pytestqt

from qtpy.QtCore import Qt


def _test_wait(qtbot, timeout):
    with pytest.raises(pytestqt.exceptions.TimeoutError):
        qtbot.waitUntil(lambda: False, timeout=timeout)


def click_view_checkbox(row, qtbot, view, delay=0):
    rect = view.visualRect(view.model().index(row, 0))
    pos = rect.center()
    pos.setX(rect.left() + int(0.01 * rect.width()))
    qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=pos, delay=delay)
