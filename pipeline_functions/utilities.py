# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 01:00:31 2019

@author: 'Martin Schulz'
"""
import sys
import os
from os.path import join, isfile
import autoreject as ar
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton,
                             QToolTip, QDesktopWidget, QVBoxLayout,
                             QCheckBox)
from PyQt5.QtGui import QFont



class BasicWindow(QWidget):

    def __init__(self, title, width, height):
        super().__init__()
        self.title = title
        self.width = width
        self.height = height
        
        self.initUI()

    def initUI(self):
        
        QToolTip.setFont(QFont('SansSerif', 10))
        
        self.setToolTip(f'This is a Window for {self.title}')
        
        qbtn = QPushButton('Quit', self)
        qbtn.setToolTip('Close the Window')
        qbtn.clicked.connect(QApplication.instance().quit)
        qbtn.resize(qbtn.sizeHint())
        qbtn.move(50, 50)

        self.resize(self.width,self.height)
        self.center()
        self.setWindowTitle(self.title)
        self.show()
    
    def center(self):
        
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
    def closeEvent(self, event):
        event.accept()

class FunctionChooser(BasicWindow):
    
    def __init__(self, functions):
        
        title = 'Choose the functions to be executed'
        width = 500
        height = 300
        super().__init__(title, width, height)
        
        self.functions = functions
        self.functions_buttons = []
        self.layout = QVBoxLayout()
        self.make_checkboxes(self.functions)
        
        self.rb = QPushButton('Run')
        self.layout.addWidget(self.rb)
        
    def make_checkboxes(self, functions):
        
        for function in functions:
            fname = function.__name__
            self.functions_buttons.append(QCheckBox(fname))
            self.layout.addWidget(self.functions_buttons[-1])
            
    def run(self):
        
        for b in self.functions_buttons:
            if b.isChecked() == True:
                print(b.text())

def choose_function():
    
    def a(b):
        print(b)
    
    functions = [a]
    app = QApplication(sys.argv)
    w = FunctionChooser(functions) #operations_to_apply, take the existing dictionary. Less running problems
    w.show()
    #app.exec_()
    #app.aboutToQuit.connect(app.deleteLater)
    sys.exit(app.exec_()) # Raises Error for SystemExit

               
def autoreject_handler(name, epochs, sub_script_path, overwrite_ar=False,
                       only_read=False):

    reject_value_path = join(sub_script_path, 'reject_values.py')
    
    if not isfile(reject_value_path):
        if only_read:
            raise Exception('New Autoreject-Threshold only from epoch_raw')
        else:
            reject = ar.get_rejection_threshold(epochs)                
            with open(reject_value_path, 'w') as rv:
                rv.write(f'{name}:{reject}\n')
            print(reject_value_path + ' created')
        
    else:
        read_reject = {}
        with open(reject_value_path, 'r') as rv:

            for item in rv:
                if ':' in item:
                    key,value = item.split(':', 1)
                    value = eval(value[:-1])
                    read_reject[key] = value
        
        if name in read_reject:
            if overwrite_ar:
                if only_read:
                    raise Exception('New Autoreject-Threshold only from epoch_raw')
                print('Rejection with Autoreject')
                reject = ar.get_rejection_threshold(epochs)
                prae_reject = read_reject[name]
                read_reject[name] = reject
                if prae_reject == reject:
                    print(f'Same reject_values {reject}')
                else:
                    print(f'Replaced AR-Threshold {prae_reject} with {reject}')
                with open(reject_value_path, 'w') as rv:
                    for key,value in read_reject.items():
                        rv.write(f'{key}:{value}\n')
            else:   
                reject = read_reject[name]
                print('Reading Rejection-Threshold from file')

        else:
            if only_read:
                raise Exception('New Autoreject-Threshold only from epoch_raw')
            print('Rejection with Autoreject')
            reject = ar.get_rejection_threshold(epochs)
            read_reject.update({name:reject})
            print(f'Added AR-Threshold {reject} for {name}')
            with open(reject_value_path, 'w') as rv:
                for key,value in read_reject.items():
                    rv.write(f'{key}:{value}\n')
    
    return reject
    

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

if __name__ == '__main__':
    app = choose_function()
    print('Huhu')
