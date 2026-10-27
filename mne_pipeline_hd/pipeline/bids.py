# -*- coding: utf-8 -*-
"""Export original project data and selected native derivatives to BIDS."""

import json
import re
import shutil
from collections import Counter, defaultdict
from contextlib import ExitStack
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory

import mne
from mne_bids import (
    BIDSPath,
    get_anonymization_daysback,
    make_dataset_description,
    write_anat,
    write_raw_bids,
)

from mne_pipeline_hd.pipeline.pipeline_utils import (
    digitizations_match,
    logger,
    type_json_hook,
)

# Exclude bem/ and other pipeline-generated source models and inverse solutions.
FREESURFER_DIRECTORIES = ("mri", "surf", "label", "stats", "scripts")

DATASET_DESCRIPTION_FIELDS = {
    "name": ("Dataset name", False),
    "authors": ("Authors", True),
    "data_license": ("License (e.g. CC0)", False),
    "acknowledgements": ("Acknowledgements", False),
    "how_to_acknowledge": ("How to acknowledge", False),
    "funding": ("Funding", True),
    "ethics_approvals": ("Ethics approvals", True),
    "references_and_links": ("References and links", True),
    "doi": ("Dataset DOI", False),
}


def validate_dataset_description(description):
    """Validate supported MNE-BIDS dataset-description keyword arguments."""
    unknown = set(description) - set(DATASET_DESCRIPTION_FIELDS)
    if unknown:
        raise ValueError(
            f"Unsupported dataset description fields: {', '.join(sorted(unknown))}"
        )
    for key, value in description.items():
        label, multiple = DATASET_DESCRIPTION_FIELDS[key]
        values = value if multiple and isinstance(value, list) else [value]
        if (
            (multiple and not isinstance(value, list))
            or not values
            or any(not isinstance(item, str) or not item.strip() for item in values)
        ):
            raise ValueError(
                f"{label} must be nonempty text"
                + (" entries in a list." if multiple else ".")
            )


@dataclass
class BIDSRecording:
    """User-supplied BIDS entities for one original project recording."""

    name: str
    subject: str
    task: str = "task"
    session: str = ""
    run: str = ""


def default_bids_mapping(project, *, shared_mris=()):
    """Suggest non-identifying labels, grouping recordings by assigned MRI."""
    subjects = {}
    recordings = []
    mri_subjects = {}
    for name in project.all_meeg:
        mri = project.meeg_to_fsmri.get(name)
        if mri == "None":
            mri = None
        key = ("mri", mri) if mri and mri not in shared_mris else ("recording", name)
        subject = subjects.setdefault(key, f"{len(subjects) + 1:03}")
        if mri:
            if mri in shared_mris:
                mri_subjects.setdefault(mri, f"template{len(mri_subjects) + 1}")
            else:
                mri_subjects[mri] = subject
        recordings.append(BIDSRecording(name, subject))
    for mri in project.all_fsmri:
        if mri not in mri_subjects:
            if mri in shared_mris:
                mri_subjects[mri] = f"template{len(mri_subjects) + 1}"
                continue
            subject = f"{len(subjects) + 1:03}"
            subjects[("mri", mri)] = subject
            mri_subjects[mri] = subject
    counts = Counter(recording.subject for recording in recordings)
    runs = Counter()
    for recording in recordings:
        if counts[recording.subject] > 1:
            runs[recording.subject] += 1
            recording.run = f"{runs[recording.subject]:02}"
    return recordings, mri_subjects


def _validate_label(value, label, optional=False):
    if optional and not value:
        return
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9]+", value) is None:
        raise ValueError(f"{label} must contain only ASCII letters and digits.")


def _convert_run_labels(recordings):
    groups = defaultdict(list)
    for recording in recordings:
        _validate_label(recording.run, "run", optional=True)
        groups[(recording.subject, recording.session, recording.task)].append(recording)
    for group in groups.values():
        used = {int(recording.run) for recording in group if recording.run.isdigit()}
        labels = sorted(
            {
                recording.run
                for recording in group
                if recording.run and not recording.run.isdigit()
            }
        )
        mapping = {}
        number = 1
        for label in labels:
            while number in used:
                number += 1
            mapping[label] = str(number)
            number += 1
        for recording in group:
            recording.run = mapping.get(recording.run, recording.run)


