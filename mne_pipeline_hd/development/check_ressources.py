import inspect
import sys
from importlib import resources
from inspect import getsourcefile
from os.path import abspath
from pathlib import Path

import pandas as pd

package_parent = str(Path(abspath(getsourcefile(lambda: 0))).parent.parent.parent)
sys.path.insert(0, package_parent)

from mne_pipeline_hd import basic_functions

# Check, if the function-arguments saved in functions.csv are the same as in the signature of the actual function
# (May have changed during development without changing func_args in functions.csv)
with resources.path('mne_pipeline_hd.pipeline_resources', 'functions.csv') as pd_funcs_path:
    pd_funcs = pd.read_csv(str(pd_funcs_path), sep=';', index_col=0)

for func_name in pd_funcs.index:
    module = pd_funcs.loc[func_name, 'module']
    try:
        func = getattr(getattr(basic_functions, module), func_name)
        real_func_args_list = list(inspect.signature(func).parameters)
        if 'kwargs' in real_func_args_list:
            real_func_args_list.remove('kwargs')
        real_func_args = ','.join(real_func_args_list)
        loaded_func_args = pd_funcs.loc[func_name, 'func_args']

        if real_func_args != loaded_func_args:
            pd_funcs.loc[func_name, 'func_args'] = real_func_args
            print(f'Changed function-arguments for {func_name}\n'
                  f'from {loaded_func_args}\n'
                  f'to {real_func_args}')
    except AttributeError:
        pd_funcs.drop(index=func_name, inplace=True)
        print(f'Droped {func_name}, because there is no corresponding function in {module}')

with resources.path('mne_pipeline_hd.pipeline_resources', 'functions.csv') as pd_funcs_path:
    pd_funcs.to_csv(str(pd_funcs_path), 'functions.csv', sep=';')
