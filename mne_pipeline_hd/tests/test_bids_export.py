# -*- coding: utf-8 -*-
"""Exercise BIDS dialog wiring without downloading sample data."""

import sys
from datetime import datetime, timezone
from functools import partial
from threading import Event, get_ident
from types import SimpleNamespace

import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow, QMessageBox

from mne_pipeline_hd.gui.bids_export import BIDSExportDialog
from mne_pipeline_hd.gui.gui_utils import ExceptionTuple, StdoutStderrStream
from mne_pipeline_hd.pipeline.bids import (
    BIDSRecording,
    bids_mapping_from_pattern,
)
from mne_pipeline_hd.pipeline.project import Project


def _dialog(qtbot, names=None):
    names = ["recording"] if names is None else names
    project = SimpleNamespace(
        all_meeg=names,
        all_fsmri=["mri"],
        all_erm=[],
        meeg_to_fsmri=dict.fromkeys(names, "mri"),
    )
    parent = QMainWindow()
    parent.ct = SimpleNamespace(pr=project)
    qtbot.addWidget(parent)
    dialog = BIDSExportDialog(parent)
    return parent, dialog


def test_bids_dialog_mapping(qtbot, monkeypatch, tmp_path):
    _parent, dialog = _dialog(qtbot)
    assert not dialog.anonymize.isChecked()
    assert dialog.recordings.item(0, 1).text() == "001"
    assert dialog.mris.item(0, 1).text() == "001"
    assert not dialog.recordings.item(0, 0).flags() & Qt.ItemIsEditable
    assert dialog.tables.orientation() == Qt.Horizontal
    assert dialog.tables.count() == 2
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    qtbot.mouseClick(dialog.export_button, Qt.LeftButton)
    assert warnings[-1] == "Set a destination directory."
    dialog.destination.setText(str(tmp_path / "bids"))
    dialog.recordings.item(0, 1).setText("002")
    qtbot.mouseClick(dialog.export_button, Qt.LeftButton)
    assert "same subject" in warnings[-1]
    assert dialog.export_button.isEnabled()


@pytest.mark.parametrize(
    "pattern",
    [
        "{subject}_{session}_{task}_{run}",
        r"(?P<subject>\d+)_(?P<session>visit\d+)_(?P<task>\w+)_(?P<run>\d+)",
    ],
)
def test_filename_pattern_dialog(qtbot, monkeypatch, pattern):
    names = ["012_visit1_rest_01", "012_visit2_rest_02"]
    _parent, dialog = _dialog(qtbot, names)
    dialog.filename_pattern.setText(pattern)
    qtbot.mouseClick(dialog.apply_pattern_button, Qt.LeftButton)
    for row in range(2):
        assert [
            dialog.recordings.item(row, column).text() for column in range(1, 5)
        ] == ["012", f"visit{row + 1}", "rest", f"{row + 1:02}"]
    assert dialog.mris.item(0, 1).text() == "012"
    assert "2 recordings" in dialog.pattern_status.text()
    # A partial match updates matching rows and reports the unchanged remainder.
    before = dialog._mapping()
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    dialog.filename_pattern.setText("012_visit1_rest_(?P<run>0)1")
    # Run zero is invalid and must still fail validation.
    qtbot.mouseClick(dialog.apply_pattern_button, Qt.LeftButton)
    assert "positive integer" in warnings[-1]
    assert dialog._mapping() == before
    assert not dialog.pattern_status.text()
    dialog.filename_pattern.setText("012_visit1_rest_{run}")
    qtbot.mouseClick(dialog.apply_pattern_button, Qt.LeftButton)
    assert names[1] in dialog.pattern_status.text()
    assert "1 recordings" in dialog.pattern_status.text()
    assert dialog._mapping() == before


