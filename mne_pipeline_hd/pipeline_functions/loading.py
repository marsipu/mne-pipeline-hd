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
from __future__ import print_function

import functools
import inspect
import itertools
import json
import os
import pickle
import shutil
from datetime import datetime
from os import listdir, makedirs, remove, rename
from os.path import exists, getsize, isdir, isfile, join
from pathlib import Path

import matplotlib.pyplot as plt
# Make use of program also possible with sensor-space installation of mne
from PyQt5.QtCore import QSettings

try:
    from mayavi import mlab
except ModuleNotFoundError:
    pass

import mne
import numpy as np

# ==============================================================================
# LOADING FUNCTIONS
# ==============================================================================
from mne_pipeline_hd.pipeline_functions.pipeline_utils import TypedJSONEncoder, type_json_hook


def load_decorator(load_func):
    @functools.wraps(load_func)
    def load_wrapper(*args, **kwargs):
        # Get Loading-Class
        obj_instance = args[0]

        # Get matching data-type from IO-Dict
        data_type = [k for k in obj_instance.io_dict
                     if obj_instance.io_dict[k]['load'] is not None
                     and obj_instance.io_dict[k]['load'].__name__ == load_func.__name__][0]

        print(f'Loading {data_type} for {obj_instance.name}')

        if data_type in obj_instance.data_dict:
            data = obj_instance.data_dict[data_type]
        else:
            # Todo: Dependencies!
            try:
                data = load_func(*args, **kwargs)
            except FileNotFoundError as fnf_err:
                if obj_instance.p_preset != 'Default':
                    print(f'No File for {data_type} from {obj_instance.name}'
                          f' with Parameter-Preset={obj_instance.p_preset} found, trying Default')

                    actual_p_preset = obj_instance.p_preset
                    obj_instance.p_preset = 'Default'
                    obj_instance.init_paths()

                    data = load_func(*args, **kwargs)

                    obj_instance.p_preset = actual_p_preset
                    obj_instance.init_paths()
                else:
                    raise fnf_err

        # Save data in data-dict for machines with big RAM
        if obj_instance.mw.qsettings['save_ram'] == 'false' or obj_instance.mw.qsettings['save_ram'] is False:
            obj_instance.data_dict[data_type] = data

        return data

    return load_wrapper


def save_decorator(save_func):
    @functools.wraps(save_func)
    def save_wrapper(*args, **kwargs):
        # Get Loading-Class
        obj_instance = args[0]

        # Get data-object
        if len(args) > 1:
            data = args[1]
        elif len(kwargs) > 0:
            data = kwargs[list(kwargs.keys())[0]]
        else:
            data = None

        # Get matching data-type from IO-Dict
        data_type = [k for k in obj_instance.io_dict
                     if obj_instance.io_dict[k]['save'] is not None
                     and obj_instance.io_dict[k]['save'].__name__ == save_func.__name__][0]

        # Make sure, that parent-directory exists
        paths = obj_instance._return_path_list(data_type)
        for path in [p for p in paths if not isdir(Path(p).parent)]:
            makedirs(Path(path).parent, exist_ok=True)

        print(f'Saving {data_type} for {obj_instance.name}')
        save_func(*args, **kwargs)

        # Save data in data-dict for machines with big RAM
        if QSettings().value('save_ram') == 'false' or QSettings().value('save_ram') is False:
            obj_instance.data_dict[data_type] = data

        # Save File-Parameters
        paths = obj_instance._return_path_list(data_type)
        for path in paths:
            obj_instance.save_file_params(path)

    return save_wrapper


