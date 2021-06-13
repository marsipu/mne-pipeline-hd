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
import inspect
from collections import OrderedDict
from importlib import import_module
from multiprocessing import Pool

from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import (QAbstractItemView)

from .loading import BaseLoading, FSMRI, Group, MEEG, Sample
from .pipeline_utils import shutdown
from .. import QS
from ..gui.gui_utils import get_exception_tuple, ExceptionTuple, Worker


def get_func(func_name, obj):
    # Get module- and package-name, has to specified in pd_funcs
    # (which imports from functions.csv or the <custom_package>.csv)
    module_name = obj.ct.pd_funcs.loc[func_name, 'module']
    module = import_module(module_name)
    func = getattr(module, func_name)

    return func


def get_arguments(func, obj):
    keyword_arguments = {}
    project_attributes = vars(obj.pr)

    # Get arguments from function signature
    arg_names = list(inspect.signature(func).parameters)

    # Remove args/kwargs
    if 'args' in arg_names:
        arg_names.remove('args')
    if 'kwargs' in arg_names:
        arg_names.remove('kwargs')

    # Get the values for parameter-names
    for arg_name in arg_names:
        if arg_name == 'ct':
            keyword_arguments.update({'ct': obj.ct})
        elif arg_name == 'controller':
            keyword_arguments.update({'controller': obj.ct})
        elif arg_name == 'pr':
            keyword_arguments.update({'pr': obj.pr})
        elif arg_name == 'project':
            keyword_arguments.update({'project': obj.pr})
        elif arg_name == 'meeg':
            keyword_arguments.update({'meeg': obj})
        elif arg_name == 'fsmri':
            keyword_arguments.update({'fsmri': obj})
        elif arg_name == 'group':
            keyword_arguments.update({'group': obj})
        elif arg_name in project_attributes:
            keyword_arguments.update({arg_name: project_attributes[arg_name]})
        elif arg_name in obj.pr.parameters[obj.pr.p_preset]:
            keyword_arguments.update({arg_name: obj.pr.parameters[obj.pr.p_preset][arg_name]})
        elif arg_name in obj.ct.settings:
            keyword_arguments.update({arg_name: obj.ct.settings[arg_name]})
        elif arg_name in QS().childKeys():
            keyword_arguments.update({arg_name: QS().value(arg_name)})
        else:
            raise RuntimeError(f'{arg_name} could not be found in Subject, Project or Parameters')

    # Add additional keyword-arguments if added for function by user
    if func.__name__ in obj.pr.add_kwargs:
        for kwarg in obj.pr.add_kwargs[func.__name__]:
            keyword_arguments[kwarg] = obj.pr.add_kwargs[func.__name__][kwarg]

    return keyword_arguments


def run_func(func, keywargs):
    try:
        return func(**keywargs)
    except:
        return get_exception_tuple()


