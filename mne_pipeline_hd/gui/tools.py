# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2020, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
import sys
from functools import partial
from time import sleep

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTextEdit, \
    QVBoxLayout

from mne_pipeline_hd.gui.base_widgets import CheckList
from mne_pipeline_hd.gui.gui_utils import Worker, get_exception_tuple
from mne_pipeline_hd.pipeline_functions.loading import MEEG


class LoadSignals(QObject):
    error = pyqtSignal()
    finished = pyqtSignal()


class LoadWorker(Worker):
    def __init__(self, function, *args, **kwargs):
        super().__init__(function, LoadSignals(), *args, *kwargs)


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
        self.obj = current_object
        self.history = list()

        self.default_t_globals = ['mw', 'main_window', 'pr', 'project', 'par', 'parameters']

        self.t_globals = {'mw': self.mw,
                          'main_window': self.mw,
                          'pr': self.mw.pr,
                          'project': self.mw.pr,
                          'par': self.mw.pr.parameters,
                          'parameters': self.mw.pr.parameters}

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
                             'trans': 'load_transformation',
                             'forward': 'load_forward',
                             'noise_cov': 'load_noise_covariance',
                             'inv_op': 'load_inverse_operator',
                             'stc': 'load_source_estimates'}

        sys.stdout.signal.text_written.connect(self.update_label)

        self.init_ui()
        self.open()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.sub_cmbx = QComboBox()
        self.sub_cmbx.addItems(self.mw.pr.all_meeg)
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

        self.displayw = QTextEdit()
        self.displayw.setReadOnly(True)
        self.layout.addWidget(self.displayw)

        self.sub_layout = QGridLayout()
        self.inputw = QTextEdit()
        self.inputw.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum))
        self.sub_layout.addWidget(self.inputw, 0, 0, 3, 1)

        self.start_bt = QPushButton('Start')
        self.start_bt.setFont(QFont('AnyStyle', 16))
        self.start_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self.start_bt.clicked.connect(self.start_execution)
        self.sub_layout.addWidget(self.start_bt, 0, 1)

        self.history_bt = QPushButton('History')
        self.history_bt.setFont(QFont('AnyStyle', 16))
        self.history_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self.history_bt.clicked.connect(partial(HistoryDlg, self))
        self.sub_layout.addWidget(self.history_bt, 1, 1)

        self.quit_bt = QPushButton('Close')
        self.quit_bt.setFont(QFont('AnyStyle', 16))
        self.quit_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self.quit_bt.clicked.connect(self.close)
        self.sub_layout.addWidget(self.quit_bt, 2, 1)

        self.layout.addLayout(self.sub_layout)

        self.setLayout(self.layout)

    def sub_selected(self, index):
        # Enable all Buttons for the first time, if no obj was given to call at the beginning
        if self.obj is None:
            for bt_name in self.bt_dict:
                self.bt_dict[bt_name].setEnabled(True)

        name = self.sub_cmbx.itemText(index)
        try:
            self.obj = MEEG(name, self.mw)
        except:
            self.print_exception()
            # Return ComboBox to previous state
            if self.obj is None:
                self.sub_cmbx.setCurrentIndex(-1)
            else:
                self.sub_cmbx.setCurrentText(self.obj.name)
        else:
            # Reset globals to default
            for key in [k for k in self.t_globals.keys() if k not in self.default_t_globals]:
                self.t_globals.pop(key)
            self.t_globals['obj'] = self.obj
            self.displayw.clear()
            self.displayw.insertHtml(f'<b>Subject: {self.obj.name} loaded</b><br>')
            self.displayw.ensureCursorVisible()

    def load_bt_pressed(self, bt_name):

        self.load_dlg = QDialog(self)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f'<h1>Loading {bt_name}...</h1>'))
        self.load_dlg.setLayout(layout)
        self.load_dlg.open()
        worker = LoadWorker(self.start_load, bt_name)
        worker.signals.finished.connect(self.load_dlg.close)
        worker.signals.error.connect(self.error_handling)
        self.mw.threadpool.start(worker)

    def error_handling(self):
        self.load_dlg.close()
        self.print_exception()

    def start_load(self, bt_name):
        try:
            load_fn = getattr(self.obj, self.load_mapping[bt_name])
            self.t_globals[bt_name] = load_fn()
        except (FileNotFoundError, OSError):
            self.displayw.insertHtml(f'<b><center>No file found for {bt_name}</center></b><br>')
            self.displayw.ensureCursorVisible()
        else:
            # To avoid (visual) print-conflicts
            sleep(0.01)
            self.displayw.insertHtml(f'<b><big><center>{bt_name} loaded (namespace = {bt_name})</center></big></b><br>')
            self.displayw.ensureCursorVisible()

    def update_label(self, text):
        self.displayw.insertPlainText(text)
        self.displayw.ensureCursorVisible()

    def print_exception(self, exc_tuple=None):
        exc_tuple = exc_tuple or get_exception_tuple()
        formated_tb_text = exc_tuple[2].replace('\n', '<br>')
        html_text = f'<b>{exc_tuple[0]}</b><br>' \
                    f'<b>{exc_tuple[1]}</b><br>' \
                    f'{formated_tb_text}'
        self.displayw.insertHtml(html_text)
        self.displayw.ensureCursorVisible()

    def start_execution(self):
        command = self.inputw.toPlainText()
        command_html = command.replace('\n', '<br>')
        self.displayw.insertHtml(f'<b><i>{command_html}</i></b><br>')
        self.displayw.ensureCursorVisible()
        self.history.insert(0, command)

        try:
            print(eval(command, self.t_globals))
        except SyntaxError:
            try:
                exec(command, self.t_globals)
            except:
                self.print_exception()
            else:
                self.inputw.clear()
        except:
            self.print_exception()
        else:
            self.inputw.clear()
