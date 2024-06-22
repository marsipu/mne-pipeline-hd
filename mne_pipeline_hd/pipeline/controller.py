# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import json
import logging
import os
import re
import shutil
import sys
import traceback
from datetime import datetime
from importlib import reload, resources, import_module
from os import listdir
from os.path import isdir, join
from pathlib import Path

import mne
import pandas as pd

from mne_pipeline_hd import functions, extra
from mne_pipeline_hd.gui.gui_utils import get_user_input_string
from mne_pipeline_hd.pipeline.legacy import transfer_file_params_to_single_subject
from mne_pipeline_hd.pipeline.pipeline_utils import (
    QS,
    logger,
    type_json_hook,
    TypedJSONEncoder,
)
from mne_pipeline_hd.pipeline.project import Project

home_dirs = ["custom_packages", "freesurfer", "projects"]
project_dirs = ["_pipeline_scripts", "data", "figures"]


class Controller:
    def __init__(self, home_path=None, selected_project=None, edu_program_name=None):
        # Check Home-Path
        self.pr = None
        # Try to load home_path from QSettings
        self.home_path = home_path or QS().value("home_path", defaultValue=None)
        self.settings = dict()
        if self.home_path is None:
            raise RuntimeError("No Home-Path found!")

        # Check if path exists
        elif not isdir(self.home_path):
            raise RuntimeError(f"{self.home_path} not found!")

        # Check, if path is writable
        elif not os.access(self.home_path, os.W_OK):
            raise RuntimeError(f"{self.home_path} not writable!")

        # Initialize log-file
        self.logging_path = join(self.home_path, "_pipeline.log")
        file_handlers = [h for h in logger().handlers if h.name == "file"]
        if len(file_handlers) > 0:
            logger().removeHandler(file_handlers[0])
        file_handler = logging.FileHandler(self.logging_path, "w")
        file_handler.set_name("file")
        logger().addHandler(file_handler)

        logger().info(f"Home-Path: {self.home_path}")
        QS().setValue("home_path", self.home_path)
        # Create subdirectories if not existing for a valid home_path
        for subdir in [d for d in home_dirs if not isdir(join(self.home_path, d))]:
            os.mkdir(join(self.home_path, subdir))

        # Get Project-Folders (recognized by distinct sub-folders)
        self.projects_path = join(self.home_path, "projects")
        self.projects = [
            p
            for p in listdir(self.projects_path)
            if all([isdir(join(self.projects_path, p, d)) for d in project_dirs])
        ]

        # Initialize Subjects-Dir
        self.subjects_dir = join(self.home_path, "freesurfer")
        mne.utils.set_config("SUBJECTS_DIR", self.subjects_dir, set_env=True)

        # Initialize folder for custom packages
        self.custom_pkg_path = join(self.home_path, "custom_packages")

        # Initialize educational programs
        self.edu_program_name = edu_program_name
        self.edu_program = None

        # Load default settings
        default_path = join(resources.files(extra), "default_settings.json")
        with open(default_path, "r") as file:
            self.default_settings = json.load(file)

        # Load settings (which are stored as .json-file in home_path)
        # settings=<everything, that's OS-independent>
        self.load_settings()

        self.all_modules = dict()
        self.all_pd_funcs = None

        # Pandas-DataFrame for contextual data of basic functions
        # (included with program)
        self.pd_funcs = pd.read_csv(
            resources.files(extra) / "functions.csv",
            sep=";",
            index_col=0,
            na_values=[""],
            keep_default_na=False,
        )

        # Pandas-DataFrame for contextual data of parameters
        # for basic functions (included with program)
        self.pd_params = pd.read_csv(
            resources.files(extra) / "parameters.csv",
            sep=";",
            index_col=0,
            na_values=[""],
            keep_default_na=False,
        )

        # Import the basic- and custom-function-modules
        self.import_custom_modules()

        # Check Project
        if selected_project is None:
            selected_project = self.settings["selected_project"]

        if selected_project is None:
            if len(self.projects) > 0:
                selected_project = self.projects[0]

        # Initialize Project
        if selected_project is not None:
            self.change_project(selected_project)

    def load_settings(self):
        try:
            with open(
                join(self.home_path, "mne_pipeline_hd-settings.json"), "r"
            ) as file:
                self.settings = json.load(file)
            # Account for settings, which were not saved
            # but exist in default_settings
            for setting in [
                s for s in self.default_settings["settings"] if s not in self.settings
            ]:
                self.settings[setting] = self.default_settings["settings"][setting]
        except FileNotFoundError:
            self.settings = self.default_settings["settings"]
        else:
            # Check integrity of Settings-Keys
            s_keys = set(self.settings.keys())
            default_keys = set(self.default_settings["settings"])
            # Remove additional (old) keys not appearing in default-settings
            for setting in s_keys - default_keys:
                self.settings.pop(setting)
            # Add new keys from default-settings
            # which are not present in settings
            for setting in default_keys - s_keys:
                self.settings[setting] = self.default_settings["settings"][setting]

        # Check integrity of QSettings-Keys
        QS().sync()
        qs_keys = set(QS().childKeys())
        qdefault_keys = set(self.default_settings["qsettings"])
        # Remove additional (old) keys not appearing in default-settings
        for qsetting in qs_keys - qdefault_keys:
            QS().remove(qsetting)
        # Add new keys from default-settings which are not present in QSettings
        for qsetting in qdefault_keys - qs_keys:
            QS().setValue(qsetting, self.default_settings["qsettings"][qsetting])

    def save_settings(self):
        try:
            with open(
                join(self.home_path, "mne_pipeline_hd-settings.json"), "w"
            ) as file:
                json.dump(self.settings, file, indent=4)
        except FileNotFoundError:
            logger().warning("Settings could not be saved!")

        # Sync QSettings with other instances
        QS().sync()

    def get_setting(self, setting):
        try:
            value = self.settings[setting]
        except KeyError:
            value = self.default_settings["settings"][setting]

        return value

    def change_project(self, new_project):
        self.pr = Project(self, new_project)
        self.settings["selected_project"] = new_project
        if new_project not in self.projects:
            self.projects.append(new_project)
        logger().info(f"Selected-Project: {self.pr.name}")
        # Legacy
        transfer_file_params_to_single_subject(self)

        return self.pr

    def remove_project(self, project):
        self.projects.remove(project)
        if self.pr.name == project:
            if len(self.projects) > 0:
                new_project = self.projects[0]
            else:
                new_project = get_user_input_string(
                    "Please enter the name of a new project!", "Add Project", force=True
                )
            self.change_project(new_project)

        # Remove Project-Folder
        try:
            shutil.rmtree(join(self.projects_path, project))
        except OSError as error:
            print(error)
            logger().warning(
                f"The folder of {project} can't be deleted "
                f"and has to be deleted manually!"
            )

    def rename_project(self):
        check_writable = os.access(self.pr.project_path, os.W_OK)
        if check_writable:
            new_project_name = get_user_input_string(
                f'Change the name of project "{self.pr.name}" to:',
                "Rename Project",
                force=False,
            )
            if new_project_name is not None:
                try:
                    old_name = self.pr.name
                    self.pr.rename(new_project_name)
                except PermissionError:
                    # ToDo: Warning-Function for GUI with dialog and non-GUI
                    logger().critical(
                        f"Can't rename {old_name} to {new_project_name}. "
                        f"Probably a file from inside the project is still opened. "
                        f"Please close all files and try again."
                    )
                else:
                    self.projects.remove(old_name)
                    self.projects.append(new_project_name)
        else:
            logger().warning(
                "The project-folder seems to be not writable at the moment, "
                "maybe some files inside are still in use?"
            )

    def copy_parameters_between_projects(
        self,
        from_name,
        from_p_preset,
        to_name,
        to_p_preset,
        parameter=None,
    ):
        from_project = Project(self, from_name)
        if to_name == self.pr.name:
            to_project = self.pr
        else:
            to_project = Project(self, to_name)
        if parameter is not None:
            from_param = from_project.parameters[from_p_preset][parameter]
            to_project.parameters[to_p_preset][parameter] = from_param
        else:
            from_param = from_project.parameters[from_p_preset]
            to_project.parameters[to_p_preset] = from_param
        to_project.save()

    def save(self, worker_signals=None):
        if self.pr is not None:
            # Save Project
            self.pr.save(worker_signals)
            self.settings["selected_project"] = self.pr.name

        self.save_settings()

    def load_edu(self):
        if self.edu_program_name is not None:
            edu_path = join(self.home_path, "edu_programs", self.edu_program_name)
            with open(edu_path, "r") as file:
                self.edu_program = json.load(file)

            self.all_pd_funcs = self.pd_funcs.copy()
            # Exclude functions which are not selected
            self.pd_funcs = self.pd_funcs.loc[
                self.pd_funcs.index.isin(self.edu_program["functions"])
            ]

            # Change the Project-Scripts-Path to a new folder
            # to store the Education-Project-Scripts separately
            self.pr.pscripts_path = join(
                self.pr.project_path, f'_pipeline_scripts{self.edu_program["name"]}'
            )
            if not isdir(self.pr.pscripts_path):
                os.mkdir(self.pr.pscripts_path)
            self.pr.init_pipeline_scripts()

            # Exclude MEEG
            self.pr._all_meeg = self.pr.all_meeg.copy()
            self.pr.all_meeg = [
                meeg for meeg in self.pr.all_meeg if meeg in self.edu_program["meeg"]
            ]

            # Exclude FSMRI
            self.pr._all_fsmri = self.pr.all_fsmri.copy()
            self.pr.all_fsmri = [
                meeg for meeg in self.pr.all_meeg if meeg in self.edu_program["meeg"]
            ]

    def import_custom_modules(self):
        """
        Load all modules in functions and custom_functions
        """

        # Load basic-modules
        # Add functions to sys.path
        sys.path.insert(0, str(Path(functions.__file__).parent))
        basic_functions_list = [x for x in dir(functions) if "__" not in x]
        self.all_modules["basic"] = list()
        for module_name in basic_functions_list:
            self.all_modules["basic"].append(module_name)

        # Load custom_modules
        pd_functions_pattern = r".*_functions\.csv"
        pd_parameters_pattern = r".*_parameters\.csv"
        custom_module_pattern = r"(.+)(\.py)$"
        for directory in [
            d for d in os.scandir(self.custom_pkg_path) if not d.name.startswith(".")
        ]:
            pkg_name = directory.name
            pkg_path = directory.path
            file_dict = {"functions": None, "parameters": None, "modules": list()}
            for file_name in [
                f for f in listdir(pkg_path) if not f.startswith((".", "_"))
            ]:
                functions_match = re.match(pd_functions_pattern, file_name)
                parameters_match = re.match(pd_parameters_pattern, file_name)
                custom_module_match = re.match(custom_module_pattern, file_name)
                if functions_match:
                    file_dict["functions"] = join(pkg_path, file_name)
                elif parameters_match:
                    file_dict["parameters"] = join(pkg_path, file_name)
                elif custom_module_match and custom_module_match.group(1) != "__init__":
                    file_dict["modules"].append(custom_module_match)

            # Check, that there is a whole set for a custom-module
            # (module-file, functions, parameters)
            if all([value is not None or value != [] for value in file_dict.values()]):
                self.all_modules[pkg_name] = list()
                functions_path = file_dict["functions"]
                parameters_path = file_dict["parameters"]
                correct_count = 0
                for module_match in file_dict["modules"]:
                    module_name = module_match.group(1)
                    # Add pkg-path to sys.path
                    sys.path.insert(0, pkg_path)
                    try:
                        import_module(module_name)
                    except Exception:
                        traceback.print_exc()
                    else:
                        correct_count += 1
                        # Add Module to dictionary
                        self.all_modules[pkg_name].append(module_name)

                # Make sure, that every module in modules
                # is imported without error
                # (otherwise don't append to pd_funcs and pd_params)
                if len(file_dict["modules"]) == correct_count:
                    try:
                        read_pd_funcs = pd.read_csv(
                            functions_path,
                            sep=";",
                            index_col=0,
                            na_values=[""],
                            keep_default_na=False,
                        )
                        read_pd_params = pd.read_csv(
                            parameters_path,
                            sep=";",
                            index_col=0,
                            na_values=[""],
                            keep_default_na=False,
                        )
                    except Exception:
                        traceback.print_exc()
                    else:
                        # Add pkg_name here (would be redundant
                        # in read_pd_funcs of each custom-package)
                        read_pd_funcs["pkg_name"] = pkg_name

                        # Check, that there are no duplicates
                        pd_funcs_to_append = read_pd_funcs.loc[
                            ~read_pd_funcs.index.isin(self.pd_funcs.index)
                        ]
                        self.pd_funcs = pd.concat([self.pd_funcs, pd_funcs_to_append])
                        pd_params_to_append = read_pd_params.loc[
                            ~read_pd_params.index.isin(self.pd_params.index)
                        ]
                        self.pd_params = pd.concat(
                            [self.pd_params, pd_params_to_append]
                        )

            else:
                missing_files = [key for key in file_dict if file_dict[key] is None]
                logger().warning(
                    f"Files for import of {pkg_name} " f"are missing: {missing_files}"
                )

    def reload_modules(self):
        for pkg_name in self.all_modules:
            for module_name in self.all_modules[pkg_name]:
                module = import_module(module_name)
                try:
                    reload(module)
                # Custom-Modules somehow can't be reloaded
                # because spec is not found
                except ModuleNotFoundError:
                    spec = None
                    if spec:
                        # All errors occuring here will
                        # be caught by the UncaughtHook
                        spec.loader.exec_module(module)
                        sys.modules[module_name] = module


