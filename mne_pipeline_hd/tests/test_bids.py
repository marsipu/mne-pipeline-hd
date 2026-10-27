# -*- coding: utf-8 -*-
"""BIDS exports using small on-disk recordings, without downloaded test data."""

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import mne
import nibabel as nib
import numpy as np
import pandas as pd
import pytest
from mne_bids import BIDSPath, read_raw_bids

from mne_pipeline_hd.pipeline.bids import (
    BIDSRecording,
    _read_event_ids,
    bids_mapping_from_pattern,
    default_bids_mapping,
    export_project_bids,
    infer_bids_sessions,
    validate_bids_mapping,
    validate_dataset_description,
)
from mne_pipeline_hd.pipeline.project import Project


@pytest.fixture
def bids_project(tmp_path):
    project_path = tmp_path / "project"
    data_path = project_path / "data"
    subjects_dir = tmp_path / "subjects"
    scripts = project_path / "_pipeline_scripts"
    data_path.mkdir(parents=True)
    scripts.mkdir()
    subjects_dir.mkdir()
    event_id_path = scripts / "meeg_event_id_Test project.json"
    event_id_path.write_text("{}")
    return SimpleNamespace(
        name="Test project",
        project_path=str(project_path),
        data_path=str(data_path),
        ct=SimpleNamespace(subjects_dir=str(subjects_dir)),
        p_preset="Default",
        all_meeg=[],
        all_erm=[],
        all_fsmri=[],
        meeg_to_fsmri={},
        meeg_to_erm={},
        meeg_bad_channels={},
        meeg_event_id={},
        meeg_event_id_path=str(event_id_path),
    )


def _raw(project, name, *, day=2, kind="meg", first_samp=0):
    info = mne.create_info(
        ["MEG0111", "MEG0121"] if kind == "meg" else ["Fp1", "Fp2"],
        sfreq=100,
        ch_types="mag" if kind == "meg" else "eeg",
    )
    raw = mne.io.RawArray(np.zeros((2, 300)), info, first_samp=first_samp)
    raw.set_meas_date(datetime(2020, 1, day, tzinfo=timezone.utc))
    if kind == "eeg":
        raw.set_montage("standard_1020")
    raw.info["subject_info"] = {
        "his_id": "identifying-id",
        "first_name": "First",
        "last_name": "Last",
        "sex": 1,
        "hand": 1,
        "birthday": datetime(1990, 1, 1).date(),
    }
    directory = Path(project.data_path) / name
    directory.mkdir()
    raw.save(directory / f"{name}-raw.fif", overwrite=True)
    return raw


def _mri(project, name):
    project.all_fsmri.append(name)
    directory = Path(project.ct.subjects_dir) / name
    for folder in ("mri", "surf", "label", "stats", "scripts", "bem"):
        (directory / folder).mkdir(parents=True)
    image = nib.MGHImage(np.ones((3, 3, 3), dtype=np.float32), np.eye(4))
    nib.save(image, directory / "mri" / "T1.mgz")
    (directory / "surf" / "lh.white").write_text("native surface")
    (directory / "bem" / "unwanted-src.fif").write_text("pipeline source model")
    (directory / "unwanted-epo.fif").write_text("epochs")
    return directory


