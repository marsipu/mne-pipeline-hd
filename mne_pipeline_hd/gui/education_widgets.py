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
import json
from os import makedirs
from os.path import isdir, join
from shutil import copytree

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, \
    QTextEdit, \
    QVBoxLayout, \
    QWizard, \
    QWizardPage

from mne_pipeline_hd.gui.base_widgets import CheckDictEditList, CheckList
from mne_pipeline_hd.gui.gui_utils import center, get_ratio_geometry


class EducationTour(QWizard):
    def __init__(self, main_win, edu_program):
        super().__init__(main_win)
        self.mw = main_win
        self.edu = edu_program

        self.setWindowTitle(self.edu['name'])
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.HaveHelpButton, False)

        width, height = get_ratio_geometry(0.4)
        self.resize(width, height)
        center(self)

        self.add_pages()
        self.show()

    def add_pages(self):
        for page_name in self.edu['tour_list']:
            page = QWizardPage()
            page.setTitle(page_name)

            layout = QVBoxLayout()
            page_view = QTextEdit()
            page_view.setReadOnly(True)
            text = self.edu['tour'][page_name]
            if self.edu['format'] == 'PlainText':
                page_view.setPlainText(text)
            elif self.edu['format'] == 'HTML':
                page_view.setHtml(text)
            elif self.edu['format'] == 'Markdown':
                page_view.setMarkdown(text)
            layout.addWidget(page_view)
            page.setLayout(layout)

            self.addPage(page)


class EducationEditor(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.edu = dict()
        self.edu['name'] = 'Education'
        self.edu['meeg'] = self.mw.pr.sel_meeg.copy()
        self.edu['fsmri'] = self.mw.pr.sel_fsmri.copy()
        self.edu['functions'] = [f for f in self.mw.pr.sel_functions if self.mw.pr.sel_functions[f]]
        self.edu['dock_kwargs'] = {'meeg_view': False, 'fsmri_view': False}
        self.edu['format'] = 'PlainText'
        self.edu['tour_list'] = list()
        self.edu['tour'] = dict()

        width, height = get_ratio_geometry(0.8)
        self.resize(width, height)

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        name_label = QLabel('Name:')
        name_label.setFont(QFont('AnyStyle', 14))
        layout.addWidget(name_label)
        name_ledit = QLineEdit()
        name_ledit.textChanged.connect(self.name_changed)
        layout.addWidget(name_ledit)

        select_layout = QHBoxLayout()
        meeg_check_list = CheckList(self.mw.pr.all_meeg, self.edu['meeg'], title='Select MEEG')
        select_layout.addWidget(meeg_check_list)

        fsmri_check_list = CheckList(self.mw.pr.all_fsmri, self.edu['fsmri'], title='Select FSMRI')
        select_layout.addWidget(fsmri_check_list)

        func_check_list = CheckList(self.mw.pd_funcs.index, self.edu['functions'], title='Select Functions')
        select_layout.addWidget(func_check_list)

        layout.addLayout(select_layout)

        page_label = QLabel('Make a Tour:')
        page_label.setFont(QFont('AnyStyle', 14))
        format_cmbx = QComboBox()
        format_cmbx.addItems(['PlainText', 'HTML', 'Markdown'])
        format_cmbx.currentTextChanged.connect(self.format_changed)
        format_cmbx.setCurrentText('PlainText')
        layout.addWidget(format_cmbx)

        self.page_list = CheckDictEditList(self.edu['tour_list'], self.edu['tour'], show_index=True)
        self.page_list.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.page_list.currentChanged.connect(self.page_changed)
        layout.addWidget(self.page_list)

        edit_layout = QGridLayout()
        edit_label = QLabel('Edit')
        edit_layout.addWidget(edit_label, 0, 0, alignment=Qt.AlignHCenter)
        self.page_edit = QTextEdit()
        self.page_edit.textChanged.connect(self.page_text_changed)
        edit_layout.addWidget(self.page_edit, 1, 0)

        preview_label = QLabel('Preview')
        edit_layout.addWidget(preview_label, 0, 1, alignment=Qt.AlignHCenter)
        self.page_display = QTextEdit()
        self.page_display.setReadOnly(True)
        edit_layout.addWidget(self.page_display, 1, 1)

        layout.addLayout(edit_layout)

        bt_layout = QHBoxLayout()
        save_bt = QPushButton('Save')
        save_bt.clicked.connect(self.save_edu)
        bt_layout.addWidget(save_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)
        layout.addLayout(bt_layout)

        self.setLayout(layout)

    def name_changed(self, text):
        if text != '':
            self.edu['name'] = text

    def format_changed(self, text):
        if text != '':
            self.edu['format'] = text
        self.page_text_changed()

    def _set_page_display(self, text):
        self.page_display.clear()
        if self.edu['format'] == 'PlainText':
            self.page_display.setPlainText(text)
        elif self.edu['format'] == 'HTML':
            self.page_display.setHtml(text)
        elif self.edu['format'] == 'Markdown':
            self.page_display.setMarkdown(text)

    def page_changed(self, page_name):
        if page_name in self.edu['tour']:
            text = self.edu['tour'][page_name]
            self.page_edit.clear()
            self.page_edit.setPlainText(text)
            self._set_page_display(text)
        else:
            self.page_edit.clear()
            self.page_display.clear()

    def page_text_changed(self):
        current_page = self.page_list.get_current()
        text = self.page_edit.toPlainText()
        self._set_page_display(text)
        if text != '':
            self.edu['tour'][current_page] = text

    def save_edu(self):
        if len(self.edu['meeg']) > 0:
            self.edu['dock_kwargs']['meeg_view'] = True
        if len(self.edu['fsmri']) > 0:
            self.edu['dock_kwargs']['fsmri_view'] = True

        edu_folder = join(self.mw.home_path, 'edu_programs')
        if not isdir(edu_folder):
            makedirs(edu_folder)

        edu_path = join(edu_folder, f'{self.edu["name"]}-edu.json')
        with open(edu_path, 'w') as file:
            json.dump(self.edu, file, indent=4)

        new_pscripts_path = join(self.mw.pr.project_path, f'_pipeline_scripts{self.edu["name"]}')
        # Copy Pipeline-Scripts
        copytree(self.mw.pr.pscripts_path, new_pscripts_path)
