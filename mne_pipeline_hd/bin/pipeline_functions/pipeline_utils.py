# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import os
import re
from ast import literal_eval
from os import makedirs
from os.path import exists, isfile, join

import autoreject as ar

from bin.pipeline_functions import islin, ismac, iswin


def autoreject_handler(name, epochs, highpass, lowpass, pscripts_path, overwrite_ar=False,
                       only_read=False):
    reject_value_path = join(pscripts_path, f'reject_values_{highpass}-{lowpass}_Hz.py')

    if not isfile(reject_value_path):
        if only_read:
            raise Exception('New Autoreject-Threshold only from epoch_raw')
        else:
            reject = ar.get_rejection_threshold(epochs, ch_types=['grad'])
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
                reject = ar.get_rejection_threshold(epochs, ch_types=['grad'])
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
            reject = ar.get_rejection_threshold(epochs, ch_types=['grad'])
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


# Todo: order-dict-function
def order_the_dict(filename, pscripts_path, unspecified_names=False):
    file_path = join(pscripts_path, 'MotStart-LBT_diffs' + '.py')
    file_dict = dict()
    order_dict1 = dict()
    order_dict2 = dict()
    order_dict3 = dict()
    order_list = []

    with open(file_path, 'r') as file:
        for item in file:
            if ':' in item:
                key, value = item.split(':', 1)
                try:
                    value = literal_eval(value)
                except ValueError:
                    pass
                file_dict[key] = value

    if not unspecified_names:
        pattern = r'(pp[0-9][0-9]*[a-z]*)_([0-9]{0,3}t?)_([a,b]$)'
    else:
        pattern = r'.*'

    for key in file_dict:
        match = re.match(pattern, key)
        number1 = match.group(1)
        number2 = match.group(2)
        number3 = match.group(3)
        order_dict1.update(number1)
        order_dict2.update(number2)
        order_dict3.update(number3)

    for key in order_dict1:
        order_list.append(order_dict1[key])
    order_list.sort()


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
