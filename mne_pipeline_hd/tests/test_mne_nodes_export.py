"""Tests for converting Pipeline-HD custom functions to MNE-Nodes plugins."""

import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from mne_pipeline_hd.pipeline.mne_nodes_export import export_custom_functions


def test_custom_function_export(tmp_path):
    source = tmp_path / "custom.py"
    original = '''\
# Copyright example
"""Original module description."""
from __future__ import annotations

import math
import os
from os.path import join
import numpy as np
import pandas as pd
from mne_pipeline_hd.functions.operations import calculate_gfp
from mne_pipeline_hd.pipeline.loading import Group

def scale(meeg, factor, limits):
    """Scale raw data."""
    raw = meeg.load_raw()
    raw["value"] *= math.floor(factor)
    meeg.save_raw(raw)

def unsafe(meeg):
    raw = meeg.load_raw()
    print(meeg.pr.name)
    meeg.save_raw(raw)

def conditional(meeg):
    raw = meeg.load_raw()
    if raw:
        meeg.save_raw(raw)

def choose_raw(meeg, factor, which="raw"):
    if which == "raw":
        raw = meeg.load_raw()
    else:
        raw = meeg.load_filtered()
    raw["value"] *= factor
    if which == "raw":
        meeg.save_raw(raw)
    else:
        meeg.save_filtered(raw)

def bad_choice(meeg, which):
    if which == "raw":
        raw = meeg.load_raw()
    else:
        raw = meeg.load_filtered("unexpected")
    if which == "raw":
        meeg.save_raw(raw)
    else:
        meeg.save_filtered(raw)

def named(meeg, factor):
    if meeg.name == "skip":
        return
    raw = meeg.load_raw()
    if "bad" in meeg.bad_channels:
        meeg.bad_channels.remove("bad")
        raw["value"] *= factor
        meeg.save_raw(raw)

def helper(epochs, table):
    epochs["value"] = int(table.iloc[0, 0])

def add_table(meeg):
    epochs = meeg.load_epochs()
    file_name = "ratings_meta"
    file_path = join(meeg.save_dir, f"{meeg.name}_{meeg.p_preset}_{file_name}.csv")
    table = pd.read_csv(file_path, index_col=0)
    helper(epochs, table)
    meeg.save_epochs(epochs)

def make_table(meeg):
    events = meeg.load_events()
    file_name = "ratings_meta"
    file_path = join(meeg.save_dir, f"{meeg.name}_{meeg.p_preset}_{file_name}.csv")
    table = pd.DataFrame({"value": events})
    table.to_csv(file_path)

def make_and_attach(meeg):
    events = meeg.load_events()
    file_name = "ratings_meta"
    file_path = join(meeg.save_dir, f"{meeg.name}_{meeg.p_preset}_{file_name}.csv")
    table = pd.DataFrame({"value": events})
    table.to_csv(file_path)
    table["value"] *= 2
    epochs = meeg.load_epochs()
    helper(epochs, table)
    meeg.save_epochs(epochs)

def combine(fsmri, label_combinations):
    for new_name, label_names in label_combinations.items():
        labels = fsmri.get_labels(label_names)
        result = labels[0]
        for label in labels[1:]:
            result += label
        result.name = new_name
        result.save(join(fsmri.subjects_dir, fsmri.name, "label", f"{new_name}.label"))

def settings_values(meeg, n_jobs, group_colors):
    raw = meeg.load_raw()
    raw["value"] = n_jobs + len(group_colors)
    meeg.save_raw(raw)

def group_summary(group):
    fig = []
    for evokeds, meeg in group.load_items(data_type="evoked"):
        fig.append((meeg.name, evokeds))
    group.plot_save("summary", matplotlib_figure=fig)

def group_gfp(group):
    fig = []
    for evokeds, meeg in group.load_items(data_type="evoked"):
        fig.append(calculate_gfp(evokeds[0])["grad"])
    group.plot_save("gfp", matplotlib_figure=fig)

def project_connectivity(ct, cluster_trial):
    fig = []
    for group_name in ct.pr.sel_groups:
        group = Group(group_name, ct)
        values = group.load_ga_con()[cluster_trial[group_name]]
        fig.append((group_name, values))
    Group("all", ct).plot_save("summary", matplotlib_figure=fig)

def unsupported_project(ct):
    group = Group("a", ct)
    fig = group.load_ga_con()
    print(ct.pr.name)
    Group("all", ct).plot_save("summary", matplotlib_figure=fig)

def bad_bound(meeg, threshold):
    raw = meeg.load_raw()
    raw["value"] = threshold
    meeg.save_raw(raw)

def make_events(meeg):
    raw = meeg.load_raw()
    events = [raw["value"]]
    meeg.save_events(events)

def group_average(group, factor):
    result = {}
    for trial in group.sel_trials:
        for evokeds, meeg in group.load_items(data_type="evoked"):
            result[trial, meeg.name] = evokeds * factor
    group.save_ga_evokeds(result)

def plot_average(group):
    ga_evokeds = group.load_ga_evokeds()
    fig = [group.name, ga_evokeds]
    fig.savefig(join(group.save_dir, f"{group.name}.png"))
'''
    source.write_text(original, encoding="utf-8")
    functions = tmp_path / "functions.csv"
    functions.write_text(
        ";target;group;tab;module;dependencies\n"
        "scale;MEEG;Test;Compute;custom;\n"
        "unsafe;MEEG;Test;Compute;custom;\n"
        "conditional;MEEG;Test;Compute;custom;\n"
        "choose_raw;MEEG;Test;Compute;custom;\n"
        "bad_choice;MEEG;Test;Compute;custom;\n"
        "named;MEEG;Test;Compute;custom;\n"
        "add_table;MEEG;Test;Compute;custom;\n"
        "make_table;MEEG;Test;Compute;custom;\n"
        "make_and_attach;MEEG;Test;Compute;custom;\n"
        "combine;FSMRI;Test;Compute;custom;\n"
        "settings_values;MEEG;Test;Compute;custom;\n"
        "group_summary;Group;Test;Compute;custom;\n"
        "group_gfp;Group;Test;Compute;custom;\n"
        "project_connectivity;Other;Test;Compute;custom;\n"
        "unsupported_project;Other;Test;Compute;custom;\n"
        "bad_bound;MEEG;Test;Compute;custom;\n"
        "make_events;MEEG;Test;Compute;custom;\n"
        "group_average;Group;Test;Compute;custom;\n"
        "plot_average;Group;Test;Compute;custom;\n",
        encoding="utf-8",
    )
    parameters = tmp_path / "parameters.csv"
    parameters.write_text(
        ";default;gui_type;gui_args;description\n"
        "factor;2;IntGui;;Factor\n"
        "limits;(1, 3);TupleGui;{'max_val': 5};Limits\n"
        "label_combinations;{};DictGui;;Labels\n"
        "group_colors;{};ColorGui;{'keys': ['A']};Colors\n"
        "cluster_trial;Trial;DictGui;;Trials\n"
        "threshold;1200;IntGui;;Threshold\n",
        encoding="utf-8",
    )
    destination = tmp_path / "output"
    destination.mkdir()
    exported, skipped = export_custom_functions(
        source, functions, [parameters], destination
    )
    assert exported == [
        "scale",
        "conditional",
        "choose_raw",
        "named",
        "add_table",
        "make_table",
        "make_and_attach",
        "combine",
        "settings_values",
        "group_summary",
        "group_gfp",
        "project_connectivity",
        "make_events",
        "group_average",
        "plot_average",
    ]
    assert set(skipped) == {"unsafe", "bad_choice", "bad_bound", "unsupported_project"}
    assert "bounds" in skipped["bad_bound"]
    assert source.read_text(encoding="utf-8") == original
    script = (destination / "custom.py").read_text(encoding="utf-8")
    assert "meeg" not in script
    assert "import os" not in script
    assert script.startswith("# Copyright example\n")
    assert "Copyright (c) 2019-2024, authors of mne-pipeline-hd" in script
    namespace = {}
    exec(compile(script, "custom.py", "exec"), namespace)  # noqa: S102
    assert namespace["__doc__"] == "Original module description."
    raw = {"value": 4}
    assert namespace["scale"](raw, 2, (1, 3)) == {"value": 8}
    assert namespace["choose_raw"]({"value": 4}, 2) == {"value": 8}
    assert namespace["named"]({"value": 4}, "run", ["bad"], 2) == ({"value": 8}, [])
    assert namespace["named"]({"value": 4}, "skip", ["bad"], 2) == (
        {"value": 4},
        ["bad"],
    )
    table = namespace["make_table"]([5])
    pd.testing.assert_frame_equal(table, pd.DataFrame({"value": [5]}))
    assert namespace["add_table"]({"value": 0}, table) == {"value": 5}
    result, saved_table = namespace["make_and_attach"]([5], {"value": 0})
    assert result == {"value": 10}
    pd.testing.assert_frame_equal(saved_table, table)

    class Label:
        def __init__(self, name, value):
            self.name = name
            self.value = value

        def __add__(self, other):
            return Label(self.name, self.value + other.value)

    combined = namespace["combine"](
        [Label("a", 1), Label("b", 2)], {"combined": ["a", "b"]}
    )
    assert [(label.name, label.value) for label in combined] == [("combined", 3)]
    assert namespace["group_summary"]([[1], [2]], ["a", "b"]) == [
        ("a", [1]),
        ("b", [2]),
    ]
    with pytest.raises(ValueError):
        namespace["group_summary"]([[1]], [])

    class Evoked:
        data = np.array([[3.0, 4.0]])

        def get_channel_types(self, **kwargs):
            return ["grad"]

        def copy(self):
            return self

        def pick(self, ch_type):
            return self

    np.testing.assert_array_equal(
        namespace["group_gfp"]([[Evoked()]], ["a"])[0], [3.0, 4.0]
    )
    assert namespace["project_connectivity"](
        {"a": {"trial": 1}, "b": {"trial": 2}}, {"a": "trial", "b": "trial"}
    ) == [("a", 1), ("b", 2)]
    assert namespace["make_events"]({"value": 3}) == [3]
    assert namespace["group_average"]([[1], [2]], ["a", "b"], ["T"], 2) == {
        ("T", "a"): [1, 1],
        ("T", "b"): [2, 2],
    }
    assert namespace["plot_average"]({"T": 1}, "A") == ["A", {"T": 1}]
    config = json.loads(
        (destination / "custom_config.json").read_text(encoding="utf-8")
    )
    assert config["scale"]["inputs"]["raw"]["accepted_ports"] == ["raw"]
    assert config["scale"]["outputs"]["raw"]["accepted_ports"] == ["raw"]
    assert config["scale"]["parameters"]["limits"]["default"] == {"tuple_type": [1, 3]}
    assert "which" not in config["choose_raw"]["parameters"]
    assert list(config["named"]["outputs"]) == ["raw", "bad_channels"]
    assert config["add_table"]["inputs"]["table"]["accepted_ports"] == ["dataframe"]
    assert config["make_table"]["outputs"]["table"]["accepted_ports"] == ["dataframe"]
    assert list(config["make_and_attach"]["inputs"]) == ["events", "epochs"]
    assert list(config["make_and_attach"]["outputs"]) == ["epochs", "table"]
    assert config["combine"]["outputs"]["combined_labels"]["accepted_ports"] == [
        "labels"
    ]
    assert config["settings_values"]["parameters"]["n_jobs"] == {
        "gui": "IntGui",
        "default": -1,
        "min_val": -1,
    }
    assert (
        config["settings_values"]["parameters"]["group_colors"]["gui"] == "ColorDictGui"
    )
    assert config["group_summary"]["target"] == "group"
    assert "cluster_trial" in config["project_connectivity"]["inputs"]
    assert "cluster_trial" not in config["project_connectivity"]["parameters"]
    assert "max_val" not in config["scale"]["parameters"]["limits"]
    assert config["make_events"]["outputs"]["events"]["accepted_ports"] == ["events"]
    assert list(config["group_average"]["parameters"]) == ["sel_trials", "factor"]
    assert config["group_average"]["outputs"]["result"]["accepted_ports"] == [
        "ga_evokeds"
    ]
    assert list(config["plot_average"]["inputs"]) == ["ga_evokeds", "group_name"]
    with pytest.raises(FileExistsError):
        export_custom_functions(source, functions, [parameters], destination)
    assert (destination / "custom.py").read_text(encoding="utf-8") == script

    cli_output = tmp_path / "cli-output"
    cli_output.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mne_pipeline_hd.pipeline.mne_nodes_export",
            str(source),
            str(functions),
            str(cli_output),
            "--parameters",
            str(parameters),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Skipped unsafe:" in result.stdout
    assert (cli_output / "custom_config.json").is_file()
