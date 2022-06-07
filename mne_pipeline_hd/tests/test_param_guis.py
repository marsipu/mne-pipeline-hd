# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""
import inspect

import pytest

from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.parameter_widgets import Param

parameters = {'IntGui': 1,
              'FloatGui': 5.3,
              'StringGui': 'postcentral-lh',
              'MultiTypeGui': 42,
              'FuncGui': 'np.arange(10) * np.pi',
              'BoolGui': True,
              'TupleGui': (45, 6),
              'ComboGui': 'a',
              'ListGui': [1, 454.33, 'postcentral-lh', 5],
              'CheckListGui': ['postcentral-lh'],
              'DictGui': {'A': 'B',
                          'C': 58.144,
                          3: [1, 2, 3, 4],
                          'D': {'A': 1, 'B': 2}},
              'SliderGui': 5}

alternative_parameters = {'IntGui': 5,
                          'FloatGui': 8.45,
                          'StringGui': 'precentral-lh',
                          'MultiTypeGui': 32,
                          'FuncGui': 'np.ones((2,3))',
                          'BoolGui': False,
                          'TupleGui': (2, 23),
                          'ComboGui': 'b',
                          'ListGui': [33, 2234.33, 'precentral-lh', 3],
                          'CheckListGui': ['precentral-lh'],
                          'DictGui': {'B': 'V',
                                      'e': 11.333,
                                      5: [65, 3, 11],
                                      'F': {'C': 1, 'D': 2}},
                          'SliderGui': 2}

gui_kwargs = {'none_select': True,
              'min_val': -4,
              'max_val': 10,
              'step': 0.5,
              'type_selection': True,
              'param_unit': 'ms',
              'options': {'a': 'A', 'b': 'B', 'c': 'C'}}


@pytest.mark.parametrize('gui_name', list(parameters.keys()))
def test_basic_param_guis(qtbot, gui_name):
    gui_class = getattr(parameter_widgets, gui_name)
    gui_parameters = list(inspect.signature(gui_class).parameters) + \
                     list(inspect.signature(Param).parameters)
    kwargs = {key: value for key, value in gui_kwargs.items()
              if key in gui_parameters}
    gui = gui_class(data=parameters, name=gui_name, **kwargs)
    qtbot.addWidget(gui)

    # Check if value is correct
    assert gui.get_value() == parameters[gui_name]

    # Check if value changes correctly
    new_param = alternative_parameters[gui_name]
    gui.set_param(new_param)
    assert gui.get_value() == new_param
    assert parameters[gui_name] == new_param

    # Set value to None
    value_pre_none = gui.get_value()
    gui.set_param(None)
    assert parameters[gui_name] is None
    assert not gui.group_box.isChecked()

    # Uncheck groupbox
    gui.group_box.setChecked(True)
    assert parameters[gui_name] == value_pre_none

    if 'max_val' in gui_parameters:
        gui.set_param(1000)
        assert parameters[gui_name] == kwargs['max_val']
        # less than min
        gui.param_widget.setValue(-1000)
        assert parameters[gui_name] == kwargs['min_val']
