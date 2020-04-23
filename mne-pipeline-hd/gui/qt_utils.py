import sys
import traceback

from PyQt5.QtCore import QRunnable, pyqtSlot


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, fn, signal_class, *args, **kwargs):
        super().__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signal_class = signal_class

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            # Todo: Logging in Worker-Class
            # logging.error('Ups, something happened:')
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signal_class.error.emit((exctype, value, traceback.format_exc(limit=-10)))
        finally:
            self.signal_class.finished.emit()  # Done