class BaseLoading:
    """ Base-Class for Sub (The current File/MRI-File/Grand-Average-Group, which is executed)"""

    def __init__(self, name, main_win):
        # Basic Attributes (partly taking parameters or main-win-attributes for easier access)
        self.name = name
        self.mw = main_win
        self.pr = main_win.pr
        self.p_preset = self.pr.p_preset
        self.subjects_dir = self.mw.subjects_dir
        self.save_plots = self.mw.get_setting('save_plots')
        self.figures_path = self.pr.figures_path
        self.img_format = self.mw.get_setting('img_format')
        self.dpi = self.mw.get_setting('dpi')

        # Prepare file-parameters-dictionary for Loading-Object
        if self.name not in self.pr.file_parameters:
            self.pr.file_parameters[self.name] = dict()
        self.file_parameters = self.pr.file_parameters[self.name]

        self.data_dict = dict()
        self.existing_paths = dict()

        self.init_p_preset_deps()
        self.init_attributes()
        self.init_paths()

    def init_p_preset_deps(self):
        self.p = self.pr.parameters[self.p_preset]

        # Prepare plot-files-dictionary for Loading-Object
        if self.name not in self.mw.pr.plot_files:
            self.pr.plot_files[self.name] = dict()
        if self.p_preset not in self.mw.pr.plot_files[self.name]:
            self.pr.plot_files[self.name][self.p_preset] = dict()
        self.plot_files = self.pr.plot_files[self.name][self.p_preset]

    def init_attributes(self):
        """Initialization of additional attributes, should be overridden in inherited classes"""
        pass

    def init_paths(self):
        """Initialization of all paths and the io_dict, should be overridden in inherited classes"""
        self.save_dir = None
        self.io_dict = dict()

    def _return_path_list(self, data_type):
        paths = self.io_dict[data_type]['path']
        # Convert paths to list
        if not isinstance(paths, list):
            # from string
            if isinstance(paths, str):
                paths = [paths]
            elif isinstance(paths, dict):
                # from string in dictionary
                paths = list(paths.values())
                if len(paths) > 0:
                    # from nested list in dictionary
                    if isinstance(paths[0], list):
                        paths = list(itertools.chain.from_iterable(paths))
                    # from nested dictionary in dictionary
                    elif isinstance(paths[0], dict):
                        paths = list(itertools.chain.from_iterable([d.values() for d in paths]))

        return paths

    # Todo: Only save relevant parameters (with dependencies)
    def save_file_params(self, path):

        # Check existence of path and append appendices for hemispheres
        if not isfile(path):
            if isfile(path + '-lh.stc'):
                paths = [path + '-lh.stc', path + '-rh.stc']
            else:
                paths = list()
        else:
            paths = [path]

        for path in paths:
            file_name = Path(path).name

            if file_name not in self.file_parameters:
                self.file_parameters[file_name] = dict()
            # Get the name of the calling function (assuming it is 2 Frames above when running in pipeline)
            function = inspect.stack()[2][3]
            self.file_parameters[file_name]['FUNCTION'] = function

            if function in self.mw.pd_funcs.index:
                critical_params_str = self.mw.pd_funcs.loc[function, 'func_args']
                # Make sure there are no spaces left
                critical_params_str = critical_params_str.replace(' ', '')
                critical_params = critical_params_str.split(',')

                # Add critical parameters
                for p_name in [p for p in self.p if p in critical_params]:
                    self.file_parameters[file_name][p_name] = self.p[p_name]

            self.file_parameters[file_name]['NAME'] = self.name

            # Save Path relative to Home-Path (to avoid conflicts between OS)
            self.file_parameters[file_name]['PATH'] = os.path.relpath(path, self.pr.data_path)

            self.file_parameters[file_name]['TIME'] = datetime.now()

            self.file_parameters[file_name]['SIZE'] = getsize(path)

            self.file_parameters[file_name]['P_PRESET'] = self.p_preset

    def plot_save(self, plot_name, subfolder=None, trial=None, idx=None, matplotlib_figure=None, mayavi=False,
                  mayavi_figure=None, brain=None, dpi=None):
        """
        Save a plot with this method either by letting the figure be detected by the backend (pyplot, mayavi) or by
        supplying the figure directly.

        Parameters
        ----------
        plot_name : str
            The name of the folder and a part of the filename.
        subfolder : str | None
            An optional name for a subfolder, which will be also part of the filename.
        trial : str | None
            An optinal name of the trial if you have several trials from the same run.
        idx : int | str | None
            An optional index as enumerator for multiple plots.
        matplotlib_figure : matplotlib.figure.Figure | None
            Supply a matplotlib-figure here (if none is given, the current-figure will be taken with plt.savefig()).
        mayavi : bool
            Set to True without supplying a mayavi-figure to save the current figure with mlab.savefig().
        mayavi_figure : mayavi.core.scene.Scene | None
            Supply a mayavi-figure here.
        brain : surfer.Brain | None
            Supply a Brain-instance here.
        dpi :
            Set the dpi-setting if you want another than specified in the MainWindow-Settings

        """
        # Take DPI from Settings if not defined by call
        if not dpi:
            dpi = self.dpi

        if self.save_plots:
            # Folder is named by plot_name
            dir_path = join(self.figures_path, self.p_preset, plot_name)

            # Create Subfolder if necessary
            if subfolder:
                dir_path = join(dir_path, subfolder)

            # Create Subfolder for trial if necessary
            if trial:
                dir_path = join(dir_path, trial)

            # Create not existent folders
            if not isdir(dir_path):
                makedirs(dir_path)

            # Get file_name depending on present attributes
            base_name_sequence = [self.name, self.p_preset, plot_name]
            if trial:
                base_name_sequence.insert(1, trial)
            if subfolder:
                base_name_sequence.append(subfolder)
            if idx is not None:
                base_name_sequence.append(str(idx))

            # Join name-parts together with "--" and append the image-format
            file_name = '--'.join(base_name_sequence)
            file_name += self.img_format

            save_path = join(dir_path, file_name)
            # Get the plot-function and the save the path to the image
            calling_func = inspect.stack()[1][3]

            # Check if required keys are in the dictionary-levels
            if calling_func not in self.plot_files:
                self.plot_files[calling_func] = list()

            if matplotlib_figure:
                if isinstance(matplotlib_figure, list):
                    for ix, figure in enumerate(matplotlib_figure):
                        # Insert additional index in front of image-format (easier with removesuffix when moving to 3.9)
                        idx_file_name = f'{file_name[:-len(self.img_format)]}--{ix}{self.img_format}'
                        idx_file_path = join(dir_path, idx_file_name)
                        figure.savefig(idx_file_path)
                        print(f'figure: {idx_file_path} has been saved')
                        # Only store relative path to be compatible across OS
                        plot_files_save_path = os.path.relpath(idx_file_path, self.figures_path)
                        # Add Plot-Save-Path to plot_files if not already contained
                        if plot_files_save_path not in self.plot_files[calling_func]:
                            self.plot_files[calling_func].append(plot_files_save_path)
                else:
                    matplotlib_figure.savefig(save_path, dpi=dpi)
            elif mayavi_figure:
                mayavi_figure.savefig(save_path)
            elif brain:
                brain.save_image(save_path)
            elif mayavi:
                mlab.savefig(save_path, figure=mlab.gcf())
            else:
                plt.savefig(save_path, dpi=dpi)
            print(f'figure: {save_path} has been saved')

            if not isinstance(matplotlib_figure, list):
                # Only store relative path to be compatible across OS
                plot_files_save_path = os.path.relpath(save_path, self.figures_path)
                # Add Plot-Save-Path to plot_files if not already contained
                if plot_files_save_path not in self.plot_files[calling_func]:
                    self.plot_files[calling_func].append(plot_files_save_path)
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

    def load_json(self, file_name, default=None):
        file_path = join(self.save_dir, f'{self.name}_{self.p_preset}_{file_name}.json')
        try:
            with open(file_path, 'r') as file:
                data = json.load(file, object_hook=type_json_hook)
        except json.JSONDecodeError:
            print(f'{file_path} could not be loaded')
            data = default
        except FileNotFoundError:
            print(f'{file_path} could not be found')
            data = default

        return data

    def save_json(self, file_name, data):
        # If file-ending is supplied, remove it to avoid doubling
        if file_name[-5:] == '.json':
            file_name = file_name[:-5]
        file_path = join(self.save_dir, f'{self.name}_{self.p_preset}_{file_name}.json')
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, cls=TypedJSONEncoder, indent=4)
        except json.JSONDecodeError:
            print(f'{file_path} could not be saved')

        self.save_file_params(file_path)

    def get_existing_paths(self):
        """Get existing paths and add the mapped File-Type to existing_paths (set)"""
        self.existing_paths.clear()
        for data_type in self.io_dict:
            paths = self._return_path_list(data_type)
            if paths:
                self.existing_paths[data_type] = [p for p in paths if isfile(p) or isdir(p)
                                                  or isfile(p + '-lh.stc') or isfile(p + '-rh.stc')]
            else:
                self.existing_paths[data_type] = list()

    def remove_path(self, data_type):
        # Remove path specified by path_type (which is the name mapped to the path in self.paths_dict)
        # Dependent on Paramter-Preset
        paths = self._return_path_list(data_type)
        for p in paths:
            p_name = Path(p).name
            # Remove from file-parameters
            try:
                self.file_parameters.pop(p_name)
            except KeyError:
                # Accounting for Source-Estimate naming-conventions
                try:
                    p_name_lh = p_name + '-lh.stc'
                    p_name_rh = p_name + '-rh.stc'
                    for pn in [p_name_lh, p_name_rh]:
                        self.file_parameters.pop(pn)
                except KeyError:
                    print(f'{Path(p).name} not in file-parameters')
            try:
                remove(p)
            except FileNotFoundError:
                # Accounting for Source-Estimate naming-conventions
                try:
                    p_lh = p + '-lh.stc'
                    p_rh = p + '-rh.stc'
                    for ps in [p_lh, p_rh]:
                        os.remove(ps)
                except FileNotFoundError:
                    print(f'{p} was not found')
            except IsADirectoryError:
                try:
                    shutil.rmtree(p)
                except OSError as err:
                    print(f'{p} could not be removed due to {err}')
            except OSError as err:
                print(f'{p} could not be removed due to {err}')


