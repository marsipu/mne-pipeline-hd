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
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                             QProgressDialog,
                             QPushButton, QScrollArea, QSpinBox, QTabWidget, QToolBar, QVBoxLayout, QWidget)
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg)

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
        self.selected_ppresets = list()

        # Stores the widgets for parameter-presets/objects
        self.all_figs = dict()
        # Stores all widget-items (including single widgets for plot_functions with multiple plots as output)
        self.all_images = dict()

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

        self.p_preset_select = CheckList(list(self.mw.pr.parameters.keys()), self.selected_ppresets,
                                         title='Select Parameter-Preset')
        list_layout.addWidget(self.p_preset_select)

        layout.addLayout(list_layout)

        bt_layout = QHBoxLayout()
        self.interactive_chkbx = QCheckBox('Interactive Plots?')

        bt_layout.addWidget(self.interactive_chkbx)

        start_bt = QPushButton('Start')
        start_bt.clicked.connect(self.load_plots)
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

    def load_plots(self):

        # Show ProgressBar
        self.total_loads = len(self.selected_obj[self.target]) * len(self.selected_ppresets)
        if self.total_loads == 0:
            QMessageBox.warning(self, 'Not enought selected!', 'An important parameter seems to be missing')
        else:
            self.prog_dlg = QProgressDialog()
            self.prog_dlg.setLabelText('Loading Plots...')
            self.prog_dlg.setMaximum(self.total_loads)
            self.prog_dlg.setCancelButton(None)
            self.prog_dlg.setMinimumDuration(0)
            self.prog_cnt = 0
            self.prog_dlg.setValue(self.prog_cnt)

            for p_preset in self.selected_ppresets:
                self.all_images[p_preset] = dict()
                self.all_figs[p_preset] = dict()
                for obj_name in self.selected_obj[self.target]:
                    if self.target == 'MEEG':
                        obj = MEEG(obj_name, self.mw)
                    elif self.target == 'FSMRI':
                        obj = FSMRI(obj_name, self.mw)
                    elif self.target == 'Group':
                        obj = Group(obj_name, self.mw)
                    else:
                        break

                    # Replace Parameter-Preset for the loaded object and reload load/save-paths
                    if p_preset != obj.p_preset:
                        obj.p_preset = p_preset
                        obj.load_paths()

                    # Load Matplotlib-Plots
                    if self.interactive_chkbx.isChecked():
                        # Get module of plot_function
                        pkg_name = self.mw.pd_funcs.loc[self.selected_func, 'pkg_name']
                        module_name = self.mw.pd_funcs.loc[self.selected_func, 'module']
                        module = self.mw.all_modules[pkg_name][module_name][0]

                        # Get Arguments for Plot-Function
                        keyword_arguments = get_arguments(self.selected_func, module, obj, self.mw)
                        plot_func = getattr(module, self.selected_func)

                        # Create Thread for Plot-Function
                        worker = Worker(plot_func, **keyword_arguments)
                        # Pass Object-Name into the plot_finished-Slot
                        # (needs to be set as default in lambda-function to survive loop)
                        worker.signals.finished.connect(lambda val, o_name=obj_name, ppreset=p_preset:
                                                        self.plot_finished(val, o_name, ppreset))
                        worker.signals.error.connect(lambda err_tuple, o_name=obj_name, ppreset=p_preset:
                                                     self.thread_error(err_tuple, o_name, ppreset, 'plot'))
                        print(f'Starting Thread for Object= {obj_name} and Parameter-Preset= {p_preset}')
                        self.mw.threadpool.start(worker)

                    # Load Plot-Images
                    else:
                        try:
                            image_paths = obj.plot_files[self.selected_func][p_preset]
                        except KeyError as ke:
                            self.all_images[p_preset][obj_name] = f'{ke} not found for {obj_name}'
                            self.thread_finished(None, obj_name, p_preset)
                        else:
                            keyword_arguments = {'image_paths': image_paths,
                                                 'obj_name': obj_name,
                                                 'p_preset': p_preset}
                            worker = Worker(self.load_images, **keyword_arguments)
                            worker.signals.finished.connect(lambda val, o_name=obj_name, ppreset=p_preset:
                                                            self.thread_finished(val, o_name, ppreset))
                            worker.signals.error.connect(lambda err_tuple, o_name=obj_name, ppreset=p_preset:
                                                         self.thread_error(err_tuple, o_name, ppreset, 'image'))
                            print(f'Starting Thread for Object= {obj_name} and Parameter-Preset= {p_preset}')
                            self.mw.threadpool.start(worker)

    def load_images(self, image_paths, obj_name, p_preset):

        # Load pixmaps from Image-Paths
        pixmaps = list()

        for image_path in image_paths:
            pixmap = QPixmap(image_path)
            pixmaps.append(pixmap)

        self.all_images[p_preset][obj_name] = pixmaps

    def thread_finished(self, _, obj_name, p_preset):
        self.prog_cnt += 1
        self.prog_dlg.setValue(self.prog_cnt)
        print(f'Finished PlotLoading-Thread for Object= {obj_name} and Parameter-Preset= {p_preset}')

        if self.prog_cnt == self.total_loads:
            # Start PlotViewer
            interactive = self.interactive_chkbx.isChecked()
            if interactive:
                items = self.all_figs
            else:
                items = self.all_images
            PlotViewer(self, items, interactive, True)
            self.hide()

    def plot_finished(self, return_value, obj_name, p_preset):

        # Check if multiple figures are given
        if not isinstance(return_value, list):
            # Make sure, that return_value is a list
            return_value = [return_value]

        fig_list = list()
        for fig in return_value:
            # Add the default size of the figure for later zooming
            fig_list.append((fig, fig.get_size_inches()))

        self.all_figs[p_preset][obj_name] = fig_list

        self.thread_finished(None, obj_name, p_preset)

    def thread_error(self, error_tuple, obj_name, p_preset, kind):
        if kind == 'image':
            self.all_images[p_preset][obj_name] = f'{error_tuple[0]}: {error_tuple[1]}'
        else:
            self.all_figs[p_preset][obj_name] = f'{error_tuple[0]}: {error_tuple[1]}'

        self.thread_finished(None, obj_name, p_preset)


