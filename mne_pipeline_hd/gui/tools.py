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
import sys
import time
from functools import partial
from random import random
from time import sleep

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                             QProgressDialog, QPushButton, QScrollArea, QSpinBox, QTabWidget, QToolBar,
                             QVBoxLayout, QWidget, QComboBox, QSizePolicy, QTextEdit)
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from mne_pipeline_hd.gui.base_widgets import CheckList, SimpleDialog, SimpleList
from mne_pipeline_hd.gui.gui_utils import Worker, set_ratio_geometry, get_exception_tuple
from mne_pipeline_hd.pipeline_functions.function_utils import get_arguments
from mne_pipeline_hd.pipeline_functions.loading import FSMRI, Group, MEEG


class HistoryDlg(QDialog):
    def __init__(self, dt):
        super().__init__(dt)
        self.dt = dt
        self.checked = list()

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        self.checklist = CheckList(self.dt.history, self.checked)

        layout.addWidget(self.checklist)

        add_bt = QPushButton('Add')
        add_bt.clicked.connect(self.add_cmds)
        layout.addWidget(add_bt)

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def add_cmds(self):
        for item in self.checked:
            self.dt.inputw.insertPlainText(item)
            self.dt.inputw.ensureCursorVisible()


# Todo: Syntax Formatting
# Todo: Add Looping over defined Subject-Selection
class DataTerminal(QDialog):
    def __init__(self, main_win, current_object=None):
        super().__init__(main_win)
        self.mw = main_win
        self.obj = current_object
        self.history = list()

        self.default_t_globals = ['mw', 'main_window', 'pr', 'project', 'par', 'parameters']

        self.t_globals = {'mw': self.mw,
                          'main_window': self.mw,
                          'pr': self.mw.pr,
                          'project': self.mw.pr,
                          'par': self.mw.pr.parameters,
                          'parameters': self.mw.pr.parameters}

        # Load the subject in globals if given in Class-Call
        if self.obj:
            self.t_globals['obj'] = self.obj

        self.bt_dict = {}

        self.load_mapping = {'info': 'load_info',
                             'raw': 'load_raw',
                             'filtered': 'load_filtered',
                             'events': 'load_events',
                             'epochs': 'load_epochs',
                             'evokeds': 'load_evokeds',
                             'ica': 'load_ica',
                             'tfr_epochs': 'load_power_tfr_epochs',
                             'tfr_average': 'load_power_tfr_average',
                             'trans': 'load_transformation',
                             'forward': 'load_forward',
                             'noise_cov': 'load_noise_covariance',
                             'inv_op': 'load_inverse_operator',
                             'stc': 'load_source_estimates'}

        sys.stdout.signal.text_written.connect(self.update_label)

        self.init_ui()
        self.open()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.sub_cmbx = QComboBox()
        self.sub_cmbx.addItems(self.mw.pr.all_meeg)
        if self.obj:
            self.sub_cmbx.setCurrentText(self.obj.name)
        else:
            self.sub_cmbx.setCurrentIndex(-1)
        self.sub_cmbx.activated.connect(self.sub_selected)
        self.layout.addWidget(self.sub_cmbx)

        # Add Buttons to load several parts of Sub
        bt_layout = QHBoxLayout()
        for bt_name in self.load_mapping:
            bt = QPushButton(bt_name)
            self.bt_dict[bt_name] = bt
            bt.clicked.connect(partial(self.load_bt_pressed, bt_name))
            bt_layout.addWidget(bt)
            if self.obj is None:
                bt.setEnabled(False)

        self.layout.addLayout(bt_layout)

        self.displayw = QTextEdit()
        self.displayw.setReadOnly(True)
        self.layout.addWidget(self.displayw)

        self.sub_layout = QGridLayout()
        self.inputw = QTextEdit()
        self.inputw.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum))
        self.sub_layout.addWidget(self.inputw, 0, 0, 3, 1)

        self.start_bt = QPushButton('Start')
        self.start_bt.setFont(QFont('AnyStyle', 16))
        self.start_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self.start_bt.clicked.connect(self.start_execution)
        self.sub_layout.addWidget(self.start_bt, 0, 1)

        self.history_bt = QPushButton('History')
        self.history_bt.setFont(QFont('AnyStyle', 16))
        self.history_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self.history_bt.clicked.connect(partial(HistoryDlg, self))
        self.sub_layout.addWidget(self.history_bt, 1, 1)

        self.quit_bt = QPushButton('Close')
        self.quit_bt.setFont(QFont('AnyStyle', 16))
        self.quit_bt.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self.quit_bt.clicked.connect(self.close)
        self.sub_layout.addWidget(self.quit_bt, 2, 1)

        self.layout.addLayout(self.sub_layout)

        self.setLayout(self.layout)

    def sub_selected(self, index):
        # Enable all Buttons for the first time, if no obj was given to call at the beginning
        if self.obj is None:
            for bt_name in self.bt_dict:
                self.bt_dict[bt_name].setEnabled(True)

        name = self.sub_cmbx.itemText(index)
        try:
            self.obj = MEEG(name, self.mw)
        except:
            self.print_exception()
            # Return ComboBox to previous state
            if self.obj is None:
                self.sub_cmbx.setCurrentIndex(-1)
            else:
                self.sub_cmbx.setCurrentText(self.obj.name)
        else:
            # Reset globals to default
            for key in [k for k in self.t_globals.keys() if k not in self.default_t_globals]:
                self.t_globals.pop(key)
            self.t_globals['obj'] = self.obj
            self.displayw.clear()
            self.displayw.insertHtml(f'<b>Subject: {self.obj.name} loaded</b><br>')
            self.displayw.ensureCursorVisible()

    def load_bt_pressed(self, bt_name):

        self.load_dlg = QDialog(self)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f'<h1>Loading {bt_name}...</h1>'))
        self.load_dlg.setLayout(layout)
        self.load_dlg.open()
        worker = Worker(self.start_load, bt_name)
        worker.signals.finished.connect(self.finished_handling)
        worker.signals.error.connect(self.error_handling)
        self.mw.threadpool.start(worker)

    def error_handling(self, _):
        self.load_dlg.close()
        self.print_exception()

    def finished_handling(self, _):
        self.load_dlg.close()

    def start_load(self, bt_name):
        try:
            load_fn = getattr(self.obj, self.load_mapping[bt_name])
            self.t_globals[bt_name] = load_fn()
        except (FileNotFoundError, OSError):
            self.displayw.insertHtml(f'<b><center>No file found for {bt_name}</center></b><br>')
            self.displayw.ensureCursorVisible()
        else:
            # To avoid (visual) print-conflicts
            sleep(0.01)
            self.displayw.insertHtml(f'<b><big><center>{bt_name} loaded (namespace = {bt_name})</center></big></b><br>')
            self.displayw.ensureCursorVisible()

    def update_label(self, text):
        self.displayw.insertPlainText(text)
        self.displayw.ensureCursorVisible()

    def print_exception(self, exc_tuple=None):
        exc_tuple = exc_tuple or get_exception_tuple()
        formated_tb_text = exc_tuple[2].replace('\n', '<br>')
        html_text = f'<b>{exc_tuple[0]}</b><br>' \
                    f'<b>{exc_tuple[1]}</b><br>' \
                    f'{formated_tb_text}'
        self.displayw.insertHtml(html_text)
        self.displayw.ensureCursorVisible()

    def start_execution(self):
        command = self.inputw.toPlainText()
        command_html = command.replace('\n', '<br>')
        self.displayw.insertHtml(f'<b><i>{command_html}</i></b><br>')
        self.displayw.ensureCursorVisible()
        self.history.insert(0, command)

        try:
            print(eval(command, self.t_globals))
        except SyntaxError:
            try:
                exec(command, self.t_globals)
            except:
                self.print_exception()
            else:
                self.inputw.clear()
        except:
            self.print_exception()
        else:
            self.inputw.clear()


