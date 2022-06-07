# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""
import logging
from shutil import copytree

import pytest

from mne_pipeline_hd.gui.main_window import MainWindow
from mne_pipeline_hd.pipeline.controller import Controller


@pytest.fixture(scope='session')
def controller_base(tmpdir_factory):
    logging.info('Setting up controller with test-files...')
    ct_path = tmpdir_factory.mktemp('test_home')
    ct = Controller(ct_path, 'test')
    ct.pr.add_meeg('_sample_')
    ct.pr.add_meeg('_test_')
    ct.pr.add_fsmri('fsaverage')

    return ct


@pytest.fixture
def controller(controller_base, tmpdir):
    base_path = controller_base.home_path
    logging.info('Copying base...')
    copytree(base_path, tmpdir, dirs_exist_ok=True)
    ct = Controller(tmpdir, 'test')

    return ct


@pytest.fixture
def main_window(controller, qtbot):
    mw = MainWindow(controller)
    qtbot.addWidget(mw)

    return mw
