# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import io
import logging
import multiprocessing
import sys
import traceback
from contextlib import contextmanager
from importlib import resources
from inspect import signature
from os.path import join

import darkdetect
from PyQt5.QtGui import QColor, QIcon
from qtpy.QtCore import (
    QObject,
    QProcess,
    QRunnable,
    QThreadPool,
    Qt,
    Signal,
    Slot,
    QTimer,
)
from qtpy.QtGui import QFont, QTextCursor, QPalette
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QStyle,
    QInputDialog,
    QPlainTextEdit,
)

from mne_pipeline_hd import extra
from mne_pipeline_hd import _object_refs
from mne_pipeline_hd.pipeline.pipeline_utils import QS, logger


def center(widget):
    qr = widget.frameGeometry()
    cp = QApplication.primaryScreen().availableGeometry().center()
    qr.moveCenter(cp)
    widget.move(qr.topLeft())


def set_ratio_geometry(size_ratio, widget=None):
    if not isinstance(size_ratio, tuple):
        size_ratio = (size_ratio, size_ratio)
    wratio, hratio = size_ratio
    desk_geometry = QApplication.primaryScreen().availableGeometry()
    width = int(desk_geometry.width() * wratio)
    height = int(desk_geometry.height() * hratio)
    if widget:
        widget.resize(width, height)

    return width, height


def get_std_icon(icon_name):
    return QApplication.instance().style().standardIcon(getattr(QStyle, icon_name))


class ExceptionTuple(object):
    def __init__(self, *args):
        self._data = [*args]

    def __getitem__(self, idx):
        return self._data[idx]

    def __setitem__(self, idx, value):
        self._data[idx] = value

    def __str__(self):
        return self._data[2]


def get_exception_tuple(is_mp=False):
    traceback.print_exc()
    exctype, value = sys.exc_info()[:2]
    traceback_str = traceback.format_exc(limit=-10)
    # ToDo: Is this doing what it's supposed to do?
    if is_mp:
        logger = multiprocessing.get_logger()
    else:
        logger = logging.getLogger()
    logger.error(f"{exctype}: {value}")
    exc_tuple = ExceptionTuple(exctype, value, traceback_str)

    return exc_tuple


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
            self.setWindowTitle("An Error ocurred!")

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
        self.formated_tb_text = self.err[2].replace("\n", "<br>")
        if self.title:
            self.html_text = (
                f"<h1>{self.title}</h1>"
                f"<h2>{self.err[1]}</h2>"
                f"{self.formated_tb_text}"
            )
        else:
            self.html_text = f"<h1>{self.err[1]}</h1>" f"{self.formated_tb_text}"
        self.display.setHtml(self.html_text)
        layout.addWidget(self.display)

        self.close_bt = QPushButton("Close")
        self.close_bt.clicked.connect(self.close)
        layout.addWidget(self.close_bt)

        self.setLayout(layout)


def show_error_dialog(exc_str):
    """Checks if a QApplication instance is available
    and shows the Error-Dialog.
     If unavailable (non-console application), log an additional notice.
    """
    if QApplication.instance() is not None:
        ErrorDialog(exc_str, title="A unexpected error occurred")
    else:
        logger().debug("No QApplication instance available.")


def gui_error_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            exc_tuple = get_exception_tuple()
            ErrorDialog(exc_tuple)

    return wrapper


@contextmanager
def gui_error():
    try:
        yield
    except Exception:
        exc_tuple = get_exception_tuple()
        ErrorDialog(exc_tuple)


# ToDo: Test
class UncaughtHook(QObject):
    """This class is a modified version
    of https://timlehr.com/python-exception-hooks-with-qt-message-box/"""

    _exception_caught = Signal(object)

    def __init__(self, *args, **kwargs):
        super(UncaughtHook, self).__init__(*args, **kwargs)

        # connect signal to execute the message box function
        # always on main thread
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
            exc_str = (
                exc_type.__name__,
                exc_value,
                "".join(traceback.format_tb(exc_traceback)),
            )
            logger().critical(
                f"Uncaught exception:\n"
                f"{exc_str[0]}: {exc_str[1]}\n"
                f"{exc_str[2]}",
                exc_info=exc_info,
            )

            # trigger showing of error-dialog
            self._exception_caught.emit(exc_str)


class CodeEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)


class ConsoleWidget(QPlainTextEdit):
    """A Widget displaying formatted stdout/stderr-output"""

    def __init__(self):
        super().__init__()

        self.setReadOnly(True)
        self.autoscroll = True
        self.is_progress = False

        # Buffer to avoid crash for too many inputs
        self.buffer = list()
        self.buffer_time = 50
        self.buffer_timer = QTimer()
        self.buffer_timer.timeout.connect(self.write_buffer)
        self.buffer_timer.start(self.buffer_time)

    def write_buffer(self):
        if self.is_progress:
            # Delete last line
            cursor = self.textCursor()
            # Avoid having no break between progress and text
            # Remove last line
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()
            self.is_progress = False

        if len(self.buffer) > 0:
            text_list = self.buffer.copy()
            self.buffer.clear()
            text = "".join(text_list)
            # Remove last break because of appendHtml above
            if text[-4:] == "<br>":
                text = text[:-4]
            self.appendHtml(text)
            if self.autoscroll:
                self.ensureCursorVisible()

    def set_autoscroll(self, autoscroll):
        self.autoscroll = autoscroll

    def write_html(self, text):
        self.buffer.append(text)

    def _html_compatible(self, text):
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace("\n", "<br>")
        text = text.replace("\x1b", "")

        if text[:1] == "\r":
            self.is_progress = True
            text = text.replace("\r", "")
            # Avoid having no break between progress and text
            text = f"<font color='green'>{text}</font>"
            if len(self.buffer) > 0:
                if self.buffer[-1][:20] == "<font color='green'>":
                    self.buffer.pop(-1)
        return text

    def write_stdout(self, text):
        text = self._html_compatible(text)
        self.buffer.append(text)

    def write_stderr(self, text):
        text = self._html_compatible(text)
        if text[-4:] == "<br>":
            text = f'<font color="red">{text[:-4]}</font><br>'
        else:
            text = f'<font color="red">{text}</font>'
        self.buffer.append(text)

    # Make sure cursor is not moved
    def mousePressEvent(self, event):
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()


class MainConsoleWidget(ConsoleWidget):
    """A subclass of ConsoleWidget which is linked to stdout/stderr
    of the main process"""

    def __init__(self):
        super().__init__()

        # Connect custom stdout and stderr to display-function
        sys.stdout.signal.text_written.connect(self.write_stdout)
        sys.stderr.signal.text_written.connect(self.write_stderr)


class StreamSignals(QObject):
    text_written = Signal(str)


class StdoutStderrStream(io.TextIOBase):
    def __init__(self, kind):
        super().__init__()
        self.signal = StreamSignals()
        self.kind = kind
        if self.kind == "stdout":
            self.original_stream = sys.__stdout__
        elif self.kind == "stderr":
            self.original_stream = sys.__stderr__
        else:
            self.original_stream = None

    def write(self, text):
        if self.original_stream is not None:
            # Still send output to the command-line
            self.original_stream.write(text)
        # Emit signal to display in GUI
        self.signal.text_written.emit(text)

    def flush(self):
        if self.original_stream is not None:
            self.original_stream.flush()


class WorkerSignals(QObject):
    """Class for standard Worker-Signals"""

    # Emitted when the function finished and returns the return-value
    finished = Signal(object)

    # Emitted when the function throws an error and returns
    # a tuple with information about the error
    # (see get_exception_tuple)
    error = Signal(object)

    # Can be passed to function to be emitted when a part
    # of the function progresses to update a Progress-Bar
    pgbar_max = Signal(int)
    pgbar_n = Signal(int)
    pgbar_text = Signal(str)

    # Only an attribute which is stored here to maintain
    # reference when passing it to the function
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

    @Slot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        # Add signals to kwargs if in parameters of function
        if "worker_signals" in signature(self.function).parameters:
            self.kwargs["worker_signals"] = self.signals

        # Retrieve args/kwargs here; and fire processing using them
        try:
            return_value = self.function(*self.args, **self.kwargs)
        except Exception:
            exc_tuple = get_exception_tuple()
            self.signals.error.emit(exc_tuple)
        else:
            self.signals.finished.emit(return_value)  # Done

    def start(self):
        QThreadPool.globalInstance().start(self)

    def cancel(self):
        self.signals.was_canceled = True