class PlotImageLoader(QObject):
    """This class loads a QPixmap of a plot-function,
    if it wasn't plotted yet an image-file for the plot is created which is loaded"""
    finished_loading = pyqtSignal(list)

    def __init__(self, obj, function, parent_w):
        super().__init__(parent_w)
        self.obj = obj
        self.function = function
        self.parent_w = parent_w
        # Make sure that the plot-function only runs once
        self.already_ran_plot = False

        self.load_plot_image()

    def load_plot_image(self):
        try:
            image_paths = self.obj.plot_files[self.function]
            pixmaps = [QPixmap(image_path) for image_path in image_paths]
            self.finished_loading.emit(pixmaps)

        except KeyError:
            if not self.already_ran_plot:
                self.plot_notifier = SimpleDialog(QLabel(f'Plotting {self.function} for {self.obj.name}'),
                                                  parent=self.parent_w, show_close_bt=False)
                # Get module of plot_function
                pkg_name = self.obj.mw.pd_funcs.loc[self.function, 'pkg_name']
                module_name = self.obj.mw.pd_funcs.loc[self.function, 'module']
                module = self.obj.mw.all_modules[pkg_name][module_name][0]

                # Get Arguments for Plot-Function
                keyword_arguments = get_arguments(self.function, module, self.obj, self.obj.mw)
                # Make sure that "show_plots" is False
                keyword_arguments['show_plots'] = False
                plot_func = getattr(module, self.function)

                # Create Thread for Plot-Function
                worker = Worker(plot_func, **keyword_arguments)
                # Pass Object-Name into the plot_finished-Slot
                # (needs to be set as default in lambda-function to survive loop)
                worker.signals.finished.connect(self.plot_finished)
                worker.signals.error.connect(self.plot_error)
                self.obj.mw.threadpool.start(worker)
            else:
                self.finished_loading.emit(list())

    def plot_finished(self):
        self.plot_notifier.close()
        self.already_ran_plot = True
        self.load_plot_image()

    def plot_error(self):
        self.plot_notifier.close()
        self.already_ran_plot = True
        self.load_plot_image()


