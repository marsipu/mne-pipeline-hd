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
import time

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QTextCursor
from PyQt5.QtWidgets import QDesktopWidget, QDialog, QGridLayout, QListWidget, QListWidgetItem, QProgressBar, \
    QPushButton, QSizePolicy, \
    QTextEdit

from ..basic_functions.loading import CurrentGAGroup, CurrentMRISub, CurrentSub
from ..basic_functions.plot import close_all
from ..gui.dialogs import ErrorDialog
from ..gui.gui_utils import Worker, get_ratio_geometry


def get_arguments(arg_names, sub, main_win):
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
            keyword_arguments.update({'sub': sub})
        elif arg_name == 'mri_sub':
            keyword_arguments.update({'mri_sub': sub})
        elif arg_name == 'ga_group':
            keyword_arguments.update({'ga_group': sub})
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


def func_from_def(func_name, sub, main_win):
    # Get Package-Name, is only defined for custom-packages
    pkg_name = main_win.pd_funcs['pkg_name'][func_name]
    # Get module, has to specified in functions.csv as it is imported
    module_name = main_win.pd_funcs['module'][func_name]
    if module_name in main_win.all_modules['basic']:
        module = main_win.all_modules['basic'][module_name]
    elif module_name in main_win.all_modules['custom']:
        module = main_win.all_modules['custom'][pkg_name][module_name][0]
    else:
        raise ModuleNotFoundError(name=module_name)

    # Get arguments from function signature
    func = getattr(module, func_name)
    arg_names = list(inspect.signature(func).parameters)

    keyword_arguments = get_arguments(arg_names, sub, main_win)

    # Catch one error due to unexpected or missing keywords
    unexp_kw_pattern = r"(.*) got an unexpected keyword argument \'(.*)\'"
    miss_kw_pattern = r"(.*) missing 1 required positional argument: \'(.*)\'"
    try:
        # Call Function from specified module with arguments from unpacked list/dictionary
        getattr(module, func_name)(**keyword_arguments)
    except TypeError as te:
        match_unexp_kw = re.match(unexp_kw_pattern, str(te))
        match_miss_kw = re.match(miss_kw_pattern, str(te))
        if match_unexp_kw:
            keyword_arguments.pop(match_unexp_kw.group(2))
            logging.warning(f'Caught unexpected keyword \"{match_unexp_kw.group(2)}\" for {func_name}')
            getattr(module, func_name)(**keyword_arguments)
        elif match_miss_kw:
            add_kw_args = get_arguments([match_miss_kw.group(2)], sub, main_win)
            keyword_arguments.update(add_kw_args)
            logging.warning(f'Caught missing keyword \"{match_miss_kw.group(2)}\" for {func_name}')
            getattr(module, func_name)(**keyword_arguments)
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

    # Signals for call_functions
    # Returns an int for a progressbar
    pgbar_n = pyqtSignal(int)
    # Returns a tuple with strings about the current subject and function
    pg_subfunc = pyqtSignal(tuple)
    # Returns a string about the current loop (mri_subjects, files, grand_average)
    pg_which_loop = pyqtSignal(str)
    # Passes arguments into the main-thread for execution (important for functions with plot)
    func_sig = pyqtSignal(dict)


class FunctionWorker(Worker):
    def __init__(self, main_win):
        self.signals = FunctionWorkerSignals()
        super().__init__(self.call_functions, self.signals)

        self.mw = main_win
        self.count = 1

        # Signals received from main_win for canceling functions and
        self.mw.cancel_functions.connect(self.check_cancel_functions)
        self.mw.plot_running.connect(self.check_plot_running)
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
        if len(self.mw.pr.sel_mri_files) * len(self.mw.sel_mri_funcs) > 0:
            self.signals.pg_which_loop.emit('mri')
            self.subject_loop('mri')

        # Call the functions for selected Files
        if len(self.mw.pr.sel_files) * len(self.mw.sel_file_funcs) > 0:
            self.signals.pg_which_loop.emit('file')
            self.subject_loop('file')

        # Call functions outside the subject-loop for Grand-Average-Groups
        if len(self.mw.pr.sel_ga_groups) * len(self.mw.sel_ga_funcs) > 0:
            self.signals.pg_which_loop.emit('ga')
            self.subject_loop('ga')

        # Calls functions, which have no Sub
        elif len(self.mw.sel_other_funcs) > 0:
            self.signals.pg_which_loop.emit('other')
            self.subject_loop('other')

    def subject_loop(self, subject_type):
        if subject_type == 'mri':
            selected_subjects = self.mw.pr.sel_mri_files
            selected_functions = self.mw.sel_mri_funcs
        elif subject_type == 'file':
            selected_subjects = self.mw.pr.sel_files
            selected_functions = self.mw.sel_file_funcs
        elif subject_type == 'ga':
            selected_subjects = self.mw.pr.sel_ga_groups
            selected_functions = self.mw.sel_ga_funcs
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


class RunDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        width, height = get_ratio_geometry(0.6)
        self.setGeometry(0, 0, width, height)
        self.center()

        self.current_sub = None
        self.current_func = None
        self.prog_running = False

        self.init_ui()
        self.center()

    def init_ui(self):
        self.layout = QGridLayout()

        self.sub_listw = QListWidget()
        self.sub_listw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.layout.addWidget(self.sub_listw, 0, 0)
        self.func_listw = QListWidget()
        self.func_listw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.layout.addWidget(self.func_listw, 0, 1)
        self.console_widget = QTextEdit()
        self.console_widget.setReadOnly(True)
        self.layout.addWidget(self.console_widget, 1, 0, 1, 2)

        self.pgbar = QProgressBar()
        self.pgbar.setValue(0)
        self.layout.addWidget(self.pgbar, 2, 0, 1, 2)

        self.cancel_bt = QPushButton('Cancel')
        self.cancel_bt.setFont(QFont('AnyStyle', 14))
        self.cancel_bt.clicked.connect(self.cancel_funcs)
        self.layout.addWidget(self.cancel_bt, 3, 0)

        self.close_bt = QPushButton('Close')
        self.close_bt.setFont(QFont('AnyStyle', 14))
        self.close_bt.setEnabled(False)
        self.close_bt.clicked.connect(self.close)
        self.layout.addWidget(self.close_bt, 3, 1)

        self.setLayout(self.layout)

    def cancel_funcs(self):
        self.mw.cancel_functions.emit(True)
        self.console_widget.insertHtml('<b><big><center>---Finishing last function...---</center></big></b><br>')
        self.console_widget.ensureCursorVisible()

    def populate(self, mode):
        if mode == 'mri':
            self.populate_listw(self.mw.pr.sel_mri_files, self.mw.sel_mri_funcs)
        elif mode == 'file':
            self.populate_listw(self.mw.pr.sel_files, self.mw.sel_file_funcs)
        elif mode == 'ga':
            self.populate_listw(self.mw.pr.sel_ga_groups, self.mw.sel_ga_funcs)
        elif mode == 'other':
            self.populate_listw(['Other Functions'], self.mw.sel_other_funcs)

    def populate_listw(self, files, funcs):
        for file in files:
            item = QListWidgetItem(file)
            item.setFlags(Qt.ItemIsEnabled)
            self.sub_listw.addItem(item)
        for func in funcs:
            item = QListWidgetItem(func)
            item.setFlags(Qt.ItemIsEnabled)
            self.func_listw.addItem(item)

    def mark_subfunc(self, subfunc):
        if self.current_sub is not None:
            self.current_sub.setBackground(QColor('white'))
        try:
            self.current_sub = self.sub_listw.findItems(subfunc[0], Qt.MatchExactly)[0]
            self.current_sub.setBackground(QColor('green'))
        except IndexError:
            pass
        if self.current_func is not None:
            self.current_func.setBackground(QColor('white'))
        try:
            self.current_func = self.func_listw.findItems(subfunc[1], Qt.MatchExactly)[0]
            self.current_func.setBackground(QColor('green'))
        except IndexError:
            pass

    def clear_marks(self):
        if self.current_sub is not None:
            self.current_sub.setBackground(QColor('white'))
        if self.current_func is not None:
            self.current_func.setBackground(QColor('white'))

    def add_text(self, text):
        self.prog_running = False
        self.console_widget.insertPlainText(text)
        self.console_widget.ensureCursorVisible()

    def progress_text(self, text):
        if self.prog_running:
            # Delete last line
            cursor = self.console_widget.textCursor()
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            self.console_widget.insertPlainText(text)

        else:
            self.prog_running = True
            self.console_widget.insertPlainText(text)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def show_errors(self, err):
        ErrorDialog(err, self)
        self.pgbar.setValue(self.mw.all_prog)
        self.close_bt.setEnabled(True)