@pytest.mark.parametrize("anonymize", [False, True])
def test_complete_export(bids_project, tmp_path, anonymize):
    project = bids_project
    project.all_meeg = ["recording-a", "recording-b"]
    project.all_erm = ["empty-a", "empty-b", "unassigned-empty"]
    project.meeg_to_fsmri = dict.fromkeys(project.all_meeg, "original-mri-name")
    project.meeg_to_erm = {"recording-a": "empty-a", "recording-b": "empty-a"}
    project.meeg_bad_channels = {"recording-a": ["MEG0121"]}
    saved_event_ids = {"recording-a": {"stimulus": 1, "unselected": 2}}
    Path(project.meeg_event_id_path).write_text(json.dumps(saved_event_ids))
    project.meeg_event_id = {"recording-a": {"stale-label": 1}}
    originals = {}
    for index, name in enumerate(project.all_meeg + project.all_erm):
        originals[name] = _raw(project, name, day=3 if index < 2 else 2)
    _mri(project, "original-mri-name")
    _mri(project, "unassigned-mri")
    source = Path(project.data_path) / "recording-a"
    mne.write_events(
        source / "recording-a_Default-eve.fif",
        np.array([[10, 0, 1], [20, 0, 2], [30, 0, 9]]),
    )
    mne.write_trans(
        source / "original-mri-name-trans.fif", mne.transforms.Transform("head", "mri")
    )
    (source / "unwanted-epo.fif").write_text("epochs")
    destination = tmp_path / "bids"
    progress_values, progress_max, progress_text = [], [], []
    signals = SimpleNamespace(
        pgbar_n=SimpleNamespace(emit=progress_values.append),
        pgbar_max=SimpleNamespace(emit=progress_max.append),
        pgbar_text=SimpleNamespace(emit=progress_text.append),
    )
    metadata = {
        "name": "Study dataset",
        "authors": ["First Author", "Second Author"],
        "data_license": "CC0",
        "acknowledgements": "Thanks",
        "how_to_acknowledge": "Cite our paper",
        "funding": ["Grant 123"],
        "ethics_approvals": ["Approval 456"],
        "references_and_links": ["https://example.org/study"],
        "doi": "doi:10.1234/example",
    }
    # Exercise the public Project entry point without constructing a GUI controller.
    assert (
        Project.export_bids(
            project,
            destination,
            anonymize=anonymize,
            worker_signals=signals,
            dataset_description=metadata,
        )
        == destination
    )
    assert progress_max == [15]
    assert progress_values[0] == 0
    assert progress_values[-1] == 15
    assert progress_values == sorted(progress_values)
    assert set(progress_values) == set(range(16))
    assert progress_text[-1] == "BIDS export complete."
    description = json.loads((destination / "dataset_description.json").read_text())
    assert description["Name"] == metadata["name"]
    assert description["Authors"] == metadata["authors"]
    assert description["License"] == metadata["data_license"]
    assert description["Funding"] == metadata["funding"]
    assert description["EthicsApprovals"] == metadata["ethics_approvals"]
    assert description["ReferencesAndLinks"] == metadata["references_and_links"]
    assert description["DatasetDOI"] == metadata["doi"]
    assert any("FreeSurfer" in text for text in progress_text)
    assert any("transform" in text for text in progress_text)
    assert (source / "unwanted-epo.fif").read_text() == "epochs"
    first = BIDSPath(
        root=destination,
        subject="001",
        task="task",
        session="01",
        run="01",
        datatype="meg",
        suffix="meg",
        extension=".fif",
    )
    raw = read_raw_bids(first)
    assert raw.info["bads"] == ["MEG0121"]
    assert raw.info["subject_info"]["sex"] == (0 if anonymize else 1)
    events = pd.read_csv(
        first.copy().update(suffix="events", extension=".tsv").fpath, sep="\t"
    )
    assert set(events.trial_type) == {"stimulus", "unselected", "event/9"}
    assert project.meeg_event_id == {"recording-a": {"stale-label": 1}}
    assert json.loads(Path(project.meeg_event_id_path).read_text()) == saved_event_ids
    assert list(events.onset) == pytest.approx([0.1, 0.2, 0.3])
    sidecar = json.loads(first.copy().update(extension=".json").fpath.read_text())
    associated = sidecar["AssociatedEmptyRoom"]
    assert (destination / associated).is_file()
    second = first.copy().update(run="02")
    assert (
        json.loads(second.copy().update(extension=".json").fpath.read_text())[
            "AssociatedEmptyRoom"
        ]
        == associated
    )
    empty_files = list((destination / "sub-emptyroom").rglob("*_meg.fif"))
    assert len(empty_files) == 3
    empty = mne.io.read_raw_fif(destination / associated)
    assert raw.info["meas_date"] - empty.info["meas_date"] == (
        originals["recording-a"].info["meas_date"]
        - originals["empty-a"].info["meas_date"]
    )
    if anonymize:
        assert raw.info["meas_date"].year < 1925
        assert empty.info["meas_date"].year < 1925
        assert raw.info["subject_info"]["his_id"] != "identifying-id"
        assert "first_name" not in raw.info["subject_info"]
        assert "original-mri-name" not in " ".join(
            str(p) for p in destination.rglob("*")
        )
    else:
        assert raw.info["meas_date"] == originals["recording-a"].info["meas_date"]
        assert (
            mne.io.read_raw_fif(first.fpath).info["subject_info"]["his_id"]
            == "identifying-id"
        )
    assert (
        destination
        / "sub-001"
        / "ses-01"
        / "anat"
        / "sub-001_ses-01_T1w.nii.gz"
    ).is_file()
    assert (
        destination / "sub-002" / "anat" / "sub-002_T1w.nii.gz"
    ).is_file()
    for subject in ("001", "002"):
        fs = destination / "derivatives" / "freesurfer" / f"sub-{subject}"
        assert (fs / "mri" / "T1.mgz").is_file()
        assert (fs / "surf" / "lh.white").read_text() == "native surface"
        assert not (fs / "bem").exists()
    transforms = list(
        (destination / "derivatives" / "mne-pipeline-hd").rglob("*-trans.fif")
    )
    assert len(transforms) == 1
    assert transforms[0].name == "sub-001_ses-01_task-task_run-01-trans.fif"
    np.testing.assert_array_equal(
        mne.read_trans(transforms[0])["trans"],
        mne.read_trans(source / "original-mri-name-trans.fif")["trans"],
    )
    assert not list(destination.rglob("*unwanted*"))
    assert (
        json.loads((destination / "dataset_description.json").read_text())[
            "DatasetType"
        ]
        == "raw"
    )
    assert (
        json.loads(
            (
                destination / "derivatives" / "freesurfer" / "dataset_description.json"
            ).read_text()
        )["DatasetType"]
        == "derivative"
    )


