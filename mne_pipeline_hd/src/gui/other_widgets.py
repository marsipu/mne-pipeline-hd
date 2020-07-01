# Use exec() and Helper-Buttons to Access Subject and Data
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget


class DataTerminal(QDialog):
    def __init__(self, main_win, subject=None):
        super().__init__(main_win)
        self.mw = main_win

        self.t_globals = {'mw': self.mw,
                          'main_window': self.mw,
                          'pr': self.mw.pr,
                          'project': self.mw.pr,
                          'par': self.mw.pr.parameters,
                          'parameters': self.mw.pr.parameters,
                          'sub': subject}

        self.init_ui()
        self.open()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.displayw = QTextEdit()
        self.displayw.setReadOnly(True)
        self.layout.addWidget(self.displayw)

        self.inputw = QTextEdit()
        self.layout.addWidget(self.inputw)

        self.start_bt = QPushButton()
        self.start_bt.clicked.connect(self.start_execution)
        self.layout.addWidget(self.start_bt)

        self.quit_bt = QPushButton()
        self.quit_bt.clicked.connect(self.close)
        self.layout.addWidget(self.quit_bt)

    def start_execution(self):
        command = self.inputw.toPlainText()
        exec(command, self.t_globals)
