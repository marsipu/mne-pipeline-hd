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
import os
import re
import shutil
import sys
from collections import Counter
from functools import partial
from os.path import exists, isdir, isfile, join
from pathlib import Path

import matplotlib
import mne
import numpy as np
import pandas as pd
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDesktopWidget, QDialog, QDockWidget, QFileDialog,
                             QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMessageBox, QProgressDialog, QPushButton,
                             QScrollArea, QSizePolicy, QTabWidget, QTableView, QTextEdit, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget, QWizard, QWizardPage)
from matplotlib import pyplot as plt

from .base_widgets import CheckDictList, CheckList, EditDict, EditList, SimpleList
from .dialogs import ErrorDialog
from .gui_utils import (Worker, get_ratio_geometry)
from .models import AddFilesModel
from ..basic_functions.loading import MEEG


def index_parser(index, all_items):
    """
    Parses indices from a index-string in all_items

    Parameters
    ----------
    index: str
        A string which contains information about indices
    all_items
        All items
    Returns
    -------

    """
    run = list()
    rm = list()

    try:
        if index == '':
            return [], []
        elif 'all' in index:
            if ',' in index:
                splits = index.split(',')
                for sp in splits:
                    if '!' in sp and '-' in sp:
                        x, y = sp.split('-')
                        x = x[1:]
                        for n in range(int(x), int(y) + 1):
                            rm.append(n)
                    elif '!' in sp:
                        rm.append(int(sp[1:]))
                    elif 'all' in sp:
                        for i in range(len(all_items)):
                            run.append(i)
            else:
                run = [x for x in range(len(all_items))]

        elif ',' in index and '-' in index:
            z = index.split(',')
            for i in z:
                if '-' in i and '!' not in i:
                    x, y = i.split('-')
                    for n in range(int(x), int(y) + 1):
                        run.append(n)
                elif '!' not in i:
                    run.append(int(i))
                elif '!' in i and '-' in i:
                    x, y = i.split('-')
                    x = x[1:]
                    for n in range(int(x), int(y) + 1):
                        rm.append(n)
                elif '!' in i:
                    rm.append(int(i[1:]))

        elif '-' in index and ',' not in index:
            x, y = index.split('-')
            run = [x for x in range(int(x), int(y) + 1)]

        elif ',' in index and '-' not in index:
            splits = index.split(',')
            for sp in splits:
                if '!' in sp:
                    rm.append(int(sp))
                else:
                    run.append(int(sp))

        else:
            if len(all_items) < int(index) or int(index) < \
                    0:
                run = []
            else:
                run = [int(index)]

        run = [i for i in run if i not in rm]
        files = [x for (i, x) in enumerate(all_items) if i in run]

        return files, run

    except ValueError:
        return [], []


class RemoveDialog(QDialog):
    def __init__(self, parentw, mode):
        super().__init__(parentw)
        self.pw = parentw
        self.pr = parentw.mw.pr
        self.mode = mode

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()
        label = QLabel(f'Do you really want to remove the selected {self.mode}?')
        layout.addWidget(label)

        if self.mode == 'MEEG':
            layout.addWidget(SimpleList(self.pr.sel_meeg))
        elif self.mode == 'FSMRI':
            layout.addWidget(SimpleList(self.pr.sel_fsmri))

        only_list_bt = QPushButton('Remove only from List')
        only_list_bt.clicked.connect(partial(self.remove_objects, False))
        layout.addWidget(only_list_bt)
        remove_files_bt = QPushButton('Remove with all Files')
        remove_files_bt.clicked.connect(partial(self.remove_objects, True))
        layout.addWidget(remove_files_bt)
        cancel_bt = QPushButton('Cancel')
        cancel_bt.clicked.connect(self.close)
        layout.addWidget(cancel_bt)
        self.setLayout(layout)

    def remove_objects(self, remove_files):
        if self.mode == 'MEEG':
            for meeg in self.pr.sel_meeg:
                # Remove MEEG from Lists/Dictionaries
                self.pr.all_meeg.remove(meeg)
                self.pr.meeg_to_erm.pop(meeg, None)
                self.pr.meeg_to_fsmri.pop(meeg, None)
                self.pr.all_info.pop(meeg, None)
                self.pr.meeg_bad_channels.pop(meeg, None)
                self.pr.meeg_event_id.pop(meeg, None)
                self.pr.file_parameters.drop(index=[i for i in self.pr.file_parameters.index if meeg in i],
                                             inplace=True)
                if remove_files:
                    try:
                        shutil.rmtree(join(self.pr.data_path, meeg))
                    except FileNotFoundError:
                        print(join(self.pr.data_path, meeg) + ' not found!')
            self.pr.sel_meeg.clear()
            self.pw.meeg_list.content_changed()

        elif self.mode == 'FSMRI':
            for fsmri in self.pr.sel_fsmri:
                self.pr.all_fsmri.remove(fsmri)
                if remove_files:
                    try:
                        shutil.rmtree(join(self.pw.mw.subjects_dir, fsmri))
                    except FileNotFoundError:
                        print(join(self.pw.mw.subjects_dir, fsmri) + ' not found!')
            self.pr.sel_fsmri.clear()
            self.pw.fsmri_list.content_changed()
        self.close()


