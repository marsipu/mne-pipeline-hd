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
from collections import Counter
from importlib import resources
from pathlib import Path

import mne
from PyQt5.QtWidgets import (QDialog, QGridLayout, QLabel, QListView, QPushButton,
                             QSizePolicy, QTextEdit, QVBoxLayout)

from mne_pipeline_hd.gui.base_widgets import SimpleList
from mne_pipeline_hd.gui.gui_utils import set_ratio_geometry
from mne_pipeline_hd.gui.models import CheckListModel
from mne_pipeline_hd.pipeline_functions.loading import MEEG


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


class RemoveProjectsDlg(CheckListDlg):
    def __init__(self, main_win, controller):
        self.mw = main_win
        self.ct = controller
        self.rm_list = []
        super().__init__(main_win, self.ct.projects, self.rm_list)

        self.do_bt.setText('Remove Projects')
        self.do_bt.clicked.connect(self.remove_selected)

        self.open()

    def remove_selected(self):
        for project in self.rm_list:
            self.ct.remove_project(project)
        self.lm.layoutChanged.emit()
        self.mw.update_project_ui()

        self.close()


class SysInfoMsg(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        layout = QVBoxLayout()
        self.show_widget = QTextEdit()
        self.show_widget.setReadOnly(True)
        layout.addWidget(self.show_widget)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        # Set geometry to ratio of screen-geometry
        set_ratio_geometry(0.4, self)

        self.setLayout(layout)
        self.show()

    def add_text(self, text):
        self.show_widget.insertPlainText(text)


class QuickGuide(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        layout = QVBoxLayout()

        text = '<b>Quick-Guide</b><br>' \
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


class RawInfo(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.info_string = None

        set_ratio_geometry(0.6, self)

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QGridLayout()
        meeg_list = SimpleList(self.mw.ct.pr.all_meeg)
        meeg_list.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        meeg_list.currentChanged.connect(self.meeg_selected)
        layout.addWidget(meeg_list, 0, 0)

        self.info_label = QTextEdit()
        self.info_label.setReadOnly(True)
        self.info_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        layout.addWidget(self.info_label, 0, 1)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt, 1, 0, 1, 2)

        self.setLayout(layout)

    def meeg_selected(self, meeg_name):
        # Get size in Mebibytes of all files associated to this
        meeg = MEEG(meeg_name, self.mw.ct)
        info = meeg.load_info()
        fp = meeg.file_parameters
        meeg.get_existing_paths()
        other_infos = dict()

        sizes = list()
        for path_type in meeg.existing_paths:
            for path in meeg.existing_paths[path_type]:
                file_name = Path(path).name
                if file_name in fp and 'SIZE' in fp[file_name]:
                    sizes.append(fp[file_name]['SIZE'])
        other_infos['no_files'] = len(sizes)

        sizes_sum = sum(sizes)
        if sizes_sum / 1024 < 1000:
            other_infos['size'] = f'{int(sizes_sum / 1024)}'
            size_unit = 'KB'
        else:
            other_infos['size'] = f'{int(sizes_sum / 1024 ** 2)}'
            size_unit = 'MB'

        ch_type_counter = Counter([mne.io.pick.channel_type(info, idx) for idx in range(len(info['chs']))])
        other_infos['ch_types'] = ', '.join([f'{key}: {value}' for key, value in ch_type_counter.items()])

        key_list = [('no_files', 'Size of all associated files'),
                    ('size', 'Size of all associated files', size_unit),
                    ('proj_name', 'Project-Name'),
                    ('experimenter', 'Experimenter'),
                    ('line_freq', 'Powerline-Frequency', 'Hz'),
                    ('sfreq', 'Samplerate', 'Hz'),
                    ('highpass', 'Highpass', 'Hz'),
                    ('lowpass', 'Lowpass', 'Hz'),
                    ('nchan', 'Number of channels'),
                    ('ch_types', 'Channel-Types'),
                    ('subject_info', 'Subject-Info'),
                    ('device_info', 'Device-Info'),
                    ('helium_info', 'Helium-Info')]

        self.info_string = f'<h1>{meeg_name}</h1>'

        for key_tuple in key_list:
            key = key_tuple[0]
            if key in info:
                value = info[key]
            elif key in other_infos:
                value = other_infos[key]
            else:
                value = None

            if len(key_tuple) == 2:
                self.info_string += f'<b>{key_tuple[1]}:</b> {value}<br>'
            else:
                self.info_string += f'<b>{key_tuple[1]}:</b> {value} <i>{key_tuple[2]}</i><br>'

        self.info_label.setHtml(self.info_string)


class AboutDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        with resources.open_text('mne_pipeline_hd.pipeline_resources', 'license.txt') as file:
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
               '<b>Dependencies:</b><br>' \
               'MNE-Python: <a href=https://github.com/mne-tools/mne-python>Website</a>' \
               '<a href=https://github.com/mne-tools/mne-python>GitHub</a><br>' \
               '<a href=https://github.com/ColinDuquesnoy/QDarkStyleSheet>qdarkstyle</a><br>' \
               '<br>' \
               '<b>Licensed under:</b><br>' \
               + license_text

        layout = QVBoxLayout()

        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setHtml(text)
        layout.addWidget(text_widget)

        self.setLayout(layout)
        set_ratio_geometry((0.25, 0.9), self)
        self.open()


