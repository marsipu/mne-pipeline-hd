# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import inspect
import logging
import shutil
import sys
import traceback
import types
from ast import literal_eval
from importlib import util
from math import isnan
from os import listdir, mkdir
from os.path import isdir, isfile, join
from pathlib import Path

import matplotlib
import pandas as pd
from PyQt5.QtCore import QObject, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QPushButton,
                             QScrollArea, QStyle, QTableWidget, QTableWidgetItem, QTableWidgetSelectionRange,
                             QVBoxLayout)

from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.qt_utils import ErrorDialog, Worker
from mne_pipeline_hd.gui.subject_widgets import CurrentMRISubject, CurrentSubject
from mne_pipeline_hd.pipeline_functions import ismac


class FunctionWorkerSignals(QObject):
    """
    Defines the Signals for the Worker and call_functions
    """
    # Worker-Signals
    finished = pyqtSignal()
    error = pyqtSignal(tuple)

    # Signals for call_functions
    pgbar_n = pyqtSignal(int)
    pg_sub = pyqtSignal(str)
    pg_func = pyqtSignal(str)
    pg_which_loop = pyqtSignal(str)
    func_sig = pyqtSignal(dict)


class FunctionWorker(Worker):
    def __init__(self, fn, *args, **kwargs):
        self.signal_class = FunctionWorkerSignals()

        # Add the callback to our kwargs
        kwargs['signals'] = {'pgbar_n': self.signal_class.pgbar_n,
                             'pg_sub': self.signal_class.pg_sub,
                             'pg_func': self.signal_class.pg_func,
                             'pg_which_loop': self.signal_class.pg_which_loop,
                             'func_sig': self.signal_class.func_sig}

        super().__init__(fn, self.signal_class, *args, **kwargs)


def func_from_def(func_name, subject, main_win):
    # Get module, has to specified in functions.csv as it is imported
    module_name = main_win.pd_funcs['module'][func_name]
    module = main_win.all_modules[module_name]

    # Get Argument-Names from functions.csv (alias pd_funcs)
    arg_string = main_win.pd_funcs.loc[func_name, 'func_args']
    if pd.notna(arg_string):
        arg_names = arg_string.split(',')
    else:
        arg_names = []

    # Get attributes from Subject/Project-Class
    if subject:
        subject_attributes = vars(subject)
    else:
        subject_attributes = {}
    project_attributes = vars(main_win.pr)

    keyword_arguments = dict()

    for arg_name in arg_names:
        # Remove trailing spaces
        arg_name = arg_name.replace(' ', '')
        if arg_name == 'mw':
            keyword_arguments.update({'mw': main_win})
        elif arg_name == 'pr':
            keyword_arguments.update({'pr': main_win.pr})
        elif arg_name in subject_attributes:
            keyword_arguments.update({arg_name: subject_attributes[arg_name]})
        elif arg_name in project_attributes:
            keyword_arguments.update({arg_name: project_attributes[arg_name]})
        elif arg_name in main_win.pr.parameters:
            keyword_arguments.update({arg_name: main_win.pr.parameters[arg_name]})
        else:
            raise RuntimeError(f'{arg_name} could not be found in Subject, Project or Parameters')

    # Call Function from specified module with arguments from unpacked list/dictionary
    return_value = getattr(module, func_name)(**keyword_arguments)

    return return_value


def subject_loop(main_win, signals, subject_type, selected_subjects, selected_functions, count):
    for name in selected_subjects:
        if not main_win.cancel_functions:
            if subject_type == 'mri':
                subject = CurrentMRISubject(name, main_win)
            elif subject_type == 'file':
                subject = CurrentSubject(name, main_win)
                main_win.subject = subject
            else:
                subject = None
            # Print Subject Console Header
            print('=' * 60 + '\n', name + '\n')
            signals['pg_sub'].emit(name)
            for func in selected_functions:
                if not main_win.cancel_functions:
                    if main_win.pd_funcs.loc[func, 'mayavi']:
                        signals['pg_func'].emit(func)
                        # Mayavi-Plots need to be called in the main thread
                        signals['func_sig'].emit({'func_name': func, 'subject': subject, 'main_win': main_win})
                        signals['pgbar_n'].emit(count)
                        count += 1
                    elif main_win.pd_funcs.loc[func, 'matplotlib'] and main_win.pr.parameters['show_plots']:
                        signals['pg_func'].emit(func)
                        # Matplotlib-Plots can be called without showing (backend: agg),
                        # but to be shown, they have to be called in the main thread
                        signals['func_sig'].emit({'func_name': func, 'subject': subject, 'main_win': main_win})
                        signals['pgbar_n'].emit(count)
                        count += 1
                    else:
                        signals['pg_func'].emit(func)
                        func_from_def(func, subject, main_win)
                        signals['pgbar_n'].emit(count)
                        count += 1
                else:
                    break
        else:
            break

    return count


