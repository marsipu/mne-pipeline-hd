# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""


def test_meeg(controller):
    controller.pr.add_meeg('__sample__')


def test_fsmri(controller):
    controller.pr.add_fsmri('fsaverage')
