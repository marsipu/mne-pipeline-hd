Exporting a project to BIDS
==========================

Choose **Export > Export project to BIDS** to copy a project using MNE-BIDS.
The source project is not modified. Select a new or empty destination directory;
existing datasets are never overwritten or merged. The destination is published
only after the complete export succeeds.

The export WorkerDialog shows stage-based progress for reading recording
metadata, session/coordinate preparation, empty-room and participant recordings,
FreeSurfer reconstructions, transforms and final publication. Large individual
recordings or FreeSurfer directories can take time without advancing the bar;
progress counts completed work items, not bytes or estimated time.

Dataset description
-------------------

Click **Dataset description...** to edit the root ``dataset_description.json``
metadata in a child dialog: dataset name, authors, license, acknowledgements,
how to acknowledge, funding, ethics approvals, references/links and dataset DOI.
Enter one item per line in list fields such as authors and funding. Blank fields
are omitted; a blank name uses the project name, or ``Exported dataset`` when
anonymizing. **OK** retains edits for this export dialog; **Cancel** discards
them. These settings are not saved to the source project.

User-supplied metadata is preserved even for anonymized exports, so review it
before sharing. Derivative descriptions keep their automatically generated
metadata. The Python API accepts the same optional ``dataset_description``
dictionary using the keyword names from ``mne_bids.make_dataset_description``
(for example ``{"authors": ["First Author"], "data_license": "CC0"}``).

Review the editable subject, session, task and run labels for every recording.
Labels contain only ASCII letters and digits, without entity prefixes such as
``sub-``. Run numbers must be positive integers; session and run are optional.
Suggested numeric subject labels group recordings by their assigned FreeSurfer
MRI. Recordings sharing a participant MRI must share a BIDS subject. Explicitly
marked shared templates do not imply that recordings belong to the same participant.
Also review the subject
labels for FreeSurfer reconstructions, including MRIs not assigned to recordings.
The recording and FreeSurfer tables are displayed side-by-side with a draggable
divider.

Shared template anatomy
----------------------

Check **Shared template** on any FreeSurfer row to allow its assigned recordings
to have different BIDS subjects. No MRI names are special-cased, including
``fsaverage``. Mark templates before applying your filename pattern, which can
then derive recording subject labels independently. The adjacent editable label
is used as the template label and must contain only ASCII letters and digits.
When selected for export, each template is copied once to
``derivatives/freesurfer/tpl-<label>``. It is not written as a participant T1w
image in the raw dataset. Existing transform files remain recording-specific.
Ordinary participant MRIs retain the one-subject consistency checks; this
shared status is an explicit user choice, not inferred from folder names.
The Python API accepts ``shared_mris={"any MRI folder name"}`` on
``default_bids_mapping``, ``bids_mapping_from_pattern`` and ``project.export_bids``.

Automatic sessions
------------------

Leave session cells empty to infer them at export time, independently for each
BIDS subject:

* Recordings with matching digitization points belong to the same session, even
  if their measurement dates differ. This uses the same comparison as the
  coregistration-copy feature: corresponding point types, identifiers and
  coordinate frames must agree, with coordinates matching within one micrometre.
  Missing digitization is never treated as a match.
* For recordings without digitization, the measurement's calendar date is used.
  They join a digitization group on that date if it is unambiguous; otherwise
  recordings without digitization on the same date form their own session.
  Different digitizations remain separate even on the same date.
* Supplied session labels are never changed. A blank session inherits a unique
  supplied label in its metadata group. Otherwise groups receive numeric labels
  such as ``01``, ``02``, skipping supplied labels. Group numbering follows
  recording-name order, not table order. Actual dates are not used as labels,
  avoiding disclosure of original dates in anonymized exports.

If a recording has neither digitization nor a measurement date, or its metadata
matches multiple supplied sessions or multiple digitizations on the same date,
export fails explicitly and requests a manual session label. Inferred labels are
logged. Duplicate recording paths are checked again after inference; they are
not silently renumbered. The Python API performs the same inference.

When recordings in a subject/session have different exact digitization metadata
(including digitized versus non-digitized recordings), the exporter assigns
``acq-coords01``, ``acq-coords02``, etc. to distinguish their coordinate sidecars.
Matching setups share an acquisition label; recordings in a session with only
one setup need no acquisition label. This also applies to empty-room recordings
on the same date. Session labels are preserved, and coordinate files are never
overwritten to resolve conflicts. Transform filenames include these labels too.

Deriving labels from recording names
-----------------------------------

Enter a **Filename pattern** and click **Apply filename pattern** to populate the
tables automatically. Match the complete recording name as displayed in the
left-hand table, without its directory or the pipeline-added ``-raw.fif`` suffix.
For example, for ``012_visit1_rest_01`` use::

    {subject}_{session}_{task}_{run}

This yields subject ``012``, session ``visit1``, task ``rest`` and run ``01``.
The placeholders match ASCII letters and digits, including ``{run}``.
Other pattern text uses Python regular-expression syntax. For more control,
use named groups, including optional groups and regex quantifiers::

    (?P<subject>\d{3})_(?P<session>visit\d+)_(?P<task>rest|motor)_(?P<run>\d+)

The supported group names are ``subject``, ``session``, ``task`` and ``run``.
Entities omitted from the pattern retain their current labels. An optional
named group that does not participate in a match clears that entity.
For example, ``.*_run{run}`` updates only run labels.