def call_functions(main_win, signals):
    """
    Call activated functions in main_window, read function-parameters from functions_empty.csv
    :param main_win: Main-Window-Instance
    :param signals: Signals to send into main-thread
    """
    count = 1

    # Set non-interactive backend for plots to be runnable in QThread
    # This can be a problem with older versions from matplotlib, as you can set the backend only once there
    # This could be solved with importing all the function-modules here, but you had to import them for each run then
    if not main_win.pr.parameters['show_plots']:
        matplotlib.use('agg')
    elif ismac:
        matplotlib.use('macosx')
    else:
        matplotlib.use('Qt5Agg')

    # Check if any mri-subject is selected
    if len(main_win.pr.sel_mri_files) * len(main_win.sel_mri_funcs) > 0:
        signals['pg_which_loop'].emit('mri')
        count = subject_loop(main_win, signals, 'mri', main_win.pr.sel_mri_files,
                             main_win.sel_mri_funcs, count)
    else:
        print('No MRI-Subject or MRI-Function selected')

    # Call the functions for selected Files
    if len(main_win.pr.sel_files) > 0:
        signals['pg_which_loop'].emit('file')
        count = subject_loop(main_win, signals, 'file', main_win.pr.sel_files,
                             main_win.sel_file_funcs, count)
    else:
        print('No Subject selected')

    # Call functions outside the subject-loop
    if len(main_win.sel_ga_funcs) > 0:
        signals['pg_which_loop'].emit('ga')
        subject_loop(main_win, signals, 'ga', ['Grand-Average'],
                     main_win.sel_ga_funcs, count)
    else:
        print('No Grand-Average-Function selected')