def bids_mapping_from_pattern(
    project,
    recordings,
    mri_subjects,
    pattern,
    *,
    session_infos=None,
    skipped_names=None,
    shared_mris=(),
):
    """Derive labels from complete recording names without changing the inputs.

    Accept Python regex named groups and the shorthand placeholders {subject},
    {session}, {task} and {run}. Entities absent from the pattern retain their
    current values. Unmatched recordings remain unchanged. Matching rows must be
    valid before they can be applied. Nonnumeric run labels are sorted within each
    subject/session/task group and assigned the lowest unused positive integers.
    """
    entities = ("subject", "session", "task", "run")
    if not pattern.strip():
        raise ValueError("Enter a filename pattern.")
    for entity in entities:
        expression = r"[A-Za-z0-9]+"
        pattern = pattern.replace("{" + entity + "}", f"(?P<{entity}>{expression})")
    try:
        regex = re.compile(pattern)
    except re.error as error:
        raise ValueError(f"Invalid filename pattern: {error}") from error
    unknown = set(regex.groupindex) - set(entities)
    if unknown:
        raise ValueError(f"Unknown BIDS groups: {', '.join(sorted(unknown))}.")
    if not regex.groupindex:
        raise ValueError("Include at least one subject, session, task or run group.")
    derived = []
    unmatched = []
    for recording in recordings:
        match = regex.fullmatch(recording.name)
        if match is None:
            unmatched.append(recording.name)
        else:
            derived.append(
                replace(
                    recording,
                    **{
                        entity: value or ""
                        for entity, value in match.groupdict().items()
                    },
                )
            )
    if not derived:
        raise ValueError(f"Pattern did not match: {', '.join(unmatched)}.")
    if session_infos is not None:
        derived = infer_bids_sessions(derived, session_infos)
    if "run" in regex.groupindex:
        matched_names = {recording.name for recording in derived}
        _convert_run_labels(
            derived
            + [
                replace(recording)
                for recording in recordings
                if recording.name not in matched_names
                and isinstance(recording.run, str)
                and re.fullmatch(r"[0-9]+", recording.run)
            ]
        )
    mri_subjects = dict(mri_subjects)
    if "subject" in regex.groupindex:
        assigned_subjects = {}
        for recording in derived:
            mri = project.meeg_to_fsmri.get(recording.name)
            if mri not in (None, "None") and mri not in shared_mris:
                previous = assigned_subjects.setdefault(mri, recording.subject)
                if previous != recording.subject:
                    raise ValueError(
                        f"The filename pattern assigns different BIDS subject labels "
                        f"to recordings sharing participant MRI {mri}."
                    )
        mri_subjects.update(assigned_subjects)
    validate_bids_mapping(
        project,
        derived,
        mri_subjects,
        allow_missing_sessions=True,
        allow_subset=True,
        shared_mris=shared_mris,
    )
    if unmatched:
        logger().warning(f"Filename pattern skipped: {', '.join(unmatched)}")
    if skipped_names is not None:
        skipped_names.extend(unmatched)
    matched = {recording.name: recording for recording in derived}
    return [
        matched.get(recording.name, replace(recording)) for recording in recordings
    ], mri_subjects


