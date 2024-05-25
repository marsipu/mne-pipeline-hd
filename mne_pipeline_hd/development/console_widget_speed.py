# -*- coding: utf-8 -*-
import sys

from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton

from mne_pipeline_hd.gui.gui_utils import ConsoleWidget

test_text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus.
Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed,
dolor. Cras elementum ultrices diam. Maecenas ligula massa, varius a, semper
congue, euismod non, mi. Proin porttitor, orci nec nonummy molestie, enim est
eleifend mi, non fermentum diam nisl sit amet erat. Duis semper. Duis arcu
massa, scelerisque vitae, consequat in, pretium a, enim. Pellentesque congue.
Ut in risus volutpat libero pharetra tempor. Cras vestibulum bibendum augue.
Praesent egestas leo in pede. Praesent blandit odio eu enim. Pellentesque
sed dui ut augue blandit sodales. Vestibulum ante ipsum primis in faucibus
orci luctus et ultrices posuere cubilia Curae; Aliquam nibh. Mauris ac mauris
sed pede pellentesque fermentum. Maecenas adipiscing ante non diam sodales
hendrerit.
\r Progress: 0%
\r Progress: 10%
\r Progress: 20%
\r Progress: 30%
\r Progress: 40%
\r Progress: 50%
\r Progress: 60%
\r Progress: 70%
\r Progress: 80%
\r Progress: 90%
\r Progress: 100%"""


class SpeedWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        self.cw = ConsoleWidget()
        layout.addWidget(self.cw)
        startbt = QPushButton("Start")
        startbt.clicked.connect(self.start)
        layout.addWidget(startbt)
        stopbt = QPushButton("Stop")
        stopbt.clicked.connect(self.stop)
        layout.addWidget(stopbt)
        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.test_text = test_text.split("\n")
        self.line_idx = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.write)

    def start(self):
        self.timer.start(42)

    def stop(self):
        self.timer.stop()

    def write(self):
        if self.line_idx >= len(self.test_text):
            self.line_idx = 0
        text = self.test_text[self.line_idx]
        self.cw.write_stdout(text)
        self.line_idx += 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SpeedWidget()
    w.show()
    sys.exit(app.exec())