class MEEG(BaseLoading):
    """ Class for File-Data in File-Loop"""

    def __init__(self, name, main_win, fsmri=None, suppress_warnings=True):
        self.fsmri = fsmri
        self.suppress_warnings = suppress_warnings
        super().__init__(name, main_win)

    def init_attributes(self):
        """Initialize additional attributes for MEEG"""
        # The assigned Empty-Room-Measurement if existing
        if self.name not in self.mw.pr.meeg_to_erm:
            self.erm = None
            if not self.suppress_warnings:
                print(f'No Empty-Room-Measurement assigned for {self.name}, defaulting to "None"')
        else:
            # Transition from 'None' to None (placed 30.01.2021, can be removed soon)
            if self.mw.pr.meeg_to_erm[self.name] == 'None':
                self.mw.pr.meeg_to_erm[self.name] = None
            self.erm = self.mw.pr.meeg_to_erm[self.name]

        # The assigned Freesurfer-MRI(already as FSMRI-Class)
        if self.name in self.mw.pr.meeg_to_fsmri:
            if self.fsmri and self.fsmri.name == self.mw.pr.meeg_to_fsmri[self.name]:
                pass
            else:
                self.fsmri = FSMRI(self.mw.pr.meeg_to_fsmri[self.name], self.mw)
        else:
            self.fsmri = FSMRI('None', self.mw)
            if not self.suppress_warnings:
                print(f'No Freesurfer-MRI-Subject assigned for {self.name}, defaulting to "None"')

        # The assigned bad-channels
        if self.name not in self.mw.pr.meeg_bad_channels:
            self.bad_channels = list()
            if not self.suppress_warnings:
                print(f'No bad channels assigned for {self.name}, defaulting to empty list')
        else:
            self.bad_channels = self.mw.pr.meeg_bad_channels[self.name]

        # The selected trials from the event-id
        if self.name not in self.mw.pr.sel_event_id:
            self.sel_trials = list()
            if not self.suppress_warnings:
                print(f'No Trials selected for {self.name}, defaulting to empty list')
        else:
            self.sel_trials = self.mw.pr.sel_event_id[self.name]

        # The assigned event-id
        if self.name not in self.mw.pr.meeg_event_id:
            self.event_id = dict()
            if not self.suppress_warnings:
                print(f'No EventID assigned for {self.name}, defaulting to empty dictionary')
        else:
            all_event_id = self.mw.pr.meeg_event_id[self.name]
            self.event_id = {key: value for key, value in all_event_id.items() if key in self.sel_trials}


    def init_paths(self):
        """Load Paths as attributes (depending on which Parameter-Preset is selected)"""

        # Main save directory
        self.save_dir = join(self.pr.data_path, self.name)

        # Data-Paths
        self.raw_path = join(self.save_dir, f'{self.name}-raw.fif')
        self.raw_filtered_path = join(self.save_dir, f'{self.name}_{self.p_preset}-filtered-raw.fif')
        if self.erm:
            self.erm_path = join(self.pr.data_path, self.erm, f'{self.erm}-raw.fif')
            self.old_erm_processed_path = join(self.pr.data_path, self.erm, f'{self.erm}_{self.p_preset}-raw.fif')
            self.erm_processed_path = join(self.pr.data_path, self.erm,
                                           f'{self.erm}-{self.name}_{self.p_preset}-processed-raw.fif')
        else:
            self.erm_path = None
            self.erm_processed_path = None
        self.events_path = join(self.save_dir, f'{self.name}_{self.p_preset}-eve.fif')
        self.epochs_path = join(self.save_dir, f'{self.name}_{self.p_preset}-epo.fif')
        self.reject_log_path = join(self.save_dir, f'{self.name}_{self.p_preset}-arlog.py')
        self.ica_path = join(self.save_dir, f'{self.name}_{self.p_preset}-ica.fif')
        self.eog_epochs_path = join(self.save_dir, f'{self.name}_{self.p_preset}-eog-epo.fif')
        self.ecg_epochs_path = join(self.save_dir, f'{self.name}_{self.p_preset}-ecg-epo.fif')
        self.evokeds_path = join(self.save_dir, f'{self.name}_{self.p_preset}-ave.fif')
        self.power_tfr_epochs_path = join(self.save_dir,
                                          f'{self.name}_{self.p_preset}_{self.p["tfr_method"]}-epo-pw-tfr.h5')
        self.itc_tfr_epochs_path = join(self.save_dir,
                                        f'{self.name}_{self.p_preset}_{self.p["tfr_method"]}-epo-itc-tfr.h5')
        self.power_tfr_average_path = join(self.save_dir,
                                           f'{self.name}_{self.p_preset}_{self.p["tfr_method"]}-ave-pw-tfr.h5')
        self.itc_tfr_average_path = join(self.save_dir,
                                         f'{self.name}_{self.p_preset}_{self.p["tfr_method"]}-ave-itc-tfr.h5')
        self.trans_path = join(self.save_dir, f'{self.fsmri.name}-trans.fif')
        self.forward_path = join(self.save_dir, f'{self.name}_{self.p_preset}-fwd.fif')
        self.calm_cov_path = join(self.save_dir, f'{self.name}_{self.p_preset}-calm-cov.fif')
        self.erm_cov_path = join(self.save_dir, f'{self.name}_{self.p_preset}-erm-cov.fif')
        self.noise_covariance_path = join(self.save_dir, f'{self.name}_{self.p_preset}-cov.fif')
        self.inverse_path = join(self.save_dir, f'{self.name}_{self.p_preset}-inv.fif')
        self.stc_paths = {trial: join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}-stc')
                          for trial in self.sel_trials}
        self.morphed_stc_paths = {trial: join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}-morphed')
                                  for trial in self.sel_trials}
        self.ecd_paths = {trial: {dip: join(self.save_dir, 'ecd_dipoles',
                                            f'{self.name}_{trial}_{self.p_preset}_{dip}-ecd-dip.dip')
                                  for dip in self.p['ecd_times']}
                          for trial in self.sel_trials}
        self.ltc_paths = {trial: {label: join(self.save_dir, 'label_time_course',
                                              f'{self.name}_{trial}_{self.p_preset}_{label}-ltc.npy')
                                  for label in self.p['target_labels']}
                          for trial in self.sel_trials}
        self.con_paths = {trial: {con_method: join(self.save_dir,
                                                   f'{self.name}_{trial}_{self.p_preset}_{con_method}-con.npy')
                                  for con_method in self.p['con_methods']}
                          for trial in self.sel_trials}

        # This dictionary contains entries for each data-type which is loaded to/saved from disk
        self.io_dict = {'Raw': {'path': self.raw_path,
                                'load': self.load_raw,
                                'save': self.save_raw},
                        'Raw (Filtered)': {'path': self.raw_filtered_path,
                                           'load': self.load_filtered,
                                           'save': self.save_filtered},
                        'EmptyRoom': {'path': self.erm_path,
                                      'load': self.load_erm,
                                      'save': None},
                        'EmptyRoom (Filtered)': {'path': self.erm_processed_path,
                                                 'load': self.load_erm_processed,
                                                 'save': self.save_erm_processed},
                        'Events': {'path': self.events_path,
                                   'load': self.load_events,
                                   'save': self.save_events},
                        'Epochs': {'path': self.epochs_path,
                                   'load': self.load_epochs,
                                   'save': self.save_epochs},
                        'RejectLog': {'path': self.reject_log_path,
                                      'load': self.load_reject_log,
                                      'save': self.save_reject_log},
                        'ICA': {'path': self.ica_path,
                                'load': self.load_ica,
                                'save': self.save_ica},
                        'Epochs (EOG)': {'path': self.eog_epochs_path,
                                         'load': self.load_eog_epochs,
                                         'save': self.save_eog_epochs},
                        'Epochs (ECG)': {'path': self.ecg_epochs_path,
                                         'load': self.load_ecg_epochs,
                                         'save': self.save_ecg_epochs},
                        'Evoked': {'path': self.evokeds_path,
                                   'load': self.load_evokeds,
                                   'save': self.save_evokeds},
                        'TF Power Epochs': {'path': self.power_tfr_epochs_path,
                                            'load': self.load_power_tfr_epochs,
                                            'save': self.save_power_tfr_epochs},
                        'TF ITC Epochs': {'path': self.itc_tfr_epochs_path,
                                          'load': self.load_itc_tfr_epochs,
                                          'save': self.save_itc_tfr_epochs},
                        'TF Power Average': {'path': self.power_tfr_average_path,
                                             'load': self.load_power_tfr_average,
                                             'save': self.save_power_tfr_average},
                        'TF ITC Average': {'path': self.itc_tfr_average_path,
                                           'load': self.load_itc_tfr_average,
                                           'save': self.save_itc_tfr_average},
                        'Transformation': {'path': self.trans_path,
                                           'load': self.load_transformation,
                                           'save': None},
                        'Forward Solution': {'path': self.forward_path,
                                             'load': self.load_forward,
                                             'save': self.save_forward},
                        'Noise Covariance': {'path': self.noise_covariance_path,
                                             'load': self.load_noise_covariance,
                                             'save': self.save_noise_covariance},
                        'Inverse Operator': {'path': self.inverse_path,
                                             'load': self.load_inverse_operator,
                                             'save': self.save_inverse_operator},
                        'Source Estimate': {'path': self.stc_paths,
                                            'load': self.load_source_estimates,
                                            'save': self.save_source_estimates},
                        'Source Estimate (Morphed)': {'path': self.morphed_stc_paths,
                                                      'load': self.load_morphed_source_estimates,
                                                      'save': self.save_morphed_source_estimates},
                        'ECD': {'path': self.ecd_paths,
                                'load': self.load_ecd,
                                'save': self.save_ecd},
                        'LTC': {'path': self.ltc_paths,
                                'load': self.load_ltc,
                                'save': self.save_ltc}}

    def rename(self, new_name):
        # Stor old name
        old_name = self.name
        old_save_dir = self.save_dir
        old_paths = dict()
        for data_type in self.io_dict:
            old_paths[data_type] = self._return_path_list(data_type)

        # Update paths
        self.name = new_name
        self.init_paths()

        # Rename save_dir
        rename(old_save_dir, self.save_dir)

        # Update entries in dictionaries
        self.mw.pr.meeg_to_erm[self.name] = self.mw.pr.meeg_to_erm[old_name].pop()
        self.mw.pr.meeg_to_fsmri[self.name] = self.mw.pr.meeg_to_fsmri[old_name].pop()
        self.mw.pr.meeg_bad_channels[self.name] = self.mw.pr.meeg_bad_channels[old_name].pop()
        self.mw.pr.meeg_event_id[self.name] = self.mw.pr.meeg_event_id[old_name].pop()
        self.mw.pr.sel_event_id[self.name] = self.mw.pr.sel_event_id[old_name].pop()
        self.init_attributes()

        # Rename old paths to new paths
        for data_type in self.io_dict:
            new_paths = self._return_path_list(data_type)
            for new_path in new_paths:
                old_path = old_paths[data_type]
                rename(old_path, new_path)

    ####################################################################################################################
    # Load- & Save-Methods
    ####################################################################################################################

    def load_info(self):
        return mne.io.read_info(self.raw_path)

    @load_decorator
    def load_raw(self):
        raw = mne.io.read_raw_fif(self.raw_path, preload=True)
        raw.info['bads'] = self.bad_channels
        return raw

    @save_decorator
    def save_raw(self, raw):
        raw.save(self.raw_path, overwrite=True)

    @load_decorator
    def load_filtered(self):
        return mne.io.read_raw_fif(self.raw_filtered_path, preload=True)

    @save_decorator
    def save_filtered(self, raw_filtered):
        raw_filtered.save(self.raw_filtered_path, overwrite=True)

    @load_decorator
    def load_erm(self):
        erm_raw = mne.io.read_raw_fif(self.erm_path, preload=True)
        if self.erm in self.pr.meeg_bad_channels:
            erm_raw.info['bads'] = self.pr.meeg_bad_channels[self.erm]
        return erm_raw

    @load_decorator
    def load_erm_processed(self):
        if isfile(self.old_erm_processed_path):
            os.remove(self.old_erm_processed_path)
        return mne.io.read_raw_fif(self.erm_processed_path, preload=True)

    @save_decorator
    def save_erm_processed(self, erm_filtered):
        erm_filtered.save(self.erm_processed_path, overwrite=True)

    @load_decorator
    def load_events(self):
        return mne.read_events(self.events_path)

    @save_decorator
    def save_events(self, events):
        mne.event.write_events(self.events_path, events)

    @load_decorator
    def load_epochs(self):
        return mne.read_epochs(self.epochs_path, proj=self.p['apply_proj'], preload=True)

    @save_decorator
    def save_epochs(self, epochs):
        epochs.save(self.epochs_path, overwrite=True)

    @load_decorator
    def load_reject_log(self):
        with open(self.reject_log_path, 'rb') as file:
            return pickle.load(file)

    @save_decorator
    def save_reject_log(self, reject_log):
        with open(self.reject_log_path, 'wb') as file:
            pickle.dump(reject_log, file)

    @load_decorator
    def load_ica(self):
        ica = mne.preprocessing.read_ica(self.ica_path)
        # Change ica.exclude to indices stored in ica_exclude.py for this MEEG-Object
        if self.name in self.pr.ica_exclude:
            ica.exclude = self.pr.ica_exclude[self.name]
        return ica

    @save_decorator
    def save_ica(self, ica):
        ica.save(self.ica_path)

    @load_decorator
    def load_eog_epochs(self):
        return mne.read_epochs(self.eog_epochs_path)

    @save_decorator
    def save_eog_epochs(self, eog_epochs):
        eog_epochs.save(self.eog_epochs_path, overwrite=True)

    @load_decorator
    def load_ecg_epochs(self):
        return mne.read_epochs(self.ecg_epochs_path)

    @save_decorator
    def save_ecg_epochs(self, ecg_epochs):
        ecg_epochs.save(self.ecg_epochs_path, overwrite=True)

    @load_decorator
    def load_evokeds(self):
        return mne.read_evokeds(self.evokeds_path, proj=self.p['apply_proj'])

    @save_decorator
    def save_evokeds(self, evokeds):
        mne.evoked.write_evokeds(self.evokeds_path, evokeds)

    @load_decorator
    def load_power_tfr_epochs(self):
        return mne.time_frequency.read_tfrs(self.power_tfr_epochs_path)

    @save_decorator
    def save_power_tfr_epochs(self, powers):
        mne.time_frequency.write_tfrs(self.power_tfr_epochs_path, powers, overwrite=True)

    @load_decorator
    def load_itc_tfr_epochs(self):
        return mne.time_frequency.read_tfrs(self.itc_tfr_epochs_path)

    @save_decorator
    def save_itc_tfr_epochs(self, itcs):
        mne.time_frequency.write_tfrs(self.itc_tfr_epochs_path, itcs, overwrite=True)

    @load_decorator
    def load_power_tfr_average(self):
        return mne.time_frequency.read_tfrs(self.power_tfr_average_path)

    @save_decorator
    def save_power_tfr_average(self, powers):
        mne.time_frequency.write_tfrs(self.power_tfr_average_path, powers, overwrite=True)

    @load_decorator
    def load_itc_tfr_average(self):
        return mne.time_frequency.read_tfrs(self.itc_tfr_average_path)

    @save_decorator
    def save_itc_tfr_average(self, itcs):
        mne.time_frequency.write_tfrs(self.itc_tfr_average_path, itcs, overwrite=True)

    @load_decorator
    def load_transformation(self):
        return mne.read_trans(self.trans_path)

    @load_decorator
    def load_forward(self):
        return mne.read_forward_solution(self.forward_path, verbose='WARNING')

    @save_decorator
    def save_forward(self, forward):
        mne.write_forward_solution(self.forward_path, forward, overwrite=True)

    @load_decorator
    def load_noise_covariance(self):
        return mne.read_cov(self.noise_covariance_path)

    @save_decorator
    def save_noise_covariance(self, noise_cov):
        mne.cov.write_cov(self.noise_covariance_path, noise_cov)

    @load_decorator
    def load_inverse_operator(self):
        return mne.minimum_norm.read_inverse_operator(self.inverse_path, verbose='WARNING')

    @save_decorator
    def save_inverse_operator(self, inverse):
        mne.minimum_norm.write_inverse_operator(self.inverse_path, inverse)

    @load_decorator
    def load_source_estimates(self):
        stcs = dict()
        for trial in self.stc_paths:
            stcs[trial] = mne.source_estimate.read_source_estimate(self.stc_paths[trial])

        return stcs

    @save_decorator
    def save_source_estimates(self, stcs):
        for trial in stcs:
            stcs[trial].save(self.stc_paths[trial])

    @load_decorator
    def load_morphed_source_estimates(self):
        morphed_stcs = dict()
        for trial in self.morphed_stc_paths:
            morphed_stcs[trial] = mne.source_estimate.read_source_estimate(self.morphed_stc_paths[trial])

        return morphed_stcs

    @save_decorator
    def save_morphed_source_estimates(self, morphed_stcs):
        for trial in morphed_stcs:
            morphed_stcs[trial].save(self.morphed_stc_paths[trial])

    def load_mixn_dipoles(self):
        mixn_dips = dict()
        for trial in self.sel_trials:
            idx = 0
            dip_list = list()
            for idx in range(len(listdir(join(self.save_dir, 'mixn_dipoles')))):
                mixn_dip_path = join(self.save_dir, 'mixn_dipoles',
                                     f'{self.name}_{trial}_{self.p_preset}-mixn-dip{idx}.dip')
                dip_list.append(mne.read_dipole(mixn_dip_path))
                idx += 1
            mixn_dips[trial] = dip_list
            print(f'{idx + 1} dipoles read for {self.name}-{trial}')

        return mixn_dips

    def save_mixn_dipoles(self, mixn_dips):
        # Remove old dipoles
        if not exists(join(self.save_dir, 'mixn_dipoles')):
            makedirs(join(self.save_dir, 'mixn_dipoles'))
        old_dipoles = listdir(join(self.save_dir, 'mixn_dipoles'))
        for file in old_dipoles:
            remove(join(self.save_dir, 'mixn_dipoles', file))

        for trial in mixn_dips:
            for idx, dip in enumerate(mixn_dips[trial]):
                mxn_dip_path = join(self.save_dir, 'mixn_dipoles',
                                    f'{self.name}_{trial}_{self.p_preset}-mixn-dip{idx}.dip')
                dip.save(mxn_dip_path)

    def load_mixn_source_estimates(self):
        mixn_stcs = dict()
        for trial in self.sel_trials:
            mx_stc_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}-mixn')
            mx_stc = mne.source_estimate.read_source_estimate(mx_stc_path)
            mixn_stcs.update({trial: mx_stc})

        return mixn_stcs

    def save_mixn_source_estimates(self, stcs):
        for trial in stcs:
            stc_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}-mixn')
            stcs[trial].save(stc_path)

    @load_decorator
    def load_ecd(self):
        ecd_dipoles = dict()
        for trial in self.ecd_paths:
            ecd_dipoles[trial] = dict()
            for dip in self.ecd_paths[trial]:
                ecd_dipoles[trial][dip] = mne.read_dipole(self.ecd_paths[trial][dip])

        return ecd_dipoles

    @save_decorator
    def save_ecd(self, ecd_dips):
        for trial in ecd_dips:
            for dip in ecd_dips[trial]:
                ecd_dips[trial][dip].save(self.ecd_paths[trial][dip], overwrite=True)

    @load_decorator
    def load_ltc(self):
        ltcs = dict()
        for trial in self.sel_trials:
            ltcs[trial] = dict()
            for label in self.ltc_paths[trial]:
                ltcs[trial][label] = np.load(self.ltc_paths[trial][label])

        return ltcs

    @save_decorator
    def save_ltc(self, ltcs):
        for trial in ltcs:
            for label in ltcs[trial]:
                np.save(self.ltc_paths[trial][label], ltcs[trial][label])

    @load_decorator
    def load_connectivity(self):
        con_dict = dict()
        for trial in self.con_paths:
            con_dict[trial] = dict()
            for con_method in self.con_paths[trial]:
                con_dict[trial][con_method] = np.load(self.con_paths[trial][con_method])

        return con_dict

    @save_decorator
    def save_connectivity(self, con_dict):
        for trial in con_dict:
            for con_method in con_dict[trial]:
                np.save(self.con_paths[trial][con_method])


