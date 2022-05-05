# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import json
import logging
import os
from os.path import isdir, join, isfile

from .loading import MEEG, FSMRI, Group
from .pipeline_utils import type_json_hook


def transfer_file_params_to_single_subject(ct):
    old_fp_path = join(ct.pr.pscripts_path, f'file_parameters_{ct.pr.name}.json')
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