class PlotViewSelection(QDialog):
    """The user selects the plot-function and the objects to show for this plot_function
    """

    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win

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
        self.interactive_chkbx.toggled.connect(self.interactive_toggled)
        bt_layout.addWidget(self.interactive_chkbx)

        start_bt = QPushButton('Start')
        start_bt.clicked.connect(self.load_plots)
        bt_layout.addWidget(start_bt)

        cancel_bt = QPushButton('Cancel')
        cancel_bt.clicked.connect(self.close)
        bt_layout.addWidget(cancel_bt)

        layout.addLayout(bt_layout)
        self.setLayout(layout)

    def update_objects(self):
        if self.selected_func is not None and self.target is not None:
            # Load object-list according to target
            if self.target == 'MEEG':
                self.objects = self.mw.pr.all_meeg
            elif self.target == 'FSMRI':
                self.objects = self.mw.pr.all_fsmri
            elif self.target == 'Group':
                self.objects = list(self.mw.pr.all_groups.keys())

            # If non-interactive only list objects where a plot-image already was saved
            if not self.interactive:
                self.objects = [ob for ob in self.objects if ob in self.mw.pr.plot_files
                                and self.mw.pr.p_preset in self.mw.pr.plot_files[ob]
                                and self.selected_func in self.mw.pr.plot_files[ob][self.mw.pr.p_preset]]

            self.obj_select.replace_data(self.objects)
            self.obj_select.replace_checked(self.selected_objs)

    def func_selected(self, func):
        """Get selected function and adjust contents of Object-Selection to target"""
        old_target = self.target
        self.selected_func = func
        self.target = self.mw.pd_funcs.loc[func, 'target']
        if old_target != self.target:
            # Clear selected objects
            self.selected_objs.clear()
            self.obj_select.replace_checked(self.selected_objs)
            if self.target == 'MEEG':
                self.obj_select.replace_data(self.mw.pr.all_meeg)
            elif self.target == 'FSMRI':
                self.obj_select.replace_data(self.mw.pr.all_fsmri)
            elif self.target == 'Group':
                self.obj_select.replace_data(list(self.mw.pr.all_groups.keys()))

    def interactive_toggled(self, checked):
        self.interactive = checked
        self.update_objects()

    def load_plots(self):

        # Show ProgressBar
        self.total_loads = len(self.selected_objs) * len(self.selected_ppresets)
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
                for obj_name in self.selected_objs:
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
                        # Make sure that "show_plots" is False
                        keyword_arguments['show_plots'] = False
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
                            image_paths = obj.plot_files[self.selected_func]
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

        # Random sleep
        time.sleep(random())

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
                            fig.set_size_inches(default_size * (self.zoom_factor / 100))
                            view_widget = FigureCanvasQTAgg(fig)
                        else:
                            view_widget = QLabel()
                            # Zoom Pixmap
                            view_widget.setPixmap(item.scaled(item.size() * (self.zoom_factor / 100),
                                                              Qt.KeepAspectRatio, Qt.SmoothTransformation))

                        if len(obj_items) > 1:
                            tab_widget.addTab(view_widget, str(item_idx))
                        else:
                            scroll_layout.addWidget(view_widget, row, col)

                    if len(obj_items) > 1:
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
        # so I found no way to store the reference to the TabWidget beforehand
        viewer_layout = self.centralWidget().layout().itemAt(0)
        for n in range(viewer_layout.count()):  # Get GridLayouts in scroll_areas for Parameter-Presets
            grid_layout = viewer_layout.itemAt(n).widget().widget().layout()
            for c in range(grid_layout.count()):
                row = c // self.column_count
                col = c % self.column_count
                item_widget = grid_layout.itemAtPosition(row, col).widget()
                if not isinstance(item_widget, QLabel):
                    tab_widget = item_widget.layout().itemAt(0).widget()
                    tab_widget.setCurrentIndex(idx)

    def update_layout(self):
        old_layout = self.main_layout.itemAt(0)
        self.main_layout.removeItem(old_layout)
        for scroll_area in [old_layout.itemAt(idx).widget() for idx in range(old_layout.count())]:
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
        item_dict = {'Default': {idx: [value] for idx, value in enumerate(obj_items)}}
        PlotViewer(self, item_dict, self.interactive, False)

    def closeEvent(self, event):
        if self.top_level:
            self.parent().show()

        event.accept()
