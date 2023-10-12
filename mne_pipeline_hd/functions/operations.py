# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

from __future__ import print_function

import gc
import logging
import os
import shutil
import subprocess
import sys
import time
from functools import reduce
from itertools import combinations
from os import environ
from os.path import isdir, isfile, join

import autoreject as ar
import mne
import mne_connectivity
import numpy as np
from mne.preprocessing import ICA, find_bad_channels_maxwell

from mne_pipeline_hd.pipeline.loading import MEEG, FSMRI
from mne_pipeline_hd.pipeline.pipeline_utils import (
    check_kwargs,
    compare_filep,
    ismac,
    iswin,
    get_n_jobs,
)


# Todo: Create docstrings for each function
# =============================================================================
# PREPROCESSING AND GETTING TO EVOKED AND TFR
# =============================================================================
def find_bads(meeg, n_jobs, **kwargs):
    raw = meeg.load_raw()

    if raw.info["dev_head_t"] is None:
        coord_frame = "meg"
    else:
        coord_frame = "head"

    # Set number of CPU-cores to use
    os.environ["OMP_NUM_THREADS"] = str(get_n_jobs(n_jobs))

    noisy_chs, flat_chs = find_bad_channels_maxwell(
        raw, coord_frame=coord_frame, **kwargs
    )
    logging.info(f"Noisy channels: {noisy_chs}\n" f"Flat channels: {flat_chs}")
    raw.info["bads"] = noisy_chs + flat_chs + raw.info["bads"]
    meeg.set_bad_channels(raw.info["bads"])
    meeg.save_raw(raw)


def filter_data(
    meeg,
    filter_target,
    highpass,
    lowpass,
    filter_length,
    l_trans_bandwidth,
    h_trans_bandwidth,
    filter_method,
    iir_params,
    fir_phase,
    fir_window,
    fir_design,
    skip_by_annotation,
    fir_pad,
    n_jobs,
    enable_cuda,
    erm_t_limit,
    bad_interpolation,
):
    # Compare Parameters from last run
    filtered_path = meeg.io_dict[filter_target]["path"]
    results = compare_filep(
        meeg, filtered_path, ["highpass", "lowpass", "bad_interpolation"]
    )

    if any([results[key] != "equal" for key in results]):
        # Load Data
        data = meeg.load(filter_target)

        # use cuda for filtering if enabled
        if enable_cuda:
            mne.cuda.init_cuda(ignore_config=True)
            n_jobs = "cuda"

        # Filter Data
        if filter_target == "evoked":
            for evoked in data:
                evoked.filter(
                    highpass,
                    lowpass,
                    filter_length=filter_length,
                    l_trans_bandwidth=l_trans_bandwidth,
                    h_trans_bandwidth=h_trans_bandwidth,
                    n_jobs=n_jobs,
                    method=filter_method,
                    iir_params=iir_params,
                    phase=fir_phase,
                    fir_window=fir_window,
                    fir_design=fir_design,
                    skip_by_annotation=skip_by_annotation,
                    pad=fir_pad,
                )
        else:
            data.filter(
                highpass,
                lowpass,
                filter_length=filter_length,
                l_trans_bandwidth=l_trans_bandwidth,
                h_trans_bandwidth=h_trans_bandwidth,
                n_jobs=n_jobs,
                method=filter_method,
                iir_params=iir_params,
                phase=fir_phase,
                fir_window=fir_window,
                fir_design=fir_design,
                skip_by_annotation=skip_by_annotation,
                pad=fir_pad,
            )

        # Save Data
        if filter_target == "raw":
            meeg.save("raw_filtered", data)
        else:
            meeg.save(filter_target, data)

        # Remove raw to avoid memory overload
        del data
        gc.collect()

    else:
        print(
            f"{meeg.name} already filtered with highpass={highpass} "
            f"and lowpass={lowpass}"
        )

    # Filter Empty-Room-Data too
    if meeg.erm:
        erm_results = compare_filep(
            meeg, meeg.erm_processed_path, ["highpass", "lowpass", "bad_interpolation"]
        )
        if any([erm_results[key] != "equal" for key in erm_results]):
            erm_raw = meeg.load_erm()

            # Crop ERM-Measurement to limit if given
            if erm_t_limit:
                erm_length = erm_raw.n_times / erm_raw.info["sfreq"]  # in s
                if erm_length > erm_t_limit:
                    diff = erm_length - erm_t_limit
                    tmin = diff / 2
                    tmax = erm_length - diff / 2
                    erm_raw.crop(tmin=tmin, tmax=tmax)

            erm_raw.filter(
                highpass,
                lowpass,
                filter_length=filter_length,
                l_trans_bandwidth=l_trans_bandwidth,
                h_trans_bandwidth=h_trans_bandwidth,
                n_jobs=n_jobs,
                method=filter_method,
                iir_params=iir_params,
                phase=fir_phase,
                fir_window=fir_window,
                fir_design=fir_design,
                skip_by_annotation=skip_by_annotation,
                pad=fir_pad,
            )

            if bad_interpolation == "raw":
                info = meeg.load_info()
                erm_raw.info["dig"] = info["dig"]
                erm_raw = erm_raw.interpolate_bads()

            meeg.save_erm_processed(erm_raw)
            print("ERM-Data filtered and saved")
        else:
            print(
                f"{meeg.erm} already filtered with highpass={highpass} "
                f"and lowpass={lowpass}"
            )

    else:
        print("no erm_file assigned")


def notch_filter(meeg, notch_frequencies, n_jobs):
    raw_filtered = meeg.load_filtered()

    raw_filtered = raw_filtered.notch_filter(notch_frequencies, n_jobs=1)
    meeg.save_filtered(raw_filtered)


def interpolate_bads(meeg, bad_interpolation):
    data = meeg.load(bad_interpolation)

    if bad_interpolation == "evoked":
        for evoked in data:
            # Add bads for channels present
            evoked.info["bads"] = [b for b in meeg.bad_channels if b in data.ch_names]
            evoked.interpolate_bads(reset_bads=True)
    else:
        # Add bads for channels present
        data.info["bads"] = [b for b in meeg.bad_channels if b in data.ch_names]
        data.interpolate_bads(reset_bads=True)

    meeg.save(bad_interpolation, data)


