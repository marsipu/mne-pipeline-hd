# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 01:00:31 2019

@author: 'Martin Schulz'
"""
import os
from os import makedirs
from os.path import join, isfile, exists, dirname
import sys
from subprocess import run

try:
    import autoreject as ar
except ImportError:
    print('#%§&$$ autoreject-Import-Bug is not corrected in latest dev')
    ar = 0
import tkinter as t
import re

from mne_pipeline_hd.pipeline_functions import operations_dict as opd


# Todo: If checked, change color
class TkFunctionWindow:

    def __init__(self, master):
        self.master = master
        master.title('Choose the functions to be executed')

        self.var_dict = dict()
        self.pre_func_dict = dict()
        self.func_dict = dict()
        self.c_path = './basic_functions/func_cache.py'

        self.make_chkbs()
        self.huga = 12

        # # React to keyboard input
        # frame = t.Frame(self.master, bg='green')
        # frame.bind('<Return>', self.start)
        # master.bind('<Return>', self.start())

    def make_chkbs(self):
        r_cnt = -1
        c_cnt = 0
        r_max = 25
        for function_group in opd.all_fs_gs:
            r_cnt += 1
            if r_cnt > 25:
                r_cnt = 0
            label = t.Label(self.master, text=function_group,
                            bg='blue', fg='white', relief=t.RAISED)
            label.grid(row=r_cnt, column=c_cnt)
            r_cnt += 1
            for function in opd.all_fs_gs[function_group]:
                var = t.IntVar()
                self.var_dict.update({function: var})
                self.func_dict.update({function: 0})
                chk = t.Checkbutton(self.master, text=function, variable=var)
                chk.grid(row=r_cnt, column=c_cnt, sticky=t.W)
                r_cnt += 1
                if r_cnt >= r_max:
                    c_cnt += 1
                    r_cnt = 0

        # Preload existing checks
        if isfile(self.c_path):
            with open(self.c_path, 'r') as fc:
                # Make sure that cache takes changes from operations_dict
                self.pre_func_dict = eval(fc.read())
                del_list = []
                for k in self.pre_func_dict:
                    if k not in self.func_dict:
                        del_list.append(k)
                if len(del_list) > 0:
                    for d in del_list:
                        del self.pre_func_dict[d]
                        print(f'{d} from operations_cache deleted')
                self.func_dict = self.pre_func_dict

            for f in self.func_dict:
                n = self.func_dict[f]
                self.var_dict[f].set(n)

        if r_cnt > r_max - 6:
            r_cnt = 0
            c_cnt += 1

        bt_start = t.Button(self.master, text='Start',
                            command=self.start, bg='green',
                            activebackground='blue',
                            fg='white', font=100,
                            relief=t.RAISED)
        bt_start.grid(row=int(r_cnt + (r_max - r_cnt) / 3), column=c_cnt,
                      rowspan=int((r_max - r_cnt + 1) / 3),
                      sticky=t.N + t.S + t.W + t.E)

        bt_stop = t.Button(self.master, text='Stop',
                           command=self.stop, bg='red',
                           activebackground='yellow',
                           fg='white', font=100,
                           relief=t.RAISED)
        bt_stop.grid(row=int(r_cnt + (r_max - r_cnt) * 2 / 3), column=c_cnt,
                     rowspan=int((r_max - r_cnt + 1) / 3),
                     sticky=t.N + t.S + t.W + t.E)

        bt_clear = t.Button(self.master, text='Clear_all',
                            command=self.clear_all, bg='magenta',
                            activebackground='cyan',
                            fg='white', font=100,
                            relief=t.RAISED)

        bt_clear.grid(row=r_cnt, column=c_cnt,
                      rowspan=int((r_max - r_cnt + 1) / 3),
                      sticky=t.N + t.S + t.W + t.E)

    def clear_all(self):
        for x in self.var_dict:
            self.var_dict[x].set(0)

    def start(self):
        for f in self.var_dict:
            n = self.var_dict[f].get()
            self.func_dict[f] = n

        with open(self.c_path, 'w') as fc:
            fc.write(str(self.func_dict))

        self.master.quit()
        self.master.destroy()

    def stop(self):
        for f in self.var_dict:
            n = self.var_dict[f].get()
            self.func_dict[f] = n

        with open(self.c_path, 'w') as fc:
            fc.write(str(self.func_dict))

        self.master.quit()
        self.master.destroy()
        # sys.exit() Not working for PyCharm, stopping the console
        raise SystemExit(0)


def choose_function():
    master = t.Tk()
    gui = TkFunctionWindow(master)
    master.mainloop()

    return gui.func_dict


def autoreject_handler(name, epochs, highpass, lowpass, sub_script_path, overwrite_ar=False,
                       only_read=False):
    reject_value_path = join(sub_script_path, f'reject_values_{highpass}-{lowpass}_Hz.py')

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
                    value = eval(value[:-1])
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


def dict_filehandler(name, file_name, sub_script_path, values=None,
                     onlyread=False, overwrite=True, silent=False):
    file_path = join(sub_script_path, file_name + '.py')
    file_dict = dict()

    if not isfile(file_path):
        if not exists(sub_script_path):
            makedirs(sub_script_path)
            if not silent:
                print(sub_script_path + ' created')
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
                    value = eval(value)
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


def read_dict_file(file_name, sub_script_path=None):
    if sub_script_path is None:
        file_path = file_name
    else:
        file_path = join(sub_script_path, file_name + '.py')
    file_dict = dict()
    with open(file_path, 'r') as file:
        for item in file:
            if ':' in item:
                key, value = item.split(':', 1)
                if value == '\n':
                    value = None
                else:
                    value = eval(value)
                file_dict[key] = value

    return file_dict


def order_the_dict(filename, sub_script_path, unspecified_names=False):
    file_path = join(sub_script_path, 'MotStart-LBT_diffs' + '.py')
    file_dict = dict()
    order_dict1 = dict()
    order_dict2 = dict()
    order_dict3 = dict()
    order_list = []

    with open(file_path, 'r') as file:
        for item in file:
            if ':' in item:
                key, value = item.split(':', 1)
                value = eval(value)
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
        order_list = []
        order_list.append(order_dict1[key])
    order_list.sort()


def get_pipeline_path(path):
    match = re.search('mne_pipeline_hd', path)
    pipeline_path = path[:match.span()[1]]

    return pipeline_path


def get_all_fif_files(dirname):
    # create a list of file and sub directories
    # names in the given directory
    list_of_file = os.walk(dirname)
    all_fif_files = list()
    paths = dict()
    # Iterate over all the entries
    for dirpath, dirnames, filenames in list_of_file:

        for file in filenames:
            if file[-4:] == '.fif':
                all_fif_files.append(file)
                paths.update({file: join(dirpath, file)})

    return all_fif_files, paths


def delete_files(data_path, pattern):
    main_dir = os.walk(data_path)
    for dirpath, dirnames, filenames in main_dir:
        for f in filenames:
            match = re.search(pattern, f)
            if match:
                os.remove(join(dirpath, f))
                print(f'{f} removed')


def shutdown():
    if sys.platform == 'win32':
        os.system('shutdown /s')
    if sys.platform == 'linux':
        os.system('sudo shutdown now')
    if sys.platform == 'darwin':
        os.system('sudo shutdown -h now')


# Todo: Update MNE-Function zum Funktionieren bringen
def update_mne():
    command = ["curl --remote-name https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml",
               "conda env update --file environment.yml",
               "pip install -r requirements.txt"]
    run(command, shell=True)


# Todo: Update Pipeline-Function
def update_pipeline(pipeline_path):
    command = f'pip install --src {dirname(pipeline_path)} --upgrade' \
              Rf'-e git+https://github.com/marsipu/mne_pipeline_hd.git@origin/master#egg=mne_pipeline_hd'
    run(command, shell=True)
