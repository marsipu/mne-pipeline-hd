# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import pytest

from mne_pipeline_hd.pipeline.pipeline_utils import logger


def _test_load_save(obj, available_test_paths, excepted_data_types=[]):
    for data_type in [d for d in obj.io_dict if d not in excepted_data_types]:
        logger().info(f"Testing {data_type}")
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
    _test_load_save(meeg, sample_paths, excepted_data_types=["trans"])


def test_fsmri(controller):
    from mne_pipeline_hd.pipeline.loading import FSMRI, fsaverage_paths

    controller.pr.add_fsmri("fsaverage")
    fsmri = FSMRI("fsaverage", controller)

    # Test load/save functions
    _test_load_save(fsmri, fsaverage_paths)


def test_kwargs_geopenfilenames():
    import inspect
    from qtpy import compat

    signature = inspect.signature(compat.getopenfilenames)
    assert "filters" in signature.parameters
