import os
from pathlib import Path

import pandas as pd

pd_funcs = pd.read_csv(str(Path(os.getcwd()).parent) + '/resources/functions_copy.csv', sep=';', index_col=0)
pd_funcs['func_args'] = None
for idx in pd_funcs.index:
    new_args = ''
    sub_args = pd_funcs['subject_args'][idx]
    proj_args = pd_funcs['project_args'][idx]
    add_args = pd_funcs['additional_args'][idx]
    if type(sub_args) == str:
        new_args += sub_args + ','
    if type(proj_args) == str:
        new_args += proj_args + ','
    if type(add_args) == str:
        new_args += add_args
    new_args = new_args.replace(',,', ',')
    new_args = new_args.replace(' ', '')
    if new_args[0] == ',':
        new_args = new_args[1:]
    if new_args[-1] == ',':
        new_args = new_args[:-1]
    pd_funcs['func_args'][idx] = new_args
pd_funcs = pd_funcs.drop(['subject_args', 'project_args', 'additional_args', 'tooltip'], axis=1)
pd_funcs.to_csv(str(Path(os.getcwd()).parent) + '/resources/functions.csv', sep=';')
