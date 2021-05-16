# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2021, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
import functools
import sys
import time

from PyQt5.QtWidgets import QApplication, QWidget

from mne_pipeline_hd.gui.gui_utils import WorkerDialog

def app_test(test_func):
    @functools.wraps(test_func)
    def app_wrapper(*args, **kwargs):
        app = QApplication(sys.argv)
        test_func(*args, **kwargs)
        app.exec()

    return app_wrapper


@app_test
def test_blocking_worker_dialog():
    def _test_func():
        time.sleep(2)
        print('Finished Test-Func')

    main_widget = QWidget()
    main_widget.show()

    time1 = time.time()
    WorkerDialog(main_widget, _test_func, blocking=True)
    print('After Worker-Dialog')
    time2 = time.time()

    print(f'Worker-Dialog took {round(time2 - time1, 2)} s')
    assert time2 - time1 > 2


if __name__ == '__main__':
    test_blocking_worker_dialog()