def add_erm_ssp(
    meeg, erm_ssp_duration, erm_n_grad, erm_n_mag, erm_n_eeg, n_jobs, show_plots
):
    raw_filtered = meeg.load_filtered()
    erm_filtered = meeg.load_erm_processed()

    # Only include channels from Empty-Room-Data,
    # which are present in filtered-data
    erm_filtered = erm_filtered.copy().pick(
        [ch for ch in erm_filtered.ch_names if ch in raw_filtered.ch_names]
    )

    erm_projs = mne.compute_proj_raw(
        erm_filtered,
        duration=erm_ssp_duration,
        n_grad=erm_n_grad,
        n_mag=erm_n_mag,
        n_eeg=erm_n_eeg,
        n_jobs=n_jobs,
    )

    raw_filtered.add_proj(erm_projs, remove_existing=True)
    meeg.save_filtered(raw_filtered)

    fig = mne.viz.plot_projs_topomap(
        erm_projs, erm_filtered.info, colorbar=True, show=show_plots
    )
    meeg.plot_save("ssp_erm", matplotlib_figure=fig)


def eeg_reference_raw(meeg, ref_channels):
    raw_filtered = meeg.load_filtered()

    if ref_channels == "REST":
        forward = meeg.load_forward()
    else:
        forward = None

    if ref_channels == "average":
        projection = True
    else:
        projection = False

    raw_filtered.set_eeg_reference(
        ref_channels=ref_channels, projection=projection, forward=forward
    )
    meeg.save_filtered(raw_filtered)


def find_events(
    meeg, stim_channels, min_duration, shortest_event, adjust_timeline_by_msec
):
    raw = meeg.load_raw()  # No copy to consume less memory

    events = mne.find_events(
        raw,
        min_duration=min_duration,
        shortest_event=shortest_event,
        stim_channel=stim_channels,
    )

    # apply latency correction
    events[:, 0] = [
        ts + np.round(adjust_timeline_by_msec * 10**-3 * raw.info["sfreq"])
        for ts in events[:, 0]
    ]

    ids = np.unique(events[:, 2])
    print("unique ID's found: ", ids)

    if np.size(events) > 0:
        meeg.save_events(events)
    else:
        print("No events found")


def find_6ch_binary_events(meeg, min_duration, shortest_event, adjust_timeline_by_msec):
    raw = meeg.load_raw()  # No copy to consume less memory

    # Binary Coding of 6 Stim Channels in Biomagenetism Lab Heidelberg
    # prepare arrays
    events = np.ndarray(shape=(0, 3), dtype=np.int32)
    evs = list()
    evs_tol = list()

    # Find events for each stim channel, append sample values to list
    evs.append(
        mne.find_events(
            raw,
            min_duration=min_duration,
            shortest_event=shortest_event,
            stim_channel=["STI 001"],
        )[:, 0]
    )
    evs.append(
        mne.find_events(
            raw,
            min_duration=min_duration,
            shortest_event=shortest_event,
            stim_channel=["STI 002"],
        )[:, 0]
    )
    evs.append(
        mne.find_events(
            raw,
            min_duration=min_duration,
            shortest_event=shortest_event,
            stim_channel=["STI 003"],
        )[:, 0]
    )
    evs.append(
        mne.find_events(
            raw,
            min_duration=min_duration,
            shortest_event=shortest_event,
            stim_channel=["STI 004"],
        )[:, 0]
    )
    evs.append(
        mne.find_events(
            raw,
            min_duration=min_duration,
            shortest_event=shortest_event,
            stim_channel=["STI 005"],
        )[:, 0]
    )
    evs.append(
        mne.find_events(
            raw,
            min_duration=min_duration,
            shortest_event=shortest_event,
            stim_channel=["STI 006"],
        )[:, 0]
    )

    for i in evs:
        # delete events in each channel,
        # which are too close too each other (1ms)
        too_close = np.where(np.diff(i) <= 1)
        if np.size(too_close) >= 1:
            print(
                f"Two close events (1ms) at samples "
                f"{i[too_close] + raw.first_samp}, first deleted"
            )
            i = np.delete(i, too_close, 0)
            evs[evs.index(i)] = i

        # add tolerance to each value
        i_tol = np.ndarray(shape=(0, 1), dtype=np.int32)
        for t in i:
            i_tol = np.append(i_tol, t - 1)
            i_tol = np.append(i_tol, t)
            i_tol = np.append(i_tol, t + 1)

        evs_tol.append(i_tol)

    # Get events from combinated Stim-Channels
    equals = reduce(
        np.intersect1d,
        (evs_tol[0], evs_tol[1], evs_tol[2], evs_tol[3], evs_tol[4], evs_tol[5]),
    )
    # elimnate duplicated events
    too_close = np.where(np.diff(equals) <= 1)
    if np.size(too_close) >= 1:
        equals = np.delete(equals, too_close, 0)
        equals -= 1  # correction, because of shift with deletion

    for q in equals:
        if (
            q not in events[:, 0]
            and q not in events[:, 0] + 1
            and q not in events[:, 0] - 1
        ):
            events = np.append(events, [[q, 0, 63]], axis=0)

    for a, b, c, d, e in combinations(range(6), 5):
        equals = reduce(
            np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c], evs_tol[d], evs_tol[e])
        )
        too_close = np.where(np.diff(equals) <= 1)
        if np.size(too_close) >= 1:
            equals = np.delete(equals, too_close, 0)
            equals -= 1

        for q in equals:
            if (
                q not in events[:, 0]
                and q not in events[:, 0] + 1
                and q not in events[:, 0] - 1
            ):
                events = np.append(
                    events,
                    [[q, 0, int(2**a + 2**b + 2**c + 2**d + 2**e)]],
                    axis=0,
                )

    for a, b, c, d in combinations(range(6), 4):
        equals = reduce(
            np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c], evs_tol[d])
        )
        too_close = np.where(np.diff(equals) <= 1)
        if np.size(too_close) >= 1:
            equals = np.delete(equals, too_close, 0)
            equals -= 1

        for q in equals:
            if (
                q not in events[:, 0]
                and q not in events[:, 0] + 1
                and q not in events[:, 0] - 1
            ):
                events = np.append(
                    events, [[q, 0, int(2**a + 2**b + 2**c + 2**d)]], axis=0
                )

    for a, b, c in combinations(range(6), 3):
        equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c]))
        too_close = np.where(np.diff(equals) <= 1)
        if np.size(too_close) >= 1:
            equals = np.delete(equals, too_close, 0)
            equals -= 1

        for q in equals:
            if (
                q not in events[:, 0]
                and q not in events[:, 0] + 1
                and q not in events[:, 0] - 1
            ):
                events = np.append(
                    events, [[q, 0, int(2**a + 2**b + 2**c)]], axis=0
                )

    for a, b in combinations(range(6), 2):
        equals = np.intersect1d(evs_tol[a], evs_tol[b])
        too_close = np.where(np.diff(equals) <= 1)
        if np.size(too_close) >= 1:
            equals = np.delete(equals, too_close, 0)
            equals -= 1

        for q in equals:
            if (
                q not in events[:, 0]
                and q not in events[:, 0] + 1
                and q not in events[:, 0] - 1
            ):
                events = np.append(events, [[q, 0, int(2**a + 2**b)]], axis=0)

    # Get single-channel events
    for i in range(6):
        for e in evs[i]:
            if (
                e not in events[:, 0]
                and e not in events[:, 0] + 1
                and e not in events[:, 0] - 1
            ):
                events = np.append(events, [[e, 0, 2**i]], axis=0)

    # sort only along samples(column 0)
    events = events[events[:, 0].argsort()]

    # apply latency correction
    events[:, 0] = [
        ts + np.round(adjust_timeline_by_msec * 10**-3 * raw.info["sfreq"])
        for ts in events[:, 0]
    ]

    ids = np.unique(events[:, 2])
    print("unique ID's found: ", ids)

    if np.size(events) > 0:
        meeg.save_events(events)
    else:
        print("No events found")