# Todo: Subject-Selection according to having or not specified Files (Combobox)
class SubjectDock(QDockWidget):
    def __init__(self, main_win):
        super().__init__('Object-Selection', main_win)
        self.mw = main_win
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget(self)
        layout = QVBoxLayout()
        tab_widget = QTabWidget(self)

        idx_example = "Examples:\n" \
                      "'5' (One File)\n" \
                      "'1,7,28' (Several Files)\n" \
                      "'1-5' (From File x to File y)\n" \
                      "'1-4,7,20-26' (The last two combined)\n" \
                      "'1-20,!4-6' (1-20 except 4-6)\n" \
                      "'all' (All files in file_list.py)\n" \
                      "'all,!4-6' (All files except 4-6)"

        # MEEG-List + Index-Line-Edit
        meeg_widget = QWidget()
        meeg_layout = QVBoxLayout()
        self.meeg_list = CheckList(self.mw.pr.all_meeg, self.mw.pr.sel_meeg, ui_button_pos='top', show_index=True,
                                   title='Select MEG/EEG')
        meeg_layout.addWidget(self.meeg_list)

        self.meeg_ledit = QLineEdit()
        self.meeg_ledit.setPlaceholderText('MEEG-Index')
        self.meeg_ledit.textEdited.connect(self.select_meeg)
        self.meeg_ledit.setToolTip(idx_example)
        meeg_layout.addWidget(self.meeg_ledit)

        # Add and Remove-Buttons
        meeg_bt_layout = QHBoxLayout()
        file_add_bt = QPushButton('Add MEEG')
        file_add_bt.clicked.connect(partial(AddFilesDialog, self.mw))
        meeg_bt_layout.addWidget(file_add_bt)
        file_rm_bt = QPushButton('Remove MEEG')
        file_rm_bt.clicked.connect(self.remove_meeg)
        meeg_bt_layout.addWidget(file_rm_bt)

        meeg_layout.addLayout(meeg_bt_layout)
        meeg_widget.setLayout(meeg_layout)

        tab_widget.addTab(meeg_widget, 'MEG/EEG')

        # MRI-Subjects-List + Index-Line-Edit
        fsmri_widget = QWidget()
        fsmri_layout = QVBoxLayout()
        self.fsmri_list = CheckList(self.mw.pr.all_fsmri, self.mw.pr.sel_fsmri, ui_button_pos='top',
                                    show_index=True, title='Select Freesurfer-MRI')
        fsmri_layout.addWidget(self.fsmri_list)

        self.fsmri_ledit = QLineEdit()
        self.fsmri_ledit.setPlaceholderText('FS-MRI-Index')
        self.fsmri_ledit.textEdited.connect(self.select_fsmri)
        self.fsmri_ledit.setToolTip(idx_example)
        fsmri_layout.addWidget(self.fsmri_ledit)

        # Add and Remove-Buttons
        fsmri_bt_layout = QHBoxLayout()
        mri_add_bt = QPushButton('Add FS-MRI')
        mri_add_bt.clicked.connect(partial(AddMRIDialog, self.mw))
        fsmri_bt_layout.addWidget(mri_add_bt)
        mri_rm_bt = QPushButton('Remove FS-MRI')
        mri_rm_bt.clicked.connect(self.remove_fsmri)
        fsmri_bt_layout.addWidget(mri_rm_bt)

        fsmri_layout.addLayout(fsmri_bt_layout)
        fsmri_widget.setLayout(fsmri_layout)

        tab_widget.addTab(fsmri_widget, 'FS-MRI')

        self.ga_widget = GrandAvgWidget(self.mw)
        tab_widget.addTab(self.ga_widget, 'Groups')

        layout.addWidget(tab_widget)
        self.central_widget.setLayout(layout)
        self.setWidget(self.central_widget)

    def update_dock(self):
        # Update lists when rereferenced elsewhere
        self.meeg_list.replace_data(self.mw.pr.all_meeg)
        self.meeg_list.replace_checked(self.mw.pr.sel_meeg)

        self.fsmri_list.replace_data(self.mw.pr.all_fsmri)
        self.fsmri_list.replace_checked(self.mw.pr.sel_fsmri)

        self.ga_widget.update_treew()

    def reload_dock(self):
        self.init_ui()
        self.central_widget.show()

    def select_meeg(self):
        index = self.meeg_ledit.text()
        self.mw.pr.sel_meeg, idxs = index_parser(index, self.mw.pr.all_meeg)
        # Replace _checked in CheckListModel because of rereferencing above
        self.meeg_list.replace_checked(self.mw.pr.sel_meeg)

    def select_fsmri(self):
        index = self.fsmri_ledit.text()
        self.mw.pr.sel_fsmri, idxs = index_parser(index, self.mw.pr.all_fsmri)
        # Replace _checked in CheckListModel because of rereferencing above
        self.fsmri_list.replace_checked(self.mw.pr.sel_fsmri)

    def remove_meeg(self):
        if len(self.mw.pr.sel_meeg) > 0:
            RemoveDialog(self, 'MEEG')

    def remove_fsmri(self):
        if len(self.mw.pr.sel_fsmri) > 0:
            RemoveDialog(self, 'FSMRI')


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
        for group in self.mw.pr.all_groups:
            top_item = QTreeWidgetItem()
            top_item.setText(0, group)
            top_item.setFlags(top_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            if group in self.mw.pr.sel_groups:
                top_item.setCheckState(0, Qt.Checked)
            else:
                top_item.setCheckState(0, Qt.Unchecked)
            for file in self.mw.pr.all_groups[group]:
                sub_item = QTreeWidgetItem(top_item)
                sub_item.setText(0, file)
            top_items.append(top_item)
        self.treew.addTopLevelItems(top_items)

    def get_treew(self):
        new_dict = {}
        self.mw.pr.sel_groups = []
        for top_idx in range(self.treew.topLevelItemCount()):
            top_item = self.treew.topLevelItem(top_idx)
            top_text = top_item.text(0)
            new_dict.update({top_text: []})
            for child_idx in range(top_item.childCount()):
                child_item = top_item.child(child_idx)
                new_dict[top_text].append(child_item.text(0))
            if top_item.checkState(0) == Qt.Checked:
                self.mw.pr.sel_groups.append(top_text)
        self.mw.pr.all_groups = new_dict

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
            msg_box.setWindowTitle('Warning')
            msg_box.setIcon(QMessageBox.Warning)
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
        for item_name in self.mw.pr.all_meeg:
            if item_name not in self.mw.pr.all_groups[self.group.text(0)]:
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


def extract_info(project, raw, new_fname):
    project.all_info[new_fname] = {}
    info_keys = ['ch_names', 'experimenter', 'highpass', 'line_freq', 'gantry_angle', 'lowpass',
                 'utc_offset', 'nchan', 'proj_name', 'sfreq', 'subject_info', 'device_info',
                 'helium_info']
    try:
        for key in info_keys:
            project.all_info[new_fname][key] = raw.info[key]
        # Add arrays of digitization-points and save it to json to make the trans-file-management possible
        # (same digitization = same trans-file)
        if raw.info['dig'] is not None:
            dig_dict = {}
            for dig_point in raw.info['dig']:
                dig_dict[dig_point['ident']] = {}
                dig_dict[dig_point['ident']]['kind'] = dig_point['kind']
                dig_dict[dig_point['ident']]['pos'] = [float(cd) for cd in dig_point['r']]
            project.all_info[new_fname]['dig'] = dig_dict
        project.all_info[new_fname]['meas_date'] = str(raw.info['meas_date'])
        # Some raw-files don't have get_channel_types?
        try:
            project.all_info[new_fname]['ch_types'] = list(set(raw.get_channel_types()))
        except AttributeError:
            project.all_info[new_fname]['ch_types'] = list()
        project.all_info[new_fname]['proj_id'] = int(raw.info['proj_id'])
        project.all_info[new_fname]['n_times'] = raw.n_times
    except (KeyError, TypeError):
        pass


class AddFileSignals(QObject):
    """
    Defines the Signals for the Worker and add_files
    """
    # Worker Signals
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    # Signals for call_functions
    pgbar_n = pyqtSignal(int)
    which_sub = pyqtSignal(str)


class AddFileWorker(Worker):
    def __init__(self, fn, *args, **kwargs):
        self.signal_class = AddFileSignals()
        kwargs['signals'] = {'pgbar_n': self.signal_class.pgbar_n,
                             'which_sub': self.signal_class.which_sub}

        super().__init__(fn, self.signal_class, *args, **kwargs)


# Todo: Enable Drag&Drop
# Todo: Bug, -raw-adden scheint manchmal problematisch
# Todo: Model/View, should solve many problems
class AddFilesWidget(QWidget):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QVBoxLayout()

        self.erm_keywords = ['leer', 'Leer', 'erm', 'ERM', 'empty', 'Empty', 'room', 'Room', 'raum', 'Raum']
        self.supported_file_types = {'.bin': 'Artemis123',
                                     '.cnt': 'Neuroscan',
                                     '.ds': 'CTF',
                                     '.dat': 'Curry',
                                     '.dap': 'Curry',
                                     '.rs3': 'Curry',
                                     '.cdt': 'Curry',
                                     '.cdt.dpa': 'Curry',
                                     '.cdt.cef': 'Curry',
                                     '.cef': 'Curry',
                                     '.edf': 'European',
                                     '.bdf': 'BioSemi',
                                     '.gdf': 'General',
                                     '.sqd': 'Ricoh/KIT',
                                     '.data': 'Nicolet',
                                     '.fif': 'Neuromag',
                                     '.set': 'EEGLAB',
                                     '.vhdr': 'Brainvision',
                                     '.egi': 'EGI',
                                     '.mff': 'EGI',
                                     '.mat': 'Fieldtrip',
                                     '.lay': 'Persyst'}

        self.pd_files = pd.DataFrame([], columns=['Name', 'File-Type', 'Empty-Room?', 'Path'])
        self.load_kwargs = {}

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

        self.view = QTableView()
        self.model = AddFilesModel(self.pd_files)
        self.view.setModel(self.model)

        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view.setToolTip('These .fif-Files can be imported \n'
                             '(the Empty-Room-Measurements should appear here '
                             'too and will be sorted according to the ERM-Keywords)')
        self.layout.addWidget(self.view)

        self.main_bt_layout = QHBoxLayout()
        import_bt = QPushButton('Import', self)
        import_bt.clicked.connect(self.add_files_starter)
        self.main_bt_layout.addWidget(import_bt)
        delete_bt = QPushButton('Remove', self)
        delete_bt.clicked.connect(self.delete_item)
        self.main_bt_layout.addWidget(delete_bt)
        erm_kw_bt = QPushButton('Empty-Room-Keywords')
        erm_kw_bt.clicked.connect(partial(ErmKwDialog, self))
        self.main_bt_layout.addWidget(erm_kw_bt)
        load_arg_bt = QPushButton('Load-Arguments')
        load_arg_bt.clicked.connect(partial(LoadArgDialog, self))
        self.main_bt_layout.addWidget(load_arg_bt)

        self.layout.addLayout(self.main_bt_layout)
        self.setLayout(self.layout)

    def delete_item(self):
        # Sorted indexes in reverse to avoid problems when removing several indices at once
        row_idxs = sorted(set([idx.row() for idx in self.view.selectionModel().selectedIndexes()]), reverse=True)
        for row_idx in row_idxs:
            self.model.removeRow(row_idx)
        # Update pd_files, because reference is changed with model.removeRow()
        self.pd_files = self.model._data

    def update_model(self):
        self.model._data = self.pd_files
        self.model.layoutChanged.emit()

    def insert_files(self, files_list):
        if len(files_list) > 0:
            existing_files = list()

            for file_path in files_list:
                p = Path(file_path)
                file_name = p.stem
                # Get already existing files and skip them
                if file_path in list(self.pd_files['Path']) \
                        or file_name in self.mw.pr.all_meeg \
                        or file_name in self.mw.pr.all_erm:
                    existing_files.append(file_name)
                    continue

                # Remove -raw from name (put stays in file_name and path later)
                if file_name[-4:] == '-raw':
                    file_name = file_name[:-4]

                if any(x in file_name for x in self.erm_keywords):
                    erm = 1
                else:
                    erm = 0

                self.pd_files = self.pd_files.append({'Name': file_name, 'File-Type': p.suffix,
                                                      'Empty-Room?': erm, 'Path': file_path}, ignore_index=True)

            self.update_model()

            if len(existing_files) > 0:
                QMessageBox.information(self, 'Existing Files',
                                        f'These files already exist in your project: {existing_files}')

    def get_files_path(self):
        filter_list = [f'{self.supported_file_types[key]} (*{key})' for key in self.supported_file_types]
        filter_list.append('All Files (*.*)')
        filter_qstring = ';;'.join(filter_list)
        files_list = QFileDialog.getOpenFileNames(self, 'Choose raw-file/s to import', filter=filter_qstring)[0]
        self.insert_files(files_list)

    def get_folder_path(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'Choose a folder to import your raw-Files from (including '
                                                             'subfolders)')
        if folder_path != '':
            # create a list of file and obj directories
            # names in the given directory
            list_of_file = os.walk(folder_path)
            files_list = list()
            # Iterate over all the entries
            for dirpath, dirnames, filenames in list_of_file:
                for file in filenames:
                    for file_type in self.supported_file_types:
                        match = re.match(rf'(.+)({file_type})', file)
                        if match and len(match.group()) == len(file):
                            # Make sure, that no files from Pipeline-Analysis are included
                            if not any(x in file for x in ['-eve.', '-epo.', '-ica.', '-ave.', '-tfr.', '-fwd.',
                                                           '-cov.', '-inv.', '-src.', '-trans.', '-bem-sol.']):
                                files_list.append(join(dirpath, file))
            self.insert_files(files_list)

    def update_erm_checks(self):
        for idx in self.pd_files.index:
            if any(x in self.pd_files.loc[idx, 'Name'] for x in self.erm_keywords):
                self.pd_files.loc[idx, 'Empty-Room?'] = 1
            else:
                self.pd_files.loc[idx, 'Empty-Room?'] = 0
        self.model.layoutChanged.emit()

    def add_files_starter(self):
        self.addf_dialog = QProgressDialog(self)
        self.addf_dialog.setLabelText('Copying Files...')
        self.addf_dialog.setMaximum(len(self.pd_files.index))
        self.addf_dialog.open()

        worker = AddFileWorker(self.add_files)
        worker.signal_class.finished.connect(self.addf_finished)
        worker.signal_class.error.connect(self.show_errors)
        worker.signal_class.pgbar_n.connect(self.addf_dialog.setValue)
        worker.signal_class.which_sub.connect(self.addf_dialog.setLabelText)
        self.mw.threadpool.start(worker)

    def show_errors(self, err):
        ErrorDialog(err, self)

    def add_files(self, signals):

        # Resolve identical file-names (but different types)
        duplicates = [item for item, i_cnt in Counter(list(self.pd_files['Name'])).items() if i_cnt > 1]
        for name in duplicates:
            dupl_df = self.pd_files[self.pd_files['Name'] == name]
            for idx in dupl_df.index:
                self.pd_files.loc[idx, 'Name'] = \
                    self.pd_files.loc[idx, 'Name'] + '-' + self.pd_files.loc[idx, 'File-Type'][1:]

        count = 1
        for idx in self.pd_files.index:
            file = self.pd_files.loc[idx, 'Name']
            if not self.addf_dialog.wasCanceled():
                signals['which_sub'].emit(f'Copying {file}')

                raw = self.load_file(idx)
                extract_info(self.mw.pr, raw, file)

                if not self.addf_dialog.wasCanceled():
                    # Copy Empty-Room-Files to their directory
                    if self.pd_files.loc[idx, 'Empty-Room?']:
                        # Organize ERMs
                        self.mw.pr.all_erm.append(file)
                        save_path = join(self.mw.pr.data_path, 'empty_room_data',
                                         file, file + '-raw.fif')
                    else:
                        # Organize sub_files
                        self.mw.pr.all_meeg.append(file)
                        save_path = join(self.mw.pr.data_path, file,
                                         file + '-raw.fif')
                    # Make sure, that all directories exist
                    parent_dir = Path(save_path).parent
                    os.makedirs(parent_dir, exist_ok=True)
                    # Copy sub_files to destination
                    raw.save(save_path, overwrite=True)
                    signals['pgbar_n'].emit(count)
                    count += 1
                else:
                    break
            else:
                break

    def addf_finished(self):
        self.pd_files = pd.DataFrame([], columns=['Name', 'File-Type', 'Empty-Room?', 'Path'])
        self.update_model()

        self.addf_dialog.close()

        self.mw.pr.save_lists()
        self.mw.subject_dock.update_dock()

    def load_file(self, idx):
        path = self.pd_files.loc[idx, 'Path']
        file_type = self.pd_files.loc[idx, 'File-Type']
        if file_type == '.bin':
            raw = mne.io.read_raw_artemis123(path, preload=True, **self.load_kwargs)
        elif file_type == '.cnt':
            raw = mne.io.read_raw_cnt(path, preload=True, **self.load_kwargs)
        elif file_type == '.ds':
            raw = mne.io.read_raw_ctf(path, preload=True, **self.load_kwargs)
        elif any(f == file_type for f in ['.dat', '.dap', '.rs3', '.cdt', '.cdt.dpa', '.cdt.cef', '.cef']):
            raw = mne.io.read_raw_curry(path, preload=True, **self.load_kwargs)
        elif file_type == '.edf':
            raw = mne.io.read_raw_edf(path, preload=True, **self.load_kwargs)
        elif file_type == '.bdf':
            raw = mne.io.read_raw_bdf(path, preload=True, **self.load_kwargs)
        elif file_type == '.fif':
            raw = mne.io.read_raw_fif(path, preload=True, **self.load_kwargs)
        elif file_type == '.gdf':
            raw = mne.io.read_raw_gdf(path, preload=True, **self.load_kwargs)
        elif file_type == '.sqd':
            raw = mne.io.read_raw_kit(path, preload=True, **self.load_kwargs)
        elif file_type == '.data':
            raw = mne.io.read_raw_nicolet(path, preload=True, **self.load_kwargs)
        elif file_type == '.set':
            raw = mne.io.read_raw_eeglab(path, preload=True, **self.load_kwargs)
        elif file_type == '.vhdr':
            raw = mne.io.read_raw_brainvision(path, preload=True, **self.load_kwargs)
        elif any(f == file_type for f in ['.egi', '.mff']):
            raw = mne.io.read_raw_egi(path, preload=True, **self.load_kwargs)
        elif file_type == '.mat':
            raw = mne.io.read_raw_fieldtrip(path, info=None, **self.load_kwargs)
        # elif file_type == '.lay':
        #     raw = mne.io.read_raw_persyst(path, preload=True, **self.load_kwargs)
        else:
            raw = None
        return raw


class ErmKwDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.layout = QVBoxLayout()
        self.init_ui()

        self.open()

    def init_ui(self):
        self.listw = EditList(self.parent.erm_keywords)
        self.layout.addWidget(self.listw)

        self.close_bt = QPushButton('Close')
        self.close_bt.clicked.connect(self.close)
        self.layout.addWidget(self.close_bt)

        self.setLayout(self.layout)

    def close_dlg(self):
        self.parent.update_erm_checks()
        self.close()


class LoadArgDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.layout = QVBoxLayout()
        self.init_ui()
        self.open()

    def init_ui(self):
        self.edit_dict = EditDict(self.parent.load_kwargs)
        self.layout.addWidget(self.edit_dict)
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        self.layout.addWidget(close_bt)
        self.setLayout(self.layout)


class AddFilesDialog(AddFilesWidget):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.dialog = QDialog(main_win)
        self.dialog.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)

        close_bt = QPushButton('Close', self)
        close_bt.clicked.connect(self.dialog.close)
        self.main_bt_layout.addWidget(close_bt)

        self.dialog.setLayout(self.layout)

        width, height = get_ratio_geometry(0.7)
        self.resize(width, height)

        self.dialog.open()


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

        self.main_bt_layout = QHBoxLayout()
        import_bt = QPushButton('Import', self)
        import_bt.clicked.connect(self.add_mri_subjects_starter)
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
        folder_path = QFileDialog.getExistingDirectory(self, 'Choose a folder with a subject\'s Freesurfe-Segmentation')

        if folder_path != '':
            if exists(join(folder_path, 'surf')):
                fsmri = Path(folder_path).name
                if fsmri not in self.mw.pr.all_fsmri and fsmri not in self.folders:
                    self.folders.append(fsmri)
                    self.paths.update({fsmri: folder_path})
                    self.populate_list_widget()
                else:
                    print(f'{fsmri} already existing in {self.mw.subjects_dir}')
            else:
                print('Selected Folder doesn\'t seem to be a Freesurfer-Segmentation')

    def import_mri_subjects(self):
        parent_folder = QFileDialog.getExistingDirectory(self, 'Choose a folder containting several '
                                                               'Freesurfer-Segmentations')
        folder_list = sorted([f for f in os.listdir(parent_folder) if not f.startswith('.')], key=str.lower)

        for fsmri in folder_list:
            folder_path = join(parent_folder, fsmri)
            if exists(join(folder_path, 'surf')):
                if fsmri not in self.mw.pr.all_fsmri and fsmri not in self.folders:
                    self.folders.append(fsmri)
                    self.paths.update({fsmri: folder_path})
                else:
                    print(f'{fsmri} already existing in {self.mw.subjects_dir}')
            else:
                print('Selected Folder doesn\'t seem to be a Freesurfer-Segmentation')
        self.populate_list_widget()

    def add_mri_subjects_starter(self):
        self.add_mri_dialog = QProgressDialog(self)
        self.add_mri_dialog.setLabelText('Copying Folders...')
        self.add_mri_dialog.setMaximum(len(self.folders))
        self.add_mri_dialog.open()

        worker = AddFileWorker(self.add_mri_subjects)
        worker.signal_class.finished.connect(self.add_mri_finished)
        worker.signal_class.error.connect(self.show_errors)
        worker.signal_class.pgbar_n.connect(self.add_mri_dialog.setValue)
        worker.signal_class.which_sub.connect(self.add_mri_dialog.setLabelText)
        self.mw.threadpool.start(worker)

    def add_mri_subjects(self, signals):
        count = 1
        for fsmri in self.folders:
            if not self.add_mri_dialog.wasCanceled():
                signals['which_sub'].emit(f'Copying {fsmri}')
                src = self.paths[fsmri]
                dst = join(self.mw.subjects_dir, fsmri)
                self.mw.pr.all_fsmri.append(fsmri)
                if not isdir(dst):
                    print(f'Copying Folder from {src}...')
                    try:
                        shutil.copytree(src, dst)
                    except shutil.Error:  # surfaces with .H and .K at the end can't be copied
                        pass
                    print(f'Finished Copying to {dst}')
                else:
                    print(f'{dst} already exists')
                signals['pgbar_n'].emit(count)
                count += 1
            else:
                break

    def show_errors(self, err):
        ErrorDialog(err, self)

    def add_mri_finished(self):
        self.list_widget.clear()
        self.folders = list()
        self.paths = dict()

        self.mw.pr.save_lists()
        self.mw.subject_dock.update_dock()


