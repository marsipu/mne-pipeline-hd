# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""

from mne_pipeline_hd import _object_refs
from mne_pipeline_hd.pipeline.pipeline_utils import _test_wait


def test_init(main_window, qtbot):
    qtbot.waitExposed(main_window)

    _test_wait(qtbot, 1000)

    main_window.close()

    _test_wait(qtbot, 1000)

    assert _object_refs['main_window'] is None
