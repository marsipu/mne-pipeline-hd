import sys
from ast import literal_eval

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QPushButton,
                             QSizePolicy, QSlider, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


class OneParam(QWidget):
    """
    General GUI for single Parameter-GUIs, not to be called directly
    """

    def __init__(self, project):
        """
        :param project: Project-Class called in main_win.py
        """
        super().__init__()
        self.project = project
        self.param_name = 'Standard'
        self.param_value = None
        self.param_unit = None
        self.param_widget = QWidget()

    def init_h_layout(self):
        self.layout = QHBoxLayout()
        self.layout.addWidget(QLabel(f'{self.param_name}: '))
        self.layout.addWidget(self.param_widget)
        self.setLayout(self.layout)

    def init_bt_layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel(f'{self.param_name}: '))
        self.layout.addWidget(self.param_widget)

        # Add Buttons to interact with list widget
        bt_layout = QHBoxLayout()
        add_bt = QPushButton('+')
        add_bt.clicked.connect(self.add_item)
        bt_layout.addWidget(add_bt)

        rm_bt = QPushButton('-')
        rm_bt.clicked.connect(self.remove_item)
        bt_layout.addWidget(rm_bt)

        self.layout.addLayout(bt_layout)
        self.setLayout(self.layout)

    def read_param(self):
        if self.param_name in self.project.parameters:
            self.param_value = self.project.parameters[self.param_name]
        else:
            pass

    def save_param(self):
        if self.param_name in self.project.parameters:
            self.project.parameters[self.param_name] = self.param_value
        else:
            self.project.parameters.update({self.param_name: self.param_value})


class IntGui(OneParam):
    """A GUI for Integer-Parameters"""

    def __init__(self, project, param_name, hint='', min_val=0, max_val=100, param_unit=None):
        super().__init__(project)
        self.param_name = param_name
        self.param_value = 1  # Default Value
        self.param_widget = QSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxValue = {max_val}')
        if param_unit is not None:
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


class FloatGui(OneParam):
    """A GUI for Float-Parameters"""

    def __init__(self, project, param_name, hint='', min_val=0., max_val=100.,
                 step=1., decimals=2, param_unit=None):
        super().__init__(project)
        self.param_name = param_name
        self.param_value = 1.
        self.param_widget = QDoubleSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setSingleStep(step)
        self.param_widget.setDecimals(decimals)
        self.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxVal = {max_val}')
        if param_unit is not None:
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


class StringGui(OneParam):
    """
    A GUI for String-Parameters

    Input-Mask: Define a string as in https://doc.qt.io/qt-5/qlineedit.html#inputMask-prop
    """

    def __init__(self, project, param_name, hint='', input_mask=None):
        super().__init__(project)
        self.param_name = param_name
        self.param_value = ''
        self.param_widget = QLineEdit()
        if input_mask is not None:
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


class FuncGui(OneParam):
    """A GUI for Parameters defined by small functions, e.g from numpy"""

    def __init__(self, project, param_name, hint=''):
        super().__init__(project)
        self.param_name = param_name
        self.param_value = ''
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
        groupbox = QGroupBox(self.param_name)
        sub_layout = QGridLayout()
        label1 = QLabel('Insert Function/Value here')
        label2 = QLabel('Output')
        sub_layout.addWidget(label1, 0, 0)
        sub_layout.addWidget(label2, 0, 1)
        sub_layout.addWidget(self.param_widget, 1, 0)
        sub_layout.addWidget(self.display_widget, 1, 1)
        groupbox.setLayout(sub_layout)

        layout.addWidget(groupbox)
        self.setLayout(layout)

    def set_param(self):
        self.param_widget.setText(self.param_value)
        self.display_widget.setText(self.param_value)

    def get_param(self):
        string_param = self.param_widget.text()
        try:
            self.param_value = eval(string_param)
            self.display_widget.setText(str(self.param_value))

        except (NameError, SyntaxError) as err:
            self.display_widget.setText(str(err))
            pass
        self.save_param()

        return self.param_value


class BoolGui(OneParam):
    """A GUI for Boolean-Parameters"""

    def __init__(self, project, param_name, hint=''):
        super().__init__(project)
        self.param_name = param_name
        self.param_value = False
        self.param_widget = QCheckBox()
        self.param_widget.setToolTip(hint)
        self.param_widget.toggled.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.init_radio_bt_layout()

    def init_radio_bt_layout(self):
        layout = QHBoxLayout()
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


