# Import QSettings or provide Dummy-Class to be independent from PyQt/PySide
import json
import sys
from ast import literal_eval
from copy import deepcopy
from importlib import resources
from os.path import join, isfile
from pathlib import Path

from ._version import __version__  # noqa

ismac = sys.platform.startswith("darwin")
iswin = sys.platform.startswith("win32")
islin = not ismac and not iswin


# Keep reference to Qt-objects without parent to avoid garbage collection
_object_refs = {'welcome_window': None,
                'main_window': None}


class BaseSettings:
    def __init__(self):
        # Load default settings
        with resources.open_text('mne_pipeline_hd.pipeline_resources',
                                 'default_settings.json') as file:
            self.default_qsettings = json.load(file)['qsettings']

    def get_default(self, name):
        if name in self.default_qsettings:
            return self.default_qsettings[name]
        else:
            raise RuntimeError(f'{name} not in default_settings.json! '
                               f'Please add it or fix the bug.')


class QSettingsDummy(BaseSettings):
    def __init__(self):
        super().__init__()

        self.settings_path = join(Path.home(), 'mnephd_settings.json')

    def _load_settings(self):
        if isfile(self.settings_path):
            with open(self.settings_path, 'r') as file:
                self.settings = json.load(file)
        else:
            self.settings = deepcopy(self.default_qsettings)

    def _write_settings(self):
        with open(self.settings_path, 'w') as file:
            json.dump(self.settings, file)

    def value(self, setting, defaultValue=None):
        self._load_settings()
        if setting in self.settings:
            return self.settings[setting]

        if defaultValue is None:
            return self.get_default(setting)
        else:
            return defaultValue

    def setValue(self, setting, value):
        self._load_settings()
        self.settings[setting] = value
        self._write_settings()


try:
    from PyQt5.QtCore import QSettings

    # ToDo: Test
    class ModQSettings(QSettings, BaseSettings):
        def __init__(self):
            super(QSettings, self).__init__()
            super(BaseSettings, self).__init__()

        def value(self, setting, defaultValue=None):
            loaded_value = super().value(setting, defaultValue=defaultValue)
            # Type-Conversion for UNIX-Systems (ini-File does not preserve type,
            # converts to strings)
            if not isinstance(loaded_value, type(self.get_default(setting))):
                try:
                    loaded_value = literal_eval(loaded_value)
                except (SyntaxError, ValueError):
                    return self.get_default(setting)
            if loaded_value is None:
                if defaultValue is None:
                    return self.get_default(setting)
                else:
                    return defaultValue
            else:
                return loaded_value

    class QS(ModQSettings):
        def __init__(self):
            super().__init__()

except ImportError:

    class QS(QSettingsDummy):
        def __init__(self):
            super().__init__()
