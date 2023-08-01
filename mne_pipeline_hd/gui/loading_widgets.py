# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import os
import re
import shutil
import time
from collections import Counter
from functools import partial
from os.path import exists, isfile, join
from pathlib import Path

import mne
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)
from matplotlib import pyplot as plt

from mne_pipeline_hd.functions.operations import (
    plot_ica_components,
    plot_ica_overlay,
    plot_ica_properties,
    plot_ica_sources,
)
from mne_pipeline_hd.gui.base_widgets import (
    AssignWidget,
    CheckDictList,
    CheckList,
    EditDict,
    EditList,
    FilePandasTable,
    SimpleDialog,
    SimpleList,
    SimplePandasTable,
)
from mne_pipeline_hd.gui.gui_utils import (
    ErrorDialog,
    Worker,
    WorkerDialog,
    center,
    get_exception_tuple,
    set_ratio_geometry,
    get_user_input_string,
)
from mne_pipeline_hd.gui.models import AddFilesModel
from mne_pipeline_hd.gui.parameter_widgets import ComboGui
from mne_pipeline_hd.pipeline.loading import FSMRI, Group, MEEG
from mne_pipeline_hd.pipeline.pipeline_utils import compare_filep


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
        if index == "":
            return [], []
        elif "all" in index:
            if "," in index:
                splits = index.split(",")
                for sp in splits:
                    if "!" in sp and "-" in sp:
                        x, y = sp.split("-")
                        x = x[1:]
                        for n in range(int(x), int(y) + 1):
                            rm.append(n)
                    elif "!" in sp:
                        rm.append(int(sp[1:]))
                    elif "all" in sp:
                        for i in range(len(all_items)):
                            run.append(i)
            else:
                run = [x for x in range(len(all_items))]

        elif "," in index and "-" in index:
            z = index.split(",")
            for i in z:
                if "-" in i and "!" not in i:
                    x, y = i.split("-")
                    for n in range(int(x), int(y) + 1):
                        run.append(n)
                elif "!" not in i:
                    run.append(int(i))
                elif "!" in i and "-" in i:
                    x, y = i.split("-")
                    x = x[1:]
                    for n in range(int(x), int(y) + 1):
                        rm.append(n)
                elif "!" in i:
                    rm.append(int(i[1:]))

        elif "-" in index and "," not in index:
            x, y = index.split("-")
            run = [x for x in range(int(x), int(y) + 1)]

        elif "," in index and "-" not in index:
            splits = index.split(",")
            for sp in splits:
                if "!" in sp:
                    rm.append(int(sp))
                else:
                    run.append(int(sp))

        else:
            if len(all_items) < int(index) or int(index) < 0:
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
        self.pr = parentw.mw.ct.pr
        self.mode = mode

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()
        label = QLabel(f"Do you really want to remove" f" the selected {self.mode}?")
        layout.addWidget(label)

        if self.mode == "MEEG":
            layout.addWidget(SimpleList(self.pr.sel_meeg))
        elif self.mode == "FSMRI":
            layout.addWidget(SimpleList(self.pr.sel_fsmri))

        only_list_bt = QPushButton("Remove only from List")
        only_list_bt.clicked.connect(partial(self.remove_objects, False))
        layout.addWidget(only_list_bt)
        remove_files_bt = QPushButton("Remove with all Files")
        remove_files_bt.clicked.connect(partial(self.remove_objects, True))
        layout.addWidget(remove_files_bt)
        cancel_bt = QPushButton("Cancel")
        cancel_bt.clicked.connect(self.close)
        layout.addWidget(cancel_bt)
        self.setLayout(layout)

    def remove_objects(self, remove_files):
        if self.mode == "MEEG":
            self.pr.remove_meeg(remove_files)
            self.pw.meeg_list.content_changed()
        elif self.mode == "FSMRI":
            self.pr.remove_fsmri(remove_files)
            self.pw.fsmri_list.content_changed()
        self.close()


# Todo: File-Selection depending on existence of data-objects
class FileDock(QDockWidget):
    def __init__(self, main_win, meeg_view=True, fsmri_view=True, group_view=True):
        super().__init__("Object-Selection", main_win)
        # Maintain main-window as top-level object from which the references to
        # the objects of controller and project are taken.
        self.mw = main_win

        self.meeg_view = meeg_view
        self.fsmri_view = fsmri_view
        self.group_view = group_view
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget(self)
        layout = QVBoxLayout()
        tab_widget = QTabWidget(self)

        idx_example = (
            "Examples:\n"
            "'5' (One File)\n"
            "'1,7,28' (Several Files)\n"
            "'1-5' (From File x to File y)\n"
            "'1-4,7,20-26' (The last two combined)\n"
            "'1-20,!4-6' (1-20 except 4-6)\n"
            "'all' (All files in file_list.py)\n"
            "'all,!4-6' (All files except 4-6)"
        )

        if self.meeg_view:
            # MEEG-List + Index-Line-Edit
            meeg_widget = QWidget()
            meeg_layout = QVBoxLayout()
            self.meeg_list = CheckList(
                self.mw.ct.pr.all_meeg,
                self.mw.ct.pr.sel_meeg,
                ui_button_pos="top",
                show_index=True,
                title="Select MEG/EEG",
            )
            meeg_layout.addWidget(self.meeg_list)

            self.meeg_ledit = QLineEdit()
            self.meeg_ledit.setPlaceholderText("MEEG-Index")
            self.meeg_ledit.textEdited.connect(self.select_meeg)
            self.meeg_ledit.setToolTip(idx_example)
            meeg_layout.addWidget(self.meeg_ledit)

            # Add and Remove-Buttons
            meeg_bt_layout = QHBoxLayout()
            file_add_bt = QPushButton("Add MEEG")
            file_add_bt.clicked.connect(partial(AddFilesDialog, self.mw))
            meeg_bt_layout.addWidget(file_add_bt)
            rename_bt = QPushButton("Rename")
            rename_bt.clicked.connect(self._rename_meeg)
            meeg_bt_layout.addWidget(rename_bt)
            file_rm_bt = QPushButton("Remove MEEG")
            file_rm_bt.clicked.connect(self.remove_meeg)
            meeg_bt_layout.addWidget(file_rm_bt)

            meeg_layout.addLayout(meeg_bt_layout)
            meeg_widget.setLayout(meeg_layout)

            tab_widget.addTab(meeg_widget, "MEG/EEG")

        if self.fsmri_view:
            # MRI-Subjects-List + Index-Line-Edit
            fsmri_widget = QWidget()
            fsmri_layout = QVBoxLayout()
            self.fsmri_list = CheckList(
                self.mw.ct.pr.all_fsmri,
                self.mw.ct.pr.sel_fsmri,
                ui_button_pos="top",
                show_index=True,
                title="Select Freesurfer-MRI",
            )
            fsmri_layout.addWidget(self.fsmri_list)

            self.fsmri_ledit = QLineEdit()
            self.fsmri_ledit.setPlaceholderText("FS-MRI-Index")
            self.fsmri_ledit.textEdited.connect(self.select_fsmri)
            self.fsmri_ledit.setToolTip(idx_example)
            fsmri_layout.addWidget(self.fsmri_ledit)

            # Add and Remove-Buttons
            fsmri_bt_layout = QHBoxLayout()
            mri_add_bt = QPushButton("Add FS-MRI")
            mri_add_bt.clicked.connect(partial(AddMRIDialog, self.mw))
            fsmri_bt_layout.addWidget(mri_add_bt)
            mri_rm_bt = QPushButton("Remove FS-MRI")
            mri_rm_bt.clicked.connect(self.remove_fsmri)
            fsmri_bt_layout.addWidget(mri_rm_bt)

            fsmri_layout.addLayout(fsmri_bt_layout)
            fsmri_widget.setLayout(fsmri_layout)

            tab_widget.addTab(fsmri_widget, "FS-MRI")

        if self.group_view:
            self.ga_widget = GrandAvgWidget(self.mw)
            tab_widget.addTab(self.ga_widget, "Groups")

        layout.addWidget(tab_widget)
        self.central_widget.setLayout(layout)
        self.setWidget(self.central_widget)

    def update_dock(self):
        # Update lists when rereferenced elsewhere
        self.meeg_list.replace_data(self.mw.ct.pr.all_meeg)
        self.meeg_list.replace_checked(self.mw.ct.pr.sel_meeg)

        self.fsmri_list.replace_data(self.mw.ct.pr.all_fsmri)
        self.fsmri_list.replace_checked(self.mw.ct.pr.sel_fsmri)

        self.ga_widget.update_treew()

    def reload_dock(self):
        self.init_ui()
        self.central_widget.show()

    def select_meeg(self):
        index = self.meeg_ledit.text()
        self.mw.ct.pr.sel_meeg, idxs = index_parser(index, self.mw.ct.pr.all_meeg)
        # Replace _checked in CheckListModel because of rereferencing above
        self.meeg_list.replace_checked(self.mw.ct.pr.sel_meeg)

    def select_fsmri(self):
        index = self.fsmri_ledit.text()
        self.mw.ct.pr.sel_fsmri, idxs = index_parser(index, self.mw.ct.pr.all_fsmri)
        # Replace _checked in CheckListModel because of rereferencing above
        self.fsmri_list.replace_checked(self.mw.ct.pr.sel_fsmri)

    def _rename_meeg(self):
        current_meeg = self.meeg_list.get_current()
        if current_meeg is not None:
            meeg = MEEG(current_meeg, self.mw.ct)
            new_name = get_user_input_string("Enter new name:", "Rename")
            if new_name is not None:
                meeg.rename(new_name)
                self.update_dock()

    def remove_meeg(self):
        if len(self.mw.ct.pr.sel_meeg) > 0:
            RemoveDialog(self, "MEEG")

    def remove_fsmri(self):
        if len(self.mw.ct.pr.sel_fsmri) > 0:
            RemoveDialog(self, "FSMRI")


