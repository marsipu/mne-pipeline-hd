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
import os
import shutil
from ast import literal_eval
from functools import partial
from importlib import util
from os import mkdir
from os.path import isdir, isfile, join
from pathlib import Path

import pandas as pd
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QButtonGroup, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                             QSizePolicy, QStyle,
                             QTextEdit, QVBoxLayout)

from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.base_widgets import BaseList, EditDict, EditList
from mne_pipeline_hd.gui.dialogs import ErrorDialog
from mne_pipeline_hd.gui.gui_utils import get_exception_tuple, get_ratio_geometry
from mne_pipeline_hd.gui.models import CheckListModel, CustomFunctionModel


class EditGuiArgsDlg(QDialog):
    def __init__(self, cf_dialog):
        super().__init__(cf_dialog)
        self.cf = cf_dialog
        self.gui_args = dict()
        self.default_gui_args = dict()

        if self.cf.current_parameter:
            covered_params = ['data', 'param_name', 'param_alias', 'default', 'param_unit', 'hint']
            # Get possible default GUI-Args additional to those covered by the Main-GUI
            gui_type = self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type']
            if pd.notna(gui_type):
                gui_handle = getattr(parameter_widgets, gui_type)
                psig = inspect.signature(gui_handle).parameters
                self.default_gui_args = {p: psig[p].default for p in psig if p not in covered_params}

            # Get current GUI-Args
            loaded_gui_args = self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_args']
            if pd.notna(loaded_gui_args):
                self.gui_args = literal_eval(loaded_gui_args)
            else:
                self.gui_args = dict()

            # Fill in all possible Options, which are not already changed
            for arg_key in [ak for ak in self.default_gui_args if ak not in self.gui_args]:
                self.gui_args[arg_key] = self.default_gui_args[arg_key]

            if len(self.gui_args) > 0:
                self.init_ui()
                self.open()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(EditDict(data=self.gui_args, ui_buttons=False))

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def closeEvent(self, event):
        # Remove all options which don't differ from the default
        for arg_key in [ak for ak in self.gui_args if self.gui_args[ak] == self.default_gui_args[ak]]:
            self.gui_args.pop(arg_key)

        if len(self.gui_args) > 0:
            self.cf.pguiargs_changed(self.gui_args)

        event.accept()


class ChooseOptions(QDialog):
    def __init__(self, cf_dialog, gui_type, options):
        super().__init__(cf_dialog)
        self.cf = cf_dialog
        self.gui_type = gui_type
        self.options = options

        self.init_ui()
        # If open(), execution doesn't stop after the dialog
        self.exec()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f'For {self.gui_type}, you need to specify the options to choose from'))
        layout.addWidget(EditList(data=self.options))
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)


