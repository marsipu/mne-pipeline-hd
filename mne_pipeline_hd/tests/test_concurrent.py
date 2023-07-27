# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

# def test_blocking_worker_dialog(qtbot):
#     def _test_func():
#         time.sleep(2)
#         print('Finished Test-Func')
#
#     time1 = time.time()
#     dlg = WorkerDialog(None, _test_func, blocking=True)
#     qtbot.addWidget(dlg)
#     time2 = time.time()
#
#     print(f'Worker-Dialog took {round(time2 - time1, 2)} s')
#     assert time2 - time1 >= 2

# def test_qprocess_worker(qtbot):
#     commands = ['conda', 'quatsch']
#     pw = QProcessWorker(commands, printtostd=False)
#     output = list()
#     errors = list()
#     pw.stdoutSignal.connect(lambda x: output.append(x))
#     pw.stderrSignal.connect(lambda x: errors.append(x))
#     pw.start()
#     blocker = qtbot.waitSignals([pw.stdoutSignal, pw.stderrSignal],
#                                 timeout=5000)
#     blocker.wait()
#     assert output[0].startswith('usage: conda-script.py [-h] [-V] command')
#     assert errors[0].startswith('An error occured with "quatsch')