def infer_bids_sessions(recordings, infos):
    """Fill blank sessions per subject using digitization, then recording dates."""
    derived = [replace(recording) for recording in recordings]
    subjects = defaultdict(list)
    for recording in derived:
        subjects[recording.subject].append(recording)
    for subject, members in subjects.items():
        if all(recording.session for recording in members):
            continue
        groups = []
        ordered = sorted(members, key=lambda recording: recording.name)
        for recording in ordered:
            dig = infos[recording.name]["dig"]
            if not dig:
                continue
            matches = [
                group
                for group in groups
                if digitizations_match(dig, infos[group[0].name]["dig"])
            ]
            if len(matches) > 1:
                raise ValueError(
                    f"Ambiguous digitization session for {recording.name}."
                )
            if matches:
                matches[0].append(recording)
            else:
                groups.append([recording])
        for recording in ordered:
            info = infos[recording.name]
            if info["dig"]:
                continue
            date = info["meas_date"]
            if date is None:
                if not recording.session:
                    raise ValueError(
                        f"Cannot infer session for {recording.name}: no digitization "
                        "or measurement date. Supply a session label."
                    )
                continue
            matches = [
                group
                for group in groups
                if any(
                    infos[item.name]["meas_date"] is not None
                    and infos[item.name]["meas_date"].date() == date.date()
                    for item in group
                )
            ]
            if len(matches) > 1:
                if not recording.session:
                    raise ValueError(
                        f"Multiple digitization sessions on the measurement date of "
                        f"{recording.name}. Supply a session label."
                    )
                continue
            if matches:
                matches[0].append(recording)
            else:
                groups.append([recording])
        used = {recording.session for recording in members if recording.session}
        number = 1
        for group in groups:
            missing = [recording for recording in group if not recording.session]
            if not missing:
                continue
            labels = {recording.session for recording in group if recording.session}
            if len(labels) > 1:
                raise ValueError(
                    f"Conflicting supplied sessions for subject {subject}; "
                    "supply sessions for the remaining recordings."
                )
            if labels:
                label = labels.pop()
            else:
                while f"{number:02}" in used:
                    number += 1
                label = f"{number:02}"
                used.add(label)
            for recording in missing:
                recording.session = label
                logger().info(f"Inferred BIDS session {label} for {recording.name}")
    return derived


def validate_bids_mapping(
    project,
    recordings,
    mri_subjects,
    *,
    allow_missing_sessions=False,
    allow_subset=False,
    shared_mris=(),
):
    """Reject ambiguous or incomplete mappings before writing anything."""
    names = [recording.name for recording in recordings]
    if (
        len(names) != len(set(names))
        or not set(names) <= set(project.all_meeg)
        or (not allow_subset and set(names) != set(project.all_meeg))
    ):
        raise ValueError(
            "Provide exactly one BIDS mapping for every project recording."
        )
    if not recordings and not mri_subjects and (allow_subset or not project.all_erm):
        raise ValueError("The project contains no data to export.")
    assigned_mris = {
        project.meeg_to_fsmri[name]
        for name in project.all_meeg
        if project.meeg_to_fsmri.get(name) not in (None, "None")
    }
    available_mris = set(project.all_fsmri) | assigned_mris
    if not set(shared_mris) <= available_mris:
        raise ValueError("Shared templates must be registered project MRIs.")
    if not set(mri_subjects) <= available_mris or (
        not allow_subset and set(mri_subjects) != available_mris
    ):
        raise ValueError("Provide a subject label for every FreeSurfer segmentation.")
    for mri, subject in mri_subjects.items():
        _validate_label(subject, f"Subject for MRI {mri}")
        if subject == "emptyroom":
            raise ValueError('The subject label "emptyroom" is reserved.')
    participant_labels = [
        subject for mri, subject in mri_subjects.items() if mri not in shared_mris
    ]
    if len(set(participant_labels)) != len(participant_labels):
        raise ValueError("Different FreeSurfer segmentations need different subjects.")
    template_labels = [
        label for mri, label in mri_subjects.items() if mri in shared_mris
    ]
    if len(set(template_labels)) != len(template_labels):
        raise ValueError("Shared templates need unique template labels.")
    paths = set()
    for recording in recordings:
        for label in ("subject", "session", "task", "run"):
            _validate_label(
                getattr(recording, label), label, optional=label in ("session", "run")
            )
        if recording.subject == "emptyroom":
            raise ValueError('The subject label "emptyroom" is reserved.')
        if recording.run and (not recording.run.isdigit() or int(recording.run) < 1):
            raise ValueError("Run must be a positive integer or empty.")
        key = (
            recording.subject,
            recording.session,
            recording.task,
            int(recording.run) if recording.run else None,
        )
        if key in paths and not (allow_missing_sessions and not recording.session):
            raise ValueError(
                "Recordings must have unique subject/session/task/run labels."
            )
        paths.add(key)
        mri = project.meeg_to_fsmri.get(recording.name)
        if (
            mri in mri_subjects
            and mri not in shared_mris
            and mri_subjects[mri] != recording.subject
        ):
            raise ValueError(
                f"Recording {recording.name} and its MRI need the same subject label."
            )


