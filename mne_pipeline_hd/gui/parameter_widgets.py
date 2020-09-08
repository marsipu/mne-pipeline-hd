# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import sys
from ast import literal_eval
from decimal import Decimal
from functools import partial

import numpy as np
from PyQt5.QtCore import QSettings, QTimer, Qt
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit, QListWidget, QMainWindow, QPushButton, QScrollArea, QSizePolicy,
                             QSlider, QSpinBox, QVBoxLayout, QWidget)

from mne_pipeline_hd.gui.base_widgets import CheckList, EditDict, EditList


class Param(QWidget):
    """
    General GUI for single Parameter-GUIs, not to be called directly
    Inherited Clases should have "Gui" in their name to get identified correctly
    """

    def __init__(self, data, param_name, param_alias=None, default=None):
        """
        :param data: Project-Class called in main_window.py
        """
        super().__init__()
        self.data = data
        self.param_name = param_name
        if param_alias:
            self.param_alias = param_alias
        else:
            self.param_alias = self.param_name
        self.param_value = None
        self.default = default
        self.param_unit = None
        self.param_widget = QWidget()

    def init_h_layout(self):
        self.layout = QHBoxLayout()
        self.layout.addWidget(QLabel(f'{self.param_alias}: '))
        self.layout.addWidget(self.param_widget)
        self.setLayout(self.layout)

    def init_v_layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel(f'{self.param_alias}: '))
        self.layout.addWidget(self.param_widget)
        self.setLayout(self.layout)

    def read_param(self):
        # Make also usable by Main-Window-Settings
        if isinstance(self.data, dict):
            if self.param_name in self.data:
                self.param_value = self.data[self.param_name]
            else:
                self.param_value = self.default

        # Make also usable by QSettings
        elif isinstance(self.data, QSettings):
            if self.param_name in self.data.childKeys():
                value = self.data.value(self.param_name, defaultValue=self.default)
                if value is None:
                    value = self.default
                # Convert booleans, which turn into strings with QSettings
                elif value == "true":
                    value = True
                elif value == "false":
                    value = False
                self.param_value = value
            else:
                self.param_value = self.default

        # Main usage to get data from Parameters in Project stored in MainWindow
        elif isinstance(self.data, QMainWindow):
            if self.param_name in self.data.pr.parameters[self.data.pr.p_preset]:
                self.param_value = self.data.pr.parameters[self.data.pr.p_preset][self.param_name]
            else:
                self.param_value = self.default

    def save_param(self):
        if isinstance(self.data, dict):
            self.data[self.param_name] = self.param_value
        elif isinstance(self.data, QSettings):
            self.data.setValue(self.param_name, self.param_value)
        elif isinstance(self.data, QMainWindow):
            self.data.pr.parameters[self.data.pr.p_preset][self.param_name] = self.param_value


