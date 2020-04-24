import os
import re
from os.path import join
from pathlib import Path

import pandas as pd

from development import operations_dict as opd

"""
Get functions from old function-call and copy them to pandas-DataFrame
"""

parent_path = str(Path(os.getcwd()).parent)

pd_funcs = pd.DataFrame([], index=['alias', 'group', 'group_idx', 'tab', 'dependencies', 'module', 'subject_args',
                                   'project_args', 'additional_args', 'tooltip'])
file = []
lines = []
func_call_pattern1 = r'([\w]+)\.([\w_]+)\((.+)'  # With Endline considered

with open(join(parent_path, 'pipeline_functions/function_call_old.py'), 'r') as f:
    for line in f:
        lines.append(line)
for idx, line in enumerate(lines):
    match = re.search(func_call_pattern1, line)
    if match:
        matched = match.group()
        current_line = match.group()
        cnt = 1
        while matched[-1] == ',':
            current_line = lines[idx + cnt]
            current_line = current_line.replace(' ', '')
            current_line = current_line.replace('\n', '')
            matched += current_line
            cnt += 1
        matched = matched.replace(' ', '')
        file.append(matched)

func_call_pattern2 = r'([\w]+)\.([\w_]+)\((.+)\)'  # Only for concatenated function-Strings

dest_path = parent_path + '/resources/functions.csv'

for line in file:
    for func_group in opd.all_fs_gs:
        for func in opd.all_fs_gs[func_group]:
            if func in line:
                match = re.search(func_call_pattern2, line)
                if match:
                    if match.group(2) == func:
                        print(f'Function: {match.group(2)}, from module: {match.group(1)}, '
                              f'with parameters: {match.group(3)} in func-group: {func_group}')
                        subject_parameters = []
                        project_parameters = []
                        parameters = []
                        all_params = match.group(3).split(',')
                        for param in all_params:
                            if 'p.' in param:
                                parameters.append(param.replace('p.', ''))
                            elif 'pr.' in param:
                                project_parameters.append(param.replace('pr.', ''))
                            elif 'mw.' in param:
                                project_parameters.append(param.replace('mw.', ''))
                            elif 'figures_path' in param:
                                project_parameters.append(param)
                            else:
                                subject_parameters.append(param)
                        subject_p_str = ','.join(subject_parameters)
                        project_p_str = ','.join(project_parameters)
                        param_str = ','.join(parameters)
                        if 'plot' in func_group:
                            tab = 'Plot'
                        else:
                            tab = 'Compute'
                        pd_funcs[match.group(2)] = [match.group(2), func_group, '', tab, '', match.group(1),
                                                    subject_p_str, project_p_str, param_str, '']
# Transform to have better readability and groupby
pd_funcs = pd_funcs.T

pd_funcs.to_csv(dest_path, sep=';')
