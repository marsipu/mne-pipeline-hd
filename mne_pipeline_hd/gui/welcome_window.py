# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""

from importlib import resources
from os import listdir
from os.path import isdir, join

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (QComboBox, QFileDialog, QGroupBox, QHBoxLayout,
                             QLabel, QPushButton, QVBoxLayout,
                             QWidget)

from mne_pipeline_hd import _object_refs
from mne_pipeline_hd.gui.base_widgets import SimpleList
from mne_pipeline_hd.gui.gui_utils import (center, WorkerDialog,
                                           get_user_input_string)
from mne_pipeline_hd.gui.main_window import MainWindow
from mne_pipeline_hd.pipeline.controller import Controller
from mne_pipeline_hd.pipeline.pipeline_utils import QS


class WelcomeWindow(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        _object_refs['welcome_window'] = self
        if controller is None:
            try:
                self.ct = Controller()
            except RuntimeError:
                self.ct = None
        else:
            self.ct = controller

        self.init_ui()
        self.update_widgets()

        self.show()
        center(self)

    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel('Welcome to MNE-Pipeline!')
        title_label.setFont(QFont(QS().value('app_font'), 20))
        layout.addWidget(title_label)

        image_label = QLabel()
        with resources.path('mne_pipeline_hd.resource',
                            'mne_pipeline_logo_evee_smaller.jpg') as img_path:
            image_label.setPixmap(QPixmap(str(img_path)))
        layout.addWidget(image_label)

        home_layout = QHBoxLayout()
        self.home_path_label = QLabel()
        home_layout.addWidget(self.home_path_label, stretch=4)
        self.home_path_bt = QPushButton('Set Home-Folder')
        self.home_path_bt.clicked.connect(self.set_home_path)
        home_layout.addWidget(self.home_path_bt, alignment=Qt.AlignRight)
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
        self.edu_groupbox.setChecked(QS().value('education',
                                                defaultValue=False))
        self.edu_groupbox.toggled.connect(self.edu_toggled)

        edu_layout = QVBoxLayout()
        self.edu_selection = SimpleList(title='Education')
        edu_layout.addWidget(self.edu_selection)
        self.edu_groupbox.setLayout(edu_layout)
        layout.addWidget(self.edu_groupbox)

        bt_layout = QHBoxLayout()
        self.start_bt = QPushButton('Start')
        self.start_bt.setFont(QFont(QS().value('app_font'), 20))
        self.start_bt.clicked.connect(self.init_main_window)
        bt_layout.addWidget(self.start_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        close_bt.setFont(QFont(QS().value('app_font'), 20))
        bt_layout.addWidget(close_bt)

        layout.addLayout(bt_layout)
        self.setLayout(layout)

    def edu_toggled(self, value):
        QS().setValue('education', value)

    def update_widgets(self):
        if self.ct is not None:
            self.home_path_label.setText(f'{self.ct.home_path} selected.')
            self.add_pr_bt.setEnabled(True)
            if hasattr(self.ct, 'projects'):
                self.project_cmbx.setEnabled(True)
                self.project_cmbx.clear()
                self.project_cmbx.addItems(self.ct.projects)
            if self.ct.pr is not None:
                self.project_label.setText(f'{self.ct.pr.name} selected.')
                self.project_cmbx.setCurrentText(self.ct.pr.name)

            self.update_education_list()
            if self.ct.pr is not None:
                self.start_bt.setEnabled(True)
        else:
            self.project_cmbx.setEnabled(False)
            self.add_pr_bt.setEnabled(False)
            self.start_bt.setEnabled(False)
            self.home_path_label.setText('No Home-Path selected')

    def set_home_path(self):
        if self.ct is not None:
            self.ct.save()
        loaded_home_path = QFileDialog.getExistingDirectory(
            self, 'Select a folder as Home-Path')
        if loaded_home_path != '':
            try:
                self.ct = Controller(str(loaded_home_path))
            except RuntimeError as err:
                self.home_path_label.setText(str(err))
                self.start_bt.setEnabled(False)
                self.project_cmbx.setEnabled(False)
                self.add_pr_bt.setEnabled(False)
                self.project_cmbx.clear()
                self.project_label.clear()
                self.ct = None
            else:
                self.update_widgets()

    def project_changed(self, project_idx):
        if self.ct is not None:
            project = self.project_cmbx.itemText(project_idx)
            self.ct.change_project(project)
            self.update_widgets()

    def update_education_list(self):
        if self.ct is not None:
            edu_path = join(self.ct.home_path, 'edu_programs')
            if isdir(edu_path):
                self.edu_selection.replace_data(
                    [f for f in listdir(edu_path) if f[-9:] == '-edu.json'])

    def add_project(self):
        if self.ct is not None:
            new_project = get_user_input_string(
                'Please enter the name of a project!', 'Add Project')
            if new_project is not None:
                self.ct.change_project(new_project)
                self.update_widgets()

    def init_main_window(self):
        if self.ct is not None:
            edu_on = QS().value('education')
            if edu_on:
                self.ct.edu_program_name = self.edu_selection.get_current()
                self.ct.load_edu()

            self.hide()
            MainWindow(self.ct)

    def closeEvent(self, event):
        if self.ct is not None:
            WorkerDialog(self, self.ct.save, blocking=True,
                         title='Saving Project!')
        if self.edu_groupbox.isChecked():
            QS().setValue('education', 1)
        else:
            QS().setValue('education', 0)
        _object_refs['welcom_window'] = None
        event.accept()
