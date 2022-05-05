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
import re
import shutil
import sys
from importlib import reload, resources, import_module
from os import listdir
from os.path import isdir, join
from pathlib import Path

import mne
import pandas as pd

from .legacy import transfer_file_params_to_single_subject
from .project import Project
from .. import basic_functions, QS
from ..gui.gui_utils import get_exception_tuple, get_user_input_string

home_dirs = ['custom_packages', 'freesurfer', 'projects']
project_dirs = ['_pipeline_scripts', 'data', 'figures']


class Controller:

    def __init__(self, home_path=None, selected_project=None, edu_program_name=None):
        # Check Home-Path
        self.errors = dict()
        self.pr = None
        # Try to load home_path from QSettings
        self.home_path = home_path or QS().value('home_path', defaultValue=None)
        if self.home_path is None:
            self.errors['home_path'] = f'No Home-Path found!'

        # Check if path exists
        elif not isdir(self.home_path):
            self.errors['home_path'] = f'{self.home_path} not found!'

        # Check, if path is writable
        elif not os.access(self.home_path, os.W_OK):
            self.errors['home_path'] = f'{self.home_path} not writable!'

        else:
            # Initialize log-file
            self.logging_path = join(self.home_path, '_pipeline.log')
            file_handler = logging.FileHandler(self.logging_path, 'w')
            logging.getLogger().addHandler(file_handler)

            logging.info(f'Home-Path: {self.home_path}')
            QS().setValue('home_path', self.home_path)
            # Create subdirectories if not existing for a valid home_path
            for subdir in [d for d in home_dirs if not isdir(join(self.home_path, d))]:
                os.mkdir(join(self.home_path, subdir))

            # Get Project-Folders (recognized by distinct sub-folders)
            self.projects_path = join(self.home_path, 'projects')
            self.projects = [p for p in listdir(self.projects_path)
                             if all([isdir(join(self.projects_path, p, d))
                                     for d in project_dirs])]

            # Initialize Subjects-Dir
            self.subjects_dir = join(self.home_path, 'freesurfer')
            mne.utils.set_config("SUBJECTS_DIR", self.subjects_dir, set_env=True)

            # Initialize folder for custom packages
            self.custom_pkg_path = join(self.home_path, 'custom_packages')

            # Initialize educational programs
            self.edu_program_name = edu_program_name
            self.edu_program = None

            # Load default settings
            with resources.open_text('mne_pipeline_hd.pipeline_resources',
                                     'default_settings.json') as file:
                self.default_settings = json.load(file)

            # Load settings (which are stored as .json-file in home_path)
            # settings=<everything, that's OS-independent>
            self.settings = dict()
            self.load_settings()

            self.all_modules = dict()
            self.all_pd_funcs = None

            # Pandas-DataFrame for contextual data of basic functions (included with program)
            with resources.path('mne_pipeline_hd.pipeline_resources',
                                'functions.csv') as pd_funcs_path:
                self.pd_funcs = pd.read_csv(str(pd_funcs_path), sep=';', index_col=0)

            # Pandas-DataFrame for contextual data of parameters
            # for basic functions (included with program)
            with resources.path('mne_pipeline_hd.pipeline_resources',
                                'parameters.csv') as pd_params_path:
                self.pd_params = pd.read_csv(str(pd_params_path), sep=';', index_col=0)

            # Import the basic- and custom-function-modules
            self.import_custom_modules()

            # Check Project
            if selected_project is None:
                selected_project = self.settings['selected_project']

            if selected_project is None:
                if len(self.projects) == 0:
                    self.errors['project'] = 'No projects!'
                else:
                    selected_project = self.projects[0]

            # Initialize Project
            if selected_project is not None:
                self.change_project(selected_project)
                logging.info(f'Selected-Project: {self.pr.name}')

    def load_settings(self):
        try:
            with open(join(self.home_path,
                           'mne_pipeline_hd-settings.json'), 'r') as file:
                self.settings = json.load(file)
            # Account for settings, which were not saved but exist in default_settings
            for setting in [s for s in self.default_settings['settings']
                            if s not in self.settings]:
                self.settings[setting] = self.default_settings['settings'][setting]
        except FileNotFoundError:
            self.settings = self.default_settings['settings']
        else:
            # Check integrity of Settings-Keys
            s_keys = set(self.settings.keys())
            default_keys = set(self.default_settings['settings'])
            # Remove additional (old) keys not appearing in default-settings
            for setting in s_keys - default_keys:
                self.settings.pop(setting)
            # Add new keys from default-settings which are not present in settings
            for setting in default_keys - s_keys:
                self.settings[setting] = self.default_settings['settings'][setting]

        # Check integrity of QSettings-Keys
        QS().sync()
        qs_keys = set(QS().childKeys())
        qdefault_keys = set(self.default_settings['qsettings'])
        # Remove additional (old) keys not appearing in default-settings
        for qsetting in qs_keys - qdefault_keys:
            QS().remove(qsetting)
        # Add new keys from default-settings which are not present in QSettings
        for qsetting in qdefault_keys - qs_keys:
            QS().setValue(qsetting, self.default_settings['qsettings'][qsetting])

    def save_settings(self):
        try:
            with open(join(self.home_path, 'mne_pipeline_hd-settings.json'), 'w') as file:
                json.dump(self.settings, file, indent=4)
        except FileNotFoundError:
            print('Settings could not be saved!')

        # Sync QSettings with other instances
        QS().sync()

    def get_setting(self, setting):
        try:
            value = self.settings[setting]
        except KeyError:
            value = self.default_settings['settings'][setting]

        return value

    def change_project(self, new_project):
        self.pr = Project(self, new_project)
        self.settings['selected_project'] = new_project
        if new_project not in self.projects:
            self.projects.append(new_project)
        # Legacy
        transfer_file_params_to_single_subject(self)

    def remove_project(self, project):
        self.projects.remove(project)
        if self.pr.name == project:
            if len(self.projects) > 0:
                new_project = self.projects[0]
            else:
                new_project = get_user_input_string('Please enter the name of a new project!',
                                                    'Add Project', force=True)
            self.change_project(new_project)

        # Remove Project-Folder
        try:
            shutil.rmtree(join(self.projects_path, project))
        except OSError as error:
            print(error)
            logging.warning(f'The folder of {project} can\'t be deleted and has to be deleted manually!')

    def copy_parameters_between_projects(self, from_name, from_p_preset,
                                         to_name, to_p_preset):
        from_project = Project(self, from_name)
        if to_name == self.pr.name:
            to_project = self.pr
        else:
            to_project = Project(self, to_name)
        to_project.parameters[to_p_preset] = from_project.parameters[from_p_preset]
        to_project.save()

    def save(self, worker_signals=None):
        if self.pr is not None:

            # Save Project
            self.pr.save(worker_signals)
            self.settings['selected_project'] = self.pr.name

        self.save_settings()

    def load_edu(self):
        if self.edu_program_name is not None:
            edu_path = join(self.home_path, 'edu_programs', self.edu_program_name)
            with open(edu_path, 'r') as file:
                self.edu_program = json.load(file)

            self.all_pd_funcs = self.pd_funcs.copy()
            # Exclude functions which are not selected
            self.pd_funcs = self.pd_funcs.loc[self.pd_funcs.index.isin(self.edu_program['functions'])]

            # Change the Project-Scripts-Path to a new folder to store the Education-Project-Scripts separately
            self.pr.pscripts_path = join(self.pr.project_path, f'_pipeline_scripts{self.edu_program["name"]}')
            if not isdir(self.pr.pscripts_path):
                os.mkdir(self.pr.pscripts_path)
            self.pr.init_pipeline_scripts()

            # Exclude MEEG
            self.pr._all_meeg = self.pr.all_meeg.copy()
            self.pr.all_meeg = [meeg for meeg in self.pr.all_meeg if meeg in self.edu_program['meeg']]

            # Exclude FSMRI
            self.pr._all_fsmri = self.pr.all_fsmri.copy()
            self.pr.all_fsmri = [meeg for meeg in self.pr.all_meeg if meeg in self.edu_program['meeg']]

    def import_custom_modules(self):
        """
        Load all modules in basic_functions and custom_functions
        """

        self.errors['custom_modules'] = dict()

        # Load basic-modules
        # Add basic_functions to sys.path
        sys.path.insert(0, str(Path(basic_functions.__file__).parent))
        basic_functions_list = [x for x in dir(basic_functions) if '__' not in x]
        self.all_modules['basic'] = list()
        for module_name in basic_functions_list:
            self.all_modules['basic'].append(module_name)

        # Load custom_modules
        pd_functions_pattern = r'.*_functions\.csv'
        pd_parameters_pattern = r'.*_parameters\.csv'
        custom_module_pattern = r'(.+)(\.py)$'
        for directory in [d for d in os.scandir(self.custom_pkg_path) if not d.name.startswith('.')]:
            pkg_name = directory.name
            pkg_path = directory.path
            file_dict = {'functions': None, 'parameters': None, 'modules': list()}
            for file_name in [f for f in listdir(pkg_path) if not f.startswith(('.', '_'))]:
                functions_match = re.match(pd_functions_pattern, file_name)
                parameters_match = re.match(pd_parameters_pattern, file_name)
                custom_module_match = re.match(custom_module_pattern, file_name)
                if functions_match:
                    file_dict['functions'] = join(pkg_path, file_name)
                elif parameters_match:
                    file_dict['parameters'] = join(pkg_path, file_name)
                elif custom_module_match and custom_module_match.group(1) != '__init__':
                    file_dict['modules'].append(custom_module_match)

            # Check, that there is a whole set for a custom-module (module-file, functions, parameters)
            if all([value is not None or value != [] for value in file_dict.values()]):
                self.all_modules[pkg_name] = list()
                functions_path = file_dict['functions']
                parameters_path = file_dict['parameters']
                correct_count = 0
                for module_match in file_dict['modules']:
                    module_name = module_match.group(1)
                    # Add pkg-path to sys.path
                    sys.path.insert(0, pkg_path)
                    try:
                        import_module(module_name)
                    except:
                        exc_tuple = get_exception_tuple()
                        self.errors['custom_modules'][module_name] = exc_tuple
                    else:
                        correct_count += 1
                        # Add Module to dictionary
                        self.all_modules[pkg_name].append(module_name)

                # Make sure, that every module in modules is imported without error
                # (otherwise don't append to pd_funcs and pd_params)
                if len(file_dict['modules']) == correct_count:
                    try:
                        read_pd_funcs = pd.read_csv(functions_path, sep=';', index_col=0)
                        read_pd_params = pd.read_csv(parameters_path, sep=';', index_col=0)
                    except:
                        exc_tuple = get_exception_tuple()
                        self.errors['custom_modules'][pkg_name] = exc_tuple
                    else:
                        # Add pkg_name here (would be redundant in read_pd_funcs of each custom-package)
                        read_pd_funcs['pkg_name'] = pkg_name

                        # Check, that there are no duplicates
                        pd_funcs_to_append = read_pd_funcs.loc[~read_pd_funcs.index.isin(self.pd_funcs.index)]
                        self.pd_funcs = pd.concat([self.pd_funcs, pd_funcs_to_append])
                        pd_params_to_append = read_pd_params.loc[~read_pd_params.index.isin(self.pd_params.index)]
                        self.pd_params = pd.concat([self.pd_params, pd_params_to_append])

            else:
                error_text = f'Files for import of {pkg_name} are missing: ' \
                             f'{[key for key in file_dict if file_dict[key] is None]}'
                self.errors['custom_modules'][pkg_name] = error_text

    def reload_modules(self):
        for pkg_name in self.all_modules:
            for module_name in self.all_modules[pkg_name]:
                module = import_module(module_name)
                try:
                    reload(module)
                # Custom-Modules somehow can't be reloaded because spec is not found
                except ModuleNotFoundError:
                    spec = None
                    if spec:
                        # All errors occuring here will be caught by the UncaughtHook
                        spec.loader.exec_module(module)
                        sys.modules[module_name] = module

