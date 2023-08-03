# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import sys
from functools import partial

import mne
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mne_pipeline_hd import _object_refs
from mne_pipeline_hd.functions.plot import close_all
from mne_pipeline_hd.gui.dialogs import (
    QuickGuide,
    RawInfo,
    RemoveProjectsDlg,
    SysInfoMsg,
    AboutDialog,
    CopyParamsDialog,
)
from mne_pipeline_hd.gui.education_widgets import EducationEditor, EducationTour
from mne_pipeline_hd.gui.function_widgets import (
    AddKwargs,
    ChooseCustomModules,
    CustomFunctionImport,
    RunDialog,
)
from mne_pipeline_hd.gui.gui_utils import (
    QProcessDialog,
    WorkerDialog,
    center,
    set_ratio_geometry,
    get_std_icon,
    get_user_input_string,
)
from mne_pipeline_hd.gui.loading_widgets import (
    AddFilesDialog,
    AddMRIDialog,
    CopyTrans,
    EventIDGui,
    FileDictDialog,
    FileDock,
    FileManagment,
    ICASelect,
    ReloadRaw,
    SubBadsDialog,
    SubjectWizard,
    ExportDialog,
)
from mne_pipeline_hd.gui.parameter_widgets import (
    BoolGui,
    IntGui,
    ParametersDock,
    SettingsDlg,
)
from mne_pipeline_hd.gui.plot_widgets import PlotViewSelection
from mne_pipeline_hd.gui.tools import DataTerminal
from mne_pipeline_hd.pipeline.controller import Controller
from mne_pipeline_hd.pipeline.pipeline_utils import (
    restart_program,
    ismac,
    QS,
    _run_from_script,
    iswin,
)


