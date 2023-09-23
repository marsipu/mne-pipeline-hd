# -*- coding: utf-8 -*-
import pytest
import pytestqt

from qtpy.QtCore import Qt


def _test_wait(qtbot, timeout):
    with pytest.raises(pytestqt.exceptions.TimeoutError):
        qtbot.waitUntil(lambda: False, timeout=timeout)


def toggle_checked_list_model(model, value=1, row=0, column=0):
    value = Qt.Checked if value else Qt.Unchecked
    model.setData(model.index(row, column), value, Qt.CheckStateRole)
