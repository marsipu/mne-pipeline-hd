# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import logging
import os
import re
import shutil
import sys
import traceback
from ast import literal_eval
from functools import partial
from importlib import util
from os.path import join
from pathlib import Path
from subprocess import run

import mne
import pandas as pd
import qdarkstyle
from PyQt5.QtCore import QObject, QSettings, QThreadPool, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox, QDesktopWidget, QDialog, QFileDialog,
                             QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
                             QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox,
                             QStyle,
                             QStyleFactory, QTabWidget, QTextEdit, QToolTip, QVBoxLayout, QWidget)
from mayavi import mlab

from src import basic_functions, resources
from src.gui import parameter_widgets
from src.gui.qt_utils import ErrorDialog, OutputStream, get_exception_tuple
from src.gui.subject_widgets import (AddFilesDialog, AddMRIDialog, SubBadsDialog, SubDictDialog,
                                     SubjectDock,
                                     SubjectWizard)
from src.pipeline_functions import iswin
from src.pipeline_functions.function_utils import (CustomFunctionImport, FunctionWorker, func_from_def)
from src.pipeline_functions.project import MyProject


def get_upstream():
    """
    Get and merge the upstream branch from a repository (e.g. developement-branch of mne-pyhon)
    :return: None
    """
    if iswin:
        command = "git fetch upstream & git checkout master & git merge upstream/master"
    else:
        command = "git fetch upstream; git checkout master; git merge upstream/master"
    result = run(command)
    print(result.stdout)