@pytest.mark.parametrize(
    "unmatched",
    [
        [],
        [f"unmatched_recording_{index:03}" for index in range(30)],
        ["unmatched" + "a" * 300],
    ],
)
def test_pattern_status_preserves_dialog_width(qtbot, unmatched):
    _parent, dialog = _dialog(qtbot, ["recording_01", *unmatched])
    qtbot.waitExposed(dialog)
    original_width = dialog.width()
    original_minimum_width = dialog.minimumSizeHint().width()
    dialog.filename_pattern.setText("recording_{run}")
    qtbot.mouseClick(dialog.apply_pattern_button, Qt.LeftButton)
    qtbot.wait(50)
    assert dialog.minimumSizeHint().width() <= original_minimum_width
    assert dialog.width() == original_width
    dialog.resize(original_width + 200, dialog.height())
    dialog.resize(original_width, dialog.height())
    assert dialog.width() == original_width
    for name in unmatched:
        assert name in dialog.pattern_status.text()


def test_partial_filename_pattern():
    project = SimpleNamespace(
        all_meeg=["recording_01", "recording_02"],
        all_fsmri=["mri"],
        all_erm=[],
        meeg_to_fsmri=dict.fromkeys(["recording_01", "recording_02"], "mri"),
    )
    recordings = [
        BIDSRecording(name, "001", "rest", "visit1", str(index))
        for index, name in enumerate(project.all_meeg, 1)
    ]
    mris = {"mri": "001"}
    derived, derived_mris = bids_mapping_from_pattern(
        project, recordings, mris, r"recording_{run}"
    )
    assert [r.run for r in derived] == ["01", "02"]
    assert [(r.subject, r.task, r.session) for r in derived] == [
        ("001", "rest", "visit1"),
        ("001", "rest", "visit1"),
    ]
    assert [r.run for r in recordings] == ["1", "2"]
    assert derived_mris == mris


def test_partial_pattern_preserves_unmatched_rows():
    names = ["pp1_rest_a", "unmatched"]
    project = SimpleNamespace(
        all_meeg=names,
        all_fsmri=[],
        all_erm=[],
        meeg_to_fsmri={},
    )
    originals = [BIDSRecording(name, "old", run="99") for name in names]
    skipped = []
    derived, _ = bids_mapping_from_pattern(
        project, originals, {}, "{subject}_{task}_{run}", skipped_names=skipped
    )
    assert derived[0] == BIDSRecording(names[0], "pp1", task="rest", run="1")
    assert derived[1] == originals[1]
    assert skipped == ["unmatched"]
    assert originals[0].subject == "old"


def test_selection_mapping(qtbot):
    _parent, dialog = _dialog(qtbot, ["first", "second"])
    dialog.recordings.item(1, 0).setCheckState(Qt.Unchecked)
    dialog.mris.item(0, 0).setCheckState(Qt.Unchecked)
    assert not dialog.selected_only.isChecked()
    assert len(dialog._mapping()[0]) == 2
    dialog.selected_only.setChecked(True)
    recordings, mris = dialog._mapping(selected=True)
    assert [recording.name for recording in recordings] == ["first"]
    assert mris == {}


def test_shared_template_dialog(qtbot):
    parent = QMainWindow()
    parent.ct = SimpleNamespace(
        pr=SimpleNamespace(
            all_meeg=["pp1_rest_a", "pp2_rest_a"],
            all_fsmri=["fsaverage"],
            all_erm=[],
            meeg_to_fsmri=dict.fromkeys(["pp1_rest_a", "pp2_rest_a"], "fsaverage"),
        )
    )
    qtbot.addWidget(parent)
    dialog = BIDSExportDialog(parent)
    assert dialog.mris.item(0, 2).checkState() == Qt.Unchecked
    dialog.mris.item(0, 2).setCheckState(Qt.Checked)
    dialog.mris.item(0, 1).setText("myTemplate")
    assert dialog.mris.item(0, 1).flags() & Qt.ItemIsEditable
    dialog.filename_pattern.setText("{subject}_{task}_{run}")
    qtbot.mouseClick(dialog.apply_pattern_button, Qt.LeftButton)
    assert [dialog.recordings.item(row, 1).text() for row in range(2)] == ["pp1", "pp2"]
    assert dialog.mris.item(0, 1).text() == "myTemplate"
    assert dialog._shared_mris() == frozenset({"fsaverage"})


