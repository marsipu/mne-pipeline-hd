# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import functools

from mne_pipeline_hd.gui.plot_widgets import show_plot_manager


def pipeline_plot(plot_func):
    @functools.wraps(plot_func)
    def func_wrapper(*args, **kwargs):
        obj = [
            kwargs.get(kw, None)
            for kw in ["meeg", "fsmri", "group"]
            if kwargs.get(kw, None) is not None
        ][0]
        use_plot_manager = obj.ct.settings["use_plot_manager"]
        if use_plot_manager and "show_plots" in kwargs:
            kwargs["show_plots"] = False
        plot = plot_func(*args, **kwargs)
        if use_plot_manager and plot is not None:
            if not isinstance(plot, list):
                plot = [plot]
            plot_manager = show_plot_manager()
            plot_manager.add_plot(plot, obj.name, plot_func.__name__)

    return func_wrapper