class MainWinSignals(QObject):
    # Signals to send into QThread to control function execution
    cancel_functions = pyqtSignal(bool)
    plot_running = pyqtSignal(bool)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.settings = QSettings()

        self.app.setFont(QFont('Calibri', 10))
        self.setWindowTitle('MNE-Pipeline HD')
        self.setCentralWidget(QWidget(self))
        self.general_layout = QVBoxLayout()
        self.centralWidget().setLayout(self.general_layout)

        # Initialize QThreadpool for creating separate Threads apart from GUI-Event-Loop later
        self.threadpool = QThreadPool()
        print(f'Multithreading with maximum {self.threadpool.maxThreadCount()} threads')

        QToolTip.setFont(QFont('SansSerif', 10))
        self.change_style('Fusion')

        # Prepare Dark-Mode
        self.dark_sheet = qdarkstyle.load_stylesheet_pyqt5()

        # Attributes for class-methods
        self.mw_signals = MainWinSignals()
        self.module_err_dlg = None
        self.func_dict = dict()
        self.bt_dict = dict()

        # Todo: Straighten confusing main_win.init() (Project vs. ModuleImport vs. pdDataFrames)
        # Pandas-DataFrame for Parameter-Pipeline-Data (parameter-values are stored in main_win.pr.parameters)
        self.pd_params = pd.read_csv(join(resources.__path__[0], 'parameters.csv'), sep=';', index_col=0)

        # Get available parameter-guis
        self.available_param_guis = [pg for pg in dir(parameter_widgets) if 'Gui' in pg and pg != 'QtGui']

        # Call project-class
        self.pr = MyProject(self)

        # Lists of functions separated in execution groups (mri_subject, subject, grand-average)
        self.pd_funcs = pd.read_csv(join(resources.__path__[0], 'functions.csv'), sep=';', index_col=0)

        # Import the basic- and custom-function-modules
        self.import_func_modules()

        # Load last parameter-preset
        self.pr.p_preset = self.settings.value('parameter_preset') or 'Default'
        if self.pr.p_preset not in self.pr.parameters:
            self.pr.p_preset = 'Default'
        # Load project-parameters after import of func_modules
        self.pr.load_parameters()
        # Load file_parameters-Data-Frame, because it needs the loaded parameters
        self.pr.load_file_parameters()
        # After load_parameters, because event-id is needed
        self.pr.populate_directories()

        self.mri_funcs = self.pd_funcs[(self.pd_funcs['group'] == 'mri_subject_operations')
                                       & (self.pd_funcs['subject_loop'] == True)]
        self.file_funcs = self.pd_funcs[(self.pd_funcs['group'] != 'mri_subject_operations')
                                        & (self.pd_funcs['subject_loop'] == True)]
        self.ga_funcs = self.pd_funcs[(self.pd_funcs['subject_loop'] == False)]

        # Get function-tabs and function-groups
        self.f_tabs = set(self.pd_funcs['tab'])
        self.f_groups = set(self.pd_funcs['group'])

        # Todo: Real logging
        # Set logging
        logging.basicConfig(filename=join(self.pr.pscripts_path, '_pipeline.log'), filemode='w')

        # initiate Subject-Dock here to avoid AttributeError
        self.subject_dock = SubjectDock(self)

        # Todo: Structure Main-Win-Frontend-Construction better
        # Call window-methods
        self.make_menu()
        self.add_dock_windows()
        self.make_toolbar()
        self.update_statusbar()
        self.make_func_bts()
        self.add_parameter_gui_tab()
        self.add_main_bts()
        self.get_toolbox_params()

        self.desk_geometry = self.app.desktop().availableGeometry()
        self.size_ratio = 0.9
        height = self.desk_geometry.height() * self.size_ratio
        width = self.desk_geometry.width() * self.size_ratio
        self.setGeometry(0, 0, width, height)

    # Todo: Import (maybe as custom-packages), which makes import across custom-packages possible
    def import_func_modules(self):
        """
        Load all modules in basic_functions and custom_functions
        """
        basic_functions_list = [x for x in dir(basic_functions) if '__' not in x]
        self.all_modules = {}
        self.custom_packages = {}
        # Load basic-modules
        for module_name in basic_functions_list:
            self.all_modules[module_name] = getattr(basic_functions, module_name)
        # Load custom_modules
        pd_functions_pattern = r'.*_functions\.csv'
        pd_parameters_pattern = r'.*_parameters\.csv'
        custom_module_pattern = r'(.+)(\.py)'
        for dir_path, dir_names, file_names in os.walk(self.pr.custom_pkg_path):
            for file_name in file_names:
                functions_match = re.match(pd_functions_pattern, file_name)
                parameters_match = re.match(pd_parameters_pattern, file_name)
                custom_module_match = re.match(custom_module_pattern, file_name)
                if functions_match:
                    read_pd_funcs = pd.read_csv(join(dir_path, file_name), sep=';', index_col=0)
                    for idx in [ix for ix in read_pd_funcs.index if ix not in self.pd_funcs.index]:
                        self.pd_funcs = self.pd_funcs.append(read_pd_funcs.loc[idx])
                elif parameters_match:
                    read_pd_params = pd.read_csv(join(dir_path, file_name), sep=';', index_col=0)
                    for idx in [ix for ix in read_pd_params.index if ix not in self.pd_params.index]:
                        self.pd_params = self.pd_params.append(read_pd_params.loc[idx])
                elif custom_module_match:
                    module_name = custom_module_match.group(1)
                    if module_name != '__init__':
                        spec = util.spec_from_file_location(file_name, join(dir_path, file_name))
                        module = util.module_from_spec(spec)
                        try:
                            spec.loader.exec_module(module)
                        except:
                            exc_tuple = get_exception_tuple()
                            self.module_err_dlg = ErrorDialog(self, exc_tuple,
                                                              title=f'Error in custom-module: {module_name}')
                        else:
                            # Add Module to dictionary
                            self.all_modules[module_name] = module
                            # Assign Module-Names to their Package
                            if dir_path != self.pr.custom_pkg_path:
                                pkg_name = Path(dir_path).name
                                if pkg_name in self.custom_packages:
                                    self.custom_packages[pkg_name].append(module_name)
                                else:
                                    self.custom_packages.update({pkg_name: [module_name]})

    def make_menu(self):
        # & in front of text-string creates automatically a shortcut with Alt + <letter after &>
        # Input
        input_menu = self.menuBar().addMenu('&Input')

        input_menu.addAction('Subject-Wizard', partial(SubjectWizard, self))
        input_menu.addSeparator()
        aaddfiles = QAction('Add Files', parent=self)
        aaddfiles.setShortcut('Ctrl+F')
        aaddfiles.setStatusTip('Add your MEG-Files here')
        aaddfiles.triggered.connect(partial(AddFilesDialog, self))
        input_menu.addAction(aaddfiles)

        aaddmri = QAction('Add MRI-Subject', self)
        aaddmri.setShortcut('Ctrl+M')
        aaddmri.setStatusTip('Add your Freesurfer-Files here')
        aaddmri.triggered.connect(partial(AddMRIDialog, self))
        input_menu.addAction(aaddmri)

        input_menu.addAction('Assign File --> MRI-Subject',
                             partial(SubDictDialog, self, 'mri'))
        input_menu.addAction('Assign File --> ERM-File',
                             partial(SubDictDialog, self, 'erm'))
        input_menu.addAction('Assign Bad-Channels --> File',
                             partial(SubBadsDialog, self))
        input_menu.addSeparator()
        input_menu.addAction('MRI-Coregistration', mne.gui.coregistration)

        # Custom-Functions
        self.customf_menu = self.menuBar().addMenu('&Custom Functions')
        self.aadd_customf = self.customf_menu.addAction('&Add custom Functions', self.add_customf)

        # View
        self.view_menu = self.menuBar().addMenu('&View')

        self.adark_mode = self.view_menu.addAction('&Dark-Mode', self.dark_mode)
        self.adark_mode.setCheckable(True)
        if self.settings.value('dark_mode') == 'true':
            self.adark_mode.setChecked(True)
        else:
            self.adark_mode.setChecked(False)
        self.view_menu.addAction('&Full-Screen', self.full_screen).setCheckable(True)

        # Settings
        self.settings_menu = self.menuBar().addMenu('&Settings')

        self.settings_menu.addAction('&Change Home-Path', self.change_home_path)
        self.settings_menu.addAction('Reset Parameters', self.reset_parameters)

        self.pyfiles = QAction('Load .py-Files')
        self.pyfiles.triggered.connect(self.pr.load_py_lists)
        self.settings_menu.addAction(self.pyfiles)

        self.asub_preload = QAction('Preload Subject-Data')
        self.asub_preload.setCheckable(True)
        if self.settings.value('sub_preload') == 'true':
            self.asub_preload.setChecked(True)
        else:
            self.asub_preload.setChecked(False)
        self.asub_preload.toggled.connect(partial(self.set_bool_setting, self.asub_preload, 'sub_preload'))
        self.settings_menu.addAction(self.asub_preload)

        # About
        about_menu = self.menuBar().addMenu('About')
        # about_menu.addAction('Update Pipeline', self.update_pipeline)
        # about_menu.addAction('Update MNE-Python', self.update_mne)
        about_menu.addAction('Quick-Guide', self.quick_guide)
        about_menu.addAction('About QT', self.about_qt)

    def make_toolbar(self):
        self.toolbar = self.addToolBar('Tools')
        # Add Project-Tools
        self.project_tools()
        self.toolbar.addSeparator()

        self.toolbar.addWidget(QLabel('n_jobs: '))
        self.n_jobs_sb = QSpinBox(self)
        self.n_jobs_sb.setMinimum(0)
        self.n_jobs_sb.setSpecialValueText('Auto')
        self.n_jobs_sb.valueChanged.connect(self.n_jobs_changed)
        self.toolbar.addWidget(self.n_jobs_sb)

        self.toolbar.addSeparator()

        self.show_plots_chkbx = QCheckBox('Show Plots', self)
        self.show_plots_chkbx.stateChanged.connect(partial(self.chkbx_changed,
                                                           self.show_plots_chkbx, 'show_plots'))
        self.show_plots_chkbx.setToolTip('Do you want to show plots?\n'
                                         '(or just save them without showing, checking "Save Plots")')
        self.toolbar.addWidget(self.show_plots_chkbx)

        self.save_plots_chkbx = QCheckBox('Save Plots', self)
        self.save_plots_chkbx.stateChanged.connect(partial(self.chkbx_changed, self.save_plots_chkbx, 'save_plots'))
        self.save_plots_chkbx.setToolTip('Do you want to save the plots made to a file?')
        self.toolbar.addWidget(self.save_plots_chkbx)

        self.overwrite_chkbx = QCheckBox('Overwrite', self)
        self.overwrite_chkbx.stateChanged.connect(partial(self.chkbx_changed, self.overwrite_chkbx, 'overwrite'))
        self.overwrite_chkbx.setToolTip('Do you want to overwrite the already existing files?')
        self.toolbar.addWidget(self.overwrite_chkbx)

        self.enable_cuda_chkbx = QCheckBox('Enable CUDA', self)
        self.enable_cuda_chkbx.stateChanged.connect(partial(self.chkbx_changed, self.enable_cuda_chkbx, 'enable_cuda'))
        self.overwrite_chkbx.setToolTip('Do you want to enable CUDA? (system has to be setup for cuda)')
        self.toolbar.addWidget(self.enable_cuda_chkbx)

        self.shutdown_chkbx = QCheckBox('Shutdown', self)
        self.shutdown_chkbx.stateChanged.connect(partial(self.chkbx_changed, self.shutdown_chkbx, 'shutdown'))
        self.shutdown_chkbx.setToolTip('Do you want to shut your system down after execution of all subjects?')
        self.toolbar.addWidget(self.shutdown_chkbx)

    def n_jobs_changed(self, value):
        # In MNE-Python -1 is automatic, for SpinBox 0 is already auto
        if value == 0:
            self.pr.parameters[self.pr.p_preset]['n_jobs'] = -1
        else:
            self.pr.parameters[self.pr.p_preset]['n_jobs'] = value
        self.qall_parameters.update_param_gui('n_jobs')

    def chkbx_changed(self, chkbx, param):
        self.pr.parameters[self.pr.p_preset][param] = chkbx.isChecked()
        self.qall_parameters.update_param_gui(param)

    # Todo: Statusbar with purpose
    def update_statusbar(self):
        self.statusBar().showMessage(f'Home-Path: {self.pr.home_path}, Project: {self.pr.project_name},'
                                     f'Parameter-Preset: {self.pr.p_preset}')

    def add_dock_windows(self):
        self.addDockWidget(Qt.LeftDockWidgetArea, self.subject_dock)
        self.view_menu.addAction(self.subject_dock.toggleViewAction())

    def change_home_path(self):
        # First save the former projects-data
        self.pr.save_sub_lists()
        self.pr.save_parameters()

        new_home_path = QFileDialog.getExistingDirectory(self, 'Change folder to store your Pipeline-Projects')
        if new_home_path == '':
            pass
        else:
            self.pr.home_path = new_home_path
            self.settings.setValue('home_path', self.pr.home_path)
            self.pr.get_paths()
            self.update_project_box()
            self.change_project(self.pr.projects[0])
            self.subject_dock.update_mri_subjects_list()

    def add_project(self):
        # First save the former projects-data
        self.pr.save_sub_lists()
        self.pr.save_parameters()

        project, ok = QInputDialog.getText(self, 'New Project',
                                           'Enter a project-name for a new project')
        if ok:
            self.pr.project_name = project
            self.pr.projects.append(project)
            self.settings.setValue('project_name', self.pr.project_name)
            self.project_box.addItem(project)
            self.project_box.setCurrentText(project)
            self.change_project(project)
        else:
            pass

    # Todo: Replace with Model/View-Template
    def remove_project(self):
        # First save the former projects-data
        self.pr.save_sub_lists()
        self.pr.save_parameters()

        dialog = QDialog(self)
        dialog.setWindowTitle('Remove Project')
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Select Project for removal'))

        plistw = QListWidget(self)
        for project in self.pr.projects:
            item = QListWidgetItem(project)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            plistw.addItem(item)
        layout.addWidget(plistw)

        def remove_selected():
            rm_list = list()
            for x in range(plistw.count()):
                chk_item = plistw.item(x)
                if chk_item.checkState() == Qt.Checked:
                    rm_list.append(chk_item.text())

            for rm_project in rm_list:
                plistw.takeItem(plistw.row(plistw.findItems(rm_project, Qt.MatchExactly)[0]))
                self.pr.projects.remove(rm_project)
                self.project_box.removeItem(self.project_box.findText(rm_project, Qt.MatchExactly))
                if rm_project == self.pr.project_name:
                    self.change_project(self.pr.projects[0])
                    self.project_box.setCurrentText(self.pr.projects[0])
                try:
                    shutil.rmtree(join(self.pr.projects_path, rm_project))
                except OSError:
                    pass

        bt_layout = QHBoxLayout()
        rm_bt = QPushButton('Remove')
        rm_bt.clicked.connect(remove_selected)
        bt_layout.addWidget(rm_bt)
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(dialog.close)
        bt_layout.addWidget(close_bt)
        layout.addLayout(bt_layout)

        dialog.setLayout(layout)
        dialog.open()

    def project_tools(self):
        self.project_box = QComboBox()
        self.project_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for project in self.pr.projects:
            self.project_box.addItem(project)
        self.project_box.setCurrentText(self.pr.project_name)
        self.project_box.activated.connect(self.project_changed)
        proj_box_label = QLabel('<b>Project: <b>')
        self.toolbar.addWidget(proj_box_label)
        self.toolbar.addWidget(self.project_box)

        aadd = QAction(parent=self, icon=self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        aadd.triggered.connect(self.add_project)
        self.toolbar.addAction(aadd)

        arm = QAction(parent=self, icon=self.style().standardIcon(QStyle.SP_DialogDiscardButton))
        arm.triggered.connect(self.remove_project)
        self.toolbar.addAction(arm)

    def project_changed(self, idx):
        # First save the former projects-data
        self.pr.save_sub_lists()
        self.pr.save_parameters()

        self.change_project(self.project_box.itemText(idx))

    def change_project(self, project):
        self.pr.project_name = project
        self.pr.p_preset = 'Default'
        self.settings.setValue('project_name', self.pr.project_name)
        print(f'{self.pr.project_name} selected')

        # Set new logging
        logging.basicConfig(filename=join(self.pr.pscripts_path, '_pipeline.log'), filemode='w')

        self.pr.make_paths()
        self.pr.load_parameters()
        self.qall_parameters.update_all_param_guis()
        self.pr.populate_directories()

        self.pr.load_sub_lists()
        self.subject_dock.update_subjects_list()
        self.subject_dock.ga_widget.update_treew()

        self.update_statusbar()

    def update_project_box(self):
        self.project_box.clear()
        for project in self.pr.projects:
            self.project_box.addItem(project)

    def add_customf(self):
        self.cf_import = CustomFunctionImport(self)

    def reset_parameters(self):
        msgbox = QMessageBox.question(self, 'Reset all Parameters?',
                                      'Do you really want to reset all parameters to their default?',
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if msgbox == QMessageBox.Yes:
            self.pr.load_default_parameters()
            self.qall_parameters.update_all_param_guis()

    def dark_mode(self):
        if self.adark_mode.isChecked():
            self.app.setStyleSheet(self.dark_sheet)
            self.settings.setValue('dark_mode', True)
        else:
            self.app.setStyleSheet('')
            self.settings.setValue('dark_mode', False)

    def full_screen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def set_bool_setting(self, action, setting_name):
        self.settings.setValue(setting_name, action.isChecked())

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def raise_win(self):
        if iswin:
            # on windows we can raise the window by minimizing and restoring
            self.showMinimized()
            self.setWindowState(Qt.WindowActive)
            self.showNormal()
            if self.module_err_dlg:
                self.module_err_dlg.showMinimized()
                self.module_err_dlg.setWindowState(Qt.WindowActive)
                self.module_err_dlg.showNormal()
        else:
            # on osx we can raise the window. on unity the icon in the tray will just flash.
            self.activateWindow()
            self.raise_()
            if self.module_err_dlg:
                self.module_err_dlg.activateWindow()
                self.module_err_dlg.raise_()

    def change_style(self, style_name):
        self.app.setStyle(QStyleFactory.create(style_name))
        self.app.setPalette(QApplication.style().standardPalette())
        self.center()

    # Todo: Make Buttons more appealing, mark when check
    #   make button-dependencies
    def make_func_bts(self):
        self.tab_func_widget = QTabWidget()
        for func in self.pd_funcs.index:
            self.func_dict.update({func: 0})

        pre_func_dict = self.settings.value('checked_funcs')
        del_list = []
        if pre_func_dict:
            # Check for functions, which have been removed, but are still present in cache
            for k in pre_func_dict:
                if k not in self.pd_funcs.index:
                    del_list.append(k)
            if len(del_list) > 0:
                for d in del_list:
                    del pre_func_dict[d]

            # Get selected functions from last run
            for f in self.func_dict:
                if f in pre_func_dict:
                    self.func_dict[f] = pre_func_dict[f]
        # Todo: Gruppieren nach Tabs und nach Gruppen, außerdem Plot- mit Funktions-Knöpfen zusammenlegen
        tabs_grouped = self.pd_funcs.groupby('tab')
        for tab_name, group in tabs_grouped:
            group_grouped = group.groupby('group')
            tab = QScrollArea()
            child_w = QWidget()
            tab_func_layout = QGridLayout()
            r_cnt = 0
            c_cnt = 0
            r_max = 1
            for function_group, _ in group_grouped:
                group_box = QGroupBox(function_group, self)
                setattr(self, f'{function_group}_gbox', group_box)
                group_box.setCheckable(True)
                group_box.toggled.connect(self.select_func)
                group_box_layout = QVBoxLayout()

                if r_cnt >= r_max:
                    c_cnt += 1
                    r_cnt = 0
                tab_func_layout.addWidget(group_box, r_cnt, c_cnt)
                r_cnt += 1

                for function in group_grouped.groups[function_group]:
                    if pd.notna(self.pd_funcs.loc[function, 'alias']):
                        alias_name = self.pd_funcs.loc[function, 'alias']
                    else:
                        alias_name = function
                    pb = QPushButton(alias_name)
                    pb.setCheckable(True)
                    self.bt_dict[function] = pb
                    if self.func_dict[function]:
                        pb.setChecked(True)
                        self.func_dict[function] = 1
                    pb.toggled.connect(self.select_func)
                    group_box_layout.addWidget(pb)
                group_box.setLayout(group_box_layout)
            child_w.setLayout(tab_func_layout)
            tab.setWidget(child_w)
            self.tab_func_widget.addTab(tab, tab_name)
        self.general_layout.addWidget(self.tab_func_widget)

    # Todo: Do in Place update of funcs and params
    def update_func_bts(self):
        pass

    def select_func(self):
        for function in self.bt_dict:
            if self.bt_dict[function].isChecked() and self.bt_dict[function].isEnabled():
                self.func_dict[function] = 1
            else:
                self.func_dict[function] = 0

    # Todo: Replace with Model/View-Template
    def add_parameter_gui_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Add Parameter-Preset-Combobox
        sublayout = QHBoxLayout()
        p_preset_l = QLabel('Parameter-Presets: ')
        sublayout.addWidget(p_preset_l)
        self.p_preset_cmbx = QComboBox()
        self.p_preset_cmbx.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for p_preset in self.pr.parameters:
            self.p_preset_cmbx.addItem(p_preset)
        self.p_preset_cmbx.activated.connect(self.p_preset_changed)
        sublayout.addWidget(self.p_preset_cmbx)

        add_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_bt.clicked.connect(self.add_p_preset)
        sublayout.addWidget(add_bt)

        rm_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_DialogDiscardButton))
        rm_bt.clicked.connect(self.remove_p_preset)
        sublayout.addWidget(rm_bt)

        sublayout.addStretch(stretch=2)

        reset_bt = QPushButton('Reset')
        reset_bt.clicked.connect(self.reset_parameters)
        sublayout.addWidget(reset_bt)

        layout.addLayout(sublayout)

        param_scroll = QScrollArea()
        self.qall_parameters = QAllParameters(self)
        param_scroll.setWidget(self.qall_parameters)

        layout.addWidget(param_scroll)
        tab.setLayout(layout)
        self.tab_func_widget.addTab(tab, 'Parameters')

    def update_p_preset_project(self):
        self.qall_parameters.update_all_param_guis()
        self.pr.populate_directories()

    def p_preset_changed(self, idx):
        self.pr.p_preset = self.p_preset_cmbx.itemText(idx)
        self.update_p_preset_project()

    def add_p_preset(self):
        preset_name, ok = QInputDialog.getText(self, 'New Parameter-Preset',
                                               'Enter a name for a new Parameter-Preset')
        if ok:
            self.pr.p_preset = preset_name
            self.pr.load_default_parameters()
            self.settings.setValue('parameter_preset', preset_name)
            self.p_preset_cmbx.addItem(preset_name)
            self.p_preset_cmbx.setCurrentText(preset_name)
            self.update_p_preset_project()
        else:
            pass

    def remove_p_preset(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Remove Parameter-Preset')
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Select Parameter-Presets for removal'))

        plistw = QListWidget(self)
        for p_preset in [p for p in self.pr.parameters if p != 'Default']:
            item = QListWidgetItem(p_preset)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            plistw.addItem(item)
        layout.addWidget(plistw)

        def remove_selected():
            rm_list = []
            for x in range(plistw.count()):
                chk_item = plistw.item(x)
                if chk_item.checkState() == Qt.Checked:
                    rm_list.append(chk_item.text())
            # Remove the selected preset from list, dict and combobox
            for rm_p_preset in rm_list:
                plistw.takeItem(plistw.row(plistw.findItems(rm_p_preset, Qt.MatchExactly)[0]))
                self.pr.parameters.pop(rm_p_preset)
                self.p_preset_cmbx.removeItem(self.p_preset_cmbx.findText(rm_p_preset, Qt.MatchExactly))
                if rm_p_preset == self.pr.p_preset:
                    self.pr.p_preset = list(self.pr.parameters.keys())[0]
                    self.settings.setValue('parameter_preset', self.pr.p_preset)
                    self.p_preset_cmbx.setCurrentText(self.pr.p_preset)
            # Update Param-GUIs for new Parameter-Preset
            self.self.update_p_preset_project()

        bt_layout = QHBoxLayout()
        rm_bt = QPushButton('Remove')
        rm_bt.clicked.connect(remove_selected)
        bt_layout.addWidget(rm_bt)
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(dialog.close)
        bt_layout.addWidget(close_bt)
        layout.addLayout(bt_layout)

        dialog.setLayout(layout)
        dialog.open()

    def add_main_bts(self):
        self.main_bt_layout = QHBoxLayout()

        clear_bt = QPushButton('Clear', self)
        start_bt = QPushButton('Start', self)
        stop_bt = QPushButton('Quit', self)

        clear_bt.setFont(QFont('AnyStyle', 18))
        start_bt.setFont(QFont('AnyStyle', 18))
        stop_bt.setFont(QFont('AnyStyle', 18))

        self.main_bt_layout.addWidget(clear_bt)
        self.main_bt_layout.addWidget(start_bt)
        self.main_bt_layout.addWidget(stop_bt)

        clear_bt.clicked.connect(self.clear)
        start_bt.clicked.connect(self.start)
        stop_bt.clicked.connect(self.close)

        self.general_layout.addLayout(self.main_bt_layout)

    def clear(self):
        for x in self.bt_dict:
            self.bt_dict[x].setChecked(False)
            self.func_dict[x] = 0

    def start(self):
        # Save project-data before data being lost in errors
        self.pr.save_parameters()
        self.pr.save_sub_lists()
        # Save Main-Window-Settings
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('checked_funcs', self.func_dict)

        # Lists of selected functions
        self.sel_mri_funcs = [mf for mf in self.mri_funcs.index if self.func_dict[mf]]
        self.sel_file_funcs = [ff for ff in self.file_funcs.index if self.func_dict[ff]]
        self.sel_ga_funcs = [gf for gf in self.ga_funcs.index if self.func_dict[gf]]

        # Determine steps in progress for all selected subjects and functions
        self.all_prog = (len(self.pr.sel_mri_files) * len(self.sel_mri_funcs) +
                         len(self.pr.sel_files) * len(self.sel_file_funcs) +
                         len(self.sel_ga_funcs))

        self.run_dialog = RunDialog(self)
        self.run_dialog.pgbar.setMaximum(self.all_prog)
        self.run_dialog.open()

        # Redirect stdout to capture it
        sys.stdout = OutputStream()
        sys.stdout.signal.text_written.connect(self.run_dialog.update_label)

        self.fworker = FunctionWorker(self)

        self.fworker.signals.error.connect(self.run_dialog.show_errors)
        self.fworker.signals.finished.connect(self.thread_complete)
        self.fworker.signals.pgbar_n.connect(self.run_dialog.pgbar.setValue)
        self.fworker.signals.pg_which_loop.connect(self.run_dialog.populate)
        self.fworker.signals.pg_subfunc.connect(self.update_subfunc)
        self.fworker.signals.func_sig.connect(self.thread_func)

        self.threadpool.start(self.fworker)

    def update_subfunc(self, subfunc):
        self.run_dialog.mark_subfunc(subfunc)
        self.statusBar().showMessage(f'{subfunc[0]}: {subfunc[1]}')

    def thread_func(self, kwargs):
        try:
            # Todo: Solve Function-Stacking-Problem, maybe with QThread, which can accept Signals from main-thread
            func_from_def(**kwargs)
            if self.pd_funcs.loc[kwargs['func_name'], 'mayavi'] == True \
                    and self.pr.parameters[self.pr.p_preset]['show_plots'] == False:
                mlab.close(all=True)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            logging.error(f'{exctype}: {value}\n'
                          f'traceback_str')
            err = (exctype, value, traceback.format_exc(limit=-10))
            self.run_dialog.show_errors(err)
        # Send Signal to Function-Worker to continue execution after plot-function in main-thread finishes
        self.mw_signals.plot_running.emit(False)

    def thread_complete(self):
        print('Finished')
        self.run_dialog.close_bt.setEnabled(True)

    def get_toolbox_params(self):
        # Get n_jobs from settings
        self.n_jobs_sb.setValue(self.pr.parameters[self.pr.p_preset]['n_jobs'])

        # Aliases for Checkboxes in Toolbar
        chkbox_dict = {'show_plots_chkbx': 'show_plots', 'save_plots_chkbx': 'save_plots',
                       'overwrite_chkbx': 'overwrite', 'enable_cuda_chkbx': 'enable_cuda', 'shutdown_chkbx': 'shutdown'}
        for chkbox_name in chkbox_dict:
            chkbox = getattr(self, chkbox_name)

            try:
                chkbox_value = self.pr.parameters[self.pr.p_preset][chkbox_dict[chkbox_name]]
                chkbox.setChecked(chkbox_value)
            except KeyError:
                pass

    # Todo: Make Run-Function (windows&non-windows)
    def update_pipeline(self):
        command = f"pip install --upgrade git+https://github.com/marsipu/mne_pipeline_hd.git#egg=mne-pipeline-hd"
        run(command, shell=True)

        msg = QMessageBox(self)
        msg.setText('Please restart the Pipeline-Program/Close the Console')
        msg.setInformativeText('Do you want to restart?')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        msg.exec_()

        if msg.Yes:
            sys.exit()
        else:
            pass

    def update_mne(self):
        msg = QMessageBox(self)
        msg.setText('You are going to update your conda-environment called mne, if none is found, one will be created')
        msg.setInformativeText('Do you want to proceed? (May take a while, watch your console)')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        msg.exec_()

        command_upd = "curl --remote-name " \
                      "https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml; " \
                      "conda update conda; " \
                      "conda activate mne; " \
                      "conda env update --file environment.yml; pip install -r requirements.txt; " \
                      "conda install -c conda-forge pyqt=5.12"

        command_upd_win = "curl --remote-name " \
                          "https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml & " \
                          "conda update conda & " \
                          "conda activate mne & " \
                          "conda env update --file environment.yml & pip install -r requirements.txt & " \
                          "conda install -c conda-forge pyqt=5.12"

        command_new = "curl --remote-name " \
                      "https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml; " \
                      "conda update conda; " \
                      "conda env create --name mne --file environment.yml;" \
                      "conda activate mne; pip install -r requirements.txt; " \
                      "conda install -c conda-forge pyqt=5.12"

        command_new_win = "curl --remote-name " \
                          "https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml & " \
                          "conda update conda & " \
                          "conda env create --name mne_test --file environment.yml & " \
                          "conda activate mne & pip install -r requirements.txt & " \
                          "conda install -c conda-forge pyqt=5.12"

        if msg.Yes:
            result = run('conda env list', shell=True, capture_output=True, text=True)
            if 'buba' in result.stdout:
                if iswin:
                    command = command_upd_win
                else:
                    command = command_upd
                result2 = run(command, shell=True, capture_output=True, text=True)
                if result2.stderr != '':
                    print(result2.stderr)
                    if iswin:
                        command = command_new_win
                    else:
                        command = command_new
                    result3 = run(command, shell=True, capture_output=True, text=True)
                    print(result3.stdout)
                else:
                    print(result2.stdout)
            else:
                print('yeah')
                if iswin:
                    command = command_new_win
                else:
                    command = command_new
                result4 = run(command, shell=True, capture_output=True, text=True)
                print(result4.stdout)
        else:
            pass

    def quick_guide(self):
        QuickGuide(self)

    def about_qt(self):
        QMessageBox.aboutQt(self, 'About Qt')

    # Todo: Make a developers command line input to access the local variables and use quickly some script on them

    def closeEvent(self, event):

        # Save Parameters
        self.pr.save_parameters()
        self.pr.save_sub_lists()

        # Save Main-Window-Settings
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('checked_funcs', self.func_dict)
        self.settings.setValue('parameter_preset', self.pr.p_preset)

        event.accept()


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


class QAllParameters(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.main_win = main_win
        self.param_guis = {}
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        sub_layout = QVBoxLayout()
        r_cnt = 0
        for idx, parameter in self.main_win.pd_params.iterrows():
            if r_cnt > 5:
                layout.addLayout(sub_layout)
                sub_layout = QVBoxLayout()
                r_cnt = 0
            else:
                r_cnt += 1

            # Get Parameters for Gui-Call
            if not pd.isna(parameter['alias']):
                param_alias = parameter['alias']
            else:
                param_alias = idx
            if not pd.isna(parameter['gui_type']):
                gui_name = parameter['gui_type']
            else:
                gui_name = 'FuncGui'
            if not pd.isna(parameter['description']):
                hint = parameter['description']
            else:
                hint = ''
            try:
                gui_args = literal_eval(parameter['gui_args'])
            except (SyntaxError, ValueError):
                gui_args = {}

            gui_handle = getattr(parameter_widgets, gui_name)
            self.param_guis[idx] = gui_handle(self.main_win.pr, idx, param_alias, hint, **gui_args)
            sub_layout.addWidget(self.param_guis[idx])

        if 0 < r_cnt <= 5:
            layout.addLayout(sub_layout)

        self.setLayout(layout)

    def update_all_param_guis(self):
        for gui_name in self.param_guis:
            param_gui = self.param_guis[gui_name]
            param_gui.read_param()
            param_gui.set_param()

    def update_param_gui(self, gui_name):
        param_gui = self.param_guis[gui_name]
        param_gui.read_param()
        param_gui.set_param()


class CustomFSelection(QDialog):
    # Todo: Nice Gui for PKG-Selection and maybe even GDrive-Down/Upload
    pass


class RunDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        desk_geometry = self.mw.app.desktop().availableGeometry()
        self.size_ratio = 0.6
        height = desk_geometry.height() * self.size_ratio
        width = desk_geometry.width() * self.size_ratio
        self.setGeometry(0, 0, width, height)
        self.center()

        self.current_sub = None
        self.current_func = None

        self.init_ui()
        self.center()

    def init_ui(self):
        self.layout = QGridLayout()

        self.sub_listw = QListWidget()
        self.layout.addWidget(self.sub_listw, 0, 0)
        self.func_listw = QListWidget()
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
        self.console_widget.insertHtml('<b><big><center>---Terminating Pipeline...---</center></big></b><br>')
        self.console_widget.ensureCursorVisible()

    def populate(self, mode):
        if mode == 'mri':
            self.populate_listw(self.mw.pr.sel_mri_files, self.mw.sel_mri_funcs)
        elif mode == 'file':
            self.populate_listw(self.mw.pr.sel_files, self.mw.sel_file_funcs)
        elif mode == 'ga':
            self.populate_listw(self.mw.pr.grand_avg_dict, self.mw.sel_ga_funcs)
        else:
            pass

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

    def update_label(self, text):
        self.console_widget.insertPlainText(text)
        self.console_widget.ensureCursorVisible()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def show_errors(self, err):
        ErrorDialog(self, err)
        self.close_bt.setEnabled(True)