def epoch_raw(
    meeg,
    ch_types,
    ch_names,
    t_epoch,
    baseline,
    apply_proj,
    reject,
    flat,
    reject_by_annotation,
    bad_interpolation,
    use_autoreject,
    consensus_percs,
    n_interpolates,
    overwrite_ar,
    decim,
    n_jobs,
):
    raw_filtered = meeg.load_filtered()
    events = meeg.load_events()

    # Pick selected channel_types if not done before
    raw_filtered.pick(ch_types)

    if len(ch_names) > 0 and ch_names != "all":
        raw_filtered.pick(ch_names)

    if bad_interpolation is None:
        # Exclude bad-channels if no Bad-Channel-Interpolation is intended
        # after making the epochs or the Evokeds
        raw_filtered.pick("all", exclude="bads")

    epochs = mne.Epochs(
        raw_filtered,
        events,
        meeg.event_id,
        t_epoch[0],
        t_epoch[1],
        baseline,
        preload=True,
        proj=apply_proj,
        reject=None,
        flat=None,
        decim=decim,
        on_missing="ignore",
        reject_by_annotation=reject_by_annotation,
    )

    if (
        any([i is not None for i in [use_autoreject, reject, flat]])
        and bad_interpolation == "evokeds"
    ):
        raise RuntimeWarning(
            'With bad_interpolation="Evokeds", '
            "the bad channels are still included and "
            "may heavily influence the outcome of dropping epochs with reject,"
            " flat or autoreject!"
            "\n(to solve this you could uncheck autoreject, "
            "reject and flat or set bad_interpolationto another value)"
        )

    existing_ch_types = epochs.get_channel_types(unique=True, only_data_chs=True)

    if use_autoreject == "Interpolation":
        ar_object = ar.AutoReject(
            n_interpolate=n_interpolates, consensus=consensus_percs, n_jobs=n_jobs
        )
        epochs, reject_log = ar_object.fit_transform(epochs, return_log=True)
        meeg.save_reject_log(reject_log)

    else:
        if use_autoreject == "Threshold":
            reject = meeg.load_json("autoreject_threshold")
            if reject is None or overwrite_ar:
                reject = ar.get_rejection_threshold(epochs, random_state=8)
                meeg.save_json("autoreject_threshold", reject)
            print(
                f"Dropping bad epochs with autoreject"
                f" rejection-thresholds: {reject}"
            )

        else:
            # Remove entries from reject if not present in channels

            if reject is not None:
                reject = reject.copy()
                for key in [k for k in reject if k not in existing_ch_types]:
                    reject.pop(key)
            print(f"Dropping bad epochs with chosen " f"rejection-thresholds: {reject}")

        epochs.drop_bad(reject=reject)

    if flat is not None:
        # Remove entries from flat if not present in channels
        flat = flat.copy()
        for key in [k for k in flat if k not in existing_ch_types]:
            flat.pop(key)
        print(f"Dropping bad epochs with chosen flat-thresholds: {flat}")
        epochs.drop_bad(flat=flat)

    meeg.save_epochs(epochs)


