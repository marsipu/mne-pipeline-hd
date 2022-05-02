# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""

import functools
import sys
import time
from multiprocessing import Pool

from PyQt5.QtWidgets import QApplication, QWidget

from ..gui.gui_utils import WorkerDialog, QProcessWorker
from ..pipeline_functions.controller import Controller
from ..pipeline_functions.function_utils import RunController


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


def test_qprocess_worker(qtbot):
    commands = ['conda', 'quatsch']
    pw = QProcessWorker(commands, printtostd=False)
    output = list()
    errors = list()
    pw.stdoutSignal.connect(lambda x: output.append(x))
    pw.stderrSignal.connect(lambda x: errors.append(x))
    pw.start()
    blocker = qtbot.waitSignals([pw.stdoutSignal, pw.stderrSignal], timeout=5000)
    blocker.wait()
    assert output[0].startswith('usage: conda-script.py [-h] [-V] command')
    assert errors[0].startswith('An error occured with "quatsch')


def test_run_controller(tmpdir, qtbot):
    ct = Controller(tmpdir)
    ct.change_project('Test')
    ct.pr.sel_functions = ['print_info']
    ct.pr.sel_meeg = ['_sample_']
    rc = RunController(ct, Pool(1))
    rc.finished()
    rc.start()
    rc.pool.close()
    rc.pool.join()
