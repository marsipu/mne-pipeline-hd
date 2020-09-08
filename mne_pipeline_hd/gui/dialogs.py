# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import inspect
import shutil
import types
from ast import literal_eval
from functools import partial
from importlib import util
from math import isnan
from os import listdir, mkdir
from os.path import isdir, isfile, join
from pathlib import Path

import pandas as pd
from PyQt5.QtCore import QPoint, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QTextCursor
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDesktopWidget, QDialog, QDockWidget, QFileDialog, QFormLayout,
                             QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem,
                             QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QStyle, QTabWidget,
                             QTableWidget,
                             QTableWidgetItem, QTableWidgetSelectionRange, QTextEdit,
                             QToolTip, QVBoxLayout, QWidget)

from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.gui_utils import ErrorDialog, get_exception_tuple
from mne_pipeline_hd.gui.models import CheckListModel
from mne_pipeline_hd.gui.parameter_widgets import BoolGui, ComboGui, IntGui, StringGui
from mne_pipeline_hd.pipeline_functions import iswin
from mne_pipeline_hd.pipeline_functions.project import Project


class CheckListDlg(QDialog):
    def __init__(self, parent, data, checked):
        """
        BaseClass for A Dialog with a Check-List, open() has to be called in SubClass or directly
        :param parent: parent-Widget
        :param data: Data for the Check-List
        :param checked: List, where Checked Data-Items are stored
        """
        super().__init__(parent)
        self.data = data
        self.checked = checked

        self.init_ui()

    def init_ui(self):
        self.layout = QGridLayout()

        self.lv = QListView()
        self.lm = CheckListModel(self.data, self.checked)
        self.lv.setModel(self.lm)
        self.layout.addWidget(self.lv, 0, 0, 1, 2)

        self.do_bt = QPushButton('<Do Something>')
        self.do_bt.clicked.connect(lambda: None)
        self.layout.addWidget(self.do_bt, 1, 0)

        self.quit_bt = QPushButton('Quit')
        self.quit_bt.clicked.connect(self.close)
        self.layout.addWidget(self.quit_bt, 1, 1)

        self.setLayout(self.layout)


class RemovePPresetDlg(CheckListDlg):
    def __init__(self, parent):
        self.parent = parent
        self.preset_list = [p for p in self.parent.mw.pr.parameters if p != 'Default']
        self.rm_list = []

        super().__init__(parent, self.preset_list, self.rm_list)

        self.do_bt.setText('Remove Parameter-Preset')
        self.do_bt.clicked.connect(self.remove_selected)

        self.open()

    def remove_selected(self):
        for p_preset in self.rm_list:
            self.preset_list.remove(p_preset)
            self.lm.layoutChanged.emit()
            # Remove from Parameters
            self.parent.mw.pr.parameters.pop(p_preset)
            self.parent.update_ppreset_cmbx()

        # If current Parameter-Preset was deleted
        if self.parent.mw.pr.p_preset not in self.parent.mw.pr.parameters:
            self.parent.mw.pr.p_preset = list(self.parent.mw.pr.parameters.keys())[0]
            self.parent.update_all_param_guis()

        self.close()


class RemoveProjectsDlg(CheckListDlg):
    def __init__(self, main_win):
        self.mw = main_win
        self.rm_list = []
        super().__init__(main_win, self.mw.projects, self.rm_list)

        self.do_bt.setText('Remove Projects')
        self.do_bt.clicked.connect(self.remove_selected)

        self.open()

    def remove_selected(self):
        for project in self.rm_list:
            self.mw.projects.remove(project)
            self.lm.layoutChanged.emit()

            # Remove Project-Folder
            try:
                shutil.rmtree(join(self.mw.projects_path, project))
            except OSError:
                QMessageBox.critical(self, 'Deletion impossible',
                                     f'The folder of {project} can\'t be deleted and has to be deleted manually')

        # If current project was deleted, load remaining or create New
        if self.mw.current_project not in self.mw.projects:
            self.mw.get_projects()
            self.mw.pr = Project(self.mw, self.mw.current_project)
            self.mw.project_updated()

        self.close()


class SettingsDlg(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(IntGui(self.mw.qsettings, 'n_jobs', min_val=-1, special_value_text='Auto',
                                hint='Set to the amount of cores of your machine '
                                     'you want to use for multiprocessing', default=-1))
        layout.addWidget(BoolGui(self.mw.settings, 'show_plots', param_alias='Show Plots',
                                 hint='Do you want to show plots?\n'
                                      '(or just save them without showing, then just check "Save Plots")',
                                 default=True))
        layout.addWidget(BoolGui(self.mw.settings, 'save_plots', param_alias='Save Plots',
                                 hint='Do you want to save the plots made to a file?', default=True))
        layout.addWidget(BoolGui(self.mw.qsettings, 'enable_cuda', param_alias='Enable CUDA',
                                 hint='Do you want to enable CUDA? (system has to be setup for cuda)',
                                 default=False))
        layout.addWidget(BoolGui(self.mw.settings, 'shutdown', param_alias='Shutdown',
                                 hint='Do you want to shut your system down after execution of all subjects?'))
        layout.addWidget(IntGui(self.mw.settings, 'dpi', min_val=0, max_val=10000,
                                hint='Set dpi for saved plots', default=300))
        layout.addWidget(ComboGui(self.mw.settings, 'img_format', self.mw.available_image_formats,
                                  param_alias='Image-Format', hint='Choose the image format for plots',
                                  default='.png'))
        layout.addWidget(ComboGui(self.mw.settings, 'mne_backend', options=['mayavi', 'pyvista'],
                                  param_alias='MNE-Backend',
                                  hint='Choose the backend for plotting in 3D (needs Restart)',
                                  default='pyvista'))
        layout.addWidget(StringGui(self.mw.qsettings, 'fs_path', param_alias='FREESURFER_HOME-Path',
                                   hint='Set the Path to the "freesurfer"-directory of your Freesurfer-Installation '
                                        '(for Windows to the LINUX-Path of the Freesurfer-Installation '
                                        'in Windows-Subsystem for Linux(WSL))',
                                   default=None))
        if iswin:
            layout.addWidget(StringGui(self.mw.qsettings, 'mne_path', param_alias='MNE-Python-Path',
                                       hint='Set the LINUX-Path to the mne-environment (e.g ...anaconda3/envs/mne)'
                                            'in Windows-Subsystem for Linux(WSL))',
                                       default=None))

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)