class AddMRIDialog(AddMRIWidget):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.dialog = QDialog(main_win)

        close_bt = QPushButton('Close', self)
        close_bt.clicked.connect(self.dialog.close)
        self.main_bt_layout.addWidget(close_bt)

        self.dialog.setLayout(self.layout)
        self.dialog.open()


class TmpBrainSignals(QObject):
    """
    Defines the Signals for the Worker and add_files
    """
    # Worker Signals
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    update_lists = pyqtSignal()


class TmpBrainWorker(Worker):
    def __init__(self, fn, *args, **kwargs):
        self.signal_class = TmpBrainSignals()

        kwargs['signals'] = {'update_lists': self.signal_class.update_lists}

        super().__init__(fn, self.signal_class, *args, **kwargs)


class TmpBrainDialog(QDialog):
    def __init__(self, parent_w):
        super().__init__(parent_w)

        self.setWindowTitle('Loading Template-Brain...')
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        self.setLayout(layout)
        self.open()

    def update_text_edit(self, text):
        self.text_edit.insertPlainText(text)
        self.text_edit.ensureCursorVisible()


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
            self.label2 = 'Choose a mri-subject'
        else:
            self.setWindowTitle('Assign files to their ERM-File')
            self.label2 = 'Choose a erm-file'

        self.init_ui()
        self.populate_lists()
        self.get_status()

    def init_ui(self):
        file_label = QLabel('Choose a file', self)
        second_label = QLabel(self.label2, self)

        self.layout.addWidget(file_label, 0, 0)
        self.layout.addWidget(second_label, 0, 1)
        # ListWidgets
        self.list_widget1 = QListWidget(self)
        self.list_widget1.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget2 = QListWidget(self)

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
            test_bt.clicked.connect(self.add_template_brain_starter)
            tb_layout.addWidget(test_bt)

            group_box.setLayout(tb_layout)
            self.bt_layout.addWidget(group_box)

        self.layout.addLayout(self.bt_layout, 0, 2, 2, 1)
        self.setLayout(self.layout)

    def populate_lists(self):
        # Check, that item is not already present (for Wizard-Page)
        for file in [f for f in self.mw.pr.all_meeg if len(self.list_widget1.findItems(f, Qt.MatchExactly)) == 0]:
            self.list_widget1.addItem(file)
        if len(self.list_widget2.findItems('None', Qt.MatchExactly)) == 0:
            self.list_widget2.addItem('None')
        if self.mode == 'mri':
            for file in [f for f in self.mw.pr.all_fsmri
                         if len(self.list_widget2.findItems(f, Qt.MatchExactly)) == 0]:
                self.list_widget2.addItem(file)
        else:
            for file in [f for f in self.mw.pr.all_erm
                         if len(self.list_widget2.findItems(f, Qt.MatchExactly)) == 0]:
                self.list_widget2.addItem(file)

    def get_status(self):
        for idx in range(self.list_widget1.count()):
            item_name = self.list_widget1.item(idx).text()
            if self.mode == 'mri':
                if item_name in self.mw.pr.meeg_to_fsmri:
                    self.list_widget1.item(idx).setBackground(QColor('green'))
                    self.list_widget1.item(idx).setForeground(QColor('white'))
                else:
                    self.list_widget1.item(idx).setBackground(QColor('red'))
                    self.list_widget1.item(idx).setForeground(QColor('white'))
            else:
                if item_name in self.mw.pr.meeg_to_erm:
                    self.list_widget1.item(idx).setBackground(QColor('green'))
                    self.list_widget1.item(idx).setForeground(QColor('white'))
                else:
                    self.list_widget1.item(idx).setBackground(QColor('red'))
                    self.list_widget1.item(idx).setForeground(QColor('white'))

    def add_template_brain_starter(self):
        self.template_brain = self.template_box.currentText()
        self.tmpb_dlg = TmpBrainDialog(self)
        # Redirect stdout to capture it
        sys.stdout.signal.text_written.connect(self.tmpb_dlg.update_text_edit)

        worker = TmpBrainWorker(self.add_template_brain)
        worker.signal_class.finished.connect(self.tmpb_dlg.close)
        worker.signal_class.error.connect(self.show_errors)
        worker.signal_class.update_lists.connect(self.update_lists)
        self.mw.threadpool.start(worker)

    def show_errors(self, err):
        ErrorDialog(err, self)

    def update_lists(self):
        if self.template_brain not in self.mw.pr.all_fsmri:
            self.mw.subject_dock.update_dock()
            self.list_widget2.addItem(self.template_brain)

    def add_template_brain(self, signals):
        if self.template_brain == 'fsaverage':
            mne.datasets.fetch_fsaverage(self.mw.subjects_dir)
            signals['update_lists'].emit()
        else:
            pass

    def sub_dict_selected(self):
        choice = self.list_widget1.currentItem().text()
        if self.mode == 'mri':
            existing_dict = self.mw.pr.meeg_to_fsmri
        else:
            existing_dict = self.mw.pr.meeg_to_erm
        if choice in existing_dict:
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
            existing_dict = self.mw.pr.meeg_to_fsmri
        else:
            existing_dict = self.mw.pr.meeg_to_erm
        for item in choices1:
            item.setBackground(QColor('green'))
            item.setForeground(QColor('white'))
            choice1 = item.text()
            if choice1 in existing_dict:
                existing_dict[choice1] = choice2
            else:
                existing_dict.update({choice1: choice2})
        if self.mode == 'mri':
            self.mw.pr.meeg_to_fsmri = existing_dict
        else:
            self.mw.pr.meeg_to_erm = existing_dict
        self.mw.pr.save_lists()

    def sub_dict_assign_none(self):
        choices = self.list_widget1.selectedItems()
        if self.mode == 'mri':
            existing_dict = self.mw.pr.meeg_to_fsmri
        else:
            existing_dict = self.mw.pr.meeg_to_erm
        for item in choices:
            item.setBackground(QColor('green'))
            item.setForeground(QColor('white'))
            choice = item.text()
            if choice in existing_dict:
                existing_dict[choice] = 'None'
            else:
                existing_dict.update({choice: 'None'})

            none_item = self.list_widget2.findItems('None', Qt.MatchExactly)[0]
            self.list_widget2.setCurrentItem(none_item)

        if self.mode == 'mri':
            self.mw.pr.meeg_to_fsmri = existing_dict
        else:
            self.mw.pr.meeg_to_erm = existing_dict
        self.mw.pr.save_lists()

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
                    self.mw.pr.meeg_to_fsmri = all_items
                elif self.mode == 'erm':
                    self.mw.pr.meeg_to_erm = all_items
            self.mw.pr.save_lists()
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

            none_item = self.list_widget2.findItems('None', Qt.MatchExactly)[0]
            self.list_widget2.setCurrentItem(none_item)

            if self.mode == 'mri':
                self.mw.pr.meeg_to_fsmri = all_items
            elif self.mode == 'erm':
                self.mw.pr.meeg_to_erm = all_items
            self.mw.pr.save_lists()

    def show_assignments(self):
        self.show_ass_dialog = QDialog(self)
        self.show_ass_dialog.setWindowTitle('Assignments')
        layout = QGridLayout()
        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        if self.mode == 'mri':
            the_dict = self.mw.pr.meeg_to_fsmri
        else:
            the_dict = self.mw.pr.meeg_to_erm
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
                self.mw.pr.meeg_to_fsmri.pop(key_text, None)
            else:
                self.mw.pr.meeg_to_erm.pop(key_text, None)

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

        width, height = get_ratio_geometry(0.8)
        self.resize(width, height)

        self.dialog.open()


