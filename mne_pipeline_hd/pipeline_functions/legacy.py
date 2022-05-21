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
from os.path import isdir, join, isfile

from mne_pipeline_hd.pipeline_functions.loading import MEEG, FSMRI, Group
from mne_pipeline_hd.pipeline_functions.pipeline_utils import type_json_hook

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
