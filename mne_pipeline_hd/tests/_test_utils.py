# -*- coding: utf-8 -*-
import pytest
import pytestqt


def _test_wait(qtbot, timeout):
    with pytest.raises(pytestqt.exceptions.TimeoutError):
        qtbot.waitUntil(lambda: False, timeout=timeout)
