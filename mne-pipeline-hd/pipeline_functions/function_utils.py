import logging
import sys
import traceback

import matplotlib
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from basic_functions import loading, operations, plot
from custom_functions import kristin, melofix, pinprick
from pipeline_functions.subjects import CurrentMRISubject, CurrentSubject

# Avoid deletion of import with "Customize Imports" from PyCharm
all_func_modules = [loading, operations, plot, kristin, melofix, pinprick]


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    Supported signals are:
    finished
        No data
    error
        `tuple` (exctype, value, traceback.format_exc() )
    result
        `object` data returned from processing, anything
    progress
        `int` indicating % progress


    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    pgbar_n = pyqtSignal(dict)
    pg_sub = pyqtSignal(str)
    pg_func = pyqtSignal(str)
    pg_which_loop = pyqtSignal(str)
    func_sig = pyqtSignal(dict)


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['signals'] = {'pgbar_n': self.signals.pgbar_n,
                                  'pg_sub': self.signals.pg_sub,
                                  'pg_func': self.signals.pg_func,
                                  'pg_which_loop': self.signals.pg_which_loop,
                                  'func_sig': self.signals.func_sig}

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            logging.error('Ups, something happened:')
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc(limit=-10)))
        finally:
            self.signals.finished.emit()  # Done


def func_from_def(func_name, subject, main_win):
    module_name = main_win.pd_funcs['module'][func_name]

    # Read Listitems from Strings from functions.csv
    subarg_string = main_win.pd_funcs['subject_args'][func_name]
    # nan (float) returned for empty csv-cells
    if type(subarg_string) is not float:
        subarg_names = subarg_string.split(',')
    else:
        subarg_names = []
    proarg_string = main_win.pd_funcs['project_args'][func_name]
    if type(proarg_string) is not float:
        proarg_names = proarg_string.split(',')
    else:
        proarg_names = []
    addarg_string = main_win.pd_funcs['additional_args'][func_name]
    if type(addarg_string) is not float:
        addarg_names = addarg_string.split(',')
    else:
        addarg_names = []

    # Get attributes from Subject/Project-Class
    if subject:
        subject_attributes = vars(subject)
    else:
        subject_attributes = {}
    project_attributes = vars(main_win.pr)

    keyword_arguments = dict()

    for subarg_name in subarg_names:
        # Remove trailing spaces
        subarg_name = subarg_name.replace(' ', '')
        if subarg_name == 'mw':
            keyword_arguments.update({'mw': main_win})
        elif subarg_name == 'pr':
            keyword_arguments.update({'pr': main_win.pr})
        else:
            try:
                keyword_arguments.update({subarg_name: subject_attributes[subarg_name]})
            except KeyError:
                print(subarg_name + ' not as CurrentSubject-Class-Attributes')
    for proarg_name in proarg_names:
        # Remove trailing spaces
        proarg_name = proarg_name.replace(' ', '')
        try:
            keyword_arguments.update({proarg_name: project_attributes[proarg_name]})
        except KeyError:
            print(proarg_name + ' not in Project-Class-Attributes')
    for addarg_name in addarg_names:
        # Remove trailing spaces
        addarg_name = addarg_name.replace(' ', '')
        try:
            keyword_arguments.update({addarg_name: main_win.pr.parameters[addarg_name]})
        except KeyError:
            print(addarg_name + ' not in Parameters')

    # Get module, has to specified in functions.csv as it is imported
    module = globals()[module_name]
    # Call Function from specified module with arguments from unpacked list/dictionary
    return_value = getattr(module, func_name)(**keyword_arguments)

    return return_value


def subject_loop(main_win, signals, subject_type, selected_subjects, selected_functions, count, all_prog):
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
                    if main_win.pd_funcs['Mayavi'][func]:
                        signals['pg_func'].emit(func)
                        # Mayavi-Plots need to be called in the main thread
                        signals['func_sig'].emit({'func_name': func, 'subject': subject, 'main_win': main_win})
                        signals['pgbar_n'].emit({'count': count, 'max': all_prog})
                        count += 1
                    elif main_win.pd_funcs['Matplotlib'][func] and main_win.pr.parameters['show_plots']:
                        signals['pg_func'].emit(func)
                        # Matplotlib-Plots can be called without showing (backend: agg),
                        # but to be shown, they have to be called in the main thread
                        signals['func_sig'].emit({'func_name': func, 'subject': subject, 'main_win': main_win})
                        signals['pgbar_n'].emit({'count': count, 'max': all_prog})
                        count += 1
                    else:
                        signals['pg_func'].emit(func)
                        func_from_def(func, subject, main_win)
                        signals['pgbar_n'].emit({'count': count, 'max': all_prog})
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

    # Determine steps in progress for all selected subjects and functions
    all_prog = (len(main_win.pr.sel_mri_files) * len(main_win.sel_mri_funcs) +
                len(main_win.pr.sel_files) * len(main_win.sel_file_funcs) +
                len(main_win.sel_ga_funcs))

    count = 1

    # Set non-interactive backend for plots to be runnable in QThread
    if not main_win.pr.parameters['show_plots']:
        matplotlib.use('agg')

    # Check if any mri-subject is selected
    if len(main_win.pr.sel_mri_files) * len(main_win.sel_mri_funcs) > 0:
        signals['pg_which_loop'].emit('mri')
        count = subject_loop(main_win, signals, 'mri', main_win.pr.sel_mri_files,
                             main_win.sel_mri_funcs, count, all_prog)
    else:
        print('No MRI-Subject or MRI-Function selected')

    # Call the functions for selected Files
    if len(main_win.pr.sel_files) > 0:
        signals['pg_which_loop'].emit('file')
        count = subject_loop(main_win, signals, 'file', main_win.pr.sel_files,
                             main_win.sel_file_funcs, count, all_prog)
    else:
        print('No Subject selected')

    # Call functions outside the subject-loop
    if len(main_win.sel_ga_funcs) > 0:
        signals['pg_which_loop'].emit('ga')
        subject_loop(main_win, signals, 'ga', ['Grand-Average'],
                     main_win.sel_ga_funcs, count, all_prog)
    else:
        print('No Grand-Average-Function selected')