Nonnumeric run labels are automatically converted to positive integers, for both
``{run}`` and ``(?P<run>...)``. Within each subject/session/task group, distinct
nonnumeric labels are sorted lexicographically (case-sensitive) and assigned the
lowest available numbers starting at 1. Existing numeric labels, including leading
zeros, are preserved and their numbers are skipped when assigning new ones.
For example, ``{subject}_{task}_{run}`` maps ``pp1a_256_a`` and ``pp1a_256_b``
to runs ``1`` and ``2``. If run ``01`` already exists in that group, ``a`` and
``b`` become ``2`` and ``3`` instead. Numbering is independent of table order and
restarts for each group; it depends on which labels are present, so a lone ``b``
becomes ``1``. Empty optional runs stay empty; numeric zero and invalid labels
remain errors. Repeated labels are not assigned distinct numbers to hide a
duplicate recording. Review the resulting numeric values before exporting.

Derived subject labels also update assigned FreeSurfer subjects; unassigned
MRIs retain their current labels. Conflicting subjects for a shared MRI,
duplicate BIDS recording labels, invalid labels, invalid regexes and unmatched
recording names are reported explicitly. Matching rows are updated while
unmatched rows keep their previous values; skipped names appear in the status
message. Invalid patterns or invalid matching labels still leave both tables
unchanged. Subject changes update assigned MRI labels, so unmatched recordings
sharing that MRI may need manual subject edits before export. Review or manually edit
the results before exporting; applying a pattern does not write any files.
Applying a pattern only parses names; it does not read recording files.
Click **Infer sessions** separately to populate blank session cells from metadata.
A background WorkerDialog shows which recording header is being read, progress,
and the digitization/date grouping phase while the GUI stays responsive.
Supplied sessions are preserved. Editing the tables, applying patterns and
exporting are disabled during inference. Session cells are updated together only
after successful inference and validation. Missing files or ambiguous metadata
leave both tables unchanged and display an error. Export still automatically
infers any sessions left blank.

Exported data
-------------

By default the entire project is exported. Enable **Export selected items only
(checked rows)** to use the checkboxes in the first column of each table.
Recording and FreeSurfer selections are independent: selecting a recording does
not force its MRI to be exported. Included MRIs must still have consistent BIDS
subject labels. Only empty-room recordings assigned to included recordings are
automatically included in this mode; unrelated empty-room recordings are omitted.
Unselected files are not opened or required to exist. Selecting only FreeSurfer
subjects is supported; an entirely empty selection is rejected. Session inference
also respects the selection when the toggle is enabled. Regex application still
operates on all rows.

The export includes:

* All original MEG/EEG recordings by default, or checked recordings in selection
  mode. MNE-BIDS writes
  available recording metadata, annotations, channel information, digitization
  and participant information. Project bad-channel assignments are included.
  EEG/iEEG recordings stored as FIF are converted to BrainVision using pybv.
* Saved events from the **active parameter preset**, with the complete project
  event-ID mapping read directly at export time from
  ``_pipeline_scripts/meeg_event_id_<project-name>.json``, not the cached
  in-memory mapping or just labels selected for epoching. Save event-ID edits
  before exporting. A missing or invalid event-ID JSON file fails the export
  explicitly. Unlabelled event codes receive ``event/<code>`` descriptions.
* All original empty-room recordings, including unassigned recordings, under
  ``sub-emptyroom``. Measurement dates are required. Recordings sharing a date
  have distinct run numbers. Assigned recordings are linked through MNE-BIDS'
  ``AssociatedEmptyRoom`` metadata.
* Available ``mri/T1.mgz`` images as BIDS T1w images. These are reconstructed T1
  images; the exporter does not invent missing acquisition metadata or landmarks.
* Native FreeSurfer ``mri``, ``surf``, ``label``, ``stats`` and ``scripts``
  directories in ``derivatives/freesurfer/sub-<label>``. Pipeline source models,
  BEM solutions and other files outside these reconstruction directories are
  excluded.
* Existing recording-specific ``*-trans.fif`` files in
  ``derivatives/mne-pipeline-hd`` under their BIDS subject/session/task/run names.
  These remain native MNE transforms, not a standardized BIDS transform format.

No epochs, evokeds, ICA, filtered recordings, covariance matrices, forward/inverse
solutions, plots or other pipeline derivatives are copied. Missing optional
events, T1 images or transforms are not generated. Missing original recordings
or registered FreeSurfer reconstructions fail the export explicitly.

Optional anonymization
----------------------

**Anonymize electrophysiology metadata** is off by default. When enabled,
MNE-BIDS removes identifying electrophysiology metadata and applies one shared
automatically determined date shift to all original and empty-room recordings,
preserving their relative timing. The shift is not stored in the exported dataset.

This is **not full dataset anonymization**: MRI images are not defaced, and native
FreeSurfer images, headers, scripts and logs are copied unchanged and can contain
identifying information. BIDS labels, annotations and event descriptions may
also identify participants. Review and sanitize these before sharing the dataset.

Python API
----------

``project.export_bids(destination, recordings=None, mri_subjects=None,
anonymize=False)`` exports the same data without opening the dialog. Use
``default_bids_mapping(project)`` from ``mne_pipeline_hd.pipeline.bids`` to obtain
editable ``BIDSRecording`` objects and the FreeSurfer-name-to-BIDS-subject mapping.