class RunController:
    def __init__(self, controller, n_parallel=1):
        self.ct = controller
        self.n_parallel = n_parallel
        self.pool = None

        self.all_steps = list()
        self.thread_idx_count = 0
        self.all_objects = OrderedDict()
        self.current_all_funcs = dict()
        self.current_obj_name = None
        self.current_object = None
        self.loaded_fsmri = None
        self.current_func = None
        self.prog_count = 0

        self.init_lists()

    def init_lists(self):
        # Lists dividing the
        self.meeg_funcs = self.ct.pd_funcs[self.ct.pd_funcs['target'] == 'MEEG']
        self.fsmri_funcs = self.ct.pd_funcs[self.ct.pd_funcs['target'] == 'FSMRI']
        self.group_funcs = self.ct.pd_funcs[self.ct.pd_funcs['target'] == 'Group']
        self.other_funcs = self.ct.pd_funcs[self.ct.pd_funcs['target'] == 'Other']

        # Lists of selected functions divided into object-types (MEEG, FSMRI, ...)
        self.sel_meeg_funcs = [ff for ff in self.meeg_funcs.index if ff in self.ct.pr.sel_functions]
        self.sel_fsmri_funcs = [mf for mf in self.fsmri_funcs.index if mf in self.ct.pr.sel_functions]
        self.sel_group_funcs = [gf for gf in self.group_funcs.index if gf in self.ct.pr.sel_functions]
        self.sel_other_funcs = [of for of in self.other_funcs.index if of in self.ct.pr.sel_functions]

        # Get a dict with all objects paired with their functions and their type-definition
        # Give all objects and functions in all_objects the status 1 (which means pending)
        if len(self.ct.pr.sel_fsmri) * len(self.sel_fsmri_funcs) != 0:
            for fsmri in self.ct.pr.sel_fsmri:
                self.all_objects[fsmri] = {'type': 'FSMRI',
                                           'functions': {x: 1 for x in self.sel_fsmri_funcs},
                                           'status': 1}
                for fsmri_func in self.sel_fsmri_funcs:
                    self.all_steps.append((fsmri, fsmri_func))

        if len(self.ct.pr.sel_meeg) * len(self.sel_meeg_funcs) != 0:
            for meeg in self.ct.pr.sel_meeg:
                self.all_objects[meeg] = {'type': 'MEEG',
                                          'functions': {x: 1 for x in self.sel_meeg_funcs},
                                          'status': 1}
                for meeg_func in self.sel_meeg_funcs:
                    self.all_steps.append((meeg, meeg_func))

        if len(self.ct.pr.sel_groups) * len(self.sel_group_funcs) != 0:
            for group in self.ct.pr.sel_groups:
                self.all_objects[group] = {'type': 'Group',
                                           'functions': {x: 1 for x in self.sel_group_funcs},
                                           'status': 1}
                for group_func in self.sel_group_funcs:
                    self.all_steps.append((group, group_func))

        if len(self.sel_other_funcs) != 0:
            # blank object-name for other functions
            self.all_objects[''] = {'type': 'Other',
                                    'functions': {x: 1 for x in self.sel_other_funcs},
                                    'status': 1}
            for other_func in self.sel_other_funcs:
                self.all_steps.append(('', other_func))

    def mark_current_items(self, status):
        # Mark current object with status
        self.all_objects[self.current_object.name]['status'] = status
        # Mark current function with status
        self.all_objects[self.current_object.name]['functions'][self.current_func] = status

    def get_object(self):
        self.current_type = self.all_objects[self.current_obj_name]['type']

        # Load object if the preceding object is not the same
        if not self.current_object or self.current_object.name != self.current_obj_name:
            if self.current_type == 'FSMRI':
                self.current_object = FSMRI(self.current_obj_name, self.ct)
                self.loaded_fsmri = self.current_object

            elif self.current_type == 'MEEG':
                # Avoid reloading of same MRI-Subject for multiple files (with the same MRI-Subject)
                if self.current_obj_name == '_sample_':
                    self.current_object = Sample(self.ct)
                elif self.current_obj_name in self.ct.pr.meeg_to_fsmri \
                        and self.loaded_fsmri \
                        and self.loaded_fsmri.name == self.ct.pr.meeg_to_fsmri[self.current_obj_name]:
                    self.current_object = MEEG(self.current_obj_name, self.ct, fsmri=self.loaded_fsmri)
                else:
                    self.current_object = MEEG(self.current_obj_name, self.ct)
                self.loaded_fsmri = self.current_object.fsmri

            elif self.current_type == 'Group':
                self.current_object = Group(self.current_obj_name, self.ct)

            elif self.current_type == 'Other':
                self.current_object = BaseLoading(self.current_obj_name, self.ct)

    def process_finished(self, result):
        # ToDo: tqdm-progressbar for headless-mode
        self.prog_count += 1
        self.start()

    def finished(self):
        pass

    def prepare_start(self):
        # Take first step of all_steps until there are no steps left.
        if len(self.all_steps) > 0:
            # Getting information as encoded in init_lists
            self.current_obj_name, self.current_func = self.all_steps.pop(0)

            # Get current object
            self.get_object()

            # Mark current object and current function
            self.mark_current_items(2)

            # Run function in Multiprocessing-Pool
            kwds = dict()
            kwds['func'] = get_func(self.current_func, self.current_object)
            kwds['keywargs'] = get_arguments(kwds['func'], self.current_object)

            return kwds

        else:
            self.finished()

    def _start_process(self, kwds):
        # Prepare multiprocessing-Pool if not initialized yet.
        if not self.pool:
            self.pool = Pool(self.n_parallel)

        self.pool.apply_async(func=run_func, kwds=kwds,
                              callback=self.process_finished)

    def start(self):
        kwds = self.prepare_start()
        if kwds:
            self._start_process(kwds)


