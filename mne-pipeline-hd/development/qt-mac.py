import sys

import matplotlib

from pipeline_functions import ismac

if ismac:
    matplotlib.use('MacOSX')
from matplotlib import pyplot as plt
from mayavi import mlab

from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QDesktopWidget, QPushButton, QVBoxLayout

from basic_functions import plot

class TestMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.app.setFont(QFont('Calibri', 24))
        self.setWindowTitle('QT-Test-Mac')
        self.setCentralWidget(QWidget(self))
        self.general_layout = QVBoxLayout()
        self.centralWidget().setLayout(self.general_layout)

        desk_geometry = self.app.desktop().screenGeometry()
        self.size_ratio = 0.8
        height = desk_geometry.height() * self.size_ratio
        width = desk_geometry.width() * self.size_ratio
        self.setGeometry(0, 0, width, height)

        self.center()
        self.init_ui()

    def init_ui(self):
        plt_test = QPushButton('Plot-Test')
        plt_test.clicked.connect(self.test_matplotlib_plot)
        self.general_layout.addWidget(plt_test)

        figure_test = QPushButton('Figure-Test')
        figure_test.clicked.connect(self.test_matplotlib_figure)
        self.general_layout.addWidget(figure_test)

        mayavi_test = QPushButton('Mayavi-Test')
        mayavi_test.clicked.connect(self.test_mayavi)
        self.general_layout.addWidget(mayavi_test)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def test_matplotlib_plot(self):
        plt.plot([1, 2, 3, 4])
        plt.show()

    def test_matplotlib_figure(self):
        name = ''
        save_dir = ''
        highpass = 1
        lowpass = 100
        figures_path = ''
        figure = plot.plot_evoked_butterfly(name, save_dir, highpass, lowpass, True, figures_path)

    def test_mayavi(self):
        mlab.figure()


app = QApplication(sys.argv)
app.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
if ismac:
    app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
    # Workaround for MAC menu-bar-focusing issue
    app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)
win = TestMainWindow()
win.show()

# Make Command-line Ctrl + C possible
timer = QTimer()
timer.timeout.connect(lambda: None)
timer.start(100)

sys.exit(app.exec_())
