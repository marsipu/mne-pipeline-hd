# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import inspect
import json
import logging
import multiprocessing
import os
import sys
from ast import literal_eval
from copy import deepcopy
from datetime import datetime
from importlib import resources
from os.path import join, isfile
from pathlib import Path

import numpy as np
import psutil

import mne_pipeline_hd

datetime_format = "%d.%m.%Y %H:%M:%S"

ismac = sys.platform.startswith("darwin")
iswin = sys.platform.startswith("win32")
islin = not ismac and not iswin


def get_n_jobs(n_jobs):
    """Get the number of jobs to use for parallel processing"""
    if n_jobs == -1 or n_jobs in ["auto", "max"]:
        n_cores = multiprocessing.cpu_count()
    else:
        n_cores = int(n_jobs)

    return n_cores


def encode_tuples(input_dict):
    """Encode tuples in a dictionary, because JSON does not recognize them
    (CAVE: input_dict is changed in place)"""
    for key, value in input_dict.items():
        if isinstance(value, dict):
            encode_tuples(value)
        else:
            if isinstance(value, tuple):
                input_dict[key] = {"tuple_type": value}


class TypedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return {"numpy_array": obj.tolist()}
        elif isinstance(obj, datetime):
            return {"datetime": obj.strftime(datetime_format)}
        elif isinstance(obj, set):
            return {"set_type": list(obj)}
        else:
            return json.JSONEncoder.default(self, obj)


def type_json_hook(obj):
    if "numpy_int" in obj.keys():
        return obj["numpy_int"]
    elif "numpy_float" in obj.keys():
        return obj["numpy_float"]
    elif "numpy_array" in obj.keys():
        return np.asarray(obj["numpy_array"])
    elif "datetime" in obj.keys():
        return datetime.strptime(obj["datetime"], datetime_format)
    elif "tuple_type" in obj.keys():
        return tuple(obj["tuple_type"])
    elif "set_type" in obj.keys():
        return set(obj["set_type"])
    else:
        return obj


def compare_filep(obj, path, target_parameters=None, verbose=True):
    """Compare the parameters of the previous run to the current
    parameters for the given path

    Parameters
    ----------
    obj : MEEG | FSMRI | Group
        A Data-Object to get the information needed
    path : str
        The path for the file to compare the parameters
    target_parameters : list | None
        The parameters to compare (set None for all)
    verbose : bool
        Set to True to print the outcome for each parameter to the console

    Returns
    -------
    result_dict : dict
        A dictionary with every parameter from target_parameters
        with a value as result:
            None, if nothing changed |
            tuple (previous_value, current_value, critical) |
            'missing', if path hasn't been saved yet
    """

    result_dict = dict()
    file_name = Path(path).name
    # Try to get the parameters relevant for the last function,
    # which altered the data at path
    try:
        # The last entry in FUNCTION should be the most recent
        function = obj.file_parameters[file_name]["FUNCTION"]
        critical_params_str = obj.ct.pd_funcs.loc[function, "func_args"]
        # Make sure there are no spaces left
        critical_params_str = critical_params_str.replace(" ", "")
        if "," in critical_params_str:
            critical_params = critical_params_str.split(",")
        else:
            critical_params = [critical_params_str]
    except KeyError:
        critical_params = list()
        function = None

    if not target_parameters:
        target_parameters = obj.pa.keys()
    for param in target_parameters:
        try:
            previous_value = obj.file_parameters[file_name][param]
            current_value = obj.pa[param]

            if str(previous_value) == str(current_value):
                result_dict[param] = "equal"
                if verbose:
                    print(f"{param} equal for {file_name}")
            else:
                if param in critical_params:
                    result_dict[param] = (previous_value, current_value, True)
                    if verbose:
                        print(
                            f"{param} changed from {previous_value} to "
                            f"{current_value} for {file_name} "
                            f"and is probably crucial for {function}"
                        )
                else:
                    result_dict[param] = (previous_value, current_value, False)
                    if verbose:
                        print(
                            f"{param} changed from {previous_value} to "
                            f"{current_value} for {file_name}"
                        )
        except KeyError:
            result_dict[param] = "missing"
            if verbose:
                print(f"{param} is missing in records for {file_name}")

    if obj.ct.settings["overwrite"]:
        result_dict[param] = "overwrite"
        if verbose:
            print(
                f"{file_name} will be overwritten anyway"
                f" because Overwrite=True (Settings)"
            )

    return result_dict


