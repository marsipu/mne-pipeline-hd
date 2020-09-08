# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import json
import os
import re
from ast import literal_eval
from copy import deepcopy
from os import listdir, makedirs
from os.path import exists, isfile, join

import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from pandas.errors import EmptyDataError

from .pipeline_utils import ParametersJSONEncoder, parameters_json_hook


class Project:
    """
    A class with attributes for all the paths, file-lists/dicts and parameters of the selected project
    """
    def __init__(self, main_win, name):
        self.mw = main_win
        self.name = name

        # Initiate Project-Lists and Dicts
        # Stores the names of all MEG/EEG-Files
        self.all_files = []
        # Stores the names of all Freesurfer-Segmentation-Folders in Subjects-Dir
        self.all_mri_subjects = []
        # Stres the names of all Empty-Room-Files (MEG/EEG)
        self.erm_files = []
        # Maps each MEG/EEG-File to a Freesurfer-Segmentation or None
        self.sub_dict = {}
        # Maps each MEG/EEG-File to a Empty-Room-File or None
        self.erm_dict = {}
        # Stores Bad-Channels for each MEG/EEG-File
        self.bad_channels_dict = {}
        # Stores Event-ID for each MEG/EEG-File
        self.event_id_dict = {}
        # Stores selected event-id-labels
        self.sel_trials_dict = {}
        # Groups MEG/EEG-Files for Grand-Average
        self.grand_avg_dict = {}
        # Stores selected Info-Attributes for each file
        self.info_dict = {}
        # Stores selected files
        self.sel_files = []
        # Stores selected Freesurfer-Segmentations
        self.sel_mri_files = []
        # Stores selected Grand-Average-Groups
        self.sel_ga_groups = []
        # Stores functions and if they are selected
        self.sel_functions = {}
        # Stores parameters for each Parameter-Preset
        self.parameters = {}
        # Paramter-Preset
        self.p_preset = 'Default'
        # Stores parameters for each file saved to disk from the current run (know, what you did to your data)
        self.file_parameters = pd.DataFrame([])
        # paths to existing files
        self.file_orga_paths = {}
        # checks in file-categories for each sub
        self.file_orga_checks = {}
        # Stores selected info-parameters on file-import for later retrival
        self.info_dict = {}

        self.make_paths()
        self.load_sub_lists()
        # self.check_data()

        # Parameter-Dict, contains parameters for each parameter-preset
        self.load_parameters()
        self.load_last_p_preset()
        self.load_file_parameters()

    def make_paths(self):
        # Initiate other paths
        self.project_path = join(self.mw.projects_path, self.name)
        self.data_path = join(self.project_path, 'data')
        self.figures_path = join(self.project_path, 'figures', self.p_preset)
        self.save_dir_averages = join(self.data_path, 'grand_averages')
        self.erm_data_path = join(self.data_path, 'empty_room_data')
        # Subject-List/Dict-Path
        self.pscripts_path = join(self.project_path, '_pipeline_scripts')
        self.file_list_path = join(self.pscripts_path, 'file_list.json')
        self.erm_list_path = join(self.pscripts_path, 'erm_list.json')
        self.mri_sub_list_path = join(self.pscripts_path, 'mri_sub_list.json')
        self.sub_dict_path = join(self.pscripts_path, 'sub_dict.json')
        self.erm_dict_path = join(self.pscripts_path, 'erm_dict.json')
        self.bad_channels_dict_path = join(self.pscripts_path, 'bad_channels_dict.json')
        self.event_id_dict_path = join(self.pscripts_path, 'event_id_dict.json')
        self.sel_trials_dict_path = join(self.pscripts_path, 'selected_evid_labels.json')
        self.grand_avg_dict_path = join(self.pscripts_path, 'grand_avg_dict.json')
        self.info_dict_path = join(self.pscripts_path, 'info_dict.json')
        self.file_parameters_path = join(self.pscripts_path, 'file_parameters.csv')
        self.sel_files_path = join(self.pscripts_path, 'selected_files.json')
        self.sel_mri_files_path = join(self.pscripts_path, 'selected_mri_files.json')
        self.sel_ga_groups_path = join(self.pscripts_path, 'selected_grand_average_groups.json')
        self.sel_funcs_path = join(self.pscripts_path, 'selected_funcs.json')

        path_lists = [self.mw.subjects_dir, self.data_path, self.erm_data_path,
                      self.pscripts_path, self.mw.custom_pkg_path, self.figures_path]
        file_lists = [self.file_list_path, self.erm_list_path, self.mri_sub_list_path,
                      self.sub_dict_path, self.erm_dict_path, self.bad_channels_dict_path, self.event_id_dict_path,
                      self.grand_avg_dict_path, self.info_dict_path, self.file_parameters_path, self.sel_files_path,
                      self.sel_mri_files_path, self.sel_ga_groups_path, self.sel_funcs_path,
                      self.sel_trials_dict_path]

        for path in path_lists:
            if not exists(path):
                makedirs(path)
                print(f'{path} created')

        for file in file_lists:
            if not isfile(file):
                with open(file, 'w') as fl:
                    fl.write('')
                print(f'{file} created')

        # create grand average-paths
        ga_folders = ['statistics', 'evoked', 'stc', 'ltc', 'tfr', 'connect']
        for subfolder in ga_folders:
            grand_average_path = join(self.data_path, 'grand_averages', subfolder)
            if not exists(grand_average_path):
                makedirs(grand_average_path)
                print(grand_average_path + ' has been created')

    def load_sub_lists(self):
        load_dict = {self.file_list_path: 'all_files',
                     self.mri_sub_list_path: 'all_mri_subjects',
                     self.erm_list_path: 'erm_files',
                     self.sub_dict_path: 'sub_dict',
                     self.erm_dict_path: 'erm_dict',
                     self.bad_channels_dict_path: 'bad_channels_dict',
                     self.event_id_dict_path: 'event_id_dict',
                     self.sel_trials_dict_path: 'sel_trials_dict',
                     self.grand_avg_dict_path: 'grand_avg_dict',
                     self.info_dict_path: 'info_dict',
                     self.sel_files_path: 'sel_files',
                     self.sel_mri_files_path: 'sel_mri_files',
                     self.sel_ga_groups_path: 'sel_ga_groups',
                     self.sel_funcs_path: 'sel_functions'
                     }

        for path in load_dict:
            try:
                with open(path, 'r') as file:
                    setattr(self, load_dict[path], json.load(file))
            # Either empty file or no file, take default from __init__
            except json.decoder.JSONDecodeError:
                pass

    def save_sub_lists(self):
        save_dict = {self.file_list_path: self.all_files,
                     self.erm_list_path: self.erm_files,
                     self.mri_sub_list_path: self.all_mri_subjects,
                     self.sub_dict_path: self.sub_dict,
                     self.erm_dict_path: self.erm_dict,
                     self.bad_channels_dict_path: self.bad_channels_dict,
                     self.event_id_dict_path: self.event_id_dict,
                     self.sel_trials_dict_path: self.sel_trials_dict,
                     self.grand_avg_dict_path: self.grand_avg_dict,
                     self.info_dict_path: self.info_dict,
                     self.sel_files_path: self.sel_files,
                     self.sel_mri_files_path: self.sel_mri_files,
                     self.sel_ga_groups_path: self.sel_ga_groups,
                     self.sel_funcs_path: self.sel_functions}

        for path in save_dict:
            try:
                with open(path, 'w') as file:
                    json.dump(save_dict[path], file, indent=4)
            except json.JSONDecodeError as err:
                print(f'There is a problem with path:\n'
                      f'{err}')

    def load_parameters(self):
        try:
            with open(join(self.pscripts_path, f'parameters_{self.name}.json'), 'r') as read_file:
                loaded_parameters = json.load(read_file, object_hook=parameters_json_hook)

                for p_preset in loaded_parameters:
                    # Make sure, that only parameters, which exist in pd_params are loaded
                    for param in [p for p in loaded_parameters[p_preset] if p not in self.mw.pd_params.index]:
                        if '_exp' not in param:
                            loaded_parameters[p_preset].pop(param)

                    # Add parameters, which exist in resources/parameters.csv,
                    # but not in loaded-parameters (e.g. added with custom-module)
                    for param in [p for p in self.mw.pd_params.index if p not in loaded_parameters[p_preset]]:
                        try:
                            eval_param = literal_eval(self.mw.pd_params.loc[param, 'default'])
                        except (ValueError, SyntaxError, NameError):
                            # Allow parameters to be defined by functions e.g. by numpy, etc.
                            if self.mw.pd_params.loc[param, 'gui_type'] == 'FuncGui':
                                default_string = self.mw.pd_params.loc[param, 'default']
                                eval_param = eval(default_string, {'np': np})
                                exp_name = param + '_exp'
                                loaded_parameters[p_preset].update({exp_name: default_string})
                            else:
                                eval_param = self.mw.pd_params.loc[param, 'default']
                        loaded_parameters[p_preset].update({param: eval_param})

                self.parameters = loaded_parameters
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.load_default_parameters()

    def load_default_parameters(self):
        string_params = dict(self.mw.pd_params['default'])
        # Empty the dict for current Parameter-Preset
        self.parameters[self.p_preset] = {}
        for param in string_params:
            try:
                self.parameters[self.p_preset][param] = literal_eval(string_params[param])
            except (ValueError, SyntaxError):
                # Allow parameters to be defined by functions e.g. by numpy, etc.
                if self.mw.pd_params.loc[param, 'gui_type'] == 'FuncGui':
                    self.parameters[self.p_preset][param] = eval(string_params[param], {'np': np})
                    exp_name = param + '_exp'
                    self.parameters[self.p_preset][exp_name] = string_params[param]
                else:
                    self.parameters[self.p_preset][param] = string_params[param]

    def load_last_p_preset(self):
        try:
            with open(join(self.pscripts_path, f'last_p_preset_{self.name}.json'), 'r') as read_file:
                self.p_preset = json.load(read_file)
                # If parameter-preset not in Parameters, load first Parameter-Key(=Parameter-Preset)
                if self.p_preset not in self.parameters:
                    self.p_preset = list(self.parameters.keys())[0]
        except FileNotFoundError:
            self.p_preset = list(self.parameters.keys())[0]

    def save_parameters(self):
        # Labeling tuples
        save_parameters = deepcopy(self.parameters)
        for p_preset in self.parameters:
            for key in self.parameters[p_preset]:
                if isinstance(self.parameters[p_preset][key], tuple):
                    save_parameters[p_preset][key] = {'tuple_type': self.parameters[p_preset][key]}
        with open(join(self.pscripts_path, f'parameters_{self.name}.json'), 'w') as write_file:
            # Use customized Encoder to deal with arrays
            json.dump(save_parameters, write_file, cls=ParametersJSONEncoder, indent=4)

    def load_file_parameters(self):
        # Load Pandas-CSV (separator=; for Excel)
        try:
            self.file_parameters = pd.read_csv(self.file_parameters_path, sep=';', index_col=0)
        except EmptyDataError:
            self.file_parameters = pd.DataFrame([], columns=[p for p in self.parameters[self.p_preset].keys()])

    def save_file_parameters(self):
        # Save Pandas-CSV (separator=; for Excel)
        self.file_parameters.to_csv(self.file_parameters_path, sep=';')

    def check_data(self):
        missing_subjects = [x for x in listdir(self.data_path) if
                            x not in ['grand_averages', 'empty_room_data'] and x not in self.all_files]

        for sub in missing_subjects:
            self.all_files.append(sub)

        missing_erm = [x for x in listdir(self.erm_data_path) if x not in self.erm_files]
        for erm in missing_erm:
            self.erm_files.append(erm)

        self.save_sub_lists()

    def find_files(self):
        # Order files under tags which correspond to columns in the DataFrame below
        file_tags = {'Events': ['-eve.fif'], 'Epochs': ['-epo.fif'], 'ICA': ['-ica-epo.fif'], 'Evokeds': ['-ave.fif'],
                     'Forward': ['-fwd.fif'], 'NoiseCov': ['-cov.fif', '-erm-cov.fif', '-clm-cov.fif'],
                     'Inverse': ['-inv.fif']}
        for p_preset in self.parameters:
            self.file_orga_paths[p_preset] = {}
            self.file_orga_checks[p_preset] = pd.DataFrame([], columns=['Events', 'Epochs', 'ICA', 'Evokeds',
                                                                        'Forward', 'NoiseCov', 'Inverse'], dtype='bool')
            for sub in self.all_files:
                print(f'Doing: {sub}')
                self.file_orga_paths[p_preset][sub] = []
                # Todo: Some File-I/O has to be changed to make '-' the only delimiter for format
                # Todo: Filter-String can be removed from regexp-pattern
                #  when everyone switched with files to parameter-presets
                file_pattern = rf'{sub}(_\w*_)?(\w*)([\-a-z]+.[a-z]*)'
                save_dir = join(self.data_path, sub)

                try:
                    for file_name in os.listdir(save_dir):
                        match = re.match(file_pattern, file_name)
                        if match:
                            if p_preset == match.group(1):
                                # Add paths to dict for each subject under each parameter-preset
                                self.file_orga_paths[p_preset][sub].append(file_name)
                                # Set True for sub, when tag is matching the file
                                for tag in file_tags:
                                    if any(x == match.group(4) for x in file_tags[tag]):
                                        self.file_orga_checks[p_preset].loc[sub, tag] = True
                            # Concerns files, which were created befor
                            elif not match.group(1):
                                if file_name not in self.file_orga_paths['Default'][sub]:
                                    # Add paths to dict for each subject under default parameter-preset
                                    self.file_orga_paths['Default'][sub].append(file_name)
                                # Set True for sub, when tag is matching the file
                                for tag in file_tags:
                                    if any(x == match.group(4) for x in file_tags[tag]):
                                        self.file_orga_checks['Default'].loc[sub, tag] = True

                except FileNotFoundError:
                    print(f'{sub} not found in {self.data_path}')


class FileManagement(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        self.init_ui()
        self.open()

    def init_ui(self):
        self.layout = QVBoxLayout()
