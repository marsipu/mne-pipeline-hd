from basic_functions import io, operations, plot
from custom_functions import kristin, melofix, pinprick
from pipeline_functions.subjects import CurrentMRISubject, CurrentSubject

# Avoid deletion of import with "Customize Imports" from PyCharm
all_func_modules = [io, operations, plot, kristin, melofix, pinprick]


def func_from_def(func_name, pd_funcs, subject, project, parameters):
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
    subject_attributes = vars(subject)
    project_attributes = vars(project)

    keyword_arguments = dict()

    for subarg_name in subarg_names:
        # Remove trailing spaces
        subarg_name = subarg_name.replace(' ', '')
        keyword_arguments.update({subarg_name: subject_attributes[subarg_name]})
    for proarg_name in proarg_names:
        # Remove trailing spaces
        proarg_name = proarg_name.replace(' ', '')
        keyword_arguments.update({proarg_name: project_attributes[proarg_name]})
    for addarg_name in addarg_names:
        # Remove trailing spaces
        addarg_name = addarg_name.replace(' ', '')
        keyword_arguments.update({addarg_name: parameters[addarg_name]})

    # Get module, has to specified in functions.csv as it is imported
    module = globals()[module_name]
    # Call Function from specified module with arguments from unpacked list/dictionary
    return_value = getattr(module, func_name)(**keyword_arguments)

    return return_value


def call_functions(main_window):
    """
    Call activated functions in main_window, read function-parameters from functions_empty.csv
    :param main_window:
    :return:
    """
    mw = main_window

    # Call the functions for selected MRI-subjects
    mri_subjects = mw.pr.sel_mri_files
    mri_ops = mw.pd_funcs[mw.pd_funcs['group'] == 'mri_subject_operations'].T
    # Check if any mri_subject_operation is selected
    if any([mw.func_dict[mri_func] for mri_func in mri_ops]):
        # Check if mri-subjects are selected
        if len(mri_subjects) > 0:
            print(f'Selected {len(mri_subjects)} MRI-Subjects:')
            for i in mri_subjects:
                print(i)

            # Show ProgressBar
            # mri_prog = QDialog(mw)
            # mri_prog_layout = QVBoxLayout()
            # mri_prog_label = QLabel('MRI-Subjects are processed, watch Terminal for more information')
            # mri_prog_layout.addWidget(mri_prog_label)
            # mri_pgbar = QProgressBar()
            # mri_pgbar.setMaximum(len(mri_subjects))
            # mri_prog_layout.addWidget(mri_pgbar)
            # mri_prog.setLayout(mri_prog_layout)
            # mri_prog.open()
            count = 1
            for mri_subject in mri_subjects:
                print('=' * 60 + '\n', mri_subject)
                prog = round((mri_subjects.index(mri_subject)) / len(mri_subjects) * 100, 2)
                print(f'Progress: {prog} %')

                msub = CurrentMRISubject(mri_subject, mw)
                for mri_func in mri_ops:
                    if mw.func_dict[mri_func]:
                        func_from_def(mri_func, mw.pd_funcs, msub, mw.pr, mw.pr.parameters)

                # mri_pgbar.setValue(count)
                count += 1
            # mri_prog.close()
        else:
            print('No MRI-Subject selected')

    # Call the functions for selected Files
    # Todo: Account for call-order (idx, group-idx)
    sel_files = mw.pr.sel_files
    file_ops = mw.pd_funcs[mw.pd_funcs['group'] != 'mri_subject_operations'].T

    if len(mw.pr.all_files) == 0:
        print('No files found!\nAdd some Files with "AddFiles" from the Input-Menu')
    else:
        print(f'Selected {len(sel_files)} Subjects:')
        for f in sel_files:
            print(f)

        # Todo: Progressbar freezes and doesn't show the progress
        # Show ProgressBar
        # file_prog = QDialog(mw)
        # file_prog_layout = QVBoxLayout()
        # file_prog_label = QLabel('Files are processed, watch Terminal for more information')
        # file_prog_layout.addWidget(file_prog_label)
        # file_pgbar = QProgressBar()
        # file_pgbar.setMaximum(len(sel_files))
        # file_prog_layout.addWidget(file_pgbar)
        # file_prog.setLayout(file_prog_layout)
        # file_prog.open()

        count = 1

        for name in sel_files:
            mw.subject = CurrentSubject(name, mw)
            # Todo: Enable continuation of program after correction of missing Subject-Assignments
            if mw.subject.dict_error:
                break
            else:
                # Check preload-setting
                if mw.settings.value('sub_preload', defaultValue=False):
                    mw.subject.preload_data()

                # Print Subject Console Header
                print(60 * '=' + '\n' + name)
                prog = round((sel_files.index(name)) / len(sel_files) * 100, 2)
                print(f'Progress: {prog} %')

                for file_func in file_ops:
                    if mw.func_dict[file_func]:
                        func_from_def(file_func, mw.pd_funcs, mw.subject, mw.pr, mw.pr.parameters)
                # file_pgbar.setValue(count)
                count += 1
        # file_prog.close()