def run_ica(
    meeg,
    ica_method,
    ica_fitto,
    n_components,
    ica_noise_cov,
    ica_remove_proj,
    ica_reject,
    ica_autoreject,
    overwrite_ar,
    ch_types,
    ch_names,
    reject_by_annotation,
    ica_eog,
    eog_channel,
    ica_ecg,
    ecg_channel,
    **kwargs,
):
    data = meeg.load(ica_fitto)
    # Bad-Channels and Channel-Types are already picked in epochs
    if ica_fitto != "epochs":
        data.pick(ch_types, exclude="bads")
        if len(ch_names) > 0 and ch_names != "all":
            data.pick(ch_names)

    # Filter if data is not highpass-filtered >= 1
    if data.info["highpass"] < 1:
        filt_data = data.filter(1, None)
    else:
        filt_data = data

    if ica_noise_cov:
        noise_cov = meeg.load_noise_covariance()
    else:
        noise_cov = None

    ica_kwargs = check_kwargs(kwargs, ICA)
    ica = ICA(
        n_components=n_components,
        noise_cov=noise_cov,
        random_state=8,
        method=ica_method,
        **ica_kwargs,
    )

    if ica_autoreject and ica_fitto != "epochs":
        # Estimate Reject-Thresholds on simulated epochs
        # Creating simulated epochs with len 1s
        simulated_events = mne.make_fixed_length_events(data, duration=1)
        simulated_epochs = mne.Epochs(
            data, simulated_events, baseline=None, tmin=0, tmax=1, proj=False
        )
        reject = ar.get_rejection_threshold(simulated_epochs, random_state=8)
        print(f"Autoreject Rejection-Threshold: {reject}")
    elif ica_autoreject and ica_fitto == "epochs":
        reject = meeg.load_json("autoreject_threshold")
        if reject is None or overwrite_ar:
            reject = ar.get_rejection_threshold(data, random_state=8)
            meeg.save_json("autoreject_threshold", reject)
    else:
        reject = ica_reject

    # Remove projections
    if ica_remove_proj:
        filt_data.del_proj()

    fit_kwargs = check_kwargs(kwargs, ica.fit)
    ica.fit(
        filt_data,
        reject=reject,
        reject_by_annotation=reject_by_annotation,
        **fit_kwargs,
    )

    # Load raw for EOG/ECG-Detection without picks
    # (e.g. still containing EEG for EOG or EOG channels)
    eog_ecg_raw = meeg.load_filtered()
    # Include EOG/ECG with all the data-channels
    eog_ecg_raw.pick_types(
        meg=True,
        eeg=True,
        eog=True,
        ecg=True,
        seeg=True,
        ecog=True,
        fnirs=True,
        exclude="bads",
    )

    if ica_eog:
        create_eog_kwargs = check_kwargs(kwargs, mne.preprocessing.create_eog_epochs)
        find_eog_kwargs = check_kwargs(kwargs, ica.find_bads_eog)

        # Using an EOG channel to select components if possible
        if "eog" in eog_ecg_raw.get_channel_types():
            eog_epochs = mne.preprocessing.create_eog_epochs(
                eog_ecg_raw, **create_eog_kwargs
            )
            eog_indices, eog_scores = ica.find_bads_eog(eog_ecg_raw, **find_eog_kwargs)
        elif eog_channel and eog_channel in eog_ecg_raw.ch_names:
            eog_epochs = mne.preprocessing.create_eog_epochs(
                eog_ecg_raw, ch_name=eog_channel, **create_eog_kwargs
            )
            eog_indices, eog_scores = ica.find_bads_eog(
                eog_ecg_raw, ch_name=eog_channel, **find_eog_kwargs
            )
        else:
            eog_indices, eog_scores, eog_epochs = None, None, None
            print(
                "No EOG-Channel found or set, "
                "thus EOG can't be used for automatic Component-Selection"
            )

        if eog_epochs:
            ica.exclude += eog_indices
            meeg.save_eog_epochs(eog_epochs)
            meeg.save_json("eog_indices", eog_indices)
            meeg.save_json("eog_scores", eog_scores)
    else:
        # Remove old eog_epochs, eog_indices and eog_scores if new ICA is calculated
        meeg.remove_path("epochs_eog")
        meeg.remove_json("eog_indices")
        meeg.remove_json("eog_scores")

    if ica_ecg:
        create_ecg_kwargs = check_kwargs(kwargs, mne.preprocessing.create_ecg_epochs)
        find_ecg_kwargs = check_kwargs(kwargs, ica.find_bads_ecg)

        # Using an ECG channel to select components
        if ecg_channel and ecg_channel in eog_ecg_raw.ch_names:
            ecg_epochs = mne.preprocessing.create_ecg_epochs(
                eog_ecg_raw, ch_name=ecg_channel, **create_ecg_kwargs
            )
            ecg_indices, ecg_scores = ica.find_bads_ecg(
                eog_ecg_raw, ch_name=ecg_channel, **find_ecg_kwargs
            )
        elif any(
            [
                ch_type in eog_ecg_raw.get_channel_types()
                for ch_type in ["mag", "grad", "meg"]
            ]
        ):
            print("ECG-Signal reconstructed from MEG")
            ecg_epochs = mne.preprocessing.create_ecg_epochs(
                eog_ecg_raw, **create_ecg_kwargs
            )
            ecg_indices, ecg_scores = ica.find_bads_ecg(eog_ecg_raw, **find_ecg_kwargs)
        else:
            ecg_indices, ecg_scores, ecg_epochs = None, None, None
            print(
                "No ECG-Channel found or set and no MEG-Channel "
                "for ECG-Detection present, thus ECG can't be used for "
                "automatic Component-Selection."
            )

        if ecg_epochs:
            ica.exclude += ecg_indices
            meeg.save_ecg_epochs(ecg_epochs)
            meeg.save_json("ecg_indices", ecg_indices)
            meeg.save_json("ecg_scores", ecg_scores)
    else:
        # Remove old ecg_epochs, ecg_indices and ecg_scores if new ICA is calculated
        meeg.remove_path("epochs_ecg")
        meeg.remove_json("ecg_indices")
        meeg.remove_json("ecg_scores")

    meeg.save_ica(ica)
    # Add components to ica_exclude-dictionary
    meeg.pr.meeg_ica_exclude[meeg.name] = ica.exclude


def apply_ica(meeg, ica_apply_target, n_pca_components):
    # Check file-parameters to make sure,
    # that ica is not applied twice in a row

    data = meeg.load(ica_apply_target)
    ica = meeg.load_ica()

    if len(ica.exclude) == 0:
        print(f"No components excluded for {meeg.name}")
    else:
        applied_data = ica.apply(data, n_pca_components=n_pca_components)
        meeg.save(ica_apply_target, applied_data)

        # Apply to Empty-Room-Data as well if present
        if meeg.erm:
            try:
                erm_data = meeg.load_erm_processed()
            except FileNotFoundError:
                erm_data = meeg.load_erm()
            try:
                ica.apply(erm_data, n_pca_components=n_pca_components)
            # Todo: Unmeddling ERM-SSP and ICA stuff
            except ValueError:
                print(
                    "There is an unresolved issue with combining SSP "
                    "from ERM and applying ICA on this ERM"
                )
            else:
                meeg.save_erm_processed(erm_data)


def get_evokeds(meeg):
    epochs = meeg.load_epochs()
    evokeds = []
    for trial in meeg.sel_trials:
        evoked = epochs[trial].average()
        # Todo: optional if you want weights in your evoked.comment?!
        evoked.comment = trial
        evokeds.append(evoked)

    meeg.save_evokeds(evokeds)


def calculate_gfp(evoked):
    ch_types = evoked.get_channel_types(unique=True, only_data_chs=True)
    gfp_dict = dict()
    for ch_type in ch_types:
        d = evoked.copy().pick(ch_type).data
        gfp = np.sqrt((d * d).mean(axis=0))
        gfp_dict[ch_type] = gfp

    return gfp_dict


def grand_avg_evokeds(group, ga_interpolate_bads, ga_drop_bads):
    trial_dict = {}
    for name in group.group_list:
        meeg = MEEG(name, group.ct)
        print(f"Add {name} to grand_average")
        evokeds = meeg.load_evokeds()
        for evoked in evokeds:
            if evoked.nave != 0:
                if evoked.comment in trial_dict:
                    trial_dict[evoked.comment].append(evoked)
                else:
                    trial_dict.update({evoked.comment: [evoked]})
            else:
                print(f"{evoked.comment} for {name} got nave=0")

    ga_evokeds = dict()
    for trial in trial_dict:
        if len(trial_dict[trial]) != 0:
            ga = mne.grand_average(
                trial_dict[trial],
                interpolate_bads=ga_interpolate_bads,
                drop_bads=ga_drop_bads,
            )
            ga.comment = trial
            ga_evokeds[trial] = ga

    group.save_ga_evokeds(ga_evokeds)


def compute_psd_raw(meeg, psd_method, n_jobs, **kwargs):
    raw = meeg.load_filtered()
    psd_raw = raw.compute_psd(
        method=psd_method, fmax=raw.info["lowpass"], n_jobs=n_jobs, **kwargs
    )
    meeg.save_psd_raw(psd_raw)


def compute_psd_epochs(meeg, psd_method, n_jobs, **kwargs):
    epochs = meeg.load_epochs()
    psd_epochs = epochs.compute_psd(
        method=psd_method, fmax=epochs.info["lowpass"], n_jobs=n_jobs, **kwargs
    )
    meeg.save_psd_epochs(psd_epochs)


