import logging
import sys
import traceback

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
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['pgbar_n'] = self.signals.pgbar_n
        self.kwargs['pg_sub'] = self.signals.pg_sub
        self.kwargs['pg_func'] = self.signals.pg_func
        self.kwargs['pg_which_loop'] = self.signals.pg_which_loop
        self.kwargs['func_sig'] = self.signals.func_sig

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
            self.signals.error.emit((exctype, value, traceback.format_exc()))
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


def call_functions(main_win, pgbar_n, pg_sub, pg_func, pg_which_loop, func_sig):
    """
    Call activated functions in main_window, read function-parameters from functions_empty.csv
    :param main_win: Main-Window-Instance
    :param pgbar_n: Signal, which emits a tuple to show overall progress (current, max)
    :param pg_sub: Signal, which emitas a string to show current sub
    :param pg_func: Signal, which emits a string to show current executed function
    :param pg_which_loop: Signal, which emits a string to show RunDialog which files and funcs to display
    :param func_sig: Signal, which is used to emit strings for calling plot-functions outside the QThread
    """

    # Determine steps in progress for all selected subjects and functions
    mri_prog = len(main_win.pr.sel_mri_files) * len(main_win.sel_mri_funcs)
    file_prog = len(main_win.pr.sel_files) * len(main_win.sel_file_funcs)
    ga_prog = len(main_win.sel_ga_funcs)

    all_prog = mri_prog + file_prog + ga_prog
    count = 1

    # Check if any mri_subject_operation is selected and any mri-subject is selected
    if mri_prog > 0:
        pg_which_loop.emit('mri')
        for mri_subject in main_win.pr.sel_mri_files:
            if not main_win.cancel_functions:
                msub = CurrentMRISubject(mri_subject, main_win)
                # Print Subject Console Header
                print('=' * 60 + '\n', mri_subject)
                pg_sub.emit(mri_subject)
                for mri_func in main_win.sel_mri_funcs:
                    if not main_win.cancel_functions:
                        pg_func.emit(mri_func)
                        if main_win.pd_funcs.loc[mri_func]['QThreading']:
                            func_from_def(mri_func, msub, main_win)
                        else:
                            func_sig.emit({'func_name': mri_func, 'subject': subject, 'main_win': main_win})
                        pgbar_n.emit({'count': count, 'max': all_prog})
                        count += 1
                    else:
                        break
            else:
                break
    else:
        print('No MRI-Subject or MRI-Function selected')

    # Call the functions for selected Files
    # Todo: Account for call-order (idx, group-idx)
    if file_prog > 0:
        pg_which_loop.emit('file')
        for name in main_win.pr.sel_files:
            if not main_win.cancel_functions:
                pg_sub.emit(name)
                subject = CurrentSubject(name, main_win)
                main_win.subject = subject
                # Check preload-setting
                if main_win.settings.value('sub_preload', defaultValue=False) == 'true':
                    main_win.subject.preload_data()
                # Print Subject Console Header
                print(60 * '=' + '\n' + name)
                for func in main_win.sel_file_funcs:
                    if not main_win.cancel_functions:
                        pg_func.emit(func)
                        if main_win.pd_funcs.loc[func]['QThreading']:
                            func_from_def(func, subject, main_win)
                        else:
                            func_sig.emit({'func_name': func, 'subject': subject, 'main_win': main_win})
                        pgbar_n.emit({'count': count, 'max': all_prog})
                        count += 1
                    else:
                        break
            else:
                break

    else:
        print('No Subject or Function selected')

    # Call functions outside the subject-loop
    if ga_prog > 0:
        pg_which_loop.emit('ga')
        for func in main_win.sel_ga_funcs:
            if not main_win.cancel_functions:
                pg_func.emit(func)
                if main_win.pd_funcs.loc[func]['QThreading']:
                    func_from_def(func, None, main_win)
                else:
                    func_sig.emit({'func_name': func, 'subject': None, 'main_win': main_win})
                pgbar_n.emit({'count': count, 'max': all_prog})
                count += 1
            else:
                break
