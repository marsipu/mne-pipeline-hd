# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 01:00:31 2019

@author: 'Martin Schulz'
"""
import sys
import os
from os.path import join, isfile
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton

class Basic_Window(QWidget):
    
    def __init__(self, title, width, height):
        super().__init__()
        self.title = title
        self.width = width
        self.height = height
        
        self.initUI()
    
    def initUI(self):
        
        qbtn = QPushButton('Quit', self)
        qbtn.clicked.connect(QApplication.quit)
        qbtn.resize(qbtn.sizeHint())
        qbtn.move(50, 50)

        self.setGeometry(300,300,self.width,self.height)        
        self.setWindowTitle(self.title)        
        self.show()         
    
    def closeEvent(self, event):
        QApplication.quit
        event.accept()

        
def choose_function():

    app = QApplication(sys.argv)
    w = Basic_Window('Choose the functions', 500, 500)
    app.exec_()
    return app

if __name__ == '__main__':
    app = choose_function()
    app.quit    
    print('Huhu')

def getallfifFiles(dirName):
    # create a list of file and sub directories 
    # names in the given directory 
    listOfFile = os.walk(dirName)
    allFiles = list()
    paths = dict()
    # Iterate over all the entries
    for dirpath, dirnames, filenames in listOfFile:
        
        for file in filenames:
            if file[-4:] == '.fif':
                allFiles.append(file)
                paths.update({file:join(dirpath, file)})
                
    return allFiles, paths



