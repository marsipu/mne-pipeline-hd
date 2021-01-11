# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2020, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
import io
import logging
import sys
import traceback

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QDesktopWidget


def center(widget):
    qr = widget.frameGeometry()
    cp = QDesktopWidget().availableGeometry().center()
    qr.moveCenter(cp)
    widget.move(qr.topLeft())


def set_ratio_geometry(size_ratio, widget=None):
    desk_geometry = QApplication.instance().desktop().availableGeometry()
    height = int(desk_geometry.height() * size_ratio)
    width = int(desk_geometry.width() * size_ratio)
    if widget:
        widget.resize(width, height)

    return width, height


def get_exception_tuple():
    traceback.print_exc()
    exctype, value = sys.exc_info()[:2]
    traceback_str = traceback.format_exc(limit=-10)
    logging.error(f'{exctype}: {value}\n'
                  f'{traceback_str}')

    return exctype, value, traceback_str


class WorkerSignals(QObject):
    """Class for standard Worker-Signals
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(tuple)


class Worker(QRunnable):
    """A class to execute a function in a seperate Thread

    Parameters
    ----------
    function
        A reference to the function which is to be executed in the thread
    args
        Any Arguments passed to the executed function
    kwargs
        Any Keyword-Arguments passed to the executed function

    """

    def __init__(self, function, *args, **kwargs):
        super().__init__()

        # Store constructor arguments (re-used for processing)
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            return_value = self.function(*self.args, **self.kwargs)
        except:
            exc_tuple = get_exception_tuple()
            self.signals.error.emit(exc_tuple)
        else:
            self.signals.finished.emit(return_value)  # Done


class StdoutSignal(QObject):
    text_written = pyqtSignal(str)


class StdoutStream(io.TextIOBase):

    def __init__(self):
        super().__init__()
        self.signal = StdoutSignal()

    def write(self, text):
        # Send still the output to the command line
        sys.__stdout__.write(text)
        # Emit additionally the written text in a pyqtSignal
        self.signal.text_written.emit(text)


class StderrSignal(QObject):
    text_written = pyqtSignal(str)
    text_updated = pyqtSignal(str)


class StderrStream(io.TextIOBase):

    def __init__(self):
        super().__init__()
        self.signal = StderrSignal()
        self.last_text = ''

    def write(self, text):
        # Send still the output to the command line
        sys.__stderr__.write(text)

        if text[:1] == '\r':
            # Emit additionally the written text in a pyqtSignal
            text = text.replace('\r', '')
            # Avoid doubling
            if text != self.last_text:
                self.signal.text_updated.emit(text)
                self.last_text = text
        else:
            # Eliminate weird symbols and avoid doubling
            if '\x1b' not in text and text != self.last_text:
                # Avoid weird last line in tqdm-progress
                if self.last_text[-1:] != '\n':
                    text = '\n' + text
                self.signal.text_written.emit(text)
                self.last_text = text