def test_export_selection_forwarded(qtbot, monkeypatch, tmp_path):
    _parent, dialog = _dialog(qtbot, ["first", "second"])
    dialog.selected_only.setChecked(True)
    dialog.recordings.item(1, 0).setCheckState(Qt.Unchecked)
    dialog.mris.item(0, 0).setCheckState(Qt.Unchecked)
    dialog.destination.setText(str(tmp_path / "bids"))
    captured = []
    monkeypatch.setattr(
        "mne_pipeline_hd.gui.bids_export.WorkerDialog",
        lambda *args, **kwargs: captured.append(kwargs)
        or SimpleNamespace(thread_finished=SimpleNamespace(connect=lambda slot: None)),
    )
    dialog.project.export_bids = lambda **kwargs: None
    qtbot.mouseClick(dialog.export_button, Qt.LeftButton)
    assert captured[0]["selected_only"] is True
    assert [recording.name for recording in captured[0]["recordings"]] == ["first"]
    assert captured[0]["mri_subjects"] == {}


def test_session_inference_selection_updates_correct_row(qtbot, monkeypatch, tmp_path):
    _parent, dialog = _dialog(qtbot, ["first", "second"])
    dialog.project.data_path = str(tmp_path)
    dialog.selected_only.setChecked(True)
    dialog.recordings.item(0, 0).setCheckState(Qt.Unchecked)
    calls = []

    def read_info(path):
        calls.append(path.parent.name)
        return {"dig": None, "meas_date": datetime(2020, 1, 1, tzinfo=timezone.utc)}

    monkeypatch.setattr("mne_pipeline_hd.gui.bids_export.mne.io.read_info", read_info)
    qtbot.mouseClick(dialog.infer_sessions_button, Qt.LeftButton)
    qtbot.waitUntil(dialog.infer_sessions_button.isEnabled)
    assert calls == ["second"]
    assert dialog.recordings.item(0, 2).text() == ""
    assert dialog.recordings.item(1, 2).text() == "01"


@pytest.mark.parametrize(
    ("pattern", "message"),
    [
        ("", "Enter a filename pattern"),
        ("[", "Invalid filename pattern"),
        (".*", "at least one"),
        (r"(?P<ses>.*)", "Unknown BIDS groups: ses"),
        ("missing_{run}", "did not match"),
        (r"[AB]_(?P<task>.*)", "ASCII"),
        (r".*_(?P<run>0)1", "positive integer"),
        (r".*(?P<run>1)", "unique"),
        (r"(?P<subject>[AB]).*_{run}", "different BIDS subject labels"),
    ],
)
def test_invalid_filename_pattern(pattern, message):
    names = ["A_rest_01", "B_rest_01"]
    project = SimpleNamespace(
        all_meeg=names,
        all_fsmri=["mri"],
        all_erm=[],
        meeg_to_fsmri=dict.fromkeys(names, "mri"),
    )
    recordings = [
        BIDSRecording(name, "001", session="visit", run=str(index))
        for index, name in enumerate(names, 1)
    ]
    with pytest.raises(ValueError, match=message):
        bids_mapping_from_pattern(project, recordings, {"mri": "001"}, pattern)
    assert [r.subject for r in recordings] == ["001", "001"]
    assert [r.run for r in recordings] == ["1", "2"]


def test_optional_regex_group_and_quantifier():
    names = ["012_rest_01", "012_rest_02_visit2"]
    project = SimpleNamespace(
        all_meeg=names,
        all_fsmri=[],
        all_erm=[],
        meeg_to_fsmri={},
    )
    recordings = [BIDSRecording(name, "old", session="old") for name in names]
    derived, _ = bids_mapping_from_pattern(
        project,
        recordings,
        {},
        r"(?P<subject>\d{3})_{task}_{run}(?:_(?P<session>visit\d))?",
    )
    assert [r.subject for r in derived] == ["012", "012"]
    assert [r.session for r in derived] == ["", "visit2"]


