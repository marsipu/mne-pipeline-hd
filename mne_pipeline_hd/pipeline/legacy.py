# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""
import json
import logging
import os
import subprocess
import sys
from os.path import isdir, join, isfile

from mne_pipeline_hd.pipeline.loading import MEEG, FSMRI, Group
from mne_pipeline_hd.pipeline.pipeline_utils import type_json_hook

renamed_parameters = {
    'filter_target': {
        'Raw': 'raw',
        'Epochs': 'epochs',
        'Evoked': 'evoked'
    },
    'bad_interpolation': {
        'Raw (Filtered)': 'raw_filtered',
        'Epochs': 'epochs',
        'Evoked': 'evoked'
    },
    'ica_fitto': {
        'Raw (Unfiltered)': 'raw',
        'Raw (Filtered)': 'raw_filtered',
        'Epochs': 'epochs'
    },
    'noise_cov_mode': {
        'Empty-Room': 'erm',
        'Epochs': 'epochs'
    },
    'ica_source_data': {
        'Raw (Unfiltered)': 'raw',
        'Raw (Filtered)': 'raw_filtered',
        'Epochs': 'epochs',
        'Epochs (EOG)': 'epochs_eog',
        'Epochs (ECG)': 'epochs_ecg',
        'Evokeds': 'evoked',
        'Evokeds (EOG)': 'evoked (EOG)',
        'Evokeds (ECG)': 'evoked (ECG)'
    },
    'ica_overlay_data': {
        'Raw (Unfiltered)': 'raw',
        'Raw (Filtered)': 'raw_filtered',
        'Evokeds': 'evoked',
        'Evokeds (EOG)': 'evoked (EOG)',
        'Evokeds (ECG)': 'evoked (ECG)'
    }
}

# New packages with {import_name: install_name} (can be the same)
new_packages = {
    'qdarktheme': 'pyqtdarktheme'
}


def install_package(package_name):
    print(f'Installing {package_name}...')
    print(subprocess.check_output([sys.executable, '-m', 'pip', 'install',
                                   package_name], text=True))


def uninstall_package(package_name):
    print(f'Uninstalling {package_name}...')
    print(subprocess.check_output([sys.executable, '-m', 'pip', 'uninstall',
                                   '-y', package_name], text=True))


def legacy_import_check(test_package=None):
    """
    This function checks for recent package changes
    and offers installation or manual installation instructions.
    """
    # For testing purposes
    if test_package is not None:
        new_packages[test_package] = test_package

    for import_name, install_name in new_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f'The package {import_name} '
                  f'is required for this application.\n')
            ans = input('Do you want to install the '
                        'new package now? [y/n]').lower()
            if ans == 'y':
                try:
                    install_package(install_name)
                except subprocess.CalledProcessError:
                    print('Installation failed!')
                else:
                    return
            print(f'Please install the new package {import_name} '
                  f'manually with:\n\n'
                  f'> pip install {install_name}')
            sys.exit(1)


def transfer_file_params_to_single_subject(ct):
    old_fp_path = join(ct.pr.pscripts_path,
                       f'file_parameters_{ct.pr.name}.json')
    if isfile(old_fp_path):
        logging.info('Transfering File-Parameters to single files...')
        with open(old_fp_path, 'r') as file:
            file_parameters = json.load(file, object_hook=type_json_hook)
            for obj_name in file_parameters:
                if obj_name in ct.pr.all_meeg:
                    obj = MEEG(obj_name, ct)
                elif obj_name in ct.pr.all_fsmri:
                    obj = FSMRI(obj_name, ct)
                elif obj_name in ct.pr.all_groups:
                    obj = Group(obj_name, ct)
                else:
                    obj = None
                if obj is not None:
                    if not isdir(obj.save_dir):
                        continue
                    obj.file_parameters = file_parameters[obj_name]
                    obj.save_file_parameter_file()
                    obj.clean_file_parameters()
        os.remove(old_fp_path)
        logging.info('Done!')
