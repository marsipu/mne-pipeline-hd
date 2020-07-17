# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import sys
from ast import literal_eval
import numpy as np
from decimal import Decimal

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel,
                             QLineEdit, QListView, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy,
                             QSlider, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


class Param(QWidget):
    """
    General GUI for single Parameter-GUIs, not to be called directly
    Inherited Clases should have "Gui" in their name to get identified correctly
    """

    def __init__(self, project, param_name, param_alias):
        """
        :param project: Project-Class called in main_window.py
        """
        super().__init__()
        self.pr = project
        self.param_name = param_name
        self.param_alias = param_alias
        self.param_value = None
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

    def init_bt_layout(self):
        self.layout = QGridLayout()
        self.layout.addWidget(QLabel(f'{self.param_alias}: '), 0, 0, 1, 2)
        self.layout.addWidget(self.param_widget, 1, 0)

        # Add Buttons to interact with list widget
        bt_layout = QVBoxLayout()
        add_bt = QPushButton('+')
        add_bt.clicked.connect(self.add_item)
        bt_layout.addWidget(add_bt)

        rm_bt = QPushButton('-')
        rm_bt.clicked.connect(self.remove_item)
        bt_layout.addWidget(rm_bt)

        self.layout.addLayout(bt_layout, 1, 1)
        self.setLayout(self.layout)

    def read_param(self):
        # Make also usable by QSettings
        if isinstance(self.pr, QSettings):
            if self.param_name in self.pr.childKeys():
                self.param_value = self.pr.value(self.param_name)
        elif self.param_name in self.pr.parameters[self.pr.p_preset]:
            self.param_value = self.pr.parameters[self.pr.p_preset][self.param_name]

    def save_param(self):
        if isinstance(self.pr, QSettings):
            self.pr.setValue(self.param_name, self.param_value)
        else:
            self.pr.parameters[self.pr.p_preset][self.param_name] = self.param_value


class IntGui(Param):
    """A GUI for Integer-Parameters"""

    def __init__(self, project, param_name, param_alias, hint, min_val=0, max_val=100, special_value_text=None,
                 param_unit=None):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_value = 1  # Default Value
        self.param_widget = QSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxValue = {max_val}')
        if special_value_text:
            self.param_widget.setSpecialValueText(special_value_text)
        if param_unit:
            self.param_widget.setSuffix(f' {param_unit}')
        self.param_widget.valueChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.init_h_layout()

    def set_param(self):
        self.param_widget.setValue(self.param_value)

    def get_param(self):
        self.param_value = self.param_widget.value()
        self.save_param()

        return self.param_value


class FloatGui(Param):
    """A GUI for Float-Parameters"""

    def __init__(self, project, param_name, param_alias, hint, min_val=0., max_val=100.,
                 step=1., decimals=2, param_unit=None):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_value = 1.
        self.param_widget = QDoubleSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setSingleStep(step)
        self.param_widget.setDecimals(decimals)
        self.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxVal = {max_val}')
        if param_unit:
            self.param_widget.setSuffix(f' {param_unit}')
        self.param_widget.valueChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
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

    def __init__(self, project, param_name, param_alias, hint, input_mask=None):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_value = ''
        self.param_widget = QLineEdit()
        if input_mask:
            self.param_widget.setInputMask(input_mask)
        self.param_widget.setToolTip(hint)
        self.param_widget.textChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.init_h_layout()

    def set_param(self):
        self.param_widget.setText(self.param_value)

    def get_param(self):
        self.param_value = self.param_widget.text()
        self.save_param()

        return self.param_value


