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
import os
from importlib import resources
from os import listdir
from os.path import isdir, join

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QFileDialog, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, \
    QVBoxLayout, QWidget

from mne_pipeline_hd.gui.base_widgets import SimpleList
from mne_pipeline_hd.gui.gui_utils import center
from mne_pipeline_hd.gui.main_window import MainWindow


class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.qsettings = QSettings()
        self.mw = None
        self.home_path = self.qsettings.value('home_path', defaultValue=None)
        self.education_programs = list()
        self.education_on = self.qsettings.value('education')

        self.init_ui()
        self.check_home_path()
        self.get_projects()

        self.show()
        center(self)

    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel('Welcome to MNE-Pipeline!')
        title_label.setFont(QFont('AnyStyle', 20))
        layout.addWidget(title_label)

        image_label = QLabel()
        with resources.path('mne_pipeline_hd.pipeline_resources', 'mne_pipeline_logo_evee_smaller.jpg') as img_path:
            image_label.setPixmap(QPixmap(str(img_path)))
        layout.addWidget(image_label)

        self.home_path_label = QLabel()
        layout.addWidget(self.home_path_label)
        home_path_bt = QPushButton('Set Home-Folder')
        home_path_bt.clicked.connect(self.set_home_path)
        layout.addWidget(home_path_bt)

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
        self.start_bt.setFont(QFont('AnyStyle', 20))
        self.start_bt.setEnabled(False)
        self.start_bt.clicked.connect(self.init_main_window)
        bt_layout.addWidget(self.start_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        close_bt.setFont(QFont('AnyStyle', 20))
        bt_layout.addWidget(close_bt)

        layout.addLayout(bt_layout)
        self.setLayout(layout)

    def check_home_path(self):
        self.start_bt.setEnabled(False)
        if self.home_path is None or self.home_path == '':
            self.home_path_label.setText('There was no home_path found!\n'
                                         'Select a folder as Home-Path')
        elif not isdir(self.home_path):
            self.home_path_label.setText(f'{self.home_path} not found!\n'
                                         f'Select a folder as Home-Path')

        # Check, if path is writable
        elif not os.access(self.home_path, os.W_OK):
            self.home_path_label.setText(f'{self.home_path} not writable!\n'
                                         f'Select a folder as Home-Path')

        else:
            self.home_path_label.setText(f'{self.home_path} was chosen')
            self.qsettings.setValue('home_path', self.home_path)
            print(f'Home-Path: {self.home_path}')
            self.start_bt.setEnabled(True)

        if self.home_path is not None:
            self.education_programs.clear()
            edu_path = join(self.home_path, 'edu_programs')
            if isdir(edu_path):
                for file in [f for f in listdir(edu_path) if f[-9:] == '-edu.json']:
                    self.education_programs.append(file)

            self.edu_selection.content_changed()

    def set_home_path(self):
        loaded_home_path = QFileDialog.getExistingDirectory(self, f'{self.home_path} not writable!'
                                                                  f'Select a folder as Home-Path')
        if loaded_home_path != '':
            self.home_path = str(loaded_home_path)

        self.check_home_path()

    def get_projects(self):
        # Get current_project
        self.current_project = self.get_setting('current_project')
        # Get Project-Folders (recognized by distinct folders)
        self.projects = [p for p in listdir(self.projects_path)
                         if all([isdir(join(self.projects_path, p, d))
                                 for d in ['_pipeline_scripts', 'data', 'figures']])]
        if len(self.projects) == 0:
            if self.gui:
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

    def init_main_window(self):
        sel_edu_program = self.edu_selection.get_current()

        # Check if MNE-Python is installed
        try:
            import mne
        except ModuleNotFoundError:
            QMessageBox.critical(self, 'MNE-Python not found!', 'MNE-Python was not found,'
                                                                ' please install it before using MNE-Pipeline!')
        else:
            if self.edu_groupbox.isChecked():
                self.mw = MainWindow(self.home_path, self, sel_edu_program)
            else:
                self.mw = MainWindow(self.home_path, self)
            self.hide()

    def closeEvent(self, event):
        if self.edu_groupbox.isChecked():
            self.qsettings.setValue('education', 'true')
        else:
            self.qsettings.setValue('education', 'false')

        event.accept()
