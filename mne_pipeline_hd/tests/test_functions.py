# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""
from mne_pipeline_hd.pipeline.function_utils import RunController
from mne_pipeline_hd.pipeline.loading import MEEG


def test_all_functions(controller):
    controller.pr.sel_functions = list(controller.pd_funcs.index)
    controller.sel_meeg = ['_sample_', '_test_']
    controller.sel_fsmri = ['fsmri']
    rc = RunController(controller)
    rc.start()


def test_event_id(controller):
    # ToDo: Not working yet
    controller.pr.add_meeg('_sample_')
    controller.pr.sel_functions = ['epoch_raw']
    controller.pr.sel_meeg = ['_sample_']
    controller.pr.meeg_event_id['_sample_'] = {'test/sub1': 1,
                                               'test/sub2': 2,
                                               'test/sub3': 3}
    controller.pr.sel_event_id['_sample_'] = ['test']
    rc = RunController(controller)
    rc.start()

    meeg = MEEG('_sample_', controller)
    epochs = meeg.load_epochs()
    assert epochs.data.shape[1] == 37