def tfr(
    meeg,
    tfr_freqs,
    tfr_n_cycles,
    tfr_average,
    tfr_use_fft,
    tfr_baseline,
    tfr_baseline_mode,
    tfr_method,
    multitaper_bandwidth,
    stockwell_width,
    n_jobs,
    **kwargs,
):
    powers = list()
    itcs = list()

    epochs = meeg.load_epochs()

    # Calculate Time-Frequency for each trial from epochs
    # using the selected method
    for trial in meeg.sel_trials:
        if tfr_method == "multitaper":
            multitaper_kwargs = check_kwargs(kwargs, mne.time_frequency.tfr_multitaper)
            tfr_result = mne.time_frequency.tfr_multitaper(
                epochs[trial],
                freqs=tfr_freqs,
                n_cycles=tfr_n_cycles,
                time_bandwidth=multitaper_bandwidth,
                n_jobs=n_jobs,
                use_fft=tfr_use_fft,
                return_itc=tfr_average,
                average=tfr_average,
                **multitaper_kwargs,
            )
        elif tfr_method == "stockwell":
            fmin, fmax = tfr_freqs[[0, -1]]
            stockwell_kwargs = check_kwargs(kwargs, mne.time_frequency.tfr_stockwell)
            tfr_result = mne.time_frequency.tfr_stockwell(
                epochs[trial],
                fmin=fmin,
                fmax=fmax,
                width=stockwell_width,
                n_jobs=n_jobs,
                return_itc=True,
                **stockwell_kwargs,
            )
        else:
            morlet_kwargs = check_kwargs(kwargs, mne.time_frequency.tfr_morlet)
            tfr_result = mne.time_frequency.tfr_morlet(
                epochs[trial],
                freqs=tfr_freqs,
                n_cycles=tfr_n_cycles,
                n_jobs=n_jobs,
                use_fft=tfr_use_fft,
                return_itc=tfr_average,
                average=tfr_average,
                **morlet_kwargs,
            )

        if isinstance(tfr_result, tuple):
            power = tfr_result[0]
            itc = tfr_result[1]
        else:
            power = tfr_result
            itc = None

        power.comment = trial
        if itc:
            itc.comment = trial

        if tfr_baseline:
            power = power.apply_baseline(tfr_baseline, mode=tfr_baseline_mode)
            if itc:
                itc = itc.apply_baseline(tfr_baseline, mode=tfr_baseline_mode)

        powers.append(power)
        if itc:
            itcs.append(itc)

    if tfr_average or tfr_method == "stockwell":
        meeg.save_power_tfr_average(powers)
        meeg.save_itc_tfr_average(itcs)

    else:
        meeg.save_power_tfr_epochs(powers)
        meeg.save_itc_tfr_epochs(itcs)

        # Saving average TFR
        powers_ave = [p.average() for p in powers]
        itcs_ave = [i.average() for i in itcs]

        meeg.save_power_tfr_average(powers_ave)
        meeg.save_itc_tfr_average(itcs_ave)


def grand_avg_tfr(group):
    trial_dict = dict()
    for name in group.group_list:
        meeg = MEEG(name, group.ct)
        print(f"Add {name} to grand_average")
        powers = meeg.load_power_tfr_average()
        for pw in powers:
            if pw.nave != 0:
                if pw.comment in trial_dict:
                    trial_dict[pw.comment].append(pw)
                else:
                    trial_dict.update({pw.comment: [pw]})
            else:
                print(f"{pw.comment} for {name} got nave=0")

    ga_dict = dict()
    for trial in trial_dict:
        if len(trial_dict[trial]) != 0:
            # Make sure, all have the same number of channels
            commons = set()
            for pw in trial_dict[trial]:
                if len(commons) == 0:
                    for c in pw.ch_names:
                        commons.add(c)
                commons = commons & set(pw.ch_names)
            print(f"{trial}:Reducing all n_channels to {len(commons)}")
            for idx, pw in enumerate(trial_dict[trial]):
                trial_dict[trial][idx] = pw.pick(list(commons))

            ga = mne.grand_average(
                trial_dict[trial], interpolate_bads=True, drop_bads=True
            )
            ga.comment = trial
            ga_dict[trial] = ga

    group.save_ga_tfr(ga_dict)


# ==============================================================================
# BASH OPERATIONS
# ==============================================================================
# These functions do not work on Windows
# local function used in the bash commands below
def run_freesurfer_subprocess(command, subjects_dir, fs_path, mne_path=None):
    # Several experiments with subprocess showed,
    # that it seems impossible to run commands like "source" from
    # a subprocess to get SetUpFreeSurfer.sh into the environment.
    # Current workaround is adding the binaries to PATH manually,
    # after the user set the path to FREESURFER_HOME
    if fs_path is None:
        raise RuntimeError("Path to FREESURFER_HOME not set, can't run this function")
    environment = environ.copy()
    environment["FREESURFER_HOME"] = fs_path
    environment["SUBJECTS_DIR"] = subjects_dir
    if iswin:
        command.insert(0, "wsl")
        if mne_path is None:
            raise RuntimeError(
                "Path to MNE-Environment in Windows-Subsytem for Linux(WSL)"
                " not set, can't run this function"
            )

        # Add Freesurfer-Path, MNE-Path and standard Ubuntu-Paths,
        # which get lost when sharing the Path from Windows
        # to WSL
        environment["PATH"] = (
            f"{fs_path}/bin:{mne_path}/bin:"
            f"/usr/local/sbin:"
            f"/usr/local/bin:"
            f"/usr/sbin:"
            f"/usr/bin:"
            f"/sbin:"
            f"/bin"
        )
        environment["WSLENV"] = "PATH/u:SUBJECTS_DIR/p:FREESURFER_HOME/u"
    else:
        # Add Freesurfer to Path
        environment["PATH"] = environment["PATH"] + f":{fs_path}/bin"

    # Add Mac-specific Freesurfer-Paths
    # (got them from FreeSurferEnv.sh in FREESURFER_HOME)
    if ismac:
        if isdir(join(fs_path, "lib/misc/lib")):
            environment["PATH"] = environment["PATH"] + f":{fs_path}/lib/misc/bin"
            environment["MISC_LIB"] = join(fs_path, "lib/misc/lib")
            environment["LD_LIBRARY_PATH"] = join(fs_path, "lib/misc/lib")
            environment["DYLD_LIBRARY_PATH"] = join(fs_path, "lib/misc/lib")

        if isdir(join(fs_path, "lib/gcc/lib")):
            environment["DYLD_LIBRARY_PATH"] = join(fs_path, "lib/gcc/lib")

    # Popen is needed, run(which is supposed to be newer)
    # somehow doesn't seem to support live-stream via PIPE?!
    process = subprocess.Popen(
        command,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )

    # write subprocess-output to main-tread streams
    while process.poll() is None:
        stdout_line = process.stdout.readline()
        if stdout_line is not None:
            sys.stdout.write(stdout_line)