class SubDictWizPage(QWizardPage):
    def __init__(self, main_win, mode, title):
        super().__init__()

        self.setTitle(title)

        layout = QVBoxLayout()
        self.sub_dict_w = SubDictWidget(main_win, mode)
        layout.addWidget(self.sub_dict_w)
        self.setLayout(layout)

    def initializePage(self):
        self.sub_dict_w.populate_lists()
        self.sub_dict_w.get_status()


class CopyBadsDialog(QDialog):
    def __init__(self, parent_w):
        super().__init__(parent_w)

        self.all_files = parent_w.mw.pr.all_meeg
        self.bad_channels_dict = parent_w.mw.pr.meeg_bad_channels
        self.info_dict = parent_w.mw.pr.all_info

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QGridLayout()

        from_l = QLabel('Copy from:')
        layout.addWidget(from_l, 0, 0)
        to_l = QLabel('Copy to:')
        layout.addWidget(to_l, 0, 1)

        self.copy_from = list()
        self.copy_tos = list()

        self.listw1 = CheckList(self.all_files, self.copy_from, ui_buttons=False, one_check=True)
        self.listw2 = CheckList(self.all_files, self.copy_tos)

        layout.addWidget(self.listw1, 1, 0)
        layout.addWidget(self.listw2, 1, 1)

        copy_bt = QPushButton('Copy')
        copy_bt.clicked.connect(self.copy_bads)
        layout.addWidget(copy_bt, 2, 0)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt, 2, 1)

        self.setLayout(layout)

    def copy_bads(self):
        # Check, that at least one item is selected in each list and that the copy_from-item is in meeg_bad_channels
        if len(self.copy_from) * len(self.copy_tos) > 0 and self.copy_from[0] in self.bad_channels_dict:
            copy_bad_chs = self.bad_channels_dict[self.copy_from[0]].copy()
            for copy_to in self.copy_tos:
                # Make sure, that only channels which exist too in copy_to are copied
                for rm_ch in [r for r in copy_bad_chs if r not in self.info_dict[copy_to]['ch_names']]:
                    copy_bad_chs.remove(rm_ch)
                self.bad_channels_dict[copy_to] = copy_bad_chs


