"""
subject_organisation by Martin Schulz
martin.schulz@stud.uni-heidelberg.de
"""
import os
import re
import shutil
from functools import partial
from os.path import isdir, isfile, join
from pathlib import Path

import mne
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAbstractItemView, QCheckBox, QComboBox, QDialog, QDockWidget, QFileDialog, QGridLayout, \
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton, \
    QStyle, QTabWidget, QVBoxLayout, QWidget
from matplotlib import pyplot as plt

from basic_functions import io
from pipeline_functions import utilities as ut


class CurrentFile:
    """ Class for File-Data in File-Loop"""

    def __init__(self, name, main_window):
        self.name = name
        self.mw = main_window
        self.pr = main_window.pr

        self.save_dir = join(self.pr.data_path, name)

        try:
            self.ermsub = self.pr.erm_dict[name]
        except KeyError as k:
            print(f'No erm_measurement assigned for {k}')
            dialog = SubDictDialog(self.mw, 'erm')
            dialog.list_widget1.setCurrentItem(dialog.list_widget1.findItems(str(k), Qt.MatchExactly)[0])
            dialog.finished.connect(self.update_file_data())
        try:
            self.subtomri = self.pr.sub_dict[name]
        except KeyError as k:
            print(f'No mri_subject assigned to {k}')
            SubDictDialog(self.mw, 'mri')
        try:
            self.bad_channels = self.pr.bad_channels_dict[name]
        except KeyError as k:
            print(f'No bad channels for {k}')
            BadChannelsSelect(self.mw)

    # Todo: Better solution for Current-File call and update together with function-call
    def update_file_data(self):
        self.ermsub = self.pr.erm_dict[self.name]
        self.subtomri = self.pr.sub_dict[self.name]
        self.bad_channels = self.pr.bad_channels_dict[self.name]


def file_selection(which_file, all_files):
    if which_file == '':
        return [], []
    else:
        # Turn string input into according sub_list-Index
        try:
            if 'all' in which_file:
                if ',' in which_file:
                    splits = which_file.split(',')
                    rm = []
                    run = []
                    for sp in splits:
                        if '!' in sp and '-' in sp:
                            x, y = sp.split('-')
                            x = x[1:]
                            for n in range(int(x) - 1, int(y)):
                                rm.append(n)
                        elif '!' in sp:
                            rm.append(int(sp[1:]) - 1)
                        elif 'all' in sp:
                            for i in range(0, len(all_files)):
                                run.append(i)
                    for r in rm:
                        if r in run:
                            run.remove(r)
                else:
                    run = [x for x in range(0, len(all_files))]

            elif ',' in which_file and '-' in which_file:
                z = which_file.split(',')
                run = []
                rm = []
                for i in z:
                    if '-' in i and '!' not in i:
                        x, y = i.split('-')
                        for n in range(int(x) - 1, int(y)):
                            run.append(n)
                    elif '!' not in i:
                        run.append(int(i) - 1)
                    elif '!' in i and '-' in i:
                        x, y = i.split('-')
                        x = x[1:]
                        for n in range(int(x) - 1, int(y)):
                            rm.append(n)
                    elif '!' in i:
                        rm.append(int(i[1:]) - 1)

                for r in rm:
                    if r in run:
                        run.remove(r)

            elif '-' in which_file and ',' not in which_file:
                x, y = which_file.split('-')
                run = [x for x in range(int(x) - 1, int(y))]

            elif ',' in which_file and '-' not in which_file:
                splits = which_file.split(',')
                rm = []
                run = []
                for sp in splits:
                    if '!' in sp:
                        rm.append(int(sp) - 1)
                    else:
                        run.append(int(sp) - 1)
                if len(rm) > 0:
                    for r in rm:
                        run.remove(r)

            else:
                if len(all_files) < int(which_file) or int(which_file) <= 0:
                    run = []
                else:
                    run = [int(which_file) - 1]

            files = [x for (i, x) in enumerate(all_files) if i in run]

            return files, run

        except ValueError:
            print(f'{which_file} is not working')
            return [], []


def update_sub_ist(qlist, files):
    qlist.clear()
    for idx, file in enumerate(files):
        idx += 1  # Let index start with 1
        item = QListWidgetItem(f'{idx}: {file}')
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        qlist.addItem(item)


