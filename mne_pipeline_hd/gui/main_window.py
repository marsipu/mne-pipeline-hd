# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import json
import logging
import os
import re
import sys
from functools import partial
from importlib import reload, util
from os import listdir
from os.path import isdir, join
from subprocess import run

import matplotlib
import mne
import pandas as pd
import qdarkstyle
from PyQt5.QtCore import QObject, QSettings, QThreadPool, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QAction, QApplication, QComboBox, QDesktopWidget, QFileDialog,
                             QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox,
                             QPushButton, QScrollArea, QSizePolicy, QStyle, QStyleFactory, QTabWidget, QToolTip,
                             QVBoxLayout, QWidget)
from mayavi import mlab

from .dialogs import (ChooseCustomModules, CustomFunctionImport, ParametersDock, QuickGuide, RemoveProjectsDlg,
                      RunDialog, SettingsDlg)
from .gui_utils import ErrorDialog, get_exception_tuple
from .other_widgets import DataTerminal
from .parameter_widgets import BoolGui, ComboGui, IntGui
from .subject_widgets import (AddFilesDialog, AddMRIDialog, EventIDGui, SubBadsDialog, SubDictDialog,
                              SubjectDock, SubjectWizard)
from .. import basic_functions, resources
from ..basic_functions.plot import close_all
from ..pipeline_functions import iswin
from ..pipeline_functions.function_utils import (FunctionWorker, func_from_def)
from ..pipeline_functions.pipeline_utils import shutdown
from ..pipeline_functions.project import Project


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


