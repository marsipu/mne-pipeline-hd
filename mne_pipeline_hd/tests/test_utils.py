from PyQt5.QtWidgets import QWidget

from ..gui.main_window import MainWindow
from ..pipeline_functions.controller import Controller


def init_test_instance(tmpdir):
    ct = Controller(tmpdir)
    ct.change_project('Test')

    main_window = MainWindow(ct)
