# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""

import io

from mne_pipeline_hd.pipeline.controller import Controller

controller_attributes = ['home_path', 'projects', 'pr', 'projects_path',
                         'subjects_dir']


def test_init(tmpdir):
    ct = Controller(tmpdir)

    for ca in controller_attributes:
        assert hasattr(ct, ca)


def _check_project(ct, project_name):
    assert ct.pr.name == project_name
    assert project_name in ct.projects
    assert ct.settings['selected_project'] == project_name


def test_project_management(tmpdir, monkeypatch):
    ct = Controller(tmpdir, 'test1')

    # Initialize with "test1"
    assert hasattr(ct, 'pr')
    _check_project(ct, 'test1')

    # Remove project "test1"
    # Add monkeypatch for stdin to pass input for "test2"
    monkeypatch.setattr('sys.stdin', io.StringIO('test2'))
    ct.remove_project('test1')
    _check_project(ct, 'test2')

    # Add two projects "test3" and "test4"
    ct.change_project('test3')
    _check_project(ct, 'test3')
    ct.change_project('test4')
    _check_project(ct, 'test4')

    # Change back to existing project
    ct.change_project('test3')
    _check_project(ct, 'test3')

    assert len(ct.projects) == 3

    # Remove non-selected project
    ct.remove_project('test2')
    _check_project(ct, 'test3')

    assert len(ct.projects) == 2