class FuncGui(Param):
    """A GUI for Parameters defined by small functions, e.g from numpy"""

    def __init__(self, project, param_name, param_alias, hint):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_alias = param_alias
        self.param_value = ''
        self.param_exp = ''
        self.param_widget = QLineEdit()
        self.param_widget.setToolTip(hint + '\n' +
                                     'Use of functions also allowed (from already imported modules)\n'
                                     'Be carefull as everything entered will be executed!')
        self.param_widget.editingFinished.connect(self.get_param)

        self.display_widget = QLabel()

        self.read_param()
        self.set_param()
        self.init_func_layout()

    def init_func_layout(self):
        layout = QHBoxLayout()
        groupbox = QGroupBox(self.param_alias)
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
        self.display_widget.setText(str(self.param_value))

    def get_param(self):
        self.param_exp = self.param_widget.text()
        try:
            self.param_value = eval(self.param_exp, {'np': np})
            self.display_widget.setText(str(self.param_value))
        except (NameError, SyntaxError) as err:
            self.display_widget.setText(str(err))
            return None
        else:
            self.save_param()
            return self.param_value

    def read_param(self):
        if self.param_name in self.pr.parameters[self.pr.p_preset]:
            self.param_value = self.pr.parameters[self.pr.p_preset][self.param_name]
        if self.param_name + '_exp' in self.pr.parameters[self.pr.p_preset]:
            self.param_exp = self.pr.parameters[self.pr.p_preset][self.param_name + '_exp']

    def save_param(self):
        self.pr.parameters[self.pr.p_preset][self.param_name] = self.param_value
        self.pr.parameters[self.pr.p_preset][self.param_name + '_exp'] = self.param_exp


class BoolGui(Param):
    """A GUI for Boolean-Parameters"""

    def __init__(self, project, param_name, param_alias, hint):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_alias = param_alias
        self.param_value = False
        self.param_widget = QCheckBox(self.param_alias)
        self.param_widget.setToolTip(hint)
        self.param_widget.toggled.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.init_radio_bt_layout()

    def init_radio_bt_layout(self):
        layout = QHBoxLayout()
        self.param_widget.setText(self.param_alias)
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

    def __init__(self, project, param_name, param_alias, hint, min_val=-1000., max_val=1000.,
                 step=.1, decimals=2, param_unit=None):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_value = (0, 1)

        self.label = QLabel(self.param_name)

        self.param_widget1 = QDoubleSpinBox()
        self.param_widget1.setMinimum(min_val)
        self.param_widget1.setMaximum(max_val)
        self.param_widget1.setSingleStep(step)
        self.param_widget1.setDecimals(decimals)
        self.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxVal = {max_val}')
        if param_unit:
            self.param_widget1.setSuffix(f' {param_unit}')
        self.param_widget1.valueChanged.connect(self.get_param)

        self.param_widget2 = QDoubleSpinBox()
        self.param_widget2.setMinimum(min_val)
        self.param_widget2.setMaximum(max_val)
        self.param_widget2.setSingleStep(step)
        self.param_widget2.setDecimals(decimals)
        self.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxVal = {max_val}')
        if param_unit:
            self.param_widget2.setSuffix(f' {param_unit}')
        self.param_widget2.valueChanged.connect(self.get_param)

        self.read_param()
        self.set_param()
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
        self.param_value = (self.param_widget1.value(), self.param_widget2.value())
        self.save_param()

        return self.param_value


class CheckTupleGui(TupleGui):
    def __init__(self, project, param_name, param_alias, hint, min_val=-1000., max_val=1000.,
                 step=.1, decimals=2, param_unit=None, unchecked_value=None):
        self.param_name = param_name
        self.unchecked_value = unchecked_value
        self.param_chkbt = QCheckBox(self.param_name)
        self.param_chkbt.stateChanged.connect(self.param_checked)
        super().__init__(project, param_name, param_alias, hint, min_val, max_val,
                         step, decimals, param_unit)

    def init_tuple_layout(self):
        layout = QGridLayout()
        layout.addWidget(self.param_chkbt, 0, 0, 1, 2)
        layout.addWidget(self.param_widget1, 1, 0)
        layout.addWidget(self.param_widget2, 1, 1)
        self.setLayout(layout)

    def set_param(self):
        if self.param_value is None:
            self.param_widget1.setEnabled(False)
            self.param_widget2.setEnabled(False)
        else:
            self.loaded_value = self.param_value
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

    def __init__(self, project, param_name, param_alias, hint, options, options_mapping=None):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_value = None
        self.options = options
        self.options_mapping = options_mapping or {}
        self.param_widget = QComboBox()
        self.param_widget.activated.connect(self.get_param)
        self.param_widget.setToolTip(hint)
        for option in self.options:
            if option in self.options_mapping:
                self.param_widget.addItem(self.options_mapping[option])
            else:
                self.param_widget.addItem(option)
        self.read_param()
        self.set_param()
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