def check_kwargs(kwargs, function):
    kwargs = kwargs.copy()

    existing_kwargs = inspect.signature(function).parameters

    for kwarg in [k for k in kwargs if k not in existing_kwargs]:
        kwargs.pop(kwarg)

    return kwargs


def count_dict_keys(d, max_level=None):
    """Count the number of keys of a nested dictionary"""
    keys = 0
    for value in d.values():
        if isinstance(value, dict):
            if max_level is None:
                keys += count_dict_keys(value)
            elif max_level > 1:
                keys += count_dict_keys(value, max_level - 1)
            else:
                keys += 1
        else:
            keys += 1

    return keys


def shutdown():
    if iswin:
        os.system("shutdown /s")
    if islin:
        os.system("sudo shutdown now")
    if ismac:
        os.system("sudo shutdown -h now")


def restart_program():
    """Restarts the current program, with file objects and descriptors
    cleanup."""
    logging.info("Restarting")
    try:
        p = psutil.Process(os.getpid())
        for handler in p.open_files() + p.connections():
            os.close(handler.fd)
    except Exception as e:
        logging.error(e)

    python = sys.executable
    os.execl(python, python, *sys.argv)


def _get_func_param_kwargs(func, params):
    kwargs = {
        kwarg: params[kwarg] if kwarg in params else None
        for kwarg in inspect.signature(func).parameters
    }

    return kwargs


class BaseSettings:
    def __init__(self):
        # Load default settings
        default_settings_path = join(
            resources.files(mne_pipeline_hd.extra), "default_settings.json"
        )
        with open(default_settings_path, "r") as file:
            self.default_qsettings = json.load(file)["qsettings"]

    def get_default(self, name):
        if name in self.default_qsettings:
            return self.default_qsettings[name]
        else:
            raise RuntimeError(
                f"{name} not in default_settings.json! "
                f"Please add it or fix the bug."
            )


# Import QSettings or provide Dummy-Class to be independent from PyQt/PySide
try:
    from qtpy.QtCore import QSettings

    class QS(BaseSettings):
        def __init__(self):
            super().__init__()

        def value(self, setting, defaultValue=None):
            loaded_value = QSettings().value(setting, defaultValue=defaultValue)
            # Type-Conversion for UNIX-Systems
            # (ini-File does not preserve type, converts to strings)
            if not isinstance(loaded_value, type(self.get_default(setting))):
                try:
                    loaded_value = literal_eval(loaded_value)
                except (SyntaxError, ValueError):
                    return self.get_default(setting)
            if loaded_value is None:
                if defaultValue is None:
                    return self.get_default(setting)
                else:
                    return defaultValue
            else:
                return loaded_value

        def setValue(self, setting, value):
            QSettings().setValue(setting, value)

        def sync(self):
            QSettings().sync()

        def childKeys(self):
            return QSettings().childKeys()

except ImportError:

    class QS(BaseSettings):
        def __init__(self):
            super().__init__()

            self.settings_path = join(Path.home(), ".mnephd_settings.json")

        def _load_settings(self):
            if isfile(self.settings_path):
                with open(self.settings_path, "r") as file:
                    self.settings = json.load(file)
            else:
                self.settings = deepcopy(self.default_qsettings)

        def _write_settings(self):
            with open(self.settings_path, "w") as file:
                json.dump(self.settings, file)

        def value(self, setting, defaultValue=None):
            self._load_settings()
            if setting in self.settings:
                return self.settings[setting]

            if defaultValue is None:
                return self.get_default(setting)
            else:
                return defaultValue

        def setValue(self, setting, value):
            self._load_settings()
            self.settings[setting] = value
            self._write_settings()

        def sync(self):
            self._write_settings()
            self._load_settings()

        def childKeys(self):
            return self.settings.keys()


def _set_test_run():
    os.environ["TEST_RUN"] = "True"


def _test_run():
    if "TEST_RUN" in os.environ:
        return True


def _run_from_script():
    return "__main__.py" in sys.argv[0]
