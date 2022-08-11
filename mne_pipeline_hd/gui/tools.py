# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""

from functools import partial

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QComboBox, QDialog, QGridLayout,
                             QHBoxLayout, QPushButton,
                             QSizePolicy, QVBoxLayout)

from mne_pipeline_hd.gui.base_widgets import CheckList
from mne_pipeline_hd.gui.gui_utils import (CodeEditor, MainConsoleWidget,
                                           WorkerDialog, get_exception_tuple,
                                           set_ratio_geometry)
from mne_pipeline_hd.pipeline.loading import MEEG
from mne_pipeline_hd.pipeline.pipeline_utils import QS


class HistoryDlg(QDialog):
    def __init__(self, dt):
        super().__init__(dt)
        self.dt = dt
        self.checked = list()

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        self.checklist = CheckList(self.dt.history, self.checked)

        layout.addWidget(self.checklist)

        add_bt = QPushButton('Add')
        add_bt.clicked.connect(self.add_cmds)
        layout.addWidget(add_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def add_cmds(self):
        for item in self.checked:
            self.dt.inputw.insertPlainText(item)
            self.dt.inputw.ensureCursorVisible()


# Todo: Syntax Formatting
# Todo: Add Looping over defined Subject-Selection
class DataTerminal(QDialog):
    def __init__(self, main_win, current_object=None):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr

        self.obj = current_object
        self.history = list()

        self.default_t_globals = ['mw', 'main_window', 'ct', 'controller',
                                  'pr', 'project', 'par', 'parameters']

        self.t_globals = {'mw': self.mw,
                          'main_window': self.mw,
                          'ct': self.ct,
                          'controller': self.ct,
                          'pr': self.pr,
                          'project': self.pr,
                          'par': self.pr.parameters,
                          'parameters': self.pr.parameters}

        # Load the subject in globals if given in Class-Call
        if self.obj:
            self.t_globals['obj'] = self.obj

        self.bt_dict = {}

        self.load_mapping = {'info': 'load_info',
                             'raw': 'load_raw',
                             'filtered': 'load_filtered',
                             'events': 'load_events',
                             'epochs': 'load_epochs',
                             'evokeds': 'load_evokeds',
                             'ica': 'load_ica',
                             'tfr_epochs': 'load_power_tfr_epochs',
                             'tfr_average': 'load_power_tfr_average',
                             'trans': 'load_transformation',
                             'forward': 'load_forward',
                             'noise_cov': 'load_noise_covariance',
                             'inv_op': 'load_inverse_operator',
                             'stc': 'load_source_estimates'}

        # sys.stdout.signal.text_written.connect(self.update_label)

        set_ratio_geometry(0.7, self)

        self.init_ui()
        self.show()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.sub_cmbx = QComboBox()
        self.sub_cmbx.addItems(self.pr.all_meeg)
        if self.obj:
            self.sub_cmbx.setCurrentText(self.obj.name)
        else:
            self.sub_cmbx.setCurrentIndex(-1)
        self.sub_cmbx.activated.connect(self.sub_selected)
        self.layout.addWidget(self.sub_cmbx)

        # Add Buttons to load several parts of Sub
        bt_layout = QHBoxLayout()
        for bt_name in self.load_mapping:
            bt = QPushButton(bt_name)
            self.bt_dict[bt_name] = bt
            bt.clicked.connect(partial(self.load_bt_pressed, bt_name))
            bt_layout.addWidget(bt)
            if self.obj is None:
                bt.setEnabled(False)

        self.layout.addLayout(bt_layout)

        self.displayw = MainConsoleWidget()
        self.layout.addWidget(self.displayw)

        self.sub_layout = QGridLayout()
        self.inputw = CodeEditor()
        self.inputw.setSizePolicy(QSizePolicy(QSizePolicy.Preferred,
                                              QSizePolicy.Maximum))
        self.sub_layout.addWidget(self.inputw, 0, 0, 3, 1)

        self.start_bt = QPushButton('Start')
        self.start_bt.setFont(QFont(QS().value('app_font'), 16))
        self.start_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum,
                                                QSizePolicy.Preferred))
        self.start_bt.clicked.connect(self.start_execution)
        self.sub_layout.addWidget(self.start_bt, 0, 1)

        self.history_bt = QPushButton('History')
        self.history_bt.setFont(QFont(QS().value('app_font'), 16))
        self.history_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum,
                                                  QSizePolicy.Preferred))
        self.history_bt.clicked.connect(partial(HistoryDlg, self))
        self.sub_layout.addWidget(self.history_bt, 1, 1)

        self.quit_bt = QPushButton('Close')
        self.quit_bt.setFont(QFont(QS().value('app_font'), 16))
        self.quit_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum,
                                               QSizePolicy.Preferred))
        self.quit_bt.clicked.connect(self.close)
        self.sub_layout.addWidget(self.quit_bt, 2, 1)

        self.layout.addLayout(self.sub_layout)

        self.setLayout(self.layout)

    def sub_selected(self, index):
        # Enable all Buttons for the first time,
        # if no obj was given to call at the beginning
        if self.obj is None:
            for bt_name in self.bt_dict:
                self.bt_dict[bt_name].setEnabled(True)

        name = self.sub_cmbx.itemText(index)
        try:
            self.obj = MEEG(name, self.ct)
        except:  # noqa: E722
            get_exception_tuple()
            # Return ComboBox to previous state
            if self.obj is None:
                self.sub_cmbx.setCurrentIndex(-1)
            else:
                self.sub_cmbx.setCurrentText(self.obj.name)
        else:
            # Reset globals to default
            for key in [k for k in self.t_globals.keys()
                        if k not in self.default_t_globals]:
                self.t_globals.pop(key)
            self.t_globals['obj'] = self.obj
            self.displayw.insertHtml(
                f'<b>Subject: {self.obj.name} loaded</b><br>')
            self.displayw.ensureCursorVisible()

    def load_bt_pressed(self, bt_name):
        worker_dialog = WorkerDialog(
            self, self.start_load, title=f'Loading {bt_name}...',
            bt_name=bt_name)
        worker_dialog.thread_finished.connect(self.finished_handling)

    def finished_handling(self, result_msg):
        if isinstance(result_msg, str):
            self.displayw.insertHtml(result_msg)
            self.displayw.ensureCursorVisible()

    def start_load(self, bt_name):
        try:
            load_fn = getattr(self.obj, self.load_mapping[bt_name])
            self.t_globals[bt_name] = load_fn()
        except (FileNotFoundError, OSError):
            result_msg = \
                f'<b><center>No file found for {bt_name}</center></b><br>'
        else:
            result_msg = \
                f'<b><big><center>{bt_name} loaded ' \
                f'(namespace = {bt_name})</center></big></b><br>'

        return result_msg

    def start_execution(self):
        command = self.inputw.toPlainText()
        command_html = command.replace('\n', '<br>')
        self.displayw.insertHtml(
            f'<font color="blue"><b><i>{command_html}</i></b></font><br>')
        self.displayw.ensureCursorVisible()
        self.history.insert(0, command)

        try:
            print(eval(command, self.t_globals))
        except SyntaxError:
            try:
                exec(command, self.t_globals)
            except:  # noqa: E722
                get_exception_tuple()
            else:
                self.inputw.clear()
        except:  # noqa: E722
            get_exception_tuple()
        else:
            self.inputw.clear()