class PlotViewer(QMainWindow):
    def __init__(self, parent_dlg, items, interactive, top_level):
        super().__init__(parent_dlg)
        self.items = items
        self.interactive = interactive
        self.top_level = top_level

        self.zoom_factor = 1
        self.column_count = 4

        # Stores references to all tab-widgets to control them simultaneously
        self.all_tab_widgets = list()

        set_ratio_geometry(0.8, self)
        self.init_ui()
        self.show()

    def _setup_views(self):
        viewer_layout = QHBoxLayout()

        for p_preset in self.items:
            scroll_area = QScrollArea()
            scroll_widget = QWidget()
            scroll_layout = QGridLayout()

            for obj_idx, obj_name in enumerate(self.items[p_preset]):
                obj_items = self.items[p_preset][obj_name]
                row = obj_idx // self.column_count
                col = obj_idx % self.column_count

                if isinstance(obj_items, str):
                    # This displays errors
                    scroll_layout.addWidget(QLabel(obj_items), row, col)

                elif isinstance(obj_items, list):
                    tab_widget = QTabWidget()

                    for item_idx, item in enumerate(obj_items):
                        if self.interactive:
                            fig, default_size = item
                            # Zoom Figure
                            fig.set_size_inches(default_size * self.zoom_factor)
                            view_widget = FigureCanvasQTAgg(fig)
                        else:
                            view_widget = QLabel()
                            # Zoom Pixmap
                            view_widget.setPixmap(item.scaled(item.size() * self.zoom_factor,
                                                              Qt.KeepAspectRatio, Qt.SmoothTransformation))

                        if len(obj_items) > 1:
                            tab_widget.addTab(view_widget, str(item_idx))
                        else:
                            scroll_layout.addWidget(view_widget, row, col)

                    if len(obj_items) > 1:
                        self.all_tab_widgets.append(tab_widget)
                        frame_widget = QWidget()
                        frame_layout = QVBoxLayout()
                        frame_layout.addWidget(tab_widget)
                        show_bt = QPushButton('Show')
                        show_bt.clicked.connect(partial(self.show_single_items, p_preset, obj_name))
                        frame_layout.addWidget(show_bt)
                        frame_widget.setLayout(frame_layout)
                        scroll_layout.addWidget(frame_widget, row, col)

            scroll_widget.setLayout(scroll_layout)
            scroll_area.setWidget(scroll_widget)
            viewer_layout.addWidget(scroll_area)

        self.main_layout.addLayout(viewer_layout)

    def init_ui(self):

        toolbar = QToolBar('Plot-Tools')
        self.addToolBar(toolbar)

        # Zoom-Control
        toolbar.addAction('-- Zoom', partial(self.zoom_items, '--'))
        toolbar.addAction('- Zoom', partial(self.zoom_items, '-'))
        self.zoom_label = QLabel(f'{self.zoom_factor * 100} %')
        toolbar.addWidget(self.zoom_label)
        toolbar.addAction('+ Zoom', partial(self.zoom_items, '+'))
        toolbar.addAction('++ Zoom', partial(self.zoom_items, '++'))

        # Column-Control
        toolbar.addAction('- Column', partial(self.change_columns, '-'))
        self.column_label = QLabel(f'{self.column_count} Columns')
        toolbar.addWidget(self.column_label)
        toolbar.addAction('+ Column', partial(self.change_columns, '+'))

        # Add control for all tab-widgets to turn all to selected tab(index)
        tab_sel_label = QLabel('Select Tab')
        toolbar.addWidget(tab_sel_label)
        tab_selection = QSpinBox()
        tab_selection.valueChanged.connect(self.tab_selected)
        tab_selection.setWrapping(True)
        toolbar.addWidget(tab_selection)

        toolbar.addAction('Close', self.close)

        # Central Widget
        widget = QWidget()
        self.main_layout = QVBoxLayout()

        self._setup_views()

        widget.setLayout(self.main_layout)
        self.setCentralWidget(widget)

    def tab_selected(self, idx):
        for tab_w in self.all_tab_widgets:
            tab_w.setCurrentIndex(idx)

    def update_layout(self):
        old_layout = self.main_layout.itemAt(0)
        self.main_layout.removeItem(old_layout)
        for scroll_area in [old_layout.itemAt(idx) for idx in range(old_layout.count())]:
            scroll_area.widget().deleteLater()
        del old_layout

        self._setup_views()

    def change_columns(self, direction):
        # Set Column-Count
        if direction == '+':
            self.column_count += 1
        else:
            self.column_count -= 1

        # Make sure, that at least one column is shown
        if self.column_count < 1:
            self.column_count = 1

        self.column_label.setText(f'{self.column_count} Columns')
        self.update_layout()

    def zoom_items(self, zoom):
        # Zoom-Labels
        if zoom == '+':
            self.zoom_factor += 0.1
        elif zoom == '++':
            self.zoom_factor += 0.5
        elif zoom == '-':
            self.zoom_factor -= 0.1
        else:
            self.zoom_factor -= 0.5

        # Make sure, that zoom is not smaller than 10%
        if self.zoom_factor < 0.1:
            self.zoom_factor = 0.1

        self.zoom_label.setText(f'{self.zoom_factor * 100} %')
        self.update_layout()

    def show_single_items(self, p_preset, obj_name):
        # Create dictionary similar to what you get from loading to open a new viewer with just the selected items
        if self.interactive:
            items = self.all_figs[p_preset][obj_name]
        else:
            items = self.all_images[p_preset][obj_name]
        item_dict = {'Default': {idx: value for idx, value in enumerate(items)}}
        PlotViewer(self, item_dict, self.interactive, False)

    def closeEvent(self, event):
        if self.top_level:
            self.parent().show()

        event.accept()
