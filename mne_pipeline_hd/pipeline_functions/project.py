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
from os import listdir, makedirs, mkdir
from os.path import exists, isdir, isfile, join
import numpy as np

import mne
import pandas as pd
from PyQt5.QtWidgets import QDialog, QFileDialog, QInputDialog, QMessageBox, QVBoxLayout
from pandas.errors import EmptyDataError

from .pipeline_utils import ParametersJSONEncoder, parameters_json_hook
from ..gui import subject_widgets as subs


class MyProject:
    """
    A class with attributes for all the paths and parameters of the selected project
    """

    def __init__(self, main_win):
        self.mw = main_win

        # Initiate Project-Lists and Dicts
        # Parameter-Dict, contains parameters for each parameter-preset
        self.parameters = {'Default': {}}

        # Default-Parameter-Preset
        self.p_preset = 'Default'

        # Stores parameters for each file saved to disk from the current run (know, what you did to your data)
        self.file_parameters = pd.DataFrame([])

        # paths to existing files
        self.file_orga_paths = {}

        # checks in file-categories for each sub
        self.file_orga_checks = {}

        # Stores selected info-parameters on file-import for later retrival
        self.info_dict = {}

        self.all_files = []
        self.all_mri_subjects = []
        self.erm_files = []
        self.sub_dict = {}
        self.erm_dict = {}
        self.bad_channels_dict = {}
        self.grand_avg_dict = {}
        self.info_dict = {}
        self.sel_files = []
        self.sel_mri_files = []
        self.sel_ga_groups = []

        self.get_paths()
        self.make_paths()
        self.load_sub_lists()
        self.check_data()

    def get_paths(self):
        # Get home_path
        self.home_path = self.mw.qsettings.value('home_path')
        if self.home_path is None or not isdir(self.home_path):
            hp = QFileDialog.getExistingDirectory(self.mw, 'Select a folder to store your Pipeline-Projects')
            if hp == '':
                msg_box = QMessageBox(self.mw)
                msg_box.setText("You can't cancel this step!")
                msg_box.setIcon(QMessageBox.Warning)
                ok = msg_box.exec()
                if ok:
                    self.get_paths()
            else:
                self.home_path = str(hp)
                self.mw.qsettings.setValue('home_path', self.home_path)

        # Check, if home-path is writable
        try:
            mkdir(join(self.home_path, 'test'))
        except OSError:
            self.home_path = None
            self.get_paths()
        else:
            os.remove(join(self.home_path, 'test'))


            # Get project_name
            self.project_name = self.mw.qsettings.value('project_name')
            self.projects_path = join(self.home_path, 'projects')
            if not isdir(self.projects_path):
                mkdir(self.projects_path)
            else:
                self.projects = [p for p in listdir(self.projects_path) if isdir(join(self.projects_path, p, 'data'))]
            if len(self.projects) == 0:
                self.project_name, ok = QInputDialog.getText(self.mw, 'Project-Selection',
                                                             f'No projects in {self.home_path} found\n'
                                                             'Enter a project-name for your first project')
                if ok and self.project_name:
                    self.projects.append(self.project_name)
                    self.mw.qsettings.setValue('project_name', self.project_name)
                    self.make_paths()
                else:
                    # Problem in Python Console, QInputDialog somehow stays in memory
                    msg_box = QMessageBox(self.mw)
                    msg_box.setText("You can't cancel this step!")
                    msg_box.setIcon(QMessageBox.Warning)
                    ok = msg_box.exec()
                    if ok:
                        self.get_paths()
            elif self.project_name is None or self.project_name not in self.projects:
                self.project_name = self.projects[0]
                self.mw.qsettings.setValue('project_name', self.project_name)

            print(f'Home-Path: {self.home_path}')
            print(f'Project-Name: {self.project_name}')
            print(f'Projects-found: {self.projects}')

    def make_paths(self):
        # Initiate other paths
        self.project_path = join(self.projects_path, self.project_name)
        self.data_path = join(self.project_path, 'data')
        self.figures_path = join(self.project_path, 'figures', self.p_preset)
        self.save_dir_averages = join(self.data_path, 'grand_averages')
        self.erm_data_path = join(self.data_path, 'empty_room_data')
        self.subjects_dir = join(self.home_path, 'freesurfer')
        mne.utils.set_config("SUBJECTS_DIR", self.subjects_dir, set_env=True)
        self.custom_pkg_path = join(self.home_path, 'custom_functions')
        # Subject-List/Dict-Path
        self.pscripts_path = join(self.project_path, '_pipeline_scripts')
        self.file_list_path = join(self.pscripts_path, 'file_list.json')
        self.erm_list_path = join(self.pscripts_path, 'erm_list.json')
        self.mri_sub_list_path = join(self.pscripts_path, 'mri_sub_list.json')
        self.sub_dict_path = join(self.pscripts_path, 'sub_dict.json')
        self.erm_dict_path = join(self.pscripts_path, 'erm_dict.json')
        self.bad_channels_dict_path = join(self.pscripts_path, 'bad_channels_dict.json')
        self.grand_avg_dict_path = join(self.pscripts_path, 'grand_avg_dict.json')
        self.info_dict_path = join(self.pscripts_path, 'info_dict.json')
        self.file_parameters_path = join(self.pscripts_path, 'file_parameters.csv')
        self.sel_files_path = join(self.pscripts_path, 'selected_files.json')
        self.sel_mri_files_path = join(self.pscripts_path, 'selected_mri_files.json')
        self.sel_ga_groups_path = join(self.pscripts_path, 'selected_grand_average_groups.json')

        path_lists = [self.subjects_dir, self.data_path, self.erm_data_path,
                      self.pscripts_path, self.custom_pkg_path, self.figures_path]
        file_lists = [self.file_list_path, self.erm_list_path, self.mri_sub_list_path,
                      self.sub_dict_path, self.erm_dict_path, self.bad_channels_dict_path, self.grand_avg_dict_path,
                      self.info_dict_path, self.file_parameters_path, self.sel_files_path, self.sel_mri_files_path,
                      self.sel_ga_groups_path]

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
        self.projects = [p for p in listdir(self.projects_path) if isdir(join(self.projects_path, p, 'data'))]

        load_dict = {self.file_list_path: 'all_files',
                     self.mri_sub_list_path: 'all_mri_subjects',
                     self.erm_list_path: 'erm_files',
                     self.sub_dict_path: 'sub_dict',
                     self.erm_dict_path: 'erm_dict',
                     self.bad_channels_dict_path: 'bad_channels_dict',
                     self.grand_avg_dict_path: 'grand_avg_dict',
                     self.info_dict_path: 'info_dict',
                     self.sel_files_path: 'sel_files',
                     self.sel_mri_files_path: 'sel_mri_files',
                     self.sel_ga_groups_path: 'sel_ga_groups'}

        for path in load_dict:
            try:
                with open(path, 'r') as file:
                    setattr(self, load_dict[path], json.load(file))
            # Either empty file or no file, take default from __init__
            except json.decoder.JSONDecodeError:
                pass

    def load_py_lists(self):
        self.all_files = subs.read_files(join(self.pscripts_path, 'file_list.py'))
        self.all_mri_subjects = subs.read_files(join(self.pscripts_path, 'mri_sub_list.py'))
        self.erm_files = subs.read_files(join(self.pscripts_path, 'erm_list.py'))
        self.sub_dict = subs.read_sub_dict(join(self.pscripts_path, 'sub_dict.py'))
        self.erm_dict = subs.read_sub_dict(join(self.pscripts_path, 'erm_dict.py'))
        self.bad_channels_dict = subs.read_bad_channels_dict(join(self.pscripts_path, 'bad_channels_dict.py'))

        self.mw.subject_dock.update_subjects_list()
        self.mw.subject_dock.update_mri_subjects_list()

    def save_sub_lists(self):
        self.mw.qsettings.setValue('home_path', self.home_path)
        self.mw.qsettings.setValue('project_name', self.project_name)
        self.mw.qsettings.setValue('projects', self.projects)

        save_dict = {self.file_list_path: self.all_files,
                     self.erm_list_path: self.erm_files,
                     self.mri_sub_list_path: self.all_mri_subjects,
                     self.sub_dict_path: self.sub_dict,
                     self.erm_dict_path: self.erm_dict,
                     self.bad_channels_dict_path: self.bad_channels_dict,
                     self.grand_avg_dict_path: self.grand_avg_dict,
                     self.info_dict_path: self.info_dict,
                     self.sel_files_path: self.sel_files,
                     self.sel_mri_files_path: self.sel_mri_files,
                     self.sel_ga_groups_path: self.sel_ga_groups}

        for path in save_dict:
            with open(path, 'w') as file:
                json.dump(save_dict[path], file, indent=4)

        # Save Pandas-CSV (separator=; for Excel)
        self.file_parameters.to_csv(self.file_parameters_path, sep=';')

    def load_parameters(self):
        try:
            with open(join(self.pscripts_path, f'parameters_{self.project_name}.json'), 'r') as read_file:
                loaded_parameters = json.load(read_file, object_hook=parameters_json_hook)
                # Avoid errors for old parameter-files
                if 'Default' not in loaded_parameters:
                    loaded_parameters = {'Default': loaded_parameters}

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
        # Empty the dict
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

    def save_parameters(self):
        with open(join(self.pscripts_path, f'parameters_{self.project_name}.json'), 'w') as write_file:
            # Use customized Encoder to deal with arrays
            json.dump(self.parameters, write_file, cls=ParametersJSONEncoder, indent=4)

    def load_file_parameters(self):
        # Load Pandas-CSV (separator=; for Excel)
        try:
            self.file_parameters = pd.read_csv(self.file_parameters_path, sep=';', index_col=0)
        except EmptyDataError:
            self.file_parameters = pd.DataFrame([], columns=[p for p in self.parameters[self.p_preset].keys()])

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
