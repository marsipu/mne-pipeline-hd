# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import json
import os
import shutil
from ast import literal_eval
from copy import deepcopy
from os import listdir, makedirs
from os.path import exists, getsize, isfile, join, isdir
from pathlib import Path

import mne
import numpy as np

from mne_pipeline_hd.pipeline.legacy import renamed_parameters
from mne_pipeline_hd.pipeline.loading import MEEG, FSMRI, Group
from mne_pipeline_hd.pipeline.pipeline_utils import (
    TypedJSONEncoder,
    count_dict_keys,
    encode_tuples,
    type_json_hook,
    logger,
)


class Project:
    """A class with attributes for all the paths, file-lists/dicts and parameters of the
    selected project."""

    def __init__(self, controller, name):
        self.ct = controller
        self.name = name

        self.init_main_paths()
        self.init_attributes()
        self.init_pipeline_scripts()
        self.load()
        self.save()
        # ToDo: MacOs weird folders added (.DSStore)
        # self.check_data()

    def init_main_paths(self):
        # Main folder of project
        self.project_path = join(self.ct.projects_path, self.name)
        # Folder to store the data
        self.data_path = join(self.project_path, "data")
        # Folder to store the figures (with an additional subfolder
        # for each parameter-preset)
        self.figures_path = join(self.project_path, "figures")
        # A dedicated folder to store grand-average data
        self.save_dir_averages = join(self.data_path, "grand_averages")
        # A folder to store all pipeline-scripts as .json-files
        self.pscripts_path = join(self.project_path, "_pipeline_scripts")

        self.main_paths = [
            self.ct.subjects_dir,
            self.data_path,
            self.save_dir_averages,
            self.pscripts_path,
            self.ct.custom_pkg_path,
            self.figures_path,
        ]

        # Create or check existence of main_paths
        for path in self.main_paths:
            if not exists(path):
                makedirs(path)
                logger().debug(f"{path} created")

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
        # Stores the names of all Freesurfer-Segmentation-Folders
        # in Subjects-Dir
        self.all_fsmri = list()
        # Stores selected Freesurfer-Segmentations
        self.sel_fsmri = list()
        # Maps each MEG/EEG-File to a Freesurfer-Segmentation or None
        self.meeg_to_fsmri = dict()
        # Stores the ICA-Components to be excluded
        self.meeg_ica_exclude = dict()
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
        self.p_preset = "Default"

        # Attributes, which have their own special function for loading
        self.special_loads = ["parameters", "p_preset"]

    def init_pipeline_scripts(self):
        # ToDo: Transition scripts to toml (only keep parameters as json for types)
        # Initiate Project-Lists and Dicts
        self.all_meeg_path = join(self.pscripts_path, f"all_meeg_{self.name}.json")
        self.sel_meeg_path = join(self.pscripts_path, f"selected_meeg_{self.name}.json")
        self.meeg_bad_channels_path = join(
            self.pscripts_path, f"meeg_bad_channels_{self.name}.json"
        )
        self.meeg_event_id_path = join(
            self.pscripts_path, f"meeg_event_id_{self.name}.json"
        )
        self.sel_event_id_path = join(
            self.pscripts_path, f"selected_event_ids_{self.name}.json"
        )
        self.all_erm_path = join(self.pscripts_path, f"all_erm_{self.name}.json")
        self.meeg_to_erm_path = join(
            self.pscripts_path, f"meeg_to_erm_{self.name}.json"
        )
        self.all_fsmri_path = join(self.pscripts_path, f"all_fsmri_{self.name}.json")
        self.sel_fsmri_path = join(
            self.pscripts_path, f"selected_fsmri_{self.name}.json"
        )
        self.meeg_to_fsmri_path = join(
            self.pscripts_path, f"meeg_to_fsmri_{self.name}.json"
        )
        self.ica_exclude_path = join(
            self.pscripts_path, f"ica_exclude_{self.name}.json"
        )
        self.all_groups_path = join(self.pscripts_path, f"all_groups_{self.name}.json")
        self.sel_groups_path = join(
            self.pscripts_path, f"selected_groups_{self.name}.json"
        )
        self.plot_files_path = join(self.pscripts_path, f"plot_files_{self.name}.json")
        self.sel_functions_path = join(
            self.pscripts_path, f"selected_functions_{self.name}.json"
        )
        self.add_kwargs_path = join(
            self.pscripts_path, f"additional_kwargs_{self.name}.json"
        )
        self.parameters_path = join(self.pscripts_path, f"parameters_{self.name}.json")
        self.sel_p_preset_path = join(
            self.pscripts_path, f"sel_p_preset_{self.name}.json"
        )

        # Map the paths to their attribute in the Project-Class
        self.path_to_attribute = {
            self.all_meeg_path: "all_meeg",
            self.sel_meeg_path: "sel_meeg",
            self.meeg_bad_channels_path: "meeg_bad_channels",
            self.meeg_event_id_path: "meeg_event_id",
            self.sel_event_id_path: "sel_event_id",
            self.all_erm_path: "all_erm",
            self.meeg_to_erm_path: "meeg_to_erm",
            self.all_fsmri_path: "all_fsmri",
            self.sel_fsmri_path: "sel_fsmri",
            self.meeg_to_fsmri_path: "meeg_to_fsmri",
            self.ica_exclude_path: "meeg_ica_exclude",
            self.all_groups_path: "all_groups",
            self.sel_groups_path: "sel_groups",
            self.plot_files_path: "plot_files",
            self.sel_functions_path: "sel_functions",
            self.add_kwargs_path: "add_kwargs",
            self.parameters_path: "parameters",
            self.sel_p_preset_path: "p_preset",
        }

    def rename(self, new_name):
        # Rename folder
        old_name = self.name
        os.rename(self.project_path, join(self.ct.projects_path, new_name))
        self.name = new_name
        self.init_main_paths()
        # Rename project-files
        old_paths = [Path(p).name for p in self.path_to_attribute]
        self.init_pipeline_scripts()
        new_paths = [Path(p).name for p in self.path_to_attribute]
        for old_path, new_path in zip(old_paths, new_paths):
            os.rename(
                join(self.pscripts_path, old_path), join(self.pscripts_path, new_path)
            )
            logger().info(f"Renamed project-script {old_path} to {new_path}")
        logger().info(f'Finished renaming project "{old_name}" to "{new_name}"')

    def load_lists(self):
        # Old Paths to allow transition (22.11.2020)
        self.old_all_meeg_path = join(self.pscripts_path, "file_list.json")
        self.old_sel_meeg_path = join(self.pscripts_path, "selected_files.json")
        self.old_meeg_bad_channels_path = join(
            self.pscripts_path, "bad_channels_dict.json"
        )
        self.old_meeg_event_id_path = join(self.pscripts_path, "event_id_dict.json")
        self.old_sel_event_id_path = join(
            self.pscripts_path, "selected_evid_labels.json"
        )
        self.old_all_erm_path = join(self.pscripts_path, "erm_list.json")
        self.old_meeg_to_erm_path = join(self.pscripts_path, "erm_dict.json")
        self.old_all_fsmri_path = join(self.pscripts_path, "mri_sub_list.json")
        self.old_sel_fsmri_path = join(self.pscripts_path, "selected_mri_files.json")
        self.old_meeg_to_fsmri_path = join(self.pscripts_path, "sub_dict.json")
        self.old_all_groups_path = join(self.pscripts_path, "grand_avg_dict.json")
        self.old_sel_groups_path = join(
            self.pscripts_path, "selected_grand_average_groups.json"
        )
        self.old_sel_funcs_path = join(self.pscripts_path, "selected_funcs.json")

        # Old Paths to allow transition (22.11.2020)
        self.old_paths = {
            self.all_meeg_path: self.old_all_meeg_path,
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
            self.sel_functions_path: self.old_sel_funcs_path,
        }

        for path in [
            p
            for p in self.path_to_attribute
            if self.path_to_attribute[p] not in self.special_loads
        ]:
            attribute_name = self.path_to_attribute[path]
            try:
                with open(path, "r") as file:
                    loaded_attribute = json.load(file, object_hook=type_json_hook)
                    # Make sure, that loaded object has same type
                    # as default from __init__
                    if isinstance(
                        loaded_attribute, type(getattr(self, attribute_name))
                    ):
                        setattr(self, attribute_name, loaded_attribute)
            # Either empty file or no file, leaving default from __init__
            except (json.JSONDecodeError, FileNotFoundError):
                # Old Paths to allow transition (22.11.2020)
                try:
                    with open(self.old_paths[path], "r") as file:
                        setattr(
                            self,
                            attribute_name,
                            json.load(file, object_hook=type_json_hook),
                        )
                except (json.JSONDecodeError, FileNotFoundError, KeyError):
                    pass

    def load_parameters(self):
        try:
            with open(
                join(self.pscripts_path, f"parameters_{self.name}.json"), "r"
            ) as read_file:
                loaded_parameters = json.load(read_file, object_hook=type_json_hook)

                for p_preset in loaded_parameters:
                    # Make sure, that only parameters,
                    # which exist in pd_params are loaded
                    for param in [
                        p
                        for p in loaded_parameters[p_preset]
                        if p not in self.ct.pd_params.index
                    ]:
                        if "_exp" not in param:
                            loaded_parameters[p_preset].pop(param)

                    # Add parameters, which exist in extra/parameters.csv,
                    # but not in loaded-parameters
                    # (e.g. added with custom-module)
                    for param in [
                        p
                        for p in self.ct.pd_params.index
                        if p not in loaded_parameters[p_preset]
                    ]:
                        try:
                            eval_param = literal_eval(
                                self.ct.pd_params.loc[param, "default"]
                            )
                        except (ValueError, SyntaxError, NameError):
                            # Allow parameters to be defined by functions
                            # e.g. by numpy, etc.
                            is_func_gui = (
                                self.ct.pd_params.loc[param, "gui_type"] == "FuncGui"
                            )
                            if is_func_gui:
                                default_string = self.ct.pd_params.loc[param, "default"]
                                eval_param = eval(default_string, {"np": np})
                                exp_name = param + "_exp"
                                loaded_parameters[p_preset].update(
                                    {exp_name: default_string}
                                )
                            else:
                                eval_param = self.ct.pd_params.loc[param, "default"]
                        loaded_parameters[p_preset].update({param: eval_param})
                    # Change renamed legacy parameters
                    for param, value in loaded_parameters[p_preset].items():
                        if param in renamed_parameters:
                            if value in renamed_parameters[param]:
                                loaded_parameters[p_preset][param] = renamed_parameters[
                                    param
                                ][value]

                self.parameters = loaded_parameters
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.load_default_parameters()

    def load_default_param(self, param_name):
        string_param = self.ct.pd_params.loc[param_name, "default"]
        try:
            self.parameters[self.p_preset][param_name] = literal_eval(string_param)
        except (ValueError, SyntaxError):
            # Allow parameters to be defined by functions e.g. by numpy, etc.
            if self.ct.pd_params.loc[param_name, "gui_type"] == "FuncGui":
                self.parameters[self.p_preset][param_name] = eval(
                    string_param, {"np": np}
                )
                exp_name = param_name + "_exp"
                self.parameters[self.p_preset][exp_name] = string_param
            else:
                self.parameters[self.p_preset][param_name] = string_param

    def load_default_parameters(self):
        # Empty the dict for current Parameter-Preset
        self.parameters[self.p_preset] = dict()
        for param_name in self.ct.pd_params.index:
            self.load_default_param(param_name)

    def load_last_p_preset(self):
        try:
            with open(self.sel_p_preset_path, "r") as read_file:
                self.p_preset = json.load(read_file)
                # If parameter-preset not in Parameters,
                # load first Parameter-Key(=Parameter-Preset)
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
                worker_signals.pgbar_text.emit(f"Saving {self.path_to_attribute[path]}")

            attribute = getattr(self, self.path_to_attribute[path], None)

            # Make sure the tuples are encoded correctly
            if isinstance(attribute, dict):
                attribute = deepcopy(attribute)
                encode_tuples(attribute)

            try:
                with open(path, "w") as file:
                    json.dump(attribute, file, cls=TypedJSONEncoder, indent=4)

            except json.JSONDecodeError as err:
                logger().warning(f"There is a problem with path:\n" f"{err}")

    def add_meeg(self, name, file_path=None, is_erm=False):
        if is_erm:
            # Organize Empty-Room-Files
            if name not in self.all_erm:
                self.all_erm.append(name)
        else:
            # Organize other files
            if name not in self.all_meeg:
                self.all_meeg.append(name)

        # Copy sub_files to destination (with MEEG-Class
        # to also include raw into file_parameters)
        meeg = MEEG(name, self.ct)

        if file_path is not None:
            # Get bad-channels from raw-file
            raw = mne.io.read_raw(file_path, preload=True)
            loaded_bads = raw.info["bads"]
            if len(loaded_bads) > 0:
                self.meeg_bad_channels[name] = raw.info["bads"]

            meeg.save_raw(raw)

        return meeg

    def remove_meeg(self, remove_files):
        for meeg in self.sel_meeg:
            try:
                # Remove MEEG from Lists/Dictionaries
                self.all_meeg.remove(meeg)
            except ValueError:
                logger().warning(f"{meeg} already removed!")
            self.meeg_to_erm.pop(meeg, None)
            self.meeg_to_fsmri.pop(meeg, None)
            self.meeg_bad_channels.pop(meeg, None)
            self.meeg_event_id.pop(meeg, None)
            if remove_files:
                try:
                    remove_path = join(self.data_path, meeg)
                    shutil.rmtree(remove_path)
                    logger().info(f"Succesful removed {remove_path}")
                except FileNotFoundError:
                    logger().critical(join(self.data_path, meeg) + " not found!")
        self.sel_meeg.clear()

    def add_fsmri(self, name, src_dir=None):
        self.all_fsmri.append(name)
        # Initialize FSMRI
        fsmri = FSMRI(name, self.ct)
        if src_dir is not None:
            dst_dir = join(self.ct.subjects_dir, name)
            if not isdir(dst_dir):
                logger().debug(f"Copying Folder from {src_dir}...")
                try:
                    shutil.copytree(src_dir, dst_dir)
                # surfaces with .H and .K at the end can't be copied
                except shutil.Error:
                    pass
                logger().debug(f"Finished Copying to {dst_dir}")
            else:
                logger().info(f"{dst_dir} already exists")

        return fsmri

    def remove_fsmri(self, remove_files):
        for fsmri in self.sel_fsmri:
            try:
                self.all_fsmri.remove(fsmri)
            except ValueError:
                logger().warning(f"{fsmri} already deleted!")
            if remove_files:
                try:
                    shutil.rmtree(join(self.ct.subjects_dir, fsmri))
                except FileNotFoundError:
                    logger().info(join(self.ct.subjects_dir, fsmri) + " not found!")
        self.sel_fsmri.clear()

    def add_group(self):
        pass

    def remove_group(self):
        pass

    def check_data(self):
        missing_objects = [
            x
            for x in listdir(self.data_path)
            if x != "grand_averages"
            and x not in self.all_meeg
            and x not in self.all_erm
        ]

        for obj in missing_objects:
            self.all_meeg.append(obj)

        # Get Freesurfer-folders (with 'surf'-folder)
        # from subjects_dir (excluding .files for Mac)
        read_dir = sorted(
            [f for f in os.listdir(self.ct.subjects_dir) if not f.startswith(".")],
            key=str.lower,
        )
        self.all_fsmri = [
            fsmri
            for fsmri in read_dir
            if exists(join(self.ct.subjects_dir, fsmri, "surf"))
        ]

        self.save()

    def clean_file_parameters(self, worker_signals=None):
        if worker_signals is not None:
            worker_signals.pgbar_max.emit(
                len(self.all_meeg) + len(self.all_fsmri) + len(self.all_groups.keys())
            )
        count = 0

        for meeg in self.all_meeg:
            meeg = MEEG(meeg, self.ct)
            worker_signals.pgbar_text.emit(f"Cleaning File-Parameters for {meeg}")
            meeg.clean_file_parameters()
            count += 1
            if worker_signals is not None:
                worker_signals.pgbar_n.emit(count)
                if worker_signals.was_canceled:
                    logger().info("Cleaning was canceled by the user!")
                    return

        for fsmri in self.all_fsmri:
            fsmri = FSMRI(fsmri, self.ct)
            worker_signals.pgbar_text.emit(f"Cleaning File-Parameters for {fsmri}")
            fsmri.clean_file_parameters()
            count += 1
            if worker_signals is not None:
                worker_signals.pgbar_n.emit(count)
                if worker_signals.was_canceled:
                    logger().info("Cleaning was canceled by the user!")
                    return

        for group in self.all_groups:
            group = Group(group, self.ct)
            worker_signals.pgbar_text.emit(f"Cleaning File-Parameters for {group}")
            group.clean_file_parameters()
            count += 1
            if worker_signals is not None:
                worker_signals.pgbar_n.emit(count)
                if worker_signals.was_canceled:
                    logger().info("Cleaning was canceled by the user!")
                    return

    def clean_plot_files(self, worker_signals=None):
        all_image_paths = list()
        # Remove object-keys which no longer exist
        remove_obj = list()
        n_remove_ppreset = 0
        n_remove_funcs = 0

        if worker_signals is not None:
            worker_signals.pgbar_max.emit(count_dict_keys(self.plot_files, max_level=3))
        key_count = 0

        for obj_key in self.plot_files:
            key_count += 1
            if worker_signals is not None:
                worker_signals.pgbar_n.emit(key_count)

            if obj_key not in self.all_meeg + self.all_erm + self.all_fsmri + list(
                self.all_groups.keys()
            ):
                remove_obj.append(obj_key)
            else:
                # Remove Parameter-Presets which no longer exist
                remove_p_preset = list()
                for p_preset in self.plot_files[obj_key]:
                    key_count += 1
                    if worker_signals is not None:
                        worker_signals.pgbar_n.emit(key_count)

                    if p_preset not in self.parameters.keys():
                        key_count += len(self.plot_files[obj_key][p_preset])
                        if worker_signals is not None:
                            worker_signals.pgbar_n.emit(key_count)

                        remove_p_preset.append(p_preset)
                    else:
                        # Remove funcs which no longer exist
                        # or got no paths left
                        remove_funcs = list()
                        for func in self.plot_files[obj_key][p_preset]:
                            key_count += 1
                            if worker_signals is not None:
                                worker_signals.pgbar_n.emit(key_count)

                            # Cancel if canceled
                            if (
                                worker_signals is not None
                                and worker_signals.was_canceled
                            ):
                                logger().info("Cleaning was canceled by user")
                                return

                            if func not in self.ct.pd_funcs.index:
                                remove_funcs.append(func)
                            else:
                                # Remove image-paths which no longer exist
                                for rel_image_path in self.plot_files[obj_key][
                                    p_preset
                                ][func]:
                                    image_path = Path(
                                        join(self.figures_path, rel_image_path)
                                    )
                                    if (
                                        not isfile(image_path)
                                        or self.figures_path in rel_image_path
                                    ):
                                        self.plot_files[obj_key][p_preset][func].remove(
                                            rel_image_path
                                        )
                                    else:
                                        all_image_paths.append(str(image_path))
                                if len(self.plot_files[obj_key][p_preset][func]) == 0:
                                    # Keys can't be dropped from dictionary
                                    # during iteration
                                    remove_funcs.append(func)

                        for remove_func_key in remove_funcs:
                            self.plot_files[obj_key][p_preset].pop(remove_func_key)
                        n_remove_funcs += len(remove_funcs)

                for remove_preset_key in remove_p_preset:
                    self.plot_files[obj_key].pop(remove_preset_key)
                n_remove_ppreset += len(remove_p_preset)

            logger().info(
                f"Removed {n_remove_ppreset} Parameter-Presets and "
                f"{n_remove_funcs} from {obj_key}"
            )

        for remove_key in remove_obj:
            self.plot_files.pop(remove_key)
        logger().info(f"Removed {len(remove_obj)} Objects from Plot-Files")

        # Remove image-files, which aren't listed in plot_files.
        free_space = 0
        logger().info("Removing unregistered images...")
        n_removed_images = 0
        for root, _, files in os.walk(self.figures_path):
            files = [join(root, f) for f in files]
            for file_path in [
                fp for fp in files if str(Path(fp)) not in all_image_paths
            ]:
                free_space += getsize(file_path)
                n_removed_images += 1
                os.remove(file_path)
        logger().info(f"Removed {n_removed_images} images")

        # Remove empty folders (loop until all empty folders are removed)
        logger().info("Removing empty folders...")
        n_removed_folders = 0
        folder_loop = True
        # Redo the file-walk because folders can get empty
        # by deleting folders inside
        while folder_loop:
            folder_loop = False
            for root, folders, _ in os.walk(self.figures_path):
                folders = [join(root, fd) for fd in folders]
                for folder in [fdp for fdp in folders if len(listdir(fdp)) == 0]:
                    os.rmdir(folder)
                    n_removed_folders += 1
                    folder_loop = True
        logger().info(f"Removed {n_removed_folders} folders")

        logger().info(f"{round(free_space / (1024 ** 2), 2)} MB of space was freed!")