class SubBadsWidget(QWidget):
    """ A Dialog to select Bad-Channels for the files """

    def __init__(self, main_win):
        """
        :param main_win: The parent-window for the dialog
        """
        super().__init__(main_win)
        self.mw = main_win
        self.setWindowTitle('Assign bad_channels for your files')
        self.bad_chkbts = {}
        self.name = None
        self.raw = None
        self.raw_fig = None

        self.init_ui()

    def init_ui(self):
        self.layout = QGridLayout()

        self.files_widget = CheckDictList(self.mw.pr.all_meeg, self.mw.pr.meeg_bad_channels, title='Files')
        self.files_widget.currentChanged.connect(self.bad_dict_selected)
        self.files_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.layout.addWidget(self.files_widget, 0, 0)

        self.bt_scroll = QScrollArea()
        self.bt_scroll.setWidgetResizable(True)
        self.layout.addWidget(self.bt_scroll, 0, 1)

        # Add Buttons
        self.bt_layout = QHBoxLayout()

        plot_bt = QPushButton('Plot Raw')
        plot_bt.clicked.connect(self.plot_raw_bad)
        self.bt_layout.addWidget(plot_bt)

        copy_bt = QPushButton('Copy Bads')
        copy_bt.clicked.connect(partial(CopyBadsDialog, self))
        self.bt_layout.addWidget(copy_bt)

        self.layout.addLayout(self.bt_layout, 1, 0, 1, 2)
        self.setLayout(self.layout)

    def make_bad_chbxs(self):
        chbx_w = QWidget()
        chbx_w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        chbx_layout = QGridLayout()
        row = 0
        column = 0
        h_size = 0
        # Currently, you have to fine-tune the max_h_size, because it doesn't seem to reflect exactly the actual width
        max_h_size = int(self.bt_scroll.geometry().width() * 0.85)

        self.bad_chkbts = dict()

        # Load info into all_info if not already existing
        if self.name not in self.mw.pr.all_info:
            meeg = MEEG(self.name, self.mw)
            raw = meeg.load_raw()
            extract_info(self.mw.pr, raw, self.name)

        # Make Checkboxes for channels from all_info
        for x, ch_name in enumerate(self.mw.pr.all_info[self.name]['ch_names']):
            chkbt = QCheckBox(ch_name, self)
            chkbt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            chkbt.clicked.connect(self.bad_dict_assign)
            self.bad_chkbts.update({ch_name: chkbt})
            h_size += chkbt.sizeHint().width()
            if h_size > max_h_size:
                column = 0
                row += 1
                h_size = chkbt.sizeHint().width()
            chbx_layout.addWidget(chkbt, row, column)
            column += 1

        chbx_w.setLayout(chbx_layout)

        if self.bt_scroll.widget():
            self.bt_scroll.takeWidget()
        self.bt_scroll.setWidget(chbx_w)

    def bad_dict_selected(self, current, _):
        old_name = self.name
        self.name = current

        # Close current Plot-Window
        if self.raw_fig:
            plt.close(self.raw_fig)

        # Reload Bad-Chkbts if other than before
        if self.name in self.mw.pr.all_info and old_name:
            if self.mw.pr.all_info[self.name]['ch_names'] != self.mw.pr.all_info[old_name]['ch_names']:
                self.make_bad_chbxs()
        else:
            self.make_bad_chbxs()

        # Clear entries
        for bt in self.bad_chkbts:
            self.bad_chkbts[bt].setChecked(False)

        # Catch Channels, which are present in meeg_bad_channels, but not in bad_chkbts
        error_list = list()
        # Then load existing bads for choice
        if self.name in self.mw.pr.meeg_bad_channels:
            for bad in self.mw.pr.meeg_bad_channels[self.name]:
                try:
                    self.bad_chkbts[bad].setChecked(True)
                except KeyError:
                    error_list.append(bad)

        for error_ch in error_list:
            self.mw.pr.meeg_bad_channels[self.name].remove(error_ch)

    def bad_dict_assign(self):
        bad_channels = []
        for ch in self.bad_chkbts:
            if self.bad_chkbts[ch].isChecked():
                bad_channels.append(ch)
        self.mw.pr.meeg_bad_channels.update({self.name: bad_channels})
        self.mw.pr.save_lists()
        self.files_widget.content_changed()

    # Todo: Automatic bad-channel-detection
    def plot_raw_bad(self):
        # Use interactiv backend again if show_plots have been turned off before
        matplotlib.use('Qt5Agg')
        meeg = MEEG(self.name, self.mw)
        dialog = QDialog(self)
        dialog.setWindowTitle('Opening...')
        dialog.open()
        self.raw = meeg.load_raw()
        if self.name in self.mw.pr.meeg_bad_channels:
            self.raw.info['bads'] = self.mw.pr.meeg_bad_channels[self.name]
        self.raw_fig = self.raw.plot(n_channels=30, bad_color='red',
                                     scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1), title=self.name)
        # Connect Closing of Matplotlib-Figure to assignment of bad-channels
        self.raw_fig.canvas.mpl_connect('close_event', self.get_selected_bads)
        dialog.close()

    def get_selected_bads(self, evt):
        # evt has to be in parameters, otherwise it won't work
        self.mw.pr.meeg_bad_channels.update({self.name: self.raw.info['bads']})
        self.mw.pr.save_lists()
        # Clear all entries
        for bt in self.bad_chkbts:
            self.bad_chkbts[bt].setChecked(False)
        for ch in self.mw.pr.meeg_bad_channels[self.name]:
            self.bad_chkbts[ch].setChecked(True)
        self.files_widget.content_changed()

    def resizeEvent(self, event):
        if self.name:
            self.make_bad_chbxs()
        event.accept()

    def closeEvent(self, event):
        if self.raw_fig:
            plt.close(self.raw_fig)
            event.accept()
        else:
            event.accept()


class SubBadsDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)

        layout = QVBoxLayout()

        bads_widget = SubBadsWidget(main_win)
        layout.addWidget(bads_widget)

        close_bt = QPushButton('Close', self)
        close_bt.clicked.connect(self.close)
        bads_widget.bt_layout.addWidget(close_bt)

        self.setLayout(layout)

        width, height = get_ratio_geometry(0.8)
        self.resize(width, height)

        self.open()


class SubBadsWizPage(QWizardPage):
    def __init__(self, main_win, title):
        super().__init__()
        self.setTitle(title)

        layout = QVBoxLayout()
        self.sub_bad_w = SubBadsWidget(main_win)
        layout.addWidget(self.sub_bad_w)
        self.setLayout(layout)


class SubjectWizard(QWizard):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        self.setWindowTitle('Subject-Wizard')
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.HaveHelpButton, False)

        width, height = get_ratio_geometry(0.6)
        self.setGeometry(0, 0, width, height)
        self.center()

        self.add_pages()
        self.open()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def add_pages(self):
        self.add_files_page = QWizardPage()
        self.add_files_page.setTitle('Import .fif-Files')
        layout = QVBoxLayout()
        layout.addWidget(AddFilesWidget(self.mw))
        self.add_files_page.setLayout(layout)

        self.add_mri_page = QWizardPage()
        self.add_mri_page.setTitle('Import MRI-Files')
        layout = QVBoxLayout()
        layout.addWidget(AddMRIWidget(self.mw))
        self.add_mri_page.setLayout(layout)

        self.assign_mri_page = SubDictWizPage(self.mw, 'mri', 'Assign File --> MRI')
        self.assign_erm_page = SubDictWizPage(self.mw, 'erm', 'Assign File --> ERM')
        self.assign_bad_channels_page = SubBadsWizPage(self.mw, 'Assign Bad-Channels')

        self.addPage(self.add_files_page)
        self.addPage(self.add_mri_page)
        self.addPage(self.assign_mri_page)
        self.addPage(self.assign_erm_page)
        self.addPage(self.assign_bad_channels_page)