class MainWindow(QMainWindow):
    # Define Main-Window-Signals to send into QThread
    # to control function execution
    cancel_functions = pyqtSignal(bool)
    plot_running = pyqtSignal(bool)

    def __init__(self, controller):
        super().__init__()
        _object_refs["main_window"] = self
        self.setWindowTitle("MNE-Pipeline HD")

        # Set QThread as default (ToDo: MP)
        QS().setValue("use_qthread", True)

        # Initiate attributes for Main-Window
        self.ct = controller
        self.pr = controller.pr
        self.edu_tour = None
        self.bt_dict = dict()
        # For functions, which should or should not
        # be called durin initialization
        self.first_init = True
        # True, if Pipeline is running (to avoid parallel starts of RunDialog)
        self.pipeline_running = False
        # For the closeEvent to avoid showing the MessageBox when restarting
        self.restarting = False

        # Set geometry to ratio of screen-geometry
        # (before adding func-buttons to allow adjustment to size)
        set_ratio_geometry(0.9, self)

        # Call window-methods
        self.init_menu()
        self.init_toolbar()
        self.init_docks()
        self.init_main_widget()
        self.init_edu()

        center(self)

        self.first_init = False

    def update_project_ui(self):
        # Redraw function-buttons and parameter-widgets
        self.redraw_func_and_param()
        # Update Subject-Lists
        self.file_dock.update_dock()
        # Update Project-Box
        self.update_project_box()
        # Update Statusbar
        self.statusBar().showMessage(
            f"Home-Path: {self.ct.home_path}, " f"Project: {self.pr.name}"
        )

    def change_home_path(self):
        # First save the former projects-data
        WorkerDialog(self, self.ct.save, blocking=True)

        new_home_path = QFileDialog.getExistingDirectory(
            self, "Change your Home-Path (top-level folder of Pipeline-Data)"
        )
        if new_home_path != "":
            try:
                new_controller = Controller(new_home_path)
            except RuntimeError as err:
                QMessageBox.critical(self, "Error with selected Home-Path", str(err))
            else:
                if new_controller.pr is None:
                    new_project = get_user_input_string(
                        "There is no project in this Home-Path,"
                        " please enter a name for a new project:",
                        "Add Project!",
                        force=True,
                    )
                    self.pr = new_controller.change_project(new_project)

                self.ct = new_controller
                welcome_window = _object_refs["welcome_window"]
                if welcome_window is not None:
                    welcome_window.ct = new_controller
                self.statusBar().showMessage(
                    f"Home-Path: {self.ct.home_path}," f" Project: {self.pr.name}"
                )
                self.update_project_ui()

    def add_project(self):
        # First save the former projects-data
        WorkerDialog(self, self.pr.save, blocking=True)

        new_project = get_user_input_string(
            "Enter a name for a new project", "Add Project"
        )
        if new_project is not None:
            self.pr = self.ct.change_project(new_project)
            self.update_project_ui()

    def remove_project(self):
        # First save the former projects-data
        WorkerDialog(self, self.pr.save, blocking=True)

        RemoveProjectsDlg(self, self.ct)

    def project_changed(self, idx):
        # First save the former projects-data
        WorkerDialog(self, self.pr.save, blocking=True)

        # Get selected Project
        project = self.project_box.itemText(idx)

        # Change project
        self.pr = self.ct.change_project(project)

        self.update_project_ui()

    def pr_clean_fp(self):
        WorkerDialog(
            self,
            self.pr.clean_file_parameters,
            show_buttons=True,
            show_console=True,
            close_directly=False,
            title="Cleaning File-Parameters",
        )

    def pr_clean_pf(self):
        WorkerDialog(
            self,
            self.pr.clean_plot_files,
            show_buttons=True,
            show_console=True,
            close_directly=False,
            title="Cleaning Plot-Files",
        )

    def pr_copy_parameters(self):
        CopyParamsDialog(self)

    def update_project_box(self):
        self.project_box.clear()
        self.project_box.addItems(self.ct.projects)
        if self.pr is not None:
            self.project_box.setCurrentText(self.pr.name)

    def init_edu(self):
        if (
            QS().value("education")
            and self.ct.edu_program
            and len(self.ct.edu_program["tour_list"]) > 0
        ):
            self.edu_tour = EducationTour(self, self.ct.edu_program)

    def init_menu(self):
        # & in front of text-string creates automatically a shortcut
        # with Alt + <letter after &>
        # Input
        import_menu = self.menuBar().addMenu("&Import")

        aaddfiles = QAction("Add MEEG", parent=self)
        aaddfiles.setShortcut("Ctrl+M")
        aaddfiles.setStatusTip("Add your MEG-Files here")
        aaddfiles.triggered.connect(partial(AddFilesDialog, self))
        import_menu.addAction(aaddfiles)

        import_menu.addAction("Add Sample-Dataset", self.add_sample_dataset)
        import_menu.addAction("Add Test-Dataset", self.add_test_dataset)
        import_menu.addAction("Reload raw", partial(ReloadRaw, self))

        import_menu.addSeparator()

        aaddmri = QAction("Add Freesurfer-MRI", self)
        aaddmri.setShortcut("Ctrl+F")
        aaddmri.setStatusTip("Add your Freesurfer-Segmentations here")
        aaddmri.triggered.connect(partial(AddMRIDialog, self))
        import_menu.addAction(aaddmri)

        import_menu.addAction("Add fsaverage", self.add_fsaverage)

        import_menu.addSeparator()

        import_menu.addAction("Show Info", partial(RawInfo, self))
        import_menu.addAction("File-Management", partial(FileManagment, self))

        export_menu = self.menuBar().addMenu("&Export")
        export_menu.addAction("Export MEEG", partial(ExportDialog, self))

        prep_menu = self.menuBar().addMenu("&Preparation")
        prep_menu.addAction("Subject-Wizard", partial(SubjectWizard, self))

        prep_menu.addSeparator()

        prep_menu.addAction(
            "Assign MEEG --> Freesurfer-MRI", partial(FileDictDialog, self, "mri")
        )
        prep_menu.addAction(
            "Assign MEEG --> Empty-Room", partial(FileDictDialog, self, "erm")
        )
        prep_menu.addAction(
            "Assign Bad-Channels --> MEEG", partial(SubBadsDialog, self)
        )
        prep_menu.addAction("Assign Event-IDs --> MEEG", partial(EventIDGui, self))
        prep_menu.addAction("Select ICA-Components", partial(ICASelect, self))

        prep_menu.addSeparator()

        prep_menu.addAction("MRI-Coregistration", mne.gui.coregistration)
        prep_menu.addAction("Copy Transformation", partial(CopyTrans, self))

        prep_menu.addSeparator()

        # Project
        project_menu = self.menuBar().addMenu("&Project")
        project_menu.addAction("&Clean File-Parameters", self.pr_clean_fp)
        project_menu.addAction("&Clean Plot-Files", self.pr_clean_pf)
        project_menu.addAction(
            "&Copy Parameters between Projects", self.pr_copy_parameters
        )

        # Custom-Functions
        func_menu = self.menuBar().addMenu("&Functions")
        func_menu.addAction("&Import Custom", partial(CustomFunctionImport, self))

        func_menu.addAction(
            "&Choose Custom-Modules", partial(ChooseCustomModules, self)
        )

        func_menu.addAction("&Reload Modules", self.ct.reload_modules)
        func_menu.addSeparator()
        func_menu.addAction("Additional Keyword-Arguments", partial(AddKwargs, self))

        # Education
        education_menu = self.menuBar().addMenu("&Education")
        if self.ct.edu_program is None:
            education_menu.addAction(
                "&Education-Editor", partial(EducationEditor, self)
            )
        else:
            education_menu.addAction("&Start Education-Tour", self.init_edu)

        # Tools
        tool_menu = self.menuBar().addMenu("&Tools")
        tool_menu.addAction("&Data-Terminal", partial(DataTerminal, self))
        tool_menu.addAction("&Plot-Viewer", partial(PlotViewSelection, self))

        # View
        self.view_menu = self.menuBar().addMenu("&View")
        if not ismac:
            self.view_menu.addAction("&Full-Screen", self.full_screen).setCheckable(
                True
            )

        # Settings
        settings_menu = self.menuBar().addMenu("&Settings")

        settings_menu.addAction("&Open Settings", partial(SettingsDlg, self, self.ct))
        settings_menu.addAction("&Change Home-Path", self.change_home_path)
        settings_menu.addSeparator()
        # ToDo: Needs to be thoroughly tested on all OS
        # settings_menu.addAction('&Update Pipeline (stable)',
        #                         partial(self.update_pipeline, 'stable'))
        # settings_menu.addAction('&Update Pipeline (dev)',
        #                         partial(self.update_pipeline, 'dev'))
        # settings_menu.addAction('&Update MNE-Python', self.update_mne)
        settings_menu.addAction("&Restart", self.restart)

        # About
        about_menu = self.menuBar().addMenu("About")
        # about_menu.addAction('Update Pipeline', self.update_pipeline)
        # about_menu.addAction('Update MNE-Python', self.update_mne)
        about_menu.addAction("Quick-Guide", partial(QuickGuide, self))
        about_menu.addAction("MNE System-Info", self.show_sys_info)
        about_menu.addAction("About", partial(AboutDialog, self))
        about_menu.addAction("About QT", QApplication.instance().aboutQt)

    def init_toolbar(self):
        self.toolbar = self.addToolBar("Tools")
        # Add Project-UI
        proj_box_label = QLabel("<b>Project: </b>")
        self.toolbar.addWidget(proj_box_label)

        self.project_box = QComboBox()
        self.project_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.project_box.activated.connect(self.project_changed)
        self.update_project_box()
        self.toolbar.addWidget(self.project_box)

        add_action = QAction(parent=self, icon=get_std_icon("SP_FileDialogNewFolder"))
        add_action.triggered.connect(self.add_project)
        self.toolbar.addAction(add_action)

        remove_action = QAction(
            parent=self, icon=get_std_icon("SP_DialogDiscardButton")
        )
        remove_action.triggered.connect(self.remove_project)
        self.toolbar.addAction(remove_action)
        self.toolbar.addSeparator()

        self.toolbar.addWidget(
            IntGui(
                data=QS(),
                name="n_jobs",
                min_val=-1,
                special_value_text="Auto",
                description="Set to the amount of (virtual) cores "
                "of your machine you want "
                "to use for multiprocessing.",
                default=-1,
                groupbox_layout=False,
            )
        )
        # self.toolbar.addWidget(
        #     IntGui(data=QS(), name='n_parallel', min_val=1,
        #            description='Set to the amount of threads you want '
        #                        'to run simultaneously in the pipeline',
        #            default=1, groupbox_layout=False))
        # self.toolbar.addWidget(
        #     BoolGui(data=QS(), name='use_qthread', alias='Use QThreads',
        #             description='Check to use QThreads for running '
        #                         'the pipeline.\n'
        #                         'This is faster than the default'
        #                         ' with separate processes, '
        #                         'but has a few limitations',
        #             default=0, return_integer=True))
        # self.toolbar.addWidget(BoolGui(data=self.ct.settings, name='overwrite',
        #                                alias='Overwrite',
        #                                description='Check to overwrite files'
        #                                            ' even if their parameters '
        #                                            'where unchanged.',
        #                                groupbox_layout=False))
        self.toolbar.addWidget(
            BoolGui(
                data=self.ct.settings,
                name="show_plots",
                alias="Show Plots",
                description="Do you want to show"
                " plots?\n"
                "(or just save them without"
                " showing, then just check"
                ' "Save Plots").',
                groupbox_layout=False,
            )
        )
        self.toolbar.addWidget(
            BoolGui(
                data=self.ct.settings,
                name="save_plots",
                alias="Save Plots",
                description="Do you want to save the " "plots made to a file?",
                groupbox_layout=False,
            )
        )
        self.toolbar.addWidget(
            BoolGui(
                data=self.ct.settings,
                name="shutdown",
                alias="Shutdown",
                description="Do you want to shut your "
                "system down after "
                " execution of all "
                "subjects?",
                groupbox_layout=False,
            )
        )
        close_all_bt = QPushButton("Close All Plots")
        close_all_bt.pressed.connect(close_all)
        self.toolbar.addWidget(close_all_bt)

    def init_main_widget(self):
        self.setCentralWidget(QWidget(self))
        self.general_layout = QGridLayout()
        self.centralWidget().setLayout(self.general_layout)

        self.tab_func_widget = QTabWidget()
        self.general_layout.addWidget(self.tab_func_widget, 0, 0, 1, 3)

        # Show already here to get the width of tab_func_widget to fit
        # the function-groups inside
        self.show()
        self.general_layout.invalidate()

        # Add Function-Buttons
        self.add_func_bts()

        # Add Main-Buttons
        clear_bt = QPushButton("Clear")
        start_bt = QPushButton("Start")
        stop_bt = QPushButton("Quit")

        clear_bt.setFont(QFont(QS().value("app_font"), 18))
        start_bt.setFont(QFont(QS().value("app_font"), 18))
        stop_bt.setFont(QFont(QS().value("app_font"), 18))

        clear_bt.clicked.connect(self.clear)
        start_bt.clicked.connect(self.start)
        stop_bt.clicked.connect(self.close)

        self.general_layout.addWidget(clear_bt, 1, 0)
        self.general_layout.addWidget(start_bt, 1, 1)
        self.general_layout.addWidget(stop_bt, 1, 2)

    # Todo: Make Buttons more appealing, mark when check
    #   make button-dependencies
    def add_func_bts(self):
        # Drop custom-modules, which aren't selected
        cleaned_pd_funcs = self.ct.pd_funcs.loc[
            self.ct.pd_funcs["module"].isin(self.ct.get_setting("selected_modules"))
        ].copy()
        # Horizontal Border for Function-Groups
        max_h_size = self.tab_func_widget.geometry().width()

        # Assert, that cleaned_pd_funcs is not empty
        # (possible, when deselecting all modules)
        if len(cleaned_pd_funcs) != 0:
            tabs_grouped = cleaned_pd_funcs.groupby("tab")
            # Add tabs
            for tab_name, group in tabs_grouped:
                group_grouped = group.groupby("group", sort=False)
                tab = QScrollArea()
                child_w = QWidget()
                tab_v_layout = QVBoxLayout()
                tab_h_layout = QHBoxLayout()
                h_size = 0
                # Add groupbox for each group
                for function_group, _ in group_grouped:
                    group_box = QGroupBox(function_group, self)
                    group_box.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
                    setattr(self, f"{function_group}_gbox", group_box)
                    group_box.setCheckable(True)
                    group_box.toggled.connect(self.func_group_toggled)
                    group_box_layout = QVBoxLayout()
                    # Add button for each function
                    for function in group_grouped.groups[function_group]:
                        if pd.notna(cleaned_pd_funcs.loc[function, "alias"]):
                            alias_name = cleaned_pd_funcs.loc[function, "alias"]
                        else:
                            alias_name = function
                        pb = QPushButton(alias_name)
                        pb.setCheckable(True)
                        self.bt_dict[function] = pb
                        if function in self.pr.sel_functions:
                            pb.setChecked(True)
                        pb.clicked.connect(partial(self.func_selected, function))
                        group_box_layout.addWidget(pb)

                    group_box.setLayout(group_box_layout)
                    h_size += group_box.sizeHint().width()
                    if h_size > max_h_size:
                        tab_v_layout.addLayout(tab_h_layout)
                        h_size = group_box.sizeHint().width()
                        tab_h_layout = QHBoxLayout()
                    tab_h_layout.addWidget(
                        group_box, alignment=Qt.AlignLeft | Qt.AlignTop
                    )

                if tab_h_layout.count() > 0:
                    tab_v_layout.addLayout(tab_h_layout)

                child_w.setLayout(tab_v_layout)
                tab.setWidget(child_w)
                self.tab_func_widget.addTab(tab, tab_name)

    def update_func_bts(self):
        # Remove tabs in tab_func_widget
        while self.tab_func_widget.count():
            tab = self.tab_func_widget.removeTab(0)
            if tab:
                tab.deleteLater()
        self.bt_dict = dict()

        self.add_func_bts()

    def redraw_func_and_param(self):
        self.update_func_bts()
        self.parameters_dock.redraw_param_widgets()

    def _update_selected_functions(self, function, checked):
        if checked:
            if function not in self.pr.sel_functions:
                self.pr.sel_functions.append(function)
        elif function in self.pr.sel_functions:
            self.pr.sel_functions.remove(function)

    def func_selected(self, function):
        self._update_selected_functions(function, self.bt_dict[function].isChecked())

    def func_group_toggled(self):
        for function in self.bt_dict:
            self._update_selected_functions(
                function,
                self.bt_dict[function].isChecked()
                and self.bt_dict[function].isEnabled(),
            )

    def update_selected_funcs(self):
        for function in self.bt_dict:
            self.bt_dict[function].setChecked(False)
            if function in self.pr.sel_functions:
                self.bt_dict[function].setChecked(True)

    def init_docks(self):
        if self.ct.edu_program:
            dock_kwargs = self.ct.edu_program["dock_kwargs"]
        else:
            dock_kwargs = dict()
        self.file_dock = FileDock(self, **dock_kwargs)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.file_dock)
        self.view_menu.addAction(self.file_dock.toggleViewAction())

        self.parameters_dock = ParametersDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.parameters_dock)
        self.view_menu.addAction(self.parameters_dock.toggleViewAction())

    def add_sample_dataset(self):
        if "_sample_" in self.pr.all_meeg:
            QMessageBox.information(
                self,
                "_sample_ exists!",
                "The sample-dataset is already " "imported as _sample_!",
            )
        else:
            WorkerDialog(
                self,
                partial(self.pr.add_meeg, "_sample_"),
                show_console=True,
                title="Loading Sample...",
                blocking=True,
            )
            self.file_dock.update_dock()

    def add_test_dataset(self):
        if "_test_" in self.pr.all_meeg:
            QMessageBox.information(
                self,
                "_test_ exists!",
                "The test-dataset is already " "imported as _test_!",
            )
        else:
            WorkerDialog(
                self,
                partial(self.pr.add_meeg, "_test_"),
                show_console=True,
                title="Loading Sample...",
                blocking=True,
            )
            self.file_dock.update_dock()

    def add_fsaverage(self):
        if "fsaverage" in self.pr.all_fsmri:
            QMessageBox.information(
                self, "fsaverage exists!", "fsaverage is already imported!"
            )
        else:
            WorkerDialog(
                self,
                partial(self.pr.add_fsmri, "fsaverage"),
                show_console=True,
                title="Loading fsaverage...",
                blocking=True,
            )
            self.file_dock.update_dock()

    def full_screen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def clear(self):
        for x in self.bt_dict:
            self.bt_dict[x].setChecked(False)
        self.pr.sel_functions.clear()

    def start(self):
        if self.pipeline_running:
            QMessageBox.warning(
                self, "Already running!", "The Pipeline is already running!"
            )
        else:
            WorkerDialog(
                self,
                self.ct.save,
                show_buttons=False,
                show_console=False,
                blocking=True,
            )
            self.run_dialog = RunDialog(self)

    def restart(self):
        self.restarting = True
        self.close()
        restart_program()

    def update_pipeline(self, version):
        if version == "stable":
            command = "pip install --upgrade mne_pipeline_hd"
        else:
            command = (
                "pip install " "https://github.com/marsipu/mne-pipeline-hd/zipball/main"
            )
        if iswin and not _run_from_script():
            QMessageBox.information(
                self,
                "Manual install required!",
                f"To update you need to exit the program "
                f'and type "{command}" into the terminal!',
            )
        else:
            QProcessDialog(
                self,
                command,
                show_buttons=True,
                show_console=True,
                close_directly=True,
                title="Updating Pipeline...",
                blocking=True,
            )

            answer = QMessageBox.question(
                self,
                "Do you want to restart?",
                "Please restart the Pipeline-Program "
                "to apply the changes from the Update!",
            )

            if answer == QMessageBox.Yes:
                self.restart()

    def update_mne(self):
        command = "pip install --upgrade mne"
        QProcessDialog(
            self,
            command,
            show_buttons=True,
            show_console=True,
            close_directly=True,
            title="Updating MNE-Python...",
            blocking=True,
        )

        answer = QMessageBox.question(
            self,
            "Do you want to restart?",
            "Please restart the Pipeline-Program "
            "to apply the changes from the Update!",
        )

        if answer == QMessageBox.Yes:
            self.restart()

    def show_sys_info(self):
        sys_info_msg = SysInfoMsg(self)
        sys.stdout.signal.text_written.connect(sys_info_msg.add_text)
        mne.sys_info()

    def resizeEvent(self, event):
        if not self.first_init:
            self.update_func_bts()
        event.accept()

    def closeEvent(self, event):
        welcome_window = _object_refs["welcome_window"]
        if self.restarting or welcome_window is None:
            answer = QMessageBox.No
        else:
            answer = QMessageBox.question(
                self,
                "Closing MNE-Pipeline",
                "Do you want to return to the Welcome-Window?",
                buttons=QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                defaultButton=QMessageBox.Yes,
            )
        if answer not in [QMessageBox.Yes, QMessageBox.No]:
            event.ignore()
        else:
            if self.edu_tour:
                self.edu_tour.close()
            event.accept()
            _object_refs["main_window"] = None

            if welcome_window is not None:
                if answer == QMessageBox.Yes:
                    welcome_window.update_widgets()
                    welcome_window.show()

                elif answer == QMessageBox.No:
                    welcome_window.close()
