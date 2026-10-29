"""Project-wide BIDS export dialog."""

from pathlib import Path

import mne
from qtpy import compat
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mne_pipeline_hd.gui.gui_utils import (
    ErrorDialog,
    ExceptionTuple,
    WorkerDialog,
)
from mne_pipeline_hd.pipeline.bids import (
    DATASET_DESCRIPTION_FIELDS,
    BIDSRecording,
    bids_mapping_from_pattern,
    default_bids_mapping,
    infer_bids_sessions,
    validate_bids_mapping,
)


class DatasetDescriptionDialog(QDialog):
    """Edit optional dataset metadata without committing cancelled changes."""

    def __init__(self, parent, metadata):
        super().__init__(parent)
        self.setWindowTitle("BIDS dataset description")
        self.setModal(True)
        self.resize(600, 650)
        layout = QVBoxLayout(self)
        help_label = QLabel(
            "Optional metadata for the root dataset_description.json. "
            "For list fields, enter one item per line. Blank fields are omitted. "
            "A blank dataset name uses the export default. These entries are "
            "preserved even when anonymization is enabled; review them before sharing."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        form = QFormLayout(panel)
        self.fields = {}
        for key, (label, multiple) in DATASET_DESCRIPTION_FIELDS.items():
            value = metadata.get(key, [] if multiple else "")
            if multiple or key in ("acknowledgements", "how_to_acknowledge"):
                field = QPlainTextEdit()
                field.setMaximumHeight(85)
                field.setPlainText("\n".join(value) if multiple else value)
            else:
                field = QLineEdit(value)
            form.addRow(label + (" (one per line)" if multiple else ""), field)
            self.fields[key] = field
        scroll.setWidget(panel)
        layout.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def metadata(self):
        result = {}
        for key, field in self.fields.items():
            text = (
                field.toPlainText()
                if isinstance(field, QPlainTextEdit)
                else field.text()
            ).strip()
            if text:
                result[key] = (
                    [line.strip() for line in text.splitlines() if line.strip()]
                    if DATASET_DESCRIPTION_FIELDS[key][1]
                    else text
                )
        return result


class BIDSExportDialog(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.project = main_win.ct.pr
        self.dataset_description = {}
        self.setWindowTitle("Export project to BIDS")
        recordings, mri_subjects = default_bids_mapping(self.project)

        layout = QVBoxLayout(self)
        info = QLabel(
            "Export all original recordings, all empty-room recordings, events from "
            "the active parameter preset, T1 images, FreeSurfer reconstructions and "
            "existing transforms. No epochs or other pipeline derivatives are exported.\n"
            "Review the suggested labels below. Recordings sharing a participant MRI "
            "must use the same subject. Mark shared anatomy using Shared template "
            "to allow different subjects. Empty sessions are inferred at export from matching "
            "digitization points, falling back to measurement dates. Run may be empty."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        pattern_layout = QHBoxLayout()
        self.filename_pattern = QLineEdit()
        self.filename_pattern.setPlaceholderText(
            "Filename pattern, e.g. {subject}_{session}_{task}_{run}"
        )
        pattern_layout.addWidget(self.filename_pattern)
        self.apply_pattern_button = QPushButton("Apply filename pattern")
        self.apply_pattern_button.clicked.connect(self._apply_pattern)
        pattern_layout.addWidget(self.apply_pattern_button)
        self.infer_sessions_button = QPushButton("Infer sessions")
        self.infer_sessions_button.clicked.connect(self._infer_sessions)
        pattern_layout.addWidget(self.infer_sessions_button)
        layout.addLayout(pattern_layout)
        pattern_help = QLabel(
            "Use {subject}, {session}, {task}, {run}, or Python regex named groups "
            r"such as (?P<run>\d+). Match the complete recording name shown below "
            "(not its path or the added -raw.fif suffix). Omitted groups keep current "
            "labels. Use Infer sessions to fill blank sessions from metadata in a "
            "background worker. Nonnumeric run labels are sorted within each subject/session/task "
            "and numbered from 1, skipping existing numeric runs. "
            "Subject changes also update assigned MRI labels. Unmatched rows stay "
            "unchanged and are reported. Matching rows must validate."
        )
        pattern_help.setWordWrap(True)
        layout.addWidget(pattern_help)
        self.pattern_status = QLabel()
        self.pattern_status.setWordWrap(True)
        self.pattern_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.pattern_status)
        self.selected_only = QCheckBox("Export selected items only (checked rows)")
        layout.addWidget(self.selected_only)
        self.tables = QSplitter(Qt.Horizontal)
        recordings_panel = QWidget(self)
        recordings_layout = QVBoxLayout(recordings_panel)
        recordings_layout.setContentsMargins(0, 0, 0, 0)
        recordings_layout.addWidget(QLabel("Recordings"))
        self.recordings = QTableWidget(len(recordings), 5)
        self.recordings.setHorizontalHeaderLabels(
            ["Recording", "Subject", "Session", "Task", "Run"]
        )
        for row, recording in enumerate(recordings):
            for column, value in enumerate(
                [
                    recording.name,
                    recording.subject,
                    recording.session,
                    recording.task,
                    recording.run,
                ]
            ):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setFlags(
                        (item.flags() & ~Qt.ItemIsEditable) | Qt.ItemIsUserCheckable
                    )
                    item.setCheckState(Qt.Checked)
                self.recordings.setItem(row, column, item)
        self.recordings.resizeColumnsToContents()
        recordings_layout.addWidget(self.recordings)
        self.tables.addWidget(recordings_panel)
        mri_panel = QWidget(self)
        mri_layout = QVBoxLayout(mri_panel)
        mri_layout.setContentsMargins(0, 0, 0, 0)
        mri_layout.addWidget(
            QLabel("FreeSurfer segmentations (including unassigned MRIs)")
        )
        self.mris = QTableWidget(len(mri_subjects), 3)
        self.mris.setHorizontalHeaderLabels(
            ["FreeSurfer subject", "BIDS subject / template", "Shared template"]
        )
        for row, (mri, subject) in enumerate(mri_subjects.items()):
            item = QTableWidgetItem(mri)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.mris.setItem(row, 0, item)
            label_item = QTableWidgetItem(subject)
            self.mris.setItem(row, 1, label_item)
            shared_item = QTableWidgetItem()
            shared_item.setFlags(
                (shared_item.flags() & ~Qt.ItemIsEditable) | Qt.ItemIsUserCheckable
            )
            shared_item.setCheckState(Qt.Unchecked)
            shared_item.setToolTip(
                "Export once as tpl-<label>; allow different recording subjects."
            )
            self.mris.setItem(row, 2, shared_item)
        self.mris.resizeColumnsToContents()
        mri_layout.addWidget(self.mris)
        self.tables.addWidget(mri_panel)
        self.tables.setStretchFactor(0, 2)
        self.tables.setStretchFactor(1, 1)
        layout.addWidget(self.tables)

        destination_layout = QHBoxLayout()
        self.destination = QLineEdit()
        self.destination.setPlaceholderText("New or empty BIDS destination directory")
        destination_layout.addWidget(self.destination)
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse)
        destination_layout.addWidget(browse)
        layout.addLayout(destination_layout)

        self.description_button = QPushButton("Dataset description...")
        self.description_button.clicked.connect(self._edit_description)
        layout.addWidget(self.description_button)
        self.anonymize = QCheckBox("Anonymize electrophysiology metadata")
        layout.addWidget(self.anonymize)
        warning = QLabel(
            "Anonymization removes identifying electrophysiology metadata and shifts "
            "all recording dates together, including empty-room dates. It does NOT "
            "deface or anonymize MRI images or native FreeSurfer files. Review these "
            "files, event descriptions and BIDS labels before sharing the dataset."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
        self.export_button = QPushButton("Export project")
        self.export_button.clicked.connect(self._export)
        layout.addWidget(self.export_button)
        self.open()

    def _edit_description(self):
        self.description_dialog = DatasetDescriptionDialog(
            self, self.dataset_description
        )
        self.description_dialog.accepted.connect(self._description_accepted)
        self.description_dialog.open()

    def _description_accepted(self):
        self.dataset_description = self.description_dialog.metadata()

    def _browse(self):
        destination = compat.getexistingdirectory(self, "Choose empty BIDS directory")
        if destination:
            self.destination.setText(destination)

    def _mapping(self, selected=False):
        recordings = []
        for row in range(self.recordings.rowCount()):
            if selected and self.recordings.item(row, 0).checkState() != Qt.Checked:
                continue
            name = self.recordings.item(row, 0).text()
            subject, session, task, run = (
                self.recordings.item(row, column).text().strip()
                for column in range(1, 5)
            )
            recordings.append(BIDSRecording(name, subject, task, session, run))
        mri_subjects = {
            self.mris.item(row, 0).text(): self.mris.item(row, 1).text().strip()
            for row in range(self.mris.rowCount())
            if not selected or self.mris.item(row, 0).checkState() == Qt.Checked
        }
        return recordings, mri_subjects

    def _shared_mris(self):
        return frozenset(
            self.mris.item(row, 0).text()
            for row in range(self.mris.rowCount())
            if self.mris.item(row, 2).checkState() == Qt.Checked
        )

    def _apply_pattern(self):
        self.pattern_status.clear()
        recordings, mri_subjects = self._mapping()
        skipped = []
        try:
            recordings, mri_subjects = bids_mapping_from_pattern(
                self.project,
                recordings,
                mri_subjects,
                self.filename_pattern.text(),
                skipped_names=skipped,
                shared_mris=self._shared_mris(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Cannot apply filename pattern", str(error))
            return
        for row, recording in enumerate(recordings):
            for column, entity in enumerate(("subject", "session", "task", "run"), 1):
                self.recordings.item(row, column).setText(getattr(recording, entity))
        for row in range(self.mris.rowCount()):
            self.mris.item(row, 1).setText(mri_subjects[self.mris.item(row, 0).text()])
        self.pattern_status.setText(
            f"Applied pattern to {len(recordings) - len(skipped)} recordings. "
            + (f"Skipped (unchanged): {', '.join(skipped)}. " if skipped else "")
            + "Review labels before export."
        )

    def _infer_sessions(self):
        recordings, mri_subjects = self._mapping(
            selected=self.selected_only.isChecked()
        )
        if all(recording.session for recording in recordings):
            self.pattern_status.setText("No blank sessions to infer.")
            return
        try:
            validate_bids_mapping(
                self.project,
                recordings,
                mri_subjects,
                allow_missing_sessions=True,
                allow_subset=self.selected_only.isChecked(),
                shared_mris=self._shared_mris(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Cannot infer sessions", str(error))
            return
        self.pattern_status.clear()
        self._set_inference_enabled(False)
        self.session_worker_dialog = WorkerDialog(
            self,
            self._infer_session_metadata,
            recordings=recordings,
            mri_subjects=mri_subjects,
            selected_only=self.selected_only.isChecked(),
            shared_mris=self._shared_mris(),
            title="Inferring BIDS sessions",
            return_exception=True,
        )
        self.session_worker_dialog.thread_finished.connect(self._sessions_finished)

    def _infer_session_metadata(
        self, recordings, mri_subjects, selected_only, shared_mris, worker_signals
    ):
        infos = {}
        worker_signals.pgbar_max.emit(len(recordings) + 1)
        for index, recording in enumerate(recordings, 1):
            worker_signals.pgbar_text.emit(f"Reading metadata: {recording.name}")
            infos[recording.name] = mne.io.read_info(
                Path(self.project.data_path)
                / recording.name
                / f"{recording.name}-raw.fif"
            )
            worker_signals.pgbar_n.emit(index)
        worker_signals.pgbar_text.emit(
            "Grouping digitization points and measurement dates..."
        )
        derived = infer_bids_sessions(recordings, infos)
        validate_bids_mapping(
            self.project,
            derived,
            mri_subjects,
            allow_subset=selected_only,
            shared_mris=shared_mris,
        )
        worker_signals.pgbar_n.emit(len(recordings) + 1)
        worker_signals.pgbar_text.emit("Session inference complete.")
        return derived

    def _set_inference_enabled(self, enabled):
        for widget in (
            self.recordings,
            self.mris,
            self.apply_pattern_button,
            self.infer_sessions_button,
            self.export_button,
            self.selected_only,
        ):
            widget.setEnabled(enabled)

    def _sessions_finished(self, result):
        self._set_inference_enabled(True)
        if isinstance(result, ExceptionTuple):
            ErrorDialog(result, parent=self)
            return
        sessions = {recording.name: recording.session for recording in result}
        for row in range(self.recordings.rowCount()):
            name = self.recordings.item(row, 0).text()
            if name in sessions:
                self.recordings.item(row, 2).setText(sessions[name])
        self.pattern_status.setText(
            f"Session inference complete for {len(result)} recordings. Review labels before export."
        )

    def _export(self):
        destination = self.destination.text().strip()
        if not destination:
            QMessageBox.warning(self, "BIDS export", "Set a destination directory.")
            return
        recordings, mri_subjects = self._mapping(
            selected=self.selected_only.isChecked()
        )
        try:
            validate_bids_mapping(
                self.project,
                recordings,
                mri_subjects,
                allow_missing_sessions=True,
                allow_subset=self.selected_only.isChecked(),
                shared_mris=self._shared_mris(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Invalid BIDS labels", str(error))
            return
        self.export_button.setEnabled(False)
        self.worker_dialog = WorkerDialog(
            self,
            self.project.export_bids,
            destination=destination,
            recordings=recordings,
            mri_subjects=mri_subjects,
            anonymize=self.anonymize.isChecked(),
            dataset_description=dict(self.dataset_description),
            selected_only=self.selected_only.isChecked(),
            shared_mris=self._shared_mris(),
            title="Exporting project to BIDS",
            show_console=True,
            return_exception=True,
        )
        self.worker_dialog.thread_finished.connect(self._finished)

    def _finished(self, result):
        self.export_button.setEnabled(True)
        if isinstance(result, ExceptionTuple):
            ErrorDialog(result, parent=self)
        else:
            QMessageBox.information(
                self, "BIDS export complete", f"Dataset saved to {result}"
            )