def apply_watershed(fsmri):
    print(
        "Running Watershed algorithm for: "
        + fsmri.name
        + ". Output is written to the bem folder "
        + "of the subject's FreeSurfer folder.\n"
        + "Bash output follows below.\n\n"
    )

    # watershed command
    command = ["mne", "watershed_bem", "--subject", fsmri.name, "--overwrite"]

    run_freesurfer_subprocess(
        command, fsmri.subjects_dir, fsmri.fs_path, fsmri.mne_path
    )

    if iswin:
        # Copy Watershed-Surfaces because the Links don't work
        # under Windows when made in WSL
        surfaces = [
            (f"{fsmri.name}_inner_skull_surface", "inner_skull.surf"),
            (f"{fsmri.name}_outer_skin_surface", "outer_skin.surf"),
            (f"{fsmri.name}_outer_skull_surface", "outer_skull.surf"),
            (f"{fsmri.name}_brain_surface", "brain.surf"),
        ]
        bem_dir = join(fsmri.subjects_dir, fsmri.name, "bem")
        watershed_dir = join(bem_dir, "watershed")
        for src, dst in surfaces:
            # Remove faulty link
            os.remove(join(bem_dir, dst))
            # Copy files
            source = join(watershed_dir, src)
            destination = join(fsmri.subjects_dir, fsmri.name, "bem", dst)
            shutil.copy2(source, destination)

            print(f"{dst} was created")


def make_dense_scalp_surfaces(fsmri):
    print(
        "Making dense scalp surfacing easing co-registration for "
        + "subject: "
        + fsmri.name
        + ". Output is written to the bem folder"
        + " of the subject's FreeSurfer folder.\n"
        + "Bash output follows below.\n\n"
    )

    command = [
        "mne",
        "make_scalp_surfaces",
        "--overwrite",
        "--subject",
        fsmri.name,
        "--force",
    ]

    run_freesurfer_subprocess(
        command, fsmri.subjects_dir, fsmri.fs_path, fsmri.mne_path
    )


# ==============================================================================
# MNE SOURCE RECONSTRUCTIONS
# ==============================================================================


def setup_src(fsmri, src_spacing, surface, n_jobs):
    src = mne.setup_source_space(
        fsmri.name,
        spacing=src_spacing,
        surface=surface,
        subjects_dir=fsmri.subjects_dir,
        add_dist=False,
        n_jobs=n_jobs,
    )
    fsmri.save_source_space(src)


def setup_vol_src(fsmri, vol_src_spacing):
    bem = fsmri.load_bem_solution()
    vol_src = mne.setup_volume_source_space(
        fsmri.name, pos=vol_src_spacing, bem=bem, subjects_dir=fsmri.subjects_dir
    )
    fsmri.save_volume_source_space(vol_src)


def compute_src_distances(fsmri, n_jobs):
    src = fsmri.load_source_space()
    src_computed = mne.add_source_space_distances(src, n_jobs=n_jobs)
    fsmri.save_source_space(src_computed)


def prepare_bem(fsmri, bem_spacing, bem_conductivity):
    bem_model = mne.make_bem_model(
        fsmri.name,
        subjects_dir=fsmri.subjects_dir,
        ico=bem_spacing,
        conductivity=bem_conductivity,
    )
    fsmri.save_bem_model(bem_model)

    bem_solution = mne.make_bem_solution(bem_model)
    fsmri.save_bem_solution(bem_solution)


def morph_fsmri(meeg, morph_to):
    if meeg.fsmri.name != morph_to:
        forward = meeg.load_forward()
        fsmri_to = FSMRI(morph_to, meeg.ct)
        morph = mne.compute_source_morph(
            forward["src"],
            subject_from=meeg.fsmri.name,
            subject_to=morph_to,
            subjects_dir=meeg.subjects_dir,
            src_to=fsmri_to.load_source_space(),
        )
        meeg.save_source_morph(morph)
    else:
        logging.info(
            f"There is no need to morph the source-space for {meeg.name}, "
            f'because the morph-destination "{morph_to}" '
            f"is the same as the associated FSMRI."
        )


def morph_labels_from_fsaverage(fsmri):
    parcellations = ["aparc_sub", "HCPMMP1_combined", "HCPMMP1"]
    if not isfile(
        join(fsmri.subjects_dir, "fsaverage/label", "lh." + parcellations[0] + ".annot")
    ):
        mne.datasets.fetch_hcp_mmp_parcellation(
            subjects_dir=fsmri.subjects_dir, verbose=True
        )

        mne.datasets.fetch_aparc_sub_parcellation(
            subjects_dir=fsmri.subjects_dir, verbose=True
        )
    else:
        print("You've already downloaded the parcellations, splendid!")

    if not isfile(
        join(
            fsmri.subjects_dir, fsmri.name, "label", "lh." + parcellations[0] + ".annot"
        )
    ):
        for pc in parcellations:
            labels = mne.read_labels_from_annot("fsaverage", pc, hemi="both")

            m_labels = mne.morph_labels(
                labels, fsmri.name, "fsaverage", fsmri.subjects_dir, surf_name="pial"
            )

            mne.write_labels_to_annot(
                m_labels,
                subject=fsmri.name,
                parc=pc,
                subjects_dir=fsmri.subjects_dir,
                overwrite=True,
            )

    else:
        print(f"{parcellations} already exist")


def create_forward_solution(meeg, n_jobs, ch_types):
    info = meeg.load_info()
    trans = meeg.load_transformation()
    bem = meeg.fsmri.load_bem_solution()
    src = meeg.fsmri.load_source_space()

    if "eeg" in ch_types:
        eeg = True
    else:
        eeg = False

    forward = mne.make_forward_solution(info, trans, src, bem, eeg=eeg, n_jobs=n_jobs)

    meeg.save_forward(forward)


def estimate_noise_covariance(
    meeg, baseline, n_jobs, noise_cov_mode, noise_cov_method, **kwargs
):
    # ToDo: method='factor_analysis' can only be used with rank='full'
    if noise_cov_mode == "epochs" or meeg.erm is None:
        print("Noise Covariance on epochs-Baseline")
        epochs = meeg.load_epochs()

        tmin, tmax = baseline
        kwargs = check_kwargs(kwargs, mne.compute_covariance)
        noise_covariance = mne.compute_covariance(
            epochs,
            tmin=tmin,
            tmax=tmax,
            method=noise_cov_method,
            n_jobs=n_jobs,
            **kwargs,
        )
        meeg.save_noise_covariance(noise_covariance)

    else:
        print("Noise Covariance on Empty-Room-Data")
        erm_filtered = meeg.load_erm_processed()
        # Add bad channels to erm-recording
        erm_filtered.info["bads"] = meeg.bad_channels

        kwargs = check_kwargs(kwargs, mne.compute_raw_covariance)
        noise_covariance = mne.compute_raw_covariance(
            erm_filtered, n_jobs=n_jobs, method=noise_cov_method, **kwargs
        )
        meeg.save_noise_covariance(noise_covariance)


