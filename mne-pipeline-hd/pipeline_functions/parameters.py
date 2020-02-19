import os
import shutil
import sys
from importlib import util
from os.path import isfile, join

from PyQt5.QtWidgets import QDesktopWidget, QDialog, QGridLayout, QVBoxLayout


class ParameterGUI(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QVBoxLayout()

        self.p = None

        deskgeo = QDesktopWidget().availableGeometry()
        param_width = int(deskgeo.width() * 0.75)
        param_height = int(deskgeo.height() * 0.75)
        self.setGeometry(0, 0, param_width, param_height)

        self.import_parameters()
        self.init_ui()

        self.setLayout(self.layout)
        self.open()

    def init_ui(self):
        parameter_layout = QGridLayout()

    def import_parameters(self):
        if not isfile(join(self.mw.pr.project_path, f'parameters_{self.mw.pr.project_name}.py')):

            shutil.copy2(join(os.getcwd(), 'resources/parameters_template.py'),
                         join(self.mw.pr.project_path, f'parameters_{self.mw.pr.project_name}.py'))
            print(f'parameters_{self.mw.pr.project_name}.py created in {self.mw.pr.project_path}'
                  f' from parameters_template.py')
        else:
            spec = util.spec_from_file_location('parameters', join(self.mw.pr.project_path,
                                                                   f'parameters_{self.mw.pr.project_name}.py'))
            p = util.module_from_spec(spec)
            sys.modules['parameters'] = p
            spec.loader.exec_module(p)
            print(f'Read Parameters from parameters_{self.mw.pr.project_name}.py in {self.mw.pr.project_path}')