class CustomFunctionImport(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.path_dict = {}
        self.function_dict = {}
        self.module_dict = {}
        self.func_setup_dict = {}
        self.param_dict = {}
        self.param_exst_dict = {}
        self.param_setup_dict = {}
        self.current_function = None
        self.current_func_row = 0
        self.current_parameter = None
        self.current_param_row = 0

        self.exst_functions = list(self.mw.pd_funcs.index)
        # Todo: Better solution to include subject-attributes
        exst_sub_attributes = ['name', 'save_dir', 'ermsub', 'bad_channels', 'info', 'raw_filtered', 'events', 'epochs',
                               'evokeds']
        exst_proj_attributes = vars(self.mw.pr)
        self.exst_parameters = exst_sub_attributes + list(exst_proj_attributes) + list(self.mw.pr.parameters)

        self.add_pd_funcs = pd.DataFrame(columns=['alias', 'tab', 'group', 'subject_loop', 'matplotlib', 'mayavi',
                                                  'dependencies', 'module', 'func_args'])
        self.add_pd_params = pd.DataFrame(columns=['alias', 'default', 'unit', 'description', 'gui_type', 'gui_args'])

        self.yes_icon = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        self.no_icon = self.style().standardIcon(QStyle.SP_DialogCancelButton)

        self.setWindowTitle('Custom-Functions-Setup')

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QHBoxLayout()

        # The Import Group-Box
        import_gbox = QGroupBox('Add Functions')
        import_layout = QVBoxLayout()

        self.exstf_l = QLabel()
        self.exstf_l.setWordWrap(True)
        self.exstf_l.hide()
        import_layout.addWidget(self.exstf_l)

        addfn_bt = QPushButton('Add Functions')
        addfn_bt.clicked.connect(self.get_functions)
        import_layout.addWidget(addfn_bt)

        self.func_tablew = QTableWidget(0, 3)
        self.func_tablew.cellClicked.connect(self.func_item_selected)
        self.func_tablew.setHorizontalHeaderLabels(['Function-Name', 'Module', 'ready'])
        self.func_tablew.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.func_tablew.setFocus()
        import_layout.addWidget(self.func_tablew)

        bt_layout = QHBoxLayout()
        showcode_bt = QPushButton('Show Source-Code')
        showcode_bt.clicked.connect(self.show_source_code)
        bt_layout.addWidget(showcode_bt)

        remove_bt = QPushButton('Remove')
        remove_bt.clicked.connect(self.remove_func_item)
        bt_layout.addWidget(remove_bt)

        save_bt = QPushButton('Save')
        save_bt.clicked.connect(self.save_pkg)
        bt_layout.addWidget(save_bt)

        close_bt = QPushButton('Quit')
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        # Workaround for Dialog not doing anything when Enter is pressed
        void_button = QPushButton(self)
        void_button.setDefault(True)
        bt_layout.addWidget(void_button)

        import_layout.addLayout(bt_layout)
        import_gbox.setLayout(import_layout)

        # The Function-Setup-Groupbox
        func_setup_gbox = QGroupBox('Function-Setup')
        func_setup_layout = QFormLayout()

        self.falias_le = QLineEdit()
        self.falias_le.setToolTip('Set a name if you want something other than the functions-name')
        self.falias_le.textEdited.connect(self.falias_changed)
        func_setup_layout.addRow('Alias', self.falias_le)

        tab_layout = QHBoxLayout()
        self.tab_cmbx = QComboBox()
        self.tab_cmbx.setToolTip('Choose the Tab for the function (Compute/Plot/...)')
        self.tab_cmbx.activated.connect(self.tab_cmbx_changed)
        tab_layout.addWidget(self.tab_cmbx)
        self.tab_chkl = QLabel()
        tab_layout.addWidget(self.tab_chkl)
        func_setup_layout.addRow('Tab', tab_layout)

        group_layout = QHBoxLayout()
        self.group_cmbx = QComboBox()
        self.group_cmbx.setToolTip('Choose the function-group for the function or create a new one')
        self.group_cmbx.setEditable(True)
        self.group_cmbx.activated.connect(self.group_cmbx_changed)
        self.group_cmbx.editTextChanged.connect(self.group_cmbx_edited)
        group_layout.addWidget(self.group_cmbx)
        self.group_chkl = QLabel()
        group_layout.addWidget(self.group_chkl)
        func_setup_layout.addRow('Group', group_layout)

        subloop_layout = QHBoxLayout()
        self.subloop_chbx = QCheckBox()
        self.subloop_chbx.setToolTip('Check if function is applied to each file '
                                     '(instead of e.g. grand-average-functions)')
        self.subloop_chbx.stateChanged.connect(self.subloop_changed)
        subloop_layout.addWidget(self.subloop_chbx)
        self.subloop_chkl = QLabel()
        subloop_layout.addWidget(self.subloop_chkl)
        func_setup_layout.addRow('Subject-Loop?', subloop_layout)

        mtpl_layout = QHBoxLayout()
        self.mtpl_chbx = QCheckBox()
        self.mtpl_chbx.setToolTip('Is the function containing a Matplotlib-Plot?')
        self.mtpl_chbx.stateChanged.connect(self.mtpl_changed)
        mtpl_layout.addWidget(self.mtpl_chbx)
        self.mtpl_chkl = QLabel()
        mtpl_layout.addWidget(self.mtpl_chkl)
        func_setup_layout.addRow('Matplotlib?', mtpl_layout)

        myv_layout = QHBoxLayout()
        self.myv_chbx = QCheckBox()
        self.myv_chbx.setToolTip('Is the function containing a Mayavi-Plot?')
        self.myv_chbx.stateChanged.connect(self.myv_changed)
        myv_layout.addWidget(self.myv_chbx)
        self.myv_chkl = QLabel()
        myv_layout.addWidget(self.myv_chkl)
        func_setup_layout.addRow('Mayavi?', myv_layout)

        self.dpd_bt = QPushButton('Set Dependencies')
        self.dpd_bt.setToolTip('Set the functions that must be activated before or the files that must be present '
                               'for this function to work')
        self.dpd_bt.clicked.connect(self.select_dependencies)
        func_setup_layout.addRow('Dependencies', self.dpd_bt)

        func_setup_gbox.setLayout(func_setup_layout)

        # The Parameter-Setup-Group-Box
        self.param_setup_gbox = QGroupBox('Parameter-Setup')
        param_setup_layout = QVBoxLayout()
        self.exstparam_l = QLabel()
        self.exstparam_l.setWordWrap(True)
        self.exstparam_l.hide()
        param_setup_layout.addWidget(self.exstparam_l)

        self.param_tablew = QTableWidget(0, 2)
        self.param_tablew.cellClicked.connect(self.param_item_selected)
        self.param_tablew.setHorizontalHeaderLabels(['Parameter-Name', 'ready'])
        self.param_tablew.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        param_setup_layout.addWidget(self.param_tablew)

        param_setup_formlayout = QFormLayout()
        self.palias_le = QLineEdit()
        self.palias_le.setToolTip('Set a name if you want something other than the parameters-name')
        self.palias_le.textEdited.connect(self.palias_changed)
        param_setup_formlayout.addRow('Alias', self.palias_le)

        default_layout = QHBoxLayout()
        self.default_le = QLineEdit()
        self.default_le.setToolTip('Set the default for the parameter (it has to fit the gui-type!)')
        self.default_le.textEdited.connect(self.pdefault_changed)
        default_layout.addWidget(self.default_le)
        self.default_chkl = QLabel()
        default_layout.addWidget(self.default_chkl)
        param_setup_formlayout.addRow('Default', default_layout)

        self.unit_le = QLineEdit()
        self.unit_le.setToolTip('Set the unit for the parameter (optional)')
        self.unit_le.textEdited.connect(self.punit_changed)
        param_setup_formlayout.addRow('Unit', self.unit_le)

        self.description_le = QLineEdit()
        self.description_le.setToolTip('Short description of the parameter (optional)')
        self.description_le.textEdited.connect(self.pdescription_changed)
        param_setup_formlayout.addRow('Description', self.description_le)

        # Todo: Proper Widgets for Gui-Arguments
        guitype_layout = QHBoxLayout()
        self.guitype_cmbx = QComboBox()
        self.guitype_cmbx.setToolTip('Choose the GUI from the available GUIs')
        self.guitype_cmbx.activated.connect(self.guitype_cmbx_changed)
        guitype_layout.addWidget(self.guitype_cmbx)
        test_bt = QPushButton('Test')
        test_bt.clicked.connect(self.show_param_gui)
        guitype_layout.addWidget(test_bt)
        self.guitype_chkl = QLabel()
        guitype_layout.addWidget(self.guitype_chkl)
        param_setup_formlayout.addRow('GUI-Type', guitype_layout)

        self.guiargs_le = QLineEdit()
        self.guiargs_le.setToolTip('Set Arguments for the GUI in a dict (optional)')
        self.guiargs_le.textEdited.connect(self.pguiargs_changed)
        param_setup_formlayout.addRow('GUI-Arguments (optional)', self.guiargs_le)

        param_setup_layout.addLayout(param_setup_formlayout)
        self.param_setup_gbox.setLayout(param_setup_layout)

        layout.addWidget(import_gbox)
        layout.addWidget(func_setup_gbox)
        layout.addWidget(self.param_setup_gbox)
        self.setLayout(layout)

        self.populate_tab_cmbx()
        self.populate_group_cmbx()
        self.populate_guitype_cmbx()

    def func_item_selected(self, row):
        # Select row
        self.func_tablew.setRangeSelected(QTableWidgetSelectionRange(row, 0, row, 2), True)
        self.current_function = self.func_tablew.item(row, 0).text()
        self.current_func_row = row
        self.update_func_setup()
        if len(self.param_setup_dict[self.current_function]) > 0:
            self.param_setup_gbox.setEnabled(True)
            self.populate_param_tablew()
            self.current_parameter = self.param_tablew.item(0, 0).text()
            self.update_param_setup()
        else:
            self.populate_param_tablew()
            self.palias_le.clear()
            self.default_le.clear()
            self.unit_le.clear()
            self.guitype_cmbx.setCurrentIndex(-1)
            self.guiargs_le.clear()
            self.param_setup_gbox.setEnabled(False)

    def param_item_selected(self, row):
        # Select row
        self.param_tablew.setRangeSelected(QTableWidgetSelectionRange(row, 0, row, 1), True)
        self.current_parameter = self.param_tablew.item(row, 0).text()
        self.current_param_row = row
        self.update_param_setup()

    def update_func_setup(self):
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'alias']):
            self.falias_le.setText(self.add_pd_funcs.loc[self.current_function, 'alias'])
        else:
            self.falias_le.clear()
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'tab']):
            self.tab_cmbx.setCurrentText(self.add_pd_funcs.loc[self.current_function, 'tab'])
            self.tab_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.tab_cmbx.setCurrentIndex(-1)
            self.tab_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'group']):
            self.group_cmbx.setCurrentText(self.add_pd_funcs.loc[self.current_function, 'group'])
            self.group_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.group_cmbx.setCurrentIndex(-1)
            self.group_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'subject_loop']):
            if self.add_pd_funcs.loc[self.current_function, 'subject_loop']:
                self.subloop_chbx.setChecked(True)
            else:
                self.subloop_chbx.setChecked(False)
            self.subloop_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.subloop_chbx.setChecked(False)
            self.subloop_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'matplotlib']):
            if self.add_pd_funcs.loc[self.current_function, 'matplotlib']:
                self.mtpl_chbx.setChecked(True)
            else:
                self.mtpl_chbx.setChecked(False)
            self.mtpl_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.mtpl_chbx.setChecked(False)
            self.mtpl_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'mayavi']):
            if self.add_pd_funcs.loc[self.current_function, 'mayavi']:
                self.myv_chbx.setChecked(True)
            else:
                self.myv_chbx.setChecked(False)
            self.myv_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.myv_chbx.setChecked(False)
            self.myv_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))

    def update_param_setup(self):
        if len(self.param_exst_dict[self.current_function]) > 0:
            self.exstparam_l.setText(f'Already existing Parameters: {self.param_exst_dict[self.current_function]}')
            self.exstparam_l.show()
        else:
            self.exstparam_l.hide()
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'alias']):
            self.palias_le.setText(self.add_pd_params.loc[self.current_parameter, 'alias'])
        else:
            self.palias_le.clear()
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'default']):
            self.default_le.setText(self.add_pd_params.loc[self.current_parameter, 'default'])
            self.default_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.default_le.clear()
            self.default_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'unit']):
            self.unit_le.setText(self.add_pd_params.loc[self.current_parameter, 'unit'])
        else:
            self.unit_le.clear()
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'description']):
            self.description_le.setText(self.add_pd_params.loc[self.current_parameter, 'description'])
        else:
            self.description_le.clear()
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_type']):
            self.guitype_cmbx.setCurrentText(self.add_pd_params.loc[self.current_parameter, 'gui_type'])
            self.guitype_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.guitype_cmbx.setCurrentIndex(-1)
            self.guitype_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_args']):
            self.guiargs_le.setText(self.add_pd_params.loc[self.current_parameter, 'gui_args'])
        else:
            self.guiargs_le.clear()

    def check_func_setup(self):
        obligatory_items = ['tab', 'group', 'subject_loop', 'matplotlib', 'mayavi']
        # Check, that all obligatory items of the Subject-Setup and the Parameter-Setup are set
        if (all([pd.notna(self.add_pd_funcs.loc[self.current_function, i]) for i in obligatory_items])
                and all([i for i in self.param_setup_dict[self.current_function].values()])):
            self.func_setup_dict[self.current_function] = True
            self.func_tablew.item(self.current_func_row, 2).setIcon(self.yes_icon)

    def check_param_setup(self):
        obligatory_items = ['default', 'gui_type']
        # Check, that all obligatory items of the Parameter-Setup are set
        if all([pd.notna(self.add_pd_params.loc[self.current_parameter, i]) for i in obligatory_items]):
            self.param_setup_dict[self.current_function][self.current_parameter] = True
            self.param_tablew.item(self.current_param_row, 1).setIcon(self.yes_icon)

    # Line-Edit Change-Signals
    def falias_changed(self, text):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'alias'] = text

    def subloop_changed(self, state):
        if self.current_function:
            if state:
                self.add_pd_funcs.loc[self.current_function, 'subject_loop'] = True
            else:
                self.add_pd_funcs.loc[self.current_function, 'subject_loop'] = False
            self.subloop_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def mtpl_changed(self, state):
        if self.current_function:
            if state:
                self.add_pd_funcs.loc[self.current_function, 'matplotlib'] = True
            else:
                self.add_pd_funcs.loc[self.current_function, 'matplotlib'] = False
            self.mtpl_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def myv_changed(self, state):
        if self.current_function:
            if state:
                self.add_pd_funcs.loc[self.current_function, 'mayavi'] = True
            else:
                self.add_pd_funcs.loc[self.current_function, 'mayavi'] = False
            self.myv_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def palias_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'alias'] = text

    def pdefault_changed(self, text):
        if self.current_parameter:
            # Check, if default_value and gui_type match
            if pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_type']):
                result = self.test_param_gui(default_string=text,
                                             gui_type=self.add_pd_params.loc[self.current_parameter, 'gui_type'])
            else:
                result = True
            if result:
                self.add_pd_params.loc[self.current_parameter, 'default'] = text
                self.default_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
                self.check_param_setup()
                self.check_func_setup()
            else:
                self.default_le.clear()
                QMessageBox.warning(self, 'Invalid default-value',
                                    'The default-value doesn\'t match the selected gui-type')

    def punit_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'unit'] = text

    def pdescription_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'description'] = text

    def pguiargs_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'gui_args'] = text

    def populate_func_tablew(self):
        row_count = self.func_tablew.rowCount()
        self.func_tablew.setRowCount(len(self.function_dict))
        for key in self.function_dict:
            name_item = QTableWidgetItem(key)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.func_tablew.setItem(row_count, 0, name_item)
            module_item = QTableWidgetItem(self.module_dict[key])
            module_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.func_tablew.setItem(row_count, 1, module_item)
            setup_item = QTableWidgetItem()
            setup_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            if self.func_setup_dict[key]:
                setup_item.setIcon(self.yes_icon)
            else:
                setup_item.setIcon(self.no_icon)
            self.func_tablew.setItem(row_count, 2, setup_item)
            row_count += 1

    def populate_param_tablew(self):
        if self.current_function and self.current_function in self.param_setup_dict:
            # Remove Rows of last function
            row_count = self.param_tablew.rowCount()
            while row_count > 0:
                self.param_tablew.removeRow(0)
                row_count -= 1
            params = self.param_setup_dict[self.current_function]
            self.param_tablew.setRowCount(row_count + len(params))
            for param in params:
                name_item = QTableWidgetItem(param)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.param_tablew.setItem(row_count, 0, name_item)
                setup_item = QTableWidgetItem()
                setup_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                if self.param_setup_dict[self.current_function][param]:
                    setup_item.setIcon(self.yes_icon)
                else:
                    setup_item.setIcon(self.no_icon)
                self.param_tablew.setItem(row_count, 1, setup_item)
                row_count += 1

    def populate_tab_cmbx(self):
        self.tab_cmbx.insertItems(0, self.mw.f_tabs)
        self.tab_cmbx.setCurrentIndex(-1)

    def populate_group_cmbx(self):
        self.group_cmbx.insertItems(0, self.mw.f_groups)
        self.group_cmbx.setCurrentIndex(-1)

    def populate_guitype_cmbx(self):
        self.guitype_cmbx.insertItems(0, self.mw.available_param_guis)
        self.guitype_cmbx.setCurrentIndex(-1)

    def tab_cmbx_changed(self, idx):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'tab'] = self.tab_cmbx.itemText(idx)
            self.tab_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def group_cmbx_changed(self, idx):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'group'] = self.group_cmbx.itemText(idx)
            self.group_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def group_cmbx_edited(self, text):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'group'] = text
            self.group_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def guitype_cmbx_changed(self, idx):
        text = self.guitype_cmbx.itemText(idx)
        if self.current_parameter:
            # Check, if default_value and gui_type match
            if pd.notna(self.add_pd_params.loc[self.current_parameter, 'default']):
                result = self.test_param_gui(default_string=self.add_pd_params.loc[self.current_parameter, 'default'],
                                             gui_type=text)
            else:
                result = True
            if result:
                self.add_pd_params.loc[self.current_parameter, 'gui_type'] = text
                self.guitype_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
                self.check_param_setup()
                self.check_func_setup()
            else:
                self.guitype_cmbx.setCurrentIndex(-1)
                QMessageBox.warning(self, 'Invalid gui_type-value',
                                    'The gui_type-value doesn\'t match the entered default_value')

    def get_functions(self):
        # Returns tuple of files-list and file-type
        files_list = QFileDialog.getOpenFileNames(self, 'Choose the Python-File//s containing your function to import',
                                                  filter='Python-File (*.py)')[0]
        already_exst_funcs = []
        if files_list:
            for path_string in files_list:
                file_path = Path(path_string)
                spec = util.spec_from_file_location(file_path.stem, file_path)
                module = util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except:
                    traceback.print_exc()
                    traceback_str = traceback.format_exc(limit=-10)
                    exctype, value = sys.exc_info()[:2]
                    logging.error(f'{exc_type}: {exc}\n'
                                  f'{traceback_str}')
                    ErrorDialog(None, (exctype, value, traceback_str))
                for func_key in module.__dict__:
                    # Check, if function is already existing
                    if func_key not in self.exst_functions:
                        func = module.__dict__[func_key]
                        # Only functions are allowed (Classes should be called from function)
                        if isinstance(func, types.FunctionType) and func.__module__ == module.__name__:
                            self.path_dict[func_key] = file_path
                            self.function_dict[func_key] = func
                            self.module_dict[func_key] = module.__name__
                            self.func_setup_dict[func_key] = False
                            # Append empty Series to Func-Data-Frame
                            func_series = pd.Series([], name=func_key, dtype='object')
                            self.add_pd_funcs = self.add_pd_funcs.append(func_series)
                            # Get Parameters and divide them in existing and setup
                            signature = inspect.signature(func)
                            all_parameters = [signature.parameters[p].name for p in signature.parameters]
                            self.param_dict[func_key] = all_parameters
                            self.param_exst_dict[func_key] = [p for p in all_parameters if p in self.exst_parameters]
                            self.param_setup_dict[func_key] = {}
                            for param in [p for p in all_parameters if p not in self.exst_parameters]:
                                self.param_setup_dict[func_key][param] = False
                                # Append empty Series to Func-Data-Frame
                                param_series = pd.Series([], name=param, dtype='object')
                                if param not in self.add_pd_params.index:
                                    self.add_pd_params = self.add_pd_params.append(param_series)
                    else:
                        already_exst_funcs.append(func_key)
            if len(already_exst_funcs) > 0:
                self.exstf_l.setText(f'Already existing functions: {already_exst_funcs}')
                self.exstf_l.show()
            else:
                self.exstf_l.hide()
            self.populate_func_tablew()

    def remove_func_item(self):
        row = self.func_tablew.currentRow()
        if row >= 0:
            name = self.func_tablew.item(row, 0).text()

            self.function_dict.pop(name, None)
            self.module_dict.pop(name, None)
            self.func_setup_dict.pop(name, None)

            self.func_tablew.removeRow(row)

    def show_source_code(self):
        row = self.func_tablew.currentRow()
        if row >= 0:
            name = self.func_tablew.item(row, 0).text()
            show_dlg = QDialog(self)
            layout = QVBoxLayout()
            label = QLabel(inspect.getsource(self.function_dict[name]))
            scroll_area = QScrollArea()
            scroll_area.setWidget(label)
            layout.addWidget(scroll_area)
            ok_bt = QPushButton('Close')
            ok_bt.clicked.connect(show_dlg.close)
            layout.addWidget(ok_bt)
            show_dlg.setLayout(layout)
            show_dlg.open()

    def select_dependencies(self):
        SelectDependencies(self)

    def test_param_gui(self, default_string, gui_type):
        self.parameters = {}
        try:
            self.parameters[self.current_parameter] = literal_eval(default_string)
        except (ValueError, SyntaxError):
            # Allow parameters to be defined by functions by numpy, etc.
            if self.add_pd_params.loc[self.current_parameter, 'gui_type'] == 'FuncGui':
                self.parameters[self.current_parameter] = eval(default_string)
            else:
                self.parameters[self.current_parameter] = default_string
        gui_handle = getattr(parameter_widgets, gui_type)
        try:
            gui_handle(self, self.current_parameter, 'Test', '')
        except TypeError:
            result = False
        else:
            result = True
        return result

    def show_param_gui(self):
        if self.current_parameter and pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_type']):
            TestParamGui(self)

    def save_pkg(self):
        if any([self.func_setup_dict[k] for k in self.func_setup_dict]):
            SavePkgDialog(self)

    def closeEvent(self, event):
        drop_funcs = [f for f in self.func_setup_dict if not self.func_setup_dict[f]]

        if len(drop_funcs) > 0:
            answer = QMessageBox.question(self, 'Close Custom-Functions?', f'There are still unfinished functions:\n'
                                                                           f'{drop_funcs}\n'
                                                                           f'Do you still want to quit?')
        else:
            answer = None

        if answer == QMessageBox.Yes or answer is None:
            event.accept()


