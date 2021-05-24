# Import QSettings or provide Dummy-Class to be independent from PyQt/PySide
class QSettingsDummy:
    def __init__(self):
        pass

    def value(self, _, defaultValue=None):
        return None

    def setValue(self, _, __):
        pass


try:
    from PyQt5.QtCore import QSettings

    QS = QSettings
except ImportError:
    QS = QSettingsDummy
