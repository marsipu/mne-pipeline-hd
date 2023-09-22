# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
import logging

import pytest


def _test_load_save(obj, available_test_paths):
    for data_type in obj.io_dict:
        logging.info(f"Testing {data_type}")
        if data_type not in available_test_paths:
            with pytest.raises((OSError, FileNotFoundError)):
                obj.load(data_type)
        else:
            data = obj.load(data_type)
            obj.save(data_type, data)


def test_meeg(controller):
    from mne_pipeline_hd.pipeline.loading import MEEG, sample_paths

    controller.pr.add_meeg("_sample_")
    meeg = MEEG("_sample_", controller)

    # Test load/save functions
    _test_load_save(meeg, sample_paths)


def test_fsmri(controller):
    from mne_pipeline_hd.pipeline.loading import FSMRI, fsaverage_paths

    controller.pr.add_fsmri("fsaverage")
    fsmri = FSMRI("fsaverage", controller)

    # Test load/save functions
    _test_load_save(fsmri, fsaverage_paths)