class ListGui(Param):
    """A GUI for List-Parameters"""

    def __init__(self, project, param_name, param_alias, hint):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_value = list()
        self.param_widget = QListWidget()
        self.param_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.param_widget.setResizeMode(QListView.Adjust)
        self.param_widget.setToolTip(hint)
        self.param_widget.itemChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.init_bt_layout()

    def set_param(self):
        self.param_widget.clear()
        if len(self.param_value) > 0:
            for item in self.param_value:
                list_item = QListWidgetItem(str(item))
                list_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
                self.param_widget.addItem(list_item)
        # Todo: Model/View and Adjustment of Layout to content
        # self.param_widget.setMaximumWidth(self.param_widget.sizeHintForColumn(0))
        # self.param_widget.setMaximumHeight(self.param_widget.sizeHintForRow(0) * self.param_widget.count())

    def get_param(self):
        param_list = list()
        for idx in range(self.param_widget.count()):
            param_text = self.param_widget.item(idx).text()
            try:
                param_text = literal_eval(param_text)
            except (SyntaxError, ValueError):
                pass
            param_list.append(param_text)
        self.param_value = param_list
        self.save_param()

        return self.param_value

    def add_item(self):
        list_item = QListWidgetItem('_None_')
        list_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
        self.param_widget.addItem(list_item)
        self.get_param()

    def remove_item(self):
        row = self.param_widget.currentRow()
        if row is not None:
            self.param_widget.takeItem(row)
        self.get_param()


class CheckListGui(Param):
    """A GUI for List-Parameters"""

    def __init__(self, project, param_name, param_alias, hint, options_mapping=None):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.options_mapping = options_mapping or {}
        self.param_value = dict()
        self.param_widget = QListWidget()
        self.param_widget.setToolTip(hint)
        self.param_widget.itemChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.init_v_layout()

    def set_param(self):
        self.param_widget.clear()
        if len(self.param_value) > 0:
            for name in self.param_value:
                if name in self.options_mapping:
                    list_item = QListWidgetItem(str(self.options_mapping[name]))
                else:
                    list_item = QListWidgetItem(str(name))
                list_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                if self.param_value[name]:
                    list_item.setCheckState(Qt.Checked)
                else:
                    list_item.setCheckState(Qt.Unchecked)
                self.param_widget.addItem(list_item)

    def get_param(self):
        param_dict = {}
        for idx in range(self.param_widget.count()):
            item = self.param_widget.item(idx)
            if item.text() in self.options_mapping.values():
                # Get Dict-Key
                param_text = [it for it in self.options_mapping.items() if item.text() in it][0][0]
            else:
                param_text = item.text()

            if item.checkState() == Qt.Checked:
                param_dict.update({param_text: 1})
            else:
                param_dict.update({param_text: 0})
        self.param_value = param_dict
        self.save_param()

        return self.param_value


