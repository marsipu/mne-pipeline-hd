# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2020, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
import json
import os
from ast import literal_eval
from copy import deepcopy
from os import listdir, makedirs
from os.path import exists, isfile, join

import numpy as np

from .pipeline_utils import NumpyJSONEncoder, numpy_json_hook


class Project:
    """
    A class with attributes for all the paths, file-lists/dicts and parameters of the selected project
    """

    def __init__(self, main_win, name):
        self.mw = main_win
        self.name = name

        # Main folder of project
        self.project_path = join(self.mw.projects_path, self.name)
        # Folder to store the data
        self.data_path = join(self.project_path, 'data')
        # Folder to store the figures (with an additional subfolder for each parameter-preset)
        self.figures_path = join(self.project_path, 'figures')
        # A dedicated folder to store grand-average data
        self.save_dir_averages = join(self.data_path, 'grand_averages')
        # A dedicated folder to store empty-room measurements
        self.erm_data_path = join(self.data_path, 'empty_room_data')
        # A folder to store all pipeline-scripts as .json-files
        self.pscripts_path = join(self.project_path, '_pipeline_scripts')

        self.main_paths = [self.mw.subjects_dir, self.data_path, self.erm_data_path,
                           self.pscripts_path, self.mw.custom_pkg_path, self.figures_path]

        # Initiate Project-Lists and Dicts
        # Stores the names of all MEG/EEG-Files
        self.all_meeg = list()
        self.all_meeg_path = join(self.pscripts_path, f'all_meeg_{self.name}.json')
        # Stores selected MEG/EEG-Files
        self.sel_meeg = list()
        self.sel_meeg_path = join(self.pscripts_path, f'selected_meeg_{self.name}.json')

        # Stores Bad-Channels for each MEG/EEG-File
        self.meeg_bad_channels = dict()
        self.meeg_bad_channels_path = join(self.pscripts_path, f'meeg_bad_channels_{self.name}.json')

        # Stores Event-ID for each MEG/EEG-File
        self.meeg_event_id = dict()
        self.meeg_event_id_path = join(self.pscripts_path, f'meeg_event_id_{self.name}.json')
        # Stores selected event-id-labels
        self.sel_event_id = dict()
        self.sel_event_id_path = join(self.pscripts_path, f'selected_event_ids_{self.name}.json')

        # Stores the names of all Empty-Room-Files (MEG/EEG)
        self.all_erm = list()
        self.all_erm_path = join(self.pscripts_path, f'all_erm_{self.name}.json')

        # Maps each MEG/EEG-File to a Empty-Room-File or None
        self.meeg_to_erm = dict()
        self.meeg_to_erm_path = join(self.pscripts_path, f'meeg_to_erm_{self.name}.json')

        # Stores the names of all Freesurfer-Segmentation-Folders in Subjects-Dir
        self.all_fsmri = list()
        self.all_fsmri_path = join(self.pscripts_path, f'all_fsmri_{self.name}.json')

        # Stores selected Freesurfer-Segmentations
        self.sel_fsmri = list()
        self.sel_fsmri_path = join(self.pscripts_path, f'selected_fsmri_{self.name}.json')

        # Maps each MEG/EEG-File to a Freesurfer-Segmentation or None
        self.meeg_to_fsmri = {}
        self.meeg_to_fsmri_path = join(self.pscripts_path, f'meeg_to_fsmri_{self.name}.json')

        self.ica_exclude = dict()
        self.ica_exclude_path = join(self.pscripts_path, f'ica_exclude_{self.name}.json')

        # Groups MEG/EEG-Files e.g. for Grand-Average
        self.all_groups = {}
        self.all_groups_path = join(self.pscripts_path, f'all_groups_{self.name}.json')

        # Stores selected Grand-Average-Groups
        self.sel_groups = list()
        self.sel_groups_path = join(self.pscripts_path, f'selected_groups_{self.name}.json')

        # Stores selected Info-Attributes for each file
        self.all_info = dict()
        self.all_info_path = join(self.pscripts_path, f'all_info_{self.name}.json')

        # Stores functions and if they are selected
        self.sel_functions = dict()
        self.sel_functions_path = join(self.pscripts_path, f'selected_functions_{self.name}.json')

        # Stores additional keyword-arguments for functions by function-name
        self.add_kwargs = dict()
        self.add_kwargs_path = join(self.pscripts_path, f'additional_kwargs_{self.name}.json')

        # Stores parameters for each Parameter-Preset
        self.parameters = dict()
        self.parameters_path = join(self.pscripts_path, f'parameters_{self.name}.json')

        # Paramter-Preset
        self.p_preset = 'Default'
        self.sel_p_preset_path = join(self.pscripts_path, f'sel_p_preset_{self.name}.json')

        # Stores parameters for each file saved to disk from the current run (know, what you did to your data)
        self.file_parameters = dict()
        self.file_parameters_path = join(self.pscripts_path, f'file_parameters_{self.name}.json')

        # Map the paths to their attribute in the Project-Class
        self.path_to_attribute = {self.all_meeg_path: 'all_meeg',
                                  self.sel_meeg_path: 'sel_meeg',
                                  self.meeg_bad_channels_path: 'meeg_bad_channels',
                                  self.meeg_event_id_path: 'meeg_event_id',
                                  self.sel_event_id_path: 'sel_event_id',
                                  self.all_erm_path: 'all_erm',
                                  self.meeg_to_erm_path: 'meeg_to_erm',
                                  self.all_fsmri_path: 'all_fsmri',
                                  self.sel_fsmri_path: 'sel_fsmri',
                                  self.meeg_to_fsmri_path: 'meeg_to_fsmri',
                                  self.ica_exclude_path: 'ica_exclude',
                                  self.all_groups_path: 'all_groups',
                                  self.sel_groups_path: 'sel_groups',
                                  self.all_info_path: 'all_info',
                                  self.sel_functions_path: 'sel_functions',
                                  self.add_kwargs_path: 'add_kwargs',
                                  self.parameters_path: 'parameters',
                                  self.sel_p_preset_path: 'p_preset',
                                  self.file_parameters_path: 'file_parameters'}

        # Attributes, which have their own special function for loading
        self.special_loads = ['parameters', 'p_preset']

        # Attributes, which have their own special function for saving
        self.special_saves = ['parameters']

        self.make_paths()
        self.load()
        self.check_data()

    def make_paths(self):

        # Create or check existence of main_paths
        for path in self.main_paths:
            if not exists(path):
                makedirs(path)
                print(f'{path} created')

        # Create empty files if files are not existing
        for file_path in self.path_to_attribute:
            if not isfile(file_path):
                with open(file_path, 'w') as fl:
                    fl.write('')
                print(f'{file_path} created')

    def load_lists(self):
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

        for path in [p for p in self.path_to_attribute if self.path_to_attribute[p] not in self.special_loads]:
            try:
                with open(path, 'r') as file:
                    setattr(self, self.path_to_attribute[path], json.load(file, object_hook=numpy_json_hook))
            # Either empty file or no file, leaving default from __init__
            except (json.JSONDecodeError, FileNotFoundError):
                # Old Paths to allow transition (22.11.2020)
                try:
                    with open(self.old_paths[path], 'r') as file:
                        setattr(self, self.path_to_attribute[path], json.load(file, object_hook=numpy_json_hook))
                except (json.JSONDecodeError, FileNotFoundError, KeyError):
                    pass

    def save_lists(self):
        for path in [p for p in self.path_to_attribute if self.path_to_attribute[p] not in self.special_saves]:
            attribute = getattr(self, self.path_to_attribute[path], None)
            try:
                with open(path, 'w') as file:
                    json.dump(attribute, file, cls=NumpyJSONEncoder, indent=4)
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
        self.parameters[self.p_preset] = dict()
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

    def save_parameters(self):
        # Encoding Tuples
        save_parameters = deepcopy(self.parameters)
        for p_preset in self.parameters:
            for key in self.parameters[p_preset]:
                if isinstance(self.parameters[p_preset][key], tuple):
                    save_parameters[p_preset][key] = {'tuple_type': self.parameters[p_preset][key]}

        with open(join(self.pscripts_path, f'parameters_{self.name}.json'), 'w') as write_file:
            # Use customized Encoder to deal with arrays
            json.dump(save_parameters, write_file, cls=NumpyJSONEncoder, indent=4)

    def load_last_p_preset(self):
        try:
            with open(self.sel_p_preset_path, 'r') as read_file:
                self.p_preset = json.load(read_file)
                # If parameter-preset not in Parameters, load first Parameter-Key(=Parameter-Preset)
                if self.p_preset not in self.parameters:
                    self.p_preset = list(self.parameters.keys())[0]
        except FileNotFoundError:
            self.p_preset = list(self.parameters.keys())[0]

    def load(self):
        self.load_lists()
        self.load_parameters()
        self.load_last_p_preset()

    def save(self):
        self.save_lists()
        self.save_parameters()

    def check_data(self):

        missing_objects = [x for x in listdir(self.data_path) if
                           x not in ['grand_averages', 'empty_room_data'] and x not in self.all_meeg]

        for obj in missing_objects:
            self.all_meeg.append(obj)

        missing_erm = [x for x in listdir(self.erm_data_path) if x not in self.all_erm]
        for erm in missing_erm:
            self.all_erm.append(erm)

        # Get Freesurfer-folders (with 'surf'-folder) from subjects_dir (excluding .files for Mac)
        read_dir = sorted([f for f in os.listdir(self.mw.subjects_dir) if not f.startswith('.')], key=str.lower)
        self.all_fsmri = [fsmri for fsmri in read_dir if exists(join(self.mw.subjects_dir, fsmri, 'surf'))]

        self.save_lists()
