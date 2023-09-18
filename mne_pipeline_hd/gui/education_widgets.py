# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import json
from os import makedirs
from os.path import isdir, join
from shutil import copytree

from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSizePolicy,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from mne_pipeline_hd.gui.base_widgets import CheckDictEditList, CheckList
from mne_pipeline_hd.gui.gui_utils import center, set_ratio_geometry
from mne_pipeline_hd.pipeline.pipeline_utils import QS


class EducationTour(QWizard):
    def __init__(self, main_win, edu_program):
        super().__init__(main_win)
        self.mw = main_win
        self.edu = edu_program

        self.setWindowTitle(self.edu["name"])
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.HaveHelpButton, False)

        set_ratio_geometry(0.4, self)
        center(self)

        self.add_pages()
        self.show()

    def add_pages(self):
        for page_name in self.edu["tour_list"]:
            page = QWizardPage()
            page.setTitle(page_name)

            layout = QVBoxLayout()
            page_view = QTextBrowser()
            page_view.setReadOnly(True)
            page_view.setOpenExternalLinks(True)
            text = self.edu["tour"][page_name]
            if self.edu["format"] == "PlainText":
                page_view.setPlainText(text)
            elif self.edu["format"] == "HTML":
                page_view.setHtml(text)
            # Not supported until PyQt>=5.14
            # elif self.edu['format'] == 'Markdown':
            #     page_view.setMarkdown(text)
            layout.addWidget(page_view)
            page.setLayout(layout)

            self.addPage(page)


