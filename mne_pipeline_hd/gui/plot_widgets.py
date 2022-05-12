# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMainWindow, QWidget, QGridLayout, QComboBox,
                             QTabWidget, QVBoxLayout)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mne.viz import Brain, Figure3D
from mne_qt_browser.figure import MNEQtBrowser

from mne_pipeline_hd import _object_refs
from mne_pipeline_hd.gui.base_widgets import SimpleList


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

        if isinstance(plot, Figure):
            plot_widget = FigureCanvasQTAgg(plot)
            plot_widget.setFocusPolicy(Qt.FocusPolicy(Qt.StrongFocus |
                                                      Qt.WheelFocus))
            plot_widget.setFocus()
        elif isinstance(plot, MNEQtBrowser):
            plot_widget = plot
        elif isinstance(plot, Brain):
            plot_widget = plot
        elif isinstance(plot, Figure3D):
            plot_widget = plot
        else:
            logging.error(f'Unrecognized type "{type(plot)}" '
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