# Todo: Controller-Class to make MainWindow-Class more light and prepare for features as Pipeline-Freezig
#  (you need an PyQt-independent system for that)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        # Initiate General-Layout
        self.app.setFont(QFont('Calibri', 10))
        QToolTip.setFont(QFont('SansSerif', 10))
        self.change_style('Fusion')
        self.dark_sheet = qdarkstyle.load_stylesheet_pyqt5()
        self.setWindowTitle('MNE-Pipeline HD')

        self.setCentralWidget(QWidget(self))
        self.general_layout = QGridLayout()
        self.centralWidget().setLayout(self.general_layout)

        # Set geometry to ratio of screen-geometry
        width, height = self.get_ratio_geometry(0.9)
        self.setGeometry(0, 0, width, height)

        # Initialize QThreadpool for creating separate Threads apart from GUI-Event-Loop later
        self.threadpool = QThreadPool()
        print(f'Multithreading with maximum {self.threadpool.maxThreadCount()} threads')

        # Initiate attributes for Main-Window
        self.home_path = ''
        self.projects_path = ''
        self.current_project = ''
        self.subjects_dir = ''
        self.custom_pkg_path = ''
        self.mw_signals = MainWinSignals()
        self.module_err_dlg = None
        self.bt_dict = dict()
        self.all_modules = {'basic': {},
                            'custom': {}}
        self.subject = None
        self.available_image_formats = {'.png': 'PNG', '.jpg': 'JPEG', '.tiff': 'TIFF'}

        # Load QSettings (which are stored in the OS)
        # qsettings=<everything, that's OS-dependent>
        self.qsettings = QSettings()
        # Get the Home-Path (OS-dependent)
        self.get_home_path()
        # Load settings (which are stored as .json-file in home_path)
        # settings=<everything, that's OS-independent>
        self.settings = {}
        self.load_settings()
        # Get projects and current_project (need settings for this, thus after self.load_settings()
        self.get_projects()

        # Load CSV-Files for Functions & Parameters
        # Lists of functions separated in execution groups (mri_subject, subject, grand-average)
        self.pd_funcs = pd.read_csv(join(resources.__path__[0], 'functions.csv'), sep=';', index_col=0)
        # Pandas-DataFrame for Parameter-Pipeline-Data (parameter-values are stored in main_win.pr.parameters)
        self.pd_params = pd.read_csv(join(resources.__path__[0], 'parameters.csv'), sep=';', index_col=0)

        # Set a dramaturgically order for the groups (which applies for func_groups and parameter_groups)
        self.group_order = {'General': 0,
                            'Raw': 1,
                            'Preprocessing': 2,
                            'Events': 3,
                            'Epochs': 3,
                            'Evoked': 3,
                            'Time-Frequency': 4,
                            'Forward': 5,
                            'Inverse': 6,
                            'Grand-Average': 7}

        # Import the basic- and custom-function-modules
        self.import_custom_modules()
        # Todo: Gruppen machen Probleme mit CustomFunctions!!!
        # Todo: verbessern, um Klarheit zu schaffen bei Unterteilung in Gruppen (über einzelne Module?)
        self.mri_funcs = self.pd_funcs[(self.pd_funcs['group'] == 'MRI-Preprocessing')
                                       & (self.pd_funcs['subject_loop'] == True)]
        self.file_funcs = self.pd_funcs[(self.pd_funcs['group'] != 'MRI-Preprocessing')
                                        & (self.pd_funcs['subject_loop'] == True)]
        self.ga_funcs = self.pd_funcs[(self.pd_funcs['subject_loop'] == False)
                                      & (self.pd_funcs['func_args'].str.contains('ga_group'))]
        self.other_funcs = self.pd_funcs[(self.pd_funcs['subject_loop'] == False)
                                         & ~ (self.pd_funcs['func_args'].str.contains('ga_group'))]

        # Call project-class
        self.pr = Project(self, self.current_project)

        # Set logging
        logging.basicConfig(filename=join(self.pr.pscripts_path, '_pipeline.log'), filemode='w')
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

        # Needs restart, otherwise error, when setting later
        if self.get_setting('mne_backend') == 'pyvista':
            mne.viz.set_3d_backend('pyvista')
        else:
            mne.viz.set_3d_backend('mayavi')

        # Call window-methods
        self.init_menu()
        self.init_main_widget()
        self.init_toolbar()
        self.add_dock_windows()

    def get_home_path(self):
        # Get home_path
        hp = self.qsettings.value('home_path')
        checking_home_path = True
        while checking_home_path:
            if hp is None or hp == '':
                hp = QFileDialog.getExistingDirectory(self, 'Select a folder to store your Pipeline-Projects')
            elif not isdir(hp):
                hp = QFileDialog.getExistingDirectory(self, f'{hp} not found!'
                                                            f'Select a folder to store your Pipeline-Projects')
            # Check, if path is writable
            elif not os.access(hp, os.W_OK):
                hp = QFileDialog.getExistingDirectory(self, f'{hp} not writable!'
                                                            f'Select a folder to store your Pipeline-Projects')
            if hp == '':
                answer = QMessageBox.question(self, 'Cancel Start?',
                                               'You can\'t start without this step, '
                                               'do you want to cancel the start?')
                if answer == QMessageBox.Yes:
                    raise RuntimeError('User canceled start')
            # Check, if the new selected Path from the Dialog is writable
            elif not os.access(hp, os.W_OK):
                pass
            else:
                self.home_path = str(hp)
                self.qsettings.setValue('home_path', self.home_path)
                self.make_base_paths()
                print(f'Home-Path: {self.home_path}')
                checking_home_path = False

    def make_base_paths(self):
        self.projects_path = join(self.home_path, 'projects')
        self.subjects_dir = join(self.home_path, 'freesurfer')
        mne.utils.set_config("SUBJECTS_DIR", self.subjects_dir, set_env=True)
        self.custom_pkg_path = join(self.home_path, 'custom_functions')
        for path in [self.projects_path, self.subjects_dir, self.custom_pkg_path]:
            if not isdir(path):
                os.mkdir(path)

    def get_projects(self):
        # Get current_project
        self.current_project = self.get_setting('current_project')
        self.projects = [p for p in listdir(self.projects_path) if isdir(join(self.projects_path, p, 'data'))]
        if len(self.projects) == 0:
            checking_projects = True
            while checking_projects:
                self.current_project, ok = QInputDialog.getText(self, 'Project-Selection',
                                                                f'No projects in {self.home_path} found\n'
                                                                'Enter a project-name for your first project')
                if ok and self.current_project:
                    self.projects.append(self.current_project)
                    self.settings['current_project'] = self.current_project
                    checking_projects = False
                else:
                    msg_box = QMessageBox.question(self, 'Cancel Start?',
                                                   'You can\'t start without this step, '
                                                   'do you want to cancel the start?')
                    answer = msg_box.exec()
                    if answer == QMessageBox.Yes:
                        raise RuntimeError('User canceled start')

        elif self.current_project is None or self.current_project not in self.projects:
            self.current_project = self.projects[0]
            self.settings['current_project'] = self.current_project

        print(f'Projects-found: {self.projects}')
        print(f'Selected-Project: {self.current_project}')

    def project_updated(self):
        # Set new logging
        logging.basicConfig(filename=join(self.pr.pscripts_path, '_pipeline.log'), filemode='w')
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

        # Update Subject-Lists
        self.subject_dock.update_subjects_list()
        self.subject_dock.update_mri_subjects_list()
        self.subject_dock.ga_widget.update_treew()

        # Update Parameters
        self.parameters_dock.update_all_param_guis()
        self.parameters_dock.update_ppreset_cmbx()

        # Update Funciton-Selection
        self.update_selected_funcs()
        # Update Project-Box
        self.update_project_box()
        # Update Statusbar
        self.statusBar().showMessage(f'Home-Path: {self.home_path}, '
                                     f'Project: {self.current_project}, '
                                     f'Parameter-Preset: {self.pr.p_preset}')

    def change_home_path(self):
        # First save the former projects-data
        self.save_main()

        new_home_path = QFileDialog.getExistingDirectory(self,
                                                         'Change your Home-Path (top-level folder of Pipeline-Data)')
        if new_home_path != '':
            self.home_path = new_home_path
            self.qsettings.setValue('home_path', self.home_path)
            self.load_settings()
            self.make_base_paths()
            self.get_projects()
            self.import_custom_modules()
            self.update_func_bts()
            self.parameters_dock.update_parameters_widget()
            # self.update_param_gui_tab()
            self.statusBar().showMessage(f'Home-Path: {self.home_path}, '
                                         f'Project: {self.current_project}, '
                                         f'Parameter-Preset: {self.pr.p_preset}')

            # Create new Project or load existing one
            self.pr = Project(self, self.current_project)
            self.project_updated()

    def add_project(self):
        # First save the former projects-data
        self.save_main()

        project, ok = QInputDialog.getText(self, 'New Project',
                                           'Enter a name for a new project')
        if ok:
            self.current_project = project
            self.settings['current_project'] = self.current_project
            self.projects.append(project)

            self.project_box.addItem(project)
            self.project_box.setCurrentText(project)

            # Create new Project
            self.pr = Project(self, self.current_project)
            self.project_updated()

    def remove_project(self):
        # First save the former projects-data
        self.save_main()
        RemoveProjectsDlg(self)

    def project_tools(self):
        self.project_box = QComboBox()
        self.project_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for project in self.projects:
            self.project_box.addItem(project)
        self.project_box.setCurrentText(self.current_project)
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
        self.save_main()

        self.current_project = self.project_box.itemText(idx)

        # Change project
        self.pr = Project(self, self.current_project)
        self.project_updated()

    def update_project_box(self):
        self.project_box.clear()
        for project in self.projects:
            self.project_box.addItem(project)
        if self.current_project in self.projects:
            self.project_box.setCurrentText(self.current_project)
        else:
            self.project_box.setCurrentText(self.projects[0])

    def load_default_settings(self):
        with open(join(resources.__path__[0], 'default_settings.json'), 'r') as file:
            self.default_settings = json.load(file)

    def load_settings(self):
        self.load_default_settings()
        try:
            with open(join(self.home_path, 'mne_pipeline_hd-settings.json'), 'r') as file:
                self.settings = json.load(file)
            # Account for settings, which were not saved but exist in default_settings
            for setting in [s for s in self.default_settings if s not in self.settings]:
                self.settings[setting] = self.default_settings[setting]
        except FileNotFoundError:
            self.settings = self.default_settings

    def save_settings(self):
        with open(join(self.home_path, 'mne_pipeline_hd-settings.json'), 'w') as file:
            json.dump(self.settings, file, indent=4)

    def get_setting(self, setting):
        try:
            value = self.settings[setting]
        except KeyError:
            value = self.default_settings[setting]

        return value

    def import_custom_modules(self):
        """
        Load all modules in basic_functions and custom_functions
        """
        # Start with empty dicts, especiall when re-importing from GUI
        self.all_modules = {'basic': {},
                            'custom': {}}

        # Lists of functions separated in execution groups (mri_subject, subject, grand-average)
        self.pd_funcs = pd.read_csv(join(resources.__path__[0], 'functions.csv'), sep=';', index_col=0)
        # Pandas-DataFrame for Parameter-Pipeline-Data (parameter-values are stored in main_win.pr.parameters)
        self.pd_params = pd.read_csv(join(resources.__path__[0], 'parameters.csv'), sep=';', index_col=0)

        # Load basic-modules
        basic_functions_list = [x for x in dir(basic_functions) if '__' not in x]
        for module_name in basic_functions_list:
            self.all_modules['basic'][module_name] = getattr(basic_functions, module_name)
        # Load custom_modules
        pd_functions_pattern = r'.*_functions\.csv'
        pd_parameters_pattern = r'.*_parameters\.csv'
        custom_module_pattern = r'(.+)(\.py)$'
        for directory in [d for d in os.scandir(self.custom_pkg_path) if not d.name.startswith('.')]:
            pkg_name = directory.name
            pkg_path = directory.path
            file_dict = {'functions': None, 'parameters': None, 'module': None}
            for file_name in [f for f in listdir(pkg_path) if not f.startswith(('.', '_'))]:
                functions_match = re.match(pd_functions_pattern, file_name)
                parameters_match = re.match(pd_parameters_pattern, file_name)
                custom_module_match = re.match(custom_module_pattern, file_name)
                if functions_match:
                    file_dict['functions'] = join(pkg_path, file_name)
                elif parameters_match:
                    file_dict['parameters'] = join(pkg_path, file_name)
                elif custom_module_match and custom_module_match.group(1) != '__init__':
                    file_dict['module'] = custom_module_match

            # Check, that there is a whole set for a custom-module (module-file, functions, parameters)
            if all([value is not None for value in file_dict.values()]):
                functions_path = file_dict['functions']
                parameters_path = file_dict['parameters']
                module_name = file_dict['module'].group(1)
                module_file_name = file_dict['module'].group()

                spec = util.spec_from_file_location(module_name, join(pkg_path, module_file_name))
                module = util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except:
                    exc_tuple = get_exception_tuple()
                    self.module_err_dlg = ErrorDialog(exc_tuple,
                                                      self, title=f'Error in import of custom-module: {module_name}')
                else:
                    # Add module to sys.modules
                    sys.modules[module_name] = module
                    # Add Module to dictionary
                    self.all_modules['custom'][module_name] = (module, spec)

                    try:
                        read_pd_funcs = pd.read_csv(functions_path, sep=';', index_col=0)
                        read_pd_params = pd.read_csv(parameters_path, sep=';', index_col=0)
                    except:
                        exc_tuple = get_exception_tuple()
                        self.module_err_dlg = ErrorDialog(exc_tuple, self,
                                                          title=f'Error in import of .csv-file: {functions_path}')
                    else:
                        for idx in [ix for ix in read_pd_funcs.index if ix not in self.pd_funcs.index]:
                            self.pd_funcs = self.pd_funcs.append(read_pd_funcs.loc[idx])
                        for idx in [ix for ix in read_pd_params.index if ix not in self.pd_params.index]:
                            self.pd_params = self.pd_params.append(read_pd_params.loc[idx])

            else:
                text = f'Files for import of {pkg_name} are missing: ' \
                       f'{[key for key in file_dict if file_dict[key] is None]}'
                QMessageBox.warning(self, 'Import-Problem', text)

    def reload_basic_modules(self):
        for module_name in self.all_modules['basic']:
            reload(self.all_modules['basic'][module_name])

    def reload_custom_modules(self):
        for module_name in self.all_modules['custom']:
            module = self.all_modules['custom'][module_name][0]
            spec = self.all_modules['custom'][module_name][1]
            spec.loader.exec_module(module)
            sys.modules[module_name] = module

    def init_menu(self):
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
        input_menu.addAction('Assign Event-IDs', partial(EventIDGui, self))
        input_menu.addSeparator()
        input_menu.addAction('MRI-Coregistration', mne.gui.coregistration)

        # Custom-Functions
        self.customf_menu = self.menuBar().addMenu('&Custom Functions')
        self.aadd_customf = self.customf_menu.addAction('&Add custom Functions', self.add_customf)

        self.achoose_customf = self.customf_menu.addAction('&Choose Custom-Modules', self.choose_customf)

        self.areload_custom_modules = QAction('Reload Custom-Modules')
        self.areload_custom_modules.triggered.connect(self.reload_custom_modules)
        self.customf_menu.addAction(self.areload_custom_modules)

        # Tools
        self.tool_menu = self.menuBar().addMenu('&Tools')
        self.asub_terminal = self.tool_menu.addAction('&Data-Terminal', self.show_terminal)

        # View
        self.view_menu = self.menuBar().addMenu('&View')

        self.adark_mode = self.view_menu.addAction('&Dark-Mode', self.dark_mode)
        self.adark_mode.setCheckable(True)
        if self.get_setting('dark_mode') == 'true':
            self.adark_mode.setChecked(True)
            self.dark_mode()
        else:
            self.adark_mode.setChecked(False)
        self.view_menu.addAction('&Full-Screen', self.full_screen).setCheckable(True)

        # Settings
        self.settings_menu = self.menuBar().addMenu('&Settings')

        self.settings_menu.addAction('&Open Settings', partial(SettingsDlg, self))
        self.settings_menu.addAction('&Change Home-Path', self.change_home_path)

        self.areload_basic_modules = QAction('Reload Basic-Modules')
        self.areload_basic_modules.triggered.connect(self.reload_basic_modules)
        self.settings_menu.addAction(self.areload_basic_modules)

        # About
        about_menu = self.menuBar().addMenu('About')
        # about_menu.addAction('Update Pipeline', self.update_pipeline)
        # about_menu.addAction('Update MNE-Python', self.update_mne)
        about_menu.addAction('Quick-Guide', self.quick_guide)
        about_menu.addAction('About', self.about)
        about_menu.addAction('About QT', self.app.aboutQt)

    def init_toolbar(self):
        self.toolbar = self.addToolBar('Tools')
        # Add Project-Tools
        self.project_tools()
        self.toolbar.addSeparator()

        self.toolbar.addWidget(IntGui(self.qsettings, 'n_jobs', min_val=-1, special_value_text='Auto',
                                      hint='Set to the amount of cores of your machine '
                                           'you want to use for multiprocessing', default=-1))
        self.toolbar.addWidget(BoolGui(self.settings, 'show_plots', param_alias='Show Plots',
                                       hint='Do you want to show plots?\n'
                                            '(or just save them without showing, then just check "Save Plots")',
                                       default=True))
        self.toolbar.addWidget(BoolGui(self.settings, 'save_plots', param_alias='Save Plots',
                                       hint='Do you want to save the plots made to a file?', default=True))
        self.toolbar.addWidget(BoolGui(self.qsettings, 'enable_cuda', param_alias='Enable CUDA',
                                       hint='Do you want to enable CUDA? (system has to be setup for cuda)',
                                       default=False))
        self.toolbar.addWidget(BoolGui(self.settings, 'shutdown', param_alias='Shutdown',
                                       hint='Do you want to shut your system down after execution of all subjects?'))
        self.toolbar.addWidget(IntGui(self.settings, 'dpi', min_val=0, max_val=10000,
                                      hint='Set dpi for saved plots', default=300))
        self.toolbar.addWidget(ComboGui(self.settings, 'img_format', self.available_image_formats,
                                        param_alias='Image-Format', hint='Choose the image format for plots',
                                        default='.png'))
        self.toolbar.addWidget(ComboGui(self.settings, 'mne_backend', {'mayavi': 'Mayavi', 'pyvista': 'PyVista'},
                                        param_alias='MNE-Backend',
                                        hint='Choose the backend for plotting in 3D (needs Restart)',
                                        default='pyvista'))
        close_all_bt = QPushButton('Close All Plots')
        close_all_bt.pressed.connect(close_all)
        self.toolbar.addWidget(close_all_bt)

    def init_main_widget(self):
        # Add Function-Buttons
        self.add_func_bts()

        # Add Main-Buttons
        clear_bt = QPushButton('Clear')
        start_bt = QPushButton('Start')
        stop_bt = QPushButton('Quit')

        clear_bt.setFont(QFont('AnyStyle', 18))
        start_bt.setFont(QFont('AnyStyle', 18))
        stop_bt.setFont(QFont('AnyStyle', 18))

        clear_bt.clicked.connect(self.clear)
        start_bt.clicked.connect(self.start)
        stop_bt.clicked.connect(self.close)

        self.general_layout.addWidget(clear_bt, 1, 0)
        self.general_layout.addWidget(start_bt, 1, 1)
        self.general_layout.addWidget(stop_bt, 1, 2)

    # Todo: Make Buttons more appealing, mark when check
    #   make button-dependencies
    def add_func_bts(self):
        self.tab_func_widget = QTabWidget()
        # Drop custom-modules, which aren't selected
        cleaned_pd_funcs = self.pd_funcs.loc[self.pd_funcs['module'].isin(self.get_setting('selected_modules'))].copy()

        # Assert, that cleaned_pd_funcs is not empty (possible, when deselecting all modules)
        if len(cleaned_pd_funcs) != 0:
            for func_name in cleaned_pd_funcs.index:
                group_name = cleaned_pd_funcs.loc[func_name, 'group']
                if group_name in self.group_order:
                    cleaned_pd_funcs.loc[func_name, 'group_idx'] = self.group_order[group_name]
                else:
                    cleaned_pd_funcs.loc[func_name, 'group_idx'] = 100

            # Sort values by group_idx for dramaturgically order
            cleaned_pd_funcs.sort_values(by='group_idx', inplace=True)

            # Remove functions from sel_functions, which are not present in cleaned_pd_funcs
            for f_rm in [f for f in self.pr.sel_functions if f not in cleaned_pd_funcs.index]:
                self.pr.sel_functions.pop(f_rm)

            # Add functions from cleaned_pd_funcs, which are not present in sel_functions
            for f_add in [f for f in cleaned_pd_funcs.index if f not in self.pr.sel_functions]:
                self.pr.sel_functions[f_add] = 0

            tabs_grouped = cleaned_pd_funcs.groupby('tab')
            # Add tabs
            for tab_name, group in tabs_grouped:
                group_grouped = group.groupby('group', sort=False)
                tab = QScrollArea()
                child_w = QWidget()
                tab_v_layout = QVBoxLayout()
                tab_h_layout = QHBoxLayout()
                h_size = 0
                max_h_size = int(self.app.desktop().availableGeometry().width() / 3)
                # Add groupbox for each group
                for function_group, _ in group_grouped:
                    group_box = QGroupBox(function_group, self)
                    setattr(self, f'{function_group}_gbox', group_box)
                    group_box.setCheckable(True)
                    group_box.toggled.connect(self.func_group_toggled)
                    group_box_layout = QVBoxLayout()
                    # Add button for each function
                    for function in group_grouped.groups[function_group]:
                        if pd.notna(cleaned_pd_funcs.loc[function, 'alias']):
                            alias_name = cleaned_pd_funcs.loc[function, 'alias']
                        else:
                            alias_name = function
                        pb = QPushButton(alias_name)
                        pb.setCheckable(True)
                        self.bt_dict[function] = pb
                        if self.pr.sel_functions[function]:
                            pb.setChecked(True)
                        pb.clicked.connect(partial(self.func_selected, function))
                        group_box_layout.addWidget(pb)

                    group_box.setLayout(group_box_layout)
                    group_box.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
                    tab_h_layout.addWidget(group_box)
                    h_size += group_box.sizeHint().width()
                    if h_size > max_h_size:
                        tab_v_layout.addLayout(tab_h_layout)
                        h_size = 0
                        tab_h_layout = QHBoxLayout()

                if not tab_h_layout.isEmpty():
                    tab_v_layout.addLayout(tab_h_layout)

                child_w.setLayout(tab_v_layout)
                tab.setWidget(child_w)
                self.tab_func_widget.addTab(tab, tab_name)

        self.general_layout.addWidget(self.tab_func_widget, 0, 0, 1, 3)

    def update_func_bts(self):
        self.general_layout.removeWidget(self.tab_func_widget)
        self.tab_func_widget.close()
        del self.tab_func_widget
        self.add_func_bts()

    def func_selected(self, function):
        if self.bt_dict[function].isChecked():
            self.pr.sel_functions[function] = 1
        else:
            self.pr.sel_functions[function] = 0

    def func_group_toggled(self):
        for function in self.bt_dict:
            if self.bt_dict[function].isChecked() and self.bt_dict[function].isEnabled():
                self.pr.sel_functions[function] = 1
            else:
                self.pr.sel_functions[function] = 0

    def update_selected_funcs(self):
        for function in self.bt_dict:
            self.bt_dict[function].setChecked(False)
            if function in self.pr.sel_functions:
                if self.pr.sel_functions[function]:
                    self.bt_dict[function].setChecked(True)

    def add_dock_windows(self):
        self.subject_dock = SubjectDock(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.subject_dock)
        self.view_menu.addAction(self.subject_dock.toggleViewAction())

        self.parameters_dock = ParametersDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.parameters_dock)
        self.view_menu.addAction(self.parameters_dock.toggleViewAction())

    def add_customf(self):
        self.cf_import = CustomFunctionImport(self)

    def choose_customf(self):
        self.cf_choose = ChooseCustomModules(self)

    def get_ratio_geometry(self, size_ratio):
        self.desk_geometry = self.app.desktop().availableGeometry()
        height = int(self.desk_geometry.height() * size_ratio)
        width = int(self.desk_geometry.width() * size_ratio)

        return width, height

    def dark_mode(self):
        if self.adark_mode.isChecked():
            self.app.setStyleSheet(self.dark_sheet)
            self.settings['dark_mode'] = True
        else:
            self.app.setStyleSheet('')
            self.settings['dark_mode'] = False

    def full_screen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def show_terminal(self):
        DataTerminal(self)

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

    def clear(self):
        for x in self.bt_dict:
            self.bt_dict[x].setChecked(False)
            self.pr.sel_functions[x] = 0

    def start(self):

        # Save Main-Window-Settings and project before possible Errors happen
        self.save_main()

        # Lists of selected functions
        self.sel_mri_funcs = [mf for mf in self.mri_funcs.index if self.pr.sel_functions[mf]]
        self.sel_file_funcs = [ff for ff in self.file_funcs.index if self.pr.sel_functions[ff]]
        self.sel_ga_funcs = [gf for gf in self.ga_funcs.index if self.pr.sel_functions[gf]]
        self.sel_other_funcs = [of for of in self.other_funcs.index if self.pr.sel_functions[of]]

        # Determine steps in progress for all selected subjects and functions
        self.all_prog = (len(self.pr.sel_mri_files) * len(self.sel_mri_funcs) +
                         len(self.pr.sel_files) * len(self.sel_file_funcs) +
                         len(self.pr.sel_ga_groups) * len(self.sel_ga_funcs) +
                         len(self.sel_other_funcs))

        self.run_dialog = RunDialog(self)
        self.run_dialog.pgbar.setMaximum(self.all_prog)
        self.run_dialog.open()

        sys.stdout.signal.text_written.connect(self.run_dialog.add_text)
        sys.stderr.signal.text_written.connect(self.run_dialog.add_text)
        # Handle Console-Ou
        sys.stderr.signal.text_updated.connect(self.run_dialog.progress_text)

        # Set non-interactive backend for plots to be runnable in QThread This can be a problem with older versions
        # from matplotlib, as you can set the backend only once there. This could be solved with importing all the
        # function-modules here, but you had to import them for each run then
        if self.get_setting('show_plots'):
            matplotlib.use('Qt5Agg')
        else:
            matplotlib.use('agg')

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
            func_from_def(**kwargs)
            if self.pd_funcs.loc[kwargs['func_name'], 'mayavi'] and not self.get_setting('show_plots'):
                mlab.close(all=True)
        except:
            exc_tuple = get_exception_tuple()
            self.run_dialog.show_errors(exc_tuple)
        # Send Signal to Function-Worker to continue execution after plot-function in main-thread finishes
        self.mw_signals.plot_running.emit(False)

    def thread_complete(self):
        print('Finished')
        self.run_dialog.pgbar.setValue(self.all_prog)
        self.run_dialog.close_bt.setEnabled(True)
        if not self.get_setting('show_plots'):
            close_all()
        if self.get_setting('shutdown'):
            self.save_main()
            shutdown()

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

    def about(self):

        with open(join(resources.__path__[0], 'license.txt'), 'r') as file:
            license_text = file.read()
        license_text = license_text.replace('\n', '<br>')
        text = '<h1>MNE-Pipeline HD</h1>' \
               '<b>A Pipeline-GUI for MNE-Python</b><br>' \
               '(originally developed for MEG-Lab Heidelberg)<br>' \
               '<i>Development was initially inspired by: ' \
               '<a href=https://doi.org/10.3389/fnins.2018.00006>Andersen L.M. 2018</a></i><br>' \
               '<br>' \
               'As for now, this program is still in alpha-state, so some features may not work as expected. ' \
               'Be sure to check all the parameters for each step to be correctly adjusted to your needs.<br>' \
               '<br>' \
               '<b>Developed by:</b><br>' \
               'Martin Schulz (medical student, Heidelberg)<br>' \
               '<br>' \
               '<b>Supported by:</b><br>' \
               'PD Dr. André Rupp, Kristin Mierisch<br>' \
               '<br>' \
               '<b>Licensed under:</b><br>' \
               + license_text

        msgbox = QMessageBox(self)
        msgbox.setWindowTitle('about')
        msgbox.setStyleSheet('QLabel{min-width: 600px; max-height: 700px}')
        msgbox.setText(text)
        msgbox.open()

    def save_main(self):
        # Save Parameters
        self.pr.save_parameters()
        self.pr.save_file_parameters()
        self.pr.save_sub_lists()

        self.settings['current_project'] = self.current_project
        self.save_settings()

    def closeEvent(self, event):
        self.save_main()
        event.accept()