class NewController:
    """New controller, that combines the former old controller and project class and loads a controller for each "project".
    The home-path structure should no longer be as rigid as before, just specifying the path to meeg- and fsmri-data.
    For each controller, there is a config-file stored, where paths to the meeg-data,
    the freesurfer-dir and the custom-packages are stored.
    """

    def __init__(self, config_file=None):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        if self.config_file is not None:
            return json.load(self.config_file, object_hook=type_json_hook)
        else:
            return dict()

    def save_config(self):
        if self.config_file is None:
            logging.error("No config-file set!")
        with open(self.config_file, "w") as file:
            json.dump(self.config, file, indent=2, cls=TypedJSONEncoder)

    @property
    def name(self):
        name_default = f"Project_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return self.config.get("name", name_default)

    # ToDo: Rename function (rename all files etc.)
    def rename(self, new_name):
        pass

    @property
    def meeg_root(self):
        if "meeg_root" not in self.config:
            raise ValueError("The path to the MEEG data is not set!")
        return self.config["meeg_root"]

    @meeg_root.setter
    def meeg_root(self, value):
        if not isdir(value):
            raise ValueError(f"Path {value} does not exist!")
        self.config["meeg_root"] = value

    @property
    def fsmri_root(self):
        if "fsmri_root" not in self.config:
            raise ValueError("The path to the FreeSurfer MRI data is not set!")
        return self.config["fsmri_root"]

    @fsmri_root.setter
    def fsmri_root(self, value):
        if not isdir(value):
            raise ValueError(f"Path {value} does not exist!")
        self.config["fsmri_root"] = value

    @property
    def plots_path(self):
        if "plots_path" not in self.config:
            raise ValueError("The path for plots is not set!")
        return self.config["plots_path"]

    @plots_path.setter
    def plots_path(self, value):
        if not isdir(value):
            raise ValueError(f"Path {value} does not exist!")
        self.config["plots_path"] = value

    @property
    def inputs(self):
        """This holds all data inputs from MEEG, FSMRI, etc."""
        if "inputs" not in self.config:
            self.config["inputs"] = {
                "MEEG": list(),
                "FSMRI": list(),
                "EmptyRoom": list(),
            }
        return self.config["inputs"]

    @property
    def selected_inputs(self):
        """This holds all selected inputs."""
        if "selected_inputs" not in self.config:
            self.config["selected_inputs"] = {
                "MEEG": list(),
                "FSMRI": list(),
                "EmptyRoom": list(),
            }
        return self.config["selected_inputs"]