class CustomFunctionImport(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.file_path = None
        self.pkg_name = None
        self.current_function = None
        self.current_parameter = None
        self.oblig_func = ['tab', 'group', 'subject_loop', 'matplotlib', 'mayavi']
        self.oblig_params = ['default', 'gui_type']

        self.exst_functions = list(self.mw.pd_funcs.index)
        self.exst_parameters = ['mw', 'pr', 'sub', 'mri_sub', 'ga_group', 'name', 'save_dir', 'ermsub', 'bad_channels']
        self.exst_parameters.append(vars(self.mw.pr))
        self.exst_parameters.append(list(self.mw.pr.parameters[self.mw.pr.p_preset].keys()))
        self.param_exst_dict = dict()

        self.code_dict = dict()

        # Get available parameter-guis
        self.available_param_guis = [pg for pg in dir(parameter_widgets) if 'Gui' in pg and pg != 'QtGui']

        self.add_pd_funcs = pd.DataFrame(columns=['alias', 'tab', 'group', 'subject_loop', 'matplotlib', 'mayavi',
                                                  'dependencies', 'module', 'func_args', 'ready'])
        self.add_pd_params = pd.DataFrame(columns=['alias', 'default', 'unit', 'description', 'gui_type',
                                                   'gui_args', 'function', 'ready'])

        self.yes_icon = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        self.no_icon = self.style().standardIcon(QStyle.SP_DialogCancelButton)

        self.setWindowTitle('Custom-Functions-Setup')

        width, height = get_ratio_geometry(0.7)
        self.resize(int(width), int(height))

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()
        sub_layout = QHBoxLayout()

        # Import Button and Combobox
        editor_layout = QVBoxLayout()

        func_cmbx_layout = QHBoxLayout()
        self.func_cmbx = QComboBox()
        self.func_cmbx.currentTextChanged.connect(self.func_item_selected)
        func_cmbx_layout.addWidget(self.func_cmbx)

        self.func_chkl = QLabel()
        self.func_chkl.setPixmap(self.no_icon.pixmap(16, 16))
        self.func_chkl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        func_cmbx_layout.addWidget(self.func_chkl)

        add_bt_layout = QHBoxLayout()
        addfn_bt = QPushButton('Load Function/s')
        addfn_bt.setFont(QFont('AnyStyle', 12))
        addfn_bt.clicked.connect(self.get_functions)
        add_bt_layout.addWidget(addfn_bt)
        editfn_bt = QPushButton('Edit Function/s')
        editfn_bt.setFont(QFont('AnyStyle', 12))
        editfn_bt.clicked.connect(self.edit_functions)
        add_bt_layout.addWidget(editfn_bt)

        editor_layout.addLayout(add_bt_layout)
        editor_layout.addLayout(func_cmbx_layout)

        # Todo: Make it a real editor (maybe even with syntax-highlighting?)
        # Editor-Widget
        self.code_editor = QTextEdit()
        self.code_editor.setReadOnly(True)
        editor_layout.addWidget(self.code_editor)
        sub_layout.addLayout(editor_layout)

        setup_layout = QVBoxLayout()
        # The Function-Setup-Groupbox
        func_setup_gbox = QGroupBox('Function-Setup')
        func_setup_gbox.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        func_setup_layout = QVBoxLayout()

        # Hint for obligatory items
        obl_hint_layout = QHBoxLayout()
        obl_hint_label1 = QLabel()
        obl_hint_label1.setPixmap(self.no_icon.pixmap(16, 16))
        obl_hint_label1.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        obl_hint_layout.addWidget(obl_hint_label1)
        obl_hint_label2 = QLabel()
        obl_hint_label2.setPixmap(self.style().standardIcon(QStyle.SP_ArrowForward).pixmap(16, 16))
        obl_hint_label2.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        obl_hint_layout.addWidget(obl_hint_label2)
        obl_hint_label3 = QLabel()
        obl_hint_label3.setPixmap(self.yes_icon.pixmap(16, 16))
        obl_hint_label3.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        obl_hint_layout.addWidget(obl_hint_label3)
        obl_hint_layout.addWidget(QLabel('(These items are obligatory)'))
        func_setup_layout.addLayout(obl_hint_layout)

        func_setup_formlayout = QFormLayout()

        self.falias_le = QLineEdit()
        self.falias_le.setToolTip('Set a name if you want something other than the functions-name')
        self.falias_le.textEdited.connect(self.falias_changed)
        func_setup_formlayout.addRow('Alias', self.falias_le)

        tab_layout = QHBoxLayout()
        self.tab_cmbx = QComboBox()
        self.tab_cmbx.setToolTip('Choose the Tab for the function (Compute/Plot/...)')
        self.tab_cmbx.setEditable(True)
        self.tab_cmbx.activated.connect(self.tab_cmbx_changed)
        self.tab_cmbx.editTextChanged.connect(self.tab_cmbx_edited)
        tab_layout.addWidget(self.tab_cmbx)
        self.tab_chkl = QLabel()
        tab_layout.addWidget(self.tab_chkl)
        func_setup_formlayout.addRow('Tab', tab_layout)

        group_layout = QHBoxLayout()
        self.group_cmbx = QComboBox()
        self.group_cmbx.setToolTip('Choose the function-group for the function or create a new one')
        self.group_cmbx.setEditable(True)
        self.group_cmbx.activated.connect(self.group_cmbx_changed)
        self.group_cmbx.editTextChanged.connect(self.group_cmbx_edited)
        group_layout.addWidget(self.group_cmbx)
        self.group_chkl = QLabel()
        group_layout.addWidget(self.group_chkl)
        func_setup_formlayout.addRow('Group', group_layout)

        subloop_layout = QHBoxLayout()
        self.subloop_bts = QButtonGroup(self)
        self.subloop_yesbt = QPushButton('Yes')
        self.subloop_yesbt.setCheckable(True)
        self.subloop_nobt = QPushButton('No')
        self.subloop_nobt.setCheckable(True)
        self.subloop_bts.addButton(self.subloop_yesbt)
        self.subloop_bts.addButton(self.subloop_nobt)
        subloop_layout.addWidget(self.subloop_yesbt)
        subloop_layout.addWidget(self.subloop_nobt)
        self.subloop_yesbt.setToolTip('Choose if function is applied to each file')
        self.subloop_nobt.setToolTip('Choose if function is applied to a group or does something else')
        self.subloop_bts.buttonToggled.connect(self.subloop_changed)
        self.subloop_chkl = QLabel()
        subloop_layout.addWidget(self.subloop_chkl)
        func_setup_formlayout.addRow('Subject-Loop?', subloop_layout)

        mtpl_layout = QHBoxLayout()
        self.mtpl_bts = QButtonGroup(self)
        self.mtpl_yesbt = QPushButton('Yes')
        self.mtpl_yesbt.setCheckable(True)
        self.mtpl_nobt = QPushButton('No')
        self.mtpl_nobt.setCheckable(True)
        self.mtpl_bts.addButton(self.mtpl_yesbt)
        self.mtpl_bts.addButton(self.mtpl_nobt)
        mtpl_layout.addWidget(self.mtpl_yesbt)
        mtpl_layout.addWidget(self.mtpl_nobt)
        self.mtpl_yesbt.setToolTip('Choose, if the function contains an interactive Matplotlib-Plot')
        self.mtpl_nobt.setToolTip('Choose, if the function contains no interactive Matplotlib-Plot')
        self.mtpl_bts.buttonToggled.connect(self.mtpl_changed)
        self.mtpl_chkl = QLabel()
        mtpl_layout.addWidget(self.mtpl_chkl)
        func_setup_formlayout.addRow('Matplotlib?', mtpl_layout)

        myv_layout = QHBoxLayout()
        self.myv_bts = QButtonGroup(self)
        self.myv_yesbt = QPushButton('Yes')
        self.myv_yesbt.setCheckable(True)
        self.myv_nobt = QPushButton('No')
        self.myv_nobt.setCheckable(True)
        self.myv_bts.addButton(self.myv_yesbt)
        self.myv_bts.addButton(self.myv_nobt)
        myv_layout.addWidget(self.myv_yesbt)
        myv_layout.addWidget(self.myv_nobt)
        self.myv_yesbt.setToolTip('Choose, if the function contains a Pyvista/Mayavi-Plot')
        self.myv_nobt.setToolTip('Choose, if the function contains a Pyvista/Mayavi-Plot')
        self.myv_bts.buttonToggled.connect(self.myv_changed)
        self.myv_chkl = QLabel()
        myv_layout.addWidget(self.myv_chkl)
        func_setup_formlayout.addRow('Pyvista/Mayavi?', myv_layout)

        self.dpd_bt = QPushButton('Set Dependencies')
        self.dpd_bt.setToolTip('Set the functions that must be activated before or the files that must be present '
                               'for this function to work')
        self.dpd_bt.clicked.connect(partial(SelectDependencies, self))
        func_setup_formlayout.addRow('Dependencies', self.dpd_bt)

        func_setup_layout.addLayout(func_setup_formlayout)

        func_setup_gbox.setLayout(func_setup_layout)
        setup_layout.addWidget(func_setup_gbox)

        # The Parameter-Setup-Group-Box
        self.param_setup_gbox = QGroupBox('Parameter-Setup')
        self.param_setup_gbox.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        param_setup_layout = QVBoxLayout()
        self.exstparam_l = QLabel()
        self.exstparam_l.setWordWrap(True)
        self.exstparam_l.hide()
        param_setup_layout.addWidget(self.exstparam_l)

        self.param_view = QListView()
        self.param_model = CustomFunctionModel(self.add_pd_params)
        self.param_view.setModel(self.param_model)
        self.param_view.selectionModel().currentChanged.connect(self.param_item_selected)
        param_setup_layout.addWidget(self.param_view)

        param_setup_formlayout = QFormLayout()
        self.palias_le = QLineEdit()
        self.palias_le.setToolTip('Set a name if you want something other than the parameters-name')
        self.palias_le.textEdited.connect(self.palias_changed)
        param_setup_formlayout.addRow('Alias', self.palias_le)

        default_layout = QHBoxLayout()
        self.default_le = QLineEdit()
        self.default_le.setToolTip('Set the default for the parameter (it has to fit the gui-type!)')
        self.default_le.textEdited.connect(self.pdefault_changed)
        default_layout.addWidget(self.default_le)
        self.default_chkl = QLabel()
        default_layout.addWidget(self.default_chkl)
        param_setup_formlayout.addRow('Default', default_layout)

        self.unit_le = QLineEdit()
        self.unit_le.setToolTip('Set the unit for the parameter (optional)')
        self.unit_le.textEdited.connect(self.punit_changed)
        param_setup_formlayout.addRow('Unit', self.unit_le)

        self.description_le = QLineEdit()
        self.description_le.setToolTip('Short description of the parameter (optional)')
        self.description_le.textEdited.connect(self.pdescription_changed)
        param_setup_formlayout.addRow('Description', self.description_le)

        guitype_layout = QHBoxLayout()
        self.guitype_cmbx = QComboBox()
        self.guitype_cmbx.setToolTip('Choose the GUI from the available GUIs')
        self.guitype_cmbx.activated.connect(self.guitype_cmbx_changed)
        guitype_layout.addWidget(self.guitype_cmbx)
        test_bt = QPushButton('Test')
        test_bt.clicked.connect(self.show_param_gui)
        guitype_layout.addWidget(test_bt)
        self.guitype_chkl = QLabel()
        guitype_layout.addWidget(self.guitype_chkl)
        param_setup_formlayout.addRow('GUI-Type', guitype_layout)

        self.guiargs_bt = QPushButton('Edit')
        self.guiargs_bt.clicked.connect(partial(EditGuiArgsDlg, self))
        self.guiargs_bt.setToolTip('Set Arguments for the GUI in a dict (optional)')
        param_setup_formlayout.addRow('Additional Options', self.guiargs_bt)

        param_setup_layout.addLayout(param_setup_formlayout)
        self.param_setup_gbox.setLayout(param_setup_layout)

        setup_layout.addWidget(self.param_setup_gbox)
        sub_layout.addLayout(setup_layout)

        layout.addLayout(sub_layout)

        bt_layout = QHBoxLayout()

        save_bt = QPushButton('Save')
        save_bt.setFont(QFont('AnyStyle', 16))
        save_bt.clicked.connect(self.save_pkg)
        bt_layout.addWidget(save_bt)

        close_bt = QPushButton('Quit')
        close_bt.setFont(QFont('AnyStyle', 16))
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        layout.addLayout(bt_layout)

        self.setLayout(layout)

        self.populate_tab_cmbx()
        self.populate_group_cmbx()
        self.populate_guitype_cmbx()

    def update_func_cmbx(self):
        self.func_cmbx.clear()
        self.func_cmbx.insertItems(0, self.add_pd_funcs.index)
        try:
            current_index = list(self.add_pd_funcs.index).index(self.current_function)
        except ValueError:
            current_index = 0
        self.func_cmbx.setCurrentIndex(current_index)

    def clear_func_items(self):
        self.falias_le.clear()
        self.tab_cmbx.setCurrentIndex(-1)
        self.tab_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        self.group_cmbx.setCurrentIndex(-1)
        self.group_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        self.subloop_yesbt.setChecked(False)
        self.subloop_nobt.setChecked(False)
        self.subloop_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        self.mtpl_yesbt.setChecked(False)
        self.mtpl_nobt.setChecked(False)
        self.mtpl_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        self.myv_nobt.setChecked(False)
        self.myv_nobt.setChecked(False)
        self.myv_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))

    def clear_param_items(self):
        self.update_param_view()
        self.palias_le.clear()
        self.default_le.clear()
        self.default_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        self.unit_le.clear()
        self.guitype_cmbx.setCurrentIndex(-1)
        self.guitype_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        self.param_setup_gbox.setEnabled(False)

    def func_item_selected(self, text):
        if text:
            self.current_function = text
            self.update_editor()
            self.update_func_setup()

            if self.current_function in list(self.add_pd_params['function']):
                self.param_setup_gbox.setEnabled(True)
                self.update_param_view()
                self.current_parameter = \
                    self.add_pd_params.loc[self.add_pd_params['function'] == self.current_function].index[0]
                self.update_exst_param_label()
                self.update_param_setup()
            else:
                self.update_exst_param_label()
                # Clear existing entries
                self.clear_param_items()

    def param_item_selected(self, current):
        self.current_parameter = self.param_model.getData(current)
        self.update_param_setup()

    def update_editor(self):
        self.code_editor.clear()
        self.code_editor.insertPlainText(self.code_dict[self.current_function])

    def update_func_setup(self):
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'alias']):
            self.falias_le.setText(self.add_pd_funcs.loc[self.current_function, 'alias'])
        else:
            self.falias_le.clear()
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'tab']):
            self.tab_cmbx.setCurrentText(self.add_pd_funcs.loc[self.current_function, 'tab'])
            self.tab_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.tab_cmbx.setCurrentIndex(-1)
            self.tab_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'group']):
            self.group_cmbx.setCurrentText(self.add_pd_funcs.loc[self.current_function, 'group'])
            self.group_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.group_cmbx.setCurrentIndex(-1)
            self.group_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'subject_loop']):
            if self.add_pd_funcs.loc[self.current_function, 'subject_loop']:
                self.subloop_yesbt.setChecked(True)
            else:
                self.subloop_nobt.setChecked(True)
            self.subloop_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.subloop_yesbt.setChecked(False)
            self.subloop_nobt.setChecked(False)
            self.subloop_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'matplotlib']):
            if self.add_pd_funcs.loc[self.current_function, 'matplotlib']:
                self.mtpl_yesbt.setChecked(True)
            else:
                self.mtpl_nobt.setChecked(True)
            self.mtpl_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.mtpl_yesbt.setChecked(False)
            self.mtpl_nobt.setChecked(False)
            self.mtpl_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'mayavi']):
            if self.add_pd_funcs.loc[self.current_function, 'mayavi']:
                self.myv_yesbt.setChecked(True)
            else:
                self.myv_nobt.setChecked(True)
            self.myv_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.myv_nobt.setChecked(False)
            self.myv_nobt.setChecked(False)
            self.myv_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))

    def update_exst_param_label(self):
        if len(self.param_exst_dict[self.current_function]) > 0:
            self.exstparam_l.setText(f'Already existing Parameters: {self.param_exst_dict[self.current_function]}')
            self.exstparam_l.show()
        else:
            self.exstparam_l.hide()

    def update_param_setup(self):
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'alias']):
            self.palias_le.setText(self.add_pd_params.loc[self.current_parameter, 'alias'])
        else:
            self.palias_le.clear()
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'default']):
            self.default_le.setText(self.add_pd_params.loc[self.current_parameter, 'default'])
            self.default_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.default_le.clear()
            self.default_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'unit']):
            self.unit_le.setText(self.add_pd_params.loc[self.current_parameter, 'unit'])
        else:
            self.unit_le.clear()
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'description']):
            self.description_le.setText(self.add_pd_params.loc[self.current_parameter, 'description'])
        else:
            self.description_le.clear()
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_type']):
            self.guitype_cmbx.setCurrentText(self.add_pd_params.loc[self.current_parameter, 'gui_type'])
            self.guitype_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.guitype_cmbx.setCurrentIndex(-1)
            self.guitype_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))

    def check_func_setup(self):
        # Check, that all obligatory items of the Subject-Setup and the Parameter-Setup are set
        if (all([pd.notna(self.add_pd_funcs.loc[self.current_function, i]) for i in self.oblig_func])
                and [pd.notna(self.add_pd_params.loc[self.add_pd_params['function'] == self.current_function, i])
                     for i in self.oblig_params][0].all()):
            self.func_chkl.setPixmap(self.yes_icon.pixmap(16, 16))
            self.add_pd_funcs.loc[self.current_function, 'ready'] = 1
        else:
            self.func_chkl.setPixmap(self.no_icon.pixmap(16, 16))
            self.add_pd_funcs.loc[self.current_function, 'ready'] = 0

    def update_param_view(self):
        # Update Param-Model with new pd_params of current_function
        current_pd_params = self.add_pd_params.loc[self.add_pd_params['function'] == self.current_function]
        self.param_model.updateData(current_pd_params)

    def check_param_setup(self):
        # Check, that all obligatory items of the Parameter-Setup are set
        if all([pd.notna(self.add_pd_params.loc[self.current_parameter, i]) for i in self.oblig_params]):
            self.add_pd_params.loc[self.current_parameter, 'ready'] = 1
        else:
            self.add_pd_params.loc[self.current_parameter, 'ready'] = 0
        self.update_param_view()

    # Line-Edit Change-Signals
    def falias_changed(self, text):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'alias'] = text

    def subloop_changed(self, current_button, state):
        if self.current_function:
            if state and current_button == self.subloop_yesbt:
                self.add_pd_funcs.loc[self.current_function, 'subject_loop'] = True
            else:
                self.add_pd_funcs.loc[self.current_function, 'subject_loop'] = False
            self.subloop_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def mtpl_changed(self, current_button, state):
        if self.current_function:
            if state and current_button == self.mtpl_yesbt:
                self.add_pd_funcs.loc[self.current_function, 'matplotlib'] = True
            else:
                self.add_pd_funcs.loc[self.current_function, 'matplotlib'] = False
            self.mtpl_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def myv_changed(self, current_button, state):
        if self.current_function:
            if state and current_button == self.myv_yesbt:
                self.add_pd_funcs.loc[self.current_function, 'mayavi'] = True
            else:
                self.add_pd_funcs.loc[self.current_function, 'mayavi'] = False
            self.myv_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def palias_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'alias'] = text

    def pdefault_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'default'] = text
            self.default_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_param_setup()
            self.check_func_setup()

    def punit_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'unit'] = text

    def pdescription_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'description'] = text

    def populate_tab_cmbx(self):
        self.tab_cmbx.insertItems(0, set(self.mw.pd_funcs['tab']))
        self.tab_cmbx.setCurrentIndex(-1)

    def populate_group_cmbx(self):
        self.group_cmbx.insertItems(0, set(self.mw.pd_funcs['group']))
        self.group_cmbx.setCurrentIndex(-1)

    def populate_guitype_cmbx(self):
        self.guitype_cmbx.insertItems(0, self.available_param_guis)
        self.guitype_cmbx.setCurrentIndex(-1)

    def tab_cmbx_changed(self, idx):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'tab'] = self.tab_cmbx.itemText(idx)
            self.tab_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def tab_cmbx_edited(self, text):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'tab'] = text
            self.tab_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def group_cmbx_changed(self, idx):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'group'] = self.group_cmbx.itemText(idx)
            self.group_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def group_cmbx_edited(self, text):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'group'] = text
            self.group_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def guitype_cmbx_changed(self, idx):
        text = self.guitype_cmbx.itemText(idx)
        gui_args = dict()
        options = list()

        if self.current_parameter:
            # If ComboGui or CheckListGui, options have to be set:
            if text in ['ComboGui', 'CheckListGui']:
                # Check if options already in gui_args
                loaded_gui_args = self.add_pd_params.loc[self.current_parameter, 'gui_args']
                if pd.notna(loaded_gui_args):
                    gui_args = literal_eval(loaded_gui_args)
                    if 'options' in gui_args:
                        options = gui_args['options']

                ChooseOptions(self, text, options)

                # Save the gui_args in add_pd_params
                gui_args['options'] = options
                self.add_pd_params.loc[self.current_parameter, 'gui_args'] = str(gui_args)

            # Check, if default_value and gui_type match
            if pd.notna(self.add_pd_params.loc[self.current_parameter, 'default']):
                result, _ = self.test_param_gui(
                        default_string=self.add_pd_params.loc[self.current_parameter, 'default'],
                        gui_type=text, gui_args=gui_args)
            else:
                result = None

            if not result:
                self.add_pd_params.loc[self.current_parameter, 'gui_type'] = text
                self.guitype_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
                self.check_param_setup()
                self.check_func_setup()
            else:
                self.guitype_cmbx.setCurrentIndex(-1)
                self.add_pd_params.loc[self.current_parameter, 'gui_type'] = None
                self.check_param_setup()
                self.check_func_setup()

    def pguiargs_changed(self, gui_args):
        if self.current_parameter:
            # Check, if default_value and gui_type match
            if pd.notna(self.add_pd_params.loc[self.current_parameter, ['default', 'gui_type']]).all():
                result, _ = self.test_param_gui(
                        default_string=self.add_pd_params.loc[self.current_parameter, 'default'],
                        gui_type=self.add_pd_params.loc[self.current_parameter, 'gui_type'],
                        gui_args=gui_args)
            else:
                result = None

            if not result:
                self.add_pd_params.loc[self.current_parameter, 'gui_args'] = str(gui_args)
            else:
                self.add_pd_params.loc[self.current_parameter, 'gui_args'] = None

    def get_functions(self):
        # Clear Function- and Parameter-DataFrame
        self.add_pd_funcs.drop(index=self.add_pd_funcs.index, inplace=True)
        self.add_pd_params.drop(index=self.add_pd_funcs.index, inplace=True)
        self.clear_func_items()
        self.clear_param_items()

        # Returns tuple of files-list and file-type
        cf_path_string = QFileDialog.getOpenFileName(self,
                                                     'Choose the Python-File containing your function to import',
                                                     filter='Python-File (*.py)')[0]
        if cf_path_string:
            self.file_path = Path(cf_path_string)
            ImportFuncs(self)

    def edit_functions(self):
        # Clear Function- and Parameter-DataFrame
        self.add_pd_funcs.drop(index=self.add_pd_funcs.index, inplace=True)
        self.add_pd_params.drop(index=self.add_pd_funcs.index, inplace=True)
        self.clear_func_items()
        self.clear_param_items()

        # Returns tuple of files-list and file-type
        cf_path_string = QFileDialog.getOpenFileName(self,
                                                     'Choose the Python-File containing the functions to edit',
                                                     filter='Python-File (*.py)')[0]
        if cf_path_string:
            self.file_path = Path(cf_path_string)
            ImportFuncs(self, edit_existing=True)

    def test_param_gui(self, default_string, gui_type, gui_args=None):
        # Test ParamGui with Value
        test_parameters = dict()
        try:
            test_parameters[self.current_parameter] = literal_eval(default_string)
        except (ValueError, SyntaxError):
            # Allow parameters to be defined by functions by numpy, etc.
            if self.add_pd_params.loc[self.current_parameter, 'gui_type'] == 'FuncGui':
                test_parameters[self.current_parameter] = eval(default_string)
            else:
                test_parameters[self.current_parameter] = default_string
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'alias']):
            param_alias = self.add_pd_params.loc[self.current_parameter, 'alias']
        else:
            param_alias = self.current_parameter
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'description']):
            hint = self.cf.add_pd_params.loc[self.cf.current_parameter, 'description']
        else:
            hint = None
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'unit']):
            param_unit = self.add_pd_params.loc[self.current_parameter, 'unit']
        else:
            param_unit = None

        gui_handle = getattr(parameter_widgets, gui_type)
        try:
            if gui_args:
                gui = gui_handle(data=test_parameters, param_name=self.current_parameter,
                                 param_alias=param_alias, hint=hint, param_unit=param_unit, **gui_args)
            else:
                gui = gui_handle(data=test_parameters, param_name=self.current_parameter,
                                 param_alias=param_alias, hint=hint, param_unit=param_unit)
        except Exception as e:
            gui = None
            result = e
            QMessageBox.warning(self, 'Error in ParamGui',
                                f'The execution of {gui_type} with {default_string} as default '
                                f'and {gui_args} as additional parameters raises the following error:\n'
                                f'{result}')
        else:
            result = None

        return result, gui

    def show_param_gui(self):
        if self.current_parameter and pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_type']):
            TestParamGui(self)

    def save_pkg(self):
        if any(self.add_pd_funcs['ready'] == 1):
            SavePkgDialog(self)

    def closeEvent(self, event):
        drop_funcs = [f for f in self.add_pd_funcs.index if not self.add_pd_funcs.loc[f, 'ready']]

        if len(drop_funcs) > 0:
            answer = QMessageBox.question(self, 'Close Custom-Functions?', f'There are still unfinished functions:\n'
                                                                           f'{drop_funcs}\n'
                                                                           f'Do you still want to quit?')
        else:
            answer = None

        if answer == QMessageBox.Yes or answer is None:
            event.accept()
        else:
            event.ignore()