class SubjectDock(QDockWidget):
    def __init__(self, main_win):
        super().__init__('Subject-Selection', main_win)
        self.mw = main_win
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.init_ui()
        self.update_subjects_list()
        self.update_mri_subjects_list()

    def init_ui(self):
        self.main_widget = QWidget(self)
        self.layout = QVBoxLayout()
        self.tab_widget = QTabWidget(self)

        idx_example = "Examples:\n" \
                      "'5' (One File)\n" \
                      "'1,7,28' (Several Files)\n" \
                      "'1-5' (From File x to File y)\n" \
                      "'1-4,7,20-26' (The last two combined)\n" \
                      "'1-20,!4-6' (1-20 except 4-6)\n" \
                      "'all' (All files in file_list.py)\n" \
                      "'all,!4-6' (All files except 4-6)"

        # Subjects-List + Index-Line-Edit
        self.sub_widget = QWidget(self)
        self.sub_layout = QVBoxLayout()
        self.sub_listw = QListWidget(self)
        self.sub_listw.itemChanged.connect(self.get_sub_selection)
        self.sub_layout.addWidget(self.sub_listw)

        self.sub_ledit = QLineEdit(self)
        self.sub_ledit.setPlaceholderText('Subject-Index')
        self.sub_ledit.textEdited.connect(self.update_sub_selection)
        self.sub_ledit.setToolTip(idx_example)
        self.sub_ledit_layout = QHBoxLayout()
        self.sub_ledit_layout.addWidget(self.sub_ledit)
        # self.sub_clear_bt = QPushButton(icon=QIcon(':/abort_icon.svg'))
        self.sub_clear_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.sub_clear_bt.clicked.connect(self.sub_clear_all)
        self.sub_ledit_layout.addWidget(self.sub_clear_bt)

        self.sub_layout.addLayout(self.sub_ledit_layout)
        self.sub_widget.setLayout(self.sub_layout)

        self.tab_widget.addTab(self.sub_widget, 'Subjects')

        # MRI-Subjects-List + Index-Line-Edit
        self.mri_widget = QWidget(self)
        self.mri_layout = QVBoxLayout()
        self.mri_listw = QListWidget(self)
        self.mri_listw.itemChanged.connect(self.get_mri_selection)
        self.mri_layout.addWidget(self.mri_listw)

        self.mri_ledit = QLineEdit(self)
        self.mri_ledit.setPlaceholderText('MRI-Subject-Index')
        self.mri_ledit.textEdited.connect(self.update_mri_selection)
        self.mri_ledit.setToolTip(idx_example)
        self.mri_ledit_layout = QHBoxLayout()
        self.mri_ledit_layout.addWidget(self.mri_ledit)
        self.mri_clear_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_DialogCancelButton))
        # self.mri_clear_bt = QPushButton(icon=QIcon(':/abort_icon.svg'))
        self.mri_clear_bt.clicked.connect(self.mri_clear_all)
        self.mri_ledit_layout.addWidget(self.mri_clear_bt)

        self.mri_layout.addLayout(self.mri_ledit_layout)
        self.mri_widget.setLayout(self.mri_layout)

        self.tab_widget.addTab(self.mri_widget, 'MRI-Subjects')

        self.layout.addWidget(self.tab_widget)
        self.main_widget.setLayout(self.layout)
        self.setWidget(self.main_widget)

    def update_subjects_list(self):
        qlist = self.sub_listw
        files = read_files(self.mw.pr.file_list_path)
        update_sub_ist(qlist, files)

    def update_mri_subjects_list(self):
        qlist = self.mri_listw
        files = read_files(self.mw.pr.mri_sub_list_path)
        # Also get all freesurfe-directories from Freesurfer-Folder (maybe user added some manually)
        existing_dirs = get_existing_mri_subjects(self.mw.pr.subjects_dir)
        for edir in existing_dirs:
            if edir not in files:
                files.append(edir)
                write_file_list(edir, self.mw.pr.mri_sub_list_path)
        update_sub_ist(qlist, files)
        self.mw.pr.update_sub_lists()

    def get_sub_selection(self):
        sel_files = []
        for idx in range(self.sub_listw.count()):
            item = self.sub_listw.item(idx)
            if item.checkState() == Qt.Checked:
                # Index in front of name has to be deleted Todo: can be done bette (maybe QTableWidget?)
                sel_files.append(item.text()[len(str(idx + 1)) + 2:])
        self.mw.pr.sel_files = sel_files

    def get_mri_selection(self):
        sel_mri = []
        for idx in range(self.mri_listw.count()):
            item = self.mri_listw.item(idx)
            if item.checkState() == Qt.Checked:
                # Index in front of name has to be deleted Todo: can be done bette (maybe QTableWidget?)
                sel_mri.append(item.text()[len(str(idx + 1)) + 2:])
        self.mw.pr.sel_mri_files = sel_mri

    def update_sub_selection(self):
        which_file = self.sub_ledit.text()
        self.mw.pr.sel_files, idxs = file_selection(which_file, self.mw.pr.all_files)
        if len(idxs) > 0:
            # Clear all check-states
            self.sub_clear_all()
            for idx in idxs:
                self.sub_listw.item(idx).setCheckState(Qt.Checked)
        else:
            pass

    def update_mri_selection(self):
        which_file = self.mri_sub_ledit.text()
        self.mw.pr.sel_mri_files, idxs = file_selection(which_file, self.mw.pr.all_mri_subjects)

    def sub_clear_all(self):
        for idx in range(self.sub_listw.count()):
            self.sub_listw.item(idx).setCheckState(Qt.Unchecked)

    def mri_clear_all(self):
        for idx in range(self.mri_listw.count()):
            self.mri_listw.item(idx).setCheckState(Qt.Unchecked)

    def closeEvent(self, event):
        self.mw.pr.update_sub_lists()
        event.accept()


