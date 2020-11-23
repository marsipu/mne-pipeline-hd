# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
Copyright © 2011-2019, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
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

from .pipeline_utils import NumpyJSONEncoder, numpy_json_hook


class Project:
    """
    A class with attributes for all the paths, file-lists/dicts and parameters of the selected project
    """

    def __init__(self, main_win, name):
        self.mw = main_win
        self.name = name

        # Initiate Project-Lists and Dicts
        # Stores the names of all MEG/EEG-Files
        self.all_meeg = []
        # Stores selected MEG/EEG-Files
        self.sel_meeg = []

        # Stores Bad-Channels for each MEG/EEG-File
        self.meeg_bad_channels = {}

        # Stores Event-ID for each MEG/EEG-File
        self.meeg_event_id = {}
        # Stores selected event-id-labels
        self.sel_event_id = {}

        # Stores the names of all Empty-Room-Files (MEG/EEG)
        self.all_erm = []
        # Stores selected Empty-Room-Files (MEG/EEG)
        self.sel_erm = []
        # Maps each MEG/EEG-File to a Empty-Room-File or None
        self.meeg_to_erm = {}

        # Stores the names of all Freesurfer-Segmentation-Folders in Subjects-Dir
        self.all_fsmri = []
        # Stores selected Freesurfer-Segmentations
        self.sel_fsmri = []
        # Maps each MEG/EEG-File to a Freesurfer-Segmentation or None
        self.meeg_to_fsmri = {}

        # Groups MEG/EEG-Files e.g. for Grand-Average
        self.all_groups = {}
        # Stores selected Grand-Average-Groups
        self.sel_groups = []

        # Stores selected Info-Attributes for each file
        self.all_info = {}

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
        # checks in file-categories for each obj
        self.file_orga_checks = {}

        self.make_paths()
        self.load_lists()
        # self.check_data()

        # Parameter-Dict, contains parameters for each parameter-preset
        self.load_parameters()
        self.load_last_p_preset()
        self.load_file_parameters()

    def make_paths(self):
        # Main folder of project
        self.project_path = join(self.mw.projects_path, self.name)
        # Folder to store the data
        self.data_path = join(self.project_path, 'data')
        # Folder to store the figures (with an additional subfolder for each parameter-preset)
        self.figures_path = join(self.project_path, 'figures', self.p_preset)
        # A dedicated folder to store grand-average data
        self.save_dir_averages = join(self.data_path, 'grand_averages')
        # A dedicated folder to store empty-room measurements
        self.erm_data_path = join(self.data_path, 'empty_room_data')
        # A folder to store all pipeline-scripts as .json-files
        self.pscripts_path = join(self.project_path, '_pipeline_scripts')

        # Create or check existence of folders
        path_lists = [self.mw.subjects_dir, self.data_path, self.erm_data_path,
                      self.pscripts_path, self.mw.custom_pkg_path, self.figures_path]

        for path in path_lists:
            if not exists(path):
                makedirs(path)
                print(f'{path} created')

        # List/Dict-Paths (stored in pscripts_path)
        self.all_meeg_path = join(self.pscripts_path, 'all_meeg.json')
        self.sel_meeg_path = join(self.pscripts_path, 'selected_meeg.json')
        self.meeg_bad_channels_path = join(self.pscripts_path, 'meeg_bad_channels.json')
        self.meeg_event_id_path = join(self.pscripts_path, 'meeg_event_id.json')
        self.sel_event_id_path = join(self.pscripts_path, 'selected_event_ids.json')
        self.all_erm_path = join(self.pscripts_path, 'all_erm.json')
        self.sel_erm_path = join(self.pscripts_path, 'selected_erm.json')
        self.meeg_to_erm_path = join(self.pscripts_path, 'meeg_to_erm.json')
        self.all_fsmri_path = join(self.pscripts_path, 'all_fsmri.json')
        self.sel_fsmri_path = join(self.pscripts_path, 'selected_fsmri.json')
        self.meeg_to_fsmri_path = join(self.pscripts_path, 'meeg_to_fsmri.json')
        self.all_groups_path = join(self.pscripts_path, 'all_groups.json')
        self.sel_groups_path = join(self.pscripts_path, 'selected_groups.json')
        self.all_info_path = join(self.pscripts_path, 'all_info.json')
        self.sel_functions_path = join(self.pscripts_path, 'selected_functions.json')
        self.file_parameters_path = join(self.pscripts_path, 'file_parameters.csv')

        # Old Paths to allow transition (22.11.2020)
        self.old_all_meeg_path = join(self.pscripts_path, 'file_list.json')
        self.old_sel_meeg_path = join(self.pscripts_path, 'selected_files.json')
        self.old_meeg_bad_channels_path = join(self.pscripts_path, 'bad_channels_dict.json')
        self.old_meeg_event_id_path = join(self.pscripts_path, 'event_id_dict.json')
        self.old_sel_event_id_path = join(self.pscripts_path, 'selected_evid_labels.json')
        self.old_all_erm_path = join(self.pscripts_path, 'erm_list.json')
        self.old_meeg_to_erm_path = join(self.pscripts_path, 'erm_dict.json')
        self.old_all_fsmri_path = join(self.pscripts_path, 'mri_sub_list.json')
        self.old_sel_fsmri_path = join(self.pscripts_path, 'selected_mri_files.json')
        self.old_meeg_to_fsmri_path = join(self.pscripts_path, 'sub_dict.json')
        self.old_all_groups_path = join(self.pscripts_path, 'grand_avg_dict.json')
        self.old_sel_groups_path = join(self.pscripts_path, 'selected_grand_average_groups.json')
        self.old_all_info_path = join(self.pscripts_path, 'info_dict.json')
        self.old_sel_funcs_path = join(self.pscripts_path, 'selected_funcs.json')

        file_paths = [self.all_meeg_path,
                      self.sel_meeg_path,
                      self.meeg_bad_channels_path,
                      self.meeg_event_id_path,
                      self.sel_event_id_path,
                      self.all_erm_path,
                      self.sel_erm_path,
                      self.meeg_to_erm_path,
                      self.all_fsmri_path,
                      self.sel_fsmri_path,
                      self.meeg_to_fsmri_path,
                      self.all_groups_path,
                      self.sel_groups_path,
                      self.all_info_path,
                      self.sel_functions_path,
                      self.file_parameters_path]

        # Old Paths to allow transition (22.11.2020)
        self.old_paths = {self.all_meeg_path: self.old_all_meeg_path,
                          self.sel_meeg_path: self.old_sel_meeg_path,
                          self.meeg_bad_channels_path: self.old_meeg_bad_channels_path,
                          self.meeg_event_id_path: self.old_meeg_event_id_path,
                          self.sel_event_id_path: self.old_sel_event_id_path,
                          self.all_erm_path: self.old_all_erm_path,
                          self.meeg_to_erm_path: self.old_meeg_to_erm_path,
                          self.all_fsmri_path: self.old_all_fsmri_path,
                          self.sel_fsmri_path: self.old_sel_fsmri_path,
                          self.meeg_to_fsmri_path: self.old_meeg_to_fsmri_path,
                          self.all_groups_path: self.old_all_groups_path,
                          self.sel_groups_path: self.old_sel_groups_path,
                          self.all_info_path: self.old_all_info_path,
                          self.sel_functions_path: self.old_sel_funcs_path}

        # Create empty files if files are not existing
        for file in file_paths:
            if not isfile(file):
                with open(file, 'w') as fl:
                    fl.write('')
                print(f'{file} created')

    def load_lists(self):
        # Map Paths to their attributes
        load_dict = {self.all_meeg_path: 'all_meeg',
                     self.sel_meeg_path: 'sel_meeg',
                     self.meeg_bad_channels_path: 'meeg_bad_channels',
                     self.meeg_event_id_path: 'meeg_event_id',
                     self.sel_event_id_path: 'sel_event_id',
                     self.all_erm_path: 'all_erm',
                     self.sel_erm_path: 'sel_erm',
                     self.meeg_to_erm_path: 'meeg_to_erm',
                     self.all_fsmri_path: 'all_fsmri',
                     self.sel_fsmri_path: 'sel_fsmri',
                     self.meeg_to_fsmri_path: 'meeg_to_fsmri',
                     self.all_groups_path: 'all_groups',
                     self.sel_groups_path: 'sel_groups',
                     self.all_info_path: 'all_info',
                     self.sel_functions_path: 'sel_functions'
                     }

        for path in load_dict:
            try:
                with open(path, 'r') as file:
                    setattr(self, load_dict[path], json.load(file, object_hook=numpy_json_hook))
            # Either empty file or no file, leaving default from __init__
            except (json.decoder.JSONDecodeError, FileNotFoundError):
                # Old Paths to allow transition (22.11.2020)
                try:
                    with open(self.old_paths[path], 'r') as file:
                        setattr(self, load_dict[path], json.load(file, object_hook=numpy_json_hook))
                except (json.decoder.JSONDecodeError, FileNotFoundError, KeyError):
                    pass

    def save_lists(self):
        save_dict = {self.all_meeg_path: self.all_meeg,
                     self.sel_meeg_path: self.sel_meeg,
                     self.meeg_bad_channels_path: self.meeg_bad_channels,
                     self.meeg_event_id_path: self.meeg_event_id,
                     self.sel_event_id_path: self.sel_event_id,
                     self.all_erm_path: self.all_erm,
                     self.sel_erm_path: self.sel_erm,
                     self.meeg_to_erm_path: self.meeg_to_erm,
                     self.all_fsmri_path: self.all_fsmri,
                     self.sel_fsmri_path: self.sel_fsmri,
                     self.meeg_to_fsmri_path: self.meeg_to_fsmri,
                     self.all_groups_path: self.all_groups,
                     self.sel_groups_path: self.sel_groups,
                     self.all_info_path: self.all_info,
                     self.sel_functions_path: self.sel_functions}

        for path in save_dict:
            try:
                with open(path, 'w') as file:
                    json.dump(save_dict[path], file, cls=NumpyJSONEncoder, indent=4)
            except json.JSONDecodeError as err:
                print(f'There is a problem with path:\n'
                      f'{err}')

    def load_parameters(self):
        try:
            with open(join(self.pscripts_path, f'parameters_{self.name}.json'), 'r') as read_file:
                loaded_parameters = json.load(read_file, object_hook=numpy_json_hook)

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
            json.dump(save_parameters, write_file, cls=NumpyJSONEncoder, indent=4)

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
        missing_objects = [x for x in listdir(self.data_path) if
                           x not in ['grand_averages', 'empty_room_data'] and x not in self.all_meeg]

        for obj in missing_objects:
            self.all_meeg.append(obj)

        missing_erm = [x for x in listdir(self.erm_data_path) if x not in self.all_erm]
        for erm in missing_erm:
            self.all_erm.append(erm)

        self.save_lists()

    def find_files(self):
        # Order files under tags which correspond to columns in the DataFrame below
        file_tags = {'Events': ['-eve.fif'], 'Epochs': ['-epo.fif'], 'ICA': ['-ica-epo.fif'], 'Evokeds': ['-ave.fif'],
                     'Forward': ['-fwd.fif'], 'NoiseCov': ['-cov.fif', '-erm-cov.fif', '-clm-cov.fif'],
                     'Inverse': ['-inv.fif']}
        for p_preset in self.parameters:
            self.file_orga_paths[p_preset] = {}
            self.file_orga_checks[p_preset] = pd.DataFrame([], columns=['Events', 'Epochs', 'ICA', 'Evokeds',
                                                                        'Forward', 'NoiseCov', 'Inverse'], dtype='bool')
            for meeg in self.all_meeg:
                print(f'Doing: {meeg}')
                self.file_orga_paths[p_preset][meeg] = []
                # Todo: Some File-I/O has to be changed to make '-' the only delimiter for format
                # Todo: Filter-String can be removed from regexp-pattern
                #  when everyone switched with files to parameter-presets
                file_pattern = rf'{meeg}(_\w*_)?(\w*)([\-a-z]+.[a-z]*)'
                save_dir = join(self.data_path, meeg)

                try:
                    for file_name in os.listdir(save_dir):
                        match = re.match(file_pattern, file_name)
                        if match:
                            if p_preset == match.group(1):
                                # Add paths to dict for each subject under each parameter-preset
                                self.file_orga_paths[p_preset][meeg].append(file_name)
                                # Set True for obj, when tag is matching the file
                                for tag in file_tags:
                                    if any(x == match.group(4) for x in file_tags[tag]):
                                        self.file_orga_checks[p_preset].loc[meeg, tag] = True
                            # Concerns files, which were created befor
                            elif not match.group(1):
                                if file_name not in self.file_orga_paths['Default'][meeg]:
                                    # Add paths to dict for each subject under default parameter-preset
                                    self.file_orga_paths['Default'][meeg].append(file_name)
                                # Set True for obj, when tag is matching the file
                                for tag in file_tags:
                                    if any(x == match.group(4) for x in file_tags[tag]):
                                        self.file_orga_checks['Default'].loc[meeg, tag] = True

                except FileNotFoundError:
                    print(f'{meeg} not found in {self.data_path}')


class FileManagement(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        self.init_ui()
        self.open()

    def init_ui(self):
        self.layout = QVBoxLayout()