class ImportFuncs(QDialog):
    def __init__(self, cf_dialog, edit_existing=False):
        super().__init__(cf_dialog)
        self.cf = cf_dialog
        self.edit_existing = edit_existing

        self.module = None
        self.loaded_cfs = []
        self.selected_cfs = []
        self.already_existing_funcs = []

        self.load_function_list()
        self.init_ui()

        self.open()

    def load_function_list(self):
        spec = util.spec_from_file_location(self.cf.file_path.stem, self.cf.file_path)
        self.module = util.module_from_spec(spec)
        try:
            spec.loader.exec_module(self.module)
        except:
            err = get_exception_tuple()
            ErrorDialog(err, self)
        else:
            for func_key in self.module.__dict__:
                func = self.module.__dict__[func_key]
                # Only functions are allowed (Classes should be called from function)
                if callable(func) and func.__module__ == self.module.__name__:
                    # Check, if function is already existing
                    if func_key not in self.cf.exst_functions or self.edit_existing:
                        self.loaded_cfs.append(func_key)
                    else:
                        self.already_exst_funcs.append(func_key)

    def init_ui(self):
        layout = QVBoxLayout()

        if len(self.already_existing_funcs) > 0:
            exst_label = QLabel(f'These functions already exist: {self.already_existing_funcs}')
            exst_label.setWordWrap(True)
            layout.addWidget(exst_label)

        self.list_view = QListView()
        self.list_model = CheckListModel(self.loaded_cfs, self.selected_cfs)
        self.list_view.setModel(self.list_model)
        layout.addWidget(self.list_view)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def load_selected_functions(self):
        selected_funcs = [cf for cf in self.loaded_cfs if cf in self.selected_cfs]
        if self.edit_existing:
            self.cf.pkg_name = self.cf.file_path.parent.name
            pd_funcs_path = join(self.cf.file_path.parent, f'{self.cf.pkg_name}_functions.csv')
            pd_params_path = join(self.cf.file_path.parent, f'{self.cf.pkg_name}_parameters.csv')
            self.cf.add_pd_funcs = pd.read_csv(pd_funcs_path, sep=';', index_col=0).loc[selected_funcs]
            self.cf.add_pd_params = pd.read_csv(pd_params_path, sep=';', index_col=0)
        else:
            self.cf.pkg_name = None

        for func_key in selected_funcs:
            func = self.module.__dict__[func_key]

            self.cf.add_pd_funcs.loc[func_key, 'module'] = self.module.__name__
            self.cf.add_pd_funcs.loc[func_key, 'ready'] = 0

            self.cf.code_dict[func_key] = inspect.getsource(func)

            # Get Parameters and divide them in existing and setup
            all_parameters = list(inspect.signature(func).parameters)
            self.cf.add_pd_funcs.loc[func_key, 'func_args'] = ','.join(all_parameters)
            existing_parameters = []

            for param_key in all_parameters:
                if param_key in self.cf.exst_parameters or param_key in self.cf.add_pd_params.index:
                    existing_parameters.append(param_key)
                else:
                    self.cf.add_pd_params.loc[param_key, 'function'] = func_key
                    self.cf.add_pd_params.loc[param_key, 'ready'] = 0

            self.cf.param_exst_dict[func_key] = existing_parameters

    def closeEvent(self, event):
        self.load_selected_functions()
        self.cf.update_func_cmbx()
        self.cf.update_exst_param_label()
        self.cf.update_editor()
        event.accept()