def test_eeg_annotations(bids_project, tmp_path):
    project = bids_project
    project.all_meeg = ["eeg"]
    raw = _raw(project, "eeg", kind="eeg", first_samp=100)
    raw.set_annotations(mne.Annotations([0.5], [0.1], ["annotation"]))
    raw.info["bads"] = ["Fp1"]
    project.meeg_bad_channels["eeg"] = []
    raw.save(Path(project.data_path) / "eeg" / "eeg-raw.fif", overwrite=True)
    destination = tmp_path / "bids"
    destination.mkdir()
    recordings, mris = default_bids_mapping(project)
    recordings[0].task = "rest"
    recordings[0].session = "01"
    recordings[0].run = "01"
    export_project_bids(project, destination, recordings, mris)
    path = BIDSPath(
        root=destination,
        subject="001",
        task="rest",
        session="01",
        run="01",
        datatype="eeg",
    )
    exported = read_raw_bids(path)
    np.testing.assert_allclose(exported.get_data(), raw.get_data(), atol=1e-12)
    assert "annotation" in exported.annotations.description
    assert exported.annotations.onset[0] == pytest.approx(0.5)
    assert exported.info["bads"] == []
    assert mne.io.read_raw_fif(Path(project.data_path) / "eeg" / "eeg-raw.fif").info[
        "bads"
    ] == ["Fp1"]
    assert list(destination.rglob("*.vhdr"))
    assert not (destination / "derivatives").exists()


def test_event_ids_are_reread_from_disk(bids_project):
    project = bids_project
    path = Path(project.meeg_event_id_path)
    path.write_text(json.dumps({"recording": {"first": 1}}))
    assert _read_event_ids(project) == {"recording": {"first": 1}}
    path.write_text(json.dumps({"recording": {"updated": {"numpy_int": 2}}}))
    assert _read_event_ids(project) == {"recording": {"updated": 2}}
    assert project.meeg_event_id == {}


@pytest.mark.parametrize(
    "metadata",
    [
        {"authors": "Not a list"},
        {"authors": [""]},
        {"name": ""},
        {"dataset_type": "derivative"},
        {"funding": [123]},
    ],
)
def test_invalid_dataset_description(metadata):
    with pytest.raises(ValueError):
        validate_dataset_description(metadata)


@pytest.mark.parametrize(
    "content",
    [
        None,
        "{",
        "[]",
        '{"recording": []}',
        '{"recording": {"label": "1"}}',
        '{"recording": {"label": true}}',
    ],
)
def test_invalid_event_id_json_fails_export(bids_project, tmp_path, content):
    project = bids_project
    project.all_meeg = ["recording"]
    path = Path(project.meeg_event_id_path)
    if content is None:
        path.unlink()
    else:
        path.write_text(content)
    project.meeg_event_id = {"recording": {"in-memory-label": 1}}
    destination = tmp_path / "bids"
    with pytest.raises((ValueError, TypeError, FileNotFoundError)):
        export_project_bids(project, destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".bids-export-*"))


