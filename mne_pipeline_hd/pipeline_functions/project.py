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
import logging
import os
from ast import literal_eval
from copy import deepcopy
from os import listdir, makedirs
from os.path import exists, getsize, isfile, join
from pathlib import Path

import numpy as np

from .pipeline_utils import TypedJSONEncoder, count_dict_keys, encode_tuples, type_json_hook
from ..gui.gui_utils import WorkerDialog


class Project:
    """
    A class with attributes for all the paths, file-lists/dicts and parameters of the selected project
    """

    def __init__(self, main_win, name):
        self.mw = main_win
        self.name = name

        self.init_main_paths()
        self.init_attributes()
        self.init_pipeline_scripts()
        self.set_logging()
        self.load()
        # self.check_data()

    def init_main_paths(self):

        # Main folder of project
        self.project_path = join(self.mw.projects_path, self.name)
        # Folder to store the data
        self.data_path = join(self.project_path, 'data')
        # Folder to store the figures (with an additional subfolder for each parameter-preset)
        self.figures_path = join(self.project_path, 'figures')
        # A dedicated folder to store grand-average data
        self.save_dir_averages = join(self.data_path, 'grand_averages')
        # A folder to store all pipeline-scripts as .json-files
        self.pscripts_path = join(self.project_path, '_pipeline_scripts')

        self.main_paths = [self.mw.subjects_dir, self.data_path, self.save_dir_averages,
                           self.pscripts_path, self.mw.custom_pkg_path, self.figures_path]

        # Create or check existence of main_paths
        for path in self.main_paths:
            if not exists(path):
                makedirs(path)
                print(f'{path} created')

    def init_attributes(self):
        # Stores the names of all MEG/EEG-Files
        self.all_meeg = list()
        # Stores selected MEG/EEG-Files
        self.sel_meeg = list()
        # Stores Bad-Channels for each MEG/EEG-File
        self.meeg_bad_channels = dict()
        # Stores Event-ID for each MEG/EEG-File
        self.meeg_event_id = dict()
        # Stores selected event-id-labels
        self.sel_event_id = dict()
        # Stores the names of all Empty-Room-Files (MEG/EEG)
        self.all_erm = list()
        # Maps each MEG/EEG-File to a Empty-Room-File or None
        self.meeg_to_erm = dict()
        # Stores the names of all Freesurfer-Segmentation-Folders in Subjects-Dir
        self.all_fsmri = list()
        # Stores selected Freesurfer-Segmentations
        self.sel_fsmri = list()
        # Maps each MEG/EEG-File to a Freesurfer-Segmentation or None
        self.meeg_to_fsmri = dict()
        # Stores the ICA-Components to be excluded
        self.ica_exclude = dict()
        # Groups MEG/EEG-Files e.g. for Grand-Average
        self.all_groups = dict()
        # Stores selected Grand-Average-Groups
        self.sel_groups = list()
        # Stores paths of saved plots
        self.plot_files = dict()
        # Stores functions and if they are selected
        self.sel_functions = list()
        # Stores additional keyword-arguments for functions by function-name
        self.add_kwargs = dict()
        # Stores parameters for each Parameter-Preset
        self.parameters = dict()
        # Parameter-Preset
        self.p_preset = 'Default'
        # Stores parameters for each file saved to disk from the current run (know, what you did to your data)
        self.file_parameters = dict()

        # Attributes, which have their own special function for loading
        self.special_loads = ['parameters', 'p_preset']

    def init_pipeline_scripts(self):
        # Initiate Project-Lists and Dicts
        # Logging Path
        self.log_path = join(self.pscripts_path, '_pipeline.log')

        self.all_meeg_path = join(self.pscripts_path, f'all_meeg_{self.name}.json')
        self.sel_meeg_path = join(self.pscripts_path, f'selected_meeg_{self.name}.json')
        self.meeg_bad_channels_path = join(self.pscripts_path, f'meeg_bad_channels_{self.name}.json')
        self.meeg_event_id_path = join(self.pscripts_path, f'meeg_event_id_{self.name}.json')
        self.sel_event_id_path = join(self.pscripts_path, f'selected_event_ids_{self.name}.json')
        self.all_erm_path = join(self.pscripts_path, f'all_erm_{self.name}.json')
        self.meeg_to_erm_path = join(self.pscripts_path, f'meeg_to_erm_{self.name}.json')
        self.all_fsmri_path = join(self.pscripts_path, f'all_fsmri_{self.name}.json')
        self.sel_fsmri_path = join(self.pscripts_path, f'selected_fsmri_{self.name}.json')
        self.meeg_to_fsmri_path = join(self.pscripts_path, f'meeg_to_fsmri_{self.name}.json')
        self.ica_exclude_path = join(self.pscripts_path, f'ica_exclude_{self.name}.json')
        self.all_groups_path = join(self.pscripts_path, f'all_groups_{self.name}.json')
        self.sel_groups_path = join(self.pscripts_path, f'selected_groups_{self.name}.json')
        self.plot_files_path = join(self.pscripts_path, f'plot_files_{self.name}.json')
        self.sel_functions_path = join(self.pscripts_path, f'selected_functions_{self.name}.json')
        self.add_kwargs_path = join(self.pscripts_path, f'additional_kwargs_{self.name}.json')
        self.parameters_path = join(self.pscripts_path, f'parameters_{self.name}.json')
        self.sel_p_preset_path = join(self.pscripts_path, f'sel_p_preset_{self.name}.json')
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
                                  self.plot_files_path: 'plot_files',
                                  self.sel_functions_path: 'sel_functions',
                                  self.add_kwargs_path: 'add_kwargs',
                                  self.parameters_path: 'parameters',
                                  self.sel_p_preset_path: 'p_preset',
                                  self.file_parameters_path: 'file_parameters'}

    def set_logging(self):
        # Add File to logging
        logger = logging.getLogger()
        file_handler = logging.FileHandler(self.log_path, 'w')
        logger.addHandler(file_handler)

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
                          self.sel_functions_path: self.old_sel_funcs_path}

        for path in [p for p in self.path_to_attribute if self.path_to_attribute[p] not in self.special_loads]:
            attribute_name = self.path_to_attribute[path]
            try:
                with open(path, 'r') as file:
                    loaded_attribute = json.load(file, object_hook=type_json_hook)
                    # Make sure, that loaded object has same type as default from __init__
                    if isinstance(loaded_attribute, type(getattr(self, attribute_name))):
                        setattr(self, attribute_name, loaded_attribute)
            # Either empty file or no file, leaving default from __init__
            except (json.JSONDecodeError, FileNotFoundError):
                # Old Paths to allow transition (22.11.2020)
                try:
                    with open(self.old_paths[path], 'r') as file:
                        setattr(self, attribute_name, json.load(file, object_hook=type_json_hook))
                except (json.JSONDecodeError, FileNotFoundError, KeyError):
                    pass

    def load_parameters(self):
        try:
            with open(join(self.pscripts_path, f'parameters_{self.name}.json'), 'r') as read_file:
                loaded_parameters = json.load(read_file, object_hook=type_json_hook)

                for p_preset in loaded_parameters:
                    # Make sure, that only parameters, which exist in pd_params are loaded
                    for param in [p for p in loaded_parameters[p_preset] if p not in self.mw.pd_params.index]:
                        if '_exp' not in param:
                            loaded_parameters[p_preset].pop(param)

                    # Add parameters, which exist in pipeline_resources/parameters.csv,
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

    def load_default_param(self, param_name):
        string_param = self.mw.pd_params.loc[param_name, 'default']
        try:
            self.parameters[self.p_preset][param_name] = literal_eval(string_param)
        except (ValueError, SyntaxError):
            # Allow parameters to be defined by functions e.g. by numpy, etc.
            if self.mw.pd_params.loc[param_name, 'gui_type'] == 'FuncGui':
                self.parameters[self.p_preset][param_name] = eval(string_param, {'np': np})
                exp_name = param_name + '_exp'
                self.parameters[self.p_preset][exp_name] = string_param
            else:
                self.parameters[self.p_preset][param_name] = string_param

    def load_default_parameters(self):
        # Empty the dict for current Parameter-Preset
        self.parameters[self.p_preset] = dict()
        for param_name in self.mw.pd_params.index:
            self.load_default_param(param_name)

    def load_last_p_preset(self):
        try:
            with open(self.sel_p_preset_path, 'r') as read_file:
                self.p_preset = json.load(read_file)
                # If parameter-preset not in Parameters, load first Parameter-Key(=Parameter-Preset)
                if self.p_preset not in self.parameters:
                    self.p_preset = list(self.parameters.keys())[0]
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.p_preset = list(self.parameters.keys())[0]

    def load(self):
        self.load_lists()
        self.load_parameters()
        self.load_last_p_preset()

    def save(self, worker_signals=None):

        if worker_signals:
            worker_signals.pgbar_max.emit(len(self.path_to_attribute))

        for idx, path in enumerate(self.path_to_attribute):
            if worker_signals:
                worker_signals.pgbar_n.emit(idx)
                worker_signals.pgbar_text.emit(f'Saving {self.path_to_attribute[path]}')

            attribute = getattr(self, self.path_to_attribute[path], None)

            # Make sure the tuples are encoded correctly
            if isinstance(attribute, dict):
                attribute = deepcopy(attribute)
                encode_tuples(attribute)

            try:
                with open(path, 'w') as file:
                    json.dump(attribute, file, cls=TypedJSONEncoder, indent=4)

            except json.JSONDecodeError as err:
                print(f'There is a problem with path:\n'
                      f'{err}')

    def check_data(self):

        missing_objects = [x for x in listdir(self.data_path) if
                           x != 'grand_averages' and x not in self.all_meeg and x not in self.all_erm]

        for obj in missing_objects:
            self.all_meeg.append(obj)

        # Get Freesurfer-folders (with 'surf'-folder) from subjects_dir (excluding .files for Mac)
        read_dir = sorted([f for f in os.listdir(self.mw.subjects_dir) if not f.startswith('.')], key=str.lower)
        self.all_fsmri = [fsmri for fsmri in read_dir if exists(join(self.mw.subjects_dir, fsmri, 'surf'))]

        self.save()

    def _clean_file_parameters(self, worker_signals):

        # Set maximum for progress-bar
        worker_signals.pgbar_max.emit(count_dict_keys(self.file_parameters, max_level=3))

        remove_obj_keys = list()
        key_count = 0
        for obj_key in self.file_parameters:
            key_count += 1
            worker_signals.pgbar_n.emit(key_count)

            if obj_key not in self.all_meeg + self.all_erm + self.all_fsmri + list(self.all_groups.keys()):
                remove_obj_keys.append(obj_key)

            remove_files = list()
            n_remove_params = 0
            for file_name in self.file_parameters[obj_key]:
                key_count += 1
                worker_signals.pgbar_n.emit(key_count)

                path = self.file_parameters[obj_key][file_name]['PATH']
                # Can be changed to only relative path (12.02.2021)
                if not isfile(path) and not isfile(join(self.data_path, path)) \
                        and not isfile(join(self.data_path, obj_key, file_name)):
                    remove_files.append(file_name)

                # Remove lists (can be removed soon 12.02.2021)
                if isinstance(self.file_parameters[obj_key][file_name]['FUNCTION'], list):
                    self.file_parameters[obj_key][file_name]['FUNCTION'] = \
                        self.file_parameters[obj_key][file_name]['FUNCTION'][0]
                if isinstance(self.file_parameters[obj_key][file_name]['TIME'], list):
                    self.file_parameters[obj_key][file_name]['TIME'] = \
                        self.file_parameters[obj_key][file_name]['TIME'][0]

                function = self.file_parameters[obj_key][file_name]['FUNCTION']
                # ToDo: Why is there sometimes <module> as FUNCTION?
                if function == '<module>' or function not in self.mw.pd_funcs.index:
                    key_count += len(self.file_parameters[obj_key][file_name])
                    worker_signals.pgbar_n.emit(key_count)
                else:
                    remove_params = list()
                    # ToDo: Critical param-removal can/should be removed,
                    #  when file-parameters upgraded with dependencies
                    critical_params_str = self.mw.pd_funcs.loc[function, 'func_args']
                    # Make sure there are no spaces left
                    critical_params_str = critical_params_str.replace(' ', '')
                    critical_params = critical_params_str.split(',')
                    critical_params += ['FUNCTION', 'NAME', 'PATH', 'TIME', 'SIZE', 'P_PRESET']

                    for param in self.file_parameters[obj_key][file_name]:
                        key_count += 1
                        worker_signals.pgbar_n.emit(key_count)

                        # Cancel if canceled
                        if worker_signals.was_canceled:
                            print('Cleaning was canceled by user')
                            return

                        if param not in critical_params:
                            remove_params.append(param)

                    for param in remove_params:
                        self.file_parameters[obj_key][file_name].pop(param)

                    n_remove_params += len(remove_params)

            for file_name in remove_files:
                self.file_parameters[obj_key].pop(file_name)
            print(f'Removed {len(remove_files)} Files and {n_remove_params} Parameters from {obj_key}')

        for remove_key in remove_obj_keys:
            self.file_parameters.pop(remove_key)
        print(f'Removed {len(remove_obj_keys)} Objects from File-Parameters')

    def clean_file_parameters(self):
        WorkerDialog(self.mw, self._clean_file_parameters, show_buttons=True, show_console=True,
                     close_directly=False, title='Cleaning File-Parameters')

    def _clean_plot_files(self, worker_signals):
        all_image_paths = list()
        # Remove object-keys which no longer exist
        remove_obj = list()
        n_remove_ppreset = 0
        n_remove_funcs = 0

        worker_signals.pgbar_max.emit(count_dict_keys(self.plot_files, max_level=3))
        key_count = 0

        for obj_key in self.plot_files:
            key_count += 1
            worker_signals.pgbar_n.emit(key_count)

            if obj_key not in self.all_meeg + self.all_erm + self.all_fsmri + list(self.all_groups.keys()):
                remove_obj.append(obj_key)
            else:
                # Remove Parameter-Presets which no longer exist
                remove_p_preset = list()
                for p_preset in self.plot_files[obj_key]:
                    key_count += 1
                    worker_signals.pgbar_n.emit(key_count)

                    if p_preset not in self.parameters.keys():
                        key_count += len(self.plot_files[obj_key][p_preset])
                        worker_signals.pgbar_n.emit(key_count)

                        remove_p_preset.append(p_preset)
                    else:
                        # Remove funcs which no longer exist or got no paths left
                        remove_funcs = list()
                        for func in self.plot_files[obj_key][p_preset]:
                            key_count += 1
                            worker_signals.pgbar_n.emit(key_count)

                            # Cancel if canceled
                            if worker_signals.was_canceled:
                                print('Cleaning was canceled by user')
                                return

                            if func not in self.mw.pd_funcs.index:
                                remove_funcs.append(func)
                            else:
                                # Remove image-paths which no longer exist
                                for rel_image_path in self.plot_files[obj_key][p_preset][func]:
                                    image_path = Path(join(self.figures_path, rel_image_path))
                                    if not isfile(image_path) or self.figures_path in rel_image_path:
                                        self.plot_files[obj_key][p_preset][func].remove(rel_image_path)
                                    else:
                                        all_image_paths.append(str(image_path))
                                if len(self.plot_files[obj_key][p_preset][func]) == 0:
                                    # Keys can't be dropped from dictionary during iteration
                                    remove_funcs.append(func)

                        for remove_func_key in remove_funcs:
                            self.plot_files[obj_key][p_preset].pop(remove_func_key)
                        n_remove_funcs += len(remove_funcs)

                for remove_preset_key in remove_p_preset:
                    self.plot_files[obj_key].pop(remove_preset_key)
                n_remove_ppreset += len(remove_p_preset)

            print(f'Removed {n_remove_ppreset} Parameter-Presets and {n_remove_funcs} from {obj_key}')

        for remove_key in remove_obj:
            self.plot_files.pop(remove_key)
        print(f'Removed {len(remove_obj)} Objects from Plot-Files')

        # Remove image-files, which aren't listed in plot_files.
        free_space = 0
        print('Removing unregistered images...')
        n_removed_images = 0
        for root, _, files in os.walk(self.figures_path):
            files = [join(root, f) for f in files]
            for file_path in [fp for fp in files if str(Path(fp)) not in all_image_paths]:
                free_space += getsize(file_path)
                n_removed_images += 1
                os.remove(file_path)
        print(f'Removed {n_removed_images} images')

        # Remove empty folders (loop until all empty folders are removed)
        print('Removing empty folders...')
        n_removed_folders = 0
        folder_loop = True
        # Redo the file-walk because folders can get empty by deleting folders inside
        while folder_loop:
            folder_loop = False
            for root, folders, _ in os.walk(self.figures_path):
                folders = [join(root, fd) for fd in folders]
                for folder in [fdp for fdp in folders if len(listdir(fdp)) == 0]:
                    os.rmdir(folder)
                    n_removed_folders += 1
                    folder_loop = True
        print(f'Removed {n_removed_folders} folders')

        print(f'{round(free_space / (1024 ** 2), 2)} MB of space was freed!')

    def clean_plot_files(self):
        WorkerDialog(self.mw, self._clean_plot_files, show_buttons=True, show_console=True,
                     close_directly=False, title='Cleaning Plot-Files')
