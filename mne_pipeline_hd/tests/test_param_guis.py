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
from mne_pipeline_hd.gui.parameter_widgets import IntGui

parameters = {'IntGui': 1,
              'FloatGui': 5.3,
              'StringGui': 'Havona',
              'MultiTypeGui': 42,
              'FuncGui': 5000,
              'BoolGui': True,
              'TupleGui': (45, 6),
              'ComboGui': 'a',
              'ListGui': [1, 454.33, 'post_central-lh', 5],
              'CheckListGui': ['bananaaa'],
              'DictGui': {'A': 'hubi', 'B': 58.144, 3: 'post_lh'},
              'SliderGui': 5}

keyword_args = {
    'IntGui': {'min_val': -4,
               'max_val': 10,
               'param_unit': 't'},
    'FloatGui': {'min_val': -18,
                 'max_val': 64,
                 'step': 0.4,
                 'param_unit': 'flurbo'},
    'StringGui': {'input_mask': 'ppAAA.AA;_',
                  'param_unit': 'N'},
    'MultiTypeGui': {'type_selection': True},
    'FuncGui': {'param_unit': 'u'},
    'BoolGui': {},
    'TupleGui': {'min_val': -10,
                 'max_val': 100,
                 'step': 1,
                 'param_unit': 'Nm'},
    'ComboGui': {'options': {'a': 'A', 'b': 'B', 'c': 'C'},
                 'param_unit': 'g'},
    'ListGui': {'param_unit': 'mol'},
    'CheckListGui': {'options': ['lemon', 'pineapple', 'bananaaa'],
                     'param_unit': 'V'},
    'DictGui': {'param_unit': '°C'},
    'SliderGui': {'min_val': -10,
                  'max_val': 10,
                  'step': 0.01,
                  'param_unit': 'Hz'}
}


def test_int_gui(qtbot):
    kwargs = keyword_args['IntGui']
    gui = IntGui(parameters, 'IntGui', none_select=True, **kwargs)
    qtbot.addWidget(gui)

    assert gui.get_param() == parameters['IntGui']
    parameters['IntGui'] = 3
    gui.read_param()
    gui.set_param()
    assert gui.get_param() == 3
    gui.param_widget.setValue(5)
    assert parameters['IntGui'] == 5
    # more than max
    gui.param_widget.setValue(1000)
    assert parameters['IntGui'] == kwargs['max_val']
    # less than min
    gui.param_widget.setValue(-1000)
    assert parameters['IntGui'] == kwargs['min_val']
    # Uncheck for None as value
    gui.group_box.setChecked(False)
    assert parameters['IntGui'] is None


@pytest.mark.parametrize('gui_name', list(keyword_args.keys()))
def test_basic_param_guis(qtbot, gui_name):
    gui = getattr(parameter_widgets, gui_name)
    gui_kwargs = keyword_args[gui_name]
    gui_parameters = inspect.signature(gui)
    gui_instance = gui(parameters, gui_name, **gui_kwargs)
