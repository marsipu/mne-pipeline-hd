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
import inspect
import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np

from . import islin, ismac, iswin

datetime_format = '%d.%m.%Y %H:%M:%S'


def encode_tuples(input_dict):
    """Encode tuples in a dictionary, because JSON does not recognize them (CAVE: input_dict is changed in place)"""
    for key, value in input_dict.items():
        if isinstance(value, dict):
            encode_tuples(value)
        else:
            if isinstance(value, tuple):
                input_dict[key] = {'tuple_type': value}


class TypedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return {'numpy_array': obj.tolist()}
        elif isinstance(obj, datetime):
            return {'datetime': obj.strftime(datetime_format)}
        elif isinstance(obj, set):
            return {'set_type': list(obj)}
        else:
            return json.JSONEncoder.default(self, obj)


def type_json_hook(obj):
    if 'numpy_int' in obj.keys():
        return obj['numpy_int']
    elif 'numpy_float' in obj.keys():
        return obj['numpy_float']
    elif 'numpy_array' in obj.keys():
        return np.asarray(obj['numpy_array'])
    elif 'datetime' in obj.keys():
        return datetime.strptime(obj['datetime'], datetime_format)
    elif 'tuple_type' in obj.keys():
        return tuple(obj['tuple_type'])
    elif 'set_type' in obj.keys():
        return set(obj['set_type'])
    else:
        return obj


def compare_filep(obj, path, target_parameters=None, verbose=True):
    """Compare the parameters of the previous run to the current parameters for the given path

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
        A dictionary with every parameter from target_parameters with a value as result:
            None, if nothing changed |
            tuple (previous_value, current_value, critical) |
            'missing', if path hasn't been saved yet
    """

    result_dict = dict()
    file_name = Path(path).name
    # Try to get the parameters relevant for the last function, which altered the data at path
    try:
        # The last entry in FUNCTION should be the most recent
        function = obj.file_parameters[file_name]['FUNCTION']
        critical_params_str = obj.mw.pd_funcs.loc[function, 'func_args']
        # Make sure there are no spaces left
        critical_params_str = critical_params_str.replace(' ', '')
        critical_params = critical_params_str.split(',')
    except KeyError:
        critical_params = list()
        function = None

    if not target_parameters:
        target_parameters = obj.p.keys()
    for param in target_parameters:
        try:
            previous_value = obj.file_parameters[file_name][param]
            current_value = obj.p[param]

            equality = str(previous_value) == str(current_value)

            if equality:
                result_dict[param] = 'equal'
                if verbose:
                    print(f'{param} equal for {file_name}')
            else:
                if param in critical_params:
                    result_dict[param] = (previous_value, current_value, True)
                    if verbose:
                        print(f'{param} changed from {previous_value} to {current_value} for {file_name} '
                              f'and is probably crucial for {function}')
                else:
                    result_dict[param] = (previous_value, current_value, False)
                    if verbose:
                        print(f'{param} changed from {previous_value} to {current_value} for {file_name}')
        except KeyError:
            result_dict[param] = 'missing'
            if verbose:
                print(f'{param} is missing in records for {file_name}')

    if obj.mw.settings['overwrite']:
        result_dict[param] = 'overwrite'
        if verbose:
            print(f'{file_name} will be overwritten anyway because Overwrite=True (Settings)')

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
    for key, value in d.items():
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
        os.system('shutdown /s')
    if islin:
        os.system('sudo shutdown now')
    if ismac:
        os.system('sudo shutdown -h now')
