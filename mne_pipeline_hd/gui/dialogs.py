# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
Copyright © 2011-2019, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import shutil
import smtplib
import ssl
import sys
from ast import literal_eval
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial
from os.path import join

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QTextCursor
from PyQt5.QtWidgets import (QApplication, QComboBox, QDesktopWidget, QDialog, QDockWidget, QGridLayout, QHBoxLayout,
                             QInputDialog,
                             QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
                             QPushButton,
                             QScrollArea, QSizePolicy, QStyle, QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.gui_utils import get_ratio_geometry
from mne_pipeline_hd.gui.models import CheckListModel
from mne_pipeline_hd.gui.parameter_widgets import BoolGui, ComboGui, IntGui, StringGui
from mne_pipeline_hd.pipeline_functions import iswin
from mne_pipeline_hd.pipeline_functions.project import Project


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
        self.preset_list = [p for p in self.parent.mw.pr.parameters if p != 'Default']
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
            self.parent.mw.pr.parameters.pop(p_preset)
            self.parent.update_ppreset_cmbx()

        # If current Parameter-Preset was deleted
        if self.parent.mw.pr.p_preset not in self.parent.mw.pr.parameters:
            self.parent.mw.pr.p_preset = list(self.parent.mw.pr.parameters.keys())[0]
            self.parent.update_all_param_guis()

        self.close()


class RemoveProjectsDlg(CheckListDlg):
    def __init__(self, main_win):
        self.mw = main_win
        self.rm_list = []
        super().__init__(main_win, self.mw.projects, self.rm_list)

        self.do_bt.setText('Remove Projects')
        self.do_bt.clicked.connect(self.remove_selected)

        self.open()

    def remove_selected(self):
        for project in self.rm_list:
            self.mw.projects.remove(project)
            self.lm.layoutChanged.emit()

            # Remove Project-Folder
            try:
                shutil.rmtree(join(self.mw.projects_path, project))
            except OSError:
                QMessageBox.critical(self, 'Deletion impossible',
                                     f'The folder of {project} can\'t be deleted and has to be deleted manually')

        # If current project was deleted, load remaining or create New
        if self.mw.current_project not in self.mw.projects:
            self.mw.get_projects()
            self.mw.pr = Project(self.mw, self.mw.current_project)
            self.mw.project_updated()

        self.close()


class SettingsDlg(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(IntGui(self.mw.qsettings, 'n_jobs', min_val=-1, special_value_text='Auto',
                                hint='Set to the amount of cores of your machine '
                                     'you want to use for multiprocessing', default=-1))
        layout.addWidget(BoolGui(self.mw.settings, 'show_plots', param_alias='Show Plots',
                                 hint='Do you want to show plots?\n'
                                      '(or just save them without showing, then just check "Save Plots")',
                                 default=True))
        layout.addWidget(BoolGui(self.mw.settings, 'save_plots', param_alias='Save Plots',
                                 hint='Do you want to save the plots made to a file?', default=True))
        layout.addWidget(BoolGui(self.mw.qsettings, 'enable_cuda', param_alias='Enable CUDA',
                                 hint='Do you want to enable CUDA? (system has to be setup for cuda)',
                                 default=False))
        layout.addWidget(BoolGui(self.mw.settings, 'shutdown', param_alias='Shutdown',
                                 hint='Do you want to shut your system down after execution of all subjects?'))
        layout.addWidget(IntGui(self.mw.settings, 'dpi', min_val=0, max_val=10000,
                                hint='Set dpi for saved plots', default=300))
        layout.addWidget(ComboGui(self.mw.settings, 'img_format', self.mw.available_image_formats,
                                  param_alias='Image-Format', hint='Choose the image format for plots',
                                  default='.png'))
        layout.addWidget(StringGui(self.mw.qsettings, 'fs_path', param_alias='FREESURFER_HOME-Path',
                                   hint='Set the Path to the "freesurfer"-directory of your Freesurfer-Installation '
                                        '(for Windows to the LINUX-Path of the Freesurfer-Installation '
                                        'in Windows-Subsystem for Linux(WSL))',
                                   default=None))
        if iswin:
            layout.addWidget(StringGui(self.mw.qsettings, 'mne_path', param_alias='MNE-Python-Path',
                                       hint='Set the LINUX-Path to the mne-environment (e.g ...anaconda3/envs/mne)'
                                            'in Windows-Subsystem for Linux(WSL))',
                                       default=None))

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)


class ParametersDock(QDockWidget):
    def __init__(self, main_win):
        super().__init__('Parameters', main_win)
        self.mw = main_win
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.main_widget = QWidget()
        self.param_guis = {}

        self.dropgroup_params()
        self.init_ui()

    def dropgroup_params(self):
        # Create a set of all unique parameters used by functions in selected_modules
        sel_pdfuncs = self.mw.pd_funcs.loc[self.mw.pd_funcs['module'].isin(self.mw.get_setting('selected_modules'))]
        # Remove rows with NaN in func_args
        sel_pdfuncs = sel_pdfuncs.loc[sel_pdfuncs['func_args'].notna()]
        all_used_params = ','.join(sel_pdfuncs['func_args']).split(',')
        drop_idx_list = list()
        self.cleaned_pd_params = self.mw.pd_params.copy()
        for param in self.cleaned_pd_params.index:
            if param in all_used_params:
                # Group-Name (if not given, set to 'Various')
                group_name = self.cleaned_pd_params.loc[param, 'group']
                if pd.isna(group_name):
                    self.cleaned_pd_params.loc[param, 'group'] = 'Various'

                # Determine order of groups by main_window.group_order
                if group_name in self.mw.group_order:
                    self.cleaned_pd_params.loc[param, 'group_idx'] = self.mw.group_order[group_name]
                else:
                    self.cleaned_pd_params.loc[param, 'group_idx'] = 100
            else:
                # Drop Parameters which aren't used by functions
                drop_idx_list.append(param)
        self.cleaned_pd_params.drop(index=drop_idx_list, inplace=True)

        # Sort values by group_idx for dramaturgically order
        if 'group_idx' in self.cleaned_pd_params.columns:
            self.cleaned_pd_params.sort_values(by='group_idx', inplace=True)

    def init_ui(self):
        self.general_layout = QVBoxLayout()

        # Add Parameter-Preset-ComboBox
        title_layout = QHBoxLayout()
        p_preset_l = QLabel('Parameter-Presets: ')
        title_layout.addWidget(p_preset_l)
        self.p_preset_cmbx = QComboBox()
        self.p_preset_cmbx.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.p_preset_cmbx.activated.connect(self.p_preset_changed)
        self.update_ppreset_cmbx()
        title_layout.addWidget(self.p_preset_cmbx)

        add_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_bt.clicked.connect(self.add_p_preset)
        title_layout.addWidget(add_bt)

        rm_bt = QPushButton(icon=self.style().standardIcon(QStyle.SP_DialogDiscardButton))
        rm_bt.clicked.connect(partial(RemovePPresetDlg, self))
        title_layout.addWidget(rm_bt)

        title_layout.addStretch(stretch=2)

        reset_bt = QPushButton('Reset')
        reset_bt.clicked.connect(self.reset_parameters)
        title_layout.addWidget(reset_bt)

        self.general_layout.addLayout(title_layout)

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
                if pd.notna(parameter['description']):
                    hint = parameter['description']
                else:
                    hint = ''
                if pd.notna(parameter['unit']):
                    unit = parameter['unit']
                else:
                    unit = None
                try:
                    gui_args = literal_eval(parameter['gui_args'])
                except (SyntaxError, ValueError):
                    gui_args = {}

                gui_handle = getattr(parameter_widgets, gui_name)
                self.param_guis[idx] = gui_handle(self.mw, param_name=idx, param_alias=param_alias,
                                                  hint=hint, param_unit=unit, **gui_args)

                layout.addWidget(self.param_guis[idx])

            child_w.setLayout(layout)
            tab.setWidget(child_w)
            self.tab_param_widget.addTab(tab, group_name)

        # Set Layout of QWidget (the class itself)
        self.general_layout.addWidget(self.tab_param_widget)

    def update_parameters_widget(self):
        self.general_layout.removeWidget(self.tab_param_widget)
        self.tab_param_widget.close()
        del self.tab_param_widget
        self.dropgroup_params()
        self.add_param_guis()

    def p_preset_changed(self, idx):
        self.mw.pr.p_preset = self.p_preset_cmbx.itemText(idx)
        self.update_all_param_guis()

    def update_ppreset_cmbx(self):
        self.p_preset_cmbx.clear()
        for p_preset in self.mw.pr.parameters.keys():
            self.p_preset_cmbx.addItem(p_preset)
        if self.mw.pr.p_preset in self.mw.pr.parameters.keys():
            self.p_preset_cmbx.setCurrentText(self.mw.pr.p_preset)
        else:
            self.p_preset_cmbx.setCurrentText(list(self.mw.pr.parameters.keys())[0])

    def add_p_preset(self):
        preset_name, ok = QInputDialog.getText(self, 'New Parameter-Preset',
                                               'Enter a name for a new Parameter-Preset')
        if ok:
            self.mw.pr.p_preset = preset_name
            self.mw.pr.load_default_parameters()
            self.p_preset_cmbx.addItem(preset_name)
            self.p_preset_cmbx.setCurrentText(preset_name)
        else:
            pass

    def update_all_param_guis(self):
        for gui_name in self.param_guis:
            param_gui = self.param_guis[gui_name]
            param_gui.read_param()
            param_gui.set_param()

    def reset_parameters(self):
        msgbox = QMessageBox.question(self, 'Reset all Parameters?',
                                      'Do you really want to reset all parameters to their default?',
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if msgbox == QMessageBox.Yes:
            self.mw.pr.load_default_parameters()
            self.update_all_param_guis()


class RunDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        width, height = get_ratio_geometry(0.6)
        self.setGeometry(0, 0, width, height)
        self.center()

        self.current_sub = None
        self.current_func = None
        self.prog_running = False

        self.init_ui()
        self.center()

    def init_ui(self):
        self.layout = QGridLayout()

        self.sub_listw = QListWidget()
        self.sub_listw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.layout.addWidget(self.sub_listw, 0, 0)
        self.func_listw = QListWidget()
        self.func_listw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
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
        self.mw.cancel_functions.emit(True)
        self.console_widget.insertHtml('<b><big><center>---Finishing last function...---</center></big></b><br>')
        self.console_widget.ensureCursorVisible()

    def populate(self, mode):
        if mode == 'mri':
            self.populate_listw(self.mw.pr.sel_mri_files, self.mw.sel_mri_funcs)
        elif mode == 'file':
            self.populate_listw(self.mw.pr.sel_files, self.mw.sel_file_funcs)
        elif mode == 'ga':
            self.populate_listw(self.mw.pr.sel_ga_groups, self.mw.sel_ga_funcs)
        elif mode == 'other':
            self.populate_listw(['Other Functions'], self.mw.sel_other_funcs)

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

    def add_text(self, text):
        self.prog_running = False
        self.console_widget.insertPlainText(text)
        self.console_widget.ensureCursorVisible()

    def progress_text(self, text):
        if self.prog_running:
            # Delete last line
            cursor = self.console_widget.textCursor()
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            self.console_widget.insertPlainText(text)

        else:
            self.prog_running = True
            self.console_widget.insertPlainText(text)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def show_errors(self, err):
        ErrorDialog(err, self)
        self.pgbar.setValue(self.mw.all_prog)
        self.close_bt.setEnabled(True)


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
        width, height = get_ratio_geometry(0.4)
        self.resize(int(width), int(height))

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


class ErrorDialog(QDialog):
    def __init__(self, exception_tuple, parent=None, title=None):
        if parent:
            super().__init__(parent)
        else:
            super().__init__()
        self.err = exception_tuple
        self.title = title
        if self.title:
            self.setWindowTitle(self.title)
        else:
            self.setWindowTitle('An Error ocurred!')

        width, height = get_ratio_geometry(0.7)
        self.setGeometry(0, 0, width, height)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.init_ui()

        if parent:
            self.open()
        else:
            self.show()
        self.center()
        self.raise_win()

    def init_ui(self):
        layout = QGridLayout()

        self.label = QLabel()
        self.formated_tb_text = self.err[2].replace('\n', '<br>')
        if self.title:
            self.html_text = f'<h1>{self.title}</h1>' \
                             f'<h2>{self.err[1]}</h2>' \
                             f'{self.formated_tb_text}'
        else:
            self.html_text = f'<h1>{self.err[1]}</h1>' \
                             f'{self.formated_tb_text}'
        self.label.setText(self.html_text)
        layout.addWidget(self.label, 0, 0, 1, 2)

        self.name_le = QLineEdit()
        self.name_le.setPlaceholderText('Enter your Name (optional)')
        layout.addWidget(self.name_le, 1, 0)

        self.email_le = QLineEdit()
        self.email_le.setPlaceholderText('Enter your E-Mail-Adress (optional)')
        layout.addWidget(self.email_le, 1, 1)

        self.send_bt = QPushButton('Send Error-Report')
        self.send_bt.clicked.connect(self.send_report)
        layout.addWidget(self.send_bt, 2, 0)

        self.close_bt = QPushButton('Close')
        self.close_bt.clicked.connect(self.close)
        layout.addWidget(self.close_bt, 2, 1)

        self.setLayout(layout)

        self.desk_geometry = QApplication.instance().desktop().availableGeometry()
        self.size_ratio = 0.7
        height = int(self.desk_geometry.height() * self.size_ratio)
        width = int(self.desk_geometry.width() * self.size_ratio)
        self.setMaximumSize(width, height)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def raise_win(self):
        if sys.platform == 'win32':
            # on windows we can raise the window by minimizing and restoring
            self.showMinimized()
            self.setWindowState(Qt.WindowActive)
            self.showNormal()
        else:
            # on osx we can raise the window. on unity the icon in the tray will just flash.
            self.activateWindow()
            self.raise_()

    # Todo: Rework with Token
    def send_report(self):
        msg_box = QMessageBox.question(self, 'Send an E-Mail-Bug-Report?',
                                       'Do you really want to send an E-Mail-Report?',
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if msg_box == QMessageBox.Yes:
            port = 465
            adress = 'mne.pipeline@gmail.com'
            password = '24DecodetheBrain7!'

            context = ssl.create_default_context()

            message = MIMEMultipart("alternative")
            message['Subject'] = str(self.err[1])
            message['From'] = adress
            message["To"] = adress

            message_body = MIMEText(f'<b><big>{self.name_le.text()}</b></big><br>'
                                    f'<i>{self.email_le.text()}</i><br><br>'
                                    f'<b>{sys.platform}</b><br>{self.formated_tb_text}', 'html')
            message.attach(message_body)
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', port, context=context) as server:
                    server.login('mne.pipeline@gmail.com', password)
                    server.sendmail(adress, adress, message.as_string())
                QMessageBox.information(self, 'E-Mail sent', 'An E-Mail was sent to mne.pipeline@gmail.com\n'
                                                             'Thank you for the Report!')
            except OSError:
                QMessageBox.information(self, 'E-Mail not sent', 'Sending an E-Mail is not possible on your OS')