class DictGui(Param):
    """A GUI for Dictionary-Parameters"""

    def __init__(self, project, param_name, param_alias, hint):
        super().__init__(project, param_name, param_alias)
        self.param_name = param_name
        self.param_value = dict()
        self.param_widget = QTableWidget(0, 2)
        self.param_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.param_widget.setToolTip(hint)
        self.param_widget.itemChanged.connect(self.get_param)
        self.param_widget.setHorizontalHeaderLabels(['key', 'value'])
        self.read_param()
        self.set_param()
        self.init_bt_layout()

    def set_items(self, row, key, value):
        key_item = QTableWidgetItem(key)
        key_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
        value_item = QTableWidgetItem(value)
        value_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
        self.param_widget.setItem(row, 0, key_item)
        self.param_widget.setItem(row, 1, value_item)
        self.param_widget.resizeColumnsToContents()

    def set_param(self):
        self.param_widget.clear()
        if len(self.param_value) > 0:
            self.param_widget.setRowCount(len(self.param_value))
            for row, (key, value) in enumerate(self.param_value.items()):
                self.set_items(row, str(key), str(value))

    def get_param(self):
        param_dict = dict()
        for row in range(self.param_widget.rowCount()):
            row_item = self.param_widget.item(row, 0)
            value_item = self.param_widget.item(row, 1)
            if row_item and value_item:
                try:
                    key = literal_eval(row_item.text())
                except (ValueError, SyntaxError):
                    key = row_item.text()
                try:
                    value = literal_eval(value_item.text())
                except (ValueError, SyntaxError):
                    value = value_item.text()
                param_dict.update({key: value})
        self.param_widget.resizeColumnsToContents()
        self.param_value = param_dict
        self.save_param()

        return self.param_value

    def add_item(self):
        row = self.param_widget.rowCount()
        self.param_widget.insertRow(row)
        self.set_items(row, '_None_key_', '_None_value_')
        self.param_widget.resizeColumnsToContents()
        self.get_param()

    def remove_item(self):
        row = self.param_widget.currentRow()
        if row is not None:
            self.param_widget.removeRow(row)
        self.get_param()


# Todo: None als Parameter (Special Parameter)
class SliderGui(Param):
    """A GUI to show a slider for Int/Float-Parameters"""

    def __init__(self, project, param_name, param_alias, hint, min_val=0., max_val=100., step=1.):
        super().__init__(project, param_name, param_alias)
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
        self.param_widget.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxValue = {max_val}\nStep = {step}')
        self.param_widget.valueChanged.connect(self.get_param)

        self.display_widget = QLineEdit()
        self.display_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.display_widget.setAlignment(Qt.AlignLeft)
        self.display_widget.editingFinished.connect(self.display_edited)

        self.read_param()
        self.set_param()
        self.init_slider_ui()

    def init_slider_ui(self):
        layout = QGridLayout()
        label = QLabel(self.param_alias + ': ')
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
                self.param_widget.setValue(new_value * 10 ** self.decimal_count)
        else:
            pass

    def set_param(self):
        if self.decimal_count > 0:
            self.param_widget.setValue(self.param_value * 10 ** self.decimal_count)
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
                                       'TestSlide2': 4.5,
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
    a = IntGui(proj, 'TestInt', 'TestInt', 'Bugibugi', -4, 10, 's')
    b = ListGui(proj, 'TestList', 'TestList', 'Bugibugi')
    c = DictGui(proj, 'TextDict', 'TextDict', 'Bugibugi')
    d = BoolGui(proj, 'Fugi?', 'Fugi?', 'Bugibugi')
    e = FloatGui(proj, 'TestFloat', 'TestFloat', 'Bugibugi', -18, +64, 0.4, 6, 'flurbo')
    f = StringGui(proj, 'TestString', 'TestString', 'Bugibugi', 'ppAAA.AA;_')
    g = SliderGui(proj, 'TestSlider', 'TestSlider', 'Bugibugi', -10, 10, 1)
    h = SliderGui(proj, 'TestSlider2', 'TestSlider2', 'Bugigugi', 0, 20.25, 1.3)
    i = FuncGui(proj, 'TestFunc', 'TestFunc', 'Hugabuga')
    j = TupleGui(proj, 'TestTuple', 'Test_Tuple', 'Higiwigi', -10, 20, 1)
    k = ComboGui(proj, 'TestCombo', 'TestCombo', 'Higiwigi', options=['a', 'b', 'c'],
                 options_mapping={'a': 'hungiwungi', 'b': 'zulu32', 'c': 'bananaaa'})
    l = CheckListGui(proj, 'TestCheckList', 'TestCheckList', 'Higiwigi',
                     options_mapping={'a': 'hungiwungi', 'b': 'zulu32', 'c': 'bananaaa'})
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
    app.exec_()

    print(proj.parameters)