class EducationEditor(QMainWindow):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.edu = dict()
        self.edu["name"] = "Education"
        self.edu["meeg"] = self.ct.pr.sel_meeg.copy()
        self.edu["fsmri"] = self.ct.pr.sel_fsmri.copy()
        self.edu["groups"] = self.ct.pr.sel_groups.copy()
        self.edu["functions"] = [
            f for f in self.ct.pr.sel_functions if f in self.ct.pr.sel_functions
        ]
        self.edu["dock_kwargs"] = {
            "meeg_view": False,
            "fsmri_view": False,
            "group_view": False,
        }
        self.edu["format"] = "PlainText"
        self.edu["tour_list"] = list()
        self.edu["tour"] = dict()

        self.edu_folder = join(self.ct.home_path, "edu_programs")
        set_ratio_geometry(0.8, self)

        self.init_menu()
        self.init_ui()
        self.show()

    def init_menu(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("&Load", self.load_edu_file)
        file_menu.addAction("&Save", self.save_edu_file)
        file_menu.addSeparator()
        file_menu.addAction("&Close", self.close)

    def init_ui(self):
        layout = QVBoxLayout()
        self.setCentralWidget(QWidget())

        name_label = QLabel("Name:")
        name_label.setFont(QFont(QS().value("app_font"), 14))
        layout.addWidget(name_label)
        self.name_ledit = QLineEdit()
        self.name_ledit.textEdited.connect(self.name_changed)
        layout.addWidget(self.name_ledit)

        select_layout = QHBoxLayout()
        self.meeg_check_list = CheckList(
            self.ct.pr.all_meeg, self.edu["meeg"], title="Select MEEG"
        )
        select_layout.addWidget(self.meeg_check_list)

        self.fsmri_check_list = CheckList(
            self.ct.pr.all_fsmri, self.edu["fsmri"], title="Select FSMRI"
        )
        select_layout.addWidget(self.fsmri_check_list)

        self.group_check_list = CheckList(
            list(self.ct.pr.all_groups.keys()),
            self.edu["groups"],
            title="Select Groups",
        )
        select_layout.addWidget(self.group_check_list)

        self.func_check_list = CheckList(
            self.ct.pd_funcs.index, self.edu["functions"], title="Select Functions"
        )
        select_layout.addWidget(self.func_check_list)

        layout.addLayout(select_layout)

        page_label = QLabel("Make a Tour:")
        page_label.setFont(QFont(QS().value("app_font"), 14))
        self.format_cmbx = QComboBox()
        self.format_cmbx.addItems(["PlainText", "HTML"])
        self.format_cmbx.currentTextChanged.connect(self.format_changed)
        self.format_cmbx.setCurrentText("PlainText")
        layout.addWidget(self.format_cmbx)

        self.page_list = CheckDictEditList(
            self.edu["tour_list"], self.edu["tour"], show_index=True
        )
        self.page_list.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.page_list.currentChanged.connect(self.page_changed)
        self.page_list.dataChanged.connect(self.page_edited)
        layout.addWidget(self.page_list)

        edit_layout = QGridLayout()
        edit_label = QLabel("Edit")
        edit_layout.addWidget(edit_label, 0, 0, alignment=Qt.AlignHCenter)
        self.page_edit = QTextEdit()
        self.page_edit.textChanged.connect(self.page_text_changed)
        edit_layout.addWidget(self.page_edit, 1, 0)

        preview_label = QLabel("Preview")
        edit_layout.addWidget(preview_label, 0, 1, alignment=Qt.AlignHCenter)
        self.page_display = QTextBrowser()
        self.page_display.setOpenExternalLinks(True)
        self.page_display.setReadOnly(True)
        edit_layout.addWidget(self.page_display, 1, 1)

        layout.addLayout(edit_layout)
        self.centralWidget().setLayout(layout)

    def update_ui(self):
        self.name_ledit.setText(self.edu["name"])
        self.meeg_check_list.replace_checked(self.edu["meeg"])
        self.fsmri_check_list.replace_checked(self.edu["fsmri"])
        self.group_check_list.replace_checked(self.edu["groups"])
        self.func_check_list.replace_checked(self.edu["functions"])
        self.format_cmbx.setCurrentText(self.edu["format"])
        self.page_list.replace_data(self.edu["tour_list"])
        self.page_list.replace_check_dict(self.edu["tour"])
        self.page_edit.clear()
        self.page_display.clear()

    def name_changed(self, text):
        if text != "":
            self.edu["name"] = text

    def format_changed(self, text):
        if text != "":
            self.edu["format"] = text
        self.page_text_changed()

    def _set_page_display(self, text):
        self.page_display.clear()
        if self.edu["format"] == "PlainText":
            self.page_display.setPlainText(text)
        elif self.edu["format"] == "HTML":
            self.page_display.setHtml(text)
        # Not supported until PyQt>=5.14
        # elif self.edu['format'] == 'Markdown':
        #     self.page_display.setMarkdown(text)

    def page_changed(self, page_name):
        if page_name in self.edu["tour"]:
            text = self.edu["tour"][page_name]
            self.page_edit.clear()
            self.page_edit.setPlainText(text)
            self._set_page_display(text)
        else:
            self.page_edit.clear()
            self.page_display.clear()

    def page_edited(self, new_page_name, index):
        # Rename key in dictionary
        try:
            old_page_name = list(self.edu["tour"].keys())[index.row()]
        except IndexError:
            old_page_name = new_page_name
        if old_page_name in self.edu["tour"]:
            self.edu["tour"][new_page_name] = self.edu["tour"].pop(old_page_name)
        else:
            self.edu["tour"][new_page_name] = ""

    def page_text_changed(self):
        current_page = self.page_list.get_current()
        text = self.page_edit.toPlainText()
        self._set_page_display(text)
        if text != "":
            self.edu["tour"][current_page] = text

    def load_edu_file(self):
        file_path = QFileDialog().getOpenFileName(self, directory=self.edu_folder)[0]
        if file_path != "":
            with open(file_path, "r") as file:
                self.edu = json.load(file)

        self.update_ui()

    def save_edu_file(self):
        if len(self.edu["meeg"]) > 0:
            self.edu["dock_kwargs"]["meeg_view"] = True
        if len(self.edu["fsmri"]) > 0:
            self.edu["dock_kwargs"]["fsmri_view"] = True
        if len(self.edu["groups"]) > 0:
            self.edu["dock_kwargs"]["group_view"] = True

        if not isdir(self.edu_folder):
            makedirs(self.edu_folder)

        edu_path = join(self.edu_folder, f'{self.edu["name"]}-edu.json')
        with open(edu_path, "w") as file:
            json.dump(self.edu, file, indent=4)

        new_pscripts_path = join(
            self.ct.pr.project_path, f'_pipeline_scripts{self.edu["name"]}'
        )
        # Copy Pipeline-Scripts
        copytree(self.ct.pr.pscripts_path, new_pscripts_path, dirs_exist_ok=True)
