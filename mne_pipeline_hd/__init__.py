# Import QSettings or provide Dummy-Class to be independent from PyQt/PySide
import json
from importlib import resources


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

    def value(self, setting, defaultValue=None):
        if defaultValue is None:
            return self.get_default(setting)
        else:
            return defaultValue

    def setValue(self, _, __):
        pass


try:
    from PyQt5.QtCore import QSettings


    class ModQSettings(QSettings, BaseSettings):
        def __init__(self):
            super(QSettings, self).__init__()
            super(BaseSettings, self).__init__()

        def value(self, setting, defaultValue=None, type=None):
            loaded_value = super().value(setting, defaultValue)
            if loaded_value is None:
                if defaultValue is None:
                    return super().get_default(setting)
                else:
                    return defaultValue
            else:
                return loaded_value

    QS = ModQSettings

except ImportError:

    QS = QSettingsDummy
