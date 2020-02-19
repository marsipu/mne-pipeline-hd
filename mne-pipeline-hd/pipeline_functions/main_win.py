import shutil
import sys
from functools import partial
from os.path import join
from subprocess import run

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import (QAction, QApplication, QComboBox, QDesktopWidget, QDialog, QFileDialog, QGridLayout,
                             QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                             QPushButton, QStyleFactory, QTabWidget, QToolTip, QVBoxLayout, QWidget)

from pipeline_functions import function_call as fc, iswin
from pipeline_functions.project import MyProject
from pipeline_functions.subjects import AddFiles, AddMRIFiles, BadChannelsSelect, SubDictDialog, SubjectDock
from resources import operations_dict as opd


def get_upstream():
    """
    Get and merge the upstream branch from a repository (e.g. developement-branch of mne-pyhon)
    :return: None
    """
    if iswin:
        command = "git fetch upstream & git checkout master & git merge upstream/master"
    else:
        command = "git fetch upstream; git checkout master; git merge upstream/master"
    result = run(command)
    print(result.stdout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.settings = QSettings()

        self.app.setFont(QFont('Calibri', 10))
        self.setWindowTitle('MNE-Pipeline HD')
        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self.general_layout = QGridLayout()
        self.centralWidget().setLayout(self.general_layout)
        QToolTip.setFont(QFont('SansSerif', 9))

        # # Workaround for MAC menu-bar-focusing issue
        # self.menuBar().setNativeMenuBar(False)

        # Attributes for class-methods
        self.func_dict = dict()
        self.bt_dict = dict()
        self.make_it_stop = False
        self.project_box = None

        # Call project-class
        self.pr = MyProject(self)

        # Call window-methods
        self.make_menu()
        self.make_toolbar()
        self.make_statusbar()
        self.add_dock_windows()
        self.project_tools()
        self.make_func_bts()
        self.add_main_bts()
        self.change_style('Fusion')

        # Center Window
        # Necessary because frameGeometry is dependent on number of function-buttons
        newh = self.sizeHint().height()
        neww = self.sizeHint().width()
        self.setGeometry(0, 0, neww, newh)

        # Causes almost full-screen on mac
        # if 'darwin' in self.platform:
        #     self.setGeometry(0, 0, self.width() * self.devicePixelRatio(), self.height() * self.devicePixelRatio())

        # This is also possible but does not center a widget with height < 480
        # self.layout().update()
        # self.layout().activate()
        self.center()
        self.raise_win()

    def make_menu(self):
        # & in front of text-string creates automatically a shortcut with Alt + <letter after &>
        # Input
        input_menu = self.menuBar().addMenu('&Input')

        # aaddfiles = QAction('Add Files', self)
        aaddfiles = QAction('Add Files', parent=self)
        aaddfiles.setShortcut('Ctrl+F')
        aaddfiles.setStatusTip('Add your MEG-Files here')
        aaddfiles.triggered.connect(partial(AddFiles, self))
        input_menu.addAction(aaddfiles)

        aaddmri = QAction('Add MRI-Subject', self)
        aaddmri.setShortcut('Ctrl+M')
        aaddmri.setStatusTip('Add your Freesurfer-Files here')
        aaddmri.triggered.connect(partial(AddMRIFiles, self))
        input_menu.addAction(aaddmri)

        input_menu.addAction('Assign File --> MRI-Subject',
                             partial(SubDictDialog, self, 'mri'))
        input_menu.addAction('Assign File --> ERM-File',
                             partial(SubDictDialog, self, 'erm'))
        input_menu.addAction('Assign Bad-Channels --> File',
                             partial(BadChannelsSelect, self))

        # View
        self.view_menu = self.menuBar().addMenu('&View')

        # Settings
        self.settings_menu = self.menuBar().addMenu('&Settings')
        self.adark_mode = self.settings_menu.addAction('&Dark-Mode', self.dark_mode)
        self.adark_mode.setCheckable(True)
        self.settings_menu.addAction('&Full-Screen', self.full_screen).setCheckable(True)
        self.settings_menu.addAction('&Change Home-Path', self.change_home_path)

        # About
        about_menu = self.menuBar().addMenu('About')
        about_menu.addAction('Update Pipeline', self.update_pipeline)
        about_menu.addAction('Update MNE-Python', self.update_mne)
        about_menu.addAction('About QT', self.about_qt)

    def make_toolbar(self):
        self.toolbar = self.addToolBar('Tools')

    def make_statusbar(self):
        self.statusBar().showMessage('Ready')

    def add_dock_windows(self):
        self.subject_dock = SubjectDock(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.subject_dock)
        self.view_menu.addAction(self.subject_dock.toggleViewAction())

    def change_home_path(self):
        new_home_path = QFileDialog.getExistingDirectory(self, 'Change folder to store your Pipeline-Projects')
        if new_home_path is '':
            pass
        else:
            self.pr.home_path = new_home_path
            self.settings.setValue('home_path', self.pr.home_path)
            self.pr.get_paths()
            self.update_project_box()

    def add_project(self):
        project, ok = QInputDialog.getText(self, 'Project-Selection',
                                           'Enter a project-name for a new project')
        if ok:
            self.pr.project_name = project
            self.pr.projects.append(project)
            self.settings.setValue('project_name', self.pr.project_name)
            self.project_box.addItem(project)
            self.project_box.setCurrentText(project)
            self.pr.make_paths()
        else:
            pass

    def remove_project(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Remove Project')
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Select Project for Removal'))

        plistw = QListWidget(self)
        for project in self.pr.projects:
            item = QListWidgetItem(project)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            plistw.addItem(item)
        layout.addWidget(plistw)

        def remove_selected():
            rm_list = list()
            for x in range(plistw.count()):
                chk_item = plistw.item(x)
                if chk_item.checkState() == Qt.Checked:
                    rm_list.append(chk_item.text())

            for rm_project in rm_list:
                plistw.takeItem(plistw.row(plistw.findItems(rm_project, Qt.MatchExactly)[0]))
                self.pr.projects.remove(rm_project)
                shutil.rmtree(join(self.pr.home_path, rm_project))
            self.update_project_box()

        bt_layout = QHBoxLayout()
        rm_bt = QPushButton('Remove', self)
        rm_bt.clicked.connect(remove_selected)
        bt_layout.addWidget(rm_bt)
        close_bt = QPushButton('Close', self)
        close_bt.clicked.connect(dialog.close)
        bt_layout.addWidget(close_bt)
        layout.addLayout(bt_layout)

        dialog.setLayout(layout)
        dialog.open()

    def project_tools(self):
        self.project_box = QComboBox()
        self.project_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for project in self.pr.projects:
            self.project_box.addItem(project)
        self.project_box.currentTextChanged.connect(self.project_changed)
        self.project_box.setCurrentText(self.pr.project_name)
        proj_box_label = QLabel('<b>Project: <b>')
        self.toolbar.addWidget(proj_box_label)
        self.toolbar.addWidget(self.project_box)

        aadd = QAction('+', self)
        aadd.triggered.connect(self.add_project)
        self.toolbar.addAction(aadd)

        arm = QAction('-', self)
        arm.triggered.connect(self.remove_project)
        self.toolbar.addAction(arm)

    def project_changed(self, project):
        self.pr.project_name = project
        self.settings.setValue('project_name', self.pr.project_name)
        print(f'{self.pr.project_name} selected')
        self.pr.make_paths()
        self.subject_dock.update_subjects_list()

    def update_project_box(self):
        self.project_box.clear()
        for project in self.pr.projects:
            self.project_box.addItem(project)

    # Todo: Fix Dark-Mode
    def dark_mode(self):
        if self.adark_mode.isChecked():
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

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def raise_win(self):
        if iswin:
            # on windows we can raise the window by minimizing and restoring
            self.showMinimized()
            self.setWindowState(Qt.WindowActive)
            self.showNormal()
        else:
            # on osx we can raise the window. on unity the icon in the tray will just flash.
            self.activateWindow()
            self.raise_()

    def change_style(self, style_name):
        self.app.setStyle(QStyleFactory.create(style_name))
        self.app.setPalette(QApplication.style().standardPalette())
        self.center()

    # Todo: Make Buttons more appealing, mark when check
    #   make button-dependencies
    def make_func_bts(self):
        tab_func_widget = QTabWidget()
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
        for tab_name in opd.calcplot_fs:
            tab = QWidget()
            tab_func_layout = QGridLayout()
            r_cnt = 0
            c_cnt = 0
            r_max = 15
            for function_group in opd.calcplot_fs[tab_name]:
                if r_cnt > r_max:
                    r_cnt = 0
                label = QLabel(f'<b>{function_group}</b>', self)
                label.setTextFormat(Qt.RichText)
                tab_func_layout.addWidget(label, r_cnt, c_cnt)
                r_cnt += 1

                for function in opd.calcplot_fs[tab_name][function_group]:
                    pb = QPushButton(function, tab)
                    pb.setCheckable(True)
                    self.bt_dict[function] = pb
                    if self.func_dict[function]:
                        pb.setChecked(True)
                        self.func_dict[function] = 1
                    pb.toggled.connect(partial(self.select_func, function))
                    tab_func_layout.addWidget(pb, r_cnt, c_cnt)
                    r_cnt += 1
                    if r_cnt >= r_max:
                        c_cnt += 1
                        r_cnt = 0
            tab.setLayout(tab_func_layout)
            tab_func_widget.addTab(tab, tab_name)
        self.general_layout.addWidget(tab_func_widget, 1, 0)

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
        stop_bt = QPushButton('Quit', self)

        main_bt_layout.addWidget(clear_bt)
        main_bt_layout.addWidget(start_bt)
        main_bt_layout.addWidget(stop_bt)

        clear_bt.clicked.connect(self.clear)
        start_bt.clicked.connect(self.start)
        stop_bt.clicked.connect(self.close)

        self.general_layout.addLayout(main_bt_layout, 2, 0)

    def clear(self):
        for x in self.bt_dict:
            self.bt_dict[x].setChecked(False)
            self.func_dict[x] = 0

    def start(self):
        # Todo: Cancel-Button, Progress-Bar for Progress
        msg = QDialog(self)
        msg.setWindowTitle('Executing Functions...')
        msg.open()
        fc.call_functions(self, self.pr)
        msg.close()

    def update_pipeline(self):
        command = f"pip install --upgrade git+https://github.com/marsipu/mne_pipeline_hd.git#egg=mne-pipeline-hd"
        run(command, shell=True)

        msg = QMessageBox(self)
        msg.setText('Please restart the Pipeline-Program/Close the Console')
        msg.setInformativeText('Do you want to restart?')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        msg.exec_()

        if msg.Yes:
            sys.exit()
        else:
            pass

    def update_mne(self):
        msg = QMessageBox(self)
        msg.setText('You are going to update your conda-environment called mne, if none is found, one will be created')
        msg.setInformativeText('Do you want to proceed? (May take a while, watch your console)')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        msg.exec_()

        command_upd = "curl --remote-name " \
                      "https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml; " \
                      "conda update conda; " \
                      "conda activate mne; " \
                      "conda env update --file environment.yml; pip install -r requirements.txt; " \
                      "conda install -c conda-forge pyqt=5.12"

        command_upd_win = "curl --remote-name " \
                          "https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml & " \
                          "conda update conda & " \
                          "conda activate mne & " \
                          "conda env update --file environment.yml & pip install -r requirements.txt & " \
                          "conda install -c conda-forge pyqt=5.12"

        command_new = "curl --remote-name " \
                      "https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml; " \
                      "conda update conda; " \
                      "conda env create --name mne --file environment.yml;" \
                      "conda activate mne; pip install -r requirements.txt; " \
                      "conda install -c conda-forge pyqt=5.12"

        command_new_win = "curl --remote-name " \
                          "https://raw.githubusercontent.com/mne-tools/mne-python/master/environment.yml & " \
                          "conda update conda & " \
                          "conda env create --name mne_test --file environment.yml & " \
                          "conda activate mne & pip install -r requirements.txt & " \
                          "conda install -c conda-forge pyqt=5.12"

        if msg.Yes:
            result = run('conda env list', shell=True, capture_output=True, text=True)
            if 'buba' in result.stdout:
                if iswin:
                    command = command_upd_win
                else:
                    command = command_upd
                result2 = run(command, shell=True, capture_output=True, text=True)
                if result2.stderr != '':
                    print(result2.stderr)
                    if iswin:
                        command = command_new_win
                    else:
                        command = command_new
                    result3 = run(command, shell=True, capture_output=True, text=True)
                    print(result3.stdout)
                else:
                    print(result2.stdout)
            else:
                print('yeah')
                if iswin:
                    command = command_new_win
                else:
                    command = command_new
                result4 = run(command, shell=True, capture_output=True, text=True)
                print(result4.stdout)
        else:
            pass

    def about_qt(self):
        QMessageBox.aboutQt(self, 'About Qt')

    # Todo: Make a developers command line input to access the local variables and use quickly some script on them

    def closeEvent(self, event):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('home_path', self.pr.home_path)
        self.settings.setValue('project_name', self.pr.project_name)
        self.settings.setValue('func_checked', self.func_dict)

        event.accept()