def create_inverse_operator(meeg):
    info = meeg.load_info()
    noise_covariance = meeg.load_noise_covariance()
    forward = meeg.load_forward()

    inverse_operator = mne.minimum_norm.make_inverse_operator(
        info, forward, noise_covariance
    )
    meeg.save_inverse_operator(inverse_operator)


def source_estimate(meeg, inverse_method, pick_ori, lambda2):
    inverse_operator = meeg.load_inverse_operator()
    evokeds = meeg.load_evokeds()

    stcs = {}
    for evoked in [ev for ev in evokeds if ev.comment in meeg.sel_trials]:
        stc = mne.minimum_norm.apply_inverse(
            evoked, inverse_operator, lambda2, method=inverse_method, pick_ori=pick_ori
        )
        stcs.update({evoked.comment: stc})

    meeg.save_source_estimates(stcs)


def label_time_course(meeg, target_labels, target_parcellation, extract_mode):
    stcs = meeg.load_source_estimates()
    src = meeg.fsmri.load_source_space()
    labels = meeg.fsmri.get_labels(target_labels, target_parcellation)

    ltc_dict = {}

    for trial in stcs:
        ltc_dict[trial] = {}
        times = stcs[trial].times
        for label in labels:
            ltc = stcs[trial].extract_label_time_course(label, src, mode=extract_mode)[
                0
            ]
            ltc_dict[trial][label.name] = np.vstack((ltc, times))

    meeg.save_ltc(ltc_dict)


# Todo: Make mixed-norm more customizable


def mixed_norm_estimate(meeg, pick_ori, inverse_method):
    evokeds = meeg.load_evokeds()
    forward = meeg.load_forward()
    noise_cov = meeg.load_noise_covariance()
    inv_op = meeg.load_inverse_operator()
    if inverse_method == "dSPM":
        print("dSPM-Inverse-Solution existent, loading...")
        stcs = meeg.load_source_estimates()
    else:
        print("No dSPM-Inverse-Solution available, calculating...")
        stcs = dict()
        snr = 3.0
        lambda2 = 1.0 / snr**2
        for evoked in evokeds:
            trial = evoked.comment
            stcs[trial] = mne.minimum_norm.apply_inverse(
                evoked, inv_op, lambda2, method="dSPM"
            )

    mixn_dips = {}
    mixn_stcs = {}

    for evoked in [ev for ev in evokeds if ev.comment in meeg.sel_trials]:
        alpha = 30  # regularization parameter between 0 and 100 (100 is high)
        n_mxne_iter = 10  # if > 1 use L0.5/L2 reweighted mixed norm solver
        # if n_mxne_iter > 1 dSPM weighting can be avoided.
        trial = evoked.comment
        mixn_dipoles, dip_residual = mne.inverse_sparse.mixed_norm(
            evoked,
            forward,
            noise_cov,
            alpha,
            maxit=3000,
            tol=1e-4,
            active_set_size=10,
            debias=True,
            weights=stcs[trial],
            n_mxne_iter=n_mxne_iter,
            return_residual=True,
            return_as_dipoles=True,
        )
        mixn_dips[trial] = mixn_dipoles

        mixn_stc, residual = mne.inverse_sparse.mixed_norm(
            evoked,
            forward,
            noise_cov,
            alpha,
            maxit=3000,
            tol=1e-4,
            active_set_size=10,
            debias=True,
            weights=stcs[trial],
            n_mxne_iter=n_mxne_iter,
            return_residual=True,
            return_as_dipoles=False,
            pick_ori=pick_ori,
        )
        mixn_stcs[evoked.comment] = mixn_stc

    meeg.save_mixn_dipoles(mixn_dips)
    meeg.save_mixn_source_estimates(mixn_stcs)


# Todo: Separate Plot-Functions
#  (better responsivness of GUI during fit, when running in QThread)


def ecd_fit(meeg, ecd_times, ecd_positions, ecd_orientations, t_epoch):
    try:
        ecd_time = ecd_times[meeg.name]
    except KeyError:
        ecd_time = {"Dip1": (0, t_epoch[1])}
        print(
            f"No Dipole times assigned for {meeg.name},"
            f" Dipole-Times: 0-{t_epoch[1]}"
        )

    evokeds = meeg.load_evokeds()
    noise_covariance = meeg.load_noise_covariance()
    bem = meeg.fsmri.load_bem_solution()
    trans = meeg.load_transformation()

    ecd_dips = {}

    for evoked in evokeds:
        trial = evoked.comment
        ecd_dips[trial] = {}
        for dip in ecd_time:
            tmin, tmax = ecd_time[dip]
            copy_evoked = evoked.copy().crop(tmin, tmax)

            try:
                ecd_position = ecd_positions[meeg.name][dip]
                ecd_orientation = ecd_orientations[meeg.name][dip]
            except KeyError:
                ecd_position = None
                ecd_orientation = None
                print(
                    f"No Position&Orientation for Dipole for {meeg.name}"
                    f" assigned, sequential fitting and free orientation "
                    "used."
                )

            if ecd_position:
                dipole, residual = mne.fit_dipole(
                    copy_evoked,
                    noise_covariance,
                    bem,
                    trans=trans,
                    min_dist=3.0,
                    n_jobs=4,
                    pos=ecd_position,
                    ori=ecd_orientation,
                )
            else:
                dipole, residual = mne.fit_dipole(
                    copy_evoked,
                    noise_covariance,
                    bem,
                    trans=trans,
                    min_dist=3.0,
                    n_jobs=4,
                )

            ecd_dips[trial][dip] = dipole

    meeg.save_ecd(ecd_dips)


def apply_morph(meeg, morph_to):
    if meeg.fsmri.name != morph_to:
        stcs = meeg.load_source_estimates()
        morph = meeg.load_source_morph()

        morphed_stcs = {}
        for trial in stcs:
            morphed_stcs[trial] = morph.apply(stcs[trial])
        meeg.save_morphed_source_estimates(morphed_stcs)
    else:
        logging.info(
            f"{meeg.name} is already in source-space of {morph_to} "
            f"and won't be morphed"
        )


