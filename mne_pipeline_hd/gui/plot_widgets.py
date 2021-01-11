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
from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImageReader, QPixmap
from PyQt5.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QProgressDialog, QPushButton,
                             QScrollArea,
                             QSizePolicy,
                             QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget)
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg, NavigationToolbar2QT)

from mne_pipeline_hd.gui.base_widgets import CheckList, SimpleList
from mne_pipeline_hd.gui.gui_utils import Worker, set_ratio_geometry
from mne_pipeline_hd.pipeline_functions.function_utils import get_arguments
from mne_pipeline_hd.pipeline_functions.loading import FSMRI, Group, MEEG


class PlotViewSelection(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

        self.selected_func = None
        self.target = None
        self.selected_obj = {'MEEG': list(),
                             'FSMRI': list(),
                             'Group': list()}
        self.selected_ppreset = list()
        self.interactive = False

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()
        list_layout = QHBoxLayout()

        func_list = self.mw.pd_funcs.loc[self.mw.pd_funcs.loc[:, 'tab'] == 'Plot'].index
        func_select = SimpleList(func_list, title='Select Plot-Function')
        func_select.currentChanged.connect(self.func_selected)
        list_layout.addWidget(func_select)

        self.obj_select = CheckList(title='Select Objects')
        list_layout.addWidget(self.obj_select)

        self.p_preset_select = CheckList(list(self.mw.pr.parameters.keys()), self.selected_ppreset,
                                         title='Select P-Preset\n(Default if none selected)')
        list_layout.addWidget(self.p_preset_select)

        layout.addLayout(list_layout)

        bt_layout = QHBoxLayout()
        self.interactive_chkbx = QCheckBox('Interactive Plots?')

        bt_layout.addWidget(self.interactive_chkbx)

        start_bt = QPushButton('Start')
        start_bt.clicked.connect(self.start)
        bt_layout.addWidget(start_bt)

        cancel_bt = QPushButton('Cancel')
        cancel_bt.clicked.connect(self.close)
        bt_layout.addWidget(cancel_bt)

        layout.addLayout(bt_layout)
        self.setLayout(layout)

    def func_selected(self, func):
        """Get selected function and adjust contents of Object-Selection to target"""
        self.selected_func = func
        self.target = self.mw.pd_funcs.loc[func, 'target']
        if self.target == 'MEEG':
            self.obj_select.replace_data(self.mw.pr.all_meeg)
            self.obj_select.replace_checked(self.selected_obj['MEEG'])
        elif self.target == 'FSMRI':
            self.obj_select.replace_data(self.mw.pr.all_fsmri)
            self.obj_select.replace_checked(self.selected_obj['FSMRI'])
        elif self.target == 'Group':
            self.obj_select.replace_data(list(self.mw.pr.all_groups.keys()))
            self.obj_select.replace_checked(self.selected_obj['Group'])

    def start(self):
        """Start PlotViewer with the selected parameters from this function and hide this window"""
        PlotViewer(self.mw, func_name=self.selected_func, objs=self.selected_obj[self.target], target=self.target,
                   p_presets=self.selected_ppreset,
                   interactive=self.interactive_chkbx.isChecked())
        self.close()


class PlotViewer(QDialog):
    def __init__(self, main_win, func_name, objs, target, p_presets, interactive):
        super().__init__(main_win)
        self.mw = main_win
        self.func_name = func_name
        self.objs = objs
        self.target = target
        self.p_presets = p_presets
        self.interactive = interactive

        # Stores the widgets for parameter-presets/objects
        self.plot_widgets = dict()
        # Stores all widget-items (including single widgets for plot_functions with multiple plots as output)
        self.plot_items = dict()
        # Stores references to all tab-widgets to control them simultaneously
        self.all_tab_widgets = list()

        for p_preset in self.p_presets:
            self.plot_widgets[p_preset] = dict()
            self.plot_items[p_preset] = dict()
            self.init_widgets[p_preset] = dict()
            for obj_name in self.objs:
                self.plot_items[p_preset][obj_name] = list()
                self.plot_widgets[p_preset][obj_name] = None

        # Stores layouts
        self.layout_dict = dict()

        # A list to store all toolbars to collectively hide&show them
        self.all_toolbars = list()

        set_ratio_geometry(0.85, self)

        self.load_plots()
        self.open()

    def load_plots(self):

        # Show ProgressBar
        self.total_loads = len(self.objs) * len(self.p_presets)
        self.prog_dlg = QProgressDialog('Loading Plots...', maximum=self.total_loads)
        self.prog_dlg.setCancelButton(None)
        self.prog_cnt = 0

        for obj_name in self.objs:
            if self.target == 'MEEG':
                obj = MEEG(obj_name, self.mw)
            elif self.target == 'FSMRI':
                obj = FSMRI(obj_name, self.mw)
            elif self.target == 'Group':
                obj = Group(obj_name, self.mw)
            else:
                break

            for p_preset in self.p_presets:

                # Load Matplotlib-Plots
                if self.interactive:
                    # Get module of plot_function
                    pkg_name = self.mw.pd_funcs.loc[self.func_name, 'pkg_name']
                    module_name = self.mw.pd_funcs.loc[self.func_name, 'module']
                    module = self.mw.all_modules[pkg_name][module_name]

                    # Replace Parameter-Preset for the loaded object and reload load/save-paths
                    if p_preset != obj.p_preset:
                        obj.p_preset = p_preset
                        obj.load_paths()

                    # Get Arguments for Plot-Function
                    keyword_arguments = get_arguments(self.func_name, module, obj, self.mw)
                    plot_func = getattr(module, self.func_name)

                    # Create Thread for Plot-Function
                    worker = Worker(plot_func, **keyword_arguments)
                    # Pass Object-Name into the plot_finished-Slot
                    # (needs to be set as default in lambda-function to survive loop)
                    worker.signals.finished.connect(lambda val, o_name=obj_name, ppreset=p_preset:
                                                    self.plot_finished(val, o_name, ppreset))
                    worker.signals.error.connect(lambda err_tuple, o_name=obj_name, ppreset=p_preset:
                                                 self.plot_error(err_tuple, o_name, ppreset))
                    print(f'Starting Thread for Object= {obj_name} and Parameter-Preset= {p_preset}')
                    self.mw.threadpool.start(worker)

                # Load Plot-Images
                else:
                    try:
                        image_paths = obj.plot_files[self.func_name][p_preset]
                    except KeyError as ke:
                        self.plot_widgets[p_preset][obj_name] = QLabel(f'{ke} not found for {obj_name}')
                    else:
                        keyword_arguments = {'image_paths': image_paths,
                                             'obj_name': obj_name,
                                             'p_preset': p_preset}
                        worker = Worker(self.load_images, **keyword_arguments)
                        worker.signals.finished.connect(lambda val, o_name=obj_name, ppreset=p_preset:
                                                        self.load_finished(val, o_name, ppreset))
                        worker.signals.error.connect(lambda err_tuple, o_name=obj_name, ppreset=p_preset:
                                                     self.plot_error(err_tuple, o_name, ppreset))
                        print(f'Starting Thread for Object= {obj_name} and Parameter-Preset= {p_preset}')
                        self.mw.threadpool.start(worker)

    def load_images(self, image_paths, obj_name, p_preset):

        # Load Images from Image-Paths and build a QTabWidget
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout = QVBoxLayout()

        if len(image_paths) > 1:
            tab_widget = QTabWidget()
            self.all_tab_widgets.append(tab_widget)
            for idx, image_path in enumerate(image_paths):
                image_label = QLabel()
                image_label.setScaledContents(True)
                image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
                image_label.setPixmap(QPixmap(image_path))
                image_label.adjustSize()
                self.plot_items[p_preset][obj_name].append(image_label)
                tab_widget.addTab(image_label, str(idx))
            layout.addWidget(tab_widget)

            # Button to show all plots of this object in a separate Window
            show_bt = QPushButton('Show')
            show_bt.clicked.connect(partial(self.show_single_items, p_preset, obj_name))
            layout.addWidget(show_bt)

        elif len(image_paths) == 1:
            image_label = QLabel()
            image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            image_label.setScaledContents(True)
            image_label.setPixmap(QPixmap(image_paths[0]))
            self.plot_items[p_preset][obj_name].append(image_label)
            layout.addWidget(image_label)

        widget.setLayout(layout)
        self.plot_widgets[p_preset][obj_name] = widget

    def show_single_items(self, p_preset, obj_name):
        widgets = self.plot_items[p_preset][obj_name]
        SingleItemViewer(self, widgets)

    def plot_finished(self, return_value, obj_name, p_preset):

        if not isinstance(return_value, list):
            return_value = [return_value]

        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout = QVBoxLayout()

        if len(return_value) > 1:
            tab_widget = QTabWidget()
            self.all_tab_widgets.append(tab_widget)
            for idx, fig in enumerate(return_value):
                plot_widget = QWidget()
                plot_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
                plot_layout = QVBoxLayout()
                fig_widget = FigureCanvasQTAgg(fig)
                plot_layout.addWidget(fig_widget)
                toolbar = NavigationToolbar2QT(fig_widget, plot_widget)
                self.all_toolbars.append(toolbar)
                plot_layout.addWidget(toolbar)
                plot_widget.setLayout(plot_layout)
                plot_widget.adjustSize()
                tab_widget.addTab(plot_widget, str(idx))
                self.plot_items[p_preset][obj_name] = plot_widget

            layout.addWidget(tab_widget)

            # Button to show all plots of this object in a separate Window
            show_bt = QPushButton('Show')
            show_bt.clicked.connect(partial(self.show_single_items, p_preset, obj_name))
            layout.addWidget(show_bt)

        elif len(return_value) == 1:
            plot_widget = QWidget()
            plot_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            plot_layout = QVBoxLayout()
            fig_widget = FigureCanvasQTAgg(return_value[0])
            plot_layout.addWidget(fig_widget)
            toolbar = NavigationToolbar2QT(fig_widget, plot_widget)
            self.all_toolbars.append(toolbar)
            plot_layout.addWidget(toolbar)
            plot_widget.setLayout(plot_layout)
            self.plot_items[p_preset][obj_name] = plot_widget

        widget.setLayout(layout)
        self.plot_widgets[p_preset][obj_name] = widget

        self.prog_cnt += 1
        self.prog_dlg.setValue(self.prog_cnt)
        print(f'Finished PlotLoading-Thread for Object= {obj_name} and Parameter-Preset= {p_preset}')

        if self.prog_cnt == self.total_loads:
            self.init_ui()

    def plot_error(self, error_tuple, obj_name, p_preset):
        self.plot_widgets[p_preset][obj_name] = QLabel(f'{error_tuple[0]}: {error_tuple[1]}')

    def load_finished(self, _, obj_name, p_preset):
        self.prog_cnt += 1
        self.prog_dlg.setValue(self.prog_cnt)
        print(f'Finished PlotLoading-Thread for Object= {obj_name} and Parameter-Preset= {p_preset}')

        if self.prog_cnt == self.total_loads:
            self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        control_layout = QHBoxLayout()

        # Add control for all tab-widgets to turn all to selected tab(index)
        if len(self.all_tab_widgets) > 0:
            n_tabs = self.all_tab_widgets[0].count()
            tab_selection = QSpinBox()
            tab_selection.valueChanged.connect(self.tab_selected)
            tab_selection.setRange(0, n_tabs)
            tab_selection.setWrapping(True)
            control_layout.addWidget(tab_selection)

        self.zoom_label = QLabel('Zoom: 3 per Row')
        control_layout.addWidget(self.zoom_label)
        zoom_in_bt = QPushButton('Zoom-In')
        zoom_in_bt.clicked.connect(partial(self.zoom_layout, 'in'))
        control_layout.addWidget(zoom_in_bt)
        zoom_out_bt = QPushButton('Zoom-Out')
        zoom_out_bt.clicked.connect(partial(self.zoom_layout, 'out'))
        control_layout.addWidget(zoom_out_bt)

        layout.addLayout(control_layout)

        p_preset_layout = QHBoxLayout()
        for p_preset in self.plot_widgets:
            scroll_area = QScrollArea()
            scroll_widget = QWidget()
            scroll_layout = QGridLayout()
            self.layout_dict[p_preset] = scroll_layout

            for idx, obj_name in enumerate(self.plot_widgets[p_preset]):
                row = idx // 4
                col = idx % 4

                scroll_layout.addWidget(widget, row, col)

            scroll_widget.setLayout(scroll_layout)
            scroll_area.setWidget(scroll_widget)
            p_preset_layout.addWidget(scroll_area)

        layout.addLayout(p_preset_layout)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def tab_selected(self, idx):
        for tab_w in self.all_tab_widgets:
            tab_w.setCurrentIndex(idx)

    def zoom_layout(self, direction):
        pass


class SingleItemViewer(QDialog):
    def __init__(self, parent_dlg, widgets):
        super().__init__(parent_dlg)
        self.widgets = widgets

        set_ratio_geometry(0.8, self)
        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()
        scroll_area = QScrollArea()

        child_widget = QWidget()
        child_layout = QVBoxLayout()
        for wdg in self.widgets:
            child_layout.addWidget(wdg)
        child_widget.setLayout(child_layout)

        layout.addWidget(scroll_area)

        close_bt = QPushButton('Close')
        close_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)
