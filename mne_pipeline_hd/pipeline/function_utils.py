# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import inspect
import io
import logging
import sys
from collections import OrderedDict
from importlib import import_module
from multiprocessing import Pipe

from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSlot, QObject, pyqtSignal
from PyQt5.QtWidgets import QAbstractItemView

from mne_pipeline_hd.gui.gui_utils import get_exception_tuple, ExceptionTuple, Worker
from mne_pipeline_hd.pipeline.loading import BaseLoading, FSMRI, Group, MEEG
from mne_pipeline_hd.pipeline.pipeline_utils import shutdown, ismac, QS


def get_func(func_name, obj):
    # Get module- and package-name, has to specified in pd_funcs
    # (which imports from functions.csv or the <custom_package>.csv)
    module_name = obj.ct.pd_funcs.loc[func_name, "module"]
    module = import_module(module_name)
    func = getattr(module, func_name)

    return func


def get_arguments(func, obj):
    keyword_arguments = {}
    project_attributes = vars(obj.pr)

    # Get arguments from function signature
    arg_names = list(inspect.signature(func).parameters)

    # Remove args/kwargs
    if "args" in arg_names:
        arg_names.remove("args")
    if "kwargs" in arg_names:
        arg_names.remove("kwargs")

    # Get the values for parameter-names
    for arg_name in arg_names:
        if arg_name == "ct":
            keyword_arguments.update({"ct": obj.ct})
        elif arg_name == "controller":
            keyword_arguments.update({"controller": obj.ct})
        elif arg_name == "pr":
            keyword_arguments.update({"pr": obj.pr})
        elif arg_name == "project":
            keyword_arguments.update({"project": obj.pr})
        elif arg_name == "meeg":
            keyword_arguments.update({"meeg": obj})
        elif arg_name == "fsmri":
            keyword_arguments.update({"fsmri": obj})
        elif arg_name == "group":
            keyword_arguments.update({"group": obj})
        elif arg_name in project_attributes:
            keyword_arguments.update({arg_name: project_attributes[arg_name]})
        elif arg_name in obj.pr.parameters[obj.pr.p_preset]:
            keyword_arguments.update(
                {arg_name: obj.pr.parameters[obj.pr.p_preset][arg_name]}
            )
        elif arg_name in obj.ct.settings:
            keyword_arguments.update({arg_name: obj.ct.settings[arg_name]})
        elif arg_name in QS().childKeys():
            keyword_arguments.update({arg_name: QS().value(arg_name)})
        else:
            raise RuntimeError(
                f"{arg_name} could not be found " f"in Subject, Project or Parameters"
            )

    # Add additional keyword-arguments if added for function by user
    if func.__name__ in obj.pr.add_kwargs:
        for kwarg in obj.pr.add_kwargs[func.__name__]:
            keyword_arguments[kwarg] = obj.pr.add_kwargs[func.__name__][kwarg]

    return keyword_arguments


class StreamManager:
    def __init__(self, pipe):
        self.pipe_busy = False
        self.stdout_sender = StreamSender(self, "stdout", pipe)
        self.stderr_sender = StreamSender(self, "stderr", pipe)


class StreamSender(io.TextIOBase):
    def __init__(self, manager, kind, pipe):
        super().__init__()
        self.manager = manager
        self.kind = kind
        if kind == "stdout":
            self.original_stream = sys.__stdout__
        else:
            self.original_stream = sys.__stderr__
        self.pipe = pipe

    def write(self, text):
        # Still send output to the command-line
        self.original_stream.write(text)
        # Wait until pipe is free
        while self.manager.pipe_busy:
            pass
        self.manager.pipe_busy = True
        if text[:1] == "\r":
            kind = "progress"
        else:
            kind = self.kind
        self.pipe.send((text, kind))
        self.manager.pipe_busy = False


class StreamRcvSignals(QObject):
    stdout_received = pyqtSignal(str)
    stderr_received = pyqtSignal(str)
    progress_received = pyqtSignal(str)


class StreamReceiver(QRunnable):
    def __init__(self, pipe):
        super().__init__()
        self.pipe = pipe
        self.signals = StreamRcvSignals()

    @pyqtSlot()
    def run(self):
        while True:
            try:
                text, kind = self.pipe.recv()
            except EOFError:
                break
            else:
                if kind == "stdout":
                    self.signals.stdout_received.emit(text)
                elif kind == "stderr":
                    self.signals.stderr_received.emit(text)
                else:
                    self.signals.progress_received.emit(text)


def run_func(func, keywargs, pipe=None):
    if pipe is not None:
        stream_manager = StreamManager(pipe)
        sys.stdout = stream_manager.stdout_sender
        sys.stderr = stream_manager.stderr_sender
    try:
        return func(**keywargs)
    except Exception:
        return get_exception_tuple(is_mp=pipe is not None)


