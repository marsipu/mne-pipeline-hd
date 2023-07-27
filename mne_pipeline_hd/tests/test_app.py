# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
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
