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
import numpy as np
from ast import literal_eval
from os import makedirs
from os.path import exists, isfile, join

import autoreject as ar

from . import islin, ismac, iswin


class ParametersJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return {'numpy_int': int(obj)}

        elif isinstance(obj, np.floating):
            return {'numpy_float': float(obj)}

        elif isinstance(obj, np.ndarray):
            return {'numpy_array': obj.tolist()}

        return json.JSONEncoder.default(self, obj)


def parameters_json_hook(obj):
    if 'numpy_array' in obj.keys():
        return np.asarray(obj['numpy_array'])
    elif 'tuple_type' in obj.keys():
        return tuple(obj['tuple_type'])
    else:
        return obj


def autoreject_handler(name, epochs, highpass, lowpass, pscripts_path, overwrite_ar=False,
                       only_read=False):
    reject_value_path = join(pscripts_path, f'reject_values_{highpass}-{lowpass}_Hz.py')

    if not isfile(reject_value_path):
        if only_read:
            raise Exception('New Autoreject-Threshold only from epoch_raw')
        else:
            reject = ar.get_rejection_threshold(epochs, ch_types=['grad'], random_state=8)
            with open(reject_value_path, 'w') as rv:
                rv.write(f'{name}:{reject}\n')
            print(reject_value_path + ' created')

    else:
        read_reject = dict()
        with open(reject_value_path, 'r') as rv:

            for item in rv:
                if ':' in item:
                    key, value = item.split(':', 1)
                    value = literal_eval(value[:-1])
                    read_reject[key] = value

        if name in read_reject:
            if overwrite_ar:
                if only_read:
                    raise Exception('New Autoreject-Threshold only from epoch_raw')
                print('Rejection with Autoreject')
                reject = ar.get_rejection_threshold(epochs, ch_types=['grad'], random_state=8)
                prae_reject = read_reject[name]
                read_reject[name] = reject
                if prae_reject == reject:
                    print(f'Same reject_values {reject}')
                else:
                    print(f'Replaced AR-Threshold {prae_reject} with {reject}')
                with open(reject_value_path, 'w') as rv:
                    for key, value in read_reject.items():
                        rv.write(f'{key}:{value}\n')
            else:
                reject = read_reject[name]
                print('Reading Rejection-Threshold from file')

        else:
            if only_read:
                raise Exception('New Autoreject-Threshold only from epoch_raw')
            print('Rejection with Autoreject')
            reject = ar.get_rejection_threshold(epochs, ch_types=['grad'], random_state=8)
            read_reject.update({name: reject})
            print(f'Added AR-Threshold {reject} for {name}')
            with open(reject_value_path, 'w') as rv:
                for key, value in read_reject.items():
                    rv.write(f'{key}:{value}\n')

    return reject


def dict_filehandler(name, file_name, pscripts_path, values=None,
                     onlyread=False, overwrite=True, silent=False):
    file_path = join(pscripts_path, file_name + '.py')
    file_dict = dict()

    if not isfile(file_path):
        if not exists(pscripts_path):
            makedirs(pscripts_path)
            if not silent:
                print(pscripts_path + ' created')
        with open(file_path, 'w') as file:
            if type(values) == str:
                file.write(f'{name}:"{values}"\n')
            else:
                file.write(f'{name}:{values}\n')
            if not silent:
                print(file_path + ' created')
    else:
        with open(file_path, 'r') as file:
            for item in file:
                if ':' in item:
                    key, value = item.split(':', 1)
                    try:
                        value = literal_eval(value)
                    except ValueError:
                        pass
                    file_dict[key] = value

        if not onlyread:
            if name in file_dict:
                if overwrite:
                    if file_dict[name] == values:
                        if not silent:
                            print(f'Same values {values} for {name}')
                    else:
                        prae_values = file_dict[name]
                        file_dict[name] = values
                        if not silent:
                            print(f'Replacing {prae_values} with {values} for {name}')
                else:
                    if not silent:
                        print(f'{name} present in dict, set overwrite=True to overwrite')

            else:
                file_dict[name] = values
                if not silent:
                    print(f'Adding {values} for {name}')

            with open(file_path, 'w') as file:
                for name, values in file_dict.items():
                    if type(values) == str:
                        file.write(f'{name}:"{values}"\n')
                    else:
                        file.write(f'{name}:{values}\n')

    return file_dict


def read_dict_file(file_name, pscripts_path=None):
    if pscripts_path is None:
        file_path = file_name
    else:
        file_path = join(pscripts_path, file_name + '.py')
    file_dict = dict()
    with open(file_path, 'r') as file:
        for item in file:
            if ':' in item:
                key, value = item.split(':', 1)
                if value == '\n':
                    value = None
                else:
                    try:
                        value = literal_eval(value)
                    except ValueError:
                        pass
                file_dict[key] = value

    return file_dict


def delete_files(data_path, pattern):
    main_dir = os.walk(data_path)
    for dirpath, dirnames, filenames in main_dir:
        for f in filenames:
            match = re.search(pattern, f)
            if match:
                os.remove(join(dirpath, f))
                print(f'{f} removed')


def shutdown():
    if iswin:
        os.system('shutdown /s')
    if islin:
        os.system('sudo shutdown now')
    if ismac:
        os.system('sudo shutdown -h now')
