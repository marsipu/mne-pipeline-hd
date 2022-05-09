# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""

from mne_pipeline_hd import _object_refs


def test_init(main_window):
    main_window.close()
    assert _object_refs['main_window'] is None
