# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 01:00:31 2019

@author: 'Martin Schulz'
"""
import os
from os import makedirs
from os.path import join, isfile, exists
import sys
import autoreject as ar
import tkinter as t
import re

from pipeline_functions import operations_dict as opd

class Function_Window:

    def __init__(self, master):
        self.master = master
        master.title('Choose the functions to be executed')

        self.var_dict = {}
        self.pre_func_dict = {}
        self.func_dict = {}
        self.c_path = './pipeline_functions/func_cache.py'

        self.make_chkbs()
        self.huga = 12

    def make_chkbs(self):
        r_cnt = -1
        c_cnt = 0
        r_max = 25
        for function_group in opd.all_fs:
            r_cnt += 1
            if r_cnt > 25:
                r_cnt = 0
            label = t.Label(self.master, text=function_group,
                            bg='blue',fg='white', relief=t.RAISED)
            label.grid(row=r_cnt, column=c_cnt)
            r_cnt += 1
            for function in opd.all_fs[function_group]:
                var = t.IntVar()
                self.var_dict.update({function:var})
                self.func_dict.update({function:0})
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
                if len(del_list)>0:
                    for d in del_list:
                        del self.pre_func_dict[d]
                        print(f'{d} from operations_cache deleted')
                self.func_dict = self.pre_func_dict

            for f in self.func_dict:
                n = self.func_dict[f]
                self.var_dict[f].set(n)
        
        if r_cnt>r_max-6:
            r_cnt = 0
            c_cnt += 1
        
        bt_start = t.Button(self.master, text='Start',
                            command=self.start, bg='green',
                            activebackground='blue',
                            fg='white', font=100,
                            relief=t.RAISED)
        bt_start.grid(row=int(r_cnt+(r_max-r_cnt)/3), column=c_cnt,
                      rowspan=int((r_max-r_cnt+1)/3),
                      sticky=t.N+t.S+t.W+t.E)

        bt_stop = t.Button(self.master, text='Stop',
                            command=self.stop, bg='red',
                            activebackground='yellow',
                            fg='white', font=100,
                            relief=t.RAISED)
        bt_stop.grid(row=int(r_cnt+(r_max-r_cnt)*2/3), column=c_cnt,
                      rowspan=int((r_max-r_cnt+1)/3),
                      sticky=t.N+t.S+t.W+t.E)

        bt_clear = t.Button(self.master, text='Clear_all',
                      command=self.clear_all, bg='magenta',
                      activebackground='cyan',
                      fg='white', font=100,
                      relief=t.RAISED)

        bt_clear.grid(row=r_cnt, column=c_cnt,
                      rowspan=int((r_max-r_cnt+1)/3),
                      sticky=t.N+t.S+t.W+t.E)

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

        print('Function-Window closed')

        self.master.quit()
        self.master.destroy()

def choose_function():
    master = t.Tk()
    gui = Function_Window(master)
    master.mainloop()

    return gui.func_dict


def autoreject_handler(name, epochs, sub_script_path, overwrite_ar=False,
                       only_read=False):

    reject_value_path = join(sub_script_path, 'reject_values.py')

    if not isfile(reject_value_path):
        if only_read:
            raise Exception('New Autoreject-Threshold only from epoch_raw')
        else:
            reject = ar.get_rejection_threshold(epochs)
            with open(reject_value_path, 'w') as rv:
                rv.write(f'{name}:{reject}\n')
            print(reject_value_path + ' created')

    else:
        read_reject = {}
        with open(reject_value_path, 'r') as rv:

            for item in rv:
                if ':' in item:
                    key,value = item.split(':', 1)
                    value = eval(value[:-1])
                    read_reject[key] = value

        if name in read_reject:
            if overwrite_ar:
                if only_read:
                    raise Exception('New Autoreject-Threshold only from epoch_raw')
                print('Rejection with Autoreject')
                reject = ar.get_rejection_threshold(epochs)
                prae_reject = read_reject[name]
                read_reject[name] = reject
                if prae_reject == reject:
                    print(f'Same reject_values {reject}')
                else:
                    print(f'Replaced AR-Threshold {prae_reject} with {reject}')
                with open(reject_value_path, 'w') as rv:
                    for key,value in read_reject.items():
                        rv.write(f'{key}:{value}\n')
            else:
                reject = read_reject[name]
                print('Reading Rejection-Threshold from file')

        else:
            if only_read:
                raise Exception('New Autoreject-Threshold only from epoch_raw')
            print('Rejection with Autoreject')
            reject = ar.get_rejection_threshold(epochs)
            read_reject.update({name:reject})
            print(f'Added AR-Threshold {reject} for {name}')
            with open(reject_value_path, 'w') as rv:
                for key,value in read_reject.items():
                    rv.write(f'{key}:{value}\n')

    return reject

def dict_filehandler(name, file_name, sub_script_path, values=None,
                     onlyread=False, overwrite=True, silent=False):

    file_path = join(sub_script_path, file_name + '.py')
    file_dict = {}

    if not isfile(file_path):
        if not exists(sub_script_path):
            makedirs(sub_script_path)
            if not silent:
                print(sub_script_path + ' created')
        with open(file_path, 'w') as file:
            file.write(f'{name}:{values}\n')
            if not silent:
                print(file_path + ' created')
    else:
        with open(file_path, 'r') as file:
            for item in file:
                if ':' in item:
                    key,value = item.split(':', 1)
                    value = eval(value)
                    file_dict[key]=value

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
                    file.write(f'{name}:{values}\n')

    return file_dict

def read_dict_file(file_name, sub_script_path):

    file_path = join(sub_script_path, file_name + '.py')
    file_dict = {}
    with open(file_path, 'r') as file:
        for item in file:
            if ':' in item:
                key,value = item.split(':', 1)
                value = eval(value)
                file_dict[key]=value

    return file_dict

def order_the_dict(filename, sub_script_path, unspecified_names=False):

    file_path = join(sub_script_path, 'MotStart-LBT_diffs' + '.py')
    file_dict = {}
    order_dict1 = {}
    order_dict2 = {}
    order_dict3 = {}
    order_list = []

    with open(file_path, 'r') as file:
        for item in file:
            if ':' in item:
                key,value = item.split(':', 1)
                value = eval(value)
                file_dict[key]=value

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

def get_subject_groups(all_files, fuse_ab, unspecified_names):

    files = []

    pre_order_dict = {}
    order_dict = {}
    ab_dict = {}
    comp_dict = {}
    grand_avg_dict = {}
    sub_files_dict = {}

    basic_pattern = r'(pp[0-9][0-9]*[a-z]*)_([0-9]{0,3}t?)_([a,b]$)'
    for s in all_files:
        match = re.match(basic_pattern, s)
        if match:
            files.append(s)

    for s in files:
        match = re.match(basic_pattern, s)
        key = match.group(1) + '_' + match.group(3)
        if key in pre_order_dict:
            pre_order_dict[key].append(match.group(2))
        else:
            pre_order_dict.update({key:[match.group(2)]})

    for key in pre_order_dict:
        v_list = pre_order_dict[key]
        order_dict.update({key:{}})
        for it in v_list:
            if it=='16' or it=='32':
                order_dict[key].update({it:'low'})
            if it=='64' or it=='128':
                order_dict[key].update({it:'middle'})
            if it=='256' or it=='512':
                order_dict[key].update({it:'high'})
            if it=='t':
                order_dict[key].update({it:'tactile'})
        """if 't' in v_list:
            v_list.remove('t')
        v_list.sort(key=int)
        order_dict.update({key:{}})
        if len(v_list)==1:
            order_dict[key].update({v_list[0]:'undefined'})
        if len(v_list)==2:
            order_dict[key].update({v_list[0]:'low'})
            order_dict[key].update({v_list[1]:'high'})
        if len(v_list)==3:
            order_dict[key].update({v_list[0]:'low'})
            order_dict[key].update({v_list[1]:'middle'})
            order_dict[key].update({v_list[2]:'high'})
        if len(v_list)==4:
            order_dict[key].update({v_list[0]:'low'})
            order_dict[key].update({v_list[1]:'middle'})
            order_dict[key].update({v_list[2]:'high'})
            order_dict[key].update({v_list[3]:'high'})
        order_dict[key].update({'t':'tactile'})"""

    for s in files:
        match = re.match(basic_pattern, s)
        key = match.group(1) + '_' + match.group(2)
        if key in ab_dict:
            ab_dict[key].append(s)
        else:
            ab_dict.update({key:[s]})

    for s in files:
        match = re.match(basic_pattern, s)
        key = match.group(1) + '_' + match.group(3)
        sub_key = order_dict[key][match.group(2)]
        if fuse_ab:
            key = match.group(1)
            if key in comp_dict:
                if sub_key in comp_dict[key]:
                    comp_dict[key][sub_key].append(s)
                else:
                    comp_dict[key].update({sub_key:[s]})
            else:
                comp_dict.update({key:{sub_key:[s]}})
        else:
            if key in comp_dict:
                comp_dict[key].update({sub_key:[s]})
            else:
                comp_dict.update({key:{sub_key:[s]}})

    for s in files:
        match = re.match(basic_pattern, s)
        if fuse_ab:
            key = order_dict[match.group(1)+'_'+match.group(3)][match.group(2)]
        else:
            key = order_dict[match.group(1)+'_'+match.group(3)][match.group(2)]\
            + '_' + match.group(3)
        if key in grand_avg_dict:
            grand_avg_dict[key].append(s)
        else:
            grand_avg_dict.update({key:[s]})

    for s in files:
        match = re.match(basic_pattern, s)
        key = match.group(1)
        if key in sub_files_dict:
            sub_files_dict[key].append(s)
        else:
            sub_files_dict.update({key:[s]})

    if unspecified_names:
        grand_avg_dict.update({'Unspecified':all_files})

    return ab_dict, comp_dict, grand_avg_dict, sub_files_dict

def getallfifFiles(dirName):
    # create a list of file and sub directories
    # names in the given directory
    listOfFile = os.walk(dirName)
    all_fif_files = list()
    paths = dict()
    # Iterate over all the entries
    for dirpath, dirnames, filenames in listOfFile:

        for file in filenames:
            if file[-4:] == '.fif':
                all_fif_files.append(file)
                paths.update({file:join(dirpath, file)})

    return all_fif_files, paths

def shutdown():
    if sys.platform == 'win32':
        os.system('shutdown /s')
    if sys.platform == 'linux':
        os.system('sudo shutdown now')
    if sys.platform == 'darwin':
        os.system('sudo shutdown -h now')