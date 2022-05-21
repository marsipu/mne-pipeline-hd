import sys
import traceback
from ast import literal_eval

from PyQt5.QtWidgets import *
from mne_pipeline_hd.gui import parameter_widgets
from mne_pipeline_hd.gui.base_widgets import SimpleDict


class Widget(QWidget):

    def __init__(self, parent=None):
        super(Widget, self).__init__()

        icons = [
            'SP_ArrowBack',
            'SP_ArrowDown',
            'SP_ArrowForward',
            'SP_ArrowLeft',
            'SP_ArrowRight',
            'SP_ArrowUp',
            'SP_BrowserReload',
            'SP_BrowserStop',
            'SP_CommandLink',
            'SP_ComputerIcon',
            'SP_CustomBase',
            'SP_DesktopIcon',
            'SP_DialogApplyButton',
            'SP_DialogCancelButton',
            'SP_DialogCloseButton',
            'SP_DialogDiscardButton',
            'SP_DialogHelpButton',
            'SP_DialogNoButton',
            'SP_DialogOkButton',
            'SP_DialogOpenButton',
            'SP_DialogResetButton',
            'SP_DialogSaveButton',
            'SP_DialogYesButton',
            'SP_DirClosedIcon',
            'SP_DirHomeIcon',
            'SP_DirIcon',
            'SP_DirLinkIcon',
            'SP_DirOpenIcon',
            'SP_DockWidgetCloseButton',
            'SP_DriveCDIcon',
            'SP_DriveDVDIcon',
            'SP_DriveFDIcon',
            'SP_DriveHDIcon',
            'SP_DriveNetIcon',
            'SP_FileDialogBack',
            'SP_FileDialogContentsView',
            'SP_FileDialogDetailedView',
            'SP_FileDialogEnd',
            'SP_FileDialogInfoView',
            'SP_FileDialogListView',
            'SP_FileDialogNewFolder',
            'SP_FileDialogStart',
            'SP_FileDialogToParent',
            'SP_FileIcon',
            'SP_FileLinkIcon',
            'SP_MediaPause',
            'SP_MediaPlay',
            'SP_MediaSeekBackward',
            'SP_MediaSeekForward',
            'SP_MediaSkipBackward',
            'SP_MediaSkipForward',
            'SP_MediaStop',
            'SP_MediaVolume',
            'SP_MediaVolumeMuted',
            'SP_MessageBoxCritical',
            'SP_MessageBoxInformation',
            'SP_MessageBoxQuestion',
            'SP_MessageBoxWarning',
            'SP_TitleBarCloseButton',
            'SP_TitleBarContextHelpButton',
            'SP_TitleBarMaxButton',
            'SP_TitleBarMenuButton',
            'SP_TitleBarMinButton',
            'SP_TitleBarNormalButton',
            'SP_TitleBarShadeButton',
            'SP_TitleBarUnshadeButton',
            'SP_ToolBarHorizontalExtensionButton',
            'SP_ToolBarVerticalExtensionButton',
            'SP_TrashIcon',
            'SP_VistaShield'
        ]

        colSize = 4

        layout = QGridLayout()

        count = 0
        for i in icons:
            btn = QPushButton(i)
            btn.setIcon(self.style().standardIcon(getattr(QStyle, i)))

            layout.addWidget(btn, int(count / colSize), int(count % colSize))
            count += 1

        self.setLayout(layout)


def show_standard_widgets():
    dialog = Widget()
    dialog.show()


class ParamGuis(QWidget):
    def __init__(self):
        super().__init__()
        self.parameters = {'IntGui': 1,
                           'FloatGui': 5.3,
                           'StringGui': 'Havona',
                           'MultiTypeGui': 42,
                           'FuncGui': 5000,
                           'BoolGui': True,
                           'TupleGui': (45, 6),
                           'ComboGui': 'a',
                           'ListGui': [1, 454.33, 'post_central-lh', 5],
                           'CheckListGui': ['bananaaa'],
                           'DictGui': {'A': 'hubi', 'B': 58.144, 3: 'post_lh'},
                           'SliderGui': 5}

        self.keyword_args = {
            'IntGui': {'min_val': -4,
                       'max_val': 10,
                       'param_unit': 't'},
            'FloatGui': {'min_val': -18,
                         'max_val': 64,
                         'step': 0.4,
                         'param_unit': 'flurbo'},
            'StringGui': {'input_mask': 'ppAAA.AA;_',
                          'param_unit': 'N'},
            'MultiTypeGui': {'type_selection': True},
            'FuncGui': {'param_unit': 'u'},
            'BoolGui': {},
            'TupleGui': {'min_val': -10,
                         'max_val': 100,
                         'step': 1,
                         'param_unit': 'Nm'},
            'ComboGui': {'options': {'a': 'A', 'b': 'B', 'c': 'C'},
                         'param_unit': 'g'},
            'ListGui': {'param_unit': 'mol'},
            'CheckListGui': {'options': ['lemon', 'pineapple', 'bananaaa'],
                             'param_unit': 'V'},
            'DictGui': {'param_unit': '°C'},
            'SliderGui': {'min_val': -10,
                          'max_val': 10,
                          'step': 0.01,
                          'param_unit': 'Hz'}
        }

        self.gui_dict = dict()

        self.init_ui()

    def init_ui(self):
        test_layout = QVBoxLayout()
        grid_layout = QGridLayout()
        max_cols = 4
        set_none_select = True
        set_groupbox_layout = True
        set_param_alias = False

        for idx, gui_nm in enumerate(self.keyword_args):
            kw_args = self.keyword_args[gui_nm]
            kw_args['none_select'] = set_none_select
            kw_args['groupbox_layout'] = set_groupbox_layout
            if set_param_alias:
                kw_args['param_alias'] = gui_nm + '-alias'
            kw_args['description'] = gui_nm + '-description'
            gui = getattr(parameter_widgets, gui_nm)(self.parameters, gui_nm,
                                                     **kw_args)
            grid_layout.addWidget(gui, idx // max_cols, idx % max_cols)
            self.gui_dict[gui_nm] = gui

        test_layout.addLayout(grid_layout)

        set_layout = QHBoxLayout()
        self.gui_cmbx = QComboBox()
        self.gui_cmbx.addItems(self.gui_dict.keys())
        set_layout.addWidget(self.gui_cmbx)

        self.set_le = QLineEdit()
        set_layout.addWidget(self.set_le)

        set_bt = QPushButton('Set')
        set_bt.clicked.connect(self.set_param)
        set_layout.addWidget(set_bt)

        show_bt = QPushButton('Show Parameters')
        show_bt.clicked.connect(self.show_parameters)
        set_layout.addWidget(show_bt)

        test_layout.addLayout(set_layout)

        self.setLayout(test_layout)

    def set_param(self):
        try:
            current_gui = self.gui_cmbx.currentText()
            try:
                value = literal_eval(self.set_le.text())
            except (SyntaxError, ValueError):
                value = self.set_le.text()
            self.parameters[current_gui] = value
            p_gui = self.gui_dict[current_gui]
            p_gui.read_param()
            p_gui.set_param()
        except:
            print(traceback.format_exc())

    def show_parameters(self):
        dlg = QDialog(self)
        layout = QVBoxLayout()
        layout.addWidget(SimpleDict(self.parameters))
        dlg.setLayout(layout)
        dlg.open()


def show_param_gui_test():
    test_widget = ParamGuis()
    test_widget.show()


if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    show_standard_widgets()
    show_param_gui_test()
    app.exec()