def move_file(forig, fdest):
    parent_dir = Path(fdest).parent
    # Copy sub_files to destination
    if not isfile(fdest):
        os.makedirs(parent_dir, exist_ok=True)
        print(f'Copying File from {forig}...')
        shutil.copy2(forig, fdest)
        print(f'Finished Copying to {fdest}')
    else:
        print(f'{fdest} already exists')
        pass


def write_file_list(fname, file_list_path):
    if not isfile(file_list_path):
        with open(file_list_path, 'w') as el1:
            el1.write(fname + '\n')
        print(f'{fname} was automatically added')
    else:
        with open(file_list_path, 'a') as sl2:
            sl2.write(fname + '\n')
        print(f'{fname} was automatically added')


def read_files(file_list_path):
    file_list = []
    file_name = Path(file_list_path).name
    try:
        with open(file_list_path, 'r') as sl:
            for line in sl:
                current_place = line[:-1]
                file_list.append(current_place)

    except FileNotFoundError:
        print(f'{file_name} not yet created')
        pass

    return file_list


# Todo: Enable Drag&Drop
# Todo: RegExp-Wizard
class AddFiles(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QVBoxLayout()

        self.files = list()
        self.paths = dict()
        self.file_types = dict()

        self.init_ui()
        self.setLayout(self.layout)
        self.open()

    def init_ui(self):
        # Input Buttons
        files_bt = QPushButton('File-Import', self)
        files_bt.clicked.connect(self.get_files_path)
        folder_bt = QPushButton('Folder-Import', self)
        folder_bt.clicked.connect(self.get_folder_path)
        input_bt_layout = QHBoxLayout()
        input_bt_layout.addWidget(files_bt)
        input_bt_layout.addWidget(folder_bt)
        self.layout.addLayout(input_bt_layout)

        list_label = QLabel('These .fif-Files can be imported \n'
                            '(the empty-room-measurements should appear here too \n'
                            ' and will be sorted, if name contains e.g. "empty", "leer", ...)', self)
        self.layout.addWidget(list_label)
        self.list_widget = QListWidget(self)
        self.list_widget.itemChanged.connect(self.item_renamed)
        self.layout.addWidget(self.list_widget)
        self.pgbar = QProgressBar(self)
        self.pgbar.setMinimum(0)
        self.layout.addWidget(self.pgbar)

        main_bt_layout = QHBoxLayout()
        import_bt = QPushButton('Import', self)
        import_bt.clicked.connect(self.add_files)
        main_bt_layout.addWidget(import_bt)
        rename_bt = QPushButton('Rename File', self)
        rename_bt.clicked.connect(self.rename_item)
        main_bt_layout.addWidget(rename_bt)
        delete_bt = QPushButton('Delete File', self)
        delete_bt.clicked.connect(self.delete_item)
        main_bt_layout.addWidget(delete_bt)
        ok_bt = QPushButton('Close', self)
        ok_bt.clicked.connect(self.close)
        main_bt_layout.addWidget(ok_bt)
        self.layout.addLayout(main_bt_layout)

    def populate_list_widget(self):
        # List with checkable names
        self.list_widget.clear()
        self.list_widget.addItems(self.files)

        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)

    def delete_item(self):
        i = self.list_widget.currentRow()
        if i >= 0:  # Assert that an item is selected
            name = self.list_widget.item(i).text()
            self.list_widget.takeItem(i)
            self.files.remove(name)

    # Todo: Double-Clicking renaming not working
    def rename_item(self):
        r = self.list_widget.currentRow()
        item = self.list_widget.currentItem()
        if r >= 0:
            self.old_name = self.list_widget.item(r).text()
            self.list_widget.editItem(item)

    def item_renamed(self):
        if self.list_widget.currentItem():
            new_name = self.list_widget.currentItem().text()
            repl_ind = self.files.index(self.old_name)
            self.files[repl_ind] = new_name
            self.paths[new_name] = self.paths[self.old_name]
            self.paths.pop(self.old_name)
            self.file_types[new_name] = self.file_types[self.old_name]
            self.file_types.pop(self.old_name)
        else:
            pass

    def get_files_path(self):
        files_list = QFileDialog.getOpenFileNames(self, 'Choose raw-file/s to import', filter='fif-Files(*.fif)')[0]
        if len(files_list) > 0:
            for file_path in files_list:
                p = Path(file_path)
                file = p.stem
                if file not in self.files:
                    self.files.append(file)
                if file not in self.paths:
                    self.paths.update({file: file_path})
                if file not in self.file_types:
                    self.file_types.update({file: p.suffix})
            self.populate_list_widget()
        else:
            pass

    def get_folder_path(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'Choose a folder to import your raw-Files from (including '
                                                             'subfolders)')
        if folder_path != '':
            # create a list of file and sub directories
            # names in the given directory
            list_of_file = os.walk(folder_path)
            # Iterate over all the entries
            for dirpath, dirnames, filenames in list_of_file:
                for full_file in filenames:
                    match = re.match(r'(.+)(\.fif)', full_file)
                    if match and len(match.group()) == len(full_file):
                        file = match.group(1)
                        if not any(x in full_file for x in ['-eve.', '-epo.', '-ica.', '-ave.', '-tfr.', '-fwd.',
                                                            '-cov.', '-inv.', '-src.', '-trans.', '-bem-sol.']):
                            if file not in self.files:
                                self.files.append(file)
                            if file not in self.paths:
                                self.paths.update({file: join(dirpath, full_file)})
                            if file not in self.file_types:
                                self.file_types.update({file: match.group(2)})
            self.populate_list_widget()
        else:
            pass

    def add_files(self):
        # Todo: Store Info-Data in Dict after copying?
        existing_files = self.mw.pr.all_files
        existing_erm_files = self.mw.pr.erm_files
        self.pgbar.setMaximum(len(self.files))
        step = 0
        for fname in self.files:
            self.pgbar.setValue(step)
            self.pgbar.update()
            forig = self.paths[fname]
            # Make sure every raw-file got it's -raw appendix
            if fname[-4:] == '-raw':
                fdest = join(self.mw.pr.data_path, fname[:-4], fname + self.file_types[fname])
                ermdest = join(self.mw.pr.data_path, 'empty_room_data', fname[:-4], fname + self.file_types[fname])
                fname = fname[:-4]
            else:
                fdest = join(self.mw.pr.data_path, fname, fname + '-raw' + self.file_types[fname])
                ermdest = join(self.mw.pr.data_path, 'empty_room_data', fname, fname + '-raw' + self.file_types[fname])

            # Copy Empty-Room-Files to their directory
            if any(x in fname for x in ['leer', 'Leer', 'erm', 'ERM', 'empty', 'Empty', 'room', 'Room']):
                # Organize ERMs
                if fname not in existing_erm_files:
                    write_file_list(fname, self.mw.pr.erm_list_path)
                # Copy empty-room-files to destination
                move_file(forig, ermdest)
            else:
                # Organize sub_files
                if fname not in existing_files:
                    write_file_list(fname, self.mw.pr.file_list_path)
                # Copy sub_files to destination
                move_file(forig, fdest)
            # Todo: No response from Window while copying thus no progress-bar-update
            step += 1
            self.pgbar.setValue(step)
            self.pgbar.update()
        self.list_widget.clear()
        self.files = list()
        self.paths = dict()
        self.file_types = dict()

    def closeEvent(self, event):
        self.mw.pr.update_sub_lists()
        self.mw.subject_dock.update_subjects_list()
        event.accept()