class IntGui(Param):
    """A GUI for Integer-Parameters"""

    def __init__(self, data, param_name, param_alias=None, hint=None, min_val=0, max_val=100,
                 special_value_text=None, param_unit=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_value = 1  # Default Value
        self.param_widget = QSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        if hint:
            self.param_widget.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxValue = {max_val}')
        else:
            self.param_widget.setToolTip(f'MinValue = {min_val}\nMaxValue = {max_val}')
        if special_value_text:
            self.param_widget.setSpecialValueText(special_value_text)
        if param_unit:
            self.param_widget.setSuffix(f' {param_unit}')
        self.param_widget.valueChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.save_param()
        self.init_h_layout()

    def set_param(self):
        self.param_widget.setValue(int(self.param_value))

    def get_param(self):
        self.param_value = self.param_widget.value()
        self.save_param()

        return self.param_value


class FloatGui(Param):
    """A GUI for Float-Parameters"""

    def __init__(self, data, param_name, param_alias=None, hint=None, min_val=-100., max_val=100.,
                 step=1., decimals=2, param_unit=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_value = 1.
        self.param_widget = QDoubleSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setSingleStep(step)
        self.param_widget.setDecimals(decimals)
        if hint:
            self.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxVal = {max_val}')
        else:
            self.setToolTip(f'MinValue = {min_val}\nMaxVal = {max_val}')
        if param_unit:
            self.param_widget.setSuffix(f' {param_unit}')
        self.param_widget.valueChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.save_param()
        self.init_h_layout()

    def set_param(self):
        self.param_widget.setValue(float(self.param_value))

    def get_param(self):
        self.param_value = self.param_widget.value()
        self.save_param()

        return self.param_value


class StringGui(Param):
    """
    A GUI for String-Parameters

    Input-Mask: Define a string as in https://doc.qt.io/qt-5/qlineedit.html#inputMask-prop
    """

    def __init__(self, data, param_name, param_alias=None, hint=None, input_mask=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_value = ''
        self.param_widget = QLineEdit()
        if input_mask:
            self.param_widget.setInputMask(input_mask)
        if hint:
            self.param_widget.setToolTip(hint)
        self.param_widget.textChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.save_param()
        self.init_h_layout()

    def set_param(self):
        self.param_widget.setText(self.param_value)

    def get_param(self):
        self.param_value = self.param_widget.text()
        self.save_param()

        return self.param_value


class FuncGui(Param):
    """A GUI for Parameters defined by small functions, e.g from numpy

    Notes
    -----
    Only works with Mainwindow.Project at the moment (not with dict or QSettings)
    """

    def __init__(self, data, param_name, param_alias=None, hint=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_alias = param_alias
        self.param_value = ''
        self.param_exp = ''
        self.param_widget = QLineEdit()
        if hint:
            self.param_widget.setToolTip(hint + '\n' +
                                         'Use of functions also allowed (from already imported modules + numpy as np)\n'
                                         'Be carefull as everything entered will be executed!')
        else:
            self.param_widget.setToolTip('Use of functions also allowed (from already imported modules + numpy as np)\n'
                                         'Be carefull as everything entered will be executed!')
        self.param_widget.editingFinished.connect(self.get_param)

        self.display_widget = QLabel()

        self.read_param()
        self.set_param()
        self.save_param()
        self.init_func_layout()

    def init_func_layout(self):
        layout = QHBoxLayout()
        if self.param_alias:
            groupbox = QGroupBox(self.param_alias)
        else:
            groupbox = QGroupBox(self.param_name)
        inner_layout = QGridLayout()
        label1 = QLabel('Insert Function/Value here')
        label2 = QLabel('Output')
        inner_layout.addWidget(label1, 0, 0)
        inner_layout.addWidget(label2, 0, 1)
        inner_layout.addWidget(self.param_widget, 1, 0)
        inner_layout.addWidget(self.display_widget, 1, 1)
        groupbox.setLayout(inner_layout)

        layout.addWidget(groupbox)
        self.setLayout(layout)

    def set_param(self):
        self.param_widget.setText(self.param_exp)
        self.display_widget.setText(str(self.param_value)[:20])

    def get_param(self):
        self.param_exp = self.param_widget.text()
        try:
            self.param_value = eval(self.param_exp, {'np': np})
            self.display_widget.setText(str(self.param_value)[:20])
        except (NameError, SyntaxError) as err:
            self.display_widget.setText(str(err)[:20])
            return None
        else:
            self.save_param()
            return self.param_value

    def read_param(self):
        if self.param_name in self.data.pr.parameters[self.data.pr.p_preset]:
            self.param_value = self.data.pr.parameters[self.data.pr.p_preset][self.param_name]
        if self.param_name + '_exp' in self.data.pr.parameters[self.data.pr.p_preset]:
            self.param_exp = self.data.pr.parameters[self.data.pr.p_preset][self.param_name + '_exp']

    def save_param(self):
        self.data.pr.parameters[self.data.pr.p_preset][self.param_name] = self.param_value
        self.data.pr.parameters[self.data.pr.p_preset][self.param_name + '_exp'] = self.param_exp


class BoolGui(Param):
    """A GUI for Boolean-Parameters"""

    def __init__(self, data, param_name, param_alias=None, hint=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_alias = param_alias
        self.param_value = 0
        self.param_widget = QCheckBox(self.param_alias)
        if hint:
            self.param_widget.setToolTip(hint)
        self.param_widget.toggled.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.save_param()
        self.init_radio_bt_layout()

    def init_radio_bt_layout(self):
        layout = QHBoxLayout()
        if self.param_alias:
            self.param_widget.setText(self.param_alias)
        else:
            self.param_widget.setText(self.param_name)
        layout.addWidget(self.param_widget)
        self.setLayout(layout)

    def set_param(self):
        if self.param_value:
            self.param_widget.setChecked(True)
        else:
            self.param_widget.setChecked(False)

    def get_param(self):
        if self.param_widget.isChecked():
            self.param_value = True
        else:
            self.param_value = False
        self.save_param()

        return self.param_value


class TupleGui(Param):
    """A GUI for Tuple-Parameters"""

    def __init__(self, data, param_name, param_alias=None, hint=None, min_val=-1000., max_val=1000.,
                 step=.1, decimals=2, param_unit=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_value = (0, 1)

        if hint:
            self.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxVal = {max_val}\nStep = {step}\nDecimals = {decimals}')
        else:
            self.setToolTip(f'MinValue = {min_val}\nMaxVal = {max_val}\nStep = {step}\nDecimals = {decimals}')

        self.label = QLabel(self.param_name)

        self.param_widget1 = QDoubleSpinBox()
        self.param_widget1.setMinimum(min_val)
        self.param_widget1.setMaximum(max_val)
        self.param_widget1.setSingleStep(step)
        self.param_widget1.setDecimals(decimals)
        if param_unit:
            self.param_widget1.setSuffix(f' {param_unit}')
        self.param_widget1.valueChanged.connect(self.get_param)

        self.param_widget2 = QDoubleSpinBox()
        self.param_widget2.setMinimum(min_val)
        self.param_widget2.setMaximum(max_val)
        self.param_widget2.setSingleStep(step)
        self.param_widget2.setDecimals(decimals)
        if param_unit:
            self.param_widget2.setSuffix(f' {param_unit}')
        self.param_widget2.valueChanged.connect(self.get_param)

        self.read_param()
        self.set_param()
        self.save_param()
        self.init_tuple_layout()

    def init_tuple_layout(self):
        layout = QGridLayout()
        layout.addWidget(self.label, 0, 0, 1, 2)
        layout.addWidget(self.param_widget1, 1, 0)
        layout.addWidget(self.param_widget2, 1, 1)
        self.setLayout(layout)

    def set_param(self):
        # Signal valueChanged is already emitted after first setValue,
        # which leads to second param_value being 0 without being preserved in self.loaded_value
        self.loaded_value = self.param_value
        self.param_widget1.setValue(self.loaded_value[0])
        self.param_widget2.setValue(self.loaded_value[1])

    def get_param(self):
        # Tuple can't be differenciated from list by json-Encoder,
        # so this key makes it possible (pipeline_utils.parameters_json_hook)
        self.param_value = (self.param_widget1.value(), self.param_widget2.value())
        self.save_param()

        return self.param_value


class CheckTupleGui(TupleGui):
    def __init__(self, data, param_name, param_alias=None, hint=None, min_val=-1000., max_val=1000.,
                 step=.1, decimals=2, param_unit=None, unchecked_value=None, default=None):
        self.param_name = param_name
        self.unchecked_value = unchecked_value
        self.param_chkbt = QCheckBox(self.param_name)
        self.param_chkbt.stateChanged.connect(self.param_checked)
        super().__init__(data, param_name, param_alias, hint, min_val, max_val,
                         step, decimals, param_unit, default)

    def init_tuple_layout(self):
        layout = QGridLayout()
        layout.addWidget(self.param_chkbt, 0, 0, 1, 2)
        layout.addWidget(self.param_widget1, 1, 0)
        layout.addWidget(self.param_widget2, 1, 1)
        self.setLayout(layout)

    def set_param(self):

        self.loaded_value = self.param_value

        if self.loaded_value is None:
            self.param_widget1.setEnabled(False)
            self.param_widget2.setEnabled(False)
        else:
            self.param_chkbt.setChecked(True)
            self.param_widget1.setValue(self.loaded_value[0])
            self.param_widget2.setValue(self.loaded_value[1])

    def param_checked(self, state):
        if state:
            self.param_widget1.setEnabled(True)
            self.param_widget2.setEnabled(True)
            self.get_param()
        else:
            self.param_widget1.setEnabled(False)
            self.param_widget2.setEnabled(False)
            self.param_value = self.unchecked_value
            self.save_param()


class ComboGui(Param):
    """A GUI for a Parameter with limited options"""

    def __init__(self, data, param_name, options, param_alias=None, hint=None, options_mapping=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_value = None
        self.options = options
        self.options_mapping = options_mapping or {}
        self.param_widget = QComboBox()
        self.param_widget.activated.connect(self.get_param)
        if hint:
            self.param_widget.setToolTip(hint)
        for option in self.options:
            if option in self.options_mapping:
                self.param_widget.addItem(self.options_mapping[option])
            else:
                self.param_widget.addItem(option)
        self.read_param()
        self.set_param()
        self.save_param()
        self.init_h_layout()

    def set_param(self):
        if self.param_value in self.options:
            if self.param_value in self.options_mapping:
                self.param_widget.setCurrentText(self.options_mapping[self.param_value])
            else:
                self.param_widget.setCurrentText(self.param_value)

    def get_param(self):
        pre_value = self.param_widget.currentText()
        # Get key from value
        if pre_value in self.options_mapping.values():
            self.param_value = [it for it in self.options_mapping.items() if pre_value in it][0][0]
        else:
            self.param_value = pre_value
        self.save_param()

        return self.param_value


class ListDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw

        self.init_layout()
        self.open()

    def init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(EditList(self.paramw.param_value))
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.paramw.set_param()
        event.accept()


class ListGui(Param):
    """A GUI for List-Parameters"""

    def __init__(self, data, param_name, param_alias=None, hint=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_value = list()
        self.name_label = QLabel(f'{self.param_alias}:')
        self.value_label = QLabel('')
        if hint:
            self.name_label.setToolTip(hint)

        self.read_param()
        self.set_param()
        self.save_param()

        self.init_layout()

    def init_layout(self):
        layout = QGridLayout()
        layout.addWidget(self.name_label, 0, 0)

        edit_bt = QPushButton('Edit')
        edit_bt.clicked.connect(partial(ListDialog, self))
        layout.addWidget(edit_bt, 0, 1)

        layout.addWidget(self.value_label, 1, 0, 1, 2)

        self.setLayout(layout)

    def set_param(self):
        val_str = str(self.param_value)
        if len(val_str) > 30:
            self.value_label.setText(f'{val_str[:30]} ...')
        else:
            self.value_label.setText(val_str)

    def get_param(self):
        self.save_param()

        return self.param_value


class CheckListDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw
        self.data = list(paramw.param_value.keys())
        self.checked = [key for key in paramw.param_value.keys() if paramw.param_value[key]]

        self.init_layout()
        self.open()

    def init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(CheckList(self.data, self.checked))

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def closeEvent(self, event):
        value_dict = dict()
        for key in self.data:
            if key in self.checked:
                value_dict[key] = 1
            else:
                value_dict[key] = 0
        self.paramw.param_value = value_dict
        self.paramw.set_param()
        event.accept()


class CheckListGui(Param):
    """A GUI for List-Parameters"""

    def __init__(self, data, param_name, param_alias=None, hint=None, options=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.options_mapping = options or {}
        self.param_value = dict()

        self.name_label = QLabel(f'{self.param_alias}:')
        if hint:
            self.name_label.setToolTip(hint)
        self.value_label = QLabel('')

        self.read_param()
        self.set_param()
        self.save_param()

        self.init_layout()

    def init_layout(self):
        layout = QGridLayout()
        layout.addWidget(self.name_label, 0, 0)

        edit_bt = QPushButton('Edit')
        edit_bt.clicked.connect(partial(CheckListDialog, self))
        layout.addWidget(edit_bt, 0, 1)

        layout.addWidget(self.value_label, 1, 0, 1, 2)

        self.setLayout(layout)

    def set_param(self):
        val_str = str(self.param_value)
        if len(val_str) > 30:
            self.value_label.setText(f'{val_str[:30]} ...')
        else:
            self.value_label.setText(val_str)

    def get_param(self):
        self.save_param()

        return self.param_value


class DictDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw

        self.init_layout()
        self.open()

    def init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(EditDict(self.paramw.param_value))
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.paramw.set_param()
        event.accept()


class DictGui(Param):
    """A GUI for Dictionary-Parameters"""

    def __init__(self, data, param_name, param_alias=None, hint=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_value = dict()

        self.name_label = QLabel(f'{self.param_alias}:')
        if hint:
            self.name_label.setToolTip(hint)
        self.value_label = QLabel('')

        self.read_param()
        self.set_param()
        self.save_param()

        self.init_layout()

    def init_layout(self):
        layout = QGridLayout()
        layout.addWidget(self.name_label, 0, 0)

        edit_bt = QPushButton('Edit')
        edit_bt.clicked.connect(partial(DictDialog, self))
        layout.addWidget(edit_bt, 0, 1)

        layout.addWidget(self.value_label, 1, 0, 1, 2)

        self.setLayout(layout)

    def set_param(self):
        val_str = str(self.param_value)
        if len(val_str) > 30:
            self.value_label.setText(f'{val_str[:30]} ...')
        else:
            self.value_label.setText(val_str)

    def get_param(self):
        self.save_param()

        return self.param_value


# Todo: None als Parameter (Special Parameter)
class SliderGui(Param):
    """A GUI to show a slider for Int/Float-Parameters"""

    def __init__(self, data, param_name, param_alias=None, hint=None,
                 min_val=0, max_val=100, step=1, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_alias = param_alias
        self.param_value = 1
        self.min_val = min_val
        self.max_val = max_val
        self.param_widget = QSlider()
        self.decimal_count = max([abs(Decimal(str(value)).as_tuple().exponent) for value in (min_val, max_val, step)])
        if self.decimal_count > 0:
            self.param_widget.setMinimum(self.min_val * 10 ** self.decimal_count)
            self.param_widget.setMaximum(self.max_val * 10 ** self.decimal_count)
        else:
            self.param_widget.setMinimum(self.min_val)
            self.param_widget.setMaximum(self.max_val)
        self.param_widget.setSingleStep(step)
        self.param_widget.setOrientation(Qt.Horizontal)
        self.param_widget.setTracking(True)
        if hint:
            self.param_widget.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxValue = {max_val}\nStep = {step}')
        else:
            self.param_widget.setToolTip(f'MinValue = {min_val}\nMaxValue = {max_val}\nStep = {step}')
        self.param_widget.valueChanged.connect(self.get_param)

        self.display_widget = QLineEdit()
        self.display_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.display_widget.setAlignment(Qt.AlignLeft)
        self.display_widget.editingFinished.connect(self.display_edited)

        self.read_param()
        self.set_param()
        self.save_param()
        self.init_slider_ui()

    def init_slider_ui(self):
        layout = QGridLayout()
        if self.param_alias:
            label = QLabel(self.param_alias + ': ')
        else:
            label = QLabel(self.param_name + ': ')
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.display_widget, 0, 1)
        layout.addWidget(self.param_widget, 1, 0, 1, 2)
        self.setLayout(layout)

    def display_edited(self):
        try:
            new_value = literal_eval(self.display_widget.text())
        except (ValueError, SyntaxError):
            new_value = ''
        if isinstance(new_value, int):
            self.param_value = new_value
            self.decimal_count = 0
            self.param_widget.setMinimum(self.min_val)
            self.param_widget.setMaximum(self.max_val)
            self.param_widget.setValue(self.param_value)
        elif isinstance(new_value, float):
            new_decimal_count = abs(Decimal(str(new_value)).as_tuple().exponent)
            if new_decimal_count > 0 and new_decimal_count != self.decimal_count:
                self.decimal_count = new_decimal_count
                self.param_widget.setMinimum(self.min_val * 10 ** self.decimal_count)
                self.param_widget.setMaximum(self.max_val * 10 ** self.decimal_count)
            self.param_value = new_value
            self.param_widget.setValue(int(new_value * 10 ** self.decimal_count))

    def set_param(self):
        if self.decimal_count > 0:
            self.param_widget.setValue(int(self.param_value * 10 ** self.decimal_count))
        else:
            self.param_widget.setValue(self.param_value)
        self.display_widget.setText(str(self.param_value))

    def get_param(self):
        new_value = self.param_widget.value()
        if self.decimal_count > 0:
            new_value /= 10 ** self.decimal_count
        self.param_value = new_value
        self.display_widget.setText(str(self.param_value))
        self.save_param()

        return self.param_value


# Todo: Label-GUI
class LabelGui(Param):
    """A GUI to select Labels depending on parcellation"""

    def __init__(self, data, param_name, param_alias=None, hint=None, default=None):
        super().__init__(data, param_name, param_alias, default)
        self.param_name = param_name
        self.param_value = []
        self.param_widget = QListWidget()
        self.param_widget.itemChanged.connect(self.get_param)
        if hint:
            self.setToolTip(hint)
        self.read_param()
        self.set_param()
        self.save_param()
        self.init_label_ui()

    def init_label_ui(self):
        start_bt = QPushButton('Select Labels')
        self.layout.addWidget(start_bt)

    def set_param(self):
        pass

    def get_param(self):
        pass
        self.save_param()

        return self.param_value


class TestProject:
    def __init__(self):
        self.test_param = 1
        self.p_preset = 'Default'
        self.parameters = {'Default': {'TestInt': 4,
                                       'TestList': [1, 454.33, 'post_central-lh', 'raga', 5],
                                       'TextDict': {'A': 'hubi', 'B': 58.144, 3: 'post_lh'},
                                       'Fugi?': True,
                                       'TestFloat': 5.3,
                                       'TestString': 'Havona',
                                       'TestSlider': 5,
                                       'TestSlider2': 4.5,
                                       'TestFunc': '2**14',
                                       'TestTuple': (45, 6.5),
                                       'TestCombo': 'a',
                                       'TestCheckList': {'a': 0, 'b': 1, 'c': 1}}}


if __name__ == '__main__':
    app = QApplication(sys.argv)
    scroll_area = QScrollArea()
    sub_layout = QGridLayout()
    main_win = QWidget()
    proj = TestProject()
    a = IntGui(proj, 'TestInt', min_val=-4, max_val=10)
    b = ListGui(proj, 'TestList')
    c = DictGui(proj, 'TextDict')
    d = BoolGui(proj, 'Huba?')
    e = FloatGui(proj, 'TestFloat', min_val=-18, max_val=+64, step=0.4, decimals=6, param_unit='flurbo')
    f = StringGui(proj, 'TestString', input_mask='ppAAA.AA;_')
    g = SliderGui(proj, 'TestSlider', min_val=-10, max_val=10, step=1)
    h = SliderGui(proj, 'TestSlider2', min_val=0, max_val=20.25, step=1.3)
    i = FuncGui(proj, 'TestFunc')
    j = TupleGui(proj, 'TestTuple', min_val=-10, max_val=20, step=1, decimals=3)
    k = ComboGui(proj, 'TestCombo', options=['a', 'b', 'c'],
                 options_mapping={'a': 'hungiwungi', 'b': 'zulu32', 'c': 'bananaaa'})
    l = CheckListGui(proj, 'TestCheckList', options={'a': 'hungiwungi', 'b': 'zulu32', 'c': 'bananaaa'})
    sub_layout.addWidget(a, 0, 0)
    sub_layout.addWidget(b, 0, 1)
    sub_layout.addWidget(c, 0, 2)
    sub_layout.addWidget(d, 0, 3)
    sub_layout.addWidget(e, 0, 4)
    sub_layout.addWidget(f, 1, 0)
    sub_layout.addWidget(g, 1, 1)
    sub_layout.addWidget(h, 1, 2)
    sub_layout.addWidget(i, 1, 3)
    sub_layout.addWidget(j, 1, 4)
    sub_layout.addWidget(k, 2, 0)
    sub_layout.addWidget(l, 2, 1)
    main_win.setLayout(sub_layout)
    scroll_area.setWidget(main_win)
    scroll_area.show()

    # Command-Line interrupt with Ctrl+C possible, easier debugging
    timer = QTimer()
    timer.timeout.connect(lambda: proj)
    timer.start(500)

    sys.exit(app.exec())