def src_connectivity(
    meeg,
    target_labels,
    target_parcellation,
    inverse_method,
    lambda2,
    con_methods,
    con_frequencies,
    con_time_window,
    n_jobs,
):
    info = meeg.load_info()
    all_epochs = meeg.load_epochs()
    inverse_operator = meeg.load_inverse_operator()
    src = inverse_operator["src"]
    labels = meeg.fsmri.get_labels(target_labels, target_parcellation)

    if len(labels) == 0:
        raise RuntimeError(
            "No labels found, check your target_labels and target_parcellation"
        )
    if len(meeg.sel_trials) == 0:
        raise RuntimeError(
            "No trials selected, check your Selected IDs in Preparation/"
        )

    con_dict = {}

    for trial in meeg.sel_trials:
        con_dict[trial] = {}
        epochs = all_epochs[trial]

        # Crop if necessary
        if con_time_window is not None:
            epochs = epochs.copy().crop(
                tmin=con_time_window[0], tmax=con_time_window[1]
            )

        # Compute inverse solution and for each epoch.
        # By using "return_generator=True" stcs will be a generator object
        # instead of a list.
        stcs = mne.minimum_norm.apply_inverse_epochs(
            epochs,
            inverse_operator,
            lambda2,
            inverse_method,
            pick_ori="normal",
            return_generator=True,
        )

        label_ts = mne.extract_label_time_course(
            stcs, labels, src, mode="mean_flip", return_generator=True
        )

        sfreq = info["sfreq"]  # the sampling frequency
        con = mne_connectivity.spectral_connectivity_epochs(
            label_ts,
            method=con_methods,
            mode="multitaper",
            sfreq=sfreq,
            fmin=con_frequencies[0],
            fmax=con_frequencies[1],
            faverage=True,
            mt_adaptive=True,
            n_jobs=n_jobs,
        )

        if not isinstance(con, list):
            con = [con]

        # con is a 3D array, get the connectivity for the first (and only)
        # freq. band for each con_method
        for method, c in zip(con_methods, con):
            con_dict[trial][method] = c

    # Add target_labels for later identification
    con_dict["__info__"] = {
        "labels": target_labels,
        "parcellation": target_parcellation,
        "frequencies": con_frequencies,
    }

    meeg.save_connectivity(con_dict)


def grand_avg_morphed(group, morph_to):
    # for less memory only import data from stcs and add it to one
    # stc in the end!!!
    n_chunks = 8
    # divide in chunks to save memory
    fusion_dict = {}
    for i in range(0, len(group.group_list), n_chunks):
        sub_trial_dict = {}
        ga_chunk = group.group_list[i : i + n_chunks]
        print(ga_chunk)
        for name in ga_chunk:
            meeg = MEEG(name, group.ct)
            print(f"Add {name} to grand_average")
            if morph_to == meeg.fsmri.name:
                stcs = meeg.load_source_estimates()
            else:
                stcs = meeg.load_morphed_source_estimates()

            for trial in stcs:
                if trial in sub_trial_dict:
                    sub_trial_dict[trial].append(stcs[trial])
                else:
                    sub_trial_dict.update({trial: [stcs[trial]]})

        # Average chunks
        for trial in sub_trial_dict:
            if len(sub_trial_dict[trial]) != 0:
                print(f"grand_average for {trial}-chunk {i}-{i + n_chunks}")
                sub_trial_average = sub_trial_dict[trial][0].copy()
                n_subjects = len(sub_trial_dict[trial])

                for trial_index in range(1, n_subjects):
                    sub_trial_average.data += sub_trial_dict[trial][trial_index].data

                sub_trial_average.data /= n_subjects
                sub_trial_average.comment = trial
                if trial in fusion_dict:
                    fusion_dict[trial].append(sub_trial_average)
                else:
                    fusion_dict.update({trial: [sub_trial_average]})

    ga_stcs = {}
    for trial in fusion_dict:
        if len(fusion_dict[trial]) != 0:
            print(f"grand_average for {group.name}-{trial}")
            trial_average = fusion_dict[trial][0].copy()
            n_subjects = len(fusion_dict[trial])

            for trial_index in range(1, n_subjects):
                trial_average.data += fusion_dict[trial][trial_index].data

            trial_average.data /= n_subjects
            trial_average.comment = trial

            ga_stcs[trial] = trial_average

    group.save_ga_stc(ga_stcs)


def grand_avg_ltc(group):
    ltc_average_dict = {}
    times = None
    for name in group.group_list:
        meeg = MEEG(name, group.ct)
        print(f"Add {name} to grand_average")
        ltc_dict = meeg.load_ltc()
        for trial in ltc_dict:
            if trial not in ltc_average_dict:
                ltc_average_dict[trial] = {}
            for label in ltc_dict[trial]:
                # First row of array is label-time-course-data,
                # second row is time-array
                if label in ltc_average_dict[trial]:
                    ltc_average_dict[trial][label].append(ltc_dict[trial][label][0])
                else:
                    ltc_average_dict[trial][label] = [ltc_dict[trial][label][0]]
                # Should be the same for each trial and label
                times = ltc_dict[trial][label][1]

    ga_ltc = {}
    for trial in ltc_average_dict:
        ga_ltc[trial] = {}
        for label in ltc_average_dict[trial]:
            if len(ltc_average_dict[trial][label]) != 0:
                print(f"grand_average for {trial}-{label}")
                ltc_list = ltc_average_dict[trial][label]
                # Take the absolute values
                ltc_list = [abs(it) for it in ltc_list]
                n_subjects = len(ltc_list)
                average = ltc_list[0]
                for idx in range(1, n_subjects):
                    average += ltc_list[idx]

                average /= n_subjects

                ga_ltc[trial][label] = np.vstack((average, times))

    group.save_ga_ltc(ga_ltc)


def grand_avg_connect(group):
    # Prepare the Average-Dict
    con_average_dict = {}
    for name in group.group_list:
        meeg = MEEG(name, group.ct)
        print(f"Add {name} to grand_average")
        con_dict = meeg.load_connectivity()
        con_info = con_dict.pop("__info__")
        for trial in con_dict:
            if trial not in con_average_dict:
                con_average_dict[trial] = {}
            for con_method in con_dict[trial]:
                if con_method in con_average_dict[trial]:
                    con_average_dict[trial][con_method].append(
                        con_dict[trial][con_method].get_data(output="dense")[:, :, 0]
                    )
                else:
                    con_average_dict[trial][con_method] = [con_dict[trial][con_method]]

    ga_con = {"__info__": con_info}
    for trial in con_average_dict:
        ga_con[trial] = {}
        for con_method in con_average_dict[trial]:
            if len(con_average_dict[trial][con_method]) != 0:
                print(f"grand_average for {trial}-{con_method}")
                con_list = con_average_dict[trial][con_method]
                n_subjects = len(con_list)
                average = con_list[0]
                for idx in range(1, n_subjects):
                    average += con_list[idx]

                average /= n_subjects

                ga_con[trial][con_method] = average

    group.save_ga_con(ga_con)


def print_info(meeg):
    print(meeg.load_info())
    for n in range(20):
        print(f"\r{n}", end="")
        time.sleep(0.1)
    raise RuntimeError("Test")
