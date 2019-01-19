# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 01:00:31 2019

@author: 'Martin Schulz'
"""
import sys
from PyQt5.QtWidgets import QApplication, QWidget


def choose_function():
    app = QApplication(sys.argv)
    w = QWidget()
    w.setWindowTitle('Choose the functions to be executed')
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    choose_function()
