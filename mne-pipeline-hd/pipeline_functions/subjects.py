"""
subject_organisation by Martin Schulz
martin.schulz@stud.uni-heidelberg.de
"""
import os
import re
import shutil
from ast import literal_eval
from functools import partial
from os.path import exists, isdir, isfile, join
from pathlib import Path

import mne
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAbstractItemView, QCheckBox, QComboBox, QDialog, QDockWidget, QFileDialog, QGridLayout, \
    QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, \
    QPushButton, QStyle, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QWizard, QWizardPage
from matplotlib import pyplot as plt

from basic_functions import io


# Todo: Adapt File-Structure to (MEG)-BIDS-Standards

class CurrentSubject:
    """ Class for File-Data in File-Loop"""

    def __init__(self, name, main_window):
        self.name = name
        self.mw = main_window
        self.p = main_window.pr.parameters
        self.dict_error = False
        self.dialog_open = False
        self.save_dir = join(self.mw.pr.data_path, name)

        try:
            self.ermsub = self.mw.pr.erm_dict[name]
        except KeyError as k:
            print(f'No erm_measurement assigned for {k}')
            # self.dialog_open = True
            # erm_dict_dialog = SubDictDialog(self.mw, 'erm')
            # erm_dict_dialog.finished.connect(self.dialog_closed)
            self.dict_error = True
        try:
            self.subtomri = self.mw.pr.sub_dict[name]
        except KeyError as k:
            print(f'No mri_subject assigned to {k}')
            # self.dialog_open = True
            # mri_dict_dialog = SubDictDialog(self.mw, 'mri')
            # mri_dict_dialog.finished.connect(self.dialog_closed)
            self.dict_error = True
        try:
            self.bad_channels = self.mw.pr.bad_channels_dict[name]
        except KeyError as k:
            print(f'No bad channels for {k}')
            # self.dialog_open = True
            # bad_chan_dialog = BadChannelsSelect(self.mw)
            # bad_chan_dialog.finished.connect(self.dialog_closed)
            self.dict_error = True

    def preload_data(self):
        try:
            self.info = io.read_info(self.name, self.save_dir)
        except FileNotFoundError:
            pass
        try:
            self.raw_filtered = io.read_filtered(self.name, self.save_dir, self.p['highpass'], self.p['lowpass'])
        except FileNotFoundError:
            pass
        try:
            self.events = io.read_events(self.name, self.save_dir)
        except FileNotFoundError:
            pass
        try:
            self.epochs = io.read_epochs(self.name, self.save_dir, self.p['highpass'], self.p['lowpass'])
        except FileNotFoundError:
            pass
        try:
            self.evokeds = io.read_evokeds(self.name, self.save_dir, self.p['highpass'], self.p['lowpass'])
        except FileNotFoundError:
            pass

    def dialog_closed(self):
        self.dialog_open = False

    # Todo: Better solution for Current-File call and update together with function-call
    def update_file_data(self):
        self.ermsub = self.mw.pr.erm_dict[self.name]
        self.subtomri = self.mw.pr.sub_dict[self.name]
        self.bad_channels = self.mw.pr.bad_channels_dict[self.name]


class CurrentMRISubject:
    def __init__(self, mri_subject, main_window):
        self.mw = main_window
        self.pr = main_window.pr
        self.mri_subject = mri_subject


def file_indexing(which_file, all_files):
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