def move_folder(src, dst):
    if not isdir(dst):
        print(f'Copying Folder from {src}...')
        try:
            shutil.copytree(src, dst)
        except shutil.Error:  # surfaces with .H and .K at the end can't be copied
            pass
        print(f'Finished Copying to {dst}')
    else:
        print(f'{dst} already exists')


def get_existing_mri_subjects(subjects_dir):
    existing_mri_subs = list()
    for mri_sub in os.listdir(subjects_dir):
        if 'surf' in os.listdir(join(subjects_dir, mri_sub)):
            existing_mri_subs.append(mri_sub)

    return existing_mri_subs


class AddMRIFiles(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QVBoxLayout()

        self.folders = list()
        self.paths = dict()
        self.file_types = dict()

        self.init_ui()
        self.setLayout(self.layout)
        self.open()

    def init_ui(self):
        bt_layout = QHBoxLayout()
        folder_bt = QPushButton('Import 1 FS-Segmentation', self)
        folder_bt.clicked.connect(self.import_mri_subject)
        bt_layout.addWidget(folder_bt)
        folders_bt = QPushButton('Import >1 FS-Segmentations', self)
        folders_bt.clicked.connect(self.import_mri_subjects)
        bt_layout.addWidget(folders_bt)
        self.layout.addLayout(bt_layout)

        list_label = QLabel('These Freesurfer-Segmentations can be imported:', self)
        self.layout.addWidget(list_label)
        self.list_widget = QListWidget(self)
        self.layout.addWidget(self.list_widget)
        self.pgbar = QProgressBar(self)
        self.pgbar.setMinimum(0)
        self.layout.addWidget(self.pgbar)

        main_bt_layout = QHBoxLayout()
        import_bt = QPushButton('Import', self)
        import_bt.clicked.connect(self.add_mri_subjects)
        main_bt_layout.addWidget(import_bt)
        rename_bt = QPushButton('Rename File', self)
        rename_bt.clicked.connect(self.rename_item)
        main_bt_layout.addWidget(rename_bt)
        delete_bt = QPushButton('Delete File', self)
        delete_bt.clicked.connect(self.delete_item)
        main_bt_layout.addWidget(delete_bt)
        ok_bt = QPushButton('OK', self)
        ok_bt.clicked.connect(self.close)
        main_bt_layout.addWidget(ok_bt)
        self.layout.addLayout(main_bt_layout)

    def populate_list_widget(self):
        # List with checkable names
        self.list_widget.clear()
        self.list_widget.addItems(self.folders)

        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)

    def delete_item(self):
        i = self.list_widget.currentRow()
        if i >= 0:
            name = self.list_widget.item(i).text()
            self.list_widget.takeItem(i)
            self.folders.remove(name)

    def rename_item(self):
        i = self.list_widget.currentRow()
        if i >= 0:
            old_name = self.list_widget.item(i).text()
            self.list_widget.edit(i)
            new_name = self.list_widget.item(i).text()
            repl_ind = self.files.index(old_name)
            self.folders[repl_ind] = new_name
            self.paths[new_name] = self.paths[old_name]

    def import_mri_subject(self):
        mri_subjects = get_existing_mri_subjects(self.mw.pr.subjects_dir)
        folder_path = QFileDialog.getExistingDirectory(self, 'Choose a folder with a subject\'s Freesurfe-Segmentation')

        if folder_path != '':
            if 'surf' in os.listdir(folder_path):
                mri_sub = Path(folder_path).name
                if mri_sub not in mri_subjects and mri_sub not in self.folders:
                    self.folders.append(mri_sub)
                    self.paths.update({mri_sub: folder_path})
                    self.populate_list_widget()
                else:
                    print(f'{mri_sub} already existing in <home_path>/Freesurfer')
            else:
                print('Selected Folder doesn\'t seem to be a Freesurfer-Segmentation')

    def import_mri_subjects(self):
        mri_subjects = get_existing_mri_subjects(self.mw.pr.subjects_dir)
        parent_folder = QFileDialog.getExistingDirectory(self, 'Choose a folder containting several '
                                                               'Freesurfer-Segmentations')
        folder_list = os.listdir(parent_folder)

        for mri_sub in folder_list:
            folder_path = join(parent_folder, mri_sub)
            if 'surf' in os.listdir(folder_path):
                if mri_sub not in mri_subjects and mri_sub not in self.folders:
                    self.folders.append(mri_sub)
                    self.paths.update({mri_sub: folder_path})
                else:
                    print(f'{mri_sub} already existing in <home_path>/Freesurfer')
            else:
                print('Selected Folder doesn\'t seem to be a Freesurfer-Segmentation')
        self.populate_list_widget()

    def add_mri_subjects(self):
        self.pgbar.setMaximum(len(self.folders))
        step = 0
        for mri_sub in self.folders:
            src = self.paths[mri_sub]
            dst = join(self.mw.pr.subjects_dir, mri_sub)
            write_file_list(mri_sub, self.mw.pr.mri_sub_list_path)
            move_folder(src, dst)
            step += 1
            self.pgbar.setValue(step)
        self.list_widget.clear()
        self.folders = list()
        self.paths = dict()

    def closeEvent(self, event):
        self.mw.pr.update_sub_lists()
        self.mw.subject_dock.update_mri_subjects_list()
        event.accept()