class ParametersDock(QDockWidget):
    def __init__(self, main_win):
        super().__init__('Parameters', main_win)
        self.mw = main_win
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.main_widget = QWidget()
        self.param_guis = {}

        # Drop custom-modules, which aren't selected
        cleaned_pd_funcs = self.mw.pd_funcs.loc[self.mw.pd_funcs['module'].isin(
                self.mw.get_setting('selected_modules'))].copy()

        # Collect args for each function
        self.arg_func_dict = dict()
        # Check if func_args is not NaN
        for func in [f for f in cleaned_pd_funcs.index if isinstance(cleaned_pd_funcs.loc[f, 'func_args'], str)]:
            # Split func_args-string into args and remove trailing spaces
            arg_list = [v.replace(' ', '') for v in cleaned_pd_funcs.loc[func, 'func_args'].split(',')]
            for argument in arg_list:
                # Add each argument to the dict with the func_names by using functions in a list
                if argument in self.arg_func_dict:
                    self.arg_func_dict[argument].append(func)
                else:
                    self.arg_func_dict[argument] = [func]
        # Drop Parameters which aren't used by functions (in selected_modules)
        self.cleaned_pd_params = self.mw.pd_params.loc[self.mw.pd_params.index.isin(self.arg_func_dict.keys())].copy()

        # Group Parameters according to groups of their functions (if used by multiple functions, put into "general")
        for param in self.cleaned_pd_params.index:
            group_name = self.cleaned_pd_params.loc[param, 'group']
            if pd.isna(group_name):
                # Get Group
                func_list = self.arg_func_dict[param]
                # Check if all value in func_list are the same (applies also to len(func_list)==1)
                if all(a == cleaned_pd_funcs.loc[func_list, 'group'][0]
                       for a in cleaned_pd_funcs.loc[func_list, 'group'].values):
                    group_name = cleaned_pd_funcs.loc[func_list[0], 'group']
                else:
                    group_name = 'General'
                self.cleaned_pd_params.loc[param, 'group'] = group_name

            if group_name in self.mw.group_order:
                self.cleaned_pd_params.loc[param, 'group_idx'] = self.mw.group_order[group_name]
            else:
                self.cleaned_pd_params.loc[param, 'group_idx'] = 100

        # Sort values by group_idx for dramaturgically order
        self.cleaned_pd_params.sort_values(by='group_idx', inplace=True)

        self.init_ui()

    def init_ui(self):
        self.general_layout = QVBoxLayout()

        # Add Parameter-Preset-ComboBox
        title_layout = QHBoxLayout()
        p_preset_l = QLabel('Parameter-Presets: ')
        title_layout.addWidget(p_preset_l)
        self.p_preset_cmbx = QComboBox()
        self.p_preset_cmbx.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.p_preset_cmbx.activated.connect(self.p_preset_changed)
        self.update_ppreset_cmbx()
        title_layout.addWidget(self.p_preset_cmbx)

        add_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_bt.clicked.connect(self.add_p_preset)
        title_layout.addWidget(add_bt)

        rm_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_DialogDiscardButton))
        rm_bt.clicked.connect(partial(RemovePPresetDlg, self))
        title_layout.addWidget(rm_bt)

        title_layout.addStretch(stretch=2)

        reset_bt = QPushButton('Reset')
        reset_bt.clicked.connect(self.reset_parameters)
        title_layout.addWidget(reset_bt)

        self.general_layout.addLayout(title_layout)

        self.add_param_guis()

        self.main_widget.setLayout(self.general_layout)
        self.setWidget(self.main_widget)

    def add_param_guis(self):
        # Create Tab-Widget for Parameters, grouped by group
        self.tab_param_widget = QTabWidget()

        grouped_params = self.cleaned_pd_params.groupby('group', sort=False)

        for group_name, group in grouped_params:
            layout = QVBoxLayout()
            tab = QScrollArea()
            child_w = QWidget()
            for idx, parameter in group.iterrows():

                # Get Parameters for Gui-Call
                if pd.notna(parameter['alias']):
                    param_alias = parameter['alias']
                else:
                    param_alias = idx
                if pd.notna(parameter['gui_type']):
                    gui_name = parameter['gui_type']
                else:
                    gui_name = 'FuncGui'
                if pd.notna(parameter['description']):
                    hint = parameter['description']
                else:
                    hint = ''
                try:
                    gui_args = literal_eval(parameter['gui_args'])
                except (SyntaxError, ValueError):
                    gui_args = {}

                gui_handle = getattr(parameter_widgets, gui_name)
                self.param_guis[idx] = gui_handle(self.mw, param_name=idx, param_alias=param_alias,
                                                  hint=hint, **gui_args)

                layout.addWidget(self.param_guis[idx])

            child_w.setLayout(layout)
            tab.setWidget(child_w)
            self.tab_param_widget.addTab(tab, group_name)

        # Set Layout of QWidget (the class itself)
        self.general_layout.addWidget(self.tab_param_widget)

    def update_parameters_widget(self):
        self.general_layout.removeWidget(self.tab_param_widget)
        self.tab_param_widget.close()
        del self.tab_param_widget
        self.add_param_guis()

    def p_preset_changed(self, idx):
        self.mw.pr.p_preset = self.p_preset_cmbx.itemText(idx)
        self.update_all_param_guis()

    def update_ppreset_cmbx(self):
        self.p_preset_cmbx.clear()
        for p_preset in self.mw.pr.parameters.keys():
            self.p_preset_cmbx.addItem(p_preset)
        if self.mw.pr.p_preset in self.mw.pr.parameters.keys():
            self.p_preset_cmbx.setCurrentText(self.mw.pr.p_preset)
        else:
            self.p_preset_cmbx.setCurrentText(list(self.mw.pr.parameters.keys())[0])

    def add_p_preset(self):
        preset_name, ok = QInputDialog.getText(self, 'New Parameter-Preset',
                                               'Enter a name for a new Parameter-Preset')
        if ok:
            self.mw.pr.p_preset = preset_name
            self.mw.pr.load_default_parameters()
            self.p_preset_cmbx.addItem(preset_name)
            self.p_preset_cmbx.setCurrentText(preset_name)
        else:
            pass

    def update_all_param_guis(self):
        for gui_name in self.param_guis:
            param_gui = self.param_guis[gui_name]
            param_gui.read_param()
            param_gui.set_param()

    def reset_parameters(self):
        msgbox = QMessageBox.question(self, 'Reset all Parameters?',
                                      'Do you really want to reset all parameters to their default?',
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if msgbox == QMessageBox.Yes:
            self.mw.pr.load_default_parameters()
            self.update_all_param_guis()


class RunDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        width, height = self.mw.get_ratio_geometry(0.6)
        self.setGeometry(0, 0, width, height)
        self.center()

        self.current_sub = None
        self.current_func = None
        self.prog_running = False

        self.init_ui()
        self.center()

    def init_ui(self):
        self.layout = QGridLayout()

        self.sub_listw = QListWidget()
        self.sub_listw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.layout.addWidget(self.sub_listw, 0, 0)
        self.func_listw = QListWidget()
        self.func_listw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.layout.addWidget(self.func_listw, 0, 1)
        self.console_widget = QTextEdit()
        self.console_widget.setReadOnly(True)
        self.layout.addWidget(self.console_widget, 1, 0, 1, 2)

        self.pgbar = QProgressBar()
        self.pgbar.setValue(0)
        self.layout.addWidget(self.pgbar, 2, 0, 1, 2)

        self.cancel_bt = QPushButton('Cancel')
        self.cancel_bt.setFont(QFont('AnyStyle', 14))
        self.cancel_bt.clicked.connect(self.cancel_funcs)
        self.layout.addWidget(self.cancel_bt, 3, 0)

        self.close_bt = QPushButton('Close')
        self.close_bt.setFont(QFont('AnyStyle', 14))
        self.close_bt.setEnabled(False)
        self.close_bt.clicked.connect(self.close)
        self.layout.addWidget(self.close_bt, 3, 1)

        self.setLayout(self.layout)

    def cancel_funcs(self):
        self.mw.mw_signals.cancel_functions.emit(True)
        self.console_widget.insertHtml('<b><big><center>---Finishing last function...---</center></big></b><br>')
        self.console_widget.ensureCursorVisible()

    def populate(self, mode):
        if mode == 'mri':
            self.populate_listw(self.mw.pr.sel_mri_files, self.mw.sel_mri_funcs)
        elif mode == 'file':
            self.populate_listw(self.mw.pr.sel_files, self.mw.sel_file_funcs)
        elif mode == 'ga':
            self.populate_listw(self.mw.pr.sel_ga_groups, self.mw.sel_ga_funcs)
        elif mode == 'other':
            self.populate_listw(['Other Functions'], self.mw.sel_other_funcs)

    def populate_listw(self, files, funcs):
        for file in files:
            item = QListWidgetItem(file)
            item.setFlags(Qt.ItemIsEnabled)
            self.sub_listw.addItem(item)
        for func in funcs:
            item = QListWidgetItem(func)
            item.setFlags(Qt.ItemIsEnabled)
            self.func_listw.addItem(item)

    def mark_subfunc(self, subfunc):
        if self.current_sub is not None:
            self.current_sub.setBackground(QColor('white'))
        try:
            self.current_sub = self.sub_listw.findItems(subfunc[0], Qt.MatchExactly)[0]
            self.current_sub.setBackground(QColor('green'))
        except IndexError:
            pass
        if self.current_func is not None:
            self.current_func.setBackground(QColor('white'))
        try:
            self.current_func = self.func_listw.findItems(subfunc[1], Qt.MatchExactly)[0]
            self.current_func.setBackground(QColor('green'))
        except IndexError:
            pass

    def clear_marks(self):
        if self.current_sub is not None:
            self.current_sub.setBackground(QColor('white'))
        if self.current_func is not None:
            self.current_func.setBackground(QColor('white'))

    def add_text(self, text):
        self.prog_running = False
        self.console_widget.insertPlainText(text)
        self.console_widget.ensureCursorVisible()

    def progress_text(self, text):
        if self.prog_running:
            # Delete last line
            cursor = self.console_widget.textCursor()
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            self.console_widget.insertPlainText(text)

        else:
            self.prog_running = True
            self.console_widget.insertPlainText(text)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def show_errors(self, err):
        ErrorDialog(err, self)
        self.pgbar.setValue(self.mw.all_prog)
        self.close_bt.setEnabled(True)


class QuickGuide(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        layout = QVBoxLayout()

        text = '<b>Guick-Guide</b><br>' \
               '1. Use the Subject-Wizard to add Subjects and the Subject-Dicts<br>' \
               '2. Select the files you want to execute<br>' \
               '3. Select the functions to execute<br>' \
               '4. If you want to show plots, check Show Plots<br>' \
               '5. For Source-Space-Operations, you need to run MRI-Coregistration from the Input-Menu<br>' \
               '6. For Grand-Averages add a group and add the files, to which you want apply the grand-average'

        self.label = QLabel(text)
        layout.addWidget(self.label)

        ok_bt = QPushButton('OK')
        ok_bt.clicked.connect(self.close)
        layout.addWidget(ok_bt)

        self.setLayout(layout)
        self.open()


# Todo: Rework with Model/View
class CustomFunctionImport(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.path_dict = {}
        self.function_dict = {}
        self.module_dict = {}
        self.func_setup_dict = {}
        self.param_dict = {}
        self.param_exst_dict = {}
        self.param_setup_dict = {}
        self.current_function = None
        self.current_func_row = 0
        self.current_parameter = None
        self.current_param_row = 0

        self.exst_functions = list(self.mw.pd_funcs.index)
        # Todo: Better solution to include subject-attributes
        exst_attributes = ['mw', 'pr', 'sub', 'mri_sub', 'ga_group', 'name', 'save_dir', 'ermsub', 'bad_channels']
        exst_proj_attributes = vars(self.mw.pr)
        self.exst_parameters = exst_attributes + list(exst_proj_attributes) + \
                               list(self.mw.pr.parameters[self.mw.pr.p_preset])

        # Get available parameter-guis
        self.available_param_guis = [pg for pg in dir(parameter_widgets) if 'Gui' in pg and pg != 'QtGui']

        self.add_pd_funcs = pd.DataFrame(columns=['alias', 'tab', 'group', 'subject_loop', 'matplotlib', 'mayavi',
                                                  'dependencies', 'module', 'func_args'])
        self.add_pd_params = pd.DataFrame(columns=['alias', 'default', 'unit', 'description', 'gui_type', 'gui_args'])

        self.yes_icon = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        self.no_icon = self.style().standardIcon(QStyle.SP_DialogCancelButton)

        self.setWindowTitle('Custom-Functions-Setup')

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QHBoxLayout()

        # The Import Group-Box
        import_gbox = QGroupBox('Add Functions')
        import_layout = QVBoxLayout()

        self.exstf_l = QLabel()
        self.exstf_l.setWordWrap(True)
        self.exstf_l.hide()
        import_layout.addWidget(self.exstf_l)

        addfn_bt = QPushButton('Add Functions')
        addfn_bt.clicked.connect(self.get_functions)
        import_layout.addWidget(addfn_bt)

        self.func_tablew = QTableWidget(0, 3)
        self.func_tablew.cellClicked.connect(self.func_item_selected)
        self.func_tablew.setHorizontalHeaderLabels(['Function-Name', 'Module', 'ready'])
        self.func_tablew.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.func_tablew.setFocus()
        import_layout.addWidget(self.func_tablew)

        bt_layout = QHBoxLayout()
        showcode_bt = QPushButton('Show Source-Code')
        showcode_bt.clicked.connect(self.show_source_code)
        bt_layout.addWidget(showcode_bt)

        remove_bt = QPushButton('Remove')
        remove_bt.clicked.connect(self.remove_func_item)
        bt_layout.addWidget(remove_bt)

        save_bt = QPushButton('Save')
        save_bt.clicked.connect(self.save_pkg)
        bt_layout.addWidget(save_bt)

        close_bt = QPushButton('Quit')
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        # Workaround for Dialog not doing anything when Enter is pressed
        void_button = QPushButton(self)
        void_button.setDefault(True)
        bt_layout.addWidget(void_button)

        import_layout.addLayout(bt_layout)
        import_gbox.setLayout(import_layout)

        # The Function-Setup-Groupbox
        func_setup_gbox = QGroupBox('Function-Setup')
        func_setup_layout = QFormLayout()

        self.falias_le = QLineEdit()
        self.falias_le.setToolTip('Set a name if you want something other than the functions-name')
        self.falias_le.textEdited.connect(self.falias_changed)
        func_setup_layout.addRow('Alias', self.falias_le)

        tab_layout = QHBoxLayout()
        self.tab_cmbx = QComboBox()
        self.tab_cmbx.setToolTip('Choose the Tab for the function (Compute/Plot/...)')
        self.tab_cmbx.activated.connect(self.tab_cmbx_changed)
        tab_layout.addWidget(self.tab_cmbx)
        self.tab_chkl = QLabel()
        tab_layout.addWidget(self.tab_chkl)
        func_setup_layout.addRow('Tab', tab_layout)

        group_layout = QHBoxLayout()
        self.group_cmbx = QComboBox()
        self.group_cmbx.setToolTip('Choose the function-group for the function or create a new one')
        self.group_cmbx.setEditable(True)
        self.group_cmbx.activated.connect(self.group_cmbx_changed)
        self.group_cmbx.editTextChanged.connect(self.group_cmbx_edited)
        group_layout.addWidget(self.group_cmbx)
        self.group_chkl = QLabel()
        group_layout.addWidget(self.group_chkl)
        func_setup_layout.addRow('Group', group_layout)

        subloop_layout = QHBoxLayout()
        self.subloop_chbx = QCheckBox()
        self.subloop_chbx.setToolTip('Check if function is applied to each file '
                                     '(instead of e.g. grand-average-functions)')
        self.subloop_chbx.stateChanged.connect(self.subloop_changed)
        subloop_layout.addWidget(self.subloop_chbx)
        self.subloop_chkl = QLabel()
        subloop_layout.addWidget(self.subloop_chkl)
        func_setup_layout.addRow('Subject-Loop?', subloop_layout)

        mtpl_layout = QHBoxLayout()
        self.mtpl_chbx = QCheckBox()
        self.mtpl_chbx.setToolTip('Is the function containing a Matplotlib-Plot?')
        self.mtpl_chbx.stateChanged.connect(self.mtpl_changed)
        mtpl_layout.addWidget(self.mtpl_chbx)
        self.mtpl_chkl = QLabel()
        mtpl_layout.addWidget(self.mtpl_chkl)
        func_setup_layout.addRow('Matplotlib?', mtpl_layout)

        myv_layout = QHBoxLayout()
        self.myv_chbx = QCheckBox()
        self.myv_chbx.setToolTip('Is the function containing a Mayavi-Plot?')
        self.myv_chbx.stateChanged.connect(self.myv_changed)
        myv_layout.addWidget(self.myv_chbx)
        self.myv_chkl = QLabel()
        myv_layout.addWidget(self.myv_chkl)
        func_setup_layout.addRow('Mayavi?', myv_layout)

        self.dpd_bt = QPushButton('Set Dependencies')
        self.dpd_bt.setToolTip('Set the functions that must be activated before or the files that must be present '
                               'for this function to work')
        self.dpd_bt.clicked.connect(self.select_dependencies)
        func_setup_layout.addRow('Dependencies', self.dpd_bt)

        func_setup_gbox.setLayout(func_setup_layout)

        # The Parameter-Setup-Group-Box
        self.param_setup_gbox = QGroupBox('Parameter-Setup')
        param_setup_layout = QVBoxLayout()
        self.exstparam_l = QLabel()
        self.exstparam_l.setWordWrap(True)
        self.exstparam_l.hide()
        param_setup_layout.addWidget(self.exstparam_l)

        self.param_tablew = QTableWidget(0, 2)
        self.param_tablew.cellClicked.connect(self.param_item_selected)
        self.param_tablew.setHorizontalHeaderLabels(['Parameter-Name', 'ready'])
        self.param_tablew.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        param_setup_layout.addWidget(self.param_tablew)

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

        # Todo: Proper Widgets for Gui-Arguments
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

        self.guiargs_le = QLineEdit()
        self.guiargs_le.setToolTip('Set Arguments for the GUI in a dict (optional)')
        self.guiargs_le.textEdited.connect(self.pguiargs_changed)
        param_setup_formlayout.addRow('GUI-Arguments (optional)', self.guiargs_le)

        param_setup_layout.addLayout(param_setup_formlayout)
        self.param_setup_gbox.setLayout(param_setup_layout)

        layout.addWidget(import_gbox)
        layout.addWidget(func_setup_gbox)
        layout.addWidget(self.param_setup_gbox)
        self.setLayout(layout)

        self.populate_tab_cmbx()
        self.populate_group_cmbx()
        self.populate_guitype_cmbx()

    def func_item_selected(self, row):
        # Select row
        self.func_tablew.setRangeSelected(QTableWidgetSelectionRange(row, 0, row, 2), True)
        self.current_function = self.func_tablew.item(row, 0).text()
        self.current_func_row = row
        self.update_func_setup()
        if len(self.param_setup_dict[self.current_function]) > 0:
            self.param_setup_gbox.setEnabled(True)
            self.populate_param_tablew()
            self.current_parameter = self.param_tablew.item(0, 0).text()
            self.update_exst_param_label()
            self.update_param_setup()
        else:
            self.update_exst_param_label()
            # Clear existing entries
            self.populate_param_tablew()
            self.palias_le.clear()
            self.default_le.clear()
            self.unit_le.clear()
            self.guitype_cmbx.setCurrentIndex(-1)
            self.guiargs_le.clear()
            self.param_setup_gbox.setEnabled(False)

    def param_item_selected(self, row):
        # Select row
        self.param_tablew.setRangeSelected(QTableWidgetSelectionRange(row, 0, row, 1), True)
        self.current_parameter = self.param_tablew.item(row, 0).text()
        self.current_param_row = row
        self.update_param_setup()

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
                self.subloop_chbx.setChecked(True)
            else:
                self.subloop_chbx.setChecked(False)
            self.subloop_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.subloop_chbx.setChecked(False)
            self.subloop_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'matplotlib']):
            if self.add_pd_funcs.loc[self.current_function, 'matplotlib']:
                self.mtpl_chbx.setChecked(True)
            else:
                self.mtpl_chbx.setChecked(False)
            self.mtpl_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.mtpl_chbx.setChecked(False)
            self.mtpl_chkl.setPixmap(self.no_icon.pixmap(QSize(16, 16)))
        if pd.notna(self.add_pd_funcs.loc[self.current_function, 'mayavi']):
            if self.add_pd_funcs.loc[self.current_function, 'mayavi']:
                self.myv_chbx.setChecked(True)
            else:
                self.myv_chbx.setChecked(False)
            self.myv_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
        else:
            self.myv_chbx.setChecked(False)
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
        if pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_args']):
            self.guiargs_le.setText(self.add_pd_params.loc[self.current_parameter, 'gui_args'])
        else:
            self.guiargs_le.clear()

    def check_func_setup(self):
        obligatory_items = ['tab', 'group', 'subject_loop', 'matplotlib', 'mayavi']
        # Check, that all obligatory items of the Subject-Setup and the Parameter-Setup are set
        if (all([pd.notna(self.add_pd_funcs.loc[self.current_function, i]) for i in obligatory_items])
                and all([i for i in self.param_setup_dict[self.current_function].values()])):
            self.func_setup_dict[self.current_function] = True
            self.func_tablew.item(self.current_func_row, 2).setIcon(self.yes_icon)

    def check_param_setup(self):
        obligatory_items = ['default', 'gui_type']
        # Check, that all obligatory items of the Parameter-Setup are set
        if all([pd.notna(self.add_pd_params.loc[self.current_parameter, i]) for i in obligatory_items]):
            self.param_setup_dict[self.current_function][self.current_parameter] = True
            self.param_tablew.item(self.current_param_row, 1).setIcon(self.yes_icon)

    # Line-Edit Change-Signals
    def falias_changed(self, text):
        if self.current_function:
            self.add_pd_funcs.loc[self.current_function, 'alias'] = text

    def subloop_changed(self, state):
        if self.current_function:
            if state:
                self.add_pd_funcs.loc[self.current_function, 'subject_loop'] = True
            else:
                self.add_pd_funcs.loc[self.current_function, 'subject_loop'] = False
            self.subloop_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def mtpl_changed(self, state):
        if self.current_function:
            if state:
                self.add_pd_funcs.loc[self.current_function, 'matplotlib'] = True
            else:
                self.add_pd_funcs.loc[self.current_function, 'matplotlib'] = False
            self.mtpl_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
            self.check_func_setup()

    def myv_changed(self, state):
        if self.current_function:
            if state:
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
            # Check, if default_value and gui_type match
            if pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_type']):
                result = self.test_param_gui(default_string=text,
                                             gui_type=self.add_pd_params.loc[self.current_parameter, 'gui_type'])
            else:
                result = True
            if result:
                self.add_pd_params.loc[self.current_parameter, 'default'] = text
                self.default_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
                self.check_param_setup()
                self.check_func_setup()
            else:
                self.default_le.clear()
                QMessageBox.warning(self, 'Invalid default-value',
                                    'The default-value doesn\'t match the selected gui-type')

    def punit_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'unit'] = text

    def pdescription_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'description'] = text

    def pguiargs_changed(self, text):
        if self.current_parameter:
            self.add_pd_params.loc[self.current_parameter, 'gui_args'] = text

    def populate_func_tablew(self):
        row_count = self.func_tablew.rowCount()
        self.func_tablew.setRowCount(len(self.function_dict))
        for key in self.function_dict:
            name_item = QTableWidgetItem(key)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.func_tablew.setItem(row_count, 0, name_item)
            module_item = QTableWidgetItem(self.module_dict[key])
            module_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.func_tablew.setItem(row_count, 1, module_item)
            setup_item = QTableWidgetItem()
            setup_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            if self.func_setup_dict[key]:
                setup_item.setIcon(self.yes_icon)
            else:
                setup_item.setIcon(self.no_icon)
            self.func_tablew.setItem(row_count, 2, setup_item)
            row_count += 1

    def populate_param_tablew(self):
        if self.current_function and self.current_function in self.param_setup_dict:
            # Remove Rows of last function
            row_count = self.param_tablew.rowCount()
            while row_count > 0:
                self.param_tablew.removeRow(0)
                row_count -= 1
            params = self.param_setup_dict[self.current_function]
            self.param_tablew.setRowCount(row_count + len(params))
            for param in params:
                name_item = QTableWidgetItem(param)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.param_tablew.setItem(row_count, 0, name_item)
                setup_item = QTableWidgetItem()
                setup_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                if self.param_setup_dict[self.current_function][param]:
                    setup_item.setIcon(self.yes_icon)
                else:
                    setup_item.setIcon(self.no_icon)
                self.param_tablew.setItem(row_count, 1, setup_item)
                row_count += 1

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
        if self.current_parameter:
            # Check, if default_value and gui_type match
            if pd.notna(self.add_pd_params.loc[self.current_parameter, 'default']):
                result = self.test_param_gui(default_string=self.add_pd_params.loc[self.current_parameter, 'default'],
                                             gui_type=text)
            else:
                result = True
            if result:
                self.add_pd_params.loc[self.current_parameter, 'gui_type'] = text
                self.guitype_chkl.setPixmap(self.yes_icon.pixmap(QSize(16, 16)))
                self.check_param_setup()
                self.check_func_setup()
            else:
                self.guitype_cmbx.setCurrentIndex(-1)
                QMessageBox.warning(self, 'Invalid gui_type-value',
                                    'The gui_type-value doesn\'t match the entered default_value')

    def get_functions(self):
        # Returns tuple of files-list and file-type
        files_list = QFileDialog.getOpenFileNames(self, 'Choose the Python-File//s containing your function to import',
                                                  filter='Python-File (*.py)')[0]
        already_exst_funcs = []
        if files_list:
            for path_string in files_list:
                file_path = Path(path_string)
                spec = util.spec_from_file_location(file_path.stem, file_path)
                module = util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except:
                    err = get_exception_tuple()
                    ErrorDialog(err, self)
                for func_key in module.__dict__:
                    # Check, if function is already existing
                    if func_key not in self.exst_functions:
                        func = module.__dict__[func_key]
                        # Only functions are allowed (Classes should be called from function)
                        if isinstance(func, types.FunctionType) and func.__module__ == module.__name__:
                            self.path_dict[func_key] = file_path
                            self.function_dict[func_key] = func
                            self.module_dict[func_key] = module.__name__
                            self.func_setup_dict[func_key] = False
                            # Append empty Series to Func-Data-Frame
                            func_series = pd.Series([], name=func_key, dtype='object')
                            self.add_pd_funcs = self.add_pd_funcs.append(func_series)
                            self.add_pd_funcs.loc[func_key, 'module'] = module.__name__
                            # Get Parameters and divide them in existing and setup
                            signature = inspect.signature(func)
                            all_parameters = [signature.parameters[p].name for p in signature.parameters]
                            self.param_dict[func_key] = all_parameters
                            self.add_pd_funcs.loc[func_key, 'func_args'] = ','.join(all_parameters)
                            self.param_exst_dict[func_key] = [p for p in all_parameters if p in self.exst_parameters]
                            self.param_setup_dict[func_key] = {}
                            for param in [p for p in all_parameters if p not in self.exst_parameters]:
                                self.param_setup_dict[func_key][param] = False
                                # Append empty Series to Func-Data-Frame
                                param_series = pd.Series([], name=param, dtype='object')
                                if param not in self.add_pd_params.index:
                                    self.add_pd_params = self.add_pd_params.append(param_series)
                    else:
                        already_exst_funcs.append(func_key)
            if len(already_exst_funcs) > 0:
                self.exstf_l.setText(f'Already existing functions: {already_exst_funcs}')
                self.exstf_l.show()
            else:
                self.exstf_l.hide()
            self.populate_func_tablew()

    def remove_func_item(self):
        row = self.func_tablew.currentRow()
        if row >= 0:
            name = self.func_tablew.item(row, 0).text()

            self.function_dict.pop(name, None)
            self.module_dict.pop(name, None)
            self.func_setup_dict.pop(name, None)

            self.func_tablew.removeRow(row)

    def show_source_code(self):
        row = self.func_tablew.currentRow()
        if row >= 0:
            name = self.func_tablew.item(row, 0).text()
            show_dlg = QDialog(self)
            layout = QVBoxLayout()
            label = QLabel(inspect.getsource(self.function_dict[name]))
            scroll_area = QScrollArea()
            scroll_area.setWidget(label)
            layout.addWidget(scroll_area)
            ok_bt = QPushButton('Close')
            ok_bt.clicked.connect(show_dlg.close)
            layout.addWidget(ok_bt)
            show_dlg.setLayout(layout)
            show_dlg.open()

    def select_dependencies(self):
        SelectDependencies(self)

    def test_param_gui(self, default_string, gui_type):
        # Simulate CustomFunctionImport as Project-Class
        self.parameters = {'Test': {}}
        self.p_preset = 'Test'
        try:
            self.parameters['Test'][self.current_parameter] = literal_eval(default_string)
        except (ValueError, SyntaxError):
            # Allow parameters to be defined by functions by numpy, etc.
            if self.add_pd_params.loc[self.current_parameter, 'gui_type'] == 'FuncGui':
                self.parameters['Test'][self.current_parameter] = eval(default_string)
            else:
                self.parameters['Test'][self.current_parameter] = default_string
        gui_handle = getattr(parameter_widgets, gui_type)
        try:
            gui_handle(self, self.current_parameter, 'Test', '')
        except TypeError:
            result = False
        else:
            result = True
        return result

    def show_param_gui(self):
        if self.current_parameter and pd.notna(self.add_pd_params.loc[self.current_parameter, 'gui_type']):
            TestParamGui(self)

    def save_pkg(self):
        if any([self.func_setup_dict[k] for k in self.func_setup_dict]):
            SavePkgDialog(self)

    def closeEvent(self, event):
        drop_funcs = [f for f in self.func_setup_dict if not self.func_setup_dict[f]]

        if len(drop_funcs) > 0:
            answer = QMessageBox.question(self, 'Close Custom-Functions?', f'There are still unfinished functions:\n'
                                                                           f'{drop_funcs}\n'
                                                                           f'Do you still want to quit?')
        else:
            answer = None

        if answer == QMessageBox.Yes or answer is None:
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
        # Replacement for Parameters in Project for Testing
        self.parameters = {'Test': {}}
        self.p_preset = 'Test'
        string_param = self.cf.add_pd_params.loc[self.cf.current_parameter, 'default']
        try:
            self.parameters['Test'][self.cf.current_parameter] = literal_eval(string_param)
        except (ValueError, SyntaxError):
            # Allow parameters to be defined by functions by numpy, etc.
            if self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type'] == 'FuncGui':
                self.parameters['Test'][self.cf.current_parameter] = eval(string_param)
            else:
                self.parameters['Test'][self.cf.current_parameter] = string_param

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        # Allow Enter-Press without closing the dialog
        if self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type'] == 'FuncGui':
            void_bt = QPushButton()
            void_bt.setDefault(True)
            layout.addWidget(void_bt)

        gui_handle = getattr(parameter_widgets, self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_type'])
        if isnan(self.cf.add_pd_params.loc[self.cf.current_parameter, 'alias']):
            param_alias = self.cf.current_parameter
        else:
            param_alias = self.cf.add_pd_params.loc[self.cf.current_parameter, 'alias']
        if isnan(self.cf.add_pd_params.loc[self.cf.current_parameter, 'description']):
            hint = ''
        else:
            hint = self.cf.add_pd_params.loc[self.cf.current_parameter, 'description']
        try:
            gui_args = literal_eval(self.cf.add_pd_params.loc[self.cf.current_parameter, 'gui_args'])
        except (SyntaxError, ValueError):
            gui_args = {}
        try:
            param_gui = gui_handle(self, self.cf.current_parameter, param_alias, hint, **gui_args)
            layout.addWidget(param_gui)
        except:
            err = get_exception_tuple()
            ErrorDialog(err, self)
            self.close()
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)


