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
from ast import literal_eval
from collections import Counter
from functools import partial
from importlib import resources
from pathlib import Path

import mne
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import (QComboBox, QDialog, QDockWidget, QGridLayout, QHBoxLayout,
                             QInputDialog,
                             QLabel, QListView, QMessageBox, QPushButton,
                             QScrollArea, QSizePolicy, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
                             QStyleFactory)
from mne_pipeline_hd import QS
from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.base_widgets import CheckList, SimpleList
from mne_pipeline_hd.gui.gui_utils import WorkerDialog, get_exception_tuple, set_ratio_geometry, get_std_icon
from mne_pipeline_hd.gui.models import CheckListModel
from mne_pipeline_hd.pipeline_functions import iswin
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


class RemovePPresetDlg(CheckListDlg):
    def __init__(self, parent):
        self.parent = parent
        self.preset_list = [p for p in self.parent.ct.pr.parameters if p != 'Default']
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
            self.parent.ct.pr.parameters.pop(p_preset)
            self.parent.update_ppreset_cmbx()

        # If current Parameter-Preset was deleted
        if self.parent.ct.pr.p_preset not in self.parent.ct.pr.parameters:
            self.parent.ct.pr.p_preset = list(self.parent.ct.pr.parameters.keys())[0]
            self.parent.update_all_param_guis()

        self.close()


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


class SettingsDlg(QDialog):
    def __init__(self, parent_widget, controller):
        super().__init__(parent_widget)
        self.ct = controller

        self.settings_items = {
            'app_style': {
                'gui_type': 'ComboGui',
                'data_type': 'QSettings',
                'gui_kwargs': {
                    'param_alias': 'Application Style',
                    'description': 'Changes the application style (Restart required).',
                    'options': ['light', 'dark'] + QStyleFactory().keys(),
                    'groupbox_layout': False
                }
            },
            'app_font': {
                'gui_type': 'ComboGui',
                'data_type': 'QSettings',
                'gui_kwargs': {
                    'param_alias': 'Application Font',
                    'description': 'Changes default application font (Restart required).',
                    'options': QFontDatabase().families(QFontDatabase.Latin)
                }
            },
            'app_font_size': {
                'gui_type': 'IntGui',
                'data_type': 'QSettings',
                'gui_kwargs': {
                    'param_alias': 'Font Size',
                    'description': 'Changes default application font-size (Restart required).',
                    'min_val': 5,
                    'max_val': 20
                }
            },
            'save_ram': {
                'gui_type': 'BoolGui',
                'data_type': 'QSettings',
                'gui_kwargs': {
                    'param_alias': 'Save RAM',
                    'description': 'Set to True on low RAM-Machines to avoid the process to be killed '
                                   'by the OS due to low Memory (with leaving it off, the pipeline goes '
                                   'a bit faster, because the data can be saved in memory).',
                    'return_integer': True
                }

            },
            'fs_path': {
                'gui_type': 'StringGui',
                'data_type': 'QSettings',
                'gui_kwargs': {
                    'param_alias': 'FREESURFER_HOME-Path',
                    'description': 'Set the Path to the "freesurfer"-directory of your '
                                   'Freesurfer-Installation '
                                   '(for Windows to the LINUX-Path of the Freesurfer-Installation '
                                   'in Windows-Subsystem for Linux(WSL))',
                    'none_select': True
                }
            },
            'mne_path': {
                'gui_type': 'StringGui',
                'data_type': 'QSettings',
                'gui_kwargs': {
                    'param_alias': 'MNE-Python-Path',
                    'description': 'Set the LINUX-Path to the mne-environment (e.g '
                                   '...anaconda3/envs/mne) in Windows-Subsystem for Linux(WSL))',
                    'none_select': True
                }
            }
        }

        if not iswin:
            self.settings_items.pop('mne_path')

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        for setting in self.settings_items:
            gui_handle = getattr(parameter_widgets, self.settings_items[setting]['gui_type'])
            data_type = self.settings_items[setting]['data_type']
            gui_kwargs = self.settings_items[setting]['gui_kwargs']
            if data_type == 'QSettings':
                gui_kwargs['data'] = QS()
                gui_kwargs['default'] = self.ct.default_settings['qsettings'][setting]
            elif data_type == 'Controller':
                gui_kwargs['data'] = self.mw.ct
                gui_kwargs['default'] = self.ct.pd_params.loc[setting, 'default']
            else:
                gui_kwargs['data'] = self.ct.settings
                gui_kwargs['default'] = self.ct.default_settings['settings'][setting]
            gui_kwargs['param_name'] = setting
            layout.addWidget(gui_handle(**gui_kwargs))

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)


