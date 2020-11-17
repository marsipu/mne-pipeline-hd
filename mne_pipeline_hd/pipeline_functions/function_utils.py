# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
Copyright © 2011-2019, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import inspect
import logging
import re
import sys
import time

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLabel, QListView, \
    QProgressBar, \
    QPushButton, QSizePolicy, \
    QStyle, QTextEdit, QVBoxLayout

from .pipeline_utils import shutdown
from ..basic_functions.loading import BaseSub, CurrentGAGroup, CurrentMRISub, CurrentSub
from ..basic_functions.plot import close_all
from ..gui.base_widgets import SimpleList
from ..gui.gui_utils import Worker, get_ratio_geometry
from ..gui.models import RunModel


def get_arguments(arg_names, obj, main_win):
    keyword_arguments = {}
    project_attributes = vars(main_win.pr)
    # Get the values for parameter-names
    for arg_name in arg_names:
        # Remove trailing spaces
        arg_name = arg_name.replace(' ', '')
        if arg_name == 'mw':
            keyword_arguments.update({'mw': main_win})
        elif arg_name == 'main_win':
            keyword_arguments.update({'main_win': main_win})
        elif arg_name == 'pr':
            keyword_arguments.update({'pr': main_win.pr})
        elif arg_name == 'sub':
            keyword_arguments.update({'sub': obj})
        elif arg_name == 'mri_sub':
            keyword_arguments.update({'mri_sub': obj})
        elif arg_name == 'ga_group':
            keyword_arguments.update({'ga_group': obj})
        elif arg_name in project_attributes:
            keyword_arguments.update({arg_name: project_attributes[arg_name]})
        elif arg_name in main_win.pr.parameters[main_win.pr.p_preset]:
            keyword_arguments.update({arg_name: main_win.pr.parameters[main_win.pr.p_preset][arg_name]})
        elif arg_name in main_win.settings:
            keyword_arguments.update({arg_name: main_win.settings[arg_name]})
        elif arg_name in main_win.qsettings.childKeys():
            keyword_arguments.update({arg_name: main_win.qsettings.value(arg_name)})
        else:
            raise RuntimeError(f'{arg_name} could not be found in Subject, Project or Parameters')

    return keyword_arguments


def func_from_def(name, obj, main_win):
    # Get Package-Name, is only defined for custom-packages
    pkg_name = main_win.pd_funcs['pkg_name'][name]
    # Get module, has to specified in functions.csv as it is imported
    module_name = main_win.pd_funcs['module'][name]
    if module_name in main_win.all_modules['basic']:
        module = main_win.all_modules['basic'][module_name]
    elif module_name in main_win.all_modules['custom']:
        module = main_win.all_modules['custom'][pkg_name][module_name][0]
    else:
        raise ModuleNotFoundError(name=module_name)

    # Get arguments from function signature
    func = getattr(module, name)
    arg_names = list(inspect.signature(func).parameters)

    keyword_arguments = get_arguments(arg_names, obj, main_win)

    # Catch one error due to unexpected or missing keywords
    unexp_kw_pattern = r"(.*) got an unexpected keyword argument \'(.*)\'"
    miss_kw_pattern = r"(.*) missing 1 required positional argument: \'(.*)\'"
    try:
        # Call Function from specified module with arguments from unpacked list/dictionary
        getattr(module, name)(**keyword_arguments)
    except TypeError as te:
        match_unexp_kw = re.match(unexp_kw_pattern, str(te))
        match_miss_kw = re.match(miss_kw_pattern, str(te))
        if match_unexp_kw:
            keyword_arguments.pop(match_unexp_kw.group(2))
            logging.warning(f'Caught unexpected keyword \"{match_unexp_kw.group(2)}\" for {name}')
            getattr(module, name)(**keyword_arguments)
        elif match_miss_kw:
            add_kw_args = get_arguments([match_miss_kw.group(2)], obj, main_win)
            keyword_arguments.update(add_kw_args)
            logging.warning(f'Caught missing keyword \"{match_miss_kw.group(2)}\" for {name}')
            getattr(module, name)(**keyword_arguments)
        else:
            raise te


class FunctionWorkerSignals(QObject):
    """
    Defines the Signals for the Worker and call_functions
    """
    # Worker-Signals
    # The Thread finished
    finished = pyqtSignal()
    # An Error occured
    error = pyqtSignal(tuple)