class SelectDependencies(QDialog):
    def __init__(self, cf_dialog):
        super().__init__(cf_dialog)
        self.cf_dialog = cf_dialog
        if pd.notna(cf_dialog.add_pd_funcs.loc[cf_dialog.current_function, 'dependencies']):
            self.dpd_list = literal_eval(cf_dialog.add_pd_funcs.loc[cf_dialog.current_function, 'dependencies'])
        else:
            self.dpd_list = []

        layout = QVBoxLayout()
        self.listw = QListWidget()
        self.listw.itemChanged.connect(self.item_checked)
        layout.addWidget(self.listw)

        ok_bt = QPushButton('OK')
        ok_bt.clicked.connect(self.close_dlg)
        layout.addWidget(ok_bt)

        self.populate_listw()
        self.setLayout(layout)
        self.open()

    def populate_listw(self):
        for function in self.cf_dialog.mw.pd_funcs.index:
            item = QListWidgetItem(function)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if function in self.dpd_list:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.listw.addItem(item)

    def item_checked(self, item):
        if item.checkState == Qt.Checked:
            self.dpd_list.append(item.text())
        elif item.text() in self.dpd_list:
            self.dpd_list.remove(item.text())

    def close_dlg(self):
        self.cf_dialog.add_pd_funcs.loc[self.cf_dialog.current_function, 'dependencies'] = str(self.dpd_list)
        self.close()


