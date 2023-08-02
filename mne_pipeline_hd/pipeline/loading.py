# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

from __future__ import print_function

import functools
import inspect
import itertools
import json
import logging
import os
import pickle
import shutil
from datetime import datetime
from os import listdir, makedirs, remove
from os.path import exists, getsize, isdir, isfile, join
from pathlib import Path

import matplotlib.pyplot as plt
import mne
import numpy as np
# =============================================================================
# LOADING FUNCTIONS
# =============================================================================
from tqdm import tqdm

from mne_pipeline_hd.pipeline.pipeline_utils import (
    TypedJSONEncoder,
    type_json_hook,
    QS,
    _test_run,
)

sample_paths = {
    "raw": "sample_audvis_raw.fif",
    "erm": "ernoise_raw.fif",
    "events": "sample_audvis_raw-eve.fif",
    "trans": "sample_audvis_raw-trans.fif",
}


def _get_data_type_from_func(self, func, method):
    # Get matching data-type from IO-Dict
    func_name = func.__name__
    data_type = None
    for dt in self.io_dict:
        io_func = self.io_dict[dt][method]
        if getattr(io_func, "__name__", None) == func_name:
            data_type = dt
            break
    if data_type is None:
        raise RuntimeError(f"No datatype for loading-function {func_name}!")

    return data_type


def load_decorator(load_func):
    @functools.wraps(load_func)
    def load_wrapper(self, *args, **kwargs):
        # Get matching data-type from IO-Dict
        data_type = _get_data_type_from_func(self, load_func, "load")
        print(f"Loading {data_type} for {self.name}")

        if data_type in self.data_dict:
            data = self.data_dict[data_type]
        else:
            # Todo: Dependencies!
            try:
                data = load_func(self, *args, **kwargs)
            except OSError as err:
                deprc_path = self.deprecated_paths.get(data_type, "")
                if isfile(deprc_path):
                    new_path = self.io_dict[data_type]["path"]
                    self.io_dict[data_type]["path"] = deprc_path
                    data = load_func(self, *args, **kwargs)
                    self.io_dict[data_type]["path"] = new_path
                    logging.info(
                        f"Deprecated path: Saving file for "
                        f"{data_type} in updated path..."
                    )
                    # Save data with new path
                    save_func = self.io_dict[data_type]["save"]
                    # Does only support save-functions with no extra args
                    save_func(self, data)
                    # Remove deprecated path
                    os.remove(deprc_path)

                elif self.p_preset != "Default":
                    print(
                        f"No File for {data_type} from {self.name}"
                        f" with Parameter-Preset={self.p_preset} found,"
                        f" trying Default"
                    )

                    actual_p_preset = self.p_preset
                    self.p_preset = "Default"
                    self.init_paths()

                    data = load_func(*args, **kwargs)

                    self.p_preset = actual_p_preset
                    self.init_paths()
                else:
                    raise err

        # Save data in data-dict for machines with big RAM
        if not QS().value("save_ram"):
            self.data_dict[data_type] = data

        return data

    return load_wrapper


def save_decorator(save_func):
    @functools.wraps(save_func)
    def save_wrapper(self, *args, **kwargs):
        # Get matching data-type from IO-Dict
        data_type = _get_data_type_from_func(self, save_func, "save")

        # Get data-object
        if len(args) > 1:
            data = args[1]
        elif len(kwargs) > 0:
            data = kwargs[list(kwargs.keys())[0]]
        else:
            data = None

        # Make sure, that parent-directory exists
        paths = self._return_path_list(data_type)
        for path in [p for p in paths if not isdir(Path(p).parent)]:
            makedirs(Path(path).parent, exist_ok=True)

        print(f"Saving {data_type} for {self.name}")
        save_func(self, *args, **kwargs)

        # Save data in data-dict for machines with big RAM
        if not QS().value("save_ram"):
            self.data_dict[data_type] = data

        # Save File-Parameters
        paths = self._return_path_list(data_type)
        for path in paths:
            self.save_file_params(path)

    return save_wrapper


