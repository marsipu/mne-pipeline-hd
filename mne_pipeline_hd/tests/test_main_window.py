# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
from mne_pipeline_hd import _object_refs
from mne_pipeline_hd.tests._test_utils import _test_wait


def test_init(main_window, qtbot):
    qtbot.waitExposed(main_window)

    _test_wait(qtbot, 1000)

    main_window.close()

    _test_wait(qtbot, 1000)

    assert _object_refs['main_window'] is None
