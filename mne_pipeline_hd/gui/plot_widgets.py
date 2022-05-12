# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import logging
from functools import partial
from importlib import import_module
from os.path import join, isfile

from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (QMainWindow, QWidget, QGridLayout, QComboBox,
                             QTabWidget, QVBoxLayout, QDialog, QHBoxLayout,
                             QCheckBox, QPushButton, QMessageBox,
                             QProgressDialog, QLabel, QScrollArea, QToolBar,
                             QSpinBox)
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mne.viz import Brain, Figure3D
from mne_qt_browser.figure import MNEQtBrowser

from mne_pipeline_hd import _object_refs
from mne_pipeline_hd.gui.base_widgets import SimpleList, CheckList
from mne_pipeline_hd.gui.gui_utils import Worker, set_ratio_geometry
from mne_pipeline_hd.pipeline_functions.function_utils import get_arguments
from mne_pipeline_hd.pipeline_functions.loading import MEEG, FSMRI, Group


class PlotManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.plots = dict()
        self.init_ui()
        self.show()

    def init_ui(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        self.name_cmbx = QComboBox()
        self.name_cmbx.activated.connect(self.name_changed)
        layout.addWidget(self.name_cmbx, 0, 0)
        self.func_list = SimpleList()
        layout.addWidget(self.func_list)
        self.plot_viewer = QWidget()
        self.plot_viewer_layout = QVBoxLayout(self.plot_viewer)
        layout.addWidget(self.plot_viewer, 0, 1, 2, 1)
        self.setCentralWidget(widget)

    def name_changed(self):
        new_name = self.name_cmbx.currentText()
        self.func_list.replace_data(list(self.plots[new_name].keys()))
        self.update_plots()

    def update_plots(self, only_add=False):
        name = self.name_cmbx.currentText()
        func_name = self.func_list.get_current()
        old_item = self.plot_viewer_layout.itemAt(0)
        if only_add and old_item is not None:
            plot_tabs = old_item.widget()
            plot = self.plots[name][func_name][-1]
            plot_tabs.addTab(plot, str(len(self.plots[name][func_name]) - 1))
        else:
            if old_item is not None:
                self.plot_viewer_layout.removeItem(old_item)
            plot_tabs = QTabWidget()
            for idx, plot in enumerate(self.plots[name][func_name]):
                plot_tabs.addTab(plot, str(idx))
            self.plot_viewer_layout.addWidget(plot_tabs)

    def add_plot(self, plot, name, func_name):
        if name not in self.plots:
            self.name_cmbx.addItem(name)
            self.plots[name] = dict()
        if func_name not in self.plots[name]:
            self.plots[name][func_name] = list()
            self.func_list.model._data.append(func_name)
            self.func_list.content_changed()

        for plt in plot:
            if isinstance(plt, Figure):
                plot_widget = FigureCanvasQTAgg(plt)
                plot_widget.setFocusPolicy(Qt.FocusPolicy(Qt.StrongFocus |
                                                          Qt.WheelFocus))
                plot_widget.setFocus()
            elif isinstance(plt, MNEQtBrowser):
                plot_widget = plt
            elif isinstance(plt, Brain):
                plot_widget = plt
            elif isinstance(plt, Figure3D):
                plot_widget = plt
            else:
                logging.error(f'Unrecognized type "{type(plt)}" '
                              f'for "{func_name}"')
                plot_widget = QWidget()

            self.plots[name][func_name].append(plot_widget)

            if self.name_cmbx.currentText() == name \
                    and self.func_list.get_current() == func_name:
                self.update_plots(only_add=True)

    def closeEvent(self, event):
        _object_refs['plot_manager'] = None
        event.accept()


def show_plot_manager():
    if _object_refs['plot_manager'] is None:
        plot_manager = PlotManager()
        _object_refs['plot_manager'] = plot_manager

    return _object_refs['plot_manager']


class PlotViewSelection(QDialog):
    """The user selects the plot-function and the objects to show for this plot_function
    """

    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.ct = main_win.ct

        self.selected_func = None
        self.target = None
        self.interactive = False
        self.objects = list()
        self.selected_objs = list()
        self.selected_ppresets = list()

        # Stores the widgets for parameter-presets/objects
        self.all_figs = dict()
        # Stores all widget-items (including single widgets for plot_functions with multiple plots as output)
        self.all_images = dict()

        self.init_ui()
        self.show()

    def init_ui(self):
        layout = QVBoxLayout()
        list_layout = QHBoxLayout()

        func_list = self.ct.pd_funcs[(self.ct.pd_funcs['matplotlib'] == True) |
                                     (self.ct.pd_funcs[
                                          'mayavi'] == True)].index
        func_select = SimpleList(func_list, title='Select Plot-Function')
        func_select.currentChanged.connect(self.func_selected)
        list_layout.addWidget(func_select)

        self.p_preset_select = CheckList(list(self.ct.pr.parameters.keys()),
                                         self.selected_ppresets,
                                         title='Select Parameter-Preset')
        self.p_preset_select.checkedChanged.connect(self.update_objects)
        list_layout.addWidget(self.p_preset_select)

        self.obj_select = CheckList(data=self.objects,
                                    checked=self.selected_objs,
                                    title='Select Objects')
        list_layout.addWidget(self.obj_select)

        layout.addLayout(list_layout)

        bt_layout = QHBoxLayout()
        # Interactive not useful at the moment because the plots loose interactivity when coming from the thread
        self.interactive_chkbx = QCheckBox('Interactive Plots?')
        self.interactive_chkbx.toggled.connect(self.interactive_toggled)
        # bt_layout.addWidget(self.interactive_chkbx)

        start_bt = QPushButton('Start')
        start_bt.clicked.connect(self.load_plots)
        bt_layout.addWidget(start_bt)

        cancel_bt = QPushButton('Cancel')
        cancel_bt.clicked.connect(self.close)
        bt_layout.addWidget(cancel_bt)

        layout.addLayout(bt_layout)
        self.setLayout(layout)

    def update_objects(self):
        self.objects.clear()
        if self.selected_func is not None and self.target is not None:
            # Load object-list according to target
            if self.target == 'MEEG':
                target_objects = self.ct.pr.all_meeg
            elif self.target == 'FSMRI':
                target_objects = self.ct.pr.all_fsmri
            elif self.target == 'Group':
                target_objects = list(self.ct.pr.all_groups.keys())
            else:
                target_objects = list()

            # If non-interactive only list objects where a plot-image already was saved
            if not self.interactive:
                for ob in target_objects:
                    if ob in self.ct.pr.plot_files:
                        for p_preset in self.selected_ppresets:
                            if p_preset in self.ct.pr.plot_files[ob]:
                                if self.selected_func in \
                                        self.ct.pr.plot_files[ob][p_preset]:
                                    if ob not in self.objects:
                                        self.objects.append(ob)
            else:
                self.objects = target_objects

        self.obj_select.replace_data(self.objects)

    def func_selected(self, func):
        """Get selected function and adjust contents of Object-Selection to target"""
        self.selected_func = func
        self.target = self.ct.pd_funcs.loc[func, 'target']
        self.update_objects()

    def interactive_toggled(self, checked):
        self.interactive = checked
        self.update_objects()

    def load_plots(self):
        # Clear previous dictionaries
        self.all_images.clear()
        self.all_figs.clear()

        # Show ProgressBar
        self.total_loads = len(self.selected_objs) * len(
            self.selected_ppresets)
        if self.total_loads == 0:
            QMessageBox.warning(self, 'Not enought selected!',
                                'An important parameter seems to be missing')
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
                for obj_name in self.selected_objs:
                    if self.target == 'MEEG':
                        obj = MEEG(obj_name, self.ct)
                    elif self.target == 'FSMRI':
                        obj = FSMRI(obj_name, self.ct)
                    elif self.target == 'Group':
                        obj = Group(obj_name, self.ct)
                    else:
                        break

                    # Replace Parameter-Preset for the loaded object and reload load/save-paths
                    if p_preset != obj.p_preset:
                        obj.p_preset = p_preset
                        obj.init_p_preset_deps()
                        obj.init_paths()

                    # Load Matplotlib-Plots
                    if self.interactive_chkbx.isChecked():
                        # Get module of plot_function
                        module_name = self.ct.pd_funcs.loc[
                            self.selected_func, 'module']
                        module = import_module(module_name)
                        plot_func = getattr(module, self.selected_func)

                        # Get Arguments for Plot-Function
                        keyword_arguments = get_arguments(plot_func, obj)
                        # Make sure that "show_plots" is False
                        keyword_arguments['show_plots'] = False

                        # Create Thread for Plot-Function
                        worker = Worker(plot_func, **keyword_arguments)
                        # Pass Object-Name into the plot_finished-Slot
                        # (needs to be set as default in lambda-function to survive loop)
                        worker.signals.finished.connect(
                            lambda val, o_name=obj_name, ppreset=p_preset:
                            self.plot_finished(val, o_name, ppreset))
                        worker.signals.error.connect(
                            lambda err_tuple, o_name=obj_name,
                                   ppreset=p_preset:
                            self.thread_error(err_tuple, o_name, ppreset,
                                              'plot'))
                        print(
                            f'Starting Thread for Object= {obj_name} and Parameter-Preset= {p_preset}')
                        QThreadPool.globalInstance().start(worker)

                    # Load Plot-Images
                    else:
                        try:
                            image_paths = [join(obj.figures_path, p) for p in
                                           obj.plot_files[self.selected_func]]
                        except KeyError as ke:
                            self.all_images[p_preset][
                                obj_name] = f'{ke} not found for {obj_name}'
                            self.thread_finished(None)
                        else:
                            # Load pixmaps from Image-Paths
                            pixmaps = list()

                            for image_path in image_paths:
                                if isfile(image_path):
                                    pixmap = QPixmap(image_path)
                                    pixmaps.append(pixmap)

                            self.all_images[p_preset][obj_name] = pixmaps

                            self.thread_finished(None)

    def thread_finished(self, _, ):
        self.prog_cnt += 1
        self.prog_dlg.setValue(self.prog_cnt)

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

        self.thread_finished(None)

    def thread_error(self, error_tuple, obj_name, p_preset, kind):
        if kind == 'image':
            self.all_images[p_preset][
                obj_name] = f'{error_tuple[0]}: {error_tuple[1]}'
        else:
            self.all_figs[p_preset][
                obj_name] = f'{error_tuple[0]}: {error_tuple[1]}'

        self.thread_finished(None)

    def closeEvent(self, event):
        for p_preset in self.all_figs:
            for obj_name in self.all_figs[p_preset]:
                for fig_tuple in self.all_figs[p_preset][obj_name]:
                    plt.close(fig_tuple[0])


class PlotViewer(QMainWindow):
    def __init__(self, parent_dlg, items, interactive, top_level):
        super().__init__(parent_dlg)
        self.items = items
        self.interactive = interactive
        self.top_level = top_level

        self.zoom_factor = 80  # In percent
        self.column_count = 4

        set_ratio_geometry(0.8, self)
        self.init_ui()
        self.show()

    def _setup_views(self):
        viewer_layout = QHBoxLayout()

        # Get the figures/images
        for p_preset in self.items:
            p_preset_layout = QVBoxLayout()
            p_preset_label = QLabel(p_preset)
            p_preset_label.setFont(QFont('AnyStlye', 16, QFont.Bold))
            p_preset_layout.addWidget(p_preset_label,
                                      alignment=Qt.AlignHCenter)

            scroll_area = QScrollArea()
            scroll_widget = QWidget()
            scroll_layout = QGridLayout()

            for obj_idx, obj_name in enumerate(self.items[p_preset]):
                obj_items = self.items[p_preset][obj_name]
                row = obj_idx // self.column_count
                col = obj_idx % self.column_count

                # Add name-label
                name_label = QLabel(str(obj_name))
                name_label.setFont(QFont('AnyType', 14))

                if isinstance(obj_items, str):
                    # This displays errors
                    error_layout = QVBoxLayout()
                    error_layout.addWidget(name_label,
                                           alignment=Qt.AlignHCenter)
                    error_layout.addWidget(QLabel(obj_items))
                    scroll_layout.addLayout(error_layout, row, col)

                elif isinstance(obj_items, list):
                    tab_widget = QTabWidget()
                    obj_layout = QVBoxLayout()
                    for item_idx, item in enumerate(obj_items):
                        if self.interactive:
                            fig, default_size = item
                            # Zoom Figure
                            fig.set_size_inches(
                                default_size * (self.zoom_factor / 100))
                            view_widget = FigureCanvasQTAgg(fig)
                        else:
                            view_widget = QLabel()
                            # Zoom Pixmap
                            view_widget.setPixmap(
                                item.scaled(
                                    item.size() * (self.zoom_factor / 100),
                                    Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation))

                        if len(obj_items) > 1:
                            tab_widget.addTab(view_widget, str(item_idx))
                        else:
                            obj_layout.addWidget(name_label,
                                                 alignment=Qt.AlignHCenter)
                            # Add view-widget if not enough items for Tab-Widget
                            obj_layout.addWidget(view_widget)
                            scroll_layout.addLayout(obj_layout, row, col)

                    if len(obj_items) > 1:
                        frame_widget = QWidget()
                        frame_layout = QVBoxLayout()
                        frame_layout.addWidget(name_label,
                                               alignment=Qt.AlignHCenter)
                        frame_layout.addWidget(tab_widget)
                        show_bt = QPushButton('Show')
                        show_bt.clicked.connect(
                            partial(self.show_single_items, p_preset,
                                    obj_name))
                        frame_layout.addWidget(show_bt)
                        frame_widget.setLayout(frame_layout)
                        scroll_layout.addWidget(frame_widget, row, col)

            scroll_widget.setLayout(scroll_layout)
            scroll_area.setWidget(scroll_widget)
            p_preset_layout.addWidget(scroll_area)

            viewer_layout.addLayout(p_preset_layout)

        self.main_layout.addLayout(viewer_layout)

    def init_ui(self):

        toolbar = QToolBar('Plot-Tools')
        self.addToolBar(toolbar)

        # Zoom-Control
        toolbar.addAction('-- Zoom', partial(self.zoom_items, '--'))
        toolbar.addAction('- Zoom', partial(self.zoom_items, '-'))
        self.zoom_label = QLabel(f'{self.zoom_factor} %')
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
        # A frankly very long call to get the tab_widgets
        # (when setCentralWidget in QMainWindow, the previous reference to widgets inside are deleted,
        # so I found no way to store the reference to the TabWidget beforehand)
        viewer_layout = self.centralWidget().layout().itemAt(0)
        for n in range(
                viewer_layout.count()):  # Get GridLayouts in scroll_areas for Parameter-Presets
            scroll_area = viewer_layout.itemAt(n).itemAt(1).widget()
            grid_layout = scroll_area.widget().layout()
            for c in range(grid_layout.count()):
                row = c // self.column_count
                col = c % self.column_count
                item_widget = grid_layout.itemAtPosition(row, col).widget()
                if not isinstance(item_widget,
                                  QLabel) and item_widget is not None:
                    tab_widget = item_widget.layout().itemAt(1).widget()
                    tab_widget.setCurrentIndex(idx)

    def update_layout(self):
        old_layout = self.main_layout.itemAt(0)
        self.main_layout.removeItem(old_layout)
        for p_preset_layout in [old_layout.itemAt(idx).layout() for idx in
                                range(old_layout.count())]:
            title_label = p_preset_layout.itemAt(0).widget()
            title_label.deleteLater()
            scroll_area = p_preset_layout.itemAt(1).widget()
            scroll_area.deleteLater()
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
            self.zoom_factor += 10
        elif zoom == '++':
            self.zoom_factor += 50
        elif zoom == '-':
            self.zoom_factor -= 10
        else:
            self.zoom_factor -= 50

        # Make sure, that zoom is not smaller than 10%
        if self.zoom_factor < 10:
            self.zoom_factor = 10

        self.zoom_label.setText(f'{self.zoom_factor} %')
        self.update_layout()

    def show_single_items(self, p_preset, obj_name):
        # Create dictionary similar to what you get from loading to open a new viewer with just the selected items
        obj_items = [item.copy() for item in self.items[p_preset][obj_name]]
        item_dict = {
            'Default': {idx: [value] for idx, value in enumerate(obj_items)}}
        PlotViewer(self, item_dict, self.interactive, False)

    def closeEvent(self, event):
        if self.top_level:
            self.parent().show()

        event.accept()