class TestParamGui(QDialog):
    def __init__(self, cf_dialog):
        super().__init__(cf_dialog)
        self.cf = cf_dialog
        # Replacement for Parameters in Project for Testing
        self.parameters = {}
        string_param = self.cf.add_pd_params.loc[self.cf.current_parameter, 'default']
        try:
            self.parameters[self.cf.current_parameter] = literal_eval(string_param)
        except (ValueError, SyntaxError):
            # Allow parameters to be defined by functions by numpy, etc.
            if self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type'] == 'FuncGui':
                self.parameters[self.cf.current_parameter] = eval(string_param)
            else:
                self.parameters[self.cf.current_parameter] = string_param

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        # Allow Enter-Press without closing the dialog
        if self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type'] == 'FuncGui':
            void_bt = QPushButton()
            void_bt.setDefault(True)
            layout.addWidget(void_bt)

        gui_handle = getattr(parameter_widgets, self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type'])
        if isnan(self.cf.add_pd_params.loc[self.cf.current_parameter, 'alias']):
            param_alias = self.cf.current_parameter
        else:
            param_alias = self.cf.add_pd_params.loc[self.cf.current_parameter, 'alias']
        if isnan(self.cf.add_pd_params.loc[self.cf.current_parameter, 'description']):
            hint = ''
        else:
            hint = self.cf.add_pd_params.loc[self.cf.current_parameter, 'description']
        try:
            gui_args = literal_eval(self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_args'])
        except (SyntaxError, ValueError):
            gui_args = {}
        try:
            param_gui = gui_handle(self, self.cf.current_parameter, param_alias, hint, **gui_args)
            layout.addWidget(param_gui)
        except:
            traceback.print_exc()
            traceback_str = traceback.format_exc(limit=-10)
            exctype, value = sys.exc_info()[:2]
            ErrorDialog(self, (exctype, value, traceback_str))
            self.close()
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)


class SavePkgDialog(QDialog):
    def __init__(self, cf_dialog):
        super().__init__(cf_dialog)
        self.cf = cf_dialog
        self.pkg_path = None

        self.init_ui()
        self.populate_pkg_cmbx()
        self.open()

    def init_ui(self):
        layout = QGridLayout()
        self.pkg_cmbx = QComboBox()
        self.pkg_cmbx.setEditable(True)
        self.pkg_cmbx.activated.connect(self.pkg_cmbx_changed)
        self.pkg_cmbx.editTextChanged.connect(self.pkg_cmbx_edited)
        layout.addWidget(self.pkg_cmbx, 0, 0, 1, 2)

        save_bt = QPushButton('Save')
        save_bt.clicked.connect(self.save_pkg)
        layout.addWidget(save_bt, 1, 0)

        cancel_bt = QPushButton('Cancel')
        cancel_bt.clicked.connect(self.close)
        layout.addWidget(cancel_bt, 1, 1)
        self.setLayout(layout)

    def populate_pkg_cmbx(self):
        self.pkg_cmbx.insertItems(0, [d for d in listdir(self.cf.mw.pr.custom_pkg_path)
                                      if isdir(join(self.cf.mw.pr.custom_pkg_path, d))])

    def pkg_cmbx_changed(self, idx):
        self.pkg_name = self.pkg_cmbx.itemText(idx)
        self.pkg_path = join(self.cf.mw.pr.custom_pkg_path, self.pkg_name)

    def pkg_cmbx_edited(self, text):
        self.pkg_name = text
        self.pkg_path = join(self.cf.mw.pr.custom_pkg_path, self.pkg_name)

    def save_pkg(self):
        copy_modules = set()
        for func in self.cf.path_dict:
            copy_modules.add(self.cf.path_dict[func])
        if not isdir(self.pkg_path):
            mkdir(self.pkg_path)
        for ori_path in copy_modules:
            shutil.copy2(ori_path, join(self.pkg_path, Path(ori_path).name))
        # Drop all functions with unfinished setup and add them to the main_window-DataFrame
        drop_funcs = [f for f in self.cf.func_setup_dict if not self.cf.func_setup_dict[f]]
        final_add_pd_funcs = self.cf.add_pd_funcs.drop(labels=drop_funcs, axis=0)
        param_set = set()
        for func in final_add_pd_funcs.index:
            for param in self.cf.param_setup_dict[func]:
                param_set.add(param)
        final_add_pd_params = self.cf.add_pd_params.loc[param_set]

        pd_funcs_path = join(self.pkg_path, f'{self.pkg_name}_functions.csv')
        pd_params_path = join(self.pkg_path, f'{self.pkg_name}_parameters.csv')

        if isfile(pd_funcs_path):
            read_pd_funcs = pd.read_csv(pd_funcs_path, sep=';', index_col=0)
            # Check, that there are no duplicates
            drop_funcs = [f for f in read_pd_funcs.index if f in final_add_pd_funcs]
            read_pd_funcs.drop(labels=drop_funcs, axis=0)
            final_add_pd_funcs = read_pd_funcs.append(final_add_pd_funcs)
        final_add_pd_funcs.to_csv(pd_funcs_path, sep=';')
        if isfile(pd_params_path):
            read_pd_params = pd.read_csv(pd_params_path, sep=';', index_col=0)
            # Check, that there are no duplicates
            drop_params = [p for p in read_pd_params.index if p in final_add_pd_params]
            read_pd_params.drop(labels=drop_params, axis=0)
            final_add_pd_params = read_pd_params.append(final_add_pd_params)
        final_add_pd_params.to_csv(pd_params_path, sep=';')

        for func in final_add_pd_funcs.index:
            item_list = self.cf.func_tablew.findItems(func, Qt.MatchExactly)
            if item_list:
                item = item_list[0]
                self.cf.func_tablew.removeRow(self.cf.func_tablew.row(item))

        self.close()

        # Todo: update func-Buttons and Parameters-Widgets


def test_func(name, save_dir, huga, buga, f=3):
    print(name)
    save_dir = save_dir + f
    huga = huga - buga

    return save_dir, huga