class RunController:
    def __init__(self, controller):
        self.ct = controller

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
        self.meeg_funcs = self.ct.pd_funcs[self.ct.pd_funcs["target"] == "MEEG"]
        self.fsmri_funcs = self.ct.pd_funcs[self.ct.pd_funcs["target"] == "FSMRI"]
        self.group_funcs = self.ct.pd_funcs[self.ct.pd_funcs["target"] == "Group"]
        self.other_funcs = self.ct.pd_funcs[self.ct.pd_funcs["target"] == "Other"]

        # Lists of selected functions divided into object-types
        # (MEEG, FSMRI, ...)
        self.sel_meeg_funcs = [
            ff for ff in self.meeg_funcs.index if ff in self.ct.pr.sel_functions
        ]
        self.sel_fsmri_funcs = [
            mf for mf in self.fsmri_funcs.index if mf in self.ct.pr.sel_functions
        ]
        self.sel_group_funcs = [
            gf for gf in self.group_funcs.index if gf in self.ct.pr.sel_functions
        ]
        self.sel_other_funcs = [
            of for of in self.other_funcs.index if of in self.ct.pr.sel_functions
        ]

        # Get a dict with all objects paired with their functions
        # and their type-definition. Give all objects and functions in
        # all_objects the status 1 (which means pending)
        if len(self.ct.pr.sel_fsmri) * len(self.sel_fsmri_funcs) != 0:
            for fsmri in self.ct.pr.sel_fsmri:
                self.all_objects[fsmri] = {
                    "type": "FSMRI",
                    "functions": {x: 1 for x in self.sel_fsmri_funcs},
                    "status": 1,
                }
                for fsmri_func in self.sel_fsmri_funcs:
                    self.all_steps.append((fsmri, fsmri_func))

        if len(self.ct.pr.sel_meeg) * len(self.sel_meeg_funcs) != 0:
            for meeg in self.ct.pr.sel_meeg:
                self.all_objects[meeg] = {
                    "type": "MEEG",
                    "functions": {x: 1 for x in self.sel_meeg_funcs},
                    "status": 1,
                }
                for meeg_func in self.sel_meeg_funcs:
                    self.all_steps.append((meeg, meeg_func))

        if len(self.ct.pr.sel_groups) * len(self.sel_group_funcs) != 0:
            for group in self.ct.pr.sel_groups:
                self.all_objects[group] = {
                    "type": "Group",
                    "functions": {x: 1 for x in self.sel_group_funcs},
                    "status": 1,
                }
                for group_func in self.sel_group_funcs:
                    self.all_steps.append((group, group_func))

        if len(self.sel_other_funcs) != 0:
            # blank object-name for other functions
            self.all_objects[""] = {
                "type": "Other",
                "functions": {x: 1 for x in self.sel_other_funcs},
                "status": 1,
            }
            for other_func in self.sel_other_funcs:
                self.all_steps.append(("", other_func))

    def mark_current_items(self, status):
        # Mark current object with status
        self.all_objects[self.current_object.name]["status"] = status
        # Mark current function with status
        self.all_objects[self.current_object.name]["functions"][
            self.current_func
        ] = status

    def get_object(self):
        self.current_type = self.all_objects[self.current_obj_name]["type"]

        # Load object if the preceding object is not the same
        if not self.current_object or self.current_object.name != self.current_obj_name:
            if self.current_type == "FSMRI":
                self.current_object = FSMRI(self.current_obj_name, self.ct)
                self.loaded_fsmri = self.current_object

            elif self.current_type == "MEEG":
                # Avoid reloading of same MRI-Subject for multiple files
                # (with the same MRI-Subject)
                if (
                    self.current_obj_name in self.ct.pr.meeg_to_fsmri
                    and self.loaded_fsmri
                    and self.loaded_fsmri.name
                    == self.ct.pr.meeg_to_fsmri[self.current_obj_name]
                ):
                    self.current_object = MEEG(
                        self.current_obj_name, self.ct, fsmri=self.loaded_fsmri
                    )
                else:
                    self.current_object = MEEG(self.current_obj_name, self.ct)
                self.loaded_fsmri = self.current_object.fsmri

            elif self.current_type == "Group":
                self.current_object = Group(self.current_obj_name, self.ct)

            elif self.current_type == "Other":
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
            logging.debug(
                f"Running {self.current_func} for " f"{self.current_obj_name}"
            )
            # Get current object
            self.get_object()

            # Mark current object and current function
            self.mark_current_items(2)

            # Run function in Multiprocessing-Pool
            kwds = dict()
            kwds["func"] = get_func(self.current_func, self.current_object)
            kwds["keywargs"] = get_arguments(kwds["func"], self.current_object)

            return kwds

        else:
            self.finished()

    def start(self):
        kwds = self.prepare_start()
        if kwds is not None:
            run_func(**kwds)
            # ToDo: MP
            # self.pool.apply_async(func=run_func, kwds=kwds,
            #                       callback=self.process_finished)
            self.process_finished(None)