class GrandAvgWidget(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win

        self.init_layout()
        self.update_treew()
        self.get_treew()

    def init_layout(self):
        self.layout = QVBoxLayout()
        self.treew = QTreeWidget()
        self.treew.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treew.itemChanged.connect(self.get_treew)
        self.treew.setColumnCount(1)
        self.treew.setHeaderLabel("Groups:")
        self.layout.addWidget(self.treew)

        self.bt_layout = QHBoxLayout()
        add_g_bt = QPushButton("Add Group")
        add_g_bt.clicked.connect(self.add_group)
        self.bt_layout.addWidget(add_g_bt)
        add_file_bt = QPushButton("Add Files")
        add_file_bt.clicked.connect(self.add_files)
        self.bt_layout.addWidget(add_file_bt)
        self.rm_bt = QPushButton("Remove")
        self.rm_bt.clicked.connect(self.remove_item)
        self.bt_layout.addWidget(self.rm_bt)
        self.layout.addLayout(self.bt_layout)

        self.setLayout(self.layout)

    def update_treew(self):
        self.treew.clear()
        top_items = []
        for group in self.mw.ct.pr.all_groups:
            top_item = QTreeWidgetItem()
            top_item.setText(0, group)
            top_item.setFlags(
                top_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable
            )
            if group in self.mw.ct.pr.sel_groups:
                top_item.setCheckState(0, Qt.Checked)
            else:
                top_item.setCheckState(0, Qt.Unchecked)
            for file in self.mw.ct.pr.all_groups[group]:
                sub_item = QTreeWidgetItem(top_item)
                sub_item.setText(0, file)
            top_items.append(top_item)
        self.treew.addTopLevelItems(top_items)

    def get_treew(self):
        new_dict = {}
        self.mw.ct.pr.sel_groups = []
        for top_idx in range(self.treew.topLevelItemCount()):
            top_item = self.treew.topLevelItem(top_idx)
            top_text = top_item.text(0)
            new_dict.update({top_text: []})
            for child_idx in range(top_item.childCount()):
                child_item = top_item.child(child_idx)
                new_dict[top_text].append(child_item.text(0))
            if top_item.checkState(0) == Qt.Checked:
                self.mw.ct.pr.sel_groups.append(top_text)
        self.mw.ct.pr.all_groups = new_dict

    def add_group(self):
        text = get_user_input_string("Enter the name for a new group:", "New Group")
        if text is not None:
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
            msg_box.setWindowTitle("Warning")
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText("No group has been selected")
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
    def __init__(self, main_win, group, ga_widget):
        super().__init__(ga_widget)
        self.mw = main_win

        self.group = group
        self.ga_widget = ga_widget
        self.setWindowTitle("Select Files to add")

        self.init_ui()

    def init_ui(self):
        dlg_layout = QGridLayout()
        self.listw = QListWidget()
        self.listw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.listw.itemSelectionChanged.connect(self.sel_changed)
        self.load_list()

        dlg_layout.addWidget(self.listw, 0, 0, 1, 4)
        add_bt = QPushButton("Add")
        add_bt.clicked.connect(self.add)
        dlg_layout.addWidget(add_bt, 1, 0)
        all_bt = QPushButton("All")
        all_bt.clicked.connect(self.sel_all)
        dlg_layout.addWidget(all_bt, 1, 1)
        clear_bt = QPushButton("Clear")
        clear_bt.clicked.connect(self.clear)
        dlg_layout.addWidget(clear_bt, 1, 2)
        quit_bt = QPushButton("Quit")
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
        for item_name in self.mw.ct.pr.all_meeg:
            if item_name not in self.mw.ct.pr.all_groups[self.group.text(0)]:
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


# Todo: Enable Drag&Drop
class AddFilesWidget(QWidget):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr
        self.layout = QVBoxLayout()

        self.erm_keywords = [
            "leer",
            "Leer",
            "erm",
            "ERM",
            "empty",
            "Empty",
            "room",
            "Room",
            "raum",
            "Raum",
        ]
        self.supported_file_types = {
            ".*": "All Files",
            ".bin": "Artemis123",
            ".cnt": "Neuroscan",
            ".ds": "CTF",
            ".dat": "Curry",
            ".dap": "Curry",
            ".rs3": "Curry",
            ".cdt": "Curry",
            ".cdt.dpa": "Curry",
            ".cdt.cef": "Curry",
            ".cef": "Curry",
            ".edf": "European",
            ".bdf": "BioSemi",
            ".gdf": "General",
            ".sqd": "Ricoh/KIT",
            ".data": "Nicolet",
            ".fif": "Neuromag",
            ".set": "EEGLAB",
            ".vhdr": "Brainvision",
            ".egi": "EGI",
            ".mff": "EGI",
            ".mat": "Fieldtrip",
            ".lay": "Persyst",
        }

        self.pd_files = pd.DataFrame(
            [], columns=["Name", "File-Type", "Empty-Room?", "Path"]
        )
        self.load_kwargs = {}

        self.init_ui()

    def init_ui(self):
        # Input Buttons
        files_bt = QPushButton("File-Import", self)
        files_bt.clicked.connect(self.get_files_path)
        folder_bt = QPushButton("Folder-Import", self)
        folder_bt.clicked.connect(self.get_folder_path)
        input_bt_layout = QHBoxLayout()
        input_bt_layout.addWidget(files_bt)
        input_bt_layout.addWidget(folder_bt)
        self.layout.addLayout(input_bt_layout)

        self.view = QTableView()
        self.model = AddFilesModel(self.pd_files)
        self.view.setModel(self.model)

        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view.setToolTip(
            "These .fif-Files can be imported \n"
            "(the Empty-Room-Measurements should appear here "
            "too and will be sorted according to the ERM-Keywords)"
        )
        self.layout.addWidget(self.view)

        self.main_bt_layout = QHBoxLayout()
        import_bt = QPushButton("Import", self)
        import_bt.clicked.connect(self.add_files_starter)
        self.main_bt_layout.addWidget(import_bt)
        delete_bt = QPushButton("Remove", self)
        delete_bt.clicked.connect(self.delete_item)
        self.main_bt_layout.addWidget(delete_bt)
        erm_kw_bt = QPushButton("Empty-Room-Keywords")
        erm_kw_bt.clicked.connect(partial(ErmKwDialog, self))
        self.main_bt_layout.addWidget(erm_kw_bt)
        load_arg_bt = QPushButton("Load-Arguments")
        load_arg_bt.clicked.connect(partial(LoadArgDialog, self))
        self.main_bt_layout.addWidget(load_arg_bt)

        self.layout.addLayout(self.main_bt_layout)
        self.setLayout(self.layout)

    def delete_item(self):
        # Sorted indexes in reverse to avoid problems when removing several
        # indices at once
        row_idxs = sorted(
            set([idx.row() for idx in self.view.selectionModel().selectedIndexes()]),
            reverse=True,
        )
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
                if (
                    file_path in list(self.pd_files["Path"])
                    or file_name in self.pr.all_meeg
                    or file_name in self.pr.all_erm
                ):
                    existing_files.append(file_name)
                    continue

                # Remove -raw from name (put stays in file_name and path later)
                if file_name[-4:] == "-raw":
                    file_name = file_name[:-4]

                if any(x in file_name for x in self.erm_keywords):
                    erm = 1
                else:
                    erm = 0

                self.pd_files = pd.concat(
                    [
                        self.pd_files,
                        pd.DataFrame(
                            [
                                {
                                    "Name": file_name,
                                    "File-Type": p.suffix,
                                    "Empty-Room?": erm,
                                    "Path": file_path,
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )

            self.update_model()

            if len(existing_files) > 0:
                QMessageBox.information(
                    self,
                    "Existing Files",
                    f"These files already exist in your meeg.pr:" f"{existing_files}",
                )

    def get_files_path(self):
        filter_list = [
            f"{self.supported_file_types[key]} (*{key})"
            for key in self.supported_file_types
        ]
        filter_list.insert(0, "All Files (*.*)")
        filter_qstring = ";;".join(filter_list)
        files_list = QFileDialog.getOpenFileNames(
            self, "Choose raw-file/s to import", filter=filter_qstring
        )[0]
        self.insert_files(files_list)

    def get_folder_path(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Choose a folder to import your raw-Files from " "(including subfolders)",
        )
        if folder_path != "":
            # create a list of file and obj directories
            # names in the given directory
            list_of_file = os.walk(folder_path)
            files_list = list()
            # Iterate over all the entries
            for dirpath, _, filenames in list_of_file:
                for file in filenames:
                    for file_type in self.supported_file_types:
                        match = re.match(rf"(.+)({file_type})", file)
                        if match and len(match.group()) == len(file):
                            # Make sure, that no files from Pipeline-Analysis
                            # are included
                            if not any(
                                x in file
                                for x in [
                                    "-eve.",
                                    "-epo.",
                                    "-ica.",
                                    "-ave.",
                                    "-tfr.",
                                    "-fwd.",
                                    "-cov.",
                                    "-inv.",
                                    "-src.",
                                    "-trans.",
                                    "-bem-sol.",
                                ]
                            ):
                                files_list.append(join(dirpath, file))
            self.insert_files(files_list)

    def update_erm_checks(self):
        for idx in self.pd_files.index:
            if any(x in self.pd_files.loc[idx, "Name"] for x in self.erm_keywords):
                self.pd_files.loc[idx, "Empty-Room?"] = 1
            else:
                self.pd_files.loc[idx, "Empty-Room?"] = 0
        self.model.layoutChanged.emit()

    def add_files(self, worker_signals):
        # Resolve identical file-names (but different types)
        duplicates = [
            item
            for item, i_cnt in Counter(list(self.pd_files["Name"])).items()
            if i_cnt > 1
        ]
        for name in duplicates:
            dupl_df = self.pd_files[self.pd_files["Name"] == name]
            for idx in dupl_df.index:
                self.pd_files.loc[idx, "Name"] = (
                    self.pd_files.loc[idx, "Name"]
                    + "-"
                    + self.pd_files.loc[idx, "File-Type"][1:]
                )

        worker_signals.pgbar_max.emit(len(self.pd_files.index))

        for n, idx in enumerate(self.pd_files.index):
            name = self.pd_files.loc[idx, "Name"]
            if not worker_signals.was_canceled:
                worker_signals.pgbar_text.emit(f"Copying {name}")
                file_path = self.pd_files.loc[idx, "Path"]
                is_erm = self.pd_files.loc[idx, "Empty-Room?"]
                self.pr.add_meeg(name, file_path, is_erm)
                worker_signals.pgbar_n.emit(n + 1)
            else:
                print("Canceled Loading")
                break

    def add_files_starter(self):
        WorkerDialog(
            self, self.add_files, show_buttons=True, show_console=True, blocking=True
        )

        self.pd_files = pd.DataFrame(
            [], columns=["Name", "File-Type", "Empty-Room?", "Path"]
        )
        self.update_model()

        self.pr.save()
        self.mw.file_dock.update_dock()


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

        self.close_bt = QPushButton("Close")
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
        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        self.layout.addWidget(close_bt)
        self.setLayout(self.layout)


class AddFilesDialog(AddFilesWidget):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.dialog = QDialog(main_win)
        self.dialog.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)

        close_bt = QPushButton("Close", self)
        close_bt.clicked.connect(self.dialog.close)
        self.main_bt_layout.addWidget(close_bt)

        self.dialog.setLayout(self.layout)

        set_ratio_geometry(0.7, self)

        self.dialog.open()


class AddMRIWidget(QWidget):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr
        self.layout = QVBoxLayout()

        self.folders = list()
        self.paths = dict()

        self.init_ui()

    def init_ui(self):
        bt_layout = QHBoxLayout()
        folder_bt = QPushButton("Import 1 FS-Segmentation", self)
        folder_bt.clicked.connect(self.import_mri_subject)
        bt_layout.addWidget(folder_bt)
        folders_bt = QPushButton("Import >1 FS-Segmentations", self)
        folders_bt.clicked.connect(self.import_mri_subjects)
        bt_layout.addWidget(folders_bt)
        self.layout.addLayout(bt_layout)

        list_label = QLabel("These Freesurfer-Segmentations can be imported:", self)
        self.layout.addWidget(list_label)
        self.list_widget = QListWidget(self)
        self.layout.addWidget(self.list_widget)

        self.main_bt_layout = QHBoxLayout()
        import_bt = QPushButton("Import", self)
        import_bt.clicked.connect(self.add_mri_subjects_starter)
        self.main_bt_layout.addWidget(import_bt)
        rename_bt = QPushButton("Rename File", self)
        rename_bt.clicked.connect(self.rename_item)
        self.main_bt_layout.addWidget(rename_bt)
        delete_bt = QPushButton("Delete File", self)
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
        folder_path = QFileDialog.getExistingDirectory(
            self, "Choose a folder with a subject's Freesurfe-Segmentation"
        )

        if folder_path != "":
            if exists(join(folder_path, "surf")):
                fsmri = Path(folder_path).name
                if fsmri not in self.pr.all_fsmri and fsmri not in self.folders:
                    self.folders.append(fsmri)
                    self.paths.update({fsmri: folder_path})
                    self.populate_list_widget()
                else:
                    print(f"{fsmri} already existing in {self.ct.subjects_dir}")
            else:
                print("Selected Folder doesn't seem to " "be a Freesurfer-Segmentation")

    def import_mri_subjects(self):
        parent_folder = QFileDialog.getExistingDirectory(
            self, "Choose a folder containting several " "Freesurfer-Segmentations"
        )
        folder_list = sorted(
            [f for f in os.listdir(parent_folder) if not f.startswith(".")],
            key=str.lower,
        )

        for fsmri in folder_list:
            folder_path = join(parent_folder, fsmri)
            if exists(join(folder_path, "surf")):
                if fsmri not in self.pr.all_fsmri and fsmri not in self.folders:
                    self.folders.append(fsmri)
                    self.paths.update({fsmri: folder_path})
                else:
                    print(f"{fsmri} already existing in {self.ct.subjects_dir}")
            else:
                print("Selected Folder doesn't seem to be " "a Freesurfer-Segmentation")
        self.populate_list_widget()

    def add_mri_subjects(self, worker_signals):
        worker_signals.pgbar_max.emit(len(self.folders))
        for n, name in enumerate(self.folders):
            if not worker_signals.was_canceled:
                worker_signals.pgbar_text.emit(f"Copying {name}")
                src = self.paths[name]
                self.pr.add_fsmri(name, src)
                worker_signals.pgbar_n.emit(n)
            else:
                break

    def show_errors(self, err):
        ErrorDialog(err, self)

    def add_mri_subjects_starter(self):
        WorkerDialog(self, self.add_mri_subjects, blocking=True)

        self.list_widget.clear()
        self.folders = list()
        self.paths = dict()

        self.pr.save()
        self.mw.file_dock.update_dock()


class AddMRIDialog(AddMRIWidget):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.dialog = QDialog(main_win)

        close_bt = QPushButton("Close", self)
        close_bt.clicked.connect(self.dialog.close)
        self.main_bt_layout.addWidget(close_bt)

        self.dialog.setLayout(self.layout)
        self.dialog.open()


class FileDictWidget(QWidget):
    def __init__(self, main_win, mode):
        """A widget to assign MRI-Subjects or Empty-Room-Files to file(s)"""

        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr
        self.mode = mode
        if mode == "mri":
            self.title = "Assign MEEG-Files to a FreeSurfer-Subject"
            self.subtitles = ("Choose a MEEG-File", "Choose a FreeSurfer-Subject")
        else:
            self.title = "Assign MEEG-File to a Empty-Room-File"
            self.subtitles = ("Choose a MEEG-File", "Choose an Empty-Room-File")

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        if self.mode == "mri":
            assign_widget = AssignWidget(
                self.pr.all_meeg,
                self.pr.all_fsmri,
                self.pr.meeg_to_fsmri,
                title=self.title,
                subtitles=self.subtitles,
            )
        else:
            assign_widget = AssignWidget(
                self.pr.all_meeg,
                self.pr.all_erm,
                self.pr.meeg_to_erm,
                title=self.title,
                subtitles=self.subtitles,
            )
        layout.addWidget(assign_widget)

        self.setLayout(layout)


class FileDictDialog(FileDictWidget):
    def __init__(self, main_win, mode):
        super().__init__(main_win, mode)

        dialog = QDialog(main_win)

        close_bt = QPushButton("Close", self)
        close_bt.clicked.connect(dialog.close)
        self.layout().addWidget(close_bt)

        dialog.setLayout(self.layout())

        set_ratio_geometry(0.6, self)

        dialog.open()


class FileDictWizardPage(QWizardPage):
    def __init__(self, main_win, mode, title):
        super().__init__()

        self.setTitle(title)

        layout = QVBoxLayout()
        self.sub_dict_w = FileDictWidget(main_win, mode)
        layout.addWidget(self.sub_dict_w)
        self.setLayout(layout)


class CopyBadsDialog(QDialog):
    def __init__(self, parent_w):
        super().__init__(parent_w)

        self.parent_w = parent_w
        self.all_files = parent_w.pr.all_meeg + parent_w.pr.all_erm
        self.bad_channels_dict = parent_w.pr.meeg_bad_channels

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QGridLayout()

        from_l = QLabel("Copy from:")
        layout.addWidget(from_l, 0, 0)
        to_l = QLabel("Copy to:")
        layout.addWidget(to_l, 0, 1)

        # Preselect the current selected MEEG
        self.copy_from = [self.parent_w.current_obj.name]
        self.copy_tos = list()

        self.listw1 = CheckList(
            self.all_files, self.copy_from, ui_buttons=False, one_check=True
        )
        self.listw2 = CheckList(self.all_files, self.copy_tos)

        layout.addWidget(self.listw1, 1, 0)
        layout.addWidget(self.listw2, 1, 1)

        copy_bt = QPushButton("Copy")
        copy_bt.clicked.connect(self.copy_bads)
        layout.addWidget(copy_bt, 2, 0)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt, 2, 1)

        self.setLayout(layout)

    def copy_bads(self):
        # Check, that at least one item is selected in each list
        # and that the copy_from-item is in meeg_bad_channels
        if (
            len(self.copy_from) * len(self.copy_tos) > 0
            and self.copy_from[0] in self.bad_channels_dict
        ):
            for copy_to in self.copy_tos:
                copy_bad_chs = self.bad_channels_dict[self.copy_from[0]].copy()
                copy_to_info = MEEG(copy_to, self.parent_w.mw.ct).load_info()
                # Make sure, that only channels which exist too
                # in copy_to are copied
                for rm_ch in [
                    r for r in copy_bad_chs if r not in copy_to_info["ch_names"]
                ]:
                    copy_bad_chs.remove(rm_ch)
                self.bad_channels_dict[copy_to] = copy_bad_chs


class SubBadsWidget(QWidget):
    """A Dialog to select Bad-Channels for the files"""

    def __init__(self, main_win):
        """
        :param main_win: The parent-window for the dialog
        """
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr
        self.setWindowTitle("Assign bad_channels for your files")
        self.bad_chkbts = dict()
        self.info_dict = dict()
        self.current_obj = None
        self.raw = None
        self.raw_fig = None

        self.init_ui()

    def init_ui(self):
        self.layout = QGridLayout()

        file_list = self.pr.all_meeg
        self.files_widget = CheckDictList(
            file_list, self.pr.meeg_bad_channels, title="Files"
        )
        self.files_widget.currentChanged.connect(self.bad_dict_selected)
        self.files_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.layout.addWidget(self.files_widget, 0, 0)

        self.bt_scroll = QScrollArea()
        self.bt_scroll.setWidgetResizable(True)
        self.layout.addWidget(self.bt_scroll, 0, 1)

        # Add Buttons
        self.bt_layout = QHBoxLayout()

        plot_bt = QPushButton("Plot raw")
        plot_bt.clicked.connect(self.plot_raw_bad)
        self.bt_layout.addWidget(plot_bt)

        copy_bt = QPushButton("Copy Bads")
        copy_bt.clicked.connect(partial(CopyBadsDialog, self))
        self.bt_layout.addWidget(copy_bt)

        self.save_raw_annot = QCheckBox("Save Annotations")
        self.bt_layout.addWidget(self.save_raw_annot)

        self.layout.addLayout(self.bt_layout, 1, 0, 1, 2)
        self.setLayout(self.layout)

    def update_selection(self):
        # Clear entries
        for bt in self.bad_chkbts:
            self.bad_chkbts[bt].setChecked(False)

        # Catch Channels, which are present in meeg_bad_channels,
        # but not in bad_chkbts
        # Then load existing bads for choice
        for bad in self.current_obj.bad_channels:
            if bad in self.bad_chkbts:
                self.bad_chkbts[bad].setChecked(True)
            else:
                # Remove bad channel from bad_channels if not existing
                # in bad_chkbts (and thus not in ch_names)
                self.current_obj.bad_channels.remove(bad)

    def _make_bad_chbxs(self, info):
        time.sleep(1)
        # Store info in dictionary
        self.info_dict[self.current_obj.name] = info

        chbx_w = QWidget()
        chbx_w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.chbx_layout = QGridLayout()
        row = 0
        column = 0
        h_size = 0
        # Currently, you have to fine-tune the max_h_size,
        # because it doesn't seem to reflect exactly the actual width
        max_h_size = int(self.bt_scroll.geometry().width() * 0.85)

        self.bad_chkbts = dict()

        # Make Checkboxes for channels in info
        for ch_name in info["ch_names"]:
            chkbt = QCheckBox(ch_name)
            chkbt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            chkbt.clicked.connect(self.bad_ckbx_assigned)
            self.bad_chkbts[ch_name] = chkbt
            h_size += chkbt.sizeHint().width()
            if h_size > max_h_size:
                column = 0
                row += 1
                h_size = chkbt.sizeHint().width()
            self.chbx_layout.addWidget(chkbt, row, column)
            column += 1

        chbx_w.setLayout(self.chbx_layout)

        # Remove previous buttons if existing
        if self.bt_scroll.widget():
            self.bt_scroll.takeWidget()

        self.bt_scroll.setWidget(chbx_w)
        self.update_selection()

    def make_bad_chbxs(self):
        if self.current_obj:
            # Don't load info twice from file
            if self.current_obj.name in self.info_dict:
                self._make_bad_chbxs(self.info_dict[self.current_obj.name])
            else:
                worker_dlg = WorkerDialog(
                    self, self.current_obj.load_info, title="Loading Channels..."
                )
                worker_dlg.thread_finished.connect(self._make_bad_chbxs)

    def bad_dict_selected(self, current, _):
        self.current_obj = MEEG(current, self.ct)

        # Close current Plot-Window
        if self.raw_fig:
            if hasattr(self.raw_fig, "canvas"):
                plt.close(self.raw_fig)
            else:
                self.raw_fig.close()

        self.make_bad_chbxs()

    def _assign_bad_channels(self, bad_channels):
        # Directly replace value in bad_channels_dict
        # (needed for first-time assignment)
        self.current_obj.pr.meeg_bad_channels[self.current_obj.name] = bad_channels
        # Restore/Establish reference to direct object-attribute
        self.current_obj.bad_channels = bad_channels
        self.files_widget.content_changed()

    def bad_ckbx_assigned(self):
        bad_channels = [ch for ch in self.bad_chkbts if self.bad_chkbts[ch].isChecked()]
        self._assign_bad_channels(bad_channels)

    def set_chkbx_enable(self, enable):
        for chkbx in self.bad_chkbts:
            self.bad_chkbts[chkbx].setEnabled(enable)

    def get_selected_bads(self, _):
        # In-Place-Operations to maintain reference
        # from current_obj to meeg_bad_channels
        bad_channels = self.raw.info["bads"]
        self._assign_bad_channels(bad_channels)
        self.update_selection()
        self.set_chkbx_enable(True)

        if self.save_raw_annot.isChecked():
            WorkerDialog(
                self,
                self.current_obj.save_raw,
                raw=self.raw,
                show_console=True,
                title="Saving raw with Annotations",
            )

        self.raw_fig = None

    def plot_raw_bad(self):
        # Disable CheckBoxes to avoid confusion
        # (Bad-Selection only goes unidirectional from Plot>GUI)
        self.set_chkbx_enable(False)

        plot_dialog = QDialog(self)
        plot_dialog.setWindowTitle("Opening raw-Plot...")
        plot_dialog.open()
        self.raw = self.current_obj.load_raw()
        try:
            events = self.current_obj.load_events()
        except FileNotFoundError:
            events = None
        self.raw_fig = self.raw.plot(
            events=events, n_channels=30, bad_color="red", title=self.current_obj.name
        )
        if hasattr(self.raw_fig, "canvas"):
            # Connect Closing of Matplotlib-Figure
            # to assignment of bad-channels
            self.raw_fig.canvas.mpl_connect("close_event", self.get_selected_bads)
        else:
            self.raw_fig.gotClosed.connect(partial(self.get_selected_bads, None))
        plot_dialog.close()

    def resizeEvent(self, event):
        if self.current_obj:
            self.make_bad_chbxs()
            self.update_selection()
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

        close_bt = QPushButton("Close", self)
        close_bt.clicked.connect(self.close)
        bads_widget.bt_layout.addWidget(close_bt)

        self.setLayout(layout)

        set_ratio_geometry(0.8, self)

        self.show()


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

        self.setWindowTitle("Subject-Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.HaveHelpButton, False)

        set_ratio_geometry(0.6, self)
        center(self)

        self.add_pages()
        self.open()

    def add_pages(self):
        self.add_files_page = QWizardPage()
        self.add_files_page.setTitle("Import .fif-Files")
        layout = QVBoxLayout()
        layout.addWidget(AddFilesWidget(self.mw))
        self.add_files_page.setLayout(layout)

        self.add_mri_page = QWizardPage()
        self.add_mri_page.setTitle("Import MRI-Files")
        layout = QVBoxLayout()
        layout.addWidget(AddMRIWidget(self.mw))
        self.add_mri_page.setLayout(layout)

        self.assign_mri_page = FileDictWizardPage(self.mw, "mri", "Assign File --> MRI")
        self.assign_erm_page = FileDictWizardPage(self.mw, "erm", "Assign File --> ERM")
        self.assign_bad_channels_page = SubBadsWizPage(self.mw, "Assign Bad-Channels")

        self.addPage(self.add_files_page)
        self.addPage(self.add_mri_page)
        self.addPage(self.assign_mri_page)
        self.addPage(self.assign_erm_page)
        self.addPage(self.assign_bad_channels_page)


class EventIDGui(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr

        self.name = None
        self.event_id = dict()
        self.labels = list()
        self.checked_labels = list()

        self.layout = QVBoxLayout()
        self.init_ui()

        self.open()

    def init_ui(self):
        list_layout = QHBoxLayout()

        self.files = CheckDictList(
            self.pr.all_meeg, self.pr.meeg_event_id, title="Files"
        )
        self.files.currentChanged.connect(self.file_selected)

        list_layout.addWidget(self.files)

        event_id_layout = QVBoxLayout()

        self.event_id_widget = EditDict(
            self.event_id, ui_buttons=True, title="Event-ID"
        )
        # Connect editing of Event-ID-Table to update of Check-List
        self.event_id_widget.dataChanged.connect(self.update_check_list)
        self.event_id_widget.setToolTip(
            "Add a Trial-Descriptor (as key) for each Event-ID (as value) "
            "you want to include it in you analysis.\n"
            "You can assign multiple descriptors per ID by "
            'separating them by "/"'
        )
        event_id_layout.addWidget(self.event_id_widget)

        self.event_id_label = QLabel()
        event_id_layout.addWidget(self.event_id_label)

        list_layout.addLayout(event_id_layout)

        self.check_widget = CheckList(title="Select IDs")
        list_layout.addWidget(self.check_widget)

        self.layout.addLayout(list_layout)

        bt_layout = QHBoxLayout()

        apply_bt = QPushButton("Apply to")
        apply_bt.clicked.connect(partial(EvIDApply, self))
        bt_layout.addWidget(apply_bt)

        show_events = QPushButton("Show events")
        show_events.clicked.connect(self.show_events)
        bt_layout.addWidget(show_events)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        self.layout.addLayout(bt_layout)

        self.setLayout(self.layout)

    def get_event_id(self):
        """Get unique event-ids from events"""
        if self.name in self.pr.meeg_event_id:
            self.event_id = self.pr.meeg_event_id[self.name]
        else:
            self.event_id = dict()
        self.event_id_widget.replace_data(self.event_id)

        try:
            # Load events from File
            meeg = MEEG(self.name, self.ct, suppress_warnings=True)
            events = meeg.load_events()
        except FileNotFoundError:
            self.event_id_label.setText(f"No events found for {self.name}")
        else:
            ids = np.unique(events[:, 2])
            self.event_id_label.setText(f"events found: {ids}")

    def save_event_id(self):
        if self.name:
            if len(self.event_id) > 0:
                # Write Event-ID to Project
                self.pr.meeg_event_id[self.name] = self.event_id

                # Get selected Trials and write them to meeg.pr
                self.pr.sel_event_id[self.name] = self.checked_labels

    def file_selected(self, current, _):
        """Called when File from file_widget is selected"""
        # Save event_id for previous file
        self.save_event_id()

        # Get event-id for selected file and update widget
        self.name = current
        self.get_event_id()

        # Load checked trials
        if self.name in self.pr.sel_event_id:
            self.checked_labels = self.pr.sel_event_id[self.name]
        else:
            self.checked_labels = list()
        self.update_check_list()

    def update_check_list(self):
        # Get selectable trials and update widget
        prelabels = [i.split("/") for i in self.event_id.keys() if i != ""]
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

    def show_events(self):
        try:
            meeg = MEEG(self.name, self.ct, suppress_warnings=True)
            events = meeg.load_events()
            mne.viz.plot_events(events, event_id=self.event_id or None, show=True)
        except FileNotFoundError:
            QMessageBox.warning(self, "No events!", f"No events found for {self.name}")

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
        label = QLabel(f"Apply {self.p.name} to:")
        self.layout.addWidget(label)

        self.check_listw = CheckList(self.p.pr.all_meeg, self.apply_to)
        self.layout.addWidget(self.check_listw)

        bt_layout = QHBoxLayout()

        apply_bt = QPushButton("Apply")
        apply_bt.clicked.connect(self.apply_evid)
        bt_layout.addWidget(apply_bt)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        self.layout.addLayout(bt_layout)
        self.setLayout(self.layout)

    def apply_evid(self):
        for file in self.apply_to:
            # Avoid with copy that CheckList-Model changes selected
            # for all afterwards (same reference)
            self.p.pr.meeg_event_id[file] = self.p.event_id.copy()
            self.p.pr.sel_event_id[file] = self.p.checked_labels.copy()


class CopyTrans(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr

        # Get MEEGs, where a trans-file is already existing
        self.from_meegs = list()
        for meeg_name in self.pr.all_meeg:
            meeg = MEEG(meeg_name, self.ct)
            if isfile(meeg.trans_path):
                self.from_meegs.append(meeg_name)

        # Get the other MEEGs (wihtout trans-file)
        self.to_meegs = [
            meeg for meeg in self.pr.all_meeg if meeg not in self.from_meegs
        ]

        self.current_meeg = None
        self.copy_tos = list()

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QGridLayout()

        from_list = SimpleList(self.from_meegs, title="From:")
        from_list.currentChanged.connect(self.from_selected)
        layout.addWidget(from_list, 0, 0)

        self.to_list = CheckList(
            self.to_meegs, self.copy_tos, ui_button_pos="bottom", title="To:"
        )
        layout.addWidget(self.to_list, 0, 1)

        copy_bt = QPushButton("Copy")
        copy_bt.clicked.connect(self.copy_trans)
        layout.addWidget(copy_bt, 1, 0)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt, 1, 1)

        self.setLayout(layout)

    def _compare_digs(self, worker_signals):
        self.copy_tos.clear()
        # Get Digitization points
        current_dig = self.current_meeg.load_info()["dig"]

        # Add all meeg, which have the exact same digitization points
        # (assuming, that they can use the same trans-file)
        worker_signals.pgbar_max.emit(len(self.to_meegs))
        for n, to_meeg in enumerate(self.to_meegs):
            worker_signals.pgbar_text.emit(f"Comparing: {to_meeg}")
            if MEEG(to_meeg, self.ct).load_info()["dig"] == current_dig:
                self.copy_tos.append(to_meeg)
            worker_signals.pgbar_n.emit(n + 1)

        self.to_list.content_changed()

    def from_selected(self, current_meeg):
        self.current_meeg = MEEG(current_meeg, self.ct)
        WorkerDialog(self, self._compare_digs, show_buttons=False, show_console=False)

    def copy_trans(self):
        if self.current_meeg:
            from_path = self.current_meeg.trans_path

            for copy_to in self.copy_tos:
                to_meeg = MEEG(copy_to, self.ct)
                to_path = to_meeg.trans_path

                shutil.copy2(from_path, to_path)

                self.to_meegs.remove(copy_to)

            self.copy_tos.clear()
            self.to_list.content_changed()


class FileManagment(QDialog):
    """A Dialog for File-Management

    Parameters
    ----------
    main_win
        A reference to Main-Window
    """

    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr

        self.load_prog = 0

        self.pd_meeg = pd.DataFrame(index=self.pr.all_meeg)
        self.pd_meeg_time = pd.DataFrame(index=self.pr.all_meeg)
        self.pd_meeg_size = pd.DataFrame(index=self.pr.all_meeg)

        self.pd_fsmri = pd.DataFrame(index=self.pr.all_fsmri)
        self.pd_fsmri_time = pd.DataFrame(index=self.pr.all_fsmri)
        self.pd_fsmri_size = pd.DataFrame(index=self.pr.all_fsmri)

        self.pd_group = pd.DataFrame(index=self.pr.all_groups)
        self.pd_group_time = pd.DataFrame(index=self.pr.all_groups)
        self.pd_group_size = pd.DataFrame(index=self.pr.all_groups)

        self.param_results = dict()

        self.init_ui()

        set_ratio_geometry(0.8, self)
        self.show()

        self.start_load_threads()

    def get_file_tables(self, kind):
        if kind == "MEEG":
            obj_list = self.pr.all_meeg
            obj_pd = self.pd_meeg
            obj_pd_time = self.pd_meeg_time
            obj_pd_size = self.pd_meeg_size
        elif kind == "FSMRI":
            obj_list = self.pr.all_fsmri
            obj_pd = self.pd_fsmri
            obj_pd_time = self.pd_fsmri_time
            obj_pd_size = self.pd_fsmri_size
        else:
            obj_list = self.pr.all_groups
            obj_pd = self.pd_group
            obj_pd_time = self.pd_group_time
            obj_pd_size = self.pd_group_size
        print(f"Loading {kind}")

        for obj_name in obj_list:
            if kind == "MEEG":
                obj = MEEG(obj_name, self.ct)
            elif kind == "FSMRI":
                obj = FSMRI(obj_name, self.ct)
            else:
                obj = Group(obj_name, self.ct)

            obj.get_existing_paths()
            self.param_results[obj_name] = dict()

            for path_type in obj.existing_paths:
                if len(obj.existing_paths[path_type]) > 0:
                    obj_pd.loc[obj_name, path_type] = "exists"
                    obj_pd_size.loc[obj_name, path_type] = 0

                    for path in obj.existing_paths[path_type]:
                        try:
                            # Add Time
                            # Last entry in TIME should be the most recent one
                            obj_pd_time.loc[obj_name, path_type] = obj.file_parameters[
                                Path(path).name
                            ]["TIME"]
                            # Add Size (accumulate, if there are several files)
                            obj_pd_size.loc[obj_name, path_type] += obj.file_parameters[
                                Path(path).name
                            ]["SIZE"]
                        except KeyError:
                            pass

                        # Compare all parameters from last run to now
                        result_dict = compare_filep(obj, path, verbose=False)
                        # Store parameter-conflicts for later retrieval
                        self.param_results[obj_name][path_type] = result_dict

                        # Change status of path_type
                        # from object if there are conflicts
                        for parameter in result_dict:
                            if isinstance(result_dict[parameter], tuple):
                                if result_dict[parameter][2]:
                                    obj_pd.loc[
                                        obj_name, path_type
                                    ] = "critical_conflict"
                                else:
                                    obj_pd.loc[
                                        obj_name, path_type
                                    ] = "possible_conflict"

    def open_prog_dlg(self):
        # Create Progress-Dialog
        self.prog_bar = QProgressBar()
        self.prog_bar.setMinimum(0)
        self.prog_bar.setMaximum(3)

        self.prog_dlg = SimpleDialog(self.prog_bar, self, title="Loading Files...")

    def thread_finished(self, _):
        self.load_prog += 1
        self.prog_bar.setValue(self.load_prog)
        if self.load_prog == 3:
            self.prog_dlg.close()
            self.meeg_table.content_changed()
            self.fsmri_table.content_changed()
            self.group_table.content_changed()

    def thread_error(self, err):
        self.thread_finished(None)
        ErrorDialog(err, self)

    def start_load_threads(self):
        self.open_prog_dlg()

        meeg_worker = Worker(function=self.get_file_tables, kind="MEEG")
        meeg_worker.signals.error.connect(self.thread_error)
        meeg_worker.signals.finished.connect(self.thread_finished)
        meeg_worker.start()

        fsmri_worker = Worker(function=self.get_file_tables, kind="FSMRI")
        fsmri_worker.signals.error.connect(self.thread_error)
        fsmri_worker.signals.finished.connect(self.thread_finished)
        fsmri_worker.start()

        group_worker = Worker(function=self.get_file_tables, kind="Group")
        group_worker.signals.error.connect(self.thread_error)
        group_worker.signals.finished.connect(self.thread_finished)
        group_worker.start()

    def init_ui(self):
        layout = QVBoxLayout()

        mode_cmbx = QComboBox()
        mode_cmbx.addItems(["Existence", "Time", "Size"])
        mode_cmbx.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        mode_cmbx.currentTextChanged.connect(self.mode_changed)
        layout.addWidget(mode_cmbx, alignment=Qt.AlignLeft)

        tab_widget = QTabWidget()

        # MEEG
        meeg_widget = QWidget()
        meeg_layout = QVBoxLayout()

        self.meeg_table = FilePandasTable(self.pd_meeg)
        meeg_layout.addWidget(self.meeg_table)

        meeg_bt_layout = QHBoxLayout()

        meeg_showp_bt = QPushButton("Show Parameters")
        meeg_showp_bt.clicked.connect(partial(self.show_parameters, "MEEG"))
        meeg_bt_layout.addWidget(meeg_showp_bt)

        meeg_remove_bt = QPushButton("Remove File")
        meeg_remove_bt.clicked.connect(partial(self.remove_file, "MEEG"))
        meeg_bt_layout.addWidget(meeg_remove_bt)

        meeg_layout.addLayout(meeg_bt_layout)
        meeg_widget.setLayout(meeg_layout)

        tab_widget.addTab(meeg_widget, "MEEG")

        # FSMRI
        fsmri_widget = QWidget()
        fsmri_layout = QVBoxLayout()

        self.fsmri_table = FilePandasTable(self.pd_fsmri)
        fsmri_layout.addWidget(self.fsmri_table)

        fsmri_bt_layout = QHBoxLayout()

        fsmri_showp_bt = QPushButton("Show Parameters")
        fsmri_showp_bt.clicked.connect(partial(self.show_parameters, "FSMRI"))
        fsmri_bt_layout.addWidget(fsmri_showp_bt)

        fsmri_remove_bt = QPushButton("Remove File")
        fsmri_remove_bt.clicked.connect(partial(self.remove_file, "FSMRI"))
        fsmri_bt_layout.addWidget(fsmri_remove_bt)

        fsmri_layout.addLayout(fsmri_bt_layout)
        fsmri_widget.setLayout(fsmri_layout)

        tab_widget.addTab(fsmri_widget, "FSMRI")

        # Group
        group_widget = QWidget()
        group_layout = QVBoxLayout()

        self.group_table = FilePandasTable(self.pd_group)
        group_layout.addWidget(self.group_table)

        group_bt_layout = QHBoxLayout()

        group_showp_bt = QPushButton("Show Parameters")
        group_showp_bt.clicked.connect(partial(self.show_parameters, "Group"))
        group_bt_layout.addWidget(group_showp_bt)

        group_remove_bt = QPushButton("Remove File")
        group_remove_bt.clicked.connect(partial(self.remove_file, "Group"))
        group_bt_layout.addWidget(group_remove_bt)

        group_layout.addLayout(group_bt_layout)
        group_widget.setLayout(group_layout)

        tab_widget.addTab(group_widget, "Group")

        layout.addWidget(tab_widget)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def mode_changed(self, mode):
        if mode == "Existence":
            self.meeg_table.replace_data(self.pd_meeg)
            self.fsmri_table.replace_data(self.pd_fsmri)
            self.group_table.replace_data(self.pd_group)
        elif mode == "Time":
            self.meeg_table.replace_data(self.pd_meeg_time)
            self.fsmri_table.replace_data(self.pd_fsmri_time)
            self.group_table.replace_data(self.pd_group_time)
        elif mode == "Size":
            self.meeg_table.replace_data(self.pd_meeg_size)
            self.fsmri_table.replace_data(self.pd_fsmri_size)
            self.group_table.replace_data(self.pd_group_size)

    def _get_current(self, kind):
        if kind == "MEEG":
            current_list = self.meeg_table.get_current()
        elif kind == "FSMRI":
            current_list = self.fsmri_table.get_current()
        else:
            current_list = self.group_table.get_current()

        if len(current_list) > 0:
            obj_name = current_list[0][1]
            path_type = current_list[0][2]
        else:
            obj_name = None
            path_type = None

        return obj_name, path_type

    def show_parameters(self, kind):
        """Show the parameters, which are different for the selected cell

        Parameters
        ----------
        kind : str
            If it is MEEG, FSMRI or Group
        """

        # Pandas DataFrame to store parameters to be compared
        compare_pd = pd.DataFrame(columns=["Previous", "Current", "Critical?"])

        obj_name, path_type = self._get_current(kind)

        if (
            obj_name
            and path_type
            and obj_name in self.param_results
            and path_type in self.param_results[obj_name]
        ):
            result_dict = self.param_results[obj_name][path_type]

            for param in result_dict:
                if isinstance(result_dict[param], tuple):
                    compare_pd.loc[param] = result_dict[param]

            if len(compare_pd.index) > 0:
                # Show changed parameters
                SimpleDialog(
                    widget=SimplePandasTable(
                        compare_pd,
                        title="Changed Parameters",
                        resize_rows=True,
                        resize_columns=True,
                    ),
                    parent=self,
                    scroll=False,
                )

            else:
                QMessageBox.information(
                    self,
                    "All parameters equal!",
                    "For the selected file all parameters are equal!",
                )

    def _file_remover(self, selected_files, kind, worker_signals):
        worker_signals.pgbar_max.emit(len(selected_files))
        for idx, (_, obj_name, path_type) in enumerate(selected_files):
            if worker_signals.was_canceled:
                worker_signals.pgbar_text.emit("Removing canceled")
                break
            if kind == "MEEG":
                obj = MEEG(obj_name, self.ct)
                obj_pd = self.pd_meeg
                obj_pd_time = self.pd_meeg_time
                obj_pd_size = self.pd_meeg_size
            elif kind == "FSMRI":
                obj = FSMRI(obj_name, self.ct)
                obj_pd = self.pd_fsmri
                obj_pd_time = self.pd_fsmri_time
                obj_pd_size = self.pd_fsmri_size
            else:
                obj = Group(obj_name, self.ct)
                obj_pd = self.pd_group
                obj_pd_time = self.pd_group_time
                obj_pd_size = self.pd_group_size

            obj_pd.loc[obj_name, path_type] = None
            obj_pd_time.loc[obj_name, path_type] = None
            obj_pd_size.loc[obj_name, path_type] = None

            # Remove File
            worker_signals.pgbar_text.emit(f"Removing: {path_type}")
            obj.remove_path(path_type)
            worker_signals.pgbar_n.emit(idx + 1)

    def _remove_finished(self, kind):
        # Update Table-Widget
        if kind == "MEEG":
            obj_table = self.meeg_table
        elif kind == "FSMRI":
            obj_table = self.fsmri_table
        else:
            obj_table = self.group_table
        obj_table.content_changed()

    def remove_file(self, kind):
        """Remove the file at the path of the current cell

        Parameters
        ----------
        kind : str
            If it is MEEG, FSMRI or Group

        """

        msgbx = QMessageBox.question(
            self, "Remove files?", "Do you really want to remove the selected Files?"
        )

        if msgbx == QMessageBox.Yes:
            if kind == "MEEG":
                selected_files = self.meeg_table.get_selected()
            elif kind == "FSMRI":
                selected_files = self.fsmri_table.get_selected()
            else:
                selected_files = self.group_table.get_selected()
            wd = WorkerDialog(
                self,
                self._file_remover,
                selected_files=selected_files,
                kind=kind,
                show_buttons=True,
                show_console=True,
                title="Removing Files",
            )
            wd.thread_finished.connect(partial(self._remove_finished, kind))


class ICASelect(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr
        self.current_obj = None
        self.parameters = dict()
        self.chkbxs = dict()

        self.max_width, self.max_height = set_ratio_geometry(0.8)
        self.setMaximumSize(self.max_width, self.max_height)

        self.init_ui()
        self.show()

    def init_ui(self):
        self.main_layout = QVBoxLayout()
        list_layout = QHBoxLayout()

        self.file_list = CheckDictList(self.pr.all_meeg, self.pr.ica_exclude)
        self.file_list.currentChanged.connect(self.obj_selected)
        list_layout.addWidget(self.file_list)

        # Add Checkboxes for Components
        comp_scroll = QScrollArea()
        comp_widget = QWidget()
        self.comp_chkbx_layout = QGridLayout()

        n_components = self.pr.parameters[self.pr.p_preset]["n_components"]
        for idx in range(n_components):
            chkbx = QCheckBox(str(idx))
            chkbx.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            chkbx.clicked.connect(self.component_selected)
            self.chkbxs[idx] = chkbx
            self.comp_chkbx_layout.addWidget(chkbx, idx // 5, idx % 5)

        comp_widget.setLayout(self.comp_chkbx_layout)
        comp_scroll.setWidget(comp_widget)
        list_layout.addWidget(comp_scroll)

        bt_layout = QVBoxLayout()

        plot_comp_bt = QPushButton("Plot Components")
        plot_comp_bt.clicked.connect(self.plot_components)
        bt_layout.addWidget(plot_comp_bt)

        # Create Parameter-GUI which stores parameter in dictionary
        # (not the same as project.parameters)
        ica_source_data_param = ComboGui(
            data=self.parameters,
            name="ica_source_data",
            options=[
                "raw",
                "raw_filtered",
                "epochs",
                "epochs_eog",
                "epochs (ECG)",
                "Evokeds",
                "Evokeds (EOG)",
                "Evokeds (ECG)",
            ],
            default="raw_filtered",
        )
        bt_layout.addWidget(ica_source_data_param)

        plot_source_bt = QPushButton("Plot Source")
        plot_source_bt.clicked.connect(self.plot_sources)
        bt_layout.addWidget(plot_source_bt)

        ica_overlay_data_param = ComboGui(
            data=self.parameters,
            name="ica_overlay_data",
            options=[
                "raw",
                "raw_filtered",
                "Evokeds",
                "Evokeds (EOG)",
                "Evokeds (ECG)",
            ],
            default="raw_filtered",
        )
        bt_layout.addWidget(ica_overlay_data_param)

        plot_overlay_bt = QPushButton("Plot Overlay")
        plot_overlay_bt.clicked.connect(self.plot_overlay)
        bt_layout.addWidget(plot_overlay_bt)

        plot_overlay_bt = QPushButton("Plot Properties")
        plot_overlay_bt.clicked.connect(self.plot_properties)
        bt_layout.addWidget(plot_overlay_bt)

        close_plots_bt = QPushButton("Close Plots")
        close_plots_bt.clicked.connect(partial(plt.close, "all"))
        bt_layout.addWidget(close_plots_bt)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        list_layout.addLayout(bt_layout)
        self.main_layout.addLayout(list_layout)

        self.setLayout(self.main_layout)

    def update_chkbxs(self):
        # Check, if object is already in ica_exclude
        if self.current_obj.name in self.pr.ica_exclude:
            selected_components = self.pr.ica_exclude[self.current_obj.name]
        else:
            selected_components = list()

        # Clear all checkboxes
        for idx in self.chkbxs:
            self.chkbxs[idx].setChecked(False)

        # Select components
        for idx in selected_components:
            if idx in self.chkbxs:
                self.chkbxs[idx].setChecked(True)
            else:
                # Remove idx if not in range(n_components)
                self.pr.ica_exclude[self.current_obj.name].remove(idx)

    def update_plots(self):
        # Remove old layout with plots
        if self.main_layout.count() > 1:
            old_layout = self.main_layout.itemAt(self.main_layout.count() - 1)
            self.main_layout.removeItem(old_layout)
            for sub_layout in [
                old_layout.itemAt(idx).layout() for idx in range(old_layout.count())
            ]:
                for widget in [
                    sub_layout.itemAt(idx).widget() for idx in range(sub_layout.count())
                ]:
                    widget.deleteLater()
            del old_layout

        plot_layout = QHBoxLayout()

        for plot_func in self.selected_offline_plots:
            sub_plot_layout = QVBoxLayout()
            try:
                plot_paths = self.current_obj.plot_files[plot_func]
            except KeyError:
                continue
            else:
                for plot_path in plot_paths:
                    plot_path = join(self.pr.figures_path, plot_path)
                    pixmap = QPixmap(plot_path)
                    label = QLabel()
                    label.setScaledContents(True)
                    label.setPixmap(pixmap)
                    sub_plot_layout.addWidget(label)
            plot_layout.addLayout(sub_plot_layout)

        self.main_layout.addLayout(plot_layout)

    def obj_selected(self, current_name):
        self.current_obj = MEEG(current_name, self.ct)
        self.update_chkbxs()
        self.update_plots()

    def component_selected(self):
        if self.current_obj:
            self.pr.ica_exclude[self.current_obj.name] = [
                idx for idx in self.chkbxs if self.chkbxs[idx].isChecked()
            ]
        self.file_list.content_changed()

    def set_chkbx_enable(self, enable):
        for chkbx in self.chkbxs:
            self.chkbxs[chkbx].setEnabled(enable)

    def get_selected_components(self, ica, _):
        self.set_chkbx_enable(True)
        self.pr.ica_exclude[self.current_obj.name] = ica.exclude
        self.update_chkbxs()
        self.file_list.content_changed()

    def plot_components(self):
        if self.current_obj:
            # Disable CheckBoxes to avoid confusion
            # (Bad-Selection only goes unidirectional from Plot>GUI)
            self.set_chkbx_enable(False)
            dialog = QDialog(self)
            dialog.setWindowTitle("Opening...")
            dialog.open()
            try:
                figs, ica = plot_ica_components(meeg=self.current_obj, show_plots=True)
                if not isinstance(figs, list):
                    figs = [figs]
                for fig in figs:
                    fig.canvas.mpl_connect(
                        "close_event", partial(self.get_selected_components, ica)
                    )
            except Exception:
                err_tuple = get_exception_tuple()
                QMessageBox.critical(
                    self,
                    "An Error ocurred!",
                    f"{err_tuple[0]}: {err_tuple[1]}\n" f"{err_tuple[2]}",
                )
                self.set_chkbx_enable(True)
            finally:
                dialog.close()

    def plot_sources(self):
        if self.current_obj:
            # Disable CheckBoxes to avoid confusion
            # (Bad-Selection only goes unidirectional from Plot>GUI)
            self.set_chkbx_enable(False)
            dialog = QDialog(self)
            dialog.setWindowTitle("Opening...")
            dialog.open()
            try:
                figs, ica = plot_ica_sources(
                    meeg=self.current_obj,
                    ica_source_data=self.parameters["ica_source_data"],
                    show_plots=True,
                )
                if not isinstance(figs, list):
                    figs = [figs]
                for fig in figs:
                    fig.canvas.mpl_connect(
                        "close_event", partial(self.get_selected_components, ica)
                    )
            except Exception:
                err_tuple = get_exception_tuple()
                QMessageBox.critical(
                    self,
                    "An Error ocurred!",
                    f"{err_tuple[0]}: {err_tuple[1]}\n" f"{err_tuple[2]}",
                )
                self.set_chkbx_enable(False)
            finally:
                dialog.close()

    def plot_overlay(self):
        if self.current_obj:
            # Disable CheckBoxes to avoid confusion
            # (Bad-Selection only goes unidirectional from Plot>GUI)
            self.set_chkbx_enable(False)
            dialog = QDialog(self)
            dialog.setWindowTitle("Opening...")
            dialog.open()
            try:
                plot_ica_overlay(
                    meeg=self.current_obj,
                    ica_overlay_data=self.parameters["ica_overlay_data"],
                    show_plots=True,
                )
            except Exception:
                err_tuple = get_exception_tuple()
                QMessageBox.critical(
                    self,
                    "An Error ocurred!",
                    f"{err_tuple[0]}: {err_tuple[1]}\n" f"{err_tuple[2]}",
                )
                self.set_chkbx_enable(False)
            finally:
                dialog.close()

    def plot_properties(self):
        if self.current_obj:
            # Disable CheckBoxes to avoid confusion
            # (Bad-Selection only goes unidirectional from Plot>GUI)
            self.set_chkbx_enable(False)
            dialog = QDialog(self)
            dialog.setWindowTitle("Opening...")
            dialog.open()
            try:
                plot_ica_properties(meeg=self.current_obj, show_plots=True)
            except Exception:
                err_tuple = get_exception_tuple()
                QMessageBox.critical(
                    self,
                    "An Error ocurred!",
                    f"{err_tuple[0]}: {err_tuple[1]}\n" f"{err_tuple[2]}",
                )
                self.set_chkbx_enable(False)
            finally:
                dialog.close()


class ReloadRaw(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.pr = main_win.ct.pr

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        self.raw_list = SimpleList(self.pr.all_meeg, title="Select raw to reload")
        layout.addWidget(self.raw_list)

        reload_bt = QPushButton("Reload")
        reload_bt.clicked.connect(self.start_reload)
        layout.addWidget(reload_bt)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def reload_raw(self, selected_raw, raw_path):
        meeg = MEEG(selected_raw, self.ct)
        raw = mne.io.read_raw(raw_path, preload=True)
        meeg.save_raw(raw)
        print(f"Reloaded raw for {selected_raw}")

    def start_reload(self):
        # Not with partial because otherwise the clicked-arg
        # from clicked goes into *args
        selected_raw = self.raw_list.get_current()
        raw_path = QFileDialog.getOpenFileName(self, "Select raw for Reload")[0]
        if raw_path:
            WorkerDialog(
                self,
                self.reload_raw,
                selected_raw=selected_raw,
                raw_path=raw_path,
                show_console=True,
                title=f"Reloading raw for {selected_raw}",
            )


class ExportDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct

        self.common_types = list()
        self.selected_types = list()
        self.dest_path = None
        self.export_paths = dict()

        self._get_common_types()
        self._init_ui()

    def _get_common_types(self):
        for meeg_name in self.ct.pr.sel_meeg:
            meeg = MEEG(meeg_name, self.ct)
            meeg.get_existing_paths()
            type_set = set(meeg.existing_paths.keys())
            if isinstance(self.common_types, list):
                self.common_types = type_set
            else:
                self.common_types = self.common_types & type_set
            self.export_paths[meeg_name] = meeg.existing_paths

    def _get_destination(self):
        dest = QFileDialog.getExistingDirectory(self, "Select Destination-Folder")[0]
        if dest:
            self.dest_path = dest

    def _init_ui(self):
        layout = QVBoxLayout()
        self.dest_label = QLabel("<No Destination-Folder set>")
        layout.addWidget(self.dest_label)
        dest_bt = QPushButton("Set Destination-Folder")
        dest_bt.clicked.connect(self._get_destination)
        layout.addWidget(dest_bt)
        layout.addWidget(QLabel())
        layout.addWidget(
            SimpleList(
                self.ct.pr.sel_meeg,
                title="Export selected data for the " "following MEEG-Files:",
            )
        )
        layout.addWidget(
            CheckList(
                list(self.common_types),
                self.selected_types,
                title="Selected Data-Types",
            )
        )
        export_bt = QPushButton("Export")
        export_bt.clicked.connect(self.export_data)
        layout.addWidget(export_bt)
        self.setLayout(layout)

    def export_data(self):
        if self.dest_path:
            print("Starting Export\n")
            for meeg_name, path_types in self.export_paths.items():
                os.mkdir(join(self.dest_path, meeg_name))
                for path_type in [pt for pt in path_types if pt in self.selected_types]:
                    paths = path_types[path_type]
                    for src_path in paths:
                        dest_name = Path(src_path).name
                        shutil.copy2(
                            src_path, join(self.dest_path, meeg_name, dest_name)
                        )
                    print(f"\r{meeg_name}: Copying {path_type}...")
        else:
            QMessageBox.warning(self, "Ups!", "Destination-Path not set!")