def read_sub_dict(sub_dict_path):
    sub_dict = {}
    file_name = Path(sub_dict_path).name
    try:
        with open(sub_dict_path, 'r') as sd:
            for item in sd:
                if ':' in item:
                    key, value = item.split(':', 1)
                    value = value[:-1]
                    sub_dict[key] = value

    except FileNotFoundError:
        print(f'{file_name} not yet created, run add_sub_dict')

    return sub_dict


# Todo: make more class-functions
class SubDictDialog(QDialog):
    """ A dialog to assign MRI-Subjects oder Empty-Room-Files to subject(s), depending on mode """

    def __init__(self, main_win, mode):
        """
        :param main_win: The parent-window for the dialog
        :param mode: 'erm' or 'mri'
        """
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QGridLayout()
        self.mode = mode
        if mode == 'mri':
            self.setWindowTitle('Assign files to their MRI-Subject')
            self.path2 = main_win.pr.mri_sub_list_path
            self.dict_path = main_win.pr.sub_dict_path
            self.label2 = 'Choose a mri-subject'
        elif mode == 'erm':
            self.setWindowTitle('Assign files to their ERM-File')
            self.path2 = main_win.pr.erm_list_path
            self.dict_path = main_win.pr.erm_dict_path
            self.label2 = 'Choose a erm-file'

        self.init_ui()
        self.open()

    def init_ui(self):
        file_label = QLabel('Choose a file', self)
        second_label = QLabel(self.label2, self)

        self.layout.addWidget(file_label, 0, 0)
        self.layout.addWidget(second_label, 0, 1)
        # ListWidgets
        self.list_widget1 = QListWidget(self)
        self.list_widget1.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget2 = QListWidget(self)
        with open(self.mw.pr.file_list_path, 'r') as sl:
            for idx, line in enumerate(sl):
                self.list_widget1.insertItem(idx, line[:-1])
        with open(self.path2, 'r') as msl:
            for idx, line in enumerate(msl):
                self.list_widget2.insertItem(idx, line[:-1])

        # Response to Clicking
        self.list_widget1.itemClicked.connect(
                partial(sub_dict_selected, self.list_widget1, self.list_widget2, self.dict_path))

        self.layout.addWidget(self.list_widget1, 1, 0)
        self.layout.addWidget(self.list_widget2, 1, 1)
        # Add buttons
        bt_layout = QVBoxLayout()
        assign_bt = QPushButton('Assign', self)
        assign_bt.clicked.connect(partial(sub_dict_assign, self.dict_path, self.list_widget1, self.list_widget2))
        bt_layout.addWidget(assign_bt)

        none_bt = QPushButton('Assign None', self)
        none_bt.clicked.connect(partial(sub_dict_assign_none, self.dict_path, self.list_widget1))
        bt_layout.addWidget(none_bt)

        all_none_bt = QPushButton('Assign None to all')
        all_none_bt.clicked.connect(partial(sub_dict_assign_all_none, self, self.dict_path, self.list_widget1))
        bt_layout.addWidget(all_none_bt)

        all_bt = QPushButton(f'Assign 1 {self.mode} to all')
        all_bt.clicked.connect(
                partial(sub_dict_assign_to_all, self, self.dict_path, self.list_widget1, self.list_widget2))
        bt_layout.addWidget(all_bt)

        read_bt = QPushButton('Print Console', self)
        read_bt.clicked.connect(partial(read, self.dict_path))
        bt_layout.addWidget(read_bt)

        delete_bt = QPushButton('Undo Assign', self)
        delete_bt.clicked.connect(partial(delete_last, self.dict_path))
        bt_layout.addWidget(delete_bt)

        if self.mode == 'mri':
            group_box = QGroupBox('Template-Brains', self)

            tb_layout = QVBoxLayout()
            self.template_box = QComboBox(self)
            template_brains = ['fsaverage']
            self.template_box.addItems(template_brains)
            self.template_box.setCurrentIndex(0)
            tb_layout.addWidget(self.template_box)

            test_bt = QPushButton('Add Template-Brain')
            test_bt.clicked.connect(self.add_template_brain)
            tb_layout.addWidget(test_bt)

            group_box.setLayout(tb_layout)
            bt_layout.addWidget(group_box)

        ok_bt = QPushButton('OK', self)
        ok_bt.clicked.connect(self.close)
        bt_layout.addWidget(ok_bt)

        self.layout.addLayout(bt_layout, 0, 2, 2, 1)
        self.setLayout(self.layout)

    def add_template_brain(self):
        template_brain = self.template_box.currentText()
        if template_brain == 'fsaverage':
            mne.datasets.fetch_fsaverage(self.mw.pr.subjects_dir)
            if 'fsaverage' not in self.mw.pr.all_mri_subjects:
                self.mw.subject_dock.update_mri_subjects_list()
        else:
            pass

    def closeEvent(self, event):
        self.mw.pr.update_sub_lists()
        event.accept()