def test_mapping_validation(bids_project):
    project = bids_project
    project.all_meeg = ["one", "two"]
    project.all_fsmri = ["mri", "unassigned"]
    project.meeg_to_fsmri = dict.fromkeys(project.all_meeg, "mri")
    recordings, mris = default_bids_mapping(project)
    assert [r.subject for r in recordings] == ["001", "001"]
    assert [r.run for r in recordings] == ["01", "02"]
    assert mris == {"mri": "001", "unassigned": "002"}
    validate_bids_mapping(project, recordings, mris)
    recordings[1].run = "1"
    with pytest.raises(ValueError, match="unique"):
        validate_bids_mapping(project, recordings, mris)
    recordings[1].run = "02"
    recordings[0].subject = "not-valid"
    with pytest.raises(ValueError, match="ASCII"):
        validate_bids_mapping(project, recordings, mris)
    recordings[0].subject = "003"
    with pytest.raises(ValueError, match="same subject"):
        validate_bids_mapping(project, recordings, mris)


def _session_info(day=1, offset=None):
    dig = None
    if offset is not None:
        montage = mne.channels.make_dig_montage(
            nasion=[0, 0.1 + offset, 0],
            lpa=[-0.1, 0, 0],
            rpa=[0.1, 0, 0],
            coord_frame="head",
        )
        dig = montage.dig
    return {
        "dig": dig,
        "meas_date": datetime(2020, 1, day, tzinfo=timezone.utc) if day else None,
    }


def test_infer_sessions_digitization_priority():
    recordings = [BIDSRecording(name, "001") for name in ["a", "b", "c", "d"]]
    infos = {
        "a": _session_info(1, 0),
        "b": _session_info(2, 0.5e-6),
        "c": _session_info(1, 0.01),
        "d": _session_info(3, 0.01),
    }
    derived = infer_bids_sessions(recordings, infos)
    assert [recording.session for recording in derived] == ["01", "01", "02", "02"]
    reversed_result = infer_bids_sessions(list(reversed(recordings)), infos)
    assert {r.name: r.session for r in reversed_result} == {
        r.name: r.session for r in derived
    }
    assert all(not recording.session for recording in recordings)


def test_infer_sessions_dates_and_subjects():
    recordings = [
        BIDSRecording("a", "001"),
        BIDSRecording("b", "001"),
        BIDSRecording("c", "001"),
        BIDSRecording("d", "002"),
    ]
    infos = {name: _session_info(day) for name, day in zip("abcd", [1, 1, 2, 2])}
    derived = infer_bids_sessions(recordings, infos)
    assert [recording.session for recording in derived] == ["01", "01", "02", "01"]


def test_infer_sessions_preserves_explicit_labels():
    recordings = [
        BIDSRecording("a", "001", session="visit"),
        BIDSRecording("b", "001"),
        BIDSRecording("c", "001", session="01"),
        BIDSRecording("d", "001"),
    ]
    infos = {
        "a": _session_info(1, 0),
        "b": _session_info(2, 0),
        "c": _session_info(3),
        "d": _session_info(4),
    }
    derived = infer_bids_sessions(recordings, infos)
    assert [recording.session for recording in derived] == [
        "visit",
        "visit",
        "01",
        "02",
    ]


def test_infer_session_from_date_of_digitized_recording():
    recordings = [BIDSRecording("a", "001"), BIDSRecording("b", "001")]
    infos = {"a": _session_info(1, 0), "b": _session_info(1)}
    assert [r.session for r in infer_bids_sessions(recordings, infos)] == ["01", "01"]


@pytest.mark.parametrize("failure", ["missing", "ambiguous-date", "conflicting-labels"])
def test_infer_sessions_requires_unambiguous_metadata(failure):
    recordings = [BIDSRecording(name, "001") for name in "abc"]
    infos = {name: _session_info(1, 0) for name in "abc"}
    if failure == "missing":
        infos["c"] = _session_info(None)
    elif failure == "ambiguous-date":
        infos["b"] = _session_info(1, 0.01)
        infos["c"] = _session_info(1)
    else:
        recordings[0].session = "visit1"
        recordings[1].session = "visit2"
    with pytest.raises(ValueError, match="session|sessions"):
        infer_bids_sessions(recordings, infos)
    assert not recordings[2].session


