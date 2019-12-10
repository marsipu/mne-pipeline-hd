import sys
# Should be executed in MNE-Environment or base with MNE installed
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QPushButton, QHBoxLayout,
                             QMainWindow, QDesktopWidget, QVBoxLayout)
import matplotlib
import mne
from mayavi import mlab

matplotlib.use('QT5Agg')
from matplotlib import pyplot as plt


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('QT-Test')
        self.setCentralWidget(QWidget(self))
        self.main_layout = QVBoxLayout()
        self.addlabel()
        self.addbuttons()
        self.centralWidget().setLayout(self.main_layout)

        # Necessary because frameGeometry is dependent on number of function-buttons
        newh = self.sizeHint().height()
        neww = self.sizeHint().width()
        self.setGeometry(0, 0, neww, newh)

        # This is also possible but does not center a widget with height < 480
        # self.layout().update()
        # self.layout().activate()
        self.center()

    def addbuttons(self):
        h_layout = QHBoxLayout()
        bt1 = QPushButton('Quit')
        bt2 = QPushButton('Matplotlib')
        bt3 = QPushButton('MNE-Coreg')
        bt4 = QPushButton('Mayavi')
        h_layout.addWidget(bt1)
        h_layout.addWidget(bt2)
        h_layout.addWidget(bt3)
        h_layout.addWidget(bt4)
        for x in range(10):
            h_layout.addWidget(QPushButton(str(x)))
        self.setLayout(h_layout)

        bt1.clicked.connect(app.quit)
        bt2.clicked.connect(self.test_matplotlib)
        bt3.clicked.connect(self.test_mne_coreg)
        bt4.clicked.connect(self.test_mayavi)

        self.main_layout.addLayout(h_layout)

    def addlabel(self):
        label = QLabel('Hello World!', self)
        self.main_layout.addWidget(label)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def test_matplotlib(self):
        plt.plot([1, 2, 3, 4])
        plt.show()

    def test_mne_coreg(self):
        mne.gui.coregistration()

    def test_mayavi(self):
        mlab.figure()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    view = TestWindow()
    # Program Mode
    view.show()
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