# Todo: Delete Subjects from Dock and Project
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
        self.sub_widget = QWidget()
        self.sub_layout = QVBoxLayout()
        self.sub_listw = QListWidget()
        self.sub_listw.itemChanged.connect(self.get_sub_selection)
        self.sub_layout.addWidget(self.sub_listw)

        self.sub_ledit = QLineEdit()
        self.sub_ledit.setPlaceholderText('Subject-Index')
        self.sub_ledit.textEdited.connect(self.update_sub_selection)
        self.sub_ledit.setToolTip(idx_example)
        self.sub_ledit_layout = QGridLayout()
        self.sub_ledit_layout.addWidget(self.sub_ledit, 0, 0)
        self.sub_clear_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.sub_clear_bt.clicked.connect(self.sub_clear_all)
        self.sub_ledit_layout.addWidget(self.sub_clear_bt, 0, 1)

        # Add and Remove-Buttons
        file_add_bt = QPushButton('Add File/s')
        file_add_bt.clicked.connect(partial(AddFilesDialog, self.mw))
        self.sub_ledit_layout.addWidget(file_add_bt, 1, 0)
        file_rm_bt = QPushButton('Remove File/s')
        file_rm_bt.clicked.connect(self.remove_files)
        self.sub_ledit_layout.addWidget(file_rm_bt, 1, 1)

        self.sub_layout.addLayout(self.sub_ledit_layout)
        self.sub_widget.setLayout(self.sub_layout)

        self.tab_widget.addTab(self.sub_widget, 'Files')

        # MRI-Subjects-List + Index-Line-Edit
        self.mri_widget = QWidget()
        self.mri_layout = QVBoxLayout()
        self.mri_listw = QListWidget()
        self.mri_listw.itemChanged.connect(self.get_mri_selection)
        self.mri_layout.addWidget(self.mri_listw)

        self.mri_ledit = QLineEdit()
        self.mri_ledit.setPlaceholderText('MRI-Subject-Index')
        self.mri_ledit.textEdited.connect(self.update_mri_selection)
        self.mri_ledit.setToolTip(idx_example)
        self.mri_bt_layout = QGridLayout()
        self.mri_bt_layout.addWidget(self.mri_ledit, 0, 0)
        self.mri_clear_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_DialogCancelButton))
        # self.mri_clear_bt = QPushButton(icon=QIcon(':/abort_icon.svg'))
        self.mri_clear_bt.clicked.connect(self.mri_clear_all)
        self.mri_bt_layout.addWidget(self.mri_clear_bt, 0, 1)
        # Add and Remove-Buttons
        mri_add_bt = QPushButton('Add MRI-Subject/s')
        mri_add_bt.clicked.connect(partial(AddMRIDialog, self.mw))
        self.mri_bt_layout.addWidget(mri_add_bt, 1, 0)
        mri_rm_bt = QPushButton('Remove MRI-Subject/s')
        mri_rm_bt.clicked.connect(self.remove_mri_subjects)
        self.mri_bt_layout.addWidget(mri_rm_bt, 1, 1)

        self.mri_layout.addLayout(self.mri_bt_layout)
        self.mri_widget.setLayout(self.mri_layout)

        self.tab_widget.addTab(self.mri_widget, 'MRI-Subjects')

        self.ga_widget = GrandAvgWidget(self.mw)
        self.tab_widget.addTab(self.ga_widget, 'Grand-Average')

        self.layout.addWidget(self.tab_widget)
        self.main_widget.setLayout(self.layout)
        self.setWidget(self.main_widget)

    def update_subjects_list(self):
        self.sub_listw.clear()
        for idx, file in enumerate(self.mw.pr.all_files):
            idx += 1  # Let index start with 1
            item = QListWidgetItem(f'{idx}: {file}')
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.mw.pr.sel_files:
                if file in self.mw.pr.sel_files:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.sub_listw.addItem(item)

    def update_mri_subjects_list(self):
        # Also get all freesurfe-directories from Freesurfer-Folder (maybe user added some manually)
        existing_dirs = get_existing_mri_subjects(self.mw.pr.subjects_dir)
        for edir in existing_dirs:
            if edir not in self.mw.pr.all_mri_subjects:
                self.mw.pr.all_mri_subjects.append(edir)
        self.mri_listw.clear()
        for idx, file in enumerate(self.mw.pr.all_mri_subjects):
            idx += 1  # Let index start with 1
            item = QListWidgetItem(f'{idx}: {file}')
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.mw.pr.sel_mri_files:
                if file in self.mw.pr.sel_mri_files:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.mri_listw.addItem(item)

    def get_sub_selection(self):
        sel_files = []
        for idx in range(self.sub_listw.count()):
            item = self.sub_listw.item(idx)
            if item.checkState() == Qt.Checked:
                # Index in front of name has to be deleted Todo: can be done better (maybe QTableWidget?)
                sel_files.append(item.text()[len(str(idx + 1)) + 2:])
        self.mw.pr.sel_files = sel_files

    def get_mri_selection(self):
        sel_mri = []
        for idx in range(self.mri_listw.count()):
            item = self.mri_listw.item(idx)
            if item.checkState() == Qt.Checked:
                # Index in front of name has to be deleted Todo: can be done better (maybe QTableWidget?)
                sel_mri.append(item.text()[len(str(idx + 1)) + 2:])
        self.mw.pr.sel_mri_files = sel_mri

    def update_sub_selection(self):
        which_file = self.sub_ledit.text()
        self.mw.pr.sel_files, idxs = file_indexing(which_file, self.mw.pr.all_files)
        if len(idxs) > 0:
            # Clear all check-states
            self.sub_clear_all()
            for idx in idxs:
                self.sub_listw.item(idx).setCheckState(Qt.Checked)
        else:
            pass

    def update_mri_selection(self):
        which_file = self.mri_sub_ledit.text()
        self.mw.pr.sel_mri_files, idxs = file_indexing(which_file, self.mw.pr.all_mri_subjects)

    def sub_clear_all(self):
        for idx in range(self.sub_listw.count()):
            self.sub_listw.item(idx).setCheckState(Qt.Unchecked)

    def mri_clear_all(self):
        for idx in range(self.mri_listw.count()):
            self.mri_listw.item(idx).setCheckState(Qt.Unchecked)

    def remove_files(self):
        if len(self.mw.pr.sel_files) > 0:
            def remove_only_list():
                for file in self.mw.pr.sel_files:
                    self.mw.pr.all_files.remove(file)
                self.mw.pr.sel_files = []
                self.update_subjects_list()
                self.sub_msg_box.close()

            def remove_with_files():
                for file in self.mw.pr.sel_files:
                    self.mw.pr.all_files.remove(file)
                    try:
                        shutil.rmtree(join(self.mw.pr.data_path, file))
                    except FileNotFoundError:
                        print(join(self.mw.pr.data_path, file) + ' not found!')
                self.mw.pr.sel_files = []
                self.update_subjects_list()
                self.sub_msg_box.close()

            self.sub_msg_box = QDialog(self.mw)
            msg_box_layout = QGridLayout()
            label = QLabel('Do you really want to remove the selected files?')
            msg_box_layout.addWidget(label, 0, 0, 1, 3)
            only_list_bt = QPushButton('Remove only from List')
            only_list_bt.clicked.connect(remove_only_list)
            msg_box_layout.addWidget(only_list_bt, 1, 0)
            remove_files_bt = QPushButton('Remove with all Files')
            remove_files_bt.clicked.connect(remove_with_files)
            msg_box_layout.addWidget(remove_files_bt, 1, 1)
            cancel_bt = QPushButton('Cancel')
            cancel_bt.clicked.connect(self.sub_msg_box.close)
            msg_box_layout.addWidget(cancel_bt, 1, 2)
            self.sub_msg_box.setLayout(msg_box_layout)
            self.sub_msg_box.open()
        else:
            pass

    def remove_mri_subjects(self):
        if len(self.mw.pr.sel_mri_files) > 0:
            def remove_only_list():
                for mri_subject in self.mw.pr.sel_mri_files:
                    self.mw.pr.all_mri_subjects.remove(mri_subject)
                self.mw.pr.sel_mri_files = []
                self.update_mri_subjects_list()
                self.mri_msg_box.close()

            def remove_with_files():
                for mri_subject in self.mw.pr.sel_mri_files:
                    self.mw.pr.all_mri_subjects.remove(mri_subject)
                    try:
                        shutil.rmtree(join(self.mw.pr.subjects_dir, mri_subject))
                    except FileNotFoundError:
                        print(join(self.mw.pr.subjects_dir, mri_subject) + ' not found!')
                self.mw.pr.sel_mri_files = []
                self.update_mri_subjects_list()
                self.mri_msg_box.close()

            self.mri_msg_box = QDialog(self.mw)
            msg_box_layout = QGridLayout()
            label = QLabel('Do you really want to remove the selected mri_subjects?')
            msg_box_layout.addWidget(label, 0, 0, 1, 3)
            only_list_bt = QPushButton('Remove from List')
            only_list_bt.clicked.connect(remove_only_list)
            msg_box_layout.addWidget(only_list_bt, 1, 0)
            remove_files_bt = QPushButton('Remove with Files')
            remove_files_bt.clicked.connect(remove_with_files)
            msg_box_layout.addWidget(remove_files_bt, 1, 1)
            cancel_bt = QPushButton('Cancel')
            cancel_bt.clicked.connect(self.mri_msg_box.close)
            msg_box_layout.addWidget(cancel_bt, 1, 2)
            self.mri_msg_box.setLayout(msg_box_layout)
            self.mri_msg_box.open()
        else:
            pass


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


