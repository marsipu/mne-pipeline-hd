# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""


def test_legacy_import_check(monkeypatch):
    from mne_pipeline_hd.pipeline.legacy import (legacy_import_check,
                                                 uninstall_package)

    # Monkeypatch input
    monkeypatch.setattr('builtins.input', lambda x: 'y')

    # Test legacy import check
    legacy_import_check('pip-install-test')
    __import__('pip_install_test')
    uninstall_package('pip-install-test')