def test_digitization_matching():
    from mne_pipeline_hd.pipeline.pipeline_utils import digitizations_match

    first = _session_info(1, 0)["dig"]
    assert digitizations_match(first, _session_info(1, 0.5e-6)["dig"])
    assert not digitizations_match(first, _session_info(1, 2e-6)["dig"])
    assert not digitizations_match(None, None)
    assert not digitizations_match([], [])
    other_frame = _session_info(1, 0)["dig"]
    other_frame[0]["coord_frame"] = 5
    assert not digitizations_match(first, other_frame)


def test_coregistration_copy_uses_digitization_comparison(monkeypatch):
    from mne_pipeline_hd.gui.loading_widgets import CopyTrans

    infos = {
        "same": _session_info(1, 0.5e-6),
        "different": _session_info(1, 0.01),
        "missing": _session_info(1),
    }
    monkeypatch.setattr(
        "mne_pipeline_hd.gui.loading_widgets.MEEG",
        lambda name, controller: SimpleNamespace(load_info=lambda: infos[name]),
    )
    emitted = []
    signal = SimpleNamespace(emit=lambda value: emitted.append(value))
    dialog = SimpleNamespace(
        copy_tos=[],
        current_meeg=SimpleNamespace(load_info=lambda: _session_info(1, 0)),
        to_meegs=list(infos),
        ct=None,
        to_list=SimpleNamespace(content_changed=lambda: None),
    )
    signals = SimpleNamespace(pgbar_max=signal, pgbar_text=signal, pgbar_n=signal)
    CopyTrans._compare_digs(dialog, signals)
    assert dialog.copy_tos == ["same"]
    dialog.current_meeg = SimpleNamespace(load_info=lambda: _session_info(1))
    CopyTrans._compare_digs(dialog, signals)
    assert dialog.copy_tos == []


def test_export_infers_sessions_before_checking_duplicates(bids_project, tmp_path):
    project = bids_project
    project.all_meeg = ["a", "b"]
    for name, day in [("a", 1), ("b", 2)]:
        _raw(project, name, day=day)
    recordings = [BIDSRecording(name, "001", task="rest") for name in project.all_meeg]
    destination = tmp_path / "bids"
    export_project_bids(project, destination, recordings, {})
    assert (destination / "sub-001" / "ses-01").is_dir()
    assert (destination / "sub-001" / "ses-02").is_dir()
    assert all(not recording.session for recording in recordings)
    for session in ("01", "02"):
        assert list((destination / "sub-001" / f"ses-{session}").rglob("*_meg.fif"))


def test_export_distinguishes_coordinate_sidecars(bids_project, tmp_path):
    project = bids_project
    project.all_meeg = ["digitized", "missing", "similar"]
    for name in project.all_meeg:
        raw = _raw(project, name)
        if name != "missing":
            raw.set_montage(
                mne.channels.make_dig_montage(
                    nasion=[0, 0.1 + (0.5e-6 if name == "similar" else 0), 0],
                    lpa=[-0.1, 0, 0],
                    rpa=[0.1, 0, 0],
                    coord_frame="head",
                )
            )
            raw.save(Path(project.data_path) / name / f"{name}-raw.fif", overwrite=True)
    recordings = [
        BIDSRecording(name, "001", task="rest", session="visit", run=str(index))
        for index, name in enumerate(project.all_meeg, 1)
    ]
    destination = tmp_path / "bids"
    export_project_bids(project, destination, recordings, {})
    sidecars = sorted(destination.rglob("*coordsystem.json"))
    assert len(sidecars) == 3
    assert all(
        "ses-visit" in path.name and "_acq-coords" in path.name for path in sidecars
    )
    coordinates = [
        json.loads(path.read_text())["AnatomicalLandmarkCoordinates"]
        for path in sidecars
    ]
    assert {} in coordinates
    assert len([item for item in coordinates if item]) == 2
    assert len(list(destination.rglob("*_meg.fif"))) == 3
    assert all(recording.session == "visit" for recording in recordings)


@pytest.mark.parametrize("include_mri", [False, True])
def test_selected_export(bids_project, tmp_path, include_mri):
    project = bids_project
    project.all_meeg = ["included", "excluded-missing"]
    project.all_erm = ["assigned", "unassigned-missing"]
    project.all_fsmri = ["excluded-missing-mri"]
    project.meeg_to_erm = {"included": "assigned"}
    project.meeg_to_fsmri = {"included": "included-mri"}
    _raw(project, "included")
    _raw(project, "assigned")
    if include_mri:
        _mri(project, "included-mri")
    destination = tmp_path / "bids"
    export_project_bids(
        project,
        destination,
        [BIDSRecording("included", "001", task="rest")],
        {"included-mri": "001"} if include_mri else {},
        selected_only=True,
    )
    assert len(list(destination.rglob("*_meg.fif"))) == 2
    assert (destination / "sub-emptyroom").is_dir()
    assert (destination / "derivatives" / "freesurfer").exists() == include_mri
    assert not list(destination.rglob("*excluded*"))


