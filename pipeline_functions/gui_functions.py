import sys
import os
from functools import partial
from os import makedirs, listdir
from os.path import join, isfile, isdir, exists

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import (QWidget, QToolTip, QPushButton, QApplication, QMainWindow, QToolBar,
                             QStatusBar, QInputDialog, QFileDialog, QLabel, QGridLayout, QDesktopWidget, QVBoxLayout,
                             QHBoxLayout, QAction, QMenu, QActionGroup, QWidgetAction, QLineEdit, QDialog, QListWidget,
                             QMessageBox)
from PyQt5.QtCore import Qt, QSettings

try:
    from . import operations_dict as opd
    from . import utilities as ut
    from . import subject_organisation as suborg
    from . import io_functions as io
except ImportError:
    from pipeline_functions import operations_dict as opd
    from pipeline_functions import utilities as ut
    from pipeline_functions import subject_organisation as suborg
    from pipeline_functions import io_functions as io


def selectedlistitem(inst1, inst2, dict_path):
    choice = inst1.currentItem().text()
    existing_dict = suborg.read_sub_dict(dict_path)
    if choice in existing_dict:
        it2 = inst2.findItems(existing_dict[choice], Qt.MatchExactly)[0]
        inst2.setCurrentItem(it2)


def assign(dict_path, list_widget1, list_widget2):
    choice1 = list_widget1.currentItem().text()
    choice2 = list_widget2.currentItem().text()
    if not isfile(dict_path):
        with open(dict_path, 'w') as sd:
            sd.write(f'{choice1}:{choice2}\n')
        print(f'{dict_path} created')

    else:
        existing_dict = suborg.read_sub_dict(dict_path)
        if choice1 in existing_dict:
            existing_dict[choice1] = choice2
        else:
            existing_dict.update({choice1: choice2})
        with open(dict_path, 'w') as sd:
            for key, value in existing_dict.items():
                sd.write(f'{key}:{value}\n')


def assign_none(dict_path, list_widget1):
    choice = list_widget1.currentItem().text()
    if not isfile(dict_path):
        with open(dict_path, 'w') as sd:
            sd.write(f'{choice}:None\n')
        print(f'{dict_path} created')

    else:
        existing_dict = suborg.read_sub_dict(dict_path)
        if choice in existing_dict:
            existing_dict[choice] = None
        else:
            existing_dict.update({choice: None})
        with open(dict_path, 'w') as sd:
            for key, value in existing_dict.items():
                sd.write(f'{key}:{value}\n')