class FSMRI(BaseLoading):
    # Todo: Store available parcellations, surfaces, etc. (maybe already loaded with import?)
    def __init__(self, name, main_win):
        if name is None:
            name = 'None'

        super().__init__(name, main_win)

    def init_attributes(self):
        """Initialize additional attributes for FSMRI"""
        self.fs_path = QSettings().value('fs_path')
        self.mne_path = QSettings().value('mne_path')

    def init_paths(self):
        # Main Path
        self.save_dir = join(self.mw.subjects_dir, self.name)

        # Data-Paths
        self.source_space_path = join(self.save_dir, 'bem', f'{self.name}_{self.p["source_space_spacing"]}-src.fif')
        # Todo: Bem-Paths with number of vertices in layers
        self.bem_model_path = join(self.save_dir, 'bem', f'{self.name}-bem.fif')
        self.bem_solution_path = join(self.save_dir, 'bem', f'{self.name}-bem-sol.fif')
        self.vol_source_space_path = join(self.save_dir, 'bem', f'{self.name}-vol-src.fif')
        self.source_morph_path = join(self.save_dir,
                                      f'{self.name}--to--{self.p["morph_to"]}_'
                                      f'{self.p["source_space_spacing"]}-morph.h5')

        # This dictionary contains entries for each data-type which is loaded to/saved from disk
        self.io_dict = {'Source-Space': {'path': self.source_space_path,
                                         'load': self.load_source_space,
                                         'save': self.save_source_space},
                        'BEM-Model': {'path': self.bem_model_path,
                                      'load': self.load_bem_model,
                                      'save': self.save_bem_model},
                        'BEM-Solution': {'path': self.bem_solution_path,
                                         'load': self.load_bem_solution,
                                         'save': self.save_bem_solution},
                        'Volume-Source-Space': {'path': self.vol_source_space_path,
                                                'load': self.load_vol_source_space,
                                                'save': self.save_vol_source_space},
                        'Source-Morph': {'path': self.source_morph_path,
                                         'load': self.load_source_morph,
                                         'save': self.save_source_morph}}

    ####################################################################################################################
    # Load- & Save-Methods
    ####################################################################################################################
    @load_decorator
    def load_source_space(self):
        return mne.source_space.read_source_spaces(self.source_space_path)

    @save_decorator
    def save_source_space(self, src):
        src.save(self.source_space_path, overwrite=True)

    @load_decorator
    def load_bem_model(self):
        return mne.read_bem_surfaces(self.bem_model_path)

    @save_decorator
    def save_bem_model(self, bem_model):
        mne.write_bem_surfaces(self.bem_model_path, bem_model, overwrite=True)

    @load_decorator
    def load_bem_solution(self):
        return mne.read_bem_solution(self.bem_solution_path)

    @save_decorator
    def save_bem_solution(self, bem_solution):
        mne.write_bem_solution(self.bem_solution_path, bem_solution, overwrite=True)

    @load_decorator
    def load_vol_source_space(self):
        return mne.source_space.read_source_spaces(self.vol_source_space_path)

    @save_decorator
    def save_vol_source_space(self, vol_source_space):
        vol_source_space.save(self.vol_source_space_path, overwrite=True)

    @load_decorator
    def load_source_morph(self):
        return mne.read_source_morph(self.source_morph_path)

    @save_decorator
    def save_source_morph(self, source_morph):
        source_morph.save(self.source_morph_path, overwrite=True)


