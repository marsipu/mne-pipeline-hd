import logging
import sys
import traceback

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from basic_functions import io, operations, plot
from custom_functions import kristin, melofix, pinprick
from pipeline_functions.subjects import CurrentMRISubject, CurrentSubject

# Avoid deletion of import with "Customize Imports" from PyCharm
all_func_modules = [io, operations, plot, kristin, melofix, pinprick]


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
    result = pyqtSignal(object)
    progress_n = pyqtSignal(tuple)
    progress_s = pyqtSignal(str)


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
        self.kwargs['progress_n'] = self.signals.progress_n
        self.kwargs['progress_s'] = self.signals.progress_s

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
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


def func_from_def(func_name, pd_funcs, subject, project, parameters, main_win):
    module_name = pd_funcs['module'][func_name]

    # Read Listitems from Strings from functions.csv
    subarg_string = pd_funcs['subject_args'][func_name]
    # nan (float) returned for empty csv-cells
    if type(subarg_string) is not float:
        subarg_names = subarg_string.split(',')
    else:
        subarg_names = []
    proarg_string = pd_funcs['project_args'][func_name]
    if type(proarg_string) is not float:
        proarg_names = proarg_string.split(',')
    else:
        proarg_names = []
    addarg_string = pd_funcs['additional_args'][func_name]
    if type(addarg_string) is not float:
        addarg_names = addarg_string.split(',')
    else:
        addarg_names = []

    # Get attributes from Subject/Project-Class
    if subject:
        subject_attributes = vars(subject)
    else:
        subject_attributes = {}
    project_attributes = vars(project)

    keyword_arguments = dict()

    for subarg_name in subarg_names:
        # Remove trailing spaces
        subarg_name = subarg_name.replace(' ', '')
        if subarg_name == 'mw':
            keyword_arguments.update({'mw': main_win})
        elif subarg_name == 'pr':
            keyword_arguments.update({'pr': project})
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
            keyword_arguments.update({addarg_name: parameters[addarg_name]})
        except KeyError:
            print(addarg_name + ' not in Parameters')

    # Get module, has to specified in functions.csv as it is imported
    module = globals()[module_name]
    # Call Function from specified module with arguments from unpacked list/dictionary
    return_value = getattr(module, func_name)(**keyword_arguments)

    return return_value


def call_functions(main_window, progress_n, progress_s):
    """
    Call activated functions in main_window, read function-parameters from functions_empty.csv
    :param main_window: Main-Window-Instance
    :param progress_n: Signal, which emits a tuple to show overall progress (current, max)
    :param progress_s: Signal, which emits a string to show current executed function

    """
    mw = main_window

    # Call the functions for selected MRI-subjects
    mri_subjects = mw.pr.sel_mri_files
    mri_ops = mw.pd_funcs[mw.pd_funcs['group'] == 'mri_subject_operations'].T
    sel_mri_funcs = [mf for mf in mri_ops if mw.func_dict[mf]]

    # Lists for File-Funcs
    sel_files = mw.pr.sel_files
    file_funcs = mw.pd_funcs[mw.pd_funcs['group'] != 'mri_subject_operations']
    file_funcs = file_funcs[file_funcs['subject_loop'] == True].T
    sel_file_funcs = [ff for ff in file_funcs if mw.func_dict[ff]]

    grand_avg_funcs = mw.pd_funcs[mw.pd_funcs['subject_loop'] == False].T
    sel_grand_avg_funcs = [gf for gf in grand_avg_funcs if mw.func_dict[gf]]

    all_prog = len(mri_subjects) * len(sel_mri_funcs) + len(sel_files) * len(sel_file_funcs) + len(sel_grand_avg_funcs)
    count = 1
    # Check if any mri_subject_operation is selected and any mri-subject is selected
    if len(mri_subjects) * len(sel_mri_funcs) > 0:
        print(f'Selected {len(mri_subjects)} MRI-Subjects:')
        for i in mri_subjects:
            print(i)
        for mri_subject in mri_subjects:
            if not mw.cancel_functions:
                print('=' * 60 + '\n', mri_subject)
                prog = round((mri_subjects.index(mri_subject)) / len(mri_subjects) * 100, 2)
                print(f'Progress: {prog} %')

                msub = CurrentMRISubject(mri_subject, mw)
                for mri_func in sel_mri_funcs:
                    if not mw.cancel_functions:
                        progress_s.emit(f'{mri_subject}: {mri_func}')
                        func_from_def(mri_func, mw.pd_funcs, msub, mw.pr, mw.pr.parameters, mw)
                        progress_n.emit((count, all_prog))
                        count += 1
                    else:
                        break
            else:
                break
    else:
        print('No MRI-Subject or MRI-Function selected')

    # Call the functions for selected Files
    # Todo: Account for call-order (idx, group-idx)
    if len(sel_files) * len(sel_file_funcs) > 0:
        print(f'Selected {len(sel_files)} Subjects:')
        for f in sel_files:
            print(f)
        for name in sel_files:
            if not mw.cancel_functions:
                mw.subject = CurrentSubject(name, mw)
                # Todo: Enable continuation of program after correction of missing Subject-Assignments
                if mw.subject.dict_error:
                    break
                else:
                    # Check preload-setting
                    if mw.settings.value('sub_preload', defaultValue=False) == 'true':
                        mw.subject.preload_data()

                    # Print Subject Console Header
                    print(60 * '=' + '\n' + name)
                    prog = round((sel_files.index(name)) / len(sel_files) * 100, 2)
                    print(f'Progress: {prog} %')

                    for func in sel_file_funcs:
                        if not mw.cancel_functions:
                            progress_s.emit(f'{name}: {func}')
                            func_from_def(func, mw.pd_funcs, mw.subject, mw.pr, mw.pr.parameters, mw)
                            progress_n.emit((count, all_prog))
                            count += 1
                        else:
                            break
            else:
                break

    else:
        print('No Subject or Function selected')

    # Call functions outside the subject-loop
    for func in sel_grand_avg_funcs:
        if not mw.cancel_functions:
            progress_n.emit((count, all_prog))
            progress_s.emit(f'{func}')
            func_from_def(func, mw.pd_funcs, mw.subject, mw.pr, mw.pr.parameters, mw)
            count += 1
        else:
            break
