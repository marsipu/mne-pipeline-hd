# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""


def test_meeg(controller):
    controller.pr.add_meeg("__sample__")


def test_fsmri(controller):
    controller.pr.add_fsmri("fsaverage")