class EventIDGui(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        self.name = None
        self.event_id = dict()
        self.labels = list()
        self.checked_labels = list()

        self.layout = QVBoxLayout()
        self.init_ui()

        self.open()

    def init_ui(self):
        list_layout = QHBoxLayout()

        self.files = CheckDictList(self.mw.pr.all_meeg, self.mw.pr.meeg_event_id, title='Files')
        self.files.currentChanged.connect(self.file_selected)

        list_layout.addWidget(self.files)

        event_id_layout = QVBoxLayout()

        self.event_id_widget = EditDict(self.event_id, ui_buttons=True, title='Event-ID')
        # Connect editing of Event-ID-Table to update of Check-List
        self.event_id_widget.dataChanged.connect(self.update_check_list)
        self.event_id_widget.setToolTip('Add a Trial-Descriptor (as key) for each Event-ID (as value) '
                                        'you want to include it in you analysis.\n'
                                        'You can assign multiple descriptors per ID by '
                                        'separating them by "/"')
        event_id_layout.addWidget(self.event_id_widget)

        self.event_id_label = QLabel()
        event_id_layout.addWidget(self.event_id_label)

        list_layout.addLayout(event_id_layout)

        self.check_widget = CheckList(title='Select IDs')
        list_layout.addWidget(self.check_widget)

        self.layout.addLayout(list_layout)

        bt_layout = QHBoxLayout()

        apply_bt = QPushButton('Apply to')
        apply_bt.clicked.connect(partial(EvIDApply, self))
        bt_layout.addWidget(apply_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        self.layout.addLayout(bt_layout)

        self.setLayout(self.layout)

    def get_event_id(self):
        """Get unique event-ids from events"""
        if self.name in self.mw.pr.meeg_event_id:
            self.event_id = self.mw.pr.meeg_event_id[self.name]
        else:
            self.event_id = dict()
        self.event_id_widget.replace_data(self.event_id)

        try:
            # Load Events from File
            meeg = MEEG(self.name, self.mw, suppress_warnings=True)
            events = meeg.load_events()
        except FileNotFoundError:
            self.event_id_label.setText(f'No events found for {self.name}')
        else:
            ids = np.unique(events[:, 2])
            self.event_id_label.setText(f'Events found: {ids}')

    def save_event_id(self):
        if self.name:
            if len(self.event_id) > 0:
                # Write Event-ID to Project
                self.mw.pr.meeg_event_id[self.name] = self.event_id

                # Get selected Trials and write them to project
                self.mw.pr.sel_event_id[self.name] = self.checked_labels

    def file_selected(self, current, _):
        """Called when File from file_widget is selected"""
        # Save event_id for previous file
        self.save_event_id()

        # Get event-id for selected file and update widget
        self.name = current
        self.get_event_id()

        # Load checked trials
        if self.name in self.mw.pr.sel_event_id:
            self.checked_labels = self.mw.pr.sel_event_id[self.name]
        else:
            self.checked_labels = list()
        self.update_check_list()

    def update_check_list(self):

        # Get selectable trials and update widget
        prelabels = [i.split('/') for i in self.event_id.keys() if i != '']
        if len(prelabels) > 0:
            # Concatenate all lists
            conc_labels = prelabels[0]
            if len(prelabels) > 1:
                for item in prelabels[1:]:
                    conc_labels += item
            # Make sure that only unique labels exist
            self.labels = list(set(conc_labels))

            # Make sure, that only trials, which exist in event_id exist
            for chk_label in self.checked_labels:
                if not any(chk_label in key for key in self.event_id):
                    self.checked_labels.remove(chk_label)
        else:
            self.labels = list()

        self.check_widget.replace_data(self.labels)
        self.check_widget.replace_checked(self.checked_labels)

    def closeEvent(self, event):
        # Save event_id for last selected file
        self.save_event_id()
        event.accept()


class EvIDApply(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.p = parent
        self.apply_to = list()

        self.layout = QVBoxLayout()
        self.init_ui()

        self.open()

    def init_ui(self):
        label = QLabel(f'Apply {self.p.name} to:')
        self.layout.addWidget(label)

        self.check_listw = CheckList(self.p.mw.pr.all_meeg, self.apply_to)
        self.layout.addWidget(self.check_listw)

        bt_layout = QHBoxLayout()

        apply_bt = QPushButton('Apply')
        apply_bt.clicked.connect(self.apply_evid)
        bt_layout.addWidget(apply_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        self.layout.addLayout(bt_layout)
        self.setLayout(self.layout)

    def apply_evid(self):
        for file in self.apply_to:
            # Avoid with copy that CheckList-Model changes selected for all afterwards (same reference)
            self.p.mw.pr.meeg_event_id[file] = self.p.event_id.copy()
            self.p.mw.pr.sel_event_id[file] = self.p.checked_labels.copy()


class CopyTrans(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        # Get MEEGs, where a trans-file is already existing
        self.from_meegs = list()
        for meeg_name in self.mw.pr.all_meeg:
            meeg = MEEG(meeg_name, self.mw)
            if isfile(meeg.trans_path):
                self.from_meegs.append(meeg_name)

        # Get the other MEEGs (wihtout trans-file)
        self.to_meegs = [meeg for meeg in self.mw.pr.all_meeg if meeg not in self.from_meegs]

        self.current_meeg = None
        self.copy_tos = list()

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QGridLayout()

        from_list = SimpleList(self.from_meegs, title='From:')
        from_list.currentChanged.connect(self.from_selected)
        layout.addWidget(from_list, 0, 0)

        self.to_list = CheckList(self.to_meegs, self.copy_tos, ui_button_pos='bottom', title='To:')
        layout.addWidget(self.to_list, 0, 1)

        copy_bt = QPushButton('Copy')
        copy_bt.clicked.connect(self.copy_trans)
        layout.addWidget(copy_bt, 1, 0)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt, 1, 1)

        self.setLayout(layout)

    def from_selected(self, current_meeg):
        self.current_meeg = current_meeg
        self.copy_tos.clear()
        if current_meeg in self.mw.pr.all_info:
            # Get Digitization points, which were stored at import into all_info
            current_dig = self.mw.pr.all_info[current_meeg]['dig']

            # Add all meeg, which have the exact same digitization points
            # (assuming, that they can use the same trans-file)
            for k in self.to_meegs:
                if k not in self.copy_tos and self.mw.pr.all_info[k]['dig'] == current_dig:
                    self.copy_tos.append(k)
        self.to_list.content_changed()

    def copy_trans(self):
        if self.current_meeg:
            meeg = MEEG(self.current_meeg, self.mw)
            from_path = meeg.trans_path

            for copy_to in self.copy_tos:
                to_meeg = MEEG(copy_to, self.mw)
                to_path = to_meeg.trans_path

                shutil.copy2(from_path, to_path)

                self.to_meegs.remove(copy_to)

            self.copy_tos.clear()
            self.to_list.content_changed()