class QRunController(RunController):
    def __init__(self, run_dialog, controller):
        super().__init__(controller)
        self.rd = run_dialog
        self.errors = dict()
        self.error_count = 0
        self.is_prog_text = False
        self.paused = False

    def mark_current_items(self, status):
        super().mark_current_items(status)
        obj_idx = list(self.all_objects.keys()).index(self.current_object.name)
        func_idx = list(
            self.all_objects[self.current_object.name]["functions"].keys()
        ).index(self.current_func)
        # Notify Object-Model of change
        self.rd.object_model.layoutChanged.emit()
        # Scroll to current object
        self.rd.object_view.scrollTo(
            self.rd.object_model.createIndex(obj_idx, 0),
            QAbstractItemView.PositionAtCenter,
        )
        # Notify Function-Model of change
        self.rd.func_model.layoutChanged.emit()
        # Scroll to current function
        self.rd.func_view.scrollTo(
            self.rd.func_model.createIndex(func_idx, 0),
            QAbstractItemView.PositionAtCenter,
        )

    def get_object(self):
        old_obj_name = self.current_obj_name
        super().get_object()
        # Print Headline for object if new
        if old_obj_name != self.current_obj_name:
            self.rd.console_widget.write_html(
                f"<br><h1>{self.current_obj_name}</h1><br>"
            )
        # Load functions for object into func_model
        # (which displays functions in func_view)
        self.current_all_funcs = self.all_objects[self.current_obj_name]["functions"]
        self.rd.func_model._data = self.current_all_funcs
        self.rd.func_model.layoutChanged.emit()

        # Print Headline for function
        self.rd.console_widget.write_html(f"<h2>{self.current_func}</h2><br>")

    def process_finished(self, result):
        self.prog_count += 1
        self.rd.pgbar.setValue(self.prog_count)
        self.mark_current_items(0)
        # Process
        if self.paused:
            self.rd.console_widget.write_html("<b><big>Paused</big></b><br>")
            # Enable/Disable Buttons
            self.rd.continue_bt.setEnabled(True)
            self.rd.pause_bt.setEnabled(False)
            self.rd.restart_bt.setEnabled(True)
            self.rd.close_bt.setEnabled(True)
        else:
            if isinstance(result, ExceptionTuple):
                error_cause = (
                    f"{self.error_count}: "
                    f"{self.current_object.name} "
                    f"<- {self.current_func}"
                )
                self.errors[error_cause] = (result, self.error_count)
                # Update Error-Widget
                self.rd.error_widget.replace_data(list(self.errors.keys()))

                # Insert Error-Number into console-widget as an anchor
                # for later inspection
                self.rd.console_widget.write_html(
                    f'<a name="{self.error_count}" href={self.error_count}>'
                    f"<i>Error No.{self.error_count}</i><br></a>"
                )
                # Increase Error-Count by one
                self.error_count += 1

            # Continue with next object
            self.start()

    def finished(self):
        self.rd.console_widget.write_html("<b><big>Finished</big></b><br>")
        # Enable/Disable Buttons
        self.rd.continue_bt.setEnabled(False)
        self.rd.pause_bt.setEnabled(False)
        self.rd.restart_bt.setEnabled(True)
        self.rd.close_bt.setEnabled(True)

        if self.ct.get_setting("shutdown"):
            self.ct.save()
            shutdown()

    def start(self):
        kwds = self.prepare_start()
        if kwds:
            # Plot functions with interactive plots currently can't
            # run in a separate thread, so they
            #  excuted in the main thread
            ismayavi = self.ct.pd_funcs.loc[self.current_func, "mayavi"]
            ismpl = self.ct.pd_funcs.loc[self.current_func, "matplotlib"]
            show_plots = self.ct.get_setting("show_plots")
            use_qthread = QS().value("use_qthread")
            if (
                ismayavi
                or (ismpl and show_plots and use_qthread)
                or (ismpl and not show_plots and use_qthread and ismac)
            ):
                logging.info("Starting in Main-Thread.")
                result = run_func(**kwds)
                self.process_finished(result)

            elif QS().value("use_qthread"):
                logging.info("Starting in separate Thread.")
                worker = Worker(function=run_func, **kwds)
                worker.signals.error.connect(self.process_finished)
                worker.signals.finished.connect(self.process_finished)
                QThreadPool.globalInstance().start(worker)

            else:
                logging.info("Starting in process from multiprocessing.")
                recv_pipe, send_pipe = Pipe(False)
                kwds["pipe"] = send_pipe
                stream_rcv = StreamReceiver(recv_pipe)
                stream_rcv.signals.stdout_received.connect(
                    self.rd.console_widget.write_stdout
                )
                stream_rcv.signals.stderr_received.connect(
                    self.rd.console_widget.write_stderr
                )
                stream_rcv.signals.progress_received.connect(
                    self.rd.console_widget.write_progress
                )
                QThreadPool.globalInstance().start(stream_rcv)
                # ToDO: MP
                self.pool.apply_async(
                    func=run_func, kwds=kwds, callback=self.process_finished
                )