class GrandAvgWidget(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw

        self.init_layout()
        self.update_treew()
        self.get_treew()

    def init_layout(self):
        self.layout = QVBoxLayout()
        self.treew = QTreeWidget()
        self.treew.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treew.itemChanged.connect(self.get_treew)
        self.treew.setColumnCount(1)
        self.treew.setHeaderLabel('Groups:')
        self.layout.addWidget(self.treew)

        self.bt_layout = QHBoxLayout()
        add_g_bt = QPushButton('Add Group')
        add_g_bt.clicked.connect(self.add_group)
        self.bt_layout.addWidget(add_g_bt)
        add_file_bt = QPushButton('Add Files')
        add_file_bt.clicked.connect(self.add_files)
        self.bt_layout.addWidget(add_file_bt)
        self.rm_bt = QPushButton('Remove')
        self.rm_bt.clicked.connect(self.remove_item)
        self.bt_layout.addWidget(self.rm_bt)
        self.layout.addLayout(self.bt_layout)

        self.setLayout(self.layout)

    def update_treew(self):
        self.treew.clear()
        top_items = []
        for group in self.mw.pr.grand_avg_dict:
            top_item = QTreeWidgetItem()
            top_item.setText(0, group)
            top_item.setFlags(top_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            if group in self.mw.pr.sel_ga_groups:
                top_item.setCheckState(0, Qt.Checked)
            else:
                top_item.setCheckState(0, Qt.Unchecked)
            for file in self.mw.pr.grand_avg_dict[group]:
                sub_item = QTreeWidgetItem(top_item)
                sub_item.setText(0, file)
            top_items.append(top_item)
        self.treew.addTopLevelItems(top_items)

    def get_treew(self):
        new_dict = {}
        self.mw.pr.sel_ga_groups = []
        for top_idx in range(self.treew.topLevelItemCount()):
            top_item = self.treew.topLevelItem(top_idx)
            top_text = top_item.text(0)
            new_dict.update({top_text: []})
            for child_idx in range(top_item.childCount()):
                child_item = top_item.child(child_idx)
                new_dict[top_text].append(child_item.text(0))
            if top_item.checkState(0) == Qt.Checked:
                self.mw.pr.sel_ga_groups.append(top_text)
        self.mw.pr.grand_avg_dict = new_dict

    def add_group(self):
        text, ok = QInputDialog.getText(self, 'New Group', 'Enter the name for a new group:')
        if ok and text:
            top_item = QTreeWidgetItem()
            top_item.setText(0, text)
            top_item.setFlags(top_item.flags() | Qt.ItemIsUserCheckable)
            top_item.setCheckState(0, Qt.Checked)
            self.treew.addTopLevelItem(top_item)
        self.get_treew()

    def add_files(self):
        sel_group = self.treew.currentItem()
        if sel_group:
            # When file in group is selected
            if sel_group.parent():
                sel_group = sel_group.parent()
            GrandAvgFileAdd(self.mw, sel_group, self)
        else:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Obacht!')
            msg_box.setText('No group has been selected')
            msg_box.open()

    def remove_item(self):
        items = self.treew.selectedItems()
        if len(items) > 0:
            for item in items:
                if item.parent():
                    item.parent().takeChild(item.parent().indexOfChild(item))
                else:
                    self.treew.takeTopLevelItem(self.treew.indexOfTopLevelItem(item))
        self.get_treew()
        self.treew.setCurrentItem(None, 0)


class GrandAvgFileAdd(QDialog):
    def __init__(self, mw, group, ga_widget):
        super().__init__(ga_widget)
        self.mw = mw
        self.group = group
        self.ga_widget = ga_widget
        self.setWindowTitle('Select Files to add')

        self.init_ui()

    def init_ui(self):

        dlg_layout = QGridLayout()
        self.listw = QListWidget()
        self.listw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.listw.itemSelectionChanged.connect(self.sel_changed)
        self.load_list()

        dlg_layout.addWidget(self.listw, 0, 0, 1, 4)
        add_bt = QPushButton('Add')
        add_bt.clicked.connect(self.add)
        dlg_layout.addWidget(add_bt, 1, 0)
        all_bt = QPushButton('All')
        all_bt.clicked.connect(self.sel_all)
        dlg_layout.addWidget(all_bt, 1, 1)
        clear_bt = QPushButton('Clear')
        clear_bt.clicked.connect(self.clear)
        dlg_layout.addWidget(clear_bt, 1, 2)
        quit_bt = QPushButton('Quit')
        quit_bt.clicked.connect(self.close)
        dlg_layout.addWidget(quit_bt, 1, 3)

        self.setLayout(dlg_layout)
        self.open()

    def sel_changed(self):
        for list_i in self.listw.selectedItems():
            list_i.setCheckState(Qt.Checked)

    def add(self):
        for idx in range(self.listw.count()):
            list_item = self.listw.item(idx)
            if list_item.checkState() == Qt.Checked:
                tree_item = QTreeWidgetItem()
                tree_item.setText(0, list_item.text())
                self.group.insertChild(self.group.childCount(), tree_item)
        self.group.setExpanded(True)
        self.listw.clear()
        self.ga_widget.get_treew()
        self.load_list()

    def load_list(self):
        for item_name in self.mw.pr.all_files:
            if item_name not in self.mw.pr.grand_avg_dict[self.group.text(0)]:
                item = QListWidgetItem(item_name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.listw.addItem(item)

    def clear(self):
        for idx in range(self.listw.count()):
            self.listw.item(idx).setCheckState(Qt.Unchecked)

    def sel_all(self):
        for idx in range(self.listw.count()):
            self.listw.item(idx).setCheckState(Qt.Checked)


# ToDo: Event-ID-Widget (Subklassen und jetzt auch mit event_colors)

# Todo: Enable Drag&Drop
# Todo: RegExp-Wizard
class AddFilesWidget(QWidget):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QVBoxLayout()

        self.files = list()
        self.paths = dict()
        self.file_types = dict()

        self.init_ui()

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

        self.main_bt_layout = QHBoxLayout()
        import_bt = QPushButton('Import', self)
        import_bt.clicked.connect(self.add_files)
        self.main_bt_layout.addWidget(import_bt)
        rename_bt = QPushButton('Rename File', self)
        rename_bt.clicked.connect(self.rename_item)
        self.main_bt_layout.addWidget(rename_bt)
        delete_bt = QPushButton('Delete File', self)
        delete_bt.clicked.connect(self.delete_item)
        self.main_bt_layout.addWidget(delete_bt)
        self.layout.addLayout(self.main_bt_layout)

        self.setLayout(self.layout)

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

    # Todo: Replace Progress-Window with working progressbar
    def add_files(self):
        # Todo: Store Info-Data in Dict after copying?
        existing_files = self.mw.pr.all_files
        existing_erm_files = self.mw.pr.erm_files
        self.pgbar.setMaximum(len(self.files))
        step = 0
        dialog = QDialog(self)
        dialog.setWindowTitle('Copying...')
        dialog.open()
        for fname in self.files:
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
                    self.mw.pr.erm_files.append(fname)
                # Copy empty-room-files to destination
                move_file(forig, ermdest)
            else:
                # Organize sub_files
                if fname not in existing_files:
                    self.mw.pr.all_files.append(fname)
                # Copy sub_files to destination
                move_file(forig, fdest)
            # Todo: No response from Window while copying thus no progress-bar-update
            step += 1
            self.pgbar.setValue(step)
            self.pgbar.update()

        dialog.close()
        self.list_widget.clear()
        self.files = list()
        self.paths = dict()
        self.file_types = dict()

        self.mw.subject_dock.update_subjects_list()


class AddFilesDialog(AddFilesWidget):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.dialog = QDialog(main_win)

        test_layout = QHBoxLayout()

        close_bt = QPushButton('Close', self)
        close_bt.clicked.connect(self.dialog.close)
        self.main_bt_layout.addWidget(close_bt)

        test_layout.addWidget(self)

        self.dialog.setLayout(test_layout)
        self.dialog.open()


class AddFilesWizPage(AddFilesWidget):
    def __init__(self, main_win):
        super().__init__(main_win)


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
    # Get Freesurfer-folders (with 'surf'-folder) from subjects_dir (excluding .files for Mac)
    read_dir = sorted([f for f in os.listdir(subjects_dir) if not f.startswith('.')], key=str.lower)
    for mri_sub in read_dir:
        if exists(join(subjects_dir, mri_sub, 'surf')):
            existing_mri_subs.append(mri_sub)

    return existing_mri_subs


class AddMRIWidget(QWidget):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QVBoxLayout()

        self.folders = list()
        self.paths = dict()
        self.file_types = dict()

        self.init_ui()

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

        self.main_bt_layout = QHBoxLayout()
        import_bt = QPushButton('Import', self)
        import_bt.clicked.connect(self.add_mri_subjects)
        self.main_bt_layout.addWidget(import_bt)
        rename_bt = QPushButton('Rename File', self)
        rename_bt.clicked.connect(self.rename_item)
        self.main_bt_layout.addWidget(rename_bt)
        delete_bt = QPushButton('Delete File', self)
        delete_bt.clicked.connect(self.delete_item)
        self.main_bt_layout.addWidget(delete_bt)

        self.layout.addLayout(self.main_bt_layout)
        self.setLayout(self.layout)

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
            if exists(join(folder_path, 'surf')):
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
        folder_list = sorted([f for f in os.listdir(parent_folder) if not f.startswith('.')], key=str.lower)

        for mri_sub in folder_list:
            folder_path = join(parent_folder, mri_sub)
            if exists(join(folder_path, 'surf')):
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
        dialog = QDialog(self)
        dialog.setWindowTitle('Copying...')
        dialog.open()
        for mri_sub in self.folders:
            src = self.paths[mri_sub]
            dst = join(self.mw.pr.subjects_dir, mri_sub)
            self.mw.pr.all_mri_subjects.append(mri_sub)
            move_folder(src, dst)
            step += 1
            self.pgbar.setValue(step)
        self.list_widget.clear()
        self.folders = list()
        self.paths = dict()
        dialog.close()

        self.mw.subject_dock.update_mri_subjects_list()


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


class AddMRIDialog(AddMRIWidget):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.dialog = QDialog(main_win)

        close_bt = QPushButton('Close', self)
        close_bt.clicked.connect(self.dialog.close)
        self.main_bt_layout.addWidget(close_bt)

        self.dialog.setLayout(self.layout)
        self.dialog.open()


class SubDictWidget(QWidget):
    """ A widget to assign MRI-Subjects oder Empty-Room-Files to subject(s), depending on mode """

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
            self.list2 = self.mw.pr.all_mri_subjects
            self.label2 = 'Choose a mri-subject'
        else:
            self.setWindowTitle('Assign files to their ERM-File')
            self.list2 = self.mw.pr.erm_files
            self.label2 = 'Choose a erm-file'

        self.init_ui()
        self.get_status()

    def init_ui(self):
        file_label = QLabel('Choose a file', self)
        second_label = QLabel(self.label2, self)

        self.layout.addWidget(file_label, 0, 0)
        self.layout.addWidget(second_label, 0, 1)
        # ListWidgets
        self.list_widget1 = QListWidget(self)
        self.list_widget1.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget1.addItems(self.mw.pr.all_files)
        self.list_widget2 = QListWidget(self)
        self.list_widget2.addItems(self.list2)

        # Response to Clicking
        self.list_widget1.itemClicked.connect(self.sub_dict_selected)

        self.layout.addWidget(self.list_widget1, 1, 0)
        self.layout.addWidget(self.list_widget2, 1, 1)
        # Add buttons
        self.bt_layout = QVBoxLayout()
        assign_bt = QPushButton('Assign', self)
        assign_bt.clicked.connect(self.sub_dict_assign)
        self.bt_layout.addWidget(assign_bt)

        none_bt = QPushButton('Assign None', self)
        none_bt.clicked.connect(self.sub_dict_assign_none)
        self.bt_layout.addWidget(none_bt)

        all_none_bt = QPushButton('Assign None to all')
        all_none_bt.clicked.connect(self.sub_dict_assign_all_none)
        self.bt_layout.addWidget(all_none_bt)

        all_bt = QPushButton(f'Assign 1 {self.mode} to all')
        all_bt.clicked.connect(self.sub_dict_assign_to_all)
        self.bt_layout.addWidget(all_bt)

        read_bt = QPushButton('Show Assignments', self)
        read_bt.clicked.connect(self.show_assignments)
        self.bt_layout.addWidget(read_bt)

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
            self.bt_layout.addWidget(group_box)

        self.layout.addLayout(self.bt_layout, 0, 2, 2, 1)
        self.setLayout(self.layout)

    def get_status(self):
        for idx in range(self.list_widget1.count()):
            item_name = self.list_widget1.item(idx).text()
            if self.mode == 'mri':
                if item_name in self.mw.pr.sub_dict:
                    self.list_widget1.item(idx).setBackground(QColor('green'))
                    self.list_widget1.item(idx).setForeground(QColor('white'))
                else:
                    self.list_widget1.item(idx).setBackground(QColor('red'))
                    self.list_widget1.item(idx).setForeground(QColor('white'))
            else:
                if item_name in self.mw.pr.erm_dict:
                    self.list_widget1.item(idx).setBackground(QColor('green'))
                    self.list_widget1.item(idx).setForeground(QColor('white'))
                else:
                    self.list_widget1.item(idx).setBackground(QColor('red'))
                    self.list_widget1.item(idx).setForeground(QColor('white'))

    def add_template_brain(self):
        template_brain = self.template_box.currentText()
        if template_brain == 'fsaverage':
            mne.datasets.fetch_fsaverage(self.mw.pr.subjects_dir)
            if 'fsaverage' not in self.mw.pr.all_mri_subjects:
                self.mw.subject_dock.update_mri_subjects_list()
        else:
            pass

    def sub_dict_selected(self):
        choice = self.list_widget1.currentItem().text()
        if self.mode == 'mri':
            existing_dict = self.mw.pr.sub_dict
        else:
            existing_dict = self.mw.pr.erm_dict
        if choice in existing_dict:
            if existing_dict[choice] == 'None':
                # Kind of bulky, improvable
                enable_none_insert = True
                for idx in range(self.list_widget2.count()):
                    if self.list_widget2.item(idx).text() == 'None':
                        enable_none_insert = False
                if enable_none_insert:
                    self.list_widget2.addItem('None')
            try:
                it2 = self.list_widget2.findItems(existing_dict[choice], Qt.MatchExactly)[0]
                self.list_widget2.setCurrentItem(it2)
            except IndexError:
                pass
        else:
            if self.list_widget2.currentItem():
                self.list_widget2.currentItem().setSelected(False)

    def sub_dict_assign(self):
        choices1 = self.list_widget1.selectedItems()
        choice2 = self.list_widget2.currentItem().text()
        if self.mode == 'mri':
            existing_dict = self.mw.pr.sub_dict
        else:
            existing_dict = self.mw.pr.erm_dict
        for item in choices1:
            item.setBackground(QColor('green'))
            item.setForeground(QColor('white'))
            choice1 = item.text()
            if choice1 in existing_dict:
                existing_dict[choice1] = choice2
            else:
                existing_dict.update({choice1: choice2})
        if self.mode == 'mri':
            self.mw.pr.sub_dict = existing_dict
        else:
            self.mw.pr.erm_dict = existing_dict

    def sub_dict_assign_none(self):
        choices = self.list_widget1.selectedItems()
        if self.mode == 'mri':
            existing_dict = self.mw.pr.sub_dict
        else:
            existing_dict = self.mw.pr.erm_dict
        for item in choices:
            item.setBackground(QColor('green'))
            item.setForeground(QColor('white'))
            choice = item.text()
            if choice in existing_dict:
                existing_dict[choice] = 'None'
            else:
                existing_dict.update({choice: 'None'})
        if self.mode == 'mri':
            self.mw.pr.sub_dict = existing_dict
        else:
            self.mw.pr.erm_dict = existing_dict

    def sub_dict_assign_to_all(self):
        try:
            selected = self.list_widget2.currentItem().text()
            reply = QMessageBox.question(self, f'Assign {selected} to All?',
                                         f'Do you really want to assign {selected} to all?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                all_items = dict()
                for i in range(self.list_widget1.count()):
                    self.list_widget1.item(i).setBackground(QColor('green'))
                    self.list_widget1.item(i).setForeground(QColor('white'))
                    all_items.update({self.list_widget1.item(i).text(): selected})
                if self.mode == 'mri':
                    self.mw.pr.sub_dict = all_items
                elif self.mode == 'erm':
                    self.mw.pr.erm_dict = all_items
        except AttributeError:
            # When no second item is selected
            pass

    def sub_dict_assign_all_none(self):
        reply = QMessageBox.question(self, 'Assign None to All?', 'Do you really want to assign none to all?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            all_items = dict()
            for i in range(self.list_widget1.count()):
                self.list_widget1.item(i).setBackground(QColor('green'))
                self.list_widget1.item(i).setForeground(QColor('white'))
                all_items.update({self.list_widget1.item(i).text(): 'None'})
            if self.mode == 'mri':
                self.mw.pr.sub_dict = all_items
            elif self.mode == 'erm':
                self.mw.pr.erm_dict = all_items

    def show_assignments(self):
        self.show_ass_dialog = QDialog(self)
        self.show_ass_dialog.setWindowTitle('Assignments')
        layout = QGridLayout()
        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        if self.mode == 'mri':
            the_dict = self.mw.pr.sub_dict
        else:
            the_dict = self.mw.pr.erm_dict
        item_list = []
        for key, value in the_dict.items():
            item_list.append(f'{key}: {value}')
        list_widget.addItems(item_list)
        layout.addWidget(list_widget, 0, 0, 1, 2)

        delete_bt = QPushButton('Delete')
        delete_bt.clicked.connect(partial(self.delete_assignment, list_widget))
        layout.addWidget(delete_bt, 1, 0)

        quit_bt = QPushButton('Quit')
        quit_bt.clicked.connect(self.show_assignments_close)
        layout.addWidget(quit_bt, 1, 1)

        self.show_ass_dialog.setLayout(layout)
        self.show_ass_dialog.open()

    def delete_assignment(self, list_widget):
        choices = list_widget.selectedItems()
        for item in choices:
            list_widget.takeItem(list_widget.row(item))
            item_text = item.text()
            key_text = item_text[:item_text.find(':')]
            if self.mode == 'mri':
                self.mw.pr.sub_dict.pop(key_text, None)
            else:
                self.mw.pr.erm_dict.pop(key_text, None)

    def show_assignments_close(self):
        self.show_ass_dialog.close()
        self.get_status()


class SubDictDialog(SubDictWidget):
    def __init__(self, main_win, mode):
        super().__init__(main_win, mode)

        self.dialog = QDialog(main_win)

        close_bt = QPushButton('Close', self)
        close_bt.clicked.connect(self.dialog.close)
        self.bt_layout.addWidget(close_bt)

        self.dialog.setLayout(self.layout)
        self.dialog.open()


class SubDictWizPage(SubDictWidget, QWizardPage):
    def __init__(self, main_win, mode):
        SubDictWidget.__init__(self, main_win, mode)
        QWizardPage.__init__(self, main_win)

    def init_wizard_ui(self):
        layout = QVBoxLayout()


def read_bad_channels_dict(bad_channels_dict_path):
    bad_channels_dict = {}

    try:
        with open(bad_channels_dict_path, 'r') as bd:
            for item in bd:
                if ':' in item:
                    key, value = item.split(':', 1)
                    value = value[:-1]
                    eval_value = literal_eval(value)
                    if 'MEG' not in value:
                        new_list = []
                        for ch in eval_value:
                            ch_name = f'MEG {ch:03}'
                            new_list.append(ch_name)
                        bad_channels_dict[key] = new_list
                    else:
                        bad_channels_dict[key] = eval_value

    except FileNotFoundError:
        print('bad_channels_dict.py not yet created, run add_bad_channels_dict')

    return bad_channels_dict


class SubBadsWidget(QWidget):
    """ A Dialog to select Bad-Channels for the files """

    def __init__(self, main_win):
        """
        :param main_win: The parent-window for the dialog
        """
        super().__init__(main_win)
        self.mw = main_win
        self.setWindowTitle('Assign bad_channels for your files')
        self.layout = QGridLayout()
        self.channel_count = 122
        self.bad_chkbts = {}
        self.name = None
        self.raw = None
        self.raw_fig = None

        self.initui()

    def initui(self):
        self.listwidget = QListWidget(self)
        self.layout.addWidget(self.listwidget, 0, 0, self.channel_count // 10, 1)
        for idx, key in enumerate(self.mw.pr.all_files):
            self.listwidget.insertItem(idx, key)
            if key in self.mw.pr.bad_channels_dict:
                self.listwidget.item(idx).setBackground(QColor('green'))
                self.listwidget.item(idx).setForeground(QColor('white'))
            else:
                self.listwidget.item(idx).setBackground(QColor('red'))
                self.listwidget.item(idx).setForeground(QColor('white'))

        # Make Checkboxes for channels
        for x in range(1, self.channel_count + 1):
            ch_name = f'MEG {x:03}'
            chkbt = QCheckBox(ch_name, self)
            chkbt.clicked.connect(self.bad_dict_assign)
            self.bad_chkbts.update({ch_name: chkbt})
            r = 0 + (x - 1) // 10
            c = 1 + (x - 1) % 10
            self.layout.addWidget(chkbt, r, c)

        # Response to Clicking
        self.listwidget.itemClicked.connect(self.bad_dict_selected)

        # Add Buttons
        self.bt_layout = QHBoxLayout()

        plot_bt = QPushButton('Plot Raw')
        plot_bt.clicked.connect(self.plot_raw_bad)
        self.bt_layout.addWidget(plot_bt)

        self.layout.addLayout(self.bt_layout, self.channel_count // 10 + 1, 0, 1, self.channel_count // 10)
        self.setLayout(self.layout)

    def bad_dict_selected(self):
        self.name = self.listwidget.currentItem().text()
        # Check for unsaved changes
        if self.name:
            # Close current Plot-Window
            if self.raw_fig:
                plt.close(self.raw_fig)
            # First clear all entries
            for bt in self.bad_chkbts:
                self.bad_chkbts[bt].setChecked(False)
            # Then load existing bads for choice
            if self.name in self.mw.pr.bad_channels_dict:
                for bad in self.mw.pr.bad_channels_dict[self.name]:
                    self.bad_chkbts[bad].setChecked(True)
        else:
            pass

    def bad_dict_assign(self):
        self.name = self.listwidget.currentItem().text()
        self.listwidget.currentItem().setBackground(QColor('green'))
        self.listwidget.currentItem().setForeground(QColor('white'))
        bad_channels = []
        for ch in self.bad_chkbts:
            if self.bad_chkbts[ch].isChecked():
                bad_channels.append(ch)
        self.mw.pr.bad_channels_dict.update({self.name: bad_channels})

    # Todo: Semi-Automatic bad-channel-detection
    def plot_raw_bad(self):
        self.name = self.listwidget.currentItem().text()
        dialog = QDialog(self)
        dialog.setWindowTitle('Opening...')
        dialog.open()
        self.raw = io.read_raw(self.name, join(self.mw.pr.data_path, self.name))
        if self.name in self.mw.pr.bad_channels_dict:
            self.raw.info['bads'] = self.mw.pr.bad_channels_dict[self.name]
        self.raw_fig = self.raw.plot(n_channels=30, bad_color='red',
                                     scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1), title=self.name)
        # Connect Closing of Matplotlib-Figure to assignment of bad-channels
        self.raw_fig.canvas.mpl_connect('close_event', self.get_selected_bads)
        dialog.close()

    def get_selected_bads(self, evt):
        print(evt)
        self.mw.pr.bad_channels_dict.update({self.name: self.raw.info['bads']})

        # Clear all entries
        for bt in self.bad_chkbts:
            self.bad_chkbts[bt].setChecked(False)
        for ch in self.mw.pr.bad_channels_dict[self.name]:
            self.bad_chkbts[ch].setChecked(True)
        self.listwidget.currentItem().setBackground(QColor('green'))
        self.listwidget.currentItem().setForeground(QColor('white'))

    def closeEvent(self, event):
        def close_function():
            # Update u.a. bad_channels_dict in project-class
            if self.raw_fig:
                plt.close(self.raw_fig)
                self.done(1)
                event.accept()
            else:
                self.done(1)
                event.accept()

        # Check if unassigned changes are present
        if self.name in self.mw.pr.bad_channels_dict and self.name:
            test_dict = dict()
            test_dict2 = dict()
            for x in range(1, self.channel_count + 1):
                test_dict.update({f'MEG {x:03}': 0})
                test_dict2.update({f'MEG {x:03}': 0})
            for bch in self.mw.pr.bad_channels_dict[self.name]:
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


class SubBadsDialog(SubBadsWidget):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.dialog = QDialog(main_win)

        close_bt = QPushButton('Close', self)
        close_bt.clicked.connect(self.dialog.close)
        self.bt_layout.addWidget(close_bt)

        self.dialog.setLayout(self.layout)
        self.dialog.open()


class SubjectWizard(QWizard):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
