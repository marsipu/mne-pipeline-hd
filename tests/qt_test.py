import sys
# Should be executed in MNE-Environment or base with MNE installed
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QPushButton, QHBoxLayout,
                             QMainWindow)
import matplotlib
matplotlib.use('QT5Agg')
from matplotlib import pyplot as plt

class Model:
    def __init__(self):
        self.view = None
        self.data = []


class TestWindow(QWidget):
    def __init__(self, model):
        super().__init__()
        self.setWindowTitle('QT-Test')
        self.setGeometry(100, 100, 280, 80)
        self.move(60, 15)
        self.addbuttons()
        self.addlabel()
        self.wuga = 42
        self.model = model

    def addbuttons(self):
        h_layout = QHBoxLayout()
        bt1 = QPushButton('Quit')
        bt2 = QPushButton('Print')
        h_layout.addWidget(bt1)
        h_layout.addWidget(bt2)
        self.setLayout(h_layout)

        bt1.clicked.connect(app.quit)
        bt2.clicked.connect(self.test_func)

    def addlabel(self):
        label = QLabel('Hello World!', self)

    def test_func(self):
        plt.plot(self.model.data)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    model = Model()
    model.view = TestWindow(model)
    a = model.view.wuga
    # Program Mode
    model.view.show()
    sys.exit(app.exec_())
    # Debug Mode
    # app.lastWindowClosed.connect(app.quit)
    # app.exec_()
    # test.close()
    # del app, test, TestWindow
# # Required, if to run repeatedly in Ipython
# if app in locals():
#     del app

# Necessary for Spyder
# app.lastWindowClosed.connect(app.quit)