def sub_dict_selected(inst1, inst2, dict_path):
    choice = inst1.currentItem().text()
    existing_dict = read_sub_dict(dict_path)
    if choice in existing_dict:
        if existing_dict[choice] == 'None':
            # Kind of bulky, improvable
            enable_none_insert = True
            for i in range(inst2.count()):
                if inst2.item(i).text() == 'None':
                    enable_none_insert = False
            if enable_none_insert:
                inst2.addItem('None')
        try:
            it2 = inst2.findItems(existing_dict[choice], Qt.MatchExactly)[0]
            inst2.setCurrentItem(it2)
        except IndexError:
            pass
    else:
        if inst2.currentItem() is not None:
            inst2.currentItem().setSelected(False)


def sub_dict_assign(dict_path, list_widget1, list_widget2):
    choices1 = list_widget1.selectedItems()
    choice2 = list_widget2.currentItem().text()
    for item in choices1:
        choice1 = item.text()
        if not isfile(dict_path):
            with open(dict_path, 'w') as sd:
                sd.write(f'{choice1}:{choice2}\n')
            print(f'{dict_path} created')

        else:
            existing_dict = read_sub_dict(dict_path)
            if choice1 in existing_dict:
                existing_dict[choice1] = choice2
            else:
                existing_dict.update({choice1: choice2})
            with open(dict_path, 'w') as sd:
                for key, value in existing_dict.items():
                    sd.write(f'{key}:{value}\n')


