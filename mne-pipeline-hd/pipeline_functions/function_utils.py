import matplotlib
from PyQt5.QtCore import QObject, pyqtSignal

from gui.qt_utils import Worker
from gui.subject_widgets import CurrentMRISubject, CurrentSubject


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
        self.kwargs = kwargs
        # Add the callback to our kwargs
        self.kwargs['signals'] = {'pgbar_n': self.signal_class.pgbar_n,
                                  'pg_sub': self.signal_class.pg_sub,
                                  'pg_func': self.signal_class.pg_func,
                                  'pg_which_loop': self.signal_class.pg_which_loop,
                                  'func_sig': self.signal_class.func_sig}
        super().__init__(fn, self.signal_class, *args, **kwargs)


def func_from_def(func_name, subject, main_win):

    # Get module, has to specified in functions.csv as it is imported
    module_name = main_win.pd_funcs['module'][func_name]
    module = main_win.all_modules[module_name]

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
                    if main_win.pd_funcs['Mayavi'][func]:
                        signals['pg_func'].emit(func)
                        # Mayavi-Plots need to be called in the main thread
                        signals['func_sig'].emit({'func_name': func, 'subject': subject, 'main_win': main_win})
                        signals['pgbar_n'].emit(count)
                        count += 1
                    elif main_win.pd_funcs['Matplotlib'][func] and main_win.pr.parameters['show_plots']:
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
    if not main_win.pr.parameters['show_plots']:
        matplotlib.use('agg')

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