class TupleGui(OneParam):
    """A GUI for Tuple-Parameters"""

    def __init__(self, project, param_name, hint='', min_val=-10., max_val=10.,
                 step=.1, decimals=2, param_unit=None):
        super().__init__(project)
        self.param_name = param_name
        self.param_value = (0, 1)
        self.param_widget1 = QDoubleSpinBox()
        self.param_widget1.setMinimum(min_val)
        self.param_widget1.setMaximum(max_val)
        self.param_widget1.setSingleStep(step)
        self.param_widget1.setDecimals(decimals)
        self.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxVal = {max_val}')
        if param_unit is not None:
            self.param_widget1.setSuffix(f' {param_unit}')
        self.param_widget1.valueChanged.connect(self.get_param)

        self.param_widget2 = QDoubleSpinBox()
        self.param_widget2.setMinimum(min_val)
        self.param_widget2.setMaximum(max_val)
        self.param_widget2.setSingleStep(step)
        self.param_widget2.setDecimals(decimals)
        self.setToolTip(f'{hint}\nMinValue = {min_val}\nMaxVal = {max_val}')
        if param_unit is not None:
            self.param_widget2.setSuffix(f' {param_unit}')
        self.param_widget2.valueChanged.connect(self.get_param)
        self.read_param()
        self.set_param()
        self.init_tuple_layout()

    def init_tuple_layout(self):
        layout = QGridLayout()
        label = QLabel(self.param_name)
        layout.addWidget(label, 0, 0, 1, 2)
        layout.addWidget(self.param_widget1, 1, 0)
        layout.addWidget(self.param_widget2, 1, 1)
        self.setLayout(layout)

    def set_param(self):
        self.param_widget1.setValue(self.param_value[0])
        self.param_widget2.setValue(self.param_value[1])

    def get_param(self):
        self.param_value = (self.param_widget1.value(), self.param_widget2.value())
        self.save_param()

        return self.param_value


class ListGui(OneParam):
    """A GUI for List-Parameters"""

    def __init__(self, project, param_name, hint=''):
        super().__init__(project)
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
        if len(self.param_value) > 0:
            for item in self.param_value:
                list_item = QListWidgetItem(str(item))
                list_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
                self.param_widget.addItem(list_item)

    def get_param(self):
        param_list = list()
        for idx in range(self.param_widget.count()):
            param_text = self.param_widget.item(idx).text()
            try:
                param_text = literal_eval(param_text)
            except ValueError:
                pass
            param_list.append(param_text)
        self.param_value = param_list
        self.save_param()

        return self.param_value

    def add_item(self):
        list_item = QListWidgetItem('<edit parameter>')
        list_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
        self.param_widget.addItem(list_item)

    def remove_item(self):
        row = self.param_widget.currentRow()
        if row is not None:
            self.param_widget.takeItem(row)


class DictGui(OneParam):
    """A GUI for Dictionary-Parameters"""

    def __init__(self, project, param_name, hint=''):
        super().__init__(project)
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
        self.param_widget.insertRow(row)
        key_item = QTableWidgetItem(key)
        key_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
        value_item = QTableWidgetItem(value)
        value_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
        self.param_widget.setItem(row, 0, key_item)
        self.param_widget.setItem(row, 1, value_item)
        self.param_widget.resizeColumnsToContents()

    def set_param(self):
        if len(self.param_value) > 0:
            for row, (key, value) in enumerate(self.param_value.items()):
                self.set_items(row, str(key), str(value))

    def get_param(self):
        param_dict = dict()
        for row in range(self.param_widget.rowCount()):
            row_item = self.param_widget.item(row, 0)
            value_item = self.param_widget.item(row, 1)
            if row_item is not None:
                try:
                    key = literal_eval(row_item.text())
                except (ValueError, SyntaxError):
                    key = row_item.text()
            else:
                key = None
            if value_item is not None:
                try:
                    value = literal_eval(value_item.text())
                except (ValueError, SyntaxError):
                    value = value_item.text()
            else:
                value = None
            param_dict.update({key: value})
        self.param_widget.resizeColumnsToContents()
        self.param_value = param_dict
        self.save_param()

        return self.param_value

    def add_item(self):
        row = self.param_widget.rowCount()
        self.set_items(row, '<edit_key>', '<edit_value>')
        self.param_widget.resizeColumnsToContents()

    def remove_item(self):
        row = self.param_widget.currentRow()
        if row is not None:
            self.param_widget.removeRow(row)
        self.get_param()