def sub_dict_assign_none(dict_path, list_widget1):
    choices = list_widget1.selectedItems()
    for item in choices:
        choice = item.text()
        if not isfile(dict_path):
            with open(dict_path, 'w') as sd:
                sd.write(f'{choice}:None\n')
            print(f'{dict_path} created')

        else:
            existing_dict = read_sub_dict(dict_path)
            if choice in existing_dict:
                existing_dict[choice] = None
            else:
                existing_dict.update({choice: None})
            with open(dict_path, 'w') as sd:
                for key, value in existing_dict.items():
                    sd.write(f'{key}:{value}\n')


def sub_dict_assign_to_all(inst, dict_path, list_widget1, list_widget2):
    selected = list_widget2.currentItem().text()
    reply = QMessageBox.question(inst, f'Assign {selected} to All?', f'Do you really want to assign {selected} to all?',
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        all_items = dict()
        for i in range(list_widget1.count()):
            all_items.update({list_widget1.item(i).text(): selected})
        with open(dict_path, 'w') as sd:
            for key, value in all_items.items():
                sd.write(f'{key}:{value}\n')


def sub_dict_assign_all_none(inst, dict_path, list_widget1):
    reply = QMessageBox.question(inst, 'Assign None to All?', 'Do you really want to assign none to all?',
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        all_items = dict()
        for i in range(list_widget1.count()):
            all_items.update({list_widget1.item(i).text(): None})
        with open(dict_path, 'w') as sd:
            for key, value in all_items.items():
                sd.write(f'{key}:{value}\n')


def delete_last(dict_path):
    with open(dict_path, 'r') as dl:
        dlist = (dl.readlines())

    with open(dict_path, 'w') as dl:
        for listitem in dlist[:-1]:
            dl.write(str(listitem))


def read(dict_path):
    try:
        with open(dict_path, 'r') as rl:
            print(rl.read())
    except FileNotFoundError:
        print('file not yet created, assign some files')


def read_bad_channels_dict(bad_channels_dict_path):
    bad_channels_dict = {}

    try:
        with open(bad_channels_dict_path, 'r') as bd:
            for item in bd:
                if ':' in item:
                    key, value = item.split(':', 1)
                    value = value[:-1]
                    value = eval(value)
                    bad_channels_dict[key] = value

    except FileNotFoundError:
        print('bad_channels_dict.py not yet created, run add_bad_channels_dict')

    return bad_channels_dict


class BadChannelsSelect(QDialog):
    """ A Dialog to select Bad-Channels for the files """

    def __init__(self, main_win):
        """
        :param main_win: The parent-window for the dialog
        """
        super().__init__(main_win)
        self.mw = main_win
        self.setWindowTitle('Assign bad_channels for your files')
        self.file_list_path = self.mw.pr.file_list_path
        self.bad_dict = read_bad_channels_dict(self.mw.pr.bad_channels_dict_path)
        self.layout = QGridLayout()
        self.channel_count = 122
        self.bad_chkbts = {}
        self.name = None
        self.raw = None
        self.raw_fig = None

        self.initui()
        self.open()

    def initui(self):
        self.listwidget = QListWidget(self)
        self.layout.addWidget(self.listwidget, 0, 0, self.channel_count // 10, 1)
        with open(self.file_list_path, 'r') as sl:
            for idx, line in enumerate(sl):
                self.listwidget.insertItem(idx, line[:-1])
                if line[:-1] in self.bad_dict:
                    self.listwidget.item(idx).setBackground(QColor('green'))
                    self.listwidget.item(idx).setForeground(QColor('white'))
                else:
                    self.listwidget.item(idx).setBackground(QColor('red'))
                    self.listwidget.item(idx).setForeground(QColor('white'))

        # Make Checkboxes for channels
        for x in range(1, self.channel_count + 1):
            ch_name = f'MEG {x:03}'
            chkbt = QCheckBox(ch_name, self)
            self.bad_chkbts.update({ch_name: chkbt})
            r = 0 + (x - 1) // 10
            c = 1 + (x - 1) % 10
            self.layout.addWidget(chkbt, r, c)

        # Response to Clicking
        self.listwidget.itemClicked.connect(self.bad_dict_selected)

        # Add Buttons
        bt_layout = QVBoxLayout()
        assign_bt = QPushButton('Assign', self)
        assign_bt.clicked.connect(self.bad_dict_assign)
        bt_layout.addWidget(assign_bt)

        plot_bt = QPushButton('Plot Raw')
        plot_bt.clicked.connect(self.plot_raw_bad)
        bt_layout.addWidget(plot_bt)

        ok_bt = QPushButton('Close', self)
        ok_bt.clicked.connect(self.close)
        bt_layout.addWidget(ok_bt)

        self.layout.addLayout(bt_layout, 0, 11, self.channel_count // 10, 1)
        self.setLayout(self.layout)

    def bad_dict_selected(self):
        def load_new_checks():
            # Close current Plot-Window
            if self.raw_fig is not None:
                plt.close(self.raw_fig)
            # First clear all entries
            for bt in self.bad_chkbts:
                self.bad_chkbts[bt].setChecked(False)
            # Then load existing bads for choice
            self.name = self.listwidget.currentItem().text()
            if self.name in self.bad_dict:
                for bad in self.bad_dict[self.name]:
                    self.bad_chkbts[bad].setChecked(True)

        # Check for unsaved changes
        if self.name is not None and self.name in self.bad_dict:
            test_dict = dict()
            test_dict2 = dict()
            for x in range(1, self.channel_count + 1):
                test_dict.update({f'MEG {x:03}': 0})
                test_dict2.update({f'MEG {x:03}': 0})
            for bch in self.bad_dict[self.name]:
                test_dict[bch] = 1
            for bbt in self.bad_chkbts:
                if self.bad_chkbts[bbt].isChecked():
                    test_dict2[bbt] = 1
            if not test_dict == test_dict2:
                answer = QMessageBox.question(self, 'Discard Changes?', 'Do you want to discard changes?',
                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer == QMessageBox.No:
                    old_item = self.listwidget.findItems(self.name, Qt.MatchExactly)[0]
                    self.listwidget.setCurrentItem(old_item)
                else:
                    load_new_checks()
            else:
                load_new_checks()
        else:
            load_new_checks()

    def bad_dict_assign(self):
        self.name = self.listwidget.currentItem().text()
        self.listwidget.currentItem().setBackground(QColor('green'))
        self.listwidget.currentItem().setForeground(QColor('white'))
        bad_channels = []
        for ch in self.bad_chkbts:
            if self.bad_chkbts[ch].isChecked():
                bad_channels.append(ch)
        self.bad_dict.update({self.name: bad_channels})
        ut.dict_filehandler(self.name, 'bad_channels_dict', self.mw.pr.pscripts_path, values=bad_channels)

    # Todo: Semi-Automatic bad-channel-detection
    def plot_raw_bad(self):
        self.name = self.listwidget.currentItem().text()
        dialog = QDialog(self)
        dialog.setWindowTitle('Opening...')
        dialog.open()
        self.raw = io.read_raw(self.name, join(self.mw.pr.data_path, self.name))
        if self.name in self.bad_dict:
            self.raw.info['bads'] = self.bad_dict[self.name]
        self.raw_fig = self.raw.plot(n_channels=30, bad_color='red',
                                     scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1), title=self.name)
        # Connect Closing of Matplotlib-Figure to assignment of bad-channels
        self.raw_fig.canvas.mpl_connect('close_event', self.get_selected_bads)
        dialog.close()

    def get_selected_bads(self, evt):
        print(evt)
        self.bad_dict.update({self.name: self.raw.info['bads']})
        ut.dict_filehandler(self.name, 'bad_channels_dict', self.mw.pr.pscripts_path,
                            values=self.raw.info['bads'])
        # Clear all entries
        for bt in self.bad_chkbts:
            self.bad_chkbts[bt].setChecked(False)
        for ch in self.bad_dict[self.name]:
            self.bad_chkbts[ch].setChecked(True)
        self.listwidget.currentItem().setBackground(QColor('green'))
        self.listwidget.currentItem().setForeground(QColor('white'))

    def closeEvent(self, event):
        def close_function():
            # Update u.a. bad_channels_dict in project-class
            self.mw.pr.update_sub_lists()
            if self.raw_fig is not None:
                plt.close(self.raw_fig)
                event.accept()
            else:
                event.accept()

        # Check if unassigned changes are present
        if self.name in self.bad_dict and self.name is not None:
            test_dict = dict()
            test_dict2 = dict()
            for x in range(1, self.channel_count + 1):
                test_dict.update({f'MEG {x:03}': 0})
                test_dict2.update({f'MEG {x:03}': 0})
            for bch in self.bad_dict[self.name]:
                test_dict[bch] = 1
            for bbt in self.bad_chkbts:
                if self.bad_chkbts[bbt].isChecked():
                    test_dict2[bbt] = 1
            if not test_dict == test_dict2:
                answer = QMessageBox.question(self, 'Discard Changes?', 'Do you want to discard changes?',
                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer == QMessageBox.Yes:
                    close_function()
                else:
                    event.ignore()
            else:
                close_function()
        else:
            changes_made = False
            for bbt in self.bad_chkbts:
                if self.bad_chkbts[bbt].isChecked():
                    changes_made = True
            if changes_made:
                answer = QMessageBox.question(self, 'Discard Changes?', 'Do you want to discard changes?',
                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer == QMessageBox.Yes:
                    close_function()
                else:
                    event.ignore()
            else:
                close_function()
