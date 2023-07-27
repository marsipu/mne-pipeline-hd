# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
import inspect
import sys
from ast import literal_eval

import pytest
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QLineEdit,
    QDialog,
    QApplication,
    QWidget,
    QHBoxLayout,
    QComboBox,
)
from numpy.testing import assert_allclose

from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.base_widgets import SimpleDict
from mne_pipeline_hd.gui.parameter_widgets import Param, _eval_param

parameters = {
    "IntGui": 1,
    "FloatGui": 5.3,
    "StringGui": "postcentral-lh",
    "MultiTypeGui": 42,
    "FuncGui": "np.arange(10) * np.pi",
    "BoolGui": True,
    "TupleGui": (45, 6),
    "ComboGui": "a",
    "ListGui": [1, 454.33, "postcentral-lh", 5],
    "CheckListGui": ["postcentral-lh"],
    "DictGui": {"A": "B", "C": 58.144, 3: [1, 2, 3, 4], "D": {"A": 1, "B": 2}},
    "SliderGui": 5,
    "ColorGui": {"C": "#98765432", "3": "#97867564"},
}

alternative_parameters = {
    "IntGui": 5,
    "FloatGui": 8.45,
    "StringGui": "precentral-lh",
    "MultiTypeGui": 32,
    "FuncGui": "np.ones((2,3))",
    "BoolGui": False,
    "TupleGui": (2, 23),
    "ComboGui": "b",
    "ListGui": [33, 2234.33, "precentral-lh", 3],
    "CheckListGui": ["precentral-lh"],
    "DictGui": {"B": "V", "e": 11.333, 5: [65, 3, 11], "F": {"C": 1, "D": 2}},
    "SliderGui": 2,
    "ColorGui": {"A": "#12345678", "B": "#13243546"},
}

gui_kwargs = {
    "none_select": True,
    "min_val": -40,
    "max_val": 100,
    "step": 0.5,
    "return_integer": False,
    "param_unit": "ms",
    "options": {"a": "A", "b": "B", "c": "C"},
    "keys": "DictGui",
}


def _check_param(gui, gui_name, alternative=False):
    if alternative:
        value = alternative_parameters[gui_name]
    else:
        value = parameters[gui_name]

    if gui_name == "FuncGui":
        value = _eval_param(value)
        assert_allclose(gui.get_value(), value)
    else:
        assert gui.get_value() == value


@pytest.mark.parametrize("gui_name", list(parameters.keys()))
def test_basic_param_guis(qtbot, gui_name):
    gui_class = getattr(parameter_widgets, gui_name)
    gui_parameters = list(inspect.signature(gui_class).parameters) + list(
        inspect.signature(Param).parameters
    )
    kwargs = {key: value for key, value in gui_kwargs.items() if key in gui_parameters}
    gui = gui_class(data=parameters, name=gui_name, **kwargs)
    qtbot.addWidget(gui)

    # Check if value is correct
    _check_param(gui, gui_name)

    # Check if value changes correctly
    new_param = alternative_parameters[gui_name]
    gui.set_param(new_param)
    _check_param(gui, gui_name, alternative=True)

    # Set value to None
    gui.set_param(None)
    assert parameters[gui_name] is None
    assert not gui.group_box.isChecked()

    # Uncheck groupbox
    gui.group_box.setChecked(True)
    parameters[gui_name] = new_param
    _check_param(gui, gui_name, alternative=True)

    if "max_val" in gui_parameters:
        if gui_name == "TupleGui":
            value = (1000, 1000)
            neg_value = (-1000, -1000)
            max_val = (kwargs["max_val"], kwargs["max_val"])
            min_val = (kwargs["min_val"], kwargs["min_val"])
        else:
            value = 1000
            neg_value = -1000
            max_val = kwargs["max_val"]
            min_val = kwargs["min_val"]
        gui.set_param(value)
        assert parameters[gui_name] == max_val
        # less than min
        gui.set_param(neg_value)
        assert parameters[gui_name] == min_val

    if "return_integer" in gui_parameters:
        gui.return_integer = True
        gui.set_param(True)
        assert gui.get_value() == 1

    if gui_name == "ComboGui":
        # Don't set values which are not in options
        with pytest.raises(KeyError):
            gui.set_param("d")

    if gui_name == "MultiTypeGui":
        for gui_type, gui_name in gui.gui_types.items():
            gui.set_param(parameters[gui_name])
            assert gui.get_value() == parameters[gui_name]
            assert type(gui.get_value()).__name__ == gui_type
        kwargs["type_selection"] = True
        kwargs["type_kwargs"] = dict()
        for gui_name in gui.gui_types.values():
            type_class = getattr(parameter_widgets, gui_name)
            gui_parameters = list(inspect.signature(type_class).parameters) + list(
                inspect.signature(Param).parameters
            )
            t_kwargs = {
                key: value for key, value in gui_kwargs.items() if key in gui_parameters
            }
            kwargs["type_kwargs"][gui_name] = t_kwargs
        gui = gui_class(data=parameters, name=gui_name, **kwargs)
        for gui_type, gui_name in gui.gui_types.items():
            type_idx = gui.types.index(gui_type)
            gui.change_type(type_idx)
            gui.set_param(parameters[gui_name])
            assert gui.get_value() == parameters[gui_name]
            assert type(gui.get_value()).__name__ == gui_type