class SelectDependencies(QDialog):
    def __init__(self, cf_dialog):
        super().__init__(cf_dialog)
        self.cf_dialog = cf_dialog
        if pd.notna(cf_dialog.add_pd_funcs.loc[cf_dialog.current_function, 'dependencies']):
            self.dpd_list = literal_eval(cf_dialog.add_pd_funcs.loc[cf_dialog.current_function, 'dependencies'])
        else:
            self.dpd_list = []

        layout = QVBoxLayout()
        self.listw = QListWidget()
        self.listw.itemChanged.connect(self.item_checked)
        layout.addWidget(self.listw)

        ok_bt = QPushButton('OK')
        ok_bt.clicked.connect(self.close_dlg)
        layout.addWidget(ok_bt)

        self.populate_listw()
        self.setLayout(layout)
        self.open()

    def populate_listw(self):
        for function in self.cf_dialog.mw.pd_funcs.index:
            item = QListWidgetItem(function)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if function in self.dpd_list:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.listw.addItem(item)

    def item_checked(self, item):
        if item.checkState == Qt.Checked:
            self.dpd_list.append(item.text())
        elif item.text() in self.dpd_list:
            self.dpd_list.remove(item.text())

    def close_dlg(self):
        self.cf_dialog.add_pd_funcs.loc[self.cf_dialog.current_function, 'dependencies'] = str(self.dpd_list)
        self.close()