class FunctionWorkerOld(Worker):
    def __init__(self, main_win):
        self.signals = FunctionWorkerSignals()
        super().__init__(self.call_functions, self.signals)

        self.mw = main_win
        self.count = 1

        # Signals received from main_win for canceling functions and
        self.is_cancel_functions = False
        self.is_plot_running = False

    def check_cancel_functions(self, is_canceled):
        if is_canceled:
            self.is_cancel_functions = True
        else:
            self.is_cancel_functions = False

    def check_plot_running(self, is_running):
        if is_running:
            self.is_plot_running = True
        else:
            self.is_plot_running = False

    def call_functions(self):
        """
        Call activated functions in main_window, read function-parameters from functions_empty.csv
        """

        # Check if any mri-subject is selected
        if len(self.mw.pr.sel_fsmri) * len(self.mw.sel_fsmri_funcs) > 0:
            self.signals.pg_which_loop.emit('mri')
            self.subject_loop('mri')

        # Call the functions for selected Files
        if len(self.mw.pr.sel_meeg) * len(self.mw.sel_meeg_funcs) > 0:
            self.signals.pg_which_loop.emit('file')
            self.subject_loop('file')

        # Call functions outside the subject-loop for Grand-Average-Groups
        if len(self.mw.pr.sel_groups) * len(self.mw.sel_group_funcs) > 0:
            self.signals.pg_which_loop.emit('ga')
            self.subject_loop('ga')

        # Calls functions, which have no Sub
        elif len(self.mw.sel_other_funcs) > 0:
            self.signals.pg_which_loop.emit('other')
            self.subject_loop('other')

    def subject_loop(self, subject_type):
        if subject_type == 'mri':
            selected_subjects = self.mw.pr.sel_fsmri
            selected_functions = self.mw.sel_fsmri_funcs
        elif subject_type == 'file':
            selected_subjects = self.mw.pr.sel_meeg
            selected_functions = self.mw.sel_meeg_funcs
        elif subject_type == 'ga':
            selected_subjects = self.mw.pr.sel_groups
            selected_functions = self.mw.sel_group_funcs
        elif subject_type == 'other':
            selected_subjects = ['Other Functions']
            selected_functions = self.mw.sel_other_funcs
        else:
            raise RuntimeError(f'Subject-Type: {subject_type} not supported')

        running_mri_sub = None
        for name in selected_subjects:
            if not self.is_cancel_functions:
                if subject_type == 'mri':
                    sub = CurrentMRISub(name, self.mw)
                    running_mri_sub = sub
                    self.mw.subject = sub

                elif subject_type == 'file':
                    # Avoid reloading of same MRI-Subject for multiple files (with the same MRI-Subject)
                    if running_mri_sub and running_mri_sub.name == self.mw.pr.sub_dict[name]:
                        sub = CurrentSub(name, self.mw, mri_sub=running_mri_sub)
                    else:
                        sub = CurrentSub(name, self.mw)
                    running_mri_sub = sub.mri_sub
                    self.mw.subject = sub

                elif subject_type == 'ga':
                    sub = CurrentGAGroup(name, self.mw)
                    self.mw.subject = sub

                elif subject_type == 'other':
                    sub = CurrentSub(name, self.mw)

                else:
                    break

                if not self.mw.get_setting('show_plots'):
                    close_all()

                # Print Subject Console Header
                print('=' * 60 + '\n', name + '\n')
                for func in selected_functions:
                    # Todo: Resolve Dependencies and Function-Order
                    # Wait for main-thread-function to finish
                    while self.is_plot_running:
                        time.sleep(1)
                    if not self.is_cancel_functions:
                        if self.mw.pd_funcs.loc[func, 'mayavi']:
                            self.is_plot_running = True
                            self.signals.pg_subfunc.emit((name, func))
                            # Mayavi-Plots need to be called in the main thread
                            self.signals.func_sig.emit({'func_name': func, 'sub': sub, 'main_win': self.mw})
                            self.signals.pgbar_n.emit(self.count)
                            self.count += 1
                        elif self.mw.pd_funcs.loc[func, 'matplotlib'] and self.mw.get_setting('show_plots'):
                            self.signals.pg_subfunc.emit((name, func))
                            # Matplotlib-Plots can be called without showing (backend: agg),
                            # but to be shown, they have to be called in the main thread
                            self.signals.func_sig.emit({'func_name': func, 'sub': sub, 'main_win': self.mw})
                            self.signals.pgbar_n.emit(self.count)
                            self.count += 1
                        else:
                            self.signals.pg_subfunc.emit((name, func))
                            func_from_def(func, sub, self.mw)
                            self.signals.pgbar_n.emit(self.count)
                            self.count += 1
                    else:
                        break
            else:
                break


