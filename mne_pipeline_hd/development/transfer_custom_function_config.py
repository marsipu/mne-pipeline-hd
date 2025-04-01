# -*- coding: utf-8 -*-
import json
import math
from ast import literal_eval

import pandas as pd

from mne_pipeline_hd.pipeline.pipeline_utils import TypedJSONEncoder

func_config_path = "../extra/functions.csv"
func_pd = pd.read_csv(func_config_path, sep=";", index_col=0)

op_dict = {"module_name": "basic_operations", "functions": {}, "parameters": {}}
op_param_set = set()

plot_dict = {"module_name": "basic_operations", "functions": {}, "parameters": {}}
plot_param_set = set()

for func_name, row in func_pd.iterrows():
    row_dict = row.to_dict()
    if row_dict["matplotlib"] or row_dict["mayavi"]:
        row_dict["thread-safe"] = False
    else:
        row_dict["thread-safe"] = True

    for pop_key in [
        "matplotlib",
        "mayavi",
        "target",
        "tab",
        "dependencies",
        "pkg_name",
    ]:
        row_dict.pop(pop_key)

    module = row_dict.pop("module")
    params = row_dict.pop("func_args").split(",")

    row_dict["inputs"] = list()
    row_dict["outputs"] = list()

    for key, value in row_dict.items():
        if isinstance(value, float) and math.isnan(value):
            row_dict[key] = None

    if module == "operations":
        op_dict["functions"][func_name] = row_dict
        op_param_set.update(params)
    else:
        plot_dict["functions"][func_name] = row_dict
        plot_param_set.update(params)


param_pd = pd.read_csv("../extra/parameters.csv", sep=";", index_col=0)
for param_name, row in param_pd.iterrows():
    row_dict = row.to_dict()
    eval_dict = dict()
    for key, value in row_dict.items():
        if key in ["default", "gui_args"]:
            try:
                value = literal_eval(value)
            except (ValueError, SyntaxError):
                pass
        if isinstance(value, float) and math.isnan(value):
            value = None
        eval_dict[key] = value

    if param_name in op_param_set:
        op_dict["parameters"][param_name] = eval_dict
    if param_name in plot_param_set:
        plot_dict["parameters"][param_name] = eval_dict

with open("../basic_functions/basic_operations_config.json", "w") as f:
    json.dump(op_dict, f, indent=4, cls=TypedJSONEncoder)

with open("../basic_functions/basic_plot_config.json", "w") as f:
    json.dump(plot_dict, f, indent=4, cls=TypedJSONEncoder)