@pytest.mark.parametrize(
    "pattern", ["{subject}_{task}_{run}", r"{subject}_{task}_(?P<run>[a-z]+)"]
)
def test_letter_run_labels_dialog(qtbot, monkeypatch, pattern):
    _parent, dialog = _dialog(qtbot, ["pp1a_256_b", "pp1a_256_a"])
    dialog.project.data_path = "unused"
    monkeypatch.setattr(
        "mne_pipeline_hd.gui.bids_export.mne.io.read_info",
        lambda path: pytest.fail("Applying a regex must not read recording headers"),
    )
    dialog.filename_pattern.setText(pattern)
    qtbot.mouseClick(dialog.apply_pattern_button, Qt.LeftButton)
    assert [dialog.recordings.item(row, 4).text() for row in range(2)] == ["2", "1"]
    assert dialog.mris.item(0, 1).text() == "pp1a"
    assert "2 recordings" in dialog.pattern_status.text()
    assert [dialog.recordings.item(row, 2).text() for row in range(2)] == ["", ""]


def test_pattern_shows_inferred_sessions(qtbot, monkeypatch, tmp_path):
    names = ["pp1_rest_01", "pp1_rest_02", "pp1_rest_03"]
    _parent, dialog = _dialog(qtbot, names)
    dialog.project.data_path = str(tmp_path)
    # An explicit session is inherited by a matching recording, but not by
    # a recording on a different measurement date.
    dialog.recordings.item(0, 2).setText("visit")
    calls = []

    def read_info(path):
        calls.append(path)
        day = 2 if path.parent.name == names[2] else 1
        return {"dig": None, "meas_date": datetime(2020, 1, day, tzinfo=timezone.utc)}

    monkeypatch.setattr("mne_pipeline_hd.gui.bids_export.mne.io.read_info", read_info)
    dialog.filename_pattern.setText("{subject}_{task}_{run}")
    qtbot.mouseClick(dialog.apply_pattern_button, Qt.LeftButton)
    assert calls == []
    main_thread = get_ident()
    threads = []
    started, release = Event(), Event()

    def slow_read_info(path):
        threads.append(get_ident())
        started.set()
        if not release.wait(timeout=5):
            raise RuntimeError("Test did not release metadata reader")
        return read_info(path)

    monkeypatch.setattr(
        "mne_pipeline_hd.gui.bids_export.mne.io.read_info", slow_read_info
    )
    qtbot.mouseClick(dialog.infer_sessions_button, Qt.LeftButton)
    try:
        qtbot.waitUntil(started.is_set)
        assert not dialog.export_button.isEnabled()
        assert not dialog.recordings.isEnabled()
        assert not dialog.infer_sessions_button.isEnabled()
        qtbot.waitUntil(
            lambda: "Reading metadata"
            in dialog.session_worker_dialog.progress_label.text()
        )
    finally:
        release.set()
    qtbot.waitUntil(dialog.infer_sessions_button.isEnabled)
    assert all(thread != main_thread for thread in threads)
    assert [dialog.recordings.item(row, 2).text() for row in range(3)] == [
        "visit",
        "visit",
        "01",
    ]
    assert len(calls) == 3
    assert calls[0] == tmp_path / names[0] / f"{names[0]}-raw.fif"
    assert dialog.mris.item(0, 1).text() == "pp1"


@pytest.mark.parametrize("missing_file", [False, True])
def test_pattern_inference_errors_leave_tables_unchanged(
    qtbot, monkeypatch, missing_file
):
    _parent, dialog = _dialog(qtbot, ["pp1_rest_a"])
    dialog.project.data_path = "unused"
    errors = []
    monkeypatch.setattr(
        "mne_pipeline_hd.gui.bids_export.ErrorDialog",
        lambda error, **kwargs: errors.append(error),
    )

    def read_info(path):
        if missing_file:
            raise FileNotFoundError("Missing recording")
        return {"dig": None, "meas_date": None}

    monkeypatch.setattr("mne_pipeline_hd.gui.bids_export.mne.io.read_info", read_info)
    dialog.filename_pattern.setText("{subject}_{task}_{run}")
    qtbot.mouseClick(dialog.apply_pattern_button, Qt.LeftButton)
    before = dialog._mapping()
    qtbot.mouseClick(dialog.infer_sessions_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: bool(errors))
    assert dialog._mapping() == before
    assert not dialog.pattern_status.text()
    assert dialog.export_button.isEnabled()
    assert dialog.recordings.isEnabled()