class FunctionWorker(Worker):
    def __init__(self, function, obj, main_win):
        self.signals = FunctionWorkerSignals()
        super().__init__(func_from_def, self.signals, name=function, obj=obj, main_win=main_win)


class RunDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        # Initialize Attributes
        self.init_attributes()

        # Connect custom stdout and stderr to display-function
        sys.stdout.signal.text_written.connect(self.add_text)
        sys.stderr.signal.text_written.connect(self.add_error_text)
        # Handle tqdm-progress-bars
        sys.stderr.signal.text_updated.connect(self.progress_text)

        self.init_lists()
        self.init_ui()

        width, height = get_ratio_geometry(0.6)
        self.resize(width, height)
        self.show()

        self.start_thread()

    def init_attributes(self):
        # Initialize class-attributes (in method to be repeatable by self.restart)
        self.all_steps = list()
        self.all_objects = dict()
        self.current_all_funcs = dict()
        self.current_step = None
        self.current_object = None
        self.loaded_fsmri = None
        self.current_func = None

        self.errors = dict()
        self.prog_count = 0
        self.is_prog_text = False
        self.paused = False
        self.autoscroll = True

    def init_lists(self):
        # Make sure, every function is in sel_functions
        for func in [f for f in self.mw.pd_funcs.index if f not in self.mw.pr.sel_functions]:
            self.mw.pr.sel_functions[func] = 0

        # Lists of selected functions divided into object-types (MEEG, FSMRI, ...)
        self.sel_fsmri_funcs = [mf for mf in self.mw.fsmri_funcs.index if self.mw.pr.sel_functions[mf]]
        self.sel_meeg_funcs = [ff for ff in self.mw.meeg_funcs.index if self.mw.pr.sel_functions[ff]]
        self.sel_group_funcs = [gf for gf in self.mw.group_funcs.index if self.mw.pr.sel_functions[gf]]
        self.sel_other_funcs = [of for of in self.mw.other_funcs.index if self.mw.pr.sel_functions[of]]

        # Get a dict with all objects paired with their functions and their type-definition
        # Give all objects and functions in all_objects the status 1 (which means pending)
        if len(self.mw.pr.sel_fsmri) * len(self.sel_fsmri_funcs) != 0:
            for fsmri in self.mw.pr.sel_fsmri:
                self.all_objects[fsmri] = {'type': 'FSMRI',
                                           'functions': {x: 1 for x in self.sel_fsmri_funcs},
                                           'status': 1}
                for fsmri_func in self.sel_fsmri_funcs:
                    self.all_steps.append((fsmri, fsmri_func))

        if len(self.mw.pr.sel_meeg) * len(self.sel_meeg_funcs) != 0:
            for meeg in self.mw.pr.sel_meeg:
                self.all_objects[meeg] = {'type': 'MEEG',
                                          'functions': {x: 1 for x in self.sel_meeg_funcs},
                                          'status': 1}
                for meeg_func in self.sel_meeg_funcs:
                    self.all_steps.append((meeg, meeg_func))

        if len(self.mw.pr.sel_groups) * len(self.sel_group_funcs) != 0:
            for group in self.mw.pr.sel_groups:
                self.all_objects[group] = {'type': 'Group',
                                           'functions': {x: 1 for x in self.sel_group_funcs},
                                           'status': 1}
                for group_func in self.sel_group_funcs:
                    self.all_steps.append((group, group_func))

        if len(self.sel_other_funcs) != 0:
            # blank object-name for other functions
            self.all_objects[''] = {'type': 'Other',
                                    'functions': {x: 1 for x in self.sel_other_funcs},
                                    'status': 1}
            for other_func in self.sel_other_funcs:
                self.all_steps.append(('', other_func))

    def init_ui(self):
        layout = QVBoxLayout()

        view_layout = QGridLayout()
        view_layout.addWidget(QLabel('Objects: '), 0, 0)
        self.object_listview = QListView()
        self.object_model = RunModel(self.all_objects, mode='object')
        self.object_listview.setModel(self.object_model)
        self.object_listview.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        view_layout.addWidget(self.object_listview, 1, 0)

        view_layout.addWidget(QLabel('Functions: '), 0, 1)
        self.func_listview = QListView()
        self.func_model = RunModel(self.current_all_funcs, mode='func')
        self.func_listview.setModel(self.func_model)
        self.func_listview.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        view_layout.addWidget(self.func_listview, 1, 1)

        view_layout.addWidget(QLabel('Errors: '), 0, 2)
        self.error_widget = SimpleList(list())
        self.error_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        # Connect Signal from error_widget to function to enable inspecting the errors
        self.error_widget.currentChanged.connect(self.show_error)
        view_layout.addWidget(self.error_widget, 1, 2)

        layout.addLayout(view_layout)

        self.console_widget = QTextEdit()
        self.console_widget.setReadOnly(True)
        layout.addWidget(self.console_widget)

        self.pgbar = QProgressBar()
        self.pgbar.setValue(0)
        self.pgbar.setMaximum(len(self.all_steps))
        layout.addWidget(self.pgbar)

        bt_layout = QHBoxLayout()

        self.continue_bt = QPushButton('Continue')
        self.continue_bt.setFont(QFont('AnyStyle', 14))
        self.continue_bt.setIcon(self.mw.app.style().standardIcon(QStyle.SP_MediaPlay))
        self.continue_bt.clicked.connect(self.start_thread)
        bt_layout.addWidget(self.continue_bt)

        self.pause_bt = QPushButton('Pause')
        self.pause_bt.setFont(QFont('AnyStyle', 14))
        self.pause_bt.setIcon(self.mw.app.style().standardIcon(QStyle.SP_MediaPause))
        self.pause_bt.clicked.connect(self.pause_funcs)
        bt_layout.addWidget(self.pause_bt)

        self.restart_bt = QPushButton('Restart')
        self.restart_bt.setFont(QFont('AnyStyle', 14))
        self.restart_bt.setIcon(self.mw.app.style().standardIcon(QStyle.SP_BrowserReload))
        self.restart_bt.clicked.connect(self.restart)
        bt_layout.addWidget(self.restart_bt)

        self.autoscroll_bt = QPushButton('Auto-Scroll')
        self.autoscroll_bt.setCheckable(True)
        self.autoscroll_bt.setChecked(True)
        self.autoscroll_bt.setIcon(self.mw.app.style().standardIcon(QStyle.SP_DialogOkButton))
        self.autoscroll_bt.clicked.connect(self.toggle_autoscroll)
        bt_layout.addWidget(self.autoscroll_bt)

        self.close_bt = QPushButton('Close')
        self.close_bt.setFont(QFont('AnyStyle', 14))
        self.close_bt.setIcon(self.mw.app.style().standardIcon(QStyle.SP_MediaStop))
        self.close_bt.clicked.connect(self.close)
        bt_layout.addWidget(self.close_bt)
        layout.addLayout(bt_layout)

        self.setLayout(layout)

    def mark_current_items(self, status):
        # Mark current-items in listmodels with status
        self.all_objects[self.current_object.name]['status'] = status
        self.object_model.layoutChanged.emit()
        self.all_objects[self.current_object.name]['functions'][self.current_func] = status
        self.func_model.layoutChanged.emit()

    def start_thread(self):
        # Save all Main-Scripts in case of error
        self.mw.save_main()
        # Set paused to false
        self.paused = False
        # Enable/Disable Buttons
        self.continue_bt.setEnabled(False)
        self.pause_bt.setEnabled(True)
        self.restart_bt.setEnabled(False)
        self.close_bt.setEnabled(False)

        # Take first step of all_steps until there are no steps left
        if len(self.all_steps) > 0:
            # Getting information as encoded in init_lists
            self.current_step = self.all_steps.pop(0)
            object_name = self.current_step[0]
            self.current_type = self.all_objects[object_name]['type']
            # Load object if the preceding object is not the same
            if not self.current_object or self.current_object.name != object_name:
                # Print Headline for object
                self.add_html('<h1>object_name</h1><br>')

                if self.current_type == 'FSMRI':
                    self.current_object = CurrentMRISub(object_name, self.mw)
                    self.loaded_fsmri = self.current_object

                elif self.current_type == 'MEEG':
                    # Avoid reloading of same MRI-Subject for multiple files (with the same MRI-Subject)
                    if self.loaded_fsmri and self.loaded_fsmri.name == self.mw.pr.sub_dict[object_name]:
                        self.current_object = CurrentSub(object_name, self.mw, mri_sub=self.loaded_fsmri)
                    else:
                        self.current_object = CurrentSub(object_name, self.mw)
                    self.loaded_fsmri = self.current_object.mri_sub

                elif self.current_type == 'Group':
                    self.current_object = CurrentGAGroup(object_name, self.mw)

                elif self.current_type == 'Other':
                    self.current_object = BaseSub(object_name, self.mw)

                # Load functions for object into func_model (which displays functions in func_listview)
                self.current_all_funcs = self.all_objects[object_name]['functions']
                self.func_model._data = self.current_all_funcs
                self.func_model.layoutChanged.emit()

            self.current_func = self.current_step[1]

            # Mark current object and current function
            self.mark_current_items(2)

            # Print Headline for function
            self.add_html(f'<h2>{self.current_func}</h2><br>')

            if (self.mw.pd_funcs.loc[self.current_func, 'mayavi'] or self.mw.pd_funcs.loc[
                self.current_func, 'matplotlib']
                    and self.mw.get_setting('show_plots')):
                # Plot functions with interactive plots currently can't run in a separate thread
                func_from_def(self.current_func, self.current_object, self.mw)
            else:
                self.fworker = FunctionWorker(self.current_func, self.current_object, self.mw)
                self.fworker.signals.error.connect(self.thread_error)
                self.fworker.signals.finished.connect(self.thread_finished)
                self.mw.threadpool.start(self.fworker)

        else:
            self.console_widget.insertHtml('<b><big>Finished</big></b><br>')
            if self.autoscroll:
                self.console_widget.ensureCursorVisible()
            # Enable/Disable Buttons
            self.continue_bt.setEnabled(False)
            self.pause_bt.setEnabled(False)
            self.restart_bt.setEnabled(True)
            self.close_bt.setEnabled(True)

            if self.mw.get_setting('shutdown'):
                self.save_main()
                shutdown()

    def thread_finished(self):
        self.prog_count += 1
        self.pgbar.setValue(self.prog_count)
        self.mark_current_items(0)

        # Close all plots if not wanted
        if not self.mw.get_setting('show_plots'):
            close_all()

        if not self.paused:
            self.start_thread()
        else:
            self.console_widget.insertHtml('<b><big>Paused</big></b><br>')
            if self.autoscroll:
                self.console_widget.ensureCursorVisible()
            # Enable/Disable Buttons
            self.continue_bt.setEnabled(True)
            self.pause_bt.setEnabled(False)
            self.restart_bt.setEnabled(True)
            self.close_bt.setEnabled(True)

    def thread_error(self, err):
        error_cause = f'{self.current_object.name} <- {self.current_func}'
        self.errors[error_cause] = err
        # Update Error-Widget
        self.error_widget.replace_data(list(self.errors.keys()))

        self.thread_finished()

    def pause_funcs(self):
        self.paused = True
        self.console_widget.insertHtml('<br><b>Finishing last function...</big><br>')
        if self.autoscroll:
            self.console_widget.ensureCursorVisible()

    def restart(self):
        self.init_attributes()
        self.init_lists()

        # Clear Console-Widget
        self.console_widget.clear()

        # Redo References to display-widgets
        self.object_model._data = self.all_objects
        self.object_model.layoutChanged.emit()
        self.func_model._data = self.current_all_funcs
        self.func_model.layoutChanged.emit()
        self.error_widget.replace_data(self.errors)

        # Restart
        self.start_thread()

    def toggle_autoscroll(self, state):
        if state:
            self.autoscroll = True
        else:
            self.autoscroll = False

    def show_error(self, current, _):
        self.autoscroll = False
        self.autoscroll_bt.setChecked(False)
        self.console_widget.scrollToAnchor(self.errors[current][2])

    def add_text(self, text):
        self.is_prog_text = False
        self.console_widget.insertPlainText(text)
        if self.autoscroll:
            self.console_widget.ensureCursorVisible()

    def add_error_text(self, text):
        self.is_prog_text = False
        text = f'<font color="red">{text}</font>'
        self.console_widget.insertHtml(text)
        if self.autoscroll:
            self.console_widget.ensureCursorVisible()

    def add_html(self, text):
        self.is_prog_text = False
        self.console_widget.insertHtml(text)
        if self.autoscroll:
            self.console_widget.ensureCursorVisible()

    def progress_text(self, text):
        if self.is_prog_text:
            # Delete last line
            cursor = self.console_widget.textCursor()
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            self.console_widget.insertPlainText(text)
        else:
            self.is_prog_text = True
            self.console_widget.insertPlainText(text)

        if self.autoscroll:
            self.console_widget.ensureCursorVisible()