# Todo: Ordering Parameters in Tabs and add Find-Command
class ResetDialog(QDialog):
    def __init__(self, p_dock):
        super().__init__(p_dock)
        self.pd = p_dock
        self.selected_params = list()

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(CheckList(list(self.pd.ct.pr.parameters[self.pd.ct.pr.p_preset].keys()),
                                   self.selected_params,
                                   title='Select the Parameters to reset'))
        reset_bt = QPushButton('Reset')
        reset_bt.clicked.connect(self.reset_params)
        layout.addWidget(reset_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def reset_params(self):
        for param_name in self.selected_params:
            self.pd.ct.pr.load_default_param(param_name)
            print(f'Reset {param_name}')
        WorkerDialog(self, self.pd.ct.pr.save, title='Saving project...', blocking=True)
        self.pd.update_all_param_guis()
        self.close()


class CopyPDialog(QDialog):
    def __init__(self, p_dock):
        super().__init__(p_dock)
        self.pd = p_dock
        self.p = p_dock.ct.pr.parameters
        self.selected_from = None
        self.selected_to = list()
        self.selected_ps = list()

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        list_layout = QHBoxLayout()
        copy_from = SimpleList(list(self.p.keys()))
        copy_from.currentChanged.connect(self.from_selected)
        list_layout.addWidget(copy_from)

        self.copy_to = CheckList(checked=self.selected_to)
        list_layout.addWidget(self.copy_to)

        self.copy_ps = CheckList(checked=self.selected_ps)
        list_layout.addWidget(self.copy_ps)

        layout.addLayout(list_layout)

        bt_layout = QHBoxLayout()

        copy_bt = QPushButton('Copy')
        copy_bt.clicked.connect(self.copy_parameters)
        bt_layout.addWidget(copy_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        layout.addLayout(bt_layout)

        self.setLayout(layout)

    def from_selected(self, current):
        self.selected_from = current
        self.copy_to.replace_data([pp for pp in self.p.keys() if pp != current])
        self.copy_ps.replace_data([p for p in self.p[current]])

    def copy_parameters(self):
        if len(self.selected_to) > 0:
            for p_preset in self.selected_to:
                for parameter in self.selected_ps:
                    self.p[p_preset][parameter] = self.p[self.selected_from][parameter]

            WorkerDialog(self, self.pd.ct.pr.save, title='Saving project...', blocking=True)
            self.pd.update_all_param_guis()
            self.close()


class ParametersDock(QDockWidget):
    def __init__(self, main_win):
        super().__init__('Parameters', main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.main_widget = QWidget()
        self.param_guis = {}

        self.dropgroup_params()
        self.init_ui()

    def dropgroup_params(self):
        # Create a set of all unique parameters used by functions in selected_modules
        sel_pdfuncs = self.ct.pd_funcs.loc[self.ct.pd_funcs['module'].isin(self.ct.get_setting('selected_modules'))]
        # Remove rows with NaN in func_args
        sel_pdfuncs = sel_pdfuncs.loc[sel_pdfuncs['func_args'].notna()]
        all_used_params_str = ','.join(sel_pdfuncs['func_args'])
        # Make sure there are no spaces left
        all_used_params_str = all_used_params_str.replace(' ', '')
        all_used_params = set(all_used_params_str.split(','))
        drop_idx_list = list()
        self.cleaned_pd_params = self.ct.pd_params.copy()
        for param in self.cleaned_pd_params.index:
            if param in all_used_params:
                # Group-Name (if not given, set to 'Various')
                group_name = self.cleaned_pd_params.loc[param, 'group']
                if pd.isna(group_name):
                    self.cleaned_pd_params.loc[param, 'group'] = 'Various'
            else:
                # Drop Parameters which aren't used by functions
                drop_idx_list.append(param)
        self.cleaned_pd_params.drop(index=drop_idx_list, inplace=True)

    def init_ui(self):
        self.general_layout = QVBoxLayout()

        # Add Parameter-Preset-ComboBox
        title_layouts = QVBoxLayout()
        title_layout1 = QHBoxLayout()
        p_preset_l = QLabel('Parameter-Presets: ')
        title_layout1.addWidget(p_preset_l)
        self.p_preset_cmbx = QComboBox()
        self.p_preset_cmbx.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.p_preset_cmbx.activated.connect(self.p_preset_changed)
        self.update_ppreset_cmbx()
        title_layout1.addWidget(self.p_preset_cmbx)

        add_bt = QPushButton(icon=get_std_icon('SP_FileDialogNewFolder'))
        add_bt.clicked.connect(self.add_p_preset)
        title_layout1.addWidget(add_bt)

        rm_bt = QPushButton(icon=get_std_icon('SP_DialogDiscardButton'))
        rm_bt.clicked.connect(partial(RemovePPresetDlg, self))
        title_layout1.addWidget(rm_bt)

        title_layouts.addLayout(title_layout1)

        title_layout2 = QHBoxLayout()
        copy_bt = QPushButton('Copy')
        copy_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        copy_bt.clicked.connect(partial(CopyPDialog, self))
        title_layout2.addWidget(copy_bt)

        reset_bt = QPushButton('Reset')
        reset_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        reset_bt.clicked.connect(partial(ResetDialog, self))
        title_layout2.addWidget(reset_bt)

        reset_all_bt = QPushButton('Reset All')
        reset_all_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        reset_all_bt.clicked.connect(self.reset_all_parameters)
        title_layout2.addWidget(reset_all_bt)

        title_layouts.addLayout(title_layout2)
        self.general_layout.addLayout(title_layouts)

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
                try:
                    default = literal_eval(parameter['default'])
                except (SyntaxError, ValueError):
                    if gui_name == 'FuncGui':
                        default = eval(parameter['default'], {'np': np})
                    else:
                        default = parameter['default']
                if pd.notna(parameter['description']):
                    description = parameter['description']
                else:
                    description = ''
                if pd.notna(parameter['unit']):
                    unit = parameter['unit']
                else:
                    unit = None
                try:
                    gui_args = literal_eval(parameter['gui_args'])
                except (SyntaxError, ValueError):
                    gui_args = {}

                gui_handle = getattr(parameter_widgets, gui_name)
                try:
                    self.param_guis[idx] = gui_handle(self.mw, param_name=idx, param_alias=param_alias,
                                                      default=default, description=description, param_unit=unit,
                                                      **gui_args)
                except:
                    err_tuple = get_exception_tuple()
                    raise RuntimeError(f'Initiliazation of Parameter-Widget "{idx}" failed:\n'
                                       f'{err_tuple[1]}')

                layout.addWidget(self.param_guis[idx])

            child_w.setLayout(layout)
            tab.setWidget(child_w)
            self.tab_param_widget.addTab(tab, group_name)

        # Set Layout of QWidget (the class itself)
        self.general_layout.addWidget(self.tab_param_widget)

    def update_ppreset_cmbx(self):
        self.p_preset_cmbx.clear()
        for p_preset in self.ct.pr.parameters.keys():
            self.p_preset_cmbx.addItem(p_preset)
        if self.ct.pr.p_preset in self.ct.pr.parameters.keys():
            self.p_preset_cmbx.setCurrentText(self.ct.pr.p_preset)
        else:
            self.p_preset_cmbx.setCurrentText(list(self.ct.pr.parameters.keys())[0])

    def p_preset_changed(self, idx):
        self.ct.pr.p_preset = self.p_preset_cmbx.itemText(idx)
        self.update_all_param_guis()

    def add_p_preset(self):
        preset_name, ok = QInputDialog.getText(self, 'New Parameter-Preset',
                                               'Enter a name for a new Parameter-Preset')
        if ok:
            self.ct.pr.p_preset = preset_name
            self.ct.pr.load_default_parameters()
            self.p_preset_cmbx.addItem(preset_name)
            self.p_preset_cmbx.setCurrentText(preset_name)
        else:
            pass

    def redraw_param_widgets(self):
        self.general_layout.removeWidget(self.tab_param_widget)
        self.tab_param_widget.close()
        del self.tab_param_widget
        self.dropgroup_params()
        self.add_param_guis()
        self.update_ppreset_cmbx()

    def update_all_param_guis(self):
        for gui_name in self.param_guis:
            param_gui = self.param_guis[gui_name]
            param_gui.read_param()
            param_gui.set_param()

    def reset_all_parameters(self):
        msgbox = QMessageBox.question(self, 'Reset all Parameters?',
                                      'Do you really want to reset all parameters to their default?',
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if msgbox == QMessageBox.Yes:
            self.ct.pr.load_default_parameters()
            self.update_all_param_guis()


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
        meeg_list = SimpleList(self.ct.pr.all_meeg)
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
        meeg = MEEG(meeg_name, self.mw)
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
               '<a href=https://github.com/pyQode/pyQode>pyqode</a><br>' \
               '<br>' \
               '<b>Licensed under:</b><br>' \
               + license_text

        layout = QVBoxLayout()

        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setHtml(text)
        layout.addWidget(text_widget)

        self.setLayout(layout)
        set_ratio_geometry((0.25, self))
        self.open()


