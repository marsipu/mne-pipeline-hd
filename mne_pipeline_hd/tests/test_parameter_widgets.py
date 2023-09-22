# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
import inspect

import pytest
from qtpy.QtCore import Qt
from numpy.testing import assert_allclose

from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.parameter_widgets import Param, _eval_param, LabelGui
from tests._test_utils import click_view_checkbox

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
    "PathGui": "C:/test",
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
    "PathGui": "D:/test",
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

    # Test return integer for BoolGui
    if "return_integer" in gui_parameters:
        gui.return_integer = True
        gui.set_param(True)
        assert gui.get_value() == 1

    # Test ComboGui
    if gui_name == "ComboGui":
        # Don't set values which are not in options
        with pytest.raises(KeyError):
            gui.set_param("d")

        # Test option-aliases
        gui.set_param("a")
        assert gui.param_widget.currentText() == "A"
        gui.param_widget.setCurrentText("B")
        assert gui.get_value() == "b"

    # Test MultiTypeGui
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


def test_label_gui(qtbot, controller):
    """Test opening label-gui without error"""
    # Add fsaverage
    controller.pr.add_fsmri("fsaverage")

    label_gui = LabelGui(data=controller, name="test_labels", default=[])
    qtbot.addWidget(label_gui)
    label_gui.show()

    # Push edit button
    label_gui.param_widget.click()

    # Test parcellation picker
    dlg = label_gui._dialog
    dlg.choose_parc_bt.click()
    parc_plot = dlg._parc_picker._renderer.plotter
    # Add label by clicking on plot
    qtbot.mouseClick(parc_plot, Qt.LeftButton, pos=parc_plot.rect().center(), delay=100)
    assert "superiorfrontal-rh" in dlg._selected_parc_labels
    # Remove label by clicking on plot
    qtbot.mouseClick(parc_plot, Qt.LeftButton, pos=parc_plot.rect().center(), delay=100)
    assert "superiorfrontal-rh" not in dlg._selected_parc_labels
    # Add label by selecting from list
    click_view_checkbox(5, qtbot, dlg.parc_label_list.view, delay=100)
    assert "caudalmiddlefrontal-rh" in dlg._parc_picker._shown_labels
    click_view_checkbox(5, qtbot, dlg.parc_label_list.view, delay=100)
    assert "caudalmiddlefrontal-rh" not in dlg._parc_picker._shown_labels

    # Add all labels
    click_view_checkbox(0, qtbot, dlg.parc_label_list.view, delay=100)
    dlg.close()
    assert label_gui.param_value == ["bankssts-lh"]