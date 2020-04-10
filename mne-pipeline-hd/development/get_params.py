import os
import re
from ast import literal_eval
from pathlib import Path

import pandas as pd

parent_path = str(Path(os.getcwd()).parent)
pd_params = pd.DataFrame([], index=['alias', 'default', 'hint', 'gui_type'])
with open(parent_path + '/resources/parameters_template.py', 'r') as p:
    for line in p:
        if '#' in line:
            param_pattern = r'([\w_]*) = (.*)#(.*)'
            match = re.search(param_pattern, line)
            if match:
                name = match.group(1)
                try:
                    default = literal_eval(match.group(2))
                except (SyntaxError, ValueError):
                    default = match.group(2)
                hint = match.group(3)
                pd_params[name] = [name, default, hint, type(default)]
        else:
            param_pattern = r'([\w_]*) = (.*)'
            match = re.search(param_pattern, line)
            if match:
                name = match.group(1)
                try:
                    default = literal_eval(match.group(2))
                except (SyntaxError, ValueError):
                    default = match.group(2)
                pd_params[name] = [name, default, '', type(default)]

# Transform to have better readability and groupby
pd_params = pd_params.T

parent_path = str(Path(os.getcwd()).parent)
dest_path = parent_path + '/resources/parameters.csv'
pd_params.to_csv(dest_path, sep=';')