class SavePkgDialog(QDialog):
    def __init__(self, cf_dialog):
        super().__init__(cf_dialog)
        self.cf = cf_dialog
        self.pkg_path = None

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QGridLayout()
        self.pkg_le = QLineEdit()
        self.pkg_le.textEdited.connect(self.pkg_le_changed)
        layout.addWidget(self.pkg_le, 0, 0, 1, 2)

        save_bt = QPushButton('Save')
        save_bt.clicked.connect(self.save_pkg)
        layout.addWidget(save_bt, 1, 0)

        cancel_bt = QPushButton('Cancel')
        cancel_bt.clicked.connect(self.close)
        layout.addWidget(cancel_bt, 1, 1)
        self.setLayout(layout)

    def pkg_le_changed(self, text):
        if text in listdir(self.cf.mw.custom_pkg_path):
            QToolTip.showText(self.pkg_le.mapToGlobal(QPoint(0, 0)), 'This name is already used!')
            self.pkg_le.setText('')
        else:
            self.pkg_name = self.pkg_le.text()
            self.pkg_path = join(self.cf.mw.custom_pkg_path, self.pkg_name)

    def save_pkg(self):
        copy_modules = set()
        for func in self.cf.path_dict:
            copy_modules.add(self.cf.path_dict[func])
        if not isdir(self.pkg_path):
            mkdir(self.pkg_path)
        # Create __init__.py to make it a package
        with open(join(self.pkg_path, '__init__.py'), 'w') as f:
            f.write('')
        for ori_path in copy_modules:
            shutil.copy2(ori_path, join(self.pkg_path, Path(ori_path).name))
        # Drop all functions with unfinished setup and add them to the main_window-DataFrame
        drop_funcs = [f for f in self.cf.func_setup_dict if not self.cf.func_setup_dict[f]]
        final_add_pd_funcs = self.cf.add_pd_funcs.drop(labels=drop_funcs, axis=0)
        param_set = set()
        for func in final_add_pd_funcs.index:
            for param in self.cf.param_setup_dict[func]:
                param_set.add(param)
        final_add_pd_params = self.cf.add_pd_params.loc[param_set]

        pd_funcs_path = join(self.pkg_path, f'{self.pkg_name}_functions.csv')
        pd_params_path = join(self.pkg_path, f'{self.pkg_name}_parameters.csv')

        if isfile(pd_funcs_path):
            read_pd_funcs = pd.read_csv(pd_funcs_path, sep=';', index_col=0)
            # Check, that there are no duplicates
            drop_funcs = [f for f in read_pd_funcs.index if f in final_add_pd_funcs]
            read_pd_funcs.drop(labels=drop_funcs, axis=0)
            final_add_pd_funcs = read_pd_funcs.append(final_add_pd_funcs)
        final_add_pd_funcs.to_csv(pd_funcs_path, sep=';')
        if isfile(pd_params_path):
            read_pd_params = pd.read_csv(pd_params_path, sep=';', index_col=0)
            # Check, that there are no duplicates
            drop_params = [p for p in read_pd_params.index if p in final_add_pd_params]
            read_pd_params.drop(labels=drop_params, axis=0)
            final_add_pd_params = read_pd_params.append(final_add_pd_params)
        final_add_pd_params.to_csv(pd_params_path, sep=';')

        for func in final_add_pd_funcs.index:
            item_list = self.cf.func_tablew.findItems(func, Qt.MatchExactly)
            if item_list:
                item = item_list[0]
                self.cf.func_tablew.removeRow(self.cf.func_tablew.row(item))

        self.cf.mw.import_custom_modules()
        self.cf.mw.update_func_bts()
        self.cf.mw.parameters_dock.update_parameters_widget()
        self.close()

        # Todo: update func-Buttons and Parameters-Widgets


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
        self.mw.update_func_bts()
        self.mw.parameters_dock.update_parameters_widget()
        event.accept()
