# -*- coding: utf-8 -*-
import sys
from time import perf_counter

import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton

from mne_pipeline_hd.gui.gui_utils import ConsoleWidget

app = QApplication(sys.argv)
widget = QWidget()
layout = QVBoxLayout()
cw = ConsoleWidget()
layout.addWidget(cw)
close_bt = QPushButton("Close")
close_bt.clicked.connect(widget.close)
layout.addWidget(close_bt)
widget.setLayout(layout)
widget.show()
last_time = perf_counter()

performance_buffer = list()


def test_write():
    global last_time
    cw.write_progress("\r" + (f"Test {len(performance_buffer)}" * 1000))
    diff = perf_counter() - last_time
    performance_buffer.append(diff)
    if len(performance_buffer) >= 100:
        fps = 1 / np.mean(performance_buffer)
        print(f"Performance is: {fps:.2f} FPS")
        performance_buffer.clear()
    last_time = perf_counter()


timer = QTimer()
timer.timeout.connect(test_write)
timer.start(1)

sys.exit(app.exec())
