# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""


def test_get_sample(controller):
    assert '_sample_' in controller.pr.all_meeg


def test_get_fsaverage(controller):
    assert 'fsaverage' in controller.pr.all_fsmri
