# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""
from mne_pipeline_hd.pipeline.function_utils import RunController


def test_all_functions(controller):
    controller.pr.sel_functions = list(controller.pd_funcs.index)
    controller.sel_meeg = ['_sample_', '_test_']
    controller.sel_fsmri = ['fsmri']
    rc = RunController(controller)
    rc.start()