class TestParamGui(QDialog):
    def __init__(self, cf_dialog):
        super().__init__(cf_dialog)
        self.cf = cf_dialog
        # Dict as Replacement for Parameters in Project for Testing
        self.test_parameters = dict()

        default_string = self.cf.add_pd_params.loc[self.cf.current_parameter, 'default']
        gui_type = self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type']
        try:
            gui_args = literal_eval(self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_args'])
        except (SyntaxError, ValueError):
            gui_args = {}

        self.result, self.gui = self.cf.test_param_gui(default_string, gui_type, gui_args)

        if not self.result:
            self.init_ui()
            self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        # Allow Enter-Press without closing the dialog
        if self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type'] == 'FuncGui':
            void_bt = QPushButton()
            void_bt.setDefault(True)
            layout.addWidget(void_bt)

        layout.addWidget(self.gui)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)


class SavePkgDialog(QDialog):
    def __init__(self, cf_dialog):
        super().__init__(cf_dialog)
        self.cf = cf_dialog

        self.my_pkg_name = None
        self.pkg_path = None

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        self.func_list = BaseList(list(self.cf.add_pd_funcs.loc[self.cf.add_pd_funcs['ready'] == 1].index))
        layout.addWidget(self.func_list)

        pkg_name_label = QLabel('Package-Name:')
        layout.addWidget(pkg_name_label)

        self.pkg_le = QLineEdit()
        if self.cf.pkg_name:
            self.pkg_le.setText(self.cf.pkg_name)
        self.pkg_le.textEdited.connect(self.pkg_le_changed)
        layout.addWidget(self.pkg_le)

        save_bt = QPushButton('Save')
        save_bt.clicked.connect(self.save_pkg)
        layout.addWidget(save_bt)

        cancel_bt = QPushButton('Cancel')
        cancel_bt.clicked.connect(self.close)
        layout.addWidget(cancel_bt)
        self.setLayout(layout)

    def pkg_le_changed(self, text):
        if text != '':
            self.my_pkg_name = text

    def save_pkg(self):
        if self.my_pkg_name or self.cf.pkg_name:
            # Drop all functions with unfinished setup and add the remaining to the main_window-DataFrame
            drop_funcs = self.cf.add_pd_funcs.loc[self.cf.add_pd_funcs['ready'] == 0].index
            final_add_pd_funcs = self.cf.add_pd_funcs.drop(index=drop_funcs)

            drop_params = self.cf.add_pd_params.loc[
                ~self.cf.add_pd_params['function'].isin(final_add_pd_funcs.index)].index
            final_add_pd_params = self.cf.add_pd_params.drop(index=drop_params)

            # Remove no longer needed columns
            del final_add_pd_funcs['ready']
            del final_add_pd_params['ready']
            del final_add_pd_params['function']

            # This is only not None, when the function was imported by edit-functions
            if self.cf.pkg_name:
                # Update and overwrite existing settings for funcs and params
                self.pkg_path = join(self.cf.mw.custom_pkg_path, self.cf.pkg_name)
                pd_funcs_path = join(self.pkg_path, f'{self.cf.pkg_name}_functions.csv')
                pd_params_path = join(self.pkg_path, f'{self.cf.pkg_name}_parameters.csv')
                if isfile(pd_funcs_path):
                    read_pd_funcs = pd.read_csv(pd_funcs_path, sep=';', index_col=0)
                    # Replace indexes from file with same name
                    drop_funcs = [f for f in read_pd_funcs.index if f in final_add_pd_funcs.index]
                    read_pd_funcs.drop(index=drop_funcs, inplace=True)
                    final_add_pd_funcs = read_pd_funcs.append(final_add_pd_funcs)
                if isfile(pd_params_path):
                    read_pd_params = pd.read_csv(pd_params_path, sep=';', index_col=0)
                    # Replace indexes from file with same name
                    drop_params = [p for p in read_pd_params.index if p in final_add_pd_params.index]
                    read_pd_params.drop(index=drop_params, inplace=True)
                    final_add_pd_params = read_pd_params.append(final_add_pd_params)

                if self.my_pkg_name and self.my_pkg_name != self.cf.pkg_name:
                    # Rename folder and .csv-files if you enter a new name
                    new_pkg_path = join(self.cf.mw.custom_pkg_path, self.my_pkg_name)
                    os.rename(self.pkg_path, new_pkg_path)

                    new_pd_funcs_path = join(new_pkg_path, f'{self.my_pkg_name}_functions.csv')
                    os.rename(pd_funcs_path, new_pd_funcs_path)
                    pd_funcs_path = new_pd_funcs_path

                    new_pd_params_path = join(new_pkg_path, f'{self.my_pkg_name}_parameters.csv')
                    os.rename(pd_params_path, new_pd_params_path)
                    pd_params_path = new_pd_params_path

            else:
                self.pkg_path = join(self.cf.mw.custom_pkg_path, self.my_pkg_name)
                if not isdir(self.pkg_path):
                    mkdir(self.pkg_path)
                pd_funcs_path = join(self.pkg_path, f'{self.my_pkg_name}_functions.csv')
                pd_params_path = join(self.pkg_path, f'{self.my_pkg_name}_parameters.csv')
                # Create __init__.py to make it a package
                with open(join(self.pkg_path, '__init__.py'), 'w') as f:
                    f.write('')
                # Copy Origin-Script to Destination
                dest_path = join(self.pkg_path, self.cf.file_path.name)
                shutil.copy2(self.cf.file_path, dest_path)

            final_add_pd_funcs.to_csv(pd_funcs_path, sep=';')
            final_add_pd_params.to_csv(pd_params_path, sep=';')

            self.cf.add_pd_funcs.drop(index=final_add_pd_funcs.index, inplace=True)
            self.cf.update_func_cmbx()
            self.cf.add_pd_params.drop(index=final_add_pd_params.index, inplace=True)
            self.cf.clear_func_items()
            self.cf.clear_param_items()

            self.cf.mw.import_custom_modules()
            self.cf.mw.update_func_bts()
            self.cf.mw.parameters_dock.update_parameters_widget()
            self.close()

        else:
            # If no valid pkg_name is existing
            QMessageBox.warning(self, 'No valid Package-Name!', 'You need to enter a valid Package-Name!')


class ChooseCustomModules(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.modules_list = list(self.mw.all_modules['basic'].keys()) + list(self.mw.all_modules['custom'].keys())
        # Don't include loading-module (should be used by functions)
        self.modules_list.remove('loading')
        self.selected_modules = self.mw.get_setting('selected_modules')

        self.init_ui()
        self.open()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.list_view = QListView()
        self.list_model = CheckListModel(data=self.modules_list, checked=self.selected_modules)
        self.list_view.setModel(self.list_model)
        self.layout.addWidget(self.list_view)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        self.layout.addWidget(close_bt)

        self.setLayout(self.layout)

    def closeEvent(self, event):
        self.mw.settings['selected_modules'] = self.selected_modules
        self.mw.import_custom_modules()
        self.mw.update_func_bts()
        self.mw.parameters_dock.update_parameters_widget()
        event.accept()
