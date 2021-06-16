# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2020, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
from importlib import resources
from os import listdir
from os.path import isdir, join

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QInputDialog,
                             QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget)

from mne_pipeline_hd import QS
from mne_pipeline_hd.gui.base_widgets import SimpleList
from mne_pipeline_hd.gui.gui_utils import ErrorDialog, center, WorkerDialog
from mne_pipeline_hd.gui.main_window import MainWindow
from mne_pipeline_hd.pipeline_functions.controller import Controller


class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.ct = Controller()
        self.main_window = None
        self.education_programs = list()
        self.education_on = QS().value('education', defaultValue=0)

        self.init_ui()
        self.check_controller()

        self.show()
        center(self)

    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel('Welcome to MNE-Pipeline!')
        title_label.setFont(QFont(QS().value('app_font'), 20))
        layout.addWidget(title_label)

        image_label = QLabel()
        with resources.path('mne_pipeline_hd.pipeline_resources',
                            'mne_pipeline_logo_evee_smaller.jpg') as img_path:
            image_label.setPixmap(QPixmap(str(img_path)))
        layout.addWidget(image_label)

        home_layout = QHBoxLayout()
        self.home_path_label = QLabel()
        home_layout.addWidget(self.home_path_label, stretch=4)
        home_path_bt = QPushButton('Set Home-Folder')
        home_path_bt.clicked.connect(self.set_home_path)
        home_layout.addWidget(home_path_bt, alignment=Qt.AlignRight)
        layout.addLayout(home_layout)

        project_layout = QHBoxLayout()
        self.project_label = QLabel()
        project_layout.addWidget(self.project_label)
        self.project_cmbx = QComboBox()
        self.project_cmbx.activated.connect(self.project_changed)
        project_layout.addWidget(self.project_cmbx)
        self.add_pr_bt = QPushButton('Add Project')
        self.add_pr_bt.clicked.connect(self.add_project)
        project_layout.addWidget(self.add_pr_bt, alignment=Qt.AlignRight)
        layout.addLayout(project_layout)

        self.edu_groupbox = QGroupBox('Education')
        self.edu_groupbox.setCheckable(True)
        if self.education_on == 'true':
            self.edu_groupbox.setChecked(True)
        else:
            self.edu_groupbox.setChecked(False)
        edu_layout = QVBoxLayout()
        self.edu_selection = SimpleList(self.education_programs, title='Education')
        edu_layout.addWidget(self.edu_selection)
        self.edu_groupbox.setLayout(edu_layout)
        layout.addWidget(self.edu_groupbox)

        bt_layout = QHBoxLayout()
        self.start_bt = QPushButton('Start')
        self.start_bt.setFont(QFont(QS().value('app_font'), 20))
        self.start_bt.setEnabled(False)
        self.start_bt.clicked.connect(self.init_main_window)
        bt_layout.addWidget(self.start_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        close_bt.setFont(QFont(QS().value('app_font'), 20))
        bt_layout.addWidget(close_bt)

        layout.addLayout(bt_layout)
        self.setLayout(layout)

    def check_controller(self):
        self.start_bt.setEnabled(False)
        self.project_cmbx.setEnabled(False)
        self.add_pr_bt.setEnabled(False)

        # Check for Home-Path-Problems
        if 'home_path' in self.ct.errors:
            ht = f'{self.ct.errors["home_path"]}\n' \
                 f'Select a folder as Home-Path!'
            self.home_path_label.setText(ht)
        else:
            self.home_path_label.setText(f'{self.ct.home_path} selected.')
            self.project_cmbx.setEnabled(True)
            self.update_project_cmbx()
            self.add_pr_bt.setEnabled(True)

            # Add education-programs if there are any
            self.education_programs.clear()
            edu_path = join(self.ct.home_path, 'edu_programs')
            if isdir(edu_path):
                for file in [f for f in listdir(edu_path) if f[-9:] == '-edu.json']:
                    self.education_programs.append(file)

            self.edu_selection.content_changed()

            # Check for Project-Problems
            if 'project' in self.ct.errors:
                pt = f'{self.ct.errors["project"]}\n' \
                     f'Select or add a project!'
                self.project_label.setText(pt)
            else:
                self.project_label.setText(f'{self.ct.pr.name} selected.')
                self.start_bt.setEnabled(True)

                # Check for Problems with Custom-Modules
                if 'custom_modules' in self.ct.errors:
                    for name in self.ct.errors['custom_modules']:
                        error_msg = self.ct.errors['custom_modules'][name]
                        if isinstance(error_msg, tuple):
                            ErrorDialog(error_msg, self,
                                        title=f'Error in import of custom-module: {name}')
                        elif isinstance(error_msg, str):
                            QMessageBox.warning(self, 'Import-Problem', error_msg)

    def set_home_path(self):
        loaded_home_path = QFileDialog.getExistingDirectory(self, f'{self.ct.home_path}'
                                                                  f'Select a folder as Home-Path')
        if loaded_home_path != '':
            self.ct = Controller(str(loaded_home_path))
            self.check_controller()

    def project_changed(self, project_idx):
        project = self.project_cmbx.itemText(project_idx)
        self.ct.change_project(project)
        self.update_project_cmbx()
        self.start_bt.setEnabled(True)

    def update_project_cmbx(self):
        if hasattr(self.ct, 'projects'):
            self.project_cmbx.clear()
            self.project_cmbx.addItems(self.ct.projects)
        if self.ct.pr is not None:
            self.project_label.setText(f'{self.ct.pr.name} selected.')
            self.project_cmbx.setCurrentText(self.ct.pr.name)

    def add_project(self):
        new_project, ok = QInputDialog.getText(self, 'Add Project',
                                               'Please enter the name of a project!')
        if ok and new_project != '':
            self.ct.change_project(new_project)
            self.update_project_cmbx()
            self.start_bt.setEnabled(True)

    def init_main_window(self):
        if self.edu_groupbox.isChecked():
            self.ct.edu_program_name = self.edu_selection.get_current()
            self.ct.load_edu()

        # Check if MNE-Python is installed
        try:
            import mne
        except ModuleNotFoundError:
            QMessageBox.critical(self, 'MNE-Python not found!', 'MNE-Python was not found,'
                                                                ' please install it before using MNE-Pipeline!')
        else:
            self.main_window = MainWindow(self.ct, self)
            if self.edu_groupbox.isChecked():
                self.main_window.start_edu()
            self.hide()

    def closeEvent(self, event):
        WorkerDialog(self, self.ct.save, blocking=True, title='Saving Project!')
        if self.edu_groupbox.isChecked():
            QS().setValue('education', 1)
        else:
            QS().setValue('education', 0)

        event.accept()
