import json
import os
from os import listdir
from os.path import isdir, isfile, join

import mne
import pandas as pd
from importlib import resources

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QInputDialog, QMessageBox

from mne_pipeline_hd.pipeline_functions.project import Project

home_dirs = ['custom_packages', 'freesurfer', 'projects']
project_dirs = ['_pipeline_scripts', 'data', 'figures']


class Controller:

    def __init__(self, home_path=None, current_project=None, edu_program_name=None):
        # Check Home-Path
        self.errors = dict()

        # Try to load home-path from QSettings
        if home_path is None:
            home_path = QSettings().value('home_path', defaultValue=None)
            if home_path is None:
                self.errors['home_path'] = f'No Home-Path found!'

        # Check if path exists
        if not isdir(home_path):
            self.errors['home_path'] = f'{home_path} not found!'

        # Check, if path is writable
        elif not os.access(home_path, os.W_OK):
            self.errors['home_path'] = f'{home_path} not writable!'

        else:
            self.home_path = home_path
            QSettings().setValue('home_path', home_path)
            # Create subdirectories if not existing for a valid home_path
            for subdir in [d for d in home_dirs if not isdir(join(home_path, d))]:
                os.mkdir(join(home_path, subdir))

            # Get Project-Folders (recognized by distinct sub-folders)
            self.projects_path = join(home_path, 'projects')
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
            if current_project is None:
                # Load settings to get current_project
                settings_path = join(home_path, 'mne_pipeline_hd-settings.json')
                if isfile(settings_path):
                    with open(settings_path, 'r') as file:
                        settings = json.load(file)
                        if 'current_project' in settings:
                            current_project = settings['current_project']

            if len(self.projects) == 0:
                self.errors['project'] = 'No projects!'

            elif current_project not in self.projects:
                self.errors['project'] = f'{current_project} not in projects!'

            else:
                self.current_project = current_project

            # Initialize Project
            self.pr = Project(self, self.current_project)

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

        # Check integrity of QSettings-Keys
        QSettings().sync()
        qs = set(QSettings().childKeys())
        ds = set(self.default_settings['qsettings'])
        # Remove additional (old) QSettings not appearing in default-settings
        for qsetting in qs - ds:
            QSettings().remove(qsetting)
        # Add new settings from default-settings which are not present in QSettings
        for qsetting in ds - qs:
            QSettings().setValue(qsetting, self.default_settings['qsettings'][qsetting])

    def save_settings(self):
        with open(join(self.home_path, 'mne_pipeline_hd-settings.json'), 'w') as file:
            json.dump(self.settings, file, indent=4)

        # Sync QSettings with other instances
        QSettings().sync()

    def get_setting(self, setting):
        try:
            value = self.settings[setting]
        except KeyError:
            value = self.default_settings['settings'][setting]

        return value

    def change_project(self, new_project):
        self.pr = Project(self, new_project)
        self.current_project = new_project
        self.settings['current_project'] = new_project
        if new_project not in self.projects:
            self.projects.append(new_project)

    def save(self, worker_signals):
        if worker_signals is not None:
            worker_signals.pgbar_text.emit('Saving Project...')

        # Save Project
        self.pr.save(worker_signals)

        if worker_signals is not None:
            worker_signals.pgbar_text.emit('Saving Settings...')

        self.settings['current_project'] = self.current_project
        self.save_settings()