def test_session_inference_skips_filled_sessions(qtbot, monkeypatch):
    _parent, dialog = _dialog(qtbot)
    dialog.recordings.item(0, 2).setText("manual")
    monkeypatch.setattr(
        "mne_pipeline_hd.gui.bids_export.mne.io.read_info",
        lambda path: pytest.fail("Filled sessions do not need metadata"),
    )
    qtbot.mouseClick(dialog.infer_sessions_button, Qt.LeftButton)
    assert dialog.pattern_status.text() == "No blank sessions to infer."


@pytest.mark.parametrize("reverse", [False, True])
def test_mixed_run_label_conversion(reverse):
    expected = {
        "pp1_visit1_rest_b": "3",
        "pp1_visit1_rest_01": "01",
        "pp1_visit1_rest_a": "2",
        "pp1_visit1_rest_repeat2": "4",
        "pp1_visit2_rest_b": "1",
        "pp1_visit1_motor_b": "1",
        "pp2_visit1_rest_b": "1",
    }
    names = list(expected)
    if reverse:
        names.reverse()
    project = SimpleNamespace(
        all_meeg=names, all_fsmri=[], all_erm=[], meeg_to_fsmri={}
    )
    originals = [BIDSRecording(name, "old", run="99") for name in names]
    derived, _ = bids_mapping_from_pattern(
        project, originals, {}, "{subject}_{session}_{task}_{run}"
    )
    assert {recording.name: recording.run for recording in derived} == expected
    assert all(recording.run == "99" for recording in originals)


@pytest.mark.parametrize(
    ("names", "pattern", "message"),
    [
        (["pp1_rest_0", "pp1_rest_a"], "{subject}_{task}_{run}", "positive integer"),
        (["pp1_rest_a-x"], r"{subject}_{task}_(?P<run>.*)", "ASCII"),
        (
            ["pp1_rest_a", "pp1_rest_a_copy"],
            r"{subject}_{task}_{run}(?:_copy)?",
            "unique",
        ),
    ],
)
def test_invalid_converted_run_labels(names, pattern, message):
    project = SimpleNamespace(
        all_meeg=names, all_fsmri=[], all_erm=[], meeg_to_fsmri={}
    )
    originals = [
        BIDSRecording(name, "old", session="visit", run="99") for name in names
    ]
    with pytest.raises(ValueError, match=message):
        bids_mapping_from_pattern(project, originals, {}, pattern)
    assert all(recording.run == "99" for recording in originals)


def test_empty_run_with_nonnumeric_labels():
    names = ["pp1_rest", "pp1_rest_a"]
    project = SimpleNamespace(
        all_meeg=names, all_fsmri=[], all_erm=[], meeg_to_fsmri={}
    )
    derived, _ = bids_mapping_from_pattern(
        project,
        [BIDSRecording(name, "old") for name in names],
        {},
        r"{subject}_{task}(?:_{run})?",
    )
    assert [recording.run for recording in derived] == ["", "1"]


@pytest.mark.parametrize("fail", [False, True])
def test_bids_dialog_worker(qtbot, monkeypatch, tmp_path, fail):
    _parent, dialog = _dialog(qtbot)
    destination = tmp_path / "bids"
    dialog.destination.setText(str(destination))
    dialog.anonymize.setChecked(True)
    dialog.dataset_description = {"authors": ["Test Author"]}
    calls = []
    notifications = []
    errors = []

    def export(**kwargs):
        calls.append(kwargs)
        if fail:
            raise RuntimeError("Export failed")
        destination.mkdir()
        return destination

    monkeypatch.setattr(sys, "stdout", StdoutStderrStream("stdout"))
    monkeypatch.setattr(sys, "stderr", StdoutStderrStream("stderr"))
    dialog.project.export_bids = export
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args: notifications.append(args[2])
    )
    monkeypatch.setattr(
        "mne_pipeline_hd.gui.bids_export.ErrorDialog",
        lambda result, **kwargs: errors.append(result),
    )
    qtbot.mouseClick(dialog.export_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: bool(errors or notifications))
    assert dialog.export_button.isEnabled()
    assert destination.is_dir() is not fail
    assert bool(errors) is fail
    assert calls[0]["anonymize"] is True
    assert calls[0]["recordings"][0].subject == "001"
    assert calls[0]["mri_subjects"] == {"mri": "001"}
    assert calls[0]["dataset_description"] == {"authors": ["Test Author"]}