class BaseLoading:
    """Base-Class for Sub (The current File/MRI-File/Grand-Average-Group,
    which is executed)"""

    def __init__(self, name, controller):
        # Basic Attributes (partly taking parameters or main-win-attributes
        # for easier access)
        self.name = name
        self.ct = controller
        self.pr = controller.pr
        self.p_preset = self.pr.p_preset
        self.subjects_dir = self.ct.subjects_dir
        self.save_plots = self.ct.get_setting("save_plots")
        self.figures_path = self.pr.figures_path
        self.img_format = self.ct.get_setting("img_format")
        self.dpi = self.ct.get_setting("dpi")

        self.data_dict = dict()
        self.existing_paths = dict()

        if name is not None:
            self.init_parameters()
            self.init_attributes()
            self.init_paths()
            self.load_file_parameter_file()

    def init_parameters(self):
        self.pa = self.pr.parameters[self.p_preset]

        # Prepare plot-files-dictionary for Loading-Object
        if self.name not in self.pr.plot_files:
            self.pr.plot_files[self.name] = dict()
        if self.p_preset not in self.pr.plot_files[self.name]:
            self.pr.plot_files[self.name][self.p_preset] = dict()
        self.plot_files = self.pr.plot_files[self.name][self.p_preset]

    def get_parameter(self, parameter_name):
        """Get parameter from parameter-dictionary"""

        if parameter_name in self.pa:
            return self.pa[parameter_name]
        else:
            raise KeyError(f"Parameter {parameter_name} not found in parameters")

    def init_attributes(self):
        """Initialization of additional attributes, should be overridden
        in inherited classes"""
        pass

    def init_paths(self):
        """Initialization of all paths and the io_dict, should be overridden
        in inherited classes"""
        self.save_dir = None
        self.io_dict = dict()
        self.deprecated_paths = dict()

    def _return_path_list(self, data_type):
        paths = self.io_dict[data_type]["path"]
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
                        paths = list(
                            itertools.chain.from_iterable([d.values() for d in paths])
                        )

        return paths

    def load_file_parameter_file(self):
        self.file_parameters_path = join(
            self.save_dir, f"_{self.name}_file_parameters.json"
        )
        try:
            with open(self.file_parameters_path, "r") as file:
                self.file_parameters = json.load(file, object_hook=type_json_hook)
        except (json.JSONDecodeError, FileNotFoundError):
            self.file_parameters = dict()

    def save_file_parameter_file(self):
        # Save File-Parameters file
        with open(self.file_parameters_path, "w") as file:
            json.dump(self.file_parameters, file, cls=TypedJSONEncoder, indent=4)

    def save_file_params(self, path):
        # Check existence of path and append appendices for hemispheres
        if not isfile(path):
            if isfile(path + "-lh.stc"):
                paths = [path + "-lh.stc", path + "-rh.stc"]
            else:
                paths = list()
        else:
            paths = [path]

        for path in paths:
            file_name = Path(path).name

            if file_name not in self.file_parameters:
                self.file_parameters[file_name] = dict()
            # Get the name of the calling function (assuming it is 2 Frames
            # above when running in pipeline)
            function = inspect.stack()[2][3]
            self.file_parameters[file_name]["FUNCTION"] = function

            if function in self.ct.pd_funcs.index:
                critical_params_str = self.ct.pd_funcs.loc[function, "func_args"]
                # Make sure there are no spaces left
                critical_params_str = critical_params_str.replace(" ", "")
                critical_params = critical_params_str.split(",")

                # Add critical parameters
                for p_name in [p for p in self.pa if p in critical_params]:
                    self.file_parameters[file_name][p_name] = self.pa[p_name]

            self.file_parameters[file_name]["NAME"] = self.name

            self.file_parameters[file_name]["TIME"] = str(datetime.now())

            self.file_parameters[file_name]["SIZE"] = getsize(path)

            self.file_parameters[file_name]["P_PRESET"] = self.p_preset

        self.save_file_parameter_file()

    def clean_file_parameters(self):
        remove_files = list()
        n_remove_params = 0
        for file_name in self.file_parameters:
            # Can be changed to only relative path (12.02.2021)
            if not isfile(join(self.save_dir, file_name)):
                remove_files.append(file_name)

            # Remove lists (can be removed soon 12.02.2021)
            if isinstance(self.file_parameters[file_name]["FUNCTION"], list):
                self.file_parameters[file_name]["FUNCTION"] = self.file_parameters[
                    file_name
                ]["FUNCTION"][0]
            if isinstance(self.file_parameters[file_name]["TIME"], list):
                self.file_parameters[file_name]["TIME"] = self.file_parameters[
                    file_name
                ]["TIME"][0]

            function = self.file_parameters[file_name]["FUNCTION"]
            # ToDo: Why is there sometimes <module> as FUNCTION?
            if function == "<module>" or function not in self.ct.pd_funcs.index:
                pass
            else:
                remove_params = list()
                critical_params_str = self.ct.pd_funcs.loc[function, "func_args"]
                # Make sure there are no spaces left
                critical_params_str = critical_params_str.replace(" ", "")
                critical_params = critical_params_str.split(",")
                critical_params += ["FUNCTION", "NAME", "TIME", "SIZE", "P_PRESET"]

                for param in self.file_parameters[file_name]:
                    if param not in critical_params:
                        remove_params.append(param)

                for param in remove_params:
                    self.file_parameters[file_name].pop(param)

                n_remove_params += len(remove_params)

        for file_name in remove_files:
            self.file_parameters.pop(file_name)
        print(
            f"Removed {len(remove_files)} Files " f"and {n_remove_params} Parameters."
        )
        self.save_file_parameter_file()

    # Todo: Type recognition
    def plot_save(
        self,
        plot_name,
        subfolder=None,
        trial=None,
        idx=None,
        matplotlib_figure=None,
        brain=None,
        brain_movie_kwargs=None,
        dpi=None,
        img_format=None,
    ):
        """
        Save a plot with this method either by letting the figure be detected
         by the backend (pyplot, mayavi) or by
        supplying the figure directly.

        Parameters
        ----------
        plot_name : str
            The name of the folder and a part of the filename.
        subfolder : str | None
            An optional name for a subfolder, which will be also part of the
            filename.
        trial : str | None
            An optinal name of the trial if you have several trials from the
             same run.
        idx : int | str | None
            An optional index as enumerator for multiple plots.
        matplotlib_figure : matplotlib.figure.Figure | None
            Supply a matplotlib-figure here (if none is given,
             the current-figure will be taken with plt.savefig()).
        brain : mne.viz.Brain | None
            Supply a Brain-instance here.
        brain_movie_kwargs : dict
            Supply keyword-arguments for brain.save_movie() here.
        dpi :
            Set the dpi-setting if you want another than specified
             in the MainWindow-Settings.
        img_format : str | None
            Set the image format if other then saved in settings.
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
            file_name = "--".join(base_name_sequence)
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
                        # Insert additional index in front of image-format
                        # (easier with removesuffix when moving to 3.9)
                        idx_file_name = (
                            f"{file_name[:-len(self.img_format)]}"
                            f"--{ix}{self.img_format}"
                        )
                        idx_file_path = join(dir_path, idx_file_name)
                        figure.savefig(idx_file_path)
                        print(f"figure: {idx_file_path} has been saved")
                        # Only store relative path to be compatible across OS
                        plot_files_save_path = os.path.relpath(
                            idx_file_path, self.figures_path
                        )
                        # Add Plot-Save-Path to plot_files
                        # if not already contained
                        if plot_files_save_path not in self.plot_files[calling_func]:
                            self.plot_files[calling_func].append(plot_files_save_path)
                else:
                    matplotlib_figure.savefig(save_path, dpi=dpi)
            elif brain:
                if brain_movie_kwargs is not None:
                    time_dilation = brain_movie_kwargs["stc_animation_dilat"]
                    tmin, tmax = brain_movie_kwargs["stc_animation_span"]
                    brain.save_movie(
                        save_path, time_dilation=time_dilation, tmin=tmin, tmax=tmax
                    )
                else:
                    brain.save_image(save_path)
            else:
                plt.savefig(save_path, dpi=dpi)
            print(f"figure: {save_path} has been saved")

            if not isinstance(matplotlib_figure, list):
                # Only store relative path to be compatible across OS
                plot_files_save_path = os.path.relpath(save_path, self.figures_path)
                # Add Plot-Save-Path to plot_files if not already contained
                if plot_files_save_path not in self.plot_files[calling_func]:
                    self.plot_files[calling_func].append(plot_files_save_path)
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

    def load(self, data_type, **kwargs):
        """General load function with data_type as parameter."""
        return self.io_dict[data_type]["load"](**kwargs)

    def save(self, data_type, data, **kwargs):
        """General save function with data_type as parameter."""
        self.io_dict[data_type]["save"](data, **kwargs)

    def load_json(self, file_name, default=None):
        file_path = join(self.save_dir, f"{self.name}_{self.p_preset}_{file_name}.json")
        try:
            with open(file_path, "r") as file:
                data = json.load(file, object_hook=type_json_hook)
        except json.JSONDecodeError:
            print(f"{file_path} could not be loaded")
            data = default
        except FileNotFoundError:
            print(f"{file_path} could not be found")
            data = default

        return data

    def save_json(self, file_name, data):
        # If file-ending is supplied, remove it to avoid doubling
        if file_name[-5:] == ".json":
            file_name = file_name[:-5]
        file_path = join(self.save_dir, f"{self.name}_{self.p_preset}_{file_name}.json")
        try:
            with open(file_path, "w") as file:
                json.dump(data, file, cls=TypedJSONEncoder, indent=4)
        except json.JSONDecodeError:
            print(f"{file_path} could not be saved")

        self.save_file_params(file_path)

    def get_existing_paths(self):
        """Get existing paths and add the mapped File-Type
        to existing_paths (set)"""
        self.existing_paths.clear()
        for data_type in self.io_dict:
            paths = self._return_path_list(data_type)
            if paths:
                self.existing_paths[data_type] = [
                    p
                    for p in paths
                    if isfile(p)
                    or isdir(p)
                    or isfile(p + "-lh.stc")
                    or isfile(p + "-rh.stc")
                ]
            else:
                self.existing_paths[data_type] = list()

    def remove_path(self, data_type):
        # Remove path specified by path_type (which is the name
        # mapped to the path in self.paths_dict)
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
                    p_name_lh = p_name + "-lh.stc"
                    p_name_rh = p_name + "-rh.stc"
                    for pn in [p_name_lh, p_name_rh]:
                        self.file_parameters.pop(pn)
                except KeyError:
                    print(f"{Path(p).name} not in file-parameters")
            try:
                remove(p)
            except FileNotFoundError:
                # Accounting for Source-Estimate naming-conventions
                try:
                    p_lh = p + "-lh.stc"
                    p_rh = p + "-rh.stc"
                    for ps in [p_lh, p_rh]:
                        os.remove(ps)
                except FileNotFoundError:
                    print(f"{p} was not found")
            except IsADirectoryError:
                try:
                    shutil.rmtree(p)
                except OSError as err:
                    print(f"{p} could not be removed due to {err}")
            except OSError as err:
                print(f"{p} could not be removed due to {err}")


class MEEG(BaseLoading):
    """Class for File-Data in File-Loop"""

    def __init__(self, name, controller, fsmri=None, suppress_warnings=True):
        self.fsmri = fsmri
        self.suppress_warnings = suppress_warnings
        super().__init__(name, controller)

        if name == "_sample_":
            self.init_sample()

    def init_attributes(self):
        """Initialize additional attributes for MEEG"""
        # The assigned Empty-Room-Measurement if existing
        if self.name not in self.pr.meeg_to_erm:
            self.erm = None
            if not self.suppress_warnings:
                print(
                    f"No Empty-Room-Measurement assigned for {self.name},"
                    f' defaulting to "None"'
                )
        else:
            # Transition from 'None' to None (placed 30.01.2021,
            # can be removed soon)
            if self.pr.meeg_to_erm[self.name] == "None":
                self.pr.meeg_to_erm[self.name] = None
            self.erm = self.pr.meeg_to_erm[self.name]

        # The assigned Freesurfer-MRI(already as FSMRI-Class)
        if self.name in self.pr.meeg_to_fsmri:
            if self.fsmri and self.fsmri.name == self.pr.meeg_to_fsmri[self.name]:
                pass
            else:
                self.fsmri = FSMRI(self.pr.meeg_to_fsmri[self.name], self.ct)
        else:
            self.fsmri = FSMRI(None, self.ct)
            if not self.suppress_warnings:
                print(
                    f"No Freesurfer-MRI-Subject assigned for {self.name},"
                    f' defaulting to "None"'
                )

        # The assigned bad-channels
        if self.name not in self.pr.meeg_bad_channels:
            self.bad_channels = list()
            if not self.suppress_warnings:
                print(
                    f"No bad channels assigned for {self.name},"
                    f" defaulting to empty list"
                )
        else:
            self.bad_channels = self.pr.meeg_bad_channels[self.name]

        # The selected trials from the event-id
        if self.name not in self.pr.sel_event_id:
            self.sel_trials = list()
            if not self.suppress_warnings:
                print(
                    f"No Trials selected for {self.name}," f" defaulting to empty list"
                )
        else:
            self.sel_trials = self.pr.sel_event_id[self.name]

        # The assigned event-id
        if self.name not in self.pr.meeg_event_id:
            self.event_id = dict()
            if not self.suppress_warnings:
                print(
                    f"No EventID assigned for {self.name},"
                    f" defaulting to empty dictionary"
                )
        else:
            # Only inlcude event-ids which are selected
            self.event_id = {
                key: value
                for key, value in self.pr.meeg_event_id[self.name].items()
                if any([k in self.sel_trials for k in key.split("/")])
            }

        # The excluded ica-components
        if self.name not in self.pr.meeg_ica_exclude:
            self.ica_exclude = list()
        else:
            self.ica_exclude = self.pr.meeg_ica_exclude[self.name]

    def init_paths(self):
        """Load Paths as attributes
        (depending on which Parameter-Preset is selected)"""

        # Main save directory
        self.save_dir = join(self.pr.data_path, self.name)
        if not isdir(self.save_dir):
            os.mkdir(self.save_dir)

        # Data-Paths
        self.raw_path = join(self.save_dir, f"{self.name}-raw.fif")
        self.raw_filtered_path = join(
            self.save_dir, f"{self.name}_{self.p_preset}-filtered-raw.fif"
        )
        if self.erm:
            self.erm_path = join(self.pr.data_path, self.erm, f"{self.erm}-raw.fif")
            self.old_erm_processed_path = join(
                self.pr.data_path, self.erm, f"{self.erm}_{self.p_preset}-raw.fif"
            )
            self.erm_processed_path = join(
                self.pr.data_path,
                self.erm,
                f"{self.erm}-{self.name}_{self.p_preset}-processed-raw.fif",
            )
        else:
            self.erm_path = None
            self.erm_processed_path = None
        self.events_path = join(self.save_dir, f"{self.name}_{self.p_preset}-eve.fif")
        self.epochs_path = join(self.save_dir, f"{self.name}_{self.p_preset}-epo.fif")
        self.reject_log_path = join(
            self.save_dir, f"{self.name}_{self.p_preset}-arlog.py"
        )
        self.ica_path = join(self.save_dir, f"{self.name}_{self.p_preset}-ica.fif")
        self.eog_epochs_path = join(
            self.save_dir, f"{self.name}_{self.p_preset}-eog-epo.fif"
        )
        self.ecg_epochs_path = join(
            self.save_dir, f"{self.name}_{self.p_preset}-ecg-epo.fif"
        )
        self.evokeds_path = join(self.save_dir, f"{self.name}_{self.p_preset}-ave.fif")
        self.power_tfr_epochs_path = join(
            self.save_dir,
            f"{self.name}_{self.p_preset}_" f'#{self.pa["tfr_method"]}-epo-pw-tfr.h5',
        )
        self.itc_tfr_epochs_path = join(
            self.save_dir,
            f"{self.name}_{self.p_preset}_" f'{self.pa["tfr_method"]}-epo-itc-tfr.h5',
        )
        self.power_tfr_average_path = join(
            self.save_dir,
            f"{self.name}_{self.p_preset}_" f'{self.pa["tfr_method"]}-ave-pw-tfr.h5',
        )
        self.itc_tfr_average_path = join(
            self.save_dir,
            f"{self.name}_{self.p_preset}_" f'{self.pa["tfr_method"]}-ave-itc-tfr.h5',
        )
        self.trans_path = join(self.save_dir, f"{self.fsmri.name}-trans.fif")
        self.forward_path = join(self.save_dir, f"{self.name}_{self.p_preset}-fwd.fif")
        self.source_morph_path = join(
            self.save_dir,
            f'{self.name}--to--{self.pa["morph_to"]}_'
            f'{self.pa["src_spacing"]}-morph.h5',
        )
        self.calm_cov_path = join(
            self.save_dir, f"{self.name}_{self.p_preset}-calm-cov.fif"
        )
        self.erm_cov_path = join(
            self.save_dir, f"{self.name}_{self.p_preset}-erm-cov.fif"
        )
        self.noise_covariance_path = join(
            self.save_dir, f"{self.name}_{self.p_preset}-cov.fif"
        )
        self.inverse_path = join(self.save_dir, f"{self.name}_{self.p_preset}-inv.fif")
        self.stc_paths = {
            trial: join(self.save_dir, f"{self.name}_{trial}_{self.p_preset}-stc")
            for trial in self.sel_trials
        }
        self.morphed_stc_paths = {
            trial: join(self.save_dir, f"{self.name}_{trial}_{self.p_preset}-morphed")
            for trial in self.sel_trials
        }
        self.ecd_paths = {
            trial: {
                dip: join(
                    self.save_dir,
                    "ecd_dipoles",
                    f"{self.name}_{trial}_{self.p_preset}_{dip}-ecd-dip.dip",
                )
                for dip in self.pa["ecd_times"]
            }
            for trial in self.sel_trials
        }
        self.ltc_paths = {
            trial: {
                label: join(
                    self.save_dir,
                    "label_time_course",
                    f"{self.name}_{trial}_{self.p_preset}_{label}-ltc.npy",
                )
                for label in self.pa["target_labels"]
            }
            for trial in self.sel_trials
        }
        self.con_paths = {
            trial: {
                con_method: join(
                    self.save_dir,
                    f"{self.name}_{trial}_{self.p_preset}_{con_method}-con.npy",
                )
                for con_method in self.pa["con_methods"]
            }
            for trial in self.sel_trials
        }

        # This dictionary contains entries for each data-type
        # which is loaded to/saved from disk
        self.io_dict = {
            "raw": {
                "path": self.raw_path,
                "load": self.load_raw,
                "save": self.save_raw,
            },
            "raw_filtered": {
                "path": self.raw_filtered_path,
                "load": self.load_filtered,
                "save": self.save_filtered,
            },
            "erm": {"path": self.erm_path, "load": self.load_erm, "save": None},
            "erm_filtered": {
                "path": self.erm_processed_path,
                "load": self.load_erm_processed,
                "save": self.save_erm_processed,
            },
            "events": {
                "path": self.events_path,
                "load": self.load_events,
                "save": self.save_events,
            },
            "epochs": {
                "path": self.epochs_path,
                "load": self.load_epochs,
                "save": self.save_epochs,
            },
            "reject_log": {
                "path": self.reject_log_path,
                "load": self.load_reject_log,
                "save": self.save_reject_log,
            },
            "ica": {
                "path": self.ica_path,
                "load": self.load_ica,
                "save": self.save_ica,
            },
            "epochs_eog": {
                "path": self.eog_epochs_path,
                "load": self.load_eog_epochs,
                "save": self.save_eog_epochs,
            },
            "epochs_ecg": {
                "path": self.ecg_epochs_path,
                "load": self.load_ecg_epochs,
                "save": self.save_ecg_epochs,
            },
            "evoked": {
                "path": self.evokeds_path,
                "load": self.load_evokeds,
                "save": self.save_evokeds,
            },
            "evoked_eog": {"path": None, "load": self.load_eog_evokeds, "save": None},
            "evoked_ecg": {"path": None, "load": self.load_ecg_evokeds, "save": None},
            "tf_power_epochs": {
                "path": self.power_tfr_epochs_path,
                "load": self.load_power_tfr_epochs,
                "save": self.save_power_tfr_epochs,
            },
            "tf_itc_epochs": {
                "path": self.itc_tfr_epochs_path,
                "load": self.load_itc_tfr_epochs,
                "save": self.save_itc_tfr_epochs,
            },
            "tf_power_average": {
                "path": self.power_tfr_average_path,
                "load": self.load_power_tfr_average,
                "save": self.save_power_tfr_average,
            },
            "tf_itc_average": {
                "path": self.itc_tfr_average_path,
                "load": self.load_itc_tfr_average,
                "save": self.save_itc_tfr_average,
            },
            "trans": {
                "path": self.trans_path,
                "load": self.load_transformation,
                "save": None,
            },
            "forward": {
                "path": self.forward_path,
                "load": self.load_forward,
                "save": self.save_forward,
            },
            "morph": {
                "path": self.source_morph_path,
                "load": self.load_source_morph,
                "save": self.save_source_morph,
            },
            "noise_cov": {
                "path": self.noise_covariance_path,
                "load": self.load_noise_covariance,
                "save": self.save_noise_covariance,
            },
            "inverse": {
                "path": self.inverse_path,
                "load": self.load_inverse_operator,
                "save": self.save_inverse_operator,
            },
            "stcs": {
                "path": self.stc_paths,
                "load": self.load_source_estimates,
                "save": self.save_source_estimates,
            },
            "stcs_morphed": {
                "path": self.morphed_stc_paths,
                "load": self.load_morphed_source_estimates,
                "save": self.save_morphed_source_estimates,
            },
            "ecd": {
                "path": self.ecd_paths,
                "load": self.load_ecd,
                "save": self.save_ecd,
            },
            "ltc": {
                "path": self.ltc_paths,
                "load": self.load_ltc,
                "save": self.save_ltc,
            },
            "src_con": {
                "path": self.con_paths,
                "load": self.load_connectivity,
                "save": self.save_connectivity,
            },
        }

        self.deprecated_paths = {
            "stcs": {
                trial: join(self.save_dir, f"{self.name}_{trial}_{self.p_preset}")
                for trial in self.sel_trials
            }
        }

    def init_sample(self):
        # Add _sample_ to project and update attributes
        self.pr.all_erm.append("ernoise")
        self.erm = "ernoise"
        self.pr.meeg_to_erm[self.name] = self.erm
        self.init_paths()

        # Load sample
        test_data_folder = join(mne.datasets.sample.data_path(), "MEG", "sample")

        for data_type in sample_paths:
            test_file_name = sample_paths[data_type]
            test_file_path = join(test_data_folder, test_file_name)
            file_path = self.io_dict[data_type]["path"]

            if isfile(test_file_path) and not isfile(file_path):
                print(f"Copying {data_type} from sample-dataset...")
                folder = Path(file_path).parent
                if not isdir(folder):
                    os.mkdir(folder)
                shutil.copy2(test_file_path, file_path)
                print("Done!")

        self.bad_channels = self.load_info()["bads"]
        self.pr.meeg_bad_channels[self.name] = self.bad_channels

    def rename(self, new_name):
        # Stor old name
        old_name = self.name
        all_old_paths = dict()
        for data_type in self.io_dict:
            all_old_paths[data_type] = self._return_path_list(data_type)

        # Update paths
        self.name = new_name
        self.init_paths()

        self.pr.all_meeg = [new_name if n == old_name else n for n in self.pr.all_meeg]
        if old_name in self.pr.sel_meeg:
            self.pr.sel_meeg = [
                new_name if n == old_name else n for n in self.pr.sel_meeg
            ]

        # Update entries in dictionaries
        # ToDo: Rename Plot-Files
        # ToDo: Rename File-Parameters
        self.pr.meeg_to_erm[self.name] = self.pr.meeg_to_erm.pop(old_name)
        self.pr.meeg_to_fsmri[self.name] = self.pr.meeg_to_fsmri.pop(old_name)
        self.pr.meeg_bad_channels[self.name] = self.pr.meeg_bad_channels.pop(old_name)
        self.pr.meeg_event_id[self.name] = self.pr.meeg_event_id.pop(old_name)
        self.pr.sel_event_id[self.name] = self.pr.sel_event_id.pop(old_name)
        self.init_attributes()

        # Rename old paths to new paths
        for data_type in self.io_dict:
            new_paths = self._return_path_list(data_type)
            old_paths = all_old_paths[data_type]
            for new_path, old_path in zip(new_paths, old_paths):
                if isfile(old_path):
                    os.renames(old_path, new_path)

    def set_bad_channels(self, bad_channels):
        self.bad_channels = bad_channels
        self.pr.meeg_bad_channels[self.name] = self.bad_channels

    def set_ica_exclude(self, ica_exclude):
        self.ica_exclude = ica_exclude
        self.pr.meeg_ica_exclude[self.name] = self.ica_exclude

    ###########################################################################
    # Load- & Save-Methods
    ###########################################################################

    def load_info(self):
        return mne.io.read_info(self.raw_path)

    @load_decorator
    def load_raw(self):
        raw = mne.io.read_raw_fif(self.raw_path, preload=True)
        raw.info["bads"] = [bc for bc in self.bad_channels if bc in raw.ch_names]
        return raw

    @save_decorator
    def save_raw(self, raw):
        raw.save(self.raw_path, fmt=raw.orig_format, overwrite=True)

    @load_decorator
    def load_filtered(self):
        raw = mne.io.read_raw_fif(self.raw_filtered_path, preload=True)
        raw.info["bads"] = [bc for bc in self.bad_channels if bc in raw.ch_names]
        return raw

    @save_decorator
    def save_filtered(self, raw_filtered):
        raw_filtered.save(
            self.raw_filtered_path, fmt=raw_filtered.orig_format, overwrite=True
        )

    @load_decorator
    def load_erm(self):
        erm_raw = mne.io.read_raw_fif(self.erm_path, preload=True)
        return erm_raw

    @load_decorator
    def load_erm_processed(self):
        if isfile(self.old_erm_processed_path):
            os.remove(self.old_erm_processed_path)
        return mne.io.read_raw_fif(self.erm_processed_path, preload=True)

    @save_decorator
    def save_erm_processed(self, erm_filtered):
        erm_filtered.save(
            self.erm_processed_path, fmt=erm_filtered.orig_format, overwrite=True
        )

    @load_decorator
    def load_events(self):
        return mne.read_events(self.events_path)

    @save_decorator
    def save_events(self, events):
        mne.write_events(self.events_path, events, overwrite=True)

    @load_decorator
    def load_epochs(self):
        return mne.read_epochs(
            self.epochs_path, proj=self.pa["apply_proj"], preload=True
        )

    @save_decorator
    def save_epochs(self, epochs):
        epochs.save(self.epochs_path, overwrite=True)

    @load_decorator
    def load_reject_log(self):
        with open(self.reject_log_path, "rb") as file:
            return pickle.load(file)

    @save_decorator
    def save_reject_log(self, reject_log):
        with open(self.reject_log_path, "wb") as file:
            pickle.dump(reject_log, file)

    @load_decorator
    def load_ica(self):
        ica = mne.preprocessing.read_ica(self.ica_path)
        # Change ica.exclude to indices stored in ica_exclude.py
        # for this MEEG-Object
        if self.name in self.pr.meeg_ica_exclude:
            ica.exclude = self.pr.meeg_ica_exclude[self.name]
        return ica

    @save_decorator
    def save_ica(self, ica):
        ica.save(self.ica_path, overwrite=True)

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
        return mne.read_evokeds(self.evokeds_path, proj=self.pa["apply_proj"])

    @save_decorator
    def save_evokeds(self, evokeds):
        mne.evoked.write_evokeds(self.evokeds_path, evokeds, overwrite=True)

    @load_decorator
    def load_eog_evokeds(self):
        return self.load_eog_epochs().average()

    @load_decorator
    def load_ecg_evokeds(self):
        return self.load_ecg_epochs().average()

    @load_decorator
    def load_power_tfr_epochs(self):
        return mne.time_frequency.read_tfrs(self.power_tfr_epochs_path)

    @save_decorator
    def save_power_tfr_epochs(self, powers):
        mne.time_frequency.write_tfrs(
            self.power_tfr_epochs_path, powers, overwrite=True
        )

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
        mne.time_frequency.write_tfrs(
            self.power_tfr_average_path, powers, overwrite=True
        )

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
        return mne.read_forward_solution(self.forward_path, verbose="WARNING")

    @save_decorator
    def save_forward(self, forward):
        mne.write_forward_solution(self.forward_path, forward, overwrite=True)

    @load_decorator
    def load_source_morph(self):
        return mne.read_source_morph(self.source_morph_path)

    @save_decorator
    def save_source_morph(self, source_morph):
        source_morph.save(self.source_morph_path, overwrite=True)

    @load_decorator
    def load_noise_covariance(self):
        return mne.read_cov(self.noise_covariance_path)

    @save_decorator
    def save_noise_covariance(self, noise_cov):
        mne.cov.write_cov(self.noise_covariance_path, noise_cov, overwrite=True)

    @load_decorator
    def load_inverse_operator(self):
        return mne.minimum_norm.read_inverse_operator(
            self.inverse_path, verbose="WARNING"
        )

    @save_decorator
    def save_inverse_operator(self, inverse):
        mne.minimum_norm.write_inverse_operator(
            self.inverse_path, inverse, overwrite=True
        )

    @load_decorator
    def load_source_estimates(self):
        stcs = dict()
        for trial in self.stc_paths:
            stcs[trial] = mne.source_estimate.read_source_estimate(
                self.stc_paths[trial]
            )

        return stcs

    @save_decorator
    def save_source_estimates(self, stcs):
        for trial in stcs:
            stcs[trial].save(self.stc_paths[trial], overwrite=True)

    @load_decorator
    def load_morphed_source_estimates(self):
        morphed_stcs = dict()
        for trial in self.morphed_stc_paths:
            morphed_stcs[trial] = mne.source_estimate.read_source_estimate(
                self.morphed_stc_paths[trial]
            )

        return morphed_stcs

    @save_decorator
    def save_morphed_source_estimates(self, morphed_stcs):
        for trial in morphed_stcs:
            morphed_stcs[trial].save(self.morphed_stc_paths[trial], overwrite=True)

    def load_mixn_dipoles(self):
        mixn_dips = dict()
        for trial in self.sel_trials:
            idx = 0
            dip_list = list()
            for idx in range(len(listdir(join(self.save_dir, "mixn_dipoles")))):
                mixn_dip_path = join(
                    self.save_dir,
                    "mixn_dipoles",
                    f"{self.name}_{trial}_" f"{self.p_preset}-mixn-dip{idx}.dip",
                )
                dip_list.append(mne.read_dipole(mixn_dip_path))
                idx += 1
            mixn_dips[trial] = dip_list
            print(f"{idx + 1} dipoles read for {self.name}-{trial}")

        return mixn_dips

    def save_mixn_dipoles(self, mixn_dips):
        # Remove old dipoles
        if not exists(join(self.save_dir, "mixn_dipoles")):
            makedirs(join(self.save_dir, "mixn_dipoles"))
        old_dipoles = listdir(join(self.save_dir, "mixn_dipoles"))
        for file in old_dipoles:
            remove(join(self.save_dir, "mixn_dipoles", file))

        for trial in mixn_dips:
            for idx, dip in enumerate(mixn_dips[trial]):
                mxn_dip_path = join(
                    self.save_dir,
                    "mixn_dipoles",
                    f"{self.name}_{trial}_" f"{self.p_preset}-mixn-dip{idx}.dip",
                )
                dip.save(mxn_dip_path, overwrite=True)

    def load_mixn_source_estimates(self):
        mixn_stcs = dict()
        for trial in self.sel_trials:
            mx_stc_path = join(
                self.save_dir, f"{self.name}_{trial}_{self.p_preset}-mixn"
            )
            mx_stc = mne.source_estimate.read_source_estimate(mx_stc_path)
            mixn_stcs.update({trial: mx_stc})

        return mixn_stcs

    def save_mixn_source_estimates(self, stcs):
        for trial in stcs:
            stc_path = join(self.save_dir, f"{self.name}_{trial}_{self.p_preset}-mixn")
            stcs[trial].save(stc_path, overwrite=True)

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
                ltc_path = self.ltc_paths[trial][label]
                if isfile(ltc_path):
                    ltcs[trial][label] = np.load(ltc_path)
                else:
                    raise FileNotFoundError(
                        f"No Label-Time-Course found "
                        f"for trial {trial} "
                        f"in label {label}!"
                    )

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
                np.save(self.con_paths[trial][con_method], con_dict[trial][con_method])


class FSMRI(BaseLoading):
    def __init__(self, name, controller, load_labels=False):
        if name == "fsaverage" and not isfile(
            join(controller.subjects_dir, "fsaverage/mri/T1.mgz")
        ):
            if _test_run():
                test_data_folder = join(
                    mne.datasets.sample.data_path(), "subjects", "fsaverage"
                )
                shutil.copytree(test_data_folder, join(controller.subjects_dir, name))
            else:
                try:
                    logging.info("Downloading fsaverage...")
                    mne.datasets.fetch_fsaverage(subjects_dir=controller.subjects_dir)
                # Not working on macOS for mne<=0.24
                except ValueError:
                    logging.warning("fsaverage could not be downloaded!")

        self.load_labels = load_labels
        super().__init__(name, controller)

    def init_attributes(self):
        """Initialize additional attributes for FSMRI"""
        self.fs_path = QS().value("fs_path")
        self.mne_path = QS().value("mne_path")

        # Initialize Parcellations and Labels
        if self.load_labels:
            self.parcellations = self._get_available_parc()
            self.labels = self._get_available_labels()
        else:
            self.parcellations = None
            self.labels = None

    def init_paths(self):
        # Main Path
        self.save_dir = join(self.subjects_dir, self.name)

        # Data-Paths
        self.src_path = join(
            self.save_dir,
            "bem",
            f'{self.name}_{self.p_preset}_{self.pa["src_spacing"]}-src.fif',
        )
        self.bem_model_path = join(
            self.save_dir, "bem", f"{self.name}_{self.p_preset}-bem.fif"
        )
        self.bem_solution_path = join(
            self.save_dir, "bem", f"{self.name}_{self.p_preset}-bem-sol.fif"
        )
        self.vol_src_path = join(
            self.save_dir, "bem", f"{self.name}_{self.p_preset}-vol-src.fif"
        )

        # This dictionary contains entries for each data-type
        # which is loaded to/saved from disk
        self.io_dict = {
            "src": {
                "path": self.src_path,
                "load": self.load_source_space,
                "save": self.save_source_space,
            },
            "bem_model": {
                "path": self.bem_model_path,
                "load": self.load_bem_model,
                "save": self.save_bem_model,
            },
            "bem_solution": {
                "path": self.bem_solution_path,
                "load": self.load_bem_solution,
                "save": self.save_bem_solution,
            },
            "volume_src": {
                "path": self.vol_src_path,
                "load": self.load_volume_source_space,
                "save": self.save_volume_source_space,
            },
        }

        self.deprecated_paths = {
            "src": join(
                self.save_dir, "bem", f'{self.name}_{self.pa["src_spacing"]}-src.fif'
            ),
            "bem_model": join(self.save_dir, "bem", f"{self.name}-bem.fif"),
            "bem_solution": join(self.save_dir, "bem", f"{self.name}-bem-sol.fif"),
            "volume_src": join(self.save_dir, "bem", f"{self.name}-vol-src.fif"),
        }

    def _get_available_parc(self):
        annot_dir = join(self.subjects_dir, self.name, "label")
        try:
            files = os.listdir(annot_dir)
            annotations = [file[3:-6] for file in files if file[-6:] == ".annot"]
        except FileNotFoundError:
            annotations = list()

        return annotations

    def _get_available_labels(self):
        labels = dict()
        labels["Other"] = list()
        label_dir = join(self.subjects_dir, self.name, "label")
        try:
            files = os.listdir(label_dir)
            for label_path in tqdm(
                [str(lp) for lp in files if lp[-6:] == ".label"],
                desc="Loading labels...",
                ascii=True,
            ):
                label = mne.read_label(join(label_dir, label_path), self.name)
                labels["Other"].append(label)
        except FileNotFoundError:
            logging.warning(f"No label directory found for {self.name}!")

        if self.parcellations is None:
            self.parcellations = self._get_available_parc()

        for parcellation in tqdm(
            self.parcellations, desc="Loading parcellations...", ascii=True
        ):
            try:
                labels[parcellation] = mne.read_labels_from_annot(
                    self.name,
                    parcellation,
                    subjects_dir=self.subjects_dir,
                    verbose="warning",
                )
            except RuntimeError:
                print(f"Parcellation {parcellation} could not be loaded!")

        return labels

    def get_labels(self, target_labels):
        labels = list()
        if target_labels is not None:
            if self.labels is None:
                self.labels = self._get_available_labels()
            for label_list in self.labels.values():
                labels += [lb for lb in label_list if lb.name in target_labels]

        return labels

    ###########################################################################
    # Load- & Save-Methods
    ###########################################################################
    @load_decorator
    def load_source_space(self):
        return mne.read_source_spaces(self.src_path)

    @save_decorator
    def save_source_space(self, src):
        src.save(self.src_path, overwrite=True)

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
    def load_volume_source_space(self):
        return mne.read_source_spaces(self.vol_src_path)

    @save_decorator
    def save_volume_source_space(self, vol_src):
        vol_src.save(self.vol_src_path, overwrite=True)


class Group(BaseLoading):
    def __init__(self, name, controller, suppress_warnings=True):
        self.suppress_warnings = suppress_warnings
        super().__init__(name, controller)

    def init_attributes(self):
        """Initialize additional attributes for Group"""
        if self.name not in self.pr.all_groups:
            self.group_list = []
            if not self.suppress_warnings:
                print(
                    f"No objects assigned for {self.name}," f" defaulting to empty list"
                )
        else:
            self.group_list = self.pr.all_groups[self.name]

        # The assigned event-id
        self.event_id = dict()
        for group_item in [
            gi for gi in self.group_list if gi in self.ct.pr.meeg_event_id
        ]:
            self.event_id = {**self.event_id, **self.ct.pr.meeg_event_id[group_item]}

        # The selected trials from the event-id
        self.sel_trials = set()
        for group_item in [
            gi for gi in self.group_list if gi in self.ct.pr.sel_event_id
        ]:
            self.sel_trials = self.sel_trials | set(self.ct.pr.sel_event_id[group_item])

        # The fsmri where all group members are morphed to
        self.fsmri = FSMRI(self.pa["morph_to"], self.ct)

    def init_paths(self):
        # Main Path
        self.save_dir = self.pr.save_dir_averages
        if not isdir(self.save_dir):
            os.mkdir(self.save_dir)

        # Data Paths
        self.ga_evokeds_paths = {
            trial: join(
                self.save_dir,
                "evokeds",
                f"{self.name}_{trial}_" f"{self.p_preset}-ave.fif",
            )
            for trial in self.sel_trials
        }
        self.ga_tfr_paths = {
            trial: join(
                self.save_dir,
                "time-frequency",
                f"{self.name}_{trial}_" f"{self.p_preset}-tfr.h5",
            )
            for trial in self.sel_trials
        }
        self.ga_stc_paths = {
            trial: join(
                self.save_dir,
                "source-estimates",
                f"{self.name}_{trial}_" f"{self.p_preset}",
            )
            for trial in self.sel_trials
        }
        self.ga_ltc_paths = {
            trial: {
                label: join(
                    self.save_dir,
                    "label-time-courses",
                    f"{self.name}_{trial}_" f"{self.p_preset}_{label}.npy",
                )
                for label in self.pa["target_labels"]
            }
            for trial in self.sel_trials
        }
        self.ga_con_paths = {
            trial: {
                con_method: join(
                    self.save_dir,
                    "connectivity",
                    f"{self.name}_{trial}_" f"{self.p_preset}_{con_method}.npy",
                )
                for con_method in self.pa["con_methods"]
            }
            for trial in self.sel_trials
        }

        # This dictionary contains entries for each data-type
        # which is loaded to/saved from disk
        self.io_dict = {
            "grand_avg_evoked": {
                "path": self.ga_evokeds_paths,
                "load": self.load_ga_evokeds,
                "save": self.save_ga_evokeds,
            },
            "grand_avg_tfr": {
                "path": self.ga_tfr_paths,
                "load": self.load_ga_tfr,
                "save": self.save_ga_tfr,
            },
            "grand_avg_stc": {
                "path": self.ga_stc_paths,
                "load": self.load_ga_stc,
                "save": self.save_ga_stc,
            },
            "grand_avg_ltc": {
                "path": self.ga_ltc_paths,
                "load": self.load_ga_ltc,
                "save": self.save_ga_ltc,
            },
            "grand_avg_src_con": {
                "path": self.ga_con_paths,
                "load": self.load_ga_con,
                "save": self.save_ga_con,
            },
        }

        self.deprecated_paths = {}

    ###########################################################################
    # Load- & Save-Methods
    ###########################################################################
    def load_items(self, obj_type="MEEG", data_type=None):
        """Returns a generator for group items."""
        for obj_name in self.group_list:
            if obj_type == "MEEG":
                obj = MEEG(obj_name, self.ct)
            elif obj_type == "FSMRI":
                obj = FSMRI(obj_name, self.ct)
            else:
                logging.error(f"The object-type {obj_type} is not valid!")
                continue
            if data_type is None:
                yield obj
            elif data_type in obj.io_dict:
                data = obj.io_dict[data_type]["load"]()
                yield data, obj
            else:
                logging.error(f"{data_type} is not valid for {obj_type}")

    @load_decorator
    def load_ga_evokeds(self):
        ga_evokeds = dict()
        for trial in self.sel_trials:
            ga_evokeds[trial] = mne.read_evokeds(self.ga_evokeds_paths[trial])[0]

        return ga_evokeds

    @save_decorator
    def save_ga_evokeds(self, ga_evokeds):
        for trial in ga_evokeds:
            mne.evoked.write_evokeds(
                self.ga_evokeds_paths[trial], ga_evokeds[trial], overwrite=True
            )

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
            ga_stcs[trial].save(self.ga_stc_paths[trial], overwrite=True)

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
                ga_connect[trial][con_method] = np.load(
                    self.ga_con_paths[trial][con_method]
                )

        return ga_connect

    @save_decorator
    def save_ga_con(self, ga_con):
        for trial in ga_con:
            for con_method in ga_con[trial]:
                np.save(self.ga_con_paths[trial][con_method], ga_con[trial][con_method])
