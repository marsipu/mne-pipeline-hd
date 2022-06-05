# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""
from mne_pipeline_hd.pipeline.controller import Controller


def test_all_functions(tmpdir):
    ct = Controller(home_path=tmpdir, selected_project='test')
    # ToDo: Determine Run-Order with dependencies