class ParamGuis(QWidget):
    def __init__(self):
        super().__init__()

        self.gui_dict = dict()

        self.init_ui()

    def init_ui(self):
        test_layout = QVBoxLayout()
        grid_layout = QGridLayout()
        max_cols = 4
        set_none_select = True
        set_groupbox_layout = False
        set_alias = False

        for idx, gui_nm in enumerate(gui_kwargs):
            kw_args = gui_kwargs[gui_nm]
            kw_args["data"] = parameters
            kw_args["name"] = gui_nm
            kw_args["none_select"] = set_none_select
            kw_args["groupbox_layout"] = set_groupbox_layout
            if set_alias:
                kw_args["alias"] = gui_nm + "-alias"
            kw_args["description"] = gui_nm + "-description"
            gui = getattr(parameter_widgets, gui_nm)(**kw_args)
            grid_layout.addWidget(gui, idx // max_cols, idx % max_cols)
            self.gui_dict[gui_nm] = gui

        test_layout.addLayout(grid_layout)

        set_layout = QHBoxLayout()
        self.gui_cmbx = QComboBox()
        self.gui_cmbx.addItems(self.gui_dict.keys())
        set_layout.addWidget(self.gui_cmbx)

        self.set_le = QLineEdit()
        set_layout.addWidget(self.set_le)

        set_bt = QPushButton("Set")
        set_bt.clicked.connect(self.set_param)
        set_layout.addWidget(set_bt)

        show_bt = QPushButton("Show Parameters")
        show_bt.clicked.connect(self.show_parameters)
        set_layout.addWidget(show_bt)

        test_layout.addLayout(set_layout)

        self.setLayout(test_layout)

    def set_param(self):
        current_gui = self.gui_cmbx.currentText()
        try:
            value = literal_eval(self.set_le.text())
        except (SyntaxError, ValueError):
            value = self.set_le.text()
        parameters[current_gui] = value
        p_gui = self.gui_dict[current_gui]
        p_gui.read_param()
        p_gui._set_param()

    def show_parameters(self):
        dlg = QDialog(self)
        layout = QVBoxLayout()
        layout.addWidget(SimpleDict(parameters))
        dlg.setLayout(layout)
        dlg.open()


def show_param_guis():
    app = QApplication.instance() or QApplication(sys.argv)
    test_widget = ParamGuis()
    test_widget.show()
    sys.exit(app.exec())