def test_bids_dialog_errors(qtbot, monkeypatch):
    _parent, dialog = _dialog(qtbot)
    errors = []
    monkeypatch.setattr(
        "mne_pipeline_hd.gui.bids_export.ErrorDialog",
        lambda result, **kwargs: errors.append(result),
    )
    error = ExceptionTuple(ValueError, ValueError("failed"), "traceback")
    dialog.export_button.setEnabled(False)
    dialog._finished(error)
    assert errors == [error]
    assert dialog.export_button.isEnabled()


def test_project_export_api(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "mne_pipeline_hd.pipeline.bids.export_project_bids",
        lambda *args, **kwargs: calls.append((args, kwargs)) or tmp_path,
    )
    project = object()
    assert Project.export_bids(project, tmp_path, anonymize=True) == tmp_path
    assert calls == [
        (
            (project, tmp_path, None, None),
            {
                "anonymize": True,
                "worker_signals": None,
                "dataset_description": None,
                "selected_only": False,
                "shared_mris": (),
            },
        )
    ]


def test_project_export_worker_progress(qtbot, monkeypatch, tmp_path):
    _parent, dialog = _dialog(qtbot)
    dialog.destination.setText(str(tmp_path / "bids"))
    monkeypatch.setattr(sys, "stdout", StdoutStderrStream("stdout"))
    monkeypatch.setattr(sys, "stderr", StdoutStderrStream("stderr"))
    release, started = Event(), Event()
    notifications = []
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args: notifications.append(args[2])
    )

    def export(*args, worker_signals=None, **kwargs):
        assert worker_signals is not None
        worker_signals.pgbar_max.emit(4)
        worker_signals.pgbar_n.emit(2)
        worker_signals.pgbar_text.emit("Exporting recording: test")
        started.set()
        if not release.wait(timeout=5):
            raise RuntimeError("Test did not release export worker")
        worker_signals.pgbar_n.emit(4)
        return tmp_path / "bids"

    monkeypatch.setattr("mne_pipeline_hd.pipeline.bids.export_project_bids", export)
    # Use the real Project method so Worker detects and forwards worker_signals.
    dialog.project.export_bids = partial(Project.export_bids, dialog.project)
    qtbot.mouseClick(dialog.export_button, Qt.LeftButton)
    try:
        qtbot.waitUntil(started.is_set)
        qtbot.waitUntil(lambda: dialog.worker_dialog.progress_bar.value() == 2)
        assert dialog.worker_dialog.progress_bar.maximum() == 4
        assert dialog.worker_dialog.progress_label.text() == "Exporting recording: test"
    finally:
        release.set()
    qtbot.waitUntil(lambda: bool(notifications))


def test_dataset_description_dialog(qtbot):
    _parent, dialog = _dialog(qtbot)
    qtbot.mouseClick(dialog.description_button, Qt.LeftButton)
    child = dialog.description_dialog
    child.fields["authors"].setPlainText(" First Author \n\n Second Author ")
    child.fields["name"].setText(" Study dataset ")
    child.fields["funding"].setPlainText("Grant A\nGrant B")
    child.accept()
    assert dialog.dataset_description == {
        "authors": ["First Author", "Second Author"],
        "name": "Study dataset",
        "funding": ["Grant A", "Grant B"],
    }
    qtbot.mouseClick(dialog.description_button, Qt.LeftButton)
    assert dialog.description_dialog.fields["authors"].toPlainText() == (
        "First Author\nSecond Author"
    )
    dialog.description_dialog.fields["authors"].setPlainText("Cancelled Author")
    dialog.description_dialog.reject()
    assert dialog.dataset_description["authors"] == ["First Author", "Second Author"]
    qtbot.mouseClick(dialog.description_button, Qt.LeftButton)
    dialog.description_dialog.fields["authors"].clear()
    dialog.description_dialog.accept()
    assert "authors" not in dialog.dataset_description