# ToDo: Make PyQt-independent with tqdm
class WorkerDialog(QDialog):
    """A Dialog for a Worker doing a function"""

    thread_finished = Signal(object)

    def __init__(
        self,
        parent,
        function,
        show_buttons=False,
        show_console=False,
        close_directly=True,
        blocking=False,
        return_exception=False,
        title=None,
        **kwargs,
    ):
        super().__init__(parent)

        self.show_buttons = show_buttons
        self.show_console = show_console
        self.close_directly = close_directly
        self.return_exception = return_exception
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
        self.worker.start()

        if self.show_console:
            set_ratio_geometry(0.4, self)

        self.init_ui()
        if blocking:
            self.exec()
        else:
            self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        if self.title:
            title_label = QLabel(self.title)
            title_label.setFont(QFont("AnyType", 18, QFont.Bold))
            layout.addWidget(title_label)

        self.progress_label = QLabel()
        self.progress_label.hide()
        layout.addWidget(self.progress_label, alignment=Qt.AlignHCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        if self.show_console:
            self.console_output = MainConsoleWidget()
            layout.addWidget(self.console_output)

        if self.show_buttons:
            bt_layout = QHBoxLayout()

            cancel_bt = QPushButton("Cancel")
            cancel_bt.clicked.connect(self.cancel)
            bt_layout.addWidget(cancel_bt)

            self.close_bt = QPushButton("Close")
            self.close_bt.clicked.connect(self.close)
            self.close_bt.setEnabled(False)
            bt_layout.addWidget(self.close_bt)

            layout.addLayout(bt_layout)

        self.setLayout(layout)

    def on_thread_finished(self, return_value):
        # Store return value to send it when user closes the dialog
        if type(return_value) == ExceptionTuple and not self.return_exception:
            return_value = None
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
            QMessageBox.warning(
                self,
                "Closing not possible!",
                "You can't close this Dialog before this Thread finished!",
            )
            event.ignore()


# ToDo: WIP
class QProcessWorker(QObject):
    """A worker for QProcess."""

    # Send stdout from current process.
    stdoutSignal = Signal(str)
    # Send stderr from curren process.
    stderrSignal = Signal(str)
    # Send when all processes from commands are finished.
    finished = Signal()

    def __init__(self, commands, printtostd=True):
        """
        Parameters
        ----------
        commands : str, list
            Provide a command or a list of commands.
        printtostd : bool
            Set False if stdout/stderr are not supposed
             to be passed to sys.stdout/sys.stderr.
        """
        super().__init__()

        # Parse command(s)
        if not isinstance(commands, list):
            commands = [commands]
        self.commands = [cmd.split(" ") for cmd in commands]
        self.printtostd = printtostd
        self.process = None

    def handle_stdout(self):
        text = bytes(self.process.readAllStandardOutput()).decode("utf8")
        self.stdoutSignal.emit(text)
        if self.printtostd:
            sys.stdout.write(text)

    def handle_stderr(self):
        text = bytes(self.process.readAllStandardError()).decode("utf8")
        self.stderrSignal.emit(text)
        if self.printtostd:
            sys.stderr.write(text)

    def error_occurred(self):
        text = (
            f'An error occured with "{self.process.program()} '
            f'{" ".join(self.process.arguments())}":\n'
            f"{self.process.errorString()}\n"
        )
        self.stderrSignal.emit(text)
        if self.printtostd:
            sys.stderr.write(text)
        self.process_finished()

    def process_finished(self):
        if self.process.exitCode() == 1:
            text = (
                f'"{self.process.program()} '
                f'{" ".join(self.process.arguments())}" has crashed\n'
            )
            self.stderrSignal.emit(text)
            if self.printtostd:
                sys.stderr.write(text)
        if len(self.commands) > 0:
            self.start()
        else:
            self.finished.emit()

    def start(self):
        # Take the first command from commands until empty.
        cmd = self.commands.pop(0)
        self.process = QProcess()
        self.process.errorOccurred.connect(self.error_occurred)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.start(cmd[0], cmd[1:])

    def kill(self, kill_all=False):
        if kill_all:
            self.commands = list()
        if self.process:
            self.process.kill()


class QProcessDialog(QDialog):
    def __init__(
        self,
        parent,
        commands,
        show_buttons=True,
        show_console=True,
        close_directly=False,
        title=None,
        blocking=True,
    ):
        super().__init__(parent)
        self.commands = commands
        self.show_buttons = show_buttons
        self.show_console = show_console
        self.close_directly = close_directly
        self.title = title

        self.process_worker = None
        self.is_finished = False

        self.init_ui()
        self.start_process()

        set_ratio_geometry(0.5, self)

        if blocking:
            self.exec()
        else:
            self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        if self.title:
            title_label = QLabel(self.title)
            title_label.setFont(QFont("AnyType", 18, QFont.Bold))
            layout.addWidget(title_label)

        if self.show_console:
            self.console_output = ConsoleWidget()
            layout.addWidget(self.console_output)

        if self.show_buttons:
            bt_layout = QHBoxLayout()

            cancel_bt = QPushButton("Cancel")
            cancel_bt.clicked.connect(self.cancel)
            bt_layout.addWidget(cancel_bt)

            self.close_bt = QPushButton("Close")
            self.close_bt.clicked.connect(self.close)
            self.close_bt.setEnabled(False)
            bt_layout.addWidget(self.close_bt)

            layout.addLayout(bt_layout)

        self.setLayout(layout)

    def process_finished(self):
        self.is_finished = True
        if self.show_buttons:
            self.close_bt.setEnabled(True)
        if self.close_directly:
            self.close()

    def cancel(self):
        self.process_worker.kill(kill_all=True)

    def start_process(self):
        self.process_worker = QProcessWorker(self.commands)
        if self.show_console:
            self.process_worker.stdoutSignal.connect(self.console_output.write_stdout)
            self.process_worker.stderrSignal.connect(self.console_output.write_stderr)
        self.process_worker.finished.connect(self.process_finished)
        self.process_worker.start()

    def closeEvent(self, event):
        if self.is_finished:
            self.deleteLater()
            event.accept()
        else:
            event.ignore()
            QMessageBox.warning(
                self,
                "Closing not possible!",
                "You can't close the Dialog before this Process finished!",
            )


def get_user_input_string(prompt, title="Input required!", force=False):
    # Determine GUI or non-GUI-mode
    if QS().value("gui") and any([obj is not None for obj in _object_refs.values()]):
        parent = _object_refs["main_window"] or _object_refs["welcome_window"]
    else:
        parent = None
    if parent is not None:
        user_input, ok = QInputDialog.getText(parent, title, prompt)
    else:
        user_input = input(f"{title}: {prompt}")
        ok = True

    # Check user input
    if not user_input or not ok:
        if force:
            if parent:
                QMessageBox().warning(
                    parent,
                    "Input required!",
                    "You need to provide an appropriate input to proceed!",
                )
            else:
                logger().warning(
                    "Input required! You need to provide "
                    "an appropriate input to proceed!"
                )
            user_input = get_user_input_string(prompt, title, force)
        else:
            user_input = None

    return user_input


# ToDo: Tweak Colors
theme_colors = {
    "light": {
        "foreground": "#000000",
        "foreground_disabled": "#A0A0A0",
        "background": "#FFFFFF",
        "alternate_background": "#F0F0F0",
        "primary": "#007ACC",
        "secondary": "#005F8C",
        "border": "#D4D4D4",
        "link": "#007ACC",
    },
    "dark": {
        "foreground": "#FFFFFF",
        "foreground_disabled": "#A0A0A0",
        "background": "#1E1E1E",
        "alternate_background": "#2E2E2E",
        "primary": "#007ACC",
        "secondary": "#005F8C",
        "border": "#D4D4D4",
        "link": "#007ACC",
    },
    "high_contrast": {
        "foreground": "#000000",
        "foreground_disabled": "#A0A0A0",
        "background": "#FFFFFF",
        "alternate_background": "#F0F0F0",
        "primary": "#007ACC",
        "secondary": "#005F8C",
        "border": "#D4D4D4",
        "link": "#007ACC",
    },
}


def get_palette(theme):
    colors = {k: QColor(v) for k, v in theme_colors[theme].items()}
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.WindowText, colors["foreground"])
    palette.setColor(QPalette.ColorRole.Button, colors["background"])
    palette.setColor(QPalette.ColorRole.ButtonText, colors["primary"])
    palette.setColor(QPalette.ColorRole.Base, colors["background"])
    palette.setColor(QPalette.ColorRole.Window, colors["background"])
    palette.setColor(QPalette.ColorRole.Highlight, colors["primary"])
    palette.setColor(QPalette.ColorRole.HighlightedText, colors["background"])
    palette.setColor(QPalette.ColorRole.AlternateBase, colors["alternate_background"])
    palette.setColor(QPalette.ColorRole.ToolTipBase, colors["background"])
    palette.setColor(QPalette.ColorRole.ToolTipText, colors["foreground"])
    if hasattr(QPalette.ColorRole, "Foreground"):
        palette.setColor(QPalette.ColorRole.Foreground, colors["foreground"])
    palette.setColor(QPalette.ColorRole.Light, colors["border"])
    palette.setColor(QPalette.ColorRole.Midlight, colors["border"])
    palette.setColor(QPalette.ColorRole.Dark, colors["border"])
    palette.setColor(QPalette.ColorRole.Mid, colors["border"])
    palette.setColor(QPalette.ColorRole.Shadow, colors["border"])
    palette.setColor(QPalette.ColorRole.Link, colors["primary"])
    palette.setColor(QPalette.ColorRole.LinkVisited, colors["link"])
    # disabled
    if hasattr(QPalette.ColorRole, "PlaceholderText"):
        palette.setColor(
            QPalette.ColorRole.PlaceholderText,
            colors["foreground_disabled"],
        )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        colors["foreground_disabled"],
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        colors["foreground_disabled"],
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Highlight,
        colors["foreground_disabled"],
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.HighlightedText,
        colors["foreground_disabled"],
    )
    # inactive
    palette.setColor(
        QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, colors["primary"]
    )
    palette.setColor(
        QPalette.ColorGroup.Inactive,
        QPalette.ColorRole.HighlightedText,
        colors["foreground"],
    )
    palette.setColor(QPalette.ColorRole.Text, colors["foreground"])
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        colors["foreground_disabled"],
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Link,
        colors["foreground_disabled"],
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.LinkVisited,
        colors["foreground_disabled"],
    )

    return palette


def set_app_theme():
    app = QApplication.instance()
    app_theme = QS().value("app_theme")
    # Detect system theme
    if app_theme == "auto":
        system_theme = darkdetect.theme().lower()
        if system_theme is None:
            logger().info("System theme detection failed. Using light theme.")
            system_theme = "light"
        app_theme = system_theme
    app.setPalette(get_palette(app_theme))
    # Set Icon
    if app_theme == "dark":
        icon_name = "mne_pipeline_icon_dark.png"
    else:
        icon_name = "mne_pipeline_icon_light.png"
    icon_path = join(str(resources.files(extra)), icon_name)
    app_icon = QIcon(str(icon_path))
    app.setWindowIcon(app_icon)


def set_app_style():
    app = QApplication.instance()
    app_style = QS().value("app_style")
    app.setStyle(app_style)


def set_app_font():
    app = QApplication.instance()
    font_family = QS().value("app_font")
    font_size = QS().value("app_font_size")
    app.setFont(QFont(font_family, font_size))