def _read_event_ids(project):
    path = Path(project.meeg_event_id_path)
    with path.open("r") as file:
        event_ids = json.load(file, object_hook=type_json_hook)
    if not isinstance(event_ids, dict):
        raise TypeError(
            f"Event-ID JSON must contain a recording-to-label mapping: {path}"
        )
    for name, labels in event_ids.items():
        if not isinstance(labels, dict) or any(
            not isinstance(label, str)
            or not label
            or not isinstance(code, int)
            or isinstance(code, bool)
            for label, code in labels.items()
        ):
            raise ValueError(f"Invalid event-ID mapping for recording {name} in {path}")
    logger().info(f"Read BIDS event-ID labels directly from {path}")
    return event_ids


def _event_metadata(event_ids, name, raw, events):
    # Unlike MEEG.event_id, use all labels, not only trials selected for epochs.
    event_id = dict(event_ids.get(name, {}))
    used_codes = set(event_id.values())
    if events is not None:
        for code in sorted(set(events[:, 2]) - used_codes):
            label = f"event/{code}"
            while label in event_id:
                label += "/unlabeled"
            event_id[label] = int(code)
    next_code = max(event_id.values(), default=0) + 1
    for description in raw.annotations.description:
        if description not in event_id:
            event_id[description] = next_code
            next_code += 1
    return event_id or None


def _description(root, name, derivative=False, metadata=None):
    metadata = dict(metadata or {})
    name = metadata.pop("name", name)
    make_dataset_description(
        path=root,
        name=name,
        dataset_type="derivative" if derivative else "raw",
        generated_by=[{"Name": root.name}] if derivative else None,
        **metadata,
    )


def _coordinate_acquisitions(entries, raws):
    """Separate exact digitizations when coordinate sidecars would share a path."""
    groups = defaultdict(list)
    for name, subject, session in entries:
        groups[(subject, session)].append(name)
    acquisitions = {}
    for names in groups.values():
        setups = {}
        for name in sorted(names):
            dig = raws[name].info["dig"] or []
            signature = tuple(
                (
                    int(point["kind"]),
                    int(point["ident"]),
                    int(point["coord_frame"]),
                    tuple(float(value) for value in point["r"]),
                )
                for point in dig
            )
            setups.setdefault(signature, []).append(name)
        if len(setups) > 1:
            for index, setup_names in enumerate(setups.values(), 1):
                for name in setup_names:
                    acquisitions[name] = f"coords{index:02}"
    return acquisitions


