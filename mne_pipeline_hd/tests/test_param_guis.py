import sys
import traceback
from ast import literal_eval

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout,
                             QHBoxLayout, QComboBox, QLineEdit,
                             QPushButton, QApplication, QDialog)

from ..gui import parameter_widgets
from ..gui.base_widgets import SimpleDict


class ParamGuiTest(QWidget):
    def __init__(self):
        super().__init__()
        self.parameters = {'IntGui': None,
                      'FloatGui': 5.3,
                      'StringGui': 'Havona',
                      'MultiTypeGui': 42,
                      'FuncGui': 5000,
                      'BoolGui': True,
                      'TupleGui': (45, 6),
                      'ComboGui': 'a',
                      'ListGui': [1, 454.33, 'post_central-lh', 'raga', 5],
                      'CheckListGui': ['bananaaa'],
                      'DictGui': {'A': 'hubi', 'B': 58.144, 3: 'post_lh'},
                      'SliderGui': 5}

        self.keyword_args = {
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

        self.gui_dict = dict()

        self.init_ui()

    def init_ui(self):
        test_layout = QVBoxLayout()
        grid_layout = QGridLayout()
        max_cols = 4
        set_none_select = True
        set_groupbox_layout = True
        set_param_alias = False

        for idx, gui_nm in enumerate(self.keyword_args):
            kw_args = self.keyword_args[gui_nm]
            kw_args['none_select'] = set_none_select
            kw_args['groupbox_layout'] = set_groupbox_layout
            if set_param_alias:
                kw_args['param_alias'] = gui_nm + '-alias'
            kw_args['description'] = gui_nm + '-description'
            gui = getattr(parameter_widgets, gui_nm)(self.parameters, gui_nm, **kw_args)
            grid_layout.addWidget(gui, idx // max_cols, idx % max_cols)
            self.gui_dict[gui_nm] = gui

        test_layout.addLayout(grid_layout)

        set_layout = QHBoxLayout()
        self.gui_cmbx = QComboBox()
        self.gui_cmbx.addItems(self.gui_dict.keys())
        set_layout.addWidget(self.gui_cmbx)

        self.set_le = QLineEdit()
        set_layout.addWidget(self.set_le)

        set_bt = QPushButton('Set')
        set_bt.clicked.connect(self.set_param)
        set_layout.addWidget(set_bt)

        show_bt = QPushButton('Show Parameters')
        show_bt.clicked.connect(self.show_parameters)
        set_layout.addWidget(show_bt)

        test_layout.addLayout(set_layout)

        self.setLayout(test_layout)

    def set_param(self):
        try:
            current_gui = self.gui_cmbx.currentText()
            try:
                value = literal_eval(self.set_le.text())
            except (SyntaxError, ValueError):
                value = self.set_le.text()
            self.parameters[current_gui] = value
            p_gui = self.gui_dict[current_gui]
            p_gui.read_param()
            p_gui.set_param()
        except:
            print(traceback.format_exc())

    def show_parameters(self):
        dlg = QDialog(self)
        layout = QVBoxLayout()
        layout.addWidget(SimpleDict(self.parameters))
        dlg.setLayout(layout)
        dlg.open()


def test_param_guis():
    app = QApplication(sys.argv)
    test_widget = ParamGuiTest()
    test_widget.show()

    sys.exit(app.exec())
