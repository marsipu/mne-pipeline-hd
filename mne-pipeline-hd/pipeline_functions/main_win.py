import sys
from functools import partial
from subprocess import run

from qtpy.QtCore import QSettings, Qt
from qtpy.QtGui import QColor, QFont, QPalette
from qtpy.QtWidgets import (QApplication, QComboBox, QDesktopWidget, QFileDialog, QGridLayout,
                             QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
                             QPushButton, QStyleFactory, QTabWidget, QToolTip, QVBoxLayout, QWidget, QAction)

from basic_functions import io
from pipeline_functions import iswin
from resources import operations_dict as opd
from pipeline_functions.project import MyProject
from pipeline_functions.subjects import AddFiles, SubDictDialog, BadChannelsSelect, AddMRIFiles


# Todo: Create BadChannelsSelect


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.pr = MyProject(self)
        self.settings = QSettings()
        self.platform = sys.platform

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
        self.lines = dict()
        self.project_box = None
        self.subsel_layout = QHBoxLayout()
        sub_sel_example = "Examples:\n" \
                          "'5' (One File)\n" \
                          "'1,7,28' (Several Files)\n" \
                          "'1-5' (From File x to File y)\n" \
                          "'1-4,7,20-26' (The last two combined)\n" \
                          "'1-20,!4-6' (1-20 except 4-6)\n" \
                          "'all' (All files in file_list.py)\n" \
                          "'all,!4-6' (All files except 4-6)"

        self.sub_sel_tips = {'which_file': f'Choose files to process!\n{sub_sel_example}',
                             'quality': f'Choose the quality!\n{sub_sel_example}',
                             'which_mri_subject': f'Choose mri_files to process\n{sub_sel_example}',
                             'which_erm_file': f'Choose erm_files to process\n{sub_sel_example}'}

        # Call methods
        self.pr.get_paths()
        self.pr.make_paths()
        self.make_menu()
        self.make_toolbar()
        self.make_statusbar()
        self.make_project_box()
        self.subject_selection()
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
            self.settings.setValue('project_name', self.pr.project_name)
            self.project_box.addItem(project)
            self.project_box.setCurrentText(project)
            self.pr.make_paths()
        else:
            pass

    def make_project_box(self):
        proj_layout = QVBoxLayout()
        self.project_box = QComboBox()
        for project in self.pr.projects:
            self.project_box.addItem(project)
        self.project_box.currentTextChanged.connect(self.change_project)
        self.project_box.setCurrentText(self.pr.project_name)
        proj_box_label = QLabel('<b>Project:<b>')
        proj_layout.addWidget(proj_box_label)
        proj_layout.addWidget(self.project_box)
        self.subsel_layout.addLayout(proj_layout)

    def change_project(self, project):
        self.pr.project_name = project
        self.settings.setValue('project_name', self.pr.project_name)
        print(self.pr.project_name)
        self.pr.make_paths()

    def update_project_box(self):
        self.project_box.clear()
        for project in self.pr.projects:
            self.project_box.addItem(project)

    def make_menu(self):
        # & in front of text-string creates automatically a shortcut with Alt + <letter after &>
        # Input
        input_menu = self.menuBar().addMenu('&Input')

        aaddfiles = QAction('Add Files', self)
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
        # Settings
        settings_menu = self.menuBar().addMenu('&Settings')
        self.adark_mode = settings_menu.addAction('&Dark-Mode', self.dark_mode)
        self.adark_mode.setCheckable(True)
        settings_menu.addAction('&Full-Screen', self.full_screen).setCheckable(True)
        settings_menu.addAction('&Change Home-Path', self.change_home_path)
        settings_menu.addAction('&Add Project', self.add_project)
        # About
        about_menu = self.menuBar().addMenu('About')
        about_menu.addAction('Update Pipeline', self.update_pipeline)
        about_menu.addAction('Update MNE-Python', self.update_mne)
        about_menu.addAction('About QT', self.about_qt)

    def make_toolbar(self):
        pass

    def make_statusbar(self):
        self.statusBar().showMessage('Ready')

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

    def subject_selection(self):
        # Todo: Default Selection for Lines, Tooltips for explanation, GUI-Button
        for t in self.sub_sel_tips:
            subsub_layout = QVBoxLayout()
            self.lines[t] = QLineEdit()
            self.lines[t].setPlaceholderText(t)
            self.lines[t].textChanged.connect(partial(self.update_subsel, t))
            self.lines[t].setToolTip(self.sub_sel_tips[t])
            label = QLabel(f'<b>{t}</b>')
            label.setTextFormat(Qt.RichText)
            subsub_layout.addWidget(label)
            subsub_layout.addWidget(self.lines[t])
            self.subsel_layout.addLayout(subsub_layout)
            # Get Selection from last run
            self.lines[t].setText(self.settings.value(t))

        self.general_layout.addLayout(self.subsel_layout, 0, 0)

    def update_subsel(self, t):
        setattr(self, t, self.lines[t].text())

    def change_style(self, style_name):
        self.app.setStyle(QStyleFactory.create(style_name))
        self.app.setPalette(QApplication.style().standardPalette())
        self.center()

    # Todo: Make Buttons more appealing, mark when checked
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
        stop_bt.clicked.connect(self.app.quit)

        self.general_layout.addLayout(main_bt_layout, 2, 0)

    def clear(self):
        for x in self.bt_dict:
            self.bt_dict[x].setChecked(False)
            self.func_dict[x] = 0

    def start(self):
        self.close()

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

    def get_upstream(self):
        if 'win' in self.platform:
            command = "git fetch upstream & git checkout master & git merge upstream/master"
        else:
            command = "git fetch upstream & git checkout master & git merge upstream/master"
        result = run(command)
        print(result.stdout)

    def about_qt(self):
        QMessageBox.aboutQt(self, 'About Qt')

    # Todo: Make a developers command line input to access the local variables and use quickly some script on them

    def closeEvent(self, event):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('home_path', self.pr.home_path)
        self.settings.setValue('project_name', self.pr.project_name)
        self.settings.setValue('func_checked', self.func_dict)
        for ln in self.lines:
            self.settings.setValue(ln, self.lines[ln].text())

        event.accept()


def plot_test():
    name = 'pp1a_256_b'
    save_dir = 'Z:/Promotion/Pin-Prick-Projekt/Daten/pp1a_256_b'
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