def export_project_bids(
    project,
    destination,
    recordings=None,
    mri_subjects=None,
    *,
    anonymize=False,
    worker_signals=None,
    dataset_description=None,
    selected_only=False,
    shared_mris=(),
):
    """Copy a complete project into a new or empty BIDS directory.

    Events come from the active parameter preset. Only FreeSurfer reconstruction
    directories and existing head/MRI transforms are included as derivatives.
    Anonymization applies to electrophysiology metadata, not MRI/FreeSurfer files.
    The destination is published only after the entire export has succeeded.
    """
    if worker_signals is not None:
        worker_signals.pgbar_text.emit("Validating BIDS export...")
    shared_mris = frozenset(shared_mris)
    defaults, default_mris = default_bids_mapping(project, shared_mris=shared_mris)
    dataset_description = dict(dataset_description or {})
    validate_dataset_description(dataset_description)
    recordings = defaults if recordings is None else list(recordings)
    mri_subjects = default_mris if mri_subjects is None else dict(mri_subjects)
    validate_bids_mapping(
        project,
        recordings,
        mri_subjects,
        allow_missing_sessions=True,
        allow_subset=selected_only,
        shared_mris=shared_mris,
    )
    event_ids = _read_event_ids(project) if recordings else {}
    destination = Path(destination).expanduser().resolve()
    for source in (project.project_path, project.ct.subjects_dir):
        if Path(source).resolve() in (destination, *destination.parents):
            raise ValueError(
                "Export outside the project and FreeSurfer source folders."
            )
    if destination.exists() and (
        not destination.is_dir() or any(destination.iterdir())
    ):
        raise FileExistsError("The BIDS destination must be a new or empty directory.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    empty_names = list(
        dict.fromkeys(
            ([] if selected_only else list(project.all_erm))
            + [
                project.meeg_to_erm[name]
                for name in [recording.name for recording in recordings]
                if project.meeg_to_erm.get(name) not in (None, "None")
            ]
        )
    )
    raw_names = list(dict.fromkeys([r.name for r in recordings] + empty_names))
    trans_paths = {
        r.name: Path(project.data_path)
        / r.name
        / f"{project.meeg_to_fsmri.get(r.name)}-trans.fif"
        for r in recordings
    }
    trans_paths = {name: path for name, path in trans_paths.items() if path.is_file()}
    total = (
        len(raw_names)
        + 1
        + len(empty_names)
        + len(recordings)
        + len(mri_subjects)
        + len(trans_paths)
        + 1
    )
    completed = 0

    def progress(text, *, advance=False):
        nonlocal completed
        if advance:
            completed += 1
        if worker_signals is not None:
            worker_signals.pgbar_text.emit(text)
            worker_signals.pgbar_n.emit(completed)

    if worker_signals is not None:
        worker_signals.pgbar_max.emit(total)
    with ExitStack() as stack:
        raws = {}
        for name in raw_names:
            progress(f"Reading recording metadata: {name}")
            path = Path(project.data_path) / name / f"{name}-raw.fif"
            raw = mne.io.read_raw_fif(path, preload=False)
            stack.callback(raw.close)
            bads = project.meeg_bad_channels.get(name, raw.info["bads"])
            raw.info["bads"] = [ch for ch in raw.ch_names if ch in bads]
            raws[name] = raw
            progress(f"Read metadata: {name}", advance=True)
        progress("Inferring sessions and preparing coordinate metadata...")
        recordings = infer_bids_sessions(
            recordings, {name: raw.info for name, raw in raws.items()}
        )
        validate_bids_mapping(
            project,
            recordings,
            mri_subjects,
            allow_subset=selected_only,
            shared_mris=shared_mris,
        )
        for name in empty_names:
            if "meg" not in raws[name] or raws[name].info["meas_date"] is None:
                raise ValueError(
                    f"Empty-room {name} needs MEG data and a measurement date."
                )
        for recording in recordings:
            erm = project.meeg_to_erm.get(recording.name)
            if erm not in (None, "None") and "meg" not in raws[recording.name]:
                raise ValueError(
                    f"Only MEG recordings can have empty-room data: {recording.name}"
                )
        anonymization = None
        if anonymize:
            dated = [raw for raw in raws.values() if raw.info["meas_date"] is not None]
            daysback = get_anonymization_daysback(dated)[0] if dated else 0
            anonymization = {
                "daysback": daysback,
                "keep_his": False,
                "keep_source": False,
            }
            logger().warning(
                "Only electrophysiology metadata is anonymized. MRI and native "
                "FreeSurfer files may contain identifying information and are not defaced."
            )
        acquisitions = _coordinate_acquisitions(
            [(r.name, r.subject, r.session) for r in recordings]
            + [
                (name, "emptyroom", raws[name].info["meas_date"].strftime("%Y%m%d"))
                for name in empty_names
            ],
            raws,
        )
        progress("Export metadata prepared.", advance=True)
        with TemporaryDirectory(prefix=".bids-export-", dir=destination.parent) as temp:
            root = Path(temp) / "dataset"
            root.mkdir()
            _description(
                root,
                "Exported dataset" if anonymize else project.name,
                metadata=dataset_description,
            )
            empty_paths = {}
            runs = Counter()
            for name in empty_names:
                progress(f"Exporting empty-room recording: {name}")
                session = raws[name].info["meas_date"].strftime("%Y%m%d")
                runs[session] += 1
                path = BIDSPath(
                    root=root,
                    subject="emptyroom",
                    session=session,
                    task="noise",
                    run=f"{runs[session]:02}",
                    datatype="meg",
                    acquisition=acquisitions.get(name),
                )
                empty_paths[name] = write_raw_bids(
                    raws[name],
                    path,
                    anonymize=anonymization,
                )
                progress(f"Exported empty-room recording: {name}", advance=True)
            transforms = []
            for recording in recordings:
                progress(f"Exporting recording: {recording.name}")
                logger().info(f"Exporting BIDS recording {recording.name}")
                path = BIDSPath(
                    root=root,
                    subject=recording.subject,
                    session=recording.session or None,
                    task=recording.task,
                    run=recording.run or None,
                    acquisition=acquisitions.get(recording.name),
                )
                events_path = (
                    Path(project.data_path)
                    / recording.name
                    / f"{recording.name}_{project.p_preset}-eve.fif"
                )
                events = mne.read_events(events_path) if events_path.is_file() else None
                raw = raws[recording.name]
                write_raw_bids(
                    raw,
                    path,
                    events=events,
                    event_id=_event_metadata(event_ids, recording.name, raw, events),
                    empty_room=empty_paths.get(project.meeg_to_erm.get(recording.name)),
                    anonymize=anonymization,
                )
                if recording.name in trans_paths:
                    transforms.append((path, trans_paths[recording.name]))
                progress(f"Exported recording: {recording.name}", advance=True)
            fs_root = root / "derivatives" / "freesurfer"
            for mri, subject in mri_subjects.items():
                progress(f"Copying FreeSurfer reconstruction and T1 image: {mri}")
                source = Path(project.ct.subjects_dir) / mri
                if not source.is_dir():
                    raise FileNotFoundError(
                        f"FreeSurfer segmentation not found: {source}"
                    )
                target = fs_root / (
                    f"tpl-{subject}" if mri in shared_mris else f"sub-{subject}"
                )
                for directory in FREESURFER_DIRECTORIES:
                    if (source / directory).is_dir():
                        progress(f"Copying FreeSurfer {mri}: {directory}")
                        shutil.copytree(source / directory, target / directory)
                if not target.exists():
                    raise ValueError(
                        f"No FreeSurfer reconstruction files found in {source}"
                    )
                t1 = source / "mri" / "T1.mgz"
                if t1.is_file() and mri not in shared_mris:
                    write_anat(
                        t1,
                        BIDSPath(root=root, subject=subject, suffix="T1w"),
                    )
                progress(f"Exported FreeSurfer reconstruction: {mri}", advance=True)
            if mri_subjects:
                _description(
                    fs_root, "Native FreeSurfer reconstructions", derivative=True
                )
            if transforms:
                trans_root = root / "derivatives" / "mne-pipeline-hd"
                _description(trans_root, "Head-MRI transforms", derivative=True)
                for path, source in transforms:
                    progress(f"Copying head-MRI transform: {path.basename}")
                    target = path.copy().update(root=trans_root, check=False)
                    directory = target.directory
                    directory.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, directory / f"{target.basename}-trans.fif")
                    progress(f"Copied transform: {path.basename}", advance=True)
            progress("Finalizing BIDS dataset...")
            # Recheck at publication time; never merge with an existing dataset.
            if destination.exists():
                destination.rmdir()
            root.replace(destination)
    progress("BIDS export complete.", advance=True)
    logger().info(f"BIDS export complete: {destination}")
    return destination
