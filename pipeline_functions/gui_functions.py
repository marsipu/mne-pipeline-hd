import sys
import os
from functools import partial
from os import makedirs, listdir
from os.path import join, isdir, exists

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import (QWidget, QToolTip, QPushButton, QApplication, QMainWindow, QToolBar,
                             QStatusBar, QInputDialog, QFileDialog, QLabel, QGridLayout, QDesktopWidget, QVBoxLayout,
                             QHBoxLayout, QAction, QMenu, QActionGroup, QWidgetAction, QLineEdit, QDialog, QListWidget)
from PyQt5.QtCore import Qt, QSettings
from . import operations_dict as opd
from . import utilities as ut
from . import subject_organisation as suborg


def bt_read(path):
    try:
        with open(path, 'r') as rl:
            print(rl.read())
    except FileNotFoundError:
        print('mri_sub_list.py not yet created, run add_mri_subjects')


def bt_delet_last(path):
    with open(path, 'r') as dl:
        dlist = (dl.readlines())

    with open(path, 'w') as dl:
        for listitem in dlist[:-1]:
            dl.write('%s' % listitem)


def bt_assign():
    pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.app.setApplicationName('mne_pipeline_hd')
        self.app.setOrganizationName('marsipu')
        self.settings = QSettings()

        self.setWindowTitle('MNE-Pipeline HD')
        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self.general_layout = QVBoxLayout()
        self._centralWidget.setLayout(self.general_layout)

        # Attributes for methods
        self.actions = dict()
        self.func_dict = dict()
        self.bt_dict = dict()
        self.make_it_stop = False
        self.lines = dict()
        self.texts = ['which_file', 'quality', 'modality', 'which_mri_subject', 'which_erm_file',
                      'which_motor_erm_file']

        self.pipeline_path = ut.get_pipeline_path(os.getcwd())
        self.cache_path = join(join(self.pipeline_path, '_pipeline_cache'))
        self.platform = sys.platform
        if not exists(join(self.pipeline_path, '_pipeline_cache')):
            makedirs(join(self.pipeline_path, '_pipeline_cache'))
        # Get home_path
        if not exists(join(self.cache_path, 'paths.py')):
            hp = QFileDialog.getExistingDirectory(self, 'Select a folder to store your Pipeline-Projects')
            if hp == '':
                raise RuntimeError('You canceled an important step, start over')
            else:
                self.home_path = str(hp)
                ut.dict_filehandler(self.platform, 'paths', self.cache_path, self.home_path, silent=True)
        else:
            path_dict = ut.read_dict_file('paths', self.cache_path)
            if self.platform in path_dict:
                self.home_path = path_dict[self.platform]
            else:
                hp = QFileDialog.getExistingDirectory(self,
                                                      'New OS: Select the folder where you store your Pipeline-Projects')
                if hp == '':
                    raise RuntimeError('You canceled an important step, start over')
                else:
                    self.home_path = str(hp)
                    ut.dict_filehandler(self.platform, 'paths', self.cache_path, self.home_path, silent=True)
        # Todo: Store evererything in QSettings
        # Get project_name
        if not exists(join(self.cache_path, 'win_cache.py')):
            self.project_name, ok = QInputDialog().getText(self, 'Project-Selection',
                                                           'Enter a project-name for your first project')
            ut.dict_filehandler('project', 'win_cache', self.cache_path, self.project_name, silent=True)
        else:
            self.project_name = ut.read_dict_file('win_cache', self.cache_path)['project']

        # Call methods
        self.create_menu()
        self.subject_selection()
        self.make_func_bts()
        self.add_main_bts()
        self.center()

        self.which_file = self.lines['which_file'].text()
        self.quality = self.lines['quality'].text()
        self.modality = self.lines['modality'].text()
        self.which_mri_subject = self.lines['which_mri_subject'].text()
        self.which_erm_file = self.lines['which_erm_file'].text()
        self.which_motor_erm_file = self.lines['which_motor_erm_file'].text()

    # Todo Mac-Bug Menu not selectable
    def create_menu(self):
        # Project
        project_menu = QMenu('Project')
        project_group = QActionGroup(project_menu)
        try:
            projects = [p for p in os.listdir(self.home_path) if isdir(join(self.home_path, p, 'Daten'))]
        except FileNotFoundError:
            print(f'{self.home_path} can not be found, choose another one!')
            hp = QFileDialog.getExistingDirectory(self, 'Select a folder to store your Pipeline-Projects')
            if hp == '':
                raise RuntimeError('You canceled an important step, start over')
            else:
                self.home_path = str(hp)
                ut.dict_filehandler(self.platform, 'paths', self.cache_path, self.home_path, silent=True)
            projects = [p for p in os.listdir(self.home_path) if isdir(join(self.home_path, p, 'Daten'))]
        if len(projects) == 0:
            self.project_name, ok = QInputDialog.getText(self, 'Project-Selection',
                                                         'Enter a project-name for your first project')
            if ok:
                projects.append(self.project_name)
                makedirs(join(self.home_path, self.project_name))
            else:
                # Problem in Python Console, QInputDialog somehow stays in memory
                raise RuntimeError('You canceled an important step, start over')
        for project in projects:
            action = QAction(project, project_menu)
            action.setCheckable(True)
            action.triggered.connect(partial(self.change_project, project))
            self.actions[project] = action
            project_menu.addAction(action)
            project_group.addAction(action)
        project_group.setExclusive(True)
        # Toggle project from win_cache
        if self.project_name in projects:
            self.actions[self.project_name].toggle()
        else:
            self.actions[projects[0]].toggle()
            self.project_name = projects[0]
            ut.dict_filehandler('project', 'win_cache', self.cache_path, self.project_name, silent=True)
        self.menuBar().addMenu(project_menu)

        project_menu.addSeparator()
        self.actions['Add_Project'] = project_menu.addAction('Add Project',
                                                             partial(self.add_project, project_menu, project_group))
        # Input
        input_menu = self.menuBar().addMenu('Input')
        project_path = join(self.home_path, self.project_name)
        orig_data_path = join(project_path, 'meg')
        data_path = join(project_path, 'Daten')
        subjects_dir = join(self.home_path, 'Freesurfer/Output')
        pscripts_path = join(project_path, '_pipeline_scripts')
        file_list_path = join(pscripts_path, 'file_list.py')
        erm_list_path = join(pscripts_path, 'erm_list.py')
        motor_erm_list_path = join(pscripts_path, 'motor_erm_list.py')
        mri_sub_list_path = join(pscripts_path, 'mri_sub_list.py')
        self.actions['add_subject'] = input_menu.addAction('Add Files', partial(suborg.add_files, file_list_path,
                                                                                erm_list_path, motor_erm_list_path,
                                                                                data_path, orig_data_path))
        self.actions['add_mri_subject'] = input_menu.addAction('Add MRI-Subject',
                                                               partial(suborg.add_mri_subjects, subjects_dir,
                                                                       mri_sub_list_path, data_path))
        self.actions['add_sub_dict'] = input_menu.addAction('Assign File --> MRI-Subject',
                                                            partial(self.add_sub_dict, file_list_path,
                                                                    mri_sub_list_path))

        # Setting
        setting_menu = self.menuBar().addMenu('Settings')
        self.actions['Dark-Mode'] = setting_menu.addAction('Dark-Mode', self.dark_mode)
        self.actions['Dark-Mode'].setCheckable(True)
        self.actions['Full-Screen'] = setting_menu.addAction('Full-Screen', self.full_screen)
        self.actions['Full-Screen'].setCheckable(True)
        self.actions['Change_Home-Path'] = setting_menu.addAction('Change Home-Path', self.change_home_path)

        # Todo: Save Widget-State
        # stat_dict = ut.read_dict_file('win_cache', self.cache_path)
        # for act in self.actions:
        #     if act in stat_dict:
        #         if stat_dict[act]:
        #             self.actions[act].setChecked()

    def change_project(self, project):
        self.project_name = project
        ut.dict_filehandler('project', 'win_cache', self.cache_path, project, silent=True)

    def add_project(self, project_menu, project_group):
        project, ok = QInputDialog.getText(self, 'Project-Selection',
                                           'Enter a project-name for a new project')
        if ok:
            self.project_name = project
            new_action = QAction(project)
            new_action.setCheckable(True)
            new_action.triggered.connect(partial(self.change_project, project))
            project_group.addAction(new_action)
            new_action.toggle()
            project_menu.insertAction(self.actions['Add_Project'], new_action)
            project_menu.update()
        else:
            pass
        # project_menu.clear()
        # project_menu.addActions(project_group.actions())
        # project_menu.addSeparator()
        # self.actions['Add_Project'] = project_menu.addAction('Add Project',
        #                                                      partial(self.add_project, project_menu, project_group))
        # project_menu.update()

    def add_sub_dict(self, file_list_path, mri_sub_list_path):
        dlg = QDialog(self)
        layout = QHBoxLayout()
        list_widget1 = QListWidget()
        list_widget2 = QListWidget()
        with open(file_list_path, 'r') as sl:
            for idx, line in enumerate(sl):
                list_widget1.insertItem(idx, line[:-1])
        with open(mri_sub_list_path, 'r') as msl:
            for idx, line in enumerate(msl):
                list_widget2.insertItem(idx, line[:-1])
        layout.addWidget(list_widget1)
        layout.addWidget(list_widget2)
        bt_layout = QVBoxLayout()
        assign_bt = QPushButton()
        assign_bt.clicked.connect(bt_assign)
        read_bt = QPushButton()
        read_bt.clicked.connect(partial(bt_read, mri_sub_list_path))
        bt_layout.addWidget(read_bt)
        delete_bt = QPushButton()
        delete_bt.clicked.connect(partial(bt_delet_last, mri_sub_list_path))
        bt_layout.addWidget(delete_bt)
        layout.addLayout(bt_layout)
        dlg.setLayout(layout)
        dlg.exec_()

    # Todo: Fix Dark-Mode
    def dark_mode(self):
        if self.actions['Dark-Mode'].isChecked():
            dark_palette = QPalette()
            dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.WindowText, Qt.white)
            dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
            dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
            dark_palette.setColor(QPalette.ToolTipText, Qt.white)
            dark_palette.setColor(QPalette.Text, Qt.white)
            dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ButtonText, Qt.white)
            dark_palette.setColor(QPalette.BrightText, Qt.red)
            dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.HighlightedText, Qt.black)
            self.app.setPalette(dark_palette)
            self.app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")
        else:
            white_palette = QPalette()
            white_palette.setColor(QPalette.Window, QColor(255, 255, 255))
            white_palette.setColor(QPalette.WindowText, Qt.black)
            white_palette.setColor(QPalette.Base, QColor(255, 255, 255))
            white_palette.setColor(QPalette.AlternateBase, QColor(255, 255, 255))
            white_palette.setColor(QPalette.ToolTipBase, Qt.black)
            white_palette.setColor(QPalette.ToolTipText, Qt.black)
            white_palette.setColor(QPalette.Text, Qt.black)
            white_palette.setColor(QPalette.Button, QColor(255, 255, 255))
            white_palette.setColor(QPalette.ButtonText, Qt.black)
            white_palette.setColor(QPalette.BrightText, Qt.red)
            white_palette.setColor(QPalette.Link, QColor(42, 130, 218))
            white_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            white_palette.setColor(QPalette.HighlightedText, Qt.white)
            self.app.setPalette(white_palette)
            self.app.setStyleSheet("QToolTip { color: #000000; background-color: #2a82da; border: 1px solid black; }")

    def full_screen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def change_home_path(self):
        self.home_path = str(
            QFileDialog.getExistingDirectory(self, 'Change folder to store your Pipeline-Projects'))
        ut.dict_filehandler(self.platform, 'paths', self.cache_path, self.home_path, silent=True)
        self.project_name = None
        self.menuBar().clear()
        self.create_menu()
        self.update()
        ut.dict_filehandler('project', 'win_cache', self.cache_path, self.project_name, silent=True)

    # # Todo: Make Center work, frameGeometry doesn't give the actual geometry after make_func_bts
    def center(self):
        # qr = self.frameGeometry()
        # print(qr)
        # cp = QDesktopWidget().availableGeometry().center()
        # qr.moveCenter(cp)
        # self.move(qr.topLeft())
        pass
        # self.move(QApplication.desktop().screen().rect().center() - self.rect().center())
        # print(f'Destop-Center: {QApplication.desktop().screen().rect().center()}, Window-Center: {self.rect().center()}'
        #       f', Difference: {QApplication.desktop().screen().rect().center() - self.rect().center()}')
        # print(self._centralWidget.geometry())
        # self.updateGeometry()
        # print(self._centralWidget.geometry())

    def subject_selection(self):
        stat_dict = ut.read_dict_file('win_cache', self.cache_path)
        subsel_layout = QHBoxLayout()

        for t in self.texts:
            self.lines[t] = QLineEdit()
            self.lines[t].setPlaceholderText(t)
            self.lines[t].textChanged.connect(partial(self.update_subsel, t))
            subsel_layout.addWidget(self.lines[t])
            if t in stat_dict:
                self.lines[t].setText(stat_dict[t])

        self.general_layout.addLayout(subsel_layout)

    def update_subsel(self, t):
        setattr(self, t, self.lines[t].text())
        # self.which_file = self.lines['which_file'].text()
        # self.quality = self.lines['quality'].text()
        # self.modality = self.lines['modality'].text()
        # self.which_mri_subject = self.lines['which_mri_subject'].text()
        # self.which_erm_file = self.lines['which_erm_file'].text()
        # self.which_motor_erm_file = self.lines['which_motor_erm_file'].text()

    # Todo: Make Buttons more appealing
    def make_func_bts(self):
        r_cnt = 0
        c_cnt = 0
        r_max = 25
        func_layout = QGridLayout()

        for f, v in opd.all_fs.items():
            self.func_dict.update({f: v})

        pre_func_dict = self.settings.value('func_checked')
        del_list = []
        if pre_func_dict is not None:
            for k in pre_func_dict:
                if k not in opd.all_fs:
                    del_list.append(k)
            if len(del_list) > 0:
                for d in del_list:
                    del pre_func_dict[d]
                    print(f'{d} from func_cache deleted')

            # Default selection from opd overwrites cache
            for f in self.func_dict:
                if f in pre_func_dict:
                    if not self.func_dict[f]:
                        self.func_dict[f] = pre_func_dict[f]

        for function_group in opd.all_fs_gs:
            if r_cnt > 25:
                r_cnt = 0
            label = QLabel(function_group, self)
            func_layout.addWidget(label, r_cnt, c_cnt)
            r_cnt += 1
            for function in opd.all_fs_gs[function_group]:
                pb = QPushButton(function, self)
                pb.setCheckable(True)
                self.bt_dict[function] = pb
                if self.func_dict[function]:
                    pb.setChecked(True)
                    self.func_dict[function] = 1
                pb.toggled.connect(partial(self.select_func, function))
                func_layout.addWidget(pb, r_cnt, c_cnt)
                r_cnt += 1
                if r_cnt >= r_max:
                    c_cnt += 1
                    r_cnt = 0
        self.general_layout.addLayout(func_layout)

    def select_func(self, function):
        if self.bt_dict[function].isChecked():
            self.func_dict[function] = 1
            print(f'{function} selected')
        else:
            print(f'{function} deselected')
            self.func_dict[function] = 0

    def add_main_bts(self):
        main_bt_layout = QHBoxLayout()
        clear_bt = QPushButton('Clear', self)
        start_bt = QPushButton('Start', self)
        stop_bt = QPushButton('Stop', self)

        main_bt_layout.addWidget(clear_bt)
        main_bt_layout.addWidget(start_bt)
        main_bt_layout.addWidget(stop_bt)

        clear_bt.clicked.connect(self.clear)
        start_bt.clicked.connect(self.start)
        stop_bt.clicked.connect(self.stop)

        self.general_layout.addLayout(main_bt_layout)

    def clear(self):
        for x in self.bt_dict:
            self.bt_dict[x].setChecked(False)
            self.func_dict[x] = 0

    def start(self):
        self.close()

    def stop(self):
        self.close()
        self.make_it_stop = True

    def closeEvent(self, event):
        self.settings.setValue('func_checked', self.func_dict)
        for ln in self.lines:

            ut.dict_filehandler(ln, 'win_cache', self.cache_path, self.lines[ln].text(), silent=True)
        # for act in self.actions:
        #     if self.actions[act].checked():
        #         ut.dict_filehandler(act, 'win_cache', self.cache_path, 1, silent=True)

        event.accept()


# for testing
if __name__ == '__main__':
    def run_main_gui():
        app = QApplication(sys.argv)
        win = MainWindow()
        win.show()
        # for Spyder, when exit-button only closes Main-Widget
        # app.lastWindowClosed.connect(app.quit)
        app.exec_()
        # win.close()
        home_path = win.home_path
        project_name = win.project_name
        exec_ops = win.func_dict
        make_it_stop = win.make_it_stop
        # del app, win, MainWindow
        if make_it_stop:
            raise SystemExit(0)
    # sys.exit(app.exec_())
    # Proper way would be sys.exit(app.exec_()), but this ends the console with exit code 0
    # This is the way, when FunctionWindow acts as main window for the Pipeline and all functions
    # are executed within. Need to resolve plot-problem (memory error 1073741819 (0xC0000005)) before