class Group(BaseLoading):
    def __init__(self, name, main_win, suppress_warnings=True):
        self.suppress_warnings = suppress_warnings
        super().__init__(name, main_win)

    def init_attributes(self):
        """Initialize additional attributes for Group"""
        if self.name not in self.pr.all_groups:
            self.group_list = [None]
            if not self.suppress_warnings:
                print(f'No objects assigned for {self.name}, defaulting to empty list')
        else:
            self.group_list = self.pr.all_groups[self.name]

        # The assigned event-id
        if self.group_list[0] not in self.mw.pr.meeg_event_id:
            self.mw.pr.meeg_event_id[self.group_list[0]] = dict()
            if not self.suppress_warnings:
                print(f'No EventID assigned for {self.name}, defaulting to empty dictionary')
        self.event_id = self.mw.pr.meeg_event_id[self.group_list[0]]

        # The selected trials from the event-id
        if self.group_list[0] not in self.mw.pr.sel_event_id:
            self.mw.pr.sel_event_id[self.group_list[0]] = list()
            if not self.suppress_warnings:
                print(f'No Trials selected for {self.name}, defaulting to empty list')
        self.sel_trials = self.mw.pr.sel_event_id[self.group_list[0]]

    def init_paths(self):
        # Main Path
        self.save_dir = self.pr.save_dir_averages

        # Data Paths
        self.ga_evokeds_path = join(self.save_dir, 'evokeds', f'{self.name}_{self.p_preset}-ave.fif')
        self.ga_tfr_paths = {trial: join(self.save_dir, 'time-frequency',
                                         f'{self.name}_{trial}_{self.p_preset}-tfr.h5')
                             for trial in self.sel_trials}
        self.ga_stc_paths = {trial: join(self.save_dir, 'source-estimates',
                                         f'{self.name}_{trial}_{self.p_preset}')
                             for trial in self.sel_trials}
        self.ga_ltc_paths = {trial: {label: join(self.save_dir, 'label-time-courses',
                                                 f'{self.name}_{trial}_{self.p_preset}_{label}.npy')
                                     for label in self.p['target_labels']}
                             for trial in self.sel_trials}
        self.ga_con_paths = {trial: {con_method: join(self.save_dir, 'connectivity',
                                                      f'{self.name}_{trial}_{self.p_preset}_{con_method}.npy')
                                     for con_method in self.p['con_methods']}
                             for trial in self.sel_trials}

        # This dictionary contains entries for each data-type which is loaded to/saved from disk
        self.io_dict = {'Grand-Average Evokeds': {'path': self.ga_evokeds_path,
                                                  'load': self.load_ga_evokeds,
                                                  'save': self.save_ga_evokeds},
                        'Grand-Average TFR': {'path': self.ga_tfr_paths,
                                              'load': self.load_ga_tfr,
                                              'save': self.save_ga_tfr},
                        'Grand-Average STC': {'path': self.ga_stc_paths,
                                              'load': self.load_ga_stc,
                                              'save': self.save_ga_stc},
                        'Grand-Average LTC': {'path': self.ga_ltc_paths,
                                              'load': self.load_ga_ltc,
                                              'save': self.save_ga_ltc},
                        'Grand-Average Connectiviy': {'path': self.ga_con_paths,
                                                      'load': self.load_ga_con,
                                                      'save': self.save_ga_con}}

    ####################################################################################################################
    # Load- & Save-Methods
    ####################################################################################################################
    @load_decorator
    def load_ga_evokeds(self):
        return mne.read_evokeds(self.ga_evokeds_path)

    @save_decorator
    def save_ga_evokeds(self, ga_evokeds):
        mne.evoked.write_evokeds(self.ga_evokeds_path, ga_evokeds)

    @load_decorator
    def load_ga_tfr(self):
        ga_tfr = dict()
        for trial in self.sel_trials:
            ga_tfr[trial] = mne.time_frequency.read_tfrs(self.ga_tfr_paths[trial])[0]

        return ga_tfr

    @save_decorator
    def save_ga_tfr(self, ga_tfr):
        for trial in ga_tfr:
            ga_tfr[trial].save(self.ga_tfr_paths[trial], overwrite=True)

    @load_decorator
    def load_ga_stc(self):
        ga_stcs = dict()
        for trial in self.sel_trials:
            ga_stcs[trial] = mne.read_source_estimate(self.ga_stc_paths[trial])

        return ga_stcs

    @save_decorator
    def save_ga_stc(self, ga_stcs):
        for trial in ga_stcs:
            ga_stcs[trial].save(self.ga_stc_paths[trial])

    @load_decorator
    def load_ga_ltc(self):
        ga_ltc = dict()
        for trial in self.ga_ltc_paths:
            ga_ltc[trial] = dict()
            for label in self.ga_ltc_paths[trial]:
                ga_ltc[trial][label] = np.load(self.ga_ltc_paths[trial][label])

        return ga_ltc

    @save_decorator
    def save_ga_ltc(self, ga_ltc):
        for trial in ga_ltc:
            for label in ga_ltc[trial]:
                np.save(self.ga_ltc_paths[trial][label], ga_ltc[trial][label])

    @load_decorator
    def load_ga_con(self):
        ga_connect = dict()
        for trial in self.ga_con_paths:
            ga_connect[trial] = {}
            for con_method in self.ga_con_paths[trial]:
                ga_connect[trial][con_method] = np.load(self.ga_con_paths[trial][con_method])

        return ga_connect

    @save_decorator
    def save_ga_con(self, ga_con):
        for trial in ga_con:
            for con_method in ga_con[trial]:
                np.save(self.ga_con_paths[trial][con_method], ga_con[trial][con_method])
