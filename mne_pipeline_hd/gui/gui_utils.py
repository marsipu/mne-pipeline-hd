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
import smtplib
import ssl
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from inspect import signature

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QDialog, QHBoxLayout, QLabel, QMessageBox,
                             QProgressBar, QPushButton, QScrollArea, QTextEdit, QVBoxLayout)
from pyqode.core.api import ColorScheme
from pyqode.python.backend import server
from pyqode.core import api, modes, panels
from pyqode.python import modes as pymodes, panels as pypanels, widgets
from pyqode.python.modes import PythonSH


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
    logging.getLogger().error(f'{exctype}: {value}')

    return exctype, value, traceback_str


# Todo: Rework how to send Issues (E-Mail, GitHub?)
class ErrorDialog(QDialog):
    def __init__(self, exception_tuple, parent=None, title=None):
        if parent:
            super().__init__(parent)
        else:
            super().__init__()
        self.err = exception_tuple
        self.title = title
        if self.title:
            self.setWindowTitle(self.title)
        else:
            self.setWindowTitle('An Error ocurred!')

        set_ratio_geometry(0.6, self)

        self.init_ui()

        if parent:
            self.open()
        else:
            self.exec()

    def init_ui(self):
        layout = QVBoxLayout()

        self.display = QTextEdit()
        self.display.setLineWrapMode(QTextEdit.WidgetWidth)
        self.display.setReadOnly(True)
        self.formated_tb_text = self.err[2].replace('\n', '<br>')
        if self.title:
            self.html_text = f'<h1>{self.title}</h1>' \
                             f'<h2>{self.err[1]}</h2>' \
                             f'{self.formated_tb_text}'
        else:
            self.html_text = f'<h1>{self.err[1]}</h1>' \
                             f'{self.formated_tb_text}'
        self.display.setHtml(self.html_text)

        # layout.addWidget(scroll_area, 0, 0, 1, 2)
        layout.addWidget(self.display)

        # self.name_le = QLineEdit()
        # self.name_le.setPlaceholderText('Enter your Name (optional)')
        # layout.addWidget(self.name_le, 1, 0)
        #
        # self.email_le = QLineEdit()
        # self.email_le.setPlaceholderText('Enter your E-Mail-Adress (optional)')
        # layout.addWidget(self.email_le, 1, 1)
        #
        # self.send_bt = QPushButton('Send Error-Report')
        # self.send_bt.clicked.connect(self.send_report)
        # layout.addWidget(self.send_bt, 2, 0)

        self.close_bt = QPushButton('Close')
        self.close_bt.clicked.connect(self.close)
        layout.addWidget(self.close_bt)

        self.setLayout(layout)

    # Todo: Rework without having to show the password
    def send_report(self):
        msg_box = QMessageBox.question(self, 'Send an E-Mail-Bug-Report?',
                                       'Do you really want to send an E-Mail-Report?',
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if msg_box == QMessageBox.Yes:
            port = 465
            adress = 'mne.pipeline@gmail.com'
            password = '24DecodetheBrain7!'

            context = ssl.create_default_context()

            message = MIMEMultipart("alternative")
            message['Subject'] = str(self.err[1])
            message['From'] = adress
            message["To"] = adress

            message_body = MIMEText(f'<b><big>{self.name_le.text()}</b></big><br>'
                                    f'<i>{self.email_le.text()}</i><br><br>'
                                    f'<b>{sys.platform}</b><br>{self.formated_tb_text}', 'html')
            message.attach(message_body)
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', port, context=context) as server:
                    server.login('mne.pipeline@gmail.com', password)
                    server.sendmail(adress, adress, message.as_string())
                QMessageBox.information(self, 'E-Mail sent', 'An E-Mail was sent to mne.pipeline@gmail.com\n'
                                                             'Thank you for the Report!')
            except OSError:
                QMessageBox.information(self, 'E-Mail not sent', 'Sending an E-Mail is not possible on your OS')


def show_error_dialog(exc_str):
    """Checks if a QApplication instance is available and shows the Error-Dialog.
    If unavailable (non-console application), log an additional notice.
    """
    if QApplication.instance() is not None:
        ErrorDialog(exc_str, title='A unexpected error occurred')
    else:
        logging.getLogger().debug("No QApplication instance available.")


class UncaughtHook(QObject):
    """This class is a modified version of https://timlehr.com/python-exception-hooks-with-qt-message-box/"""
    _exception_caught = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super(UncaughtHook, self).__init__(*args, **kwargs)

        # this registers the exception_hook() function as hook with the Python interpreter
        sys.excepthook = self.exception_hook

        # connect signal to execute the message box function always on main thread
        self._exception_caught.connect(show_error_dialog)

    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """Function handling uncaught exceptions.
        It is triggered each time an uncaught exception occurs.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # ignore keyboard interrupt to support console applications
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        else:
            # Print Error to Console
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            exc_info = (exc_type, exc_value, exc_traceback)
            exc_str = (exc_type.__name__, exc_value, ''.join(traceback.format_tb(exc_traceback)))
            logging.getLogger().critical(f'Uncaught exception:\n'
                                         f'{exc_str[0]}: {exc_str[1]}\n'
                                         f'{exc_str[2]}',
                                         exc_info=exc_info)

            # trigger showing of error-dialog
            self._exception_caught.emit(exc_str)


class CodeEditor(widgets.PyCodeEditBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # starts the default pyqode.python server (which enable the jedi code
        # completion worker).
        self.backend.start(server.__file__)

        # # some other modes/panels require the analyser mode, the best is to
        # # install it first
        # self.modes.append(pymodes.DocumentAnalyserMode())

        # --- core panels
        self.panels.append(panels.FoldingPanel())
        self.panels.append(panels.LineNumberPanel())
        # self.panels.append(panels.CheckerPanel())
        self.panels.append(panels.SearchAndReplacePanel(),
                           panels.SearchAndReplacePanel.Position.BOTTOM)
        self.panels.append(panels.EncodingPanel(), api.Panel.Position.TOP)
        # add a context menu separator between editor's
        # builtin action and the python specific actions
        self.add_separator()

        # --- python specific panels
        self.panels.append(pypanels.QuickDocPanel(), api.Panel.Position.BOTTOM)

        # Syntax-Highlighting
        self.modes.append(PythonSH(self.document(), color_scheme=ColorScheme('autumn')))

        # --- core modes
        self.modes.append(modes.CaretLineHighlighterMode())
        self.modes.append(modes.CodeCompletionMode())
        self.modes.append(modes.ExtendedSelectionMode())
        self.modes.append(modes.FileWatcherMode())
        self.modes.append(modes.OccurrencesHighlighterMode())
        # self.modes.append(modes.RightMarginMode())
        self.modes.append(modes.SmartBackSpaceMode())
        self.modes.append(modes.SymbolMatcherMode())
        self.modes.append(modes.ZoomMode())

        # ---  python specific modes
        self.modes.append(pymodes.CommentsMode())
        self.modes.append(pymodes.CalltipsMode())
        # self.modes.append(pymodes.FrostedCheckerMode())
        # self.modes.append(pymodes.PEP8CheckerMode())
        self.modes.append(pymodes.PyAutoCompleteMode())
        self.modes.append(pymodes.PyAutoIndentMode())
        self.modes.append(pymodes.PyIndenterMode())


def _html_compatible(text):
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('\n', '<br>')
    text = text.replace('\x1b', '')

    return text


class ConsoleWidget(QTextEdit):
    def __init__(self):
        super().__init__()

        self.setReadOnly(True)
        self.is_prog_text = False
        self.autoscroll = True

        # Connect custom stdout and stderr to display-function
        sys.stdout.signal.text_written.connect(self.write_stdout)
        sys.stderr.signal.text_written.connect(self.write_error)
        # Handle progress-bars
        sys.stdout.signal.text_updated.connect(self.write_progress)
        sys.stderr.signal.text_updated.connect(self.write_progress)

    def add_html(self, text):
        # Make sure the cursor is at the end of the console
        cursor = self.textCursor()
        if not cursor.atEnd():
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)

        self.insertHtml(text)
        if self.autoscroll:
            self.ensureCursorVisible()

    def set_autoscroll(self, autoscroll):
        self.autoscroll = autoscroll

    def write_stdout(self, text):
        self.is_prog_text = False
        text = _html_compatible(text)
        self.add_html(text)

    def write_error(self, text):
        self.is_prog_text = False
        text = _html_compatible(text)
        text = f'<font color="red">{text}</font>'
        self.add_html(text)

    def write_progress(self, text):
        text = text.replace('\r', '')
        text = _html_compatible(text)
        text = f'<font color="green">{text}</font>'
        if self.is_prog_text:
            # Delete last line
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            self.add_html(text)
        else:
            self.is_prog_text = True
            self.add_html(text)


class StreamSignals(QObject):
    text_updated = pyqtSignal(str)
    text_written = pyqtSignal(str)


# ToDo: Buffering and halting signal-emission (continue writing to sys.__stdout__/__stderr__)
#  when no accepted/printed-signal is coming back from receiving Widget
class StdoutStderrStream(io.TextIOBase):

    def __init__(self, kind):
        super().__init__()
        self.signal = StreamSignals()
        if kind == 'stdout':
            self.original_stream = sys.__stdout__
        else:
            self.original_stream = sys.__stderr__

    def write(self, text):
        # Still send output to the command-line
        self.original_stream.write(text)

        # Get progress-text with '\r' as prefix
        if text[:1] == '\r':
            self.signal.text_updated.emit(text)
        else:
            self.signal.text_written.emit(text)


class WorkerSignals(QObject):
    """Class for standard Worker-Signals
    """
    # Emitted when the function finished and returns the return-value
    finished = pyqtSignal(object)

    # Emitted when the function throws an error and returns a tuple with information about the error
    # (see get_exception_tuple)
    error = pyqtSignal(tuple)

    # Can be passed to function to be emitted when a part of the function progresses to update a Progress-Bar
    pgbar_max = pyqtSignal(int)
    pgbar_n = pyqtSignal(int)
    pgbar_text = pyqtSignal(str)

    # Only an attribute which is stored here to maintain reference when passing it to the function
    was_canceled = False


class Worker(QRunnable):
    """A class to execute a function in a seperate Thread

    Parameters
    ----------
    function
        A reference to the function which is to be executed in the thread
    include_signals
        If to include the signals into the function-call
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
        # Add signals to kwargs if in parameters of function
        if 'worker_signals' in signature(self.function).parameters:
            self.kwargs['worker_signals'] = self.signals

        # Retrieve args/kwargs here; and fire processing using them
        try:
            return_value = self.function(*self.args, **self.kwargs)
        except:
            exc_tuple = get_exception_tuple()
            self.signals.error.emit(exc_tuple)
        else:
            self.signals.finished.emit(return_value)  # Done

    def cancel(self):
        self.signals.was_canceled = True


class WorkerDialog(QDialog):
    """A Dialog for a Worker doing a function"""
    thread_finished = pyqtSignal(object)

    def __init__(self, parent, function, show_buttons=False, show_console=False, close_directly=True,
                 title=None, **kwargs):
        super().__init__(parent)

        self.show_buttons = show_buttons
        self.show_console = show_console
        self.close_directly = close_directly
        self.title = title
        self.is_finished = False
        self.return_value = None

        # Initialize worker
        self.worker = Worker(function, **kwargs)
        self.worker.signals.finished.connect(self.on_thread_finished)
        self.worker.signals.error.connect(self.on_thread_finished)
        self.worker.signals.pgbar_max.connect(self.set_pgbar_max)
        self.worker.signals.pgbar_n.connect(self.pgbar_changed)
        self.worker.signals.pgbar_text.connect(self.label_changed)
        QThreadPool.globalInstance().start(self.worker)

        if self.show_console:
            set_ratio_geometry(0.3, self)

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        if self.title:
            title_label = QLabel(self.title)
            title_label.setFont(QFont('AnyType', 18, QFont.Bold))
            layout.addWidget(title_label)

        self.progress_label = QLabel()
        self.progress_label.hide()
        layout.addWidget(self.progress_label, alignment=Qt.AlignHCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        if self.show_console:
            self.console_output = ConsoleWidget()
            layout.addWidget(self.console_output)

        if self.show_buttons:
            bt_layout = QHBoxLayout()

            cancel_bt = QPushButton('Cancel')
            cancel_bt.clicked.connect(self.cancel)
            bt_layout.addWidget(cancel_bt)

            self.close_bt = QPushButton('Close')
            self.close_bt.clicked.connect(self.close)
            self.close_bt.setEnabled(False)
            bt_layout.addWidget(self.close_bt)

            layout.addLayout(bt_layout)

        self.setLayout(layout)

    def on_thread_finished(self, return_value):
        # Store return value to send it when user closes the dialog
        self.return_value = return_value
        self.is_finished = True
        if self.show_buttons:
            self.close_bt.setEnabled(True)
        if self.close_directly:
            self.close()

    def set_pgbar_max(self, maximum):
        self.progress_bar.show()
        self.progress_bar.setMaximum(maximum)

    def pgbar_changed(self, value):
        self.progress_bar.setValue(value)

    def label_changed(self, text):
        self.progress_label.show()
        self.progress_label.setText(text)

    def cancel(self):
        self.worker.cancel()

    def closeEvent(self, event):
        # Can't close Dialog before Thread has finished or threw error
        if self.is_finished:
            self.thread_finished.emit(self.return_value)
            self.deleteLater()
            event.accept()
        else:
            QMessageBox.warning(self, 'Closing not possible!',
                                'You can\'t close this Dialog before this Thread finished!')
