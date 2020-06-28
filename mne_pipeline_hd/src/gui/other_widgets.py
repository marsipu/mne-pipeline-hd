# Use exec() and Helper-Buttons to Access Subject and Data
from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QWidget


class DataTerminal(QWidget):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.displayw = QTextEdit()