def test_selected_mri_only_export(bids_project, tmp_path):
    project = bids_project
    _mri(project, "included-mri")
    project.all_meeg = ["unavailable"]
    project.all_erm = ["unavailable-empty"]
    destination = tmp_path / "bids"
    export_project_bids(
        project, destination, [], {"included-mri": "001"}, selected_only=True
    )
    assert list(destination.rglob("*_T1w.nii.gz"))
    assert not (destination / "sub-emptyroom").exists()


@pytest.mark.parametrize("mri_name", ["fsaverage", "custom_average-brain"])
def test_shared_template_export(bids_project, tmp_path, mri_name):
    project = bids_project
    project.all_meeg = ["pp1_rest_a", "pp2_rest_a"]
    project.meeg_to_fsmri = dict.fromkeys(project.all_meeg, mri_name)
    _mri(project, mri_name)
    for name in project.all_meeg:
        _raw(project, name)
        mne.write_trans(
            Path(project.data_path) / name / f"{mri_name}-trans.fif",
            mne.transforms.Transform("head", "mri"),
        )
    defaults, mris = default_bids_mapping(project, shared_mris={mri_name})
    assert [recording.subject for recording in defaults] == ["001", "002"]
    assert mris == {mri_name: "template1"}
    recordings, mris = bids_mapping_from_pattern(
        project, defaults, mris, "{subject}_{task}_{run}", shared_mris={mri_name}
    )
    assert [recording.subject for recording in recordings] == ["pp1", "pp2"]
    assert mris == {mri_name: "template1"}
    destination = tmp_path / "bids"
    export_project_bids(project, destination, recordings, mris, shared_mris={mri_name})
    template = destination / "derivatives" / "freesurfer" / "tpl-template1"
    assert (template / "mri" / "T1.mgz").is_file()
    assert not list(destination.glob("sub-*/anat/*T1w*"))
    assert not (destination / "sub-fsaverage").exists()
    assert len(list(destination.rglob("*_meg.fif"))) == 2
    assert len(list(destination.rglob("*-trans.fif"))) == 2
    assert len(list((destination / "derivatives" / "freesurfer").glob("tpl-*"))) == 1


def test_unassigned_fsaverage_mapping(bids_project):
    bids_project.all_fsmri = ["fsaverage"]
    recordings, mris = default_bids_mapping(bids_project, shared_mris={"fsaverage"})
    assert recordings == []
    assert mris == {"fsaverage": "template1"}
    validate_bids_mapping(bids_project, recordings, mris, shared_mris={"fsaverage"})
    with pytest.raises(ValueError, match="registered"):
        validate_bids_mapping(bids_project, recordings, mris, shared_mris={"unknown"})


def test_empty_selection_rejected(bids_project, tmp_path):
    with pytest.raises(ValueError, match="no data"):
        export_project_bids(bids_project, tmp_path / "bids", [], {}, selected_only=True)


@pytest.mark.parametrize("failure", ["raw", "mri", "empty-date", "nonempty", "source"])
def test_export_failure_is_safe(bids_project, tmp_path, failure):
    project = bids_project
    project.all_meeg = ["recording"]
    destination = tmp_path / "bids"
    if failure != "raw":
        _raw(project, "recording")
    if failure == "mri":
        project.all_fsmri = ["missing-mri"]
    elif failure == "empty-date":
        project.all_erm = ["empty"]
        raw = _raw(project, "empty")
        raw.set_meas_date(None)
        raw.save(Path(project.data_path) / "empty" / "empty-raw.fif", overwrite=True)
    elif failure == "nonempty":
        destination.mkdir()
        (destination / "keep").write_text("untouched")
    elif failure == "source":
        destination = Path(project.data_path) / "export"
    with pytest.raises((ValueError, FileExistsError, FileNotFoundError)):
        export_project_bids(project, destination)
    if failure == "nonempty":
        assert (destination / "keep").read_text() == "untouched"
    else:
        assert not destination.exists()
    assert not list(tmp_path.glob(".bids-export-*"))