class SliderGui(OneParam):
    """A GUI to show a slider for Int/Float-Parameters"""

    def __init__(self, project, param_name, hint='', min_val=0., max_val=10., step=1.):
        super().__init__(project)
        self.param_name = param_name
        self.param_value = 1
        self.min_val = min_val
        self.max_val = max_val
        self.param_widget = QSlider()
        # Implement also compatibility for floating-point-numbers (not supported for x < 0.0001)
        self.decimal_count = max([str(value)[::-1].find('.') for value in (min_val, max_val, step)])
        if self.decimal_count != -1:
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
        self.display_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.display_widget.setAlignment(Qt.AlignRight)
        self.display_widget.editingFinished.connect(self.display_edited)

        self.read_param()
        self.set_param()
        self.init_slider_ui()

    def init_slider_ui(self):
        layout = QHBoxLayout()
        layout.addWidget(self.display_widget)
        layout.addWidget(self.param_widget)
        self.setLayout(layout)

    def display_edited(self):
        try:
            new_value = literal_eval(self.display_widget.text())
        except (ValueError, SyntaxError):
            new_value = ''
        if isinstance(new_value, int):
            self.param_value = new_value
            self.decimal_count = -1
            self.param_widget.setMinimum(self.min_val)
            self.param_widget.setMaximum(self.max_val)
            self.param_widget.setValue(self.param_value)
        elif isinstance(new_value, float):
            new_decimal_count = str(new_value)[::-1].find('.')
            if new_decimal_count != -1 and new_decimal_count != self.decimal_count:
                self.decimal_count = new_decimal_count
                self.param_widget.setMinimum(self.min_val * 10 ** self.decimal_count)
                self.param_widget.setMaximum(self.max_val * 10 ** self.decimal_count)
                self.param_value = new_value
                self.param_widget.setValue(new_value * 10 ** self.decimal_count)
        else:
            pass

    def set_param(self):
        self.param_widget.setValue(self.param_value)
        self.display_widget.setText(str(self.param_value))

    def get_param(self):
        new_value = self.param_widget.value()
        if self.decimal_count != -1:
            new_value /= 10 ** self.decimal_count
        self.param_value = new_value
        self.display_widget.setText(str(self.param_value))
        self.save_param()

        return self.param_value


class TestProject:
    def __init__(self):
        self.test_param = 1
        self.parameters = {'TestInt': 4,
                           'TestList': [1, 454.33, 'post_central-lh', 'raga', 5],
                           'TextDict': {'A': 'hubi', 'B': 58.144, 3: 'post_lh'},
                           'Fugi?': True}


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_layout = QHBoxLayout()
    main_win = QWidget()
    proj = TestProject()
    a = IntGui(proj, 'TestInt', 'Bugibugi', -4, 10, 's')
    b = ListGui(proj, 'TestList', 'Bugibugi')
    c = DictGui(proj, 'TextDict', 'Bugibugi')
    d = BoolGui(proj, 'Fugi?', 'Bugibugi')
    e = FloatGui(proj, 'TestFloat', 'Bugibugi', -18, +64, 0.4, 6, 'flurbo')
    f = StringGui(proj, 'TestString', 'Bugibugi', 'ppAAA.AA;_')
    g = SliderGui(proj, 'TestSlider', 'Bugibugi', -10, 10, 1)
    h = SliderGui(proj, 'TestSlider2', 'Bugigugi', 0, 20.25, 1.3)
    i = FuncGui(proj, 'TestFunc', 'Hugabuga')
    j = TupleGui(proj, 'Test_Tuple', 'Higiwigi', -10, 20, 1)
    main_layout.addWidget(a)
    main_layout.addWidget(b)
    main_layout.addWidget(c)
    main_layout.addWidget(d)
    main_layout.addWidget(e)
    main_layout.addWidget(f)
    main_layout.addWidget(g)
    main_layout.addWidget(h)
    main_layout.addWidget(i)
    main_layout.addWidget(j)
    main_win.setLayout(main_layout)
    main_win.show()
    app.exec_()

    print(proj.parameters)