class QRunController(RunController):
    def __init__(self, run_dialog, use_qthread=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rd = run_dialog
        self.use_qthread = use_qthread
        self.errors = dict()
        self.error_count = 0
        self.is_prog_text = False
        self.paused = False

    def mark_current_items(self, status):
        super().mark_current_items(status)
        obj_idx = list(self.all_objects.keys()).index(self.current_object.name)
        func_idx = list(self.all_objects[self.current_object.name]['functions'].keys()
                        ).index(self.current_func)
        # Notify Object-Model of change
        self.rd.object_model.layoutChanged.emit()
        # Scroll to current object
        self.rd.object_view.scrollTo(self.rd.object_model.createIndex(obj_idx, 0),
                                     QAbstractItemView.PositionAtCenter)
        # Notify Function-Model of change
        self.rd.func_model.layoutChanged.emit()
        # Scroll to current function
        self.rd.func_view.scrollTo(self.rd.func_model.createIndex(func_idx, 0),
                                   QAbstractItemView.PositionAtCenter)

    def get_object(self):
        old_obj_name = self.current_obj_name
        super().get_object()
        # Print Headline for object if new
        if old_obj_name != self.current_obj_name:
            self.rd.console_widget.add_html(f'<br><h1>{self.current_obj_name}</h1><br>')
        # Load functions for object into func_model (which displays functions in func_view)
        self.current_all_funcs = self.all_objects[self.current_obj_name]['functions']
        self.rd.func_model._data = self.current_all_funcs
        self.rd.func_model.layoutChanged.emit()

        # Print Headline for function
        self.rd.console_widget.add_html(f'<h2>{self.current_func}</h2><br>')

    def process_finished(self, result):
        super().process_finished(result)
        self.rd.pgbar.setValue(self.prog_count)
        self.mark_current_items(0)
        # Process
        if self.paused:
            self.rd.console_widget.add_html('<b><big>Paused</big></b><br>')
            # Enable/Disable Buttons
            self.rd.continue_bt.setEnabled(True)
            self.rd.pause_bt.setEnabled(False)
            self.rd.restart_bt.setEnabled(True)
            self.rd.close_bt.setEnabled(True)
        else:
            if isinstance(result, ExceptionTuple):
                error_cause = f'{self.error_count}: {self.current_object.name} <- {self.current_func}'
                self.errors[error_cause] = (result, self.error_count)
                # Update Error-Widget
                self.rd.error_widget.replace_data(list(self.errors.keys()))

                # Insert Error-Number into console-widget as an anchor for later inspection
                self.rd.console_widget.add_html(f'<a name=\"{self.error_count}\" href={self.error_count}>'
                                             f'<i>Error No.{self.error_count}</i><br></a>')
                # Increase Error-Count by one
                self.error_count += 1

            # Continue with next object
            self.start()

    def finished(self):
        if self.pool:
            self.pool.close()
            self.pool.join()
        self.rd.console_widget.add_html('<b><big>Finished</big></b><br>')
        # Enable/Disable Buttons
        self.rd.continue_bt.setEnabled(False)
        self.rd.pause_bt.setEnabled(False)
        self.rd.restart_bt.setEnabled(True)
        self.rd.close_bt.setEnabled(True)

        if self.ct.get_setting('shutdown'):
            self.ct.save()
            shutdown()

    def start(self):
        kwds = self.prepare_start()
        if kwds:
            if self.use_qthread:
                worker = Worker(function=run_func, **kwds)
                worker.signals.error.connect(self.process_finished)
                worker.signals.finished.connect(self.process_finished)
                QThreadPool.globalInstance().start(worker)
            else:
                self._start_process(kwds)
