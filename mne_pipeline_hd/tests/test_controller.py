# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2021, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
from mne_pipeline_hd.pipeline_functions.controller import Controller

controller_attributes = ['home_path', 'projects', 'pr', 'projects_path', 'subjects_dir']


def test_init(tmpdir):
    ct = Controller(tmpdir)

    for ca in controller_attributes:
        assert hasattr(ct, ca)


def test_project_management(tmpdir):
    ct = Controller(tmpdir)

    ct.change_project('test')

    assert hasattr(ct, 'pr')
    assert ct.pr.name == 'test'

    ct.remove_project('test')