def assign_all_none(inst, dict_path, list_widget1):
    reply = QMessageBox.question(inst, 'Assign None to All?', 'Do you really want to assign none to all?',
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        all_items = dict()
        for i in range(list_widget1.count()):
            all_items.update({list_widget1.item(i).text(): None})
        if not isfile(dict_path):
            with open(dict_path, 'w') as sd:
                for key, value in all_items.items():
                    sd.write(f'{key}:{value}\n')
        else:
            with open(dict_path, 'w') as sd:
                for key, value in all_items.items():
                    sd.write(f'{key}:{value}\n')
    else:
        print('Puh, pig haved')


def delete_last(dict_path):
    with open(dict_path, 'r') as dl:
        dlist = (dl.readlines())

    with open(dict_path, 'w') as dl:
        for listitem in dlist[:-1]:
            dl.write(str(listitem))


def read(dict_path):
    try:
        with open(dict_path, 'r') as rl:
            print(rl.read())
    except FileNotFoundError:
        print('file not yet created, assign some files')


# General Function for Assignment of MRI-Subject and ERM-File
class SubDictDialog(QDialog):
    def __init__(self, main_win, mode):
        super().__init__(main_win)
        self.main_win = main_win
        self.layout = QGridLayout()
        self.mode = mode
        if mode == 'mri':
            self.setWindowTitle('Assign files to their MRI-Subject')
            self.path2 = main_win.mri_sub_list_path
            self.dict_path = main_win.sub_dict_path
            self.label2 = 'Choose a mri-subject'
        elif mode == 'erm':
            self.setWindowTitle('Assign files to their ERM-File')
            self.path2 = main_win.erm_list_path
            self.dict_path = main_win.erm_dict_path
            self.label2 = 'Choose a erm-file'

        self.init_ui()
        self.show()
        self.activateWindow()
        self.exec_()

    def init_ui(self):
        file_label = QLabel('Choose a file', self)
        second_label = QLabel(self.label2, self)

        self.layout.addWidget(file_label, 0, 0)
        self.layout.addWidget(second_label, 0, 1)
        # ListWidgets
        list_widget1 = QListWidget(self)
        list_widget2 = QListWidget(self)
        with open(self.main_win.file_list_path, 'r') as sl:
            for idx, line in enumerate(sl):
                list_widget1.insertItem(idx, line[:-1])
        with open(self.path2, 'r') as msl:
            for idx, line in enumerate(msl):
                list_widget2.insertItem(idx, line[:-1])

        # Response to Clicking
        list_widget1.itemClicked.connect(partial(selectedlistitem, list_widget1, list_widget2, self.dict_path))

        self.layout.addWidget(list_widget1, 1, 0)
        self.layout.addWidget(list_widget2, 1, 1)
        # Add buttons
        bt_layout = QVBoxLayout()
        assign_bt = QPushButton('Assign', self)
        assign_bt.clicked.connect(partial(assign, self.dict_path, list_widget1, list_widget2))
        bt_layout.addWidget(assign_bt)

        none_bt = QPushButton('Assign None')
        none_bt.clicked.connect(partial(assign_none, self.dict_path, list_widget1))
        bt_layout.addWidget(none_bt)

        all_none_bt = QPushButton('Assign None to all')
        all_none_bt.clicked.connect(partial(assign_all_none, self, self.dict_path, list_widget1))
        bt_layout.addWidget(all_none_bt)

        read_bt = QPushButton('Read', self)
        read_bt.clicked.connect(partial(read, self.dict_path))
        bt_layout.addWidget(read_bt)

        delete_bt = QPushButton('Delete Last', self)
        delete_bt.clicked.connect(partial(delete_last, self.dict_path))
        bt_layout.addWidget(delete_bt)

        ok_bt = QPushButton('OK', self)
        ok_bt.clicked.connect(self.close)
        bt_layout.addWidget(ok_bt)

        self.layout.addLayout(bt_layout, 0, 2, 2, 1)
        self.setLayout(self.layout)


class BadChannelsSelect(QDialog):
    def __init__(self, parent):
        super().__init__(parent)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.settings = QSettings()

        self.setWindowTitle('MNE-Pipeline HD')
        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self.general_layout = QVBoxLayout()
        self._centralWidget.setLayout(self.general_layout)

        # Attributes for class-methods
        self.actions = dict()
        self.func_dict = dict()
        self.bt_dict = dict()
        self.make_it_stop = False
        self.lines = dict()
        self.texts = ['which_file', 'quality', 'modality', 'which_mri_subject', 'which_erm_file',
                      'which_motor_erm_file']

        # Pipeline-Paths
        self.pipeline_path = ut.get_pipeline_path(os.getcwd())
        self.cache_path = join(join(self.pipeline_path, '_pipeline_cache'))
        self.platform = sys.platform
        if not exists(join(self.pipeline_path, '_pipeline_cache')):
            makedirs(join(self.pipeline_path, '_pipeline_cache'))

        # Get home_path
        if not exists(join(self.cache_path, 'paths.py')):
            hp = QFileDialog.getExistingDirectory(self, 'Select a folder to store your Pipeline-Projects')
            if hp == '':
                self.close()
                raise RuntimeError('You canceled an important step, start over')
            else:
                self.home_path = str(hp)
                ut.dict_filehandler(self.platform, 'paths', self.cache_path, self.home_path, silent=True)
        else:
            path_dict = ut.read_dict_file('paths', self.cache_path)
            if self.platform in path_dict:
                self.home_path = path_dict[self.platform]
            else:
                hp = QFileDialog.getExistingDirectory(self, 'New OS: Select the folder where '
                                                            'you store your Pipeline-Projects')
                if hp == '':
                    self.close()
                    raise RuntimeError('You canceled an important step, start over')
                else:
                    self.home_path = str(hp)
                    ut.dict_filehandler(self.platform, 'paths', self.cache_path, self.home_path, silent=True)
        # Todo: Store everything in QSettings, make reading of project_name more reliable concerning existing projects
        # Get project_name
        if not exists(join(self.cache_path, 'win_cache.py')):
            self.project_name, ok = QInputDialog().getText(self, 'Project-Selection',
                                                           'Enter a project-name for your first project')
            ut.dict_filehandler('project', 'win_cache', self.cache_path, self.project_name, silent=True)
        else:
            self.project_name = ut.read_dict_file('win_cache', self.cache_path)['project']

        # Initiate other paths
        self.project_path = join(self.home_path, self.project_name)
        self.orig_data_path = join(self.project_path, 'meg')
        self.data_path = join(self.project_path, 'Daten')
        self.subjects_dir = join(self.home_path, 'Freesurfer')
        self.pscripts_path = join(self.project_path, '_pipeline_scripts')
        self.file_list_path = join(self.pscripts_path, 'file_list.py')
        self.erm_list_path = join(self.pscripts_path, 'erm_list.py')
        self.motor_erm_list_path = join(self.pscripts_path, 'motor_erm_list.py')
        self.mri_sub_list_path = join(self.pscripts_path, 'mri_sub_list.py')
        self.sub_dict_path = join(self.pscripts_path, 'sub_dict.py')
        self.erm_dict_path = join(self.pscripts_path, 'erm_dict.py')
        self.bad_channels_dict_path = join(self.pscripts_path, 'bad_channels_dict.py')
        self.quality_dict_path = join(self.pscripts_path, 'quality.py')

        path_lists = [self.subjects_dir, self.orig_data_path, self.data_path, self.pscripts_path]
        file_lists = [self.file_list_path, self.erm_list_path, self.motor_erm_list_path, self.mri_sub_list_path,
                      self.sub_dict_path, self.erm_dict_path, self.bad_channels_dict_path, self.quality_dict_path]

        for path in path_lists:
            if not exists(path):
                os.makedirs(path)
                print(f'{path} created')

        for file in file_lists:
            if not isfile(file):
                with open(file, 'w') as fl:
                    fl.write('')
                print(f'{file} created')

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
                self.close()
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
                self.close()
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

        self.actions['Add_Project'] = project_menu.addAction('Add Project',
                                                             partial(self.add_project, project_menu, project_group))
        # Todo: Separator Issue
        # project_menu.insertSeparator(self.actions['Add_Project'])
        # Input
        input_menu = self.menuBar().addMenu('Input')

        self.actions['add_subject'] = input_menu.addAction('Add Files', partial(suborg.add_files, self.file_list_path,
                                                                                self.erm_list_path,
                                                                                self.motor_erm_list_path,
                                                                                self.data_path, self.orig_data_path))
        self.actions['add_mri_subject'] = input_menu.addAction('Add MRI-Subject',
                                                               partial(suborg.add_mri_subjects, self.subjects_dir,
                                                                       self.mri_sub_list_path, self.data_path))
        self.actions['add_sub_dict'] = input_menu.addAction('Assign File --> MRI-Subject',
                                                            partial(SubDictDialog, self, 'mri'))
        self.actions['add_erm_dict'] = input_menu.addAction('Assign File --> ERM-File',
                                                            partial(SubDictDialog, self, 'erm'))

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
        self.__init__()

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
            new_action.trigger()
            project_menu.insertAction(self.actions['Add_Project'], new_action)
            project_menu.update()
        else:
            pass

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
        new_home_path = str(
            QFileDialog.getExistingDirectory(self, 'Change folder to store your Pipeline-Projects'))
        if new_home_path is not None:
            self.home_path = new_home_path
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
        # print(f'Destop-Center: {QApplication.desktop().screen().rect().center()},
        #       f'Window-Center: {self.rect().center()}'
        #       f', Difference: {QApplication.desktop().screen().rect().center() - self.rect().center()}')
        # print(self._centralWidget.geometry())
        # self.updateGeometry()
        # print(self._centralWidget.geometry())

    def subject_selection(self):
        stat_dict = ut.read_dict_file('win_cache', self.cache_path)
        subsel_layout = QHBoxLayout()
        # Todo: Default Selection for Lines, Tooltips for explanation, GUI-Button
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
        # start_bt.clicked.connect(self.start)
        start_bt.clicked.connect(plot_test)
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


def plot_test():
    name = 'pp1a_256_b'
    save_dir = 'Z:/Promotion\Pin-Prick-Projekt\Daten\pp1a_256_b'
    r = io.read_raw(name, save_dir)
    r.plot()


# for testing
if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    # not working in PyCharm, needed for Spyder
    # app.lastWindowClosed.connect(app.quit)
    app.exec_()
    # win.close()
    make_it_stop = win.make_it_stop
    del app, win
    if make_it_stop:
        raise SystemExit(0)
    # sys.exit(app.exec_())
    # Proper way would be sys.exit(app.exec_()), but this ends the console with exit code 0
    # This is the way, when FunctionWindow acts as main window for the Pipeline and all functions
    # are executed within. Need to resolve plot-problem (memory error 1073741819 (0xC0000005)) before
