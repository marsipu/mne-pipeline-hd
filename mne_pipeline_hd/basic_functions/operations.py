# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
Copyright © 2011-2019, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
from __future__ import print_function

import os
import shutil
import subprocess
import sys
from functools import reduce
from itertools import combinations
from os import environ, makedirs
from os.path import exists, isdir, isfile, join

import autoreject as ar
import mne
import numpy as np

from mne_pipeline_hd.pipeline_functions.loading import MEEG
from ..pipeline_functions import ismac, iswin, pipeline_utils as ut
from ..pipeline_functions.pipeline_utils import compare_filep


# Todo: Change normal comments to docstrings

# ==============================================================================
# PREPROCESSING AND GETTING TO EVOKED AND TFR
# ==============================================================================

def filter_raw(meeg, highpass, lowpass, n_jobs, enable_cuda, erm_t_limit):
    results = compare_filep(meeg, meeg.raw_filtered_path, ['highpass', 'lowpass'])
    if results['highpass'] != 'equal' or results['lowpass'] != 'equal':
        # Get raw from Subject-class, load as copy to avoid changing attribute value inplace
        raw = meeg.load_raw().copy()
        if enable_cuda:  # use cuda for filtering
            n_jobs = 'cuda'
        raw.filter(highpass, lowpass, n_jobs=n_jobs)

        # Save some data in the info-dictionary and finally save it
        raw.info['description'] = meeg.name
        raw.info['bads'] = meeg.bad_channels

        meeg.save_filtered(raw)
    else:
        print(f'{meeg.name} already filtered with highpass={highpass} and lowpass={lowpass}')

    # Filter Empty-Room-Data too
    if meeg.erm != 'None':
        erm_results = compare_filep(meeg, meeg.erm_filtered_path, ['highpass', 'lowpass'])
        if erm_results['highpass'] != 'equal' or erm_results['lowpass'] != 'equal':
            raw = meeg.load_raw()
            erm_raw = meeg.load_erm().copy()

            # Due to channel-deletion sometimes in HPI-Fitting-Process
            ch_list = set(erm_raw.info['ch_names']) & set(raw.info['ch_names'])
            erm_raw.pick_channels(ch_list)
            erm_raw.pick_types(meg=True, exclude=meeg.bad_channels)
            erm_raw.filter(highpass, lowpass)

            erm_length = erm_raw.n_times / erm_raw.info['sfreq']  # in s

            if erm_length > erm_t_limit:
                diff = erm_length - erm_t_limit
                tmin = diff / 2
                tmax = erm_length - diff / 2
                erm_raw.crop(tmin=tmin, tmax=tmax)

            meeg.save_erm_filtered(erm_raw)
            print('ERM-Data filtered and saved')
        else:
            print(f'{meeg.erm} already filtered with highpass={highpass} and lowpass={lowpass}')

    else:
        print('no erm_file assigned')


def find_events(meeg, stim_channels, min_duration, shortest_event, adjust_timeline_by_msec):
    raw = meeg.load_raw()

    events = mne.find_events(raw, min_duration=min_duration, shortest_event=shortest_event,
                             stim_channel=stim_channels)

    # apply latency correction
    events[:, 0] = [ts + np.round(adjust_timeline_by_msec * 10 ** -3 *
                                  raw.info['sfreq']) for ts in events[:, 0]]

    ids = np.unique(events[:, 2])
    print('unique ID\'s found: ', ids)

    if np.size(events) > 0:
        meeg.save_events(events)
    else:
        print('No events found')


def find_6ch_binary_events(meeg, min_duration, shortest_event, adjust_timeline_by_msec):
    raw = meeg.load_raw()

    # Binary Coding of 6 Stim Channels in Biomagenetism Lab Heidelberg
    # prepare arrays
    events = np.ndarray(shape=(0, 3), dtype=np.int32)
    evs = list()
    evs_tol = list()

    # Find events for each stim channel, append sample values to list
    evs.append(mne.find_events(raw, min_duration=min_duration, shortest_event=shortest_event,
                               stim_channel=['STI 001'])[:, 0])
    evs.append(mne.find_events(raw, min_duration=min_duration, shortest_event=shortest_event,
                               stim_channel=['STI 002'])[:, 0])
    evs.append(mne.find_events(raw, min_duration=min_duration, shortest_event=shortest_event,
                               stim_channel=['STI 003'])[:, 0])
    evs.append(mne.find_events(raw, min_duration=min_duration, shortest_event=shortest_event,
                               stim_channel=['STI 004'])[:, 0])
    evs.append(mne.find_events(raw, min_duration=min_duration, shortest_event=shortest_event,
                               stim_channel=['STI 005'])[:, 0])
    evs.append(mne.find_events(raw, min_duration=min_duration, shortest_event=shortest_event,
                               stim_channel=['STI 006'])[:, 0])

    for i in evs:

        # delete events in each channel, which are too close too each other (1ms)
        too_close = np.where(np.diff(i) <= 1)
        if np.size(too_close) >= 1:
            print(f'Two close events (1ms) at samples {i[too_close] + raw.first_samp}, first deleted')
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
    equals = reduce(np.intersect1d, (evs_tol[0], evs_tol[1], evs_tol[2],
                                     evs_tol[3], evs_tol[4], evs_tol[5]))
    # elimnate duplicated events
    too_close = np.where(np.diff(equals) <= 1)
    if np.size(too_close) >= 1:
        equals = np.delete(equals, too_close, 0)
        equals -= 1  # correction, because of shift with deletion

    for q in equals:
        if q not in events[:, 0] and q not in events[:, 0] + 1 and q not in events[:, 0] - 1:
            events = np.append(events, [[q, 0, 63]], axis=0)

    for a, b, c, d, e in combinations(range(6), 5):
        equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c],
                                         evs_tol[d], evs_tol[e]))
        too_close = np.where(np.diff(equals) <= 1)
        if np.size(too_close) >= 1:
            equals = np.delete(equals, too_close, 0)
            equals -= 1

        for q in equals:
            if q not in events[:, 0] and q not in events[:, 0] + 1 and q not in events[:, 0] - 1:
                events = np.append(events, [[q, 0, int(2 ** a + 2 ** b + 2 ** c + 2 ** d + 2 ** e)]], axis=0)

    for a, b, c, d in combinations(range(6), 4):
        equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c], evs_tol[d]))
        too_close = np.where(np.diff(equals) <= 1)
        if np.size(too_close) >= 1:
            equals = np.delete(equals, too_close, 0)
            equals -= 1

        for q in equals:
            if q not in events[:, 0] and q not in events[:, 0] + 1 and q not in events[:, 0] - 1:
                events = np.append(events, [[q, 0, int(2 ** a + 2 ** b + 2 ** c + 2 ** d)]], axis=0)

    for a, b, c in combinations(range(6), 3):
        equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c]))
        too_close = np.where(np.diff(equals) <= 1)
        if np.size(too_close) >= 1:
            equals = np.delete(equals, too_close, 0)
            equals -= 1

        for q in equals:
            if q not in events[:, 0] and q not in events[:, 0] + 1 and q not in events[:, 0] - 1:
                events = np.append(events, [[q, 0, int(2 ** a + 2 ** b + 2 ** c)]], axis=0)

    for a, b in combinations(range(6), 2):
        equals = np.intersect1d(evs_tol[a], evs_tol[b])
        too_close = np.where(np.diff(equals) <= 1)
        if np.size(too_close) >= 1:
            equals = np.delete(equals, too_close, 0)
            equals -= 1

        for q in equals:
            if q not in events[:, 0] and q not in events[:, 0] + 1 and q not in events[:, 0] - 1:
                events = np.append(events, [[q, 0, int(2 ** a + 2 ** b)]], axis=0)

    # Get single-channel events
    for i in range(6):
        for e in evs[i]:
            if e not in events[:, 0] and e not in events[:, 0] + 1 and e not in events[:, 0] - 1:
                events = np.append(events, [[e, 0, 2 ** i]], axis=0)

    # sort only along samples(column 0)
    events = events[events[:, 0].argsort()]

    # apply latency correction
    events[:, 0] = [ts + np.round(adjust_timeline_by_msec * 10 ** -3 *
                                  raw.info['sfreq']) for ts in events[:, 0]]

    ids = np.unique(events[:, 2])
    print('unique ID\'s found: ', ids)

    if np.size(events) > 0:
        meeg.save_events(events)
    else:
        print('No events found')


def epoch_raw(meeg, ch_types, t_epoch, baseline, reject, flat, autoreject_interpolation, consensus_percs,
              n_interpolates, autoreject_threshold, overwrite_ar, decim, n_jobs):
    raw = meeg.load_filtered()
    events = meeg.load_events()

    raw_picked = raw.copy().pick(ch_types, exclude=meeg.bad_channels)

    epochs = mne.Epochs(raw_picked, events, meeg.event_id, t_epoch[0], t_epoch[1], baseline,
                        preload=True, proj=False, reject=None,
                        decim=decim, on_missing='ignore', reject_by_annotation=True)

    if autoreject_interpolation:
        ar_object = ar.AutoReject(n_interpolates, consensus_percs, random_state=8,
                                  n_jobs=n_jobs)
        epochs, reject_log = ar_object.fit_transform(epochs, return_log=True)
        meeg.save_reject_log(reject_log)

    elif autoreject_threshold:
        reject = ut.autoreject_handler(meeg.name, epochs, meeg.p["highpass"], meeg.p["lowpass"],
                                       meeg.pr.pscripts_path, overwrite_ar=overwrite_ar)
        print(f'Autoreject Rejection-Threshold: {reject}')
        epochs.drop_bad(reject=reject, flat=flat)
    else:
        print(f'Chosen Rejection-Threshold: {reject}')
        epochs.drop_bad(reject=reject, flat=flat)

    meeg.save_epochs(epochs)


def run_ica_new(meeg, ica_method, ica_fitto, n_components, max_pca_components, n_pca_components,
                ica_noise_cov, **kwargs):
    if ica_fitto == 'Raw':
        data = meeg.load_filtered()
    elif ica_fitto == 'Epochs':
        data = meeg.load_epochs()
    else:
        data = meeg.load_evokeds()

    if data.info['highpass'] < 1:
        filt_data = data.copy().filter(1, None)
    else:
        filt_data = data

    if ica_noise_cov:
        noise_cov = meeg.load_noise_covariance()
    else:
        noise_cov = None

    ica = mne.preprocessing.ICA(n_components=n_components, max_pca_components=max_pca_components,
                                n_pca_components=n_pca_components, noise_cov=noise_cov, random_state=8,
                                method=ica_method, **kwargs)

    ica.fit(filt_data)


# TODO: Organize run_ica properly
# Todo: Choices for: Fit(Raw, Epochs, Evokeds), Apply (Raw, Epochs, Evokeds)

def run_ica(meeg, eog_channel, ecg_channel, reject, flat, autoreject_interpolation,
            autoreject_threshold, save_plots, figures_path, pscripts_path):
    info = meeg.load_info()

    ica_dict = ut.dict_filehandler(meeg.name, f'ica_components_{meeg.p_preset}',
                                   pscripts_path,
                                   onlyread=True)

    raw = meeg.load_filtered()
    if raw.info['highpass'] < 1:
        raw.filter(l_freq=1., h_freq=None)
    epochs = meeg.load_epochs()
    picks = mne.pick_types(raw.info, meg=True, eeg=True, eog=False,
                           stim=False, exclude=meeg.bad_channels)

    if not isdir(join(figures_path, 'ica')):
        makedirs(join(figures_path, 'ica'))

    # Calculate ICA
    ica = mne.preprocessing.ICA(n_components=25, method='fastica', random_state=8)

    if autoreject_interpolation:
        # Avoid calculation of rejection-threshold again on already cleaned epochs, therefore creating new epochs
        simulated_events = mne.make_fixed_length_events(raw, duration=5)
        simulated_epochs = mne.Epochs(raw, simulated_events, baseline=None, picks=picks, tmin=0, tmax=2)
        reject = ar.get_rejection_threshold(simulated_epochs)
        print(f'Autoreject Rejection-Threshold: {reject}')
    elif autoreject_threshold:
        reject = ut.autoreject_handler(meeg.name, epochs, meeg.p["highpass"], meeg.p["lowpass"], meeg.pr.pscripts_path,
                                       overwrite_ar=False, only_read=True)
        print(f'Autoreject Rejection-Threshold: {reject}')
    else:
        print(f'Chosen Rejection-Threshold: {reject}')

    ica.fit(raw, picks, reject=reject, flat=flat,
            reject_by_annotation=True)

    if meeg.name in ica_dict and ica_dict[meeg.name] != [] and ica_dict[meeg.name]:
        indices = ica_dict[meeg.name]
        ica.exclude += indices
        print(f'{indices} added to ica.exclude from ica_components.py')
        meeg.save_ica(ica)

        comp_list = []
        for c in range(ica.n_components):
            comp_list.append(c)
        fig1 = ica.plot_components(picks=comp_list, title=meeg.name, show=False)
        fig3 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=meeg.name, show=False)
        fig4 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=meeg.name, show=False)
        for trial in meeg.sel_trials:
            fig = ica.plot_overlay(epochs[trial].average(), title=meeg.name + '-' + trial, show=False)
            if not exists(join(figures_path, 'ica/evoked_overlay')):
                makedirs(join(figures_path, 'ica/evoked_overlay'))
            save_path = join(figures_path, 'ica/evoked_overlay', meeg.name + '-' + trial +
                             '_ica_ovl' + '_' + meeg.pr.p_preset + '.jpg')
            fig.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')
        if save_plots and save_plots != 'false':

            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_comp' + '_' + meeg.pr.p_preset + '.jpg')
            fig1.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_src' + '_' + meeg.pr.p_preset + '_0.jpg')
            fig3.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_src' + '_' + meeg.pr.p_preset + '_1.jpg')
            fig4.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')

    elif eog_channel in info['ch_names']:
        eeg_picks = mne.pick_types(raw.info, meg=True, eeg=True, eog=True,
                                   stim=False, exclude=meeg.bad_channels)

        eog_epochs = mne.preprocessing.create_eog_epochs(raw, picks=eeg_picks,
                                                         reject=reject, flat=flat, ch_name=eog_channel)
        if ecg_channel:
            ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, picks=eeg_picks,
                                                             reject=reject, flat=flat, ch_name=ecg_channel)
        else:
            ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, picks=eeg_picks,
                                                             reject=reject, flat=flat)

        if len(eog_epochs) != 0:
            eog_indices, eog_scores = ica.find_bads_eog(eog_epochs, ch_name=eog_channel)
            ica.exclude.extend(eog_indices)
            print('EOG-Components: ', eog_indices)
            if len(eog_indices) != 0:
                # Plot EOG-Plots
                fig3 = ica.plot_scores(eog_scores, title=meeg.name + '_eog', show=False)
                fig2 = ica.plot_properties(eog_epochs, eog_indices, psd_args={'fmax': meeg.p["lowpass"]},
                                           image_args={'sigma': 1.}, show=False)
                fig7 = ica.plot_overlay(eog_epochs.average(), exclude=eog_indices, title=meeg.name + '_eog',
                                        show=False)
                if save_plots and save_plots != 'false':
                    for f in fig2:
                        save_path = join(figures_path, 'ica', meeg.name +
                                         '_ica_prop_eog' + '_' + meeg.pr.p_preset +
                                         f'_{fig2.index(f)}.jpg')
                        f.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

                    save_path = join(figures_path, 'ica', meeg.name +
                                     '_ica_scor_eog' + '_' + meeg.pr.p_preset + '.jpg')
                    fig3.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

                    save_path = join(figures_path, 'ica', meeg.name +
                                     '_ica_ovl_eog' + '_' + meeg.pr.p_preset + '.jpg')
                    fig7.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

        if len(ecg_epochs) != 0:
            if ecg_channel:
                ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs, threshold='auto', ch_name=ecg_channel)
            else:
                ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs, threshold='auto')
            ica.exclude.extend(ecg_indices)
            print('ECG-Components: ', ecg_indices)
            print(len(ecg_indices))
            if len(ecg_indices) != 0:
                # Plot ECG-Plots
                fig4 = ica.plot_scores(ecg_scores, title=meeg.name + '_ecg', show=False)
                fig9 = ica.plot_properties(ecg_epochs, ecg_indices, psd_args={'fmax': meeg.p["lowpass"]},
                                           image_args={'sigma': 1.}, show=False)
                fig8 = ica.plot_overlay(ecg_epochs.average(), exclude=ecg_indices, title=meeg.name + '_ecg',
                                        show=False)
                if save_plots and save_plots != 'false':
                    for f in fig9:
                        save_path = join(figures_path, 'ica', meeg.name +
                                         '_ica_prop_ecg' + '_' + meeg.pr.p_preset +
                                         f'_{fig9.index(f)}.jpg')
                        f.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

                    save_path = join(figures_path, 'ica', meeg.name +
                                     '_ica_scor_ecg' + '_' + meeg.pr.p_preset + '.jpg')
                    fig4.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

                    save_path = join(figures_path, 'ica', meeg.name +
                                     '_ica_ovl_ecg' + '_' + meeg.pr.p_preset + '.jpg')
                    fig8.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

        meeg.save_ica(ica)

        # Reading and Writing ICA-Components to a .py-file
        exes = ica.exclude
        indices = []
        for i in exes:
            indices.append(int(i))

        ut.dict_filehandler(meeg.name, f'ica_components_{meeg.pr.p_preset}', pscripts_path,
                            values=indices, overwrite=True)

        # Plot ICA integrated
        comp_list = []
        for c in range(ica.n_components):
            comp_list.append(c)
        fig1 = ica.plot_components(picks=comp_list, title=meeg.name, show=False)
        fig5 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=meeg.name, show=False)
        fig6 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=meeg.name, show=False)
        fig10 = ica.plot_overlay(epochs.average(), title=meeg.name, show=False)

        if save_plots and save_plots != 'false':
            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_comp' + '_' + meeg.pr.p_preset + '.jpg')
            fig1.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')
            if not exists(join(figures_path, 'ica/evoked_overlay')):
                makedirs(join(figures_path, 'ica/evoked_overlay'))
            save_path = join(figures_path, 'ica/evoked_overlay', meeg.name +
                             '_ica_ovl' + '_' + meeg.pr.p_preset + '.jpg')
            fig10.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_src' + '_' + meeg.pr.p_preset + '_0.jpg')
            fig5.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_src' + '_' + meeg.pr.p_preset + '_1.jpg')
            fig6.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')

    # No EEG was acquired during the measurement,
    # components have to be selected manually in the ica_components.py
    else:
        print('No EEG-Channels to read EOG/EEG from')
        meg_picks = mne.pick_types(raw.info, meg=True, eeg=True, eog=False,
                                   stim=False, exclude=meeg.bad_channels)
        ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, picks=meg_picks,
                                                         reject=reject, flat=flat)

        if len(ecg_epochs) != 0:
            ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs)
            print('ECG-Components: ', ecg_indices)
            if len(ecg_indices) != 0:
                fig4 = ica.plot_scores(ecg_scores, title=meeg.name + '_ecg', show=False)
                fig5 = ica.plot_properties(ecg_epochs, ecg_indices, psd_args={'fmax': meeg.p["lowpass"]},
                                           image_args={'sigma': 1.}, show=False)
                fig6 = ica.plot_overlay(ecg_epochs.average(), exclude=ecg_indices, title=meeg.name + '_ecg',
                                        show=False)

                save_path = join(figures_path, 'ica', meeg.name +
                                 '_ica_scor_ecg' + '_' + meeg.pr.p_preset + '.jpg')
                fig4.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')
                for f in fig5:
                    save_path = join(figures_path, 'ica', meeg.name +
                                     '_ica_prop_ecg' + '_' + meeg.pr.p_preset
                                     + f'_{fig5.index(f)}.jpg')
                    f.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')
                save_path = join(figures_path, 'ica', meeg.name +
                                 '_ica_ovl_ecg' + '_' + meeg.pr.p_preset + '.jpg')
                fig6.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

        ut.dict_filehandler(meeg.name, f'ica_components_{meeg.pr.p_preset}', pscripts_path, values=[])

        meeg.save_ica(ica)
        comp_list = []
        for c in range(ica.n_components):
            comp_list.append(c)
        fig1 = ica.plot_components(picks=comp_list, title=meeg.name, show=False)
        fig2 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=meeg.name, show=False)
        fig3 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=meeg.name, show=False)

        if save_plots and save_plots != 'false':
            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_comp' + '_' + meeg.pr.p_preset + '.jpg')
            fig1.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_src' + '_' + meeg.pr.p_preset + '_0.jpg')
            fig2.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', meeg.name +
                             '_ica_src' + '_' + meeg.pr.p_preset + '_1.jpg')
            fig3.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')


def apply_ica(meeg):
    epochs = meeg.load_epochs()
    ica = meeg.load_ica()

    if len(ica.exclude) == 0:
        print('No components excluded here')

    ica_epochs = ica.apply(epochs)
    meeg.save_ica_epochs(ica_epochs)


def interpolate_bad_chs(meeg, bad_interpolation, enable_ica):
    if bad_interpolation == 'Raw':
        raw = meeg.load_raw_filtered()
        new_raw = raw.interpolate_bads(reset_bads=False)
        meeg.save_filtered(new_raw)
    elif bad_interpolation == 'Epochs':
        if enable_ica:
            epochs = meeg.load_ica_epochs()
        else:
            epochs = meeg.load_epochs()
        new_epochs = epochs.interpolate_bads(reset_bads=False)
        meeg.save_epochs(new_epochs)
    elif bad_interpolation == 'Evokeds':
        evokeds = meeg.load_evokeds()
        new_evokeds = []
        for evoked in evokeds:
            new_evokeds.append(evoked.interpolate_bdas(reset_bads=False))
        meeg.save_evokeds(new_evokeds)


def get_evokeds(meeg, enable_ica):
    if enable_ica:
        epochs = meeg.load_ica_epochs()
        print('Evokeds from ICA-Epochs')
    else:
        epochs = meeg.load_epochs()
        print('Evokeds from (normal) Epochs')
    evokeds = []
    for trial in meeg.sel_trials:
        print(f'Evoked for {trial}')
        evoked = epochs[trial].average()
        # Todo: optional if you want weights in your evoked.comment?!
        evoked.comment = trial
        evokeds.append(evoked)

    meeg.save_evokeds(evokeds)


def calculate_gfp(evoked):
    d = evoked.data
    gfp = np.sqrt((d * d).mean(axis=0))

    return gfp


def grand_avg_evokeds(group):
    trial_dict = {}
    for name in group.group_list:
        meeg = MEEG(name, group.mw)
        print(f'Add {name} to grand_average')
        evokeds = meeg.load_evokeds()
        for evoked in evokeds:
            if evoked.nave != 0:
                if evoked.comment in trial_dict:
                    trial_dict[evoked.comment].append(evoked)
                else:
                    trial_dict.update({evoked.comment: [evoked]})
            else:
                print(f'{evoked.comment} for {name} got nave=0')

    ga_evokeds = []
    for trial in trial_dict:
        if len(trial_dict[trial]) != 0:
            ga = mne.grand_average(trial_dict[trial],
                                   interpolate_bads=True,
                                   drop_bads=True)
            ga.comment = trial
            ga_evokeds.append(ga)

    group.save_ga_evokeds(ga_evokeds)


def tfr(meeg, enable_ica, tfr_freqs, overwrite_tfr,
        tfr_method, multitaper_bandwith, stockwell_width, n_jobs):
    n_cycles = [freq / 2 for freq in tfr_freqs]
    powers = []
    itcs = []

    if overwrite_tfr or not isfile(meeg.power_tfr_path) or not isfile(meeg.itc_tfr_path):
        if enable_ica:
            epochs = meeg.load_ica_epochs()
        else:
            epochs = meeg.load_epochs()

        for trial in meeg.sel_trials:
            if tfr_method == 'morlet':
                power, itc = mne.time_frequency.tfr_morlet(epochs[trial],
                                                           freqs=tfr_freqs,
                                                           n_cycles=n_cycles,
                                                           n_jobs=n_jobs)
            elif tfr_method == 'multitaper':
                power, itc = mne.time_frequency.tfr_multitaper(epochs[trial],
                                                               freqs=tfr_freqs,
                                                               n_cycles=n_cycles,
                                                               time_bandwith=multitaper_bandwith,
                                                               n_jobs=n_jobs)
            elif tfr_method == 'stockwell':
                fmin, fmax = tfr_freqs[[0, -1]]
                power, itc = mne.time_frequency.tfr_stockwell(epochs[trial],
                                                              fmin=fmin, fmax=fmax,
                                                              width=stockwell_width,
                                                              n_jobs=n_jobs)
            else:
                power, itc = [], []
                print('No appropriate tfr_method defined in pipeline')

            power.comment = trial
            itc.comment = trial

            powers.append(power)
            itcs.append(itc)

        meeg.save_power_tfr(powers)
        meeg.save_itc_tfr(itcs)


def grand_avg_tfr(group):
    trial_dict = {}
    for name in group.group_list:
        meeg = MEEG(name, group.mw)
        print(f'Add {name} to grand_average')
        powers = meeg.load_power_tfr()
        for pw in powers:
            if pw.nave != 0:
                if pw.comment in trial_dict:
                    trial_dict[pw.comment].append(pw)
                else:
                    trial_dict.update({pw.comment: [pw]})
            else:
                print(f'{pw.comment} for {name} got nave=0')

    for trial in trial_dict:
        if len(trial_dict[trial]) != 0:

            # Make sure, all have the same number of channels
            commons = set()
            for pw in trial_dict[trial]:
                if len(commons) == 0:
                    for c in pw.ch_names:
                        commons.add(c)
                commons = commons & set(pw.ch_names)
            print(f'{trial}:Reducing all n_channels to {len(commons)}')
            for idx, pw in enumerate(trial_dict[trial]):
                trial_dict[trial][idx] = pw.pick_channels(list(commons))

            ga = mne.grand_average(trial_dict[trial],
                                   interpolate_bads=True,
                                   drop_bads=True)
            ga.comment = trial

            group.save_ga_tfr(ga, trial)


# ==============================================================================
# BASH OPERATIONS
# ==============================================================================
# These functions do not work on Windows

# local function used in the bash commands below
def run_freesurfer_subprocess(command, subjects_dir, fs_path, mne_path=None):
    # Several experiments with subprocess showed, that it seems impossible to run commands like "source" from
    # a subprocess to get SetUpFreeSurfer.sh into the environment.
    # Current workaround is adding the binaries to PATH manually, after the user set the path to FREESURFER_HOME
    if fs_path is None:
        raise RuntimeError('Path to FREESURFER_HOME not set, can\'t run this function')
    environment = environ.copy()
    environment['FREESURFER_HOME'] = fs_path
    environment['SUBJECTS_DIR'] = subjects_dir
    if iswin:
        command.insert(0, 'wsl')
        if mne_path is None:
            raise RuntimeError('Path to MNE-Environment in Windows-Subsytem for Linux(WSL) not set, '
                               'can\'t run this function')

        # Add Freesurfer-Path, MNE-Path and standard Ubuntu-Paths, which get lost when sharing the Path from Windows
        # to WSL
        environment['PATH'] = f'{fs_path}/bin:{mne_path}/bin:' \
                              f'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        environment['WSLENV'] = 'PATH/u:SUBJECTS_DIR/p:FREESURFER_HOME/u'
    else:
        # Add Freesurfer to Path
        environment['PATH'] = environment['PATH'] + f':{fs_path}/bin'

    # Add Mac-specific Freesurfer-Paths (got them from FreeSurferEnv.sh in FREESURFER_HOME)
    if ismac:
        if isdir(join(fs_path, 'lib/misc/lib')):
            environment['PATH'] = environment['PATH'] + f':{fs_path}/lib/misc/bin'
            environment['MISC_LIB'] = join(fs_path, 'lib/misc/lib')
            environment['LD_LIBRARY_PATH'] = join(fs_path, 'lib/misc/lib')
            environment['DYLD_LIBRARY_PATH'] = join(fs_path, 'lib/misc/lib')

        if isdir(join(fs_path, 'lib/gcc/lib')):
            environment['DYLD_LIBRARY_PATH'] = join(fs_path, 'lib/gcc/lib')

    # Popen is needed, run(which is supposed to be newer) somehow doesn't seem to support live-stream via PIPE?!
    process = subprocess.Popen(command, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, universal_newlines=True)

    # write bash output in python console
    for line in process.stdout:
        sys.stdout.write(line)

    # Wait for subprocess to finish
    process.wait()


def apply_watershed(fsmri):
    print('Running Watershed algorithm for: ' + fsmri.name +
          ". Output is written to the bem folder " +
          "of the subject's FreeSurfer folder.\n" +
          'Bash output follows below.\n\n')

    # watershed command
    command = ['mne', 'watershed_bem',
               '--subject', fsmri.name,
               '--overwrite']

    run_freesurfer_subprocess(command, fsmri.subjects_dir, fsmri.fs_path, fsmri.mne_path)

    if iswin:
        # Copy Watershed-Surfaces because the Links don't work under Windows when made in WSL
        surfaces = [(f'{fsmri.name}_inner_skull_surface', 'inner_skull.surf'),
                    (f'{fsmri.name}_outer_skin_surface', 'outer_skin.surf'),
                    (f'{fsmri.name}_outer_skull_surface', 'outer_skull.surf'),
                    (f'{fsmri.name}_brain_surface', 'brain.surf')]

        for surface_tuple in surfaces:
            # Remove faulty link
            os.remove(join(fsmri.subjects_dir, fsmri.name, 'bem', surface_tuple[1]))
            # Copy files
            source = join(fsmri.subjects_dir, fsmri.name, 'bem', 'watershed', surface_tuple[0])
            destination = join(fsmri.subjects_dir, fsmri.name, 'bem', surface_tuple[1])
            shutil.copy2(source, destination)

            print(f'{surface_tuple[1]} was created')


def make_dense_scalp_surfaces(fsmri):
    print('Making dense scalp surfacing easing co-registration for ' +
          'subject: ' + fsmri.name +
          ". Output is written to the bem folder" +
          " of the subject's FreeSurfer folder.\n" +
          'Bash output follows below.\n\n')

    command = ['mne', 'make_scalp_surfaces',
               '--subject', fsmri.name,
               '--overwrite']

    run_freesurfer_subprocess(command, fsmri.subjects_dir, fsmri.fs_path, fsmri.mne_path)


# ==============================================================================
# MNE SOURCE RECONSTRUCTIONS
# ==============================================================================

def setup_src(fsmri, source_space_spacing, surface, n_jobs):
    src = mne.setup_source_space(fsmri.name, spacing=source_space_spacing,
                                 surface=surface, subjects_dir=fsmri.subjects_dir,
                                 add_dist=False, n_jobs=n_jobs)
    fsmri.save_source_space(src)


def setup_vol_src(fsmri, vol_source_space_spacing):
    bem = fsmri.load_bem_solution()
    vol_src = mne.setup_volume_source_space(fsmri.name, pos=vol_source_space_spacing, bem=bem,
                                            subjects_dir=fsmri.subjects_dir)
    fsmri.save_vol_source_space(vol_src)


def compute_src_distances(fsmri, n_jobs):
    src = fsmri.load_source_space()
    src_computed = mne.add_source_space_distances(src, n_jobs=n_jobs)
    fsmri.save_source_space(src_computed)


def prepare_bem(fsmri, bem_spacing):
    bem_model = mne.make_bem_model(fsmri.name, subjects_dir=fsmri.subjects_dir,
                                   ico=bem_spacing)
    fsmri.save_bem_model(bem_model)

    bem_solution = mne.make_bem_solution(bem_model)
    fsmri.save_bem_solution(bem_solution)


def morph_fsmri(fsmri, morph_to):
    src = fsmri.load_source_space()
    morph = mne.compute_source_morph(src, subject_from=fsmri.name,
                                     subject_to=morph_to, subjects_dir=fsmri.subjects_dir)
    fsmri.save_source_morph(morph)


def morph_labels_from_fsaverage(fsmri):
    parcellations = ['aparc_sub', 'HCPMMP1_combined', 'HCPMMP1']
    if not isfile(join(fsmri.subjects_dir, 'fsaverage/label',
                       'lh.' + parcellations[0] + '.annot')):
        mne.datasets.fetch_hcp_mmp_parcellation(subjects_dir=fsmri.subjects_dir,
                                                verbose=True)

        mne.datasets.fetch_aparc_sub_parcellation(subjects_dir=fsmri.subjects_dir,
                                                  verbose=True)
    else:
        print('You\'ve already downloaded the parcellations, splendid!')

    if not isfile(join(fsmri.subjects_dir, fsmri.name, 'label',
                       'lh.' + parcellations[0] + '.annot')):
        for pc in parcellations:
            labels = mne.read_labels_from_annot('fsaverage', pc, hemi='both')

            m_labels = mne.morph_labels(labels, fsmri.name, 'fsaverage', fsmri.subjects_dir,
                                        surf_name='pial')

            mne.write_labels_to_annot(m_labels, subject=fsmri.name, parc=pc,
                                      subjects_dir=fsmri.subjects_dir, overwrite=True)

    else:
        print(f'{parcellations} already exist')


def create_forward_solution(meeg, n_jobs, eeg_fwd):
    info = meeg.load_info()
    trans = meeg.load_transformation()
    bem = meeg.fsmri.load_bem_solution()
    source_space = meeg.fsmri.load_source_space()

    forward = mne.make_forward_solution(info, trans, source_space, bem,
                                        n_jobs=n_jobs, eeg=eeg_fwd)

    meeg.save_forward(forward)


def estimate_noise_covariance(meeg, baseline, n_jobs, erm_noise_cov, calm_noise_cov, enable_ica):
    if calm_noise_cov:
        print('Noise Covariance on 1-Minute-Calm')

        raw = meeg.read_filtered()
        raw.crop(tmin=5, tmax=50)
        raw.pick_types(exclude=meeg.bad_channels)

        noise_covariance = mne.compute_raw_covariance(raw, n_jobs=n_jobs,
                                                      method='empirical')
        meeg.save_noise_covariance(noise_covariance, 'calm')

    elif meeg.erm == 'None' or erm_noise_cov is False:
        print('Noise Covariance on Epochs')
        if enable_ica:
            epochs = meeg.load_ica_epochs()
        else:
            epochs = meeg.load_epochs()

        tmin, tmax = baseline
        noise_covariance = mne.compute_covariance(epochs, tmin=tmin, tmax=tmax,
                                                  method='empirical', n_jobs=n_jobs)

        meeg.save_noise_covariance(noise_covariance, 'epochs')

    else:
        print('Noise Covariance on ERM')

        erm_filtered = meeg.load_erm_filtered()
        erm_filtered.pick_types(exclude=meeg.bad_channels)

        noise_covariance = mne.compute_raw_covariance(erm_filtered, n_jobs=n_jobs,
                                                      method='empirical')
        meeg.save_noise_covariance(noise_covariance, 'erm')


def create_inverse_operator(meeg):
    info = meeg.load_info()
    noise_covariance = meeg.load_noise_covariance()
    forward = meeg.load_forward()

    inverse_operator = mne.minimum_norm.make_inverse_operator(info, forward, noise_covariance)
    meeg.save_inverse_operator(inverse_operator)


def source_estimate(meeg, inverse_method, pick_ori, lambda2):
    inverse_operator = meeg.load_inverse_operator()
    evokeds = meeg.load_evokeds()

    stcs = {}
    for evoked in [ev for ev in evokeds if ev.comment in meeg.sel_trials]:
        stc = mne.minimum_norm.apply_inverse(evoked, inverse_operator, lambda2, method=inverse_method,
                                             pick_ori=pick_ori)
        stcs.update({evoked.comment: stc})

    meeg.save_source_estimates(stcs)


def label_time_course(meeg, target_labels, parcellation, extract_mode):
    stcs = meeg.load_source_estimates()
    src = meeg.fsmri.load_source_space()

    labels = mne.read_labels_from_annot(meeg.fsmri.name,
                                        subjects_dir=meeg.subjects_dir,
                                        parc=parcellation)
    chosen_labels = [label for label in labels if label.name in target_labels]

    ltc_dict = {}

    for trial in stcs:
        ltc_dict[trial] = {}
        times = stcs[trial].times
        for label in chosen_labels:
            ltc = stcs[trial].extract_label_time_course(label, src, mode=extract_mode)[0]
            ltc_dict[trial][label.name] = np.vstack((ltc, times))

    meeg.save_ltc(ltc_dict)


# Todo: Make mixed-norm more customizable

def mixed_norm_estimate(meeg, pick_ori, inverse_method):
    evokeds = meeg.load_evokeds()
    forward = meeg.load_forward()
    noise_cov = meeg.load_noise_covariance()
    inv_op = meeg.load_inverse_operator()
    if inverse_method == 'dSPM':
        print('dSPM-Inverse-Solution existent, loading...')
        stcs = meeg.load_source_estimates()
    else:
        print('No dSPM-Inverse-Solution available, calculating...')
        stcs = dict()
        snr = 3.0
        lambda2 = 1.0 / snr ** 2
        for evoked in evokeds:
            trial = evoked.comment
            stcs[trial] = mne.minimum_norm.apply_inverse(evoked, inv_op, lambda2, method='dSPM')

    mixn_dips = {}
    mixn_stcs = {}

    for evoked in [ev for ev in evokeds if ev.comment in meeg.sel_trials]:
        alpha = 30  # regularization parameter between 0 and 100 (100 is high)
        n_mxne_iter = 10  # if > 1 use L0.5/L2 reweighted mixed norm solver
        # if n_mxne_iter > 1 dSPM weighting can be avoided.
        trial = evoked.comment
        mixn_dipoles, dip_residual = mne.inverse_sparse.mixed_norm(evoked, forward, noise_cov, alpha,
                                                                   maxit=3000, tol=1e-4, active_set_size=10,
                                                                   debias=True, weights=stcs[trial],
                                                                   n_mxne_iter=n_mxne_iter, return_residual=True,
                                                                   return_as_dipoles=True)
        mixn_dips[trial] = mixn_dipoles

        mixn_stc, residual = mne.inverse_sparse.mixed_norm(evoked, forward, noise_cov, alpha,
                                                           maxit=3000, tol=1e-4, active_set_size=10, debias=True,
                                                           weights=stcs[trial], n_mxne_iter=n_mxne_iter,
                                                           return_residual=True, return_as_dipoles=False,
                                                           pick_ori=pick_ori)
        mixn_stcs[evoked.comment] = mixn_stc

    meeg.save_mixn_dipoles(mixn_dips)
    meeg.save_mixn_source_estimates(mixn_stcs)


# Todo: Separate Plot-Functions (better responsivness of GUI during fit, when running in QThread)

def ecd_fit(meeg, ecd_times, ecd_positions, ecd_orientations, t_epoch):
    try:
        ecd_time = ecd_times[meeg.name]
    except KeyError:
        ecd_time = {'Dip1': (0, t_epoch[1])}
        print(f'No Dipole times assigned for {meeg.name}, Dipole-Times: 0-{t_epoch[1]}')

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
                print(f'No Position&Orientation for Dipole for {meeg.name} assigned, '
                      f'sequential fitting and free orientation used')

            if ecd_position:
                dipole, residual = mne.fit_dipole(copy_evoked, noise_covariance, bem, trans=trans,
                                                  min_dist=3.0, n_jobs=4, pos=ecd_position, ori=ecd_orientation)
            else:
                dipole, residual = mne.fit_dipole(copy_evoked, noise_covariance, bem, trans=trans, min_dist=3.0,
                                                  n_jobs=4)

            ecd_dips[trial][dip] = dipole

    meeg.save_ecd(ecd_dips)


def apply_morph(meeg):
    stcs = meeg.load_source_estimates()
    morph = meeg.fsmri.load_source_morph()

    morphed_stcs = {}
    for trial in stcs:
        morphed_stcs[trial] = morph.apply(stcs[trial])
    meeg.save_morphed_source_estimates(morphed_stcs)


def source_space_connectivity(meeg, parcellation, target_labels, inverse_method, lambda2, con_methods,
                              con_fmin, con_fmax, n_jobs, enable_ica):
    info = meeg.load_info()
    if enable_ica:
        all_epochs = meeg.load_ica_epochs()
    else:
        all_epochs = meeg.load_epochs()
    inverse_operator = meeg.load_inverse_operator()
    src = inverse_operator['src']

    con_dict = {}
    for trial in all_epochs.event_id:
        con_dict[trial] = {}
        epochs = all_epochs[trial]
        # Compute inverse solution and for each epoch. By using "return_generator=True"
        # stcs will be a generator object instead of a list.
        stcs = mne.minimum_norm.apply_inverse_epochs(epochs, inverse_operator, lambda2, inverse_method,
                                                     pick_ori="normal", return_generator=True)

        # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
        labels = mne.read_labels_from_annot(meeg.fsmri.name, parc=parcellation,
                                            subjects_dir=meeg.subjects_dir)

        actual_labels = [lb for lb in labels if lb.name in target_labels]

        # Average the source estimates within each label using sign-flips to reduce
        # signal cancellations, also here we return a generator

        label_ts = mne.extract_label_time_course(stcs, actual_labels,
                                                 src, mode='mean_flip',
                                                 return_generator=True)

        sfreq = info['sfreq']  # the sampling frequency
        con, freqs, times, n_epochs, n_tapers = mne.connectivity.spectral_connectivity(
                label_ts, method=con_methods, mode='multitaper', sfreq=sfreq, fmin=con_fmin,
                fmax=con_fmax, faverage=True, mt_adaptive=True, n_jobs=n_jobs)

        # con is a 3D array, get the connectivity for the first (and only) freq. band
        # for each con_method
        con_dict = dict()
        for con_method, c in zip(con_methods, con):
            con_dict[trial][con_method] = c

    meeg.save_connectivity(con_dict)


def grand_avg_morphed(group):
    # for less memory only import data from stcs and add it to one fsaverage-stc in the end!!!
    n_chunks = 8
    # divide in chunks to save memory
    fusion_dict = {}
    for i in range(0, len(group.group_list), n_chunks):
        sub_trial_dict = {}
        ga_chunk = group.group_list[i:i + n_chunks]
        print(ga_chunk)
        for name in ga_chunk:
            meeg = MEEG(name, group.mw)
            print(f'Add {name} to grand_average')
            stcs = meeg.load_morphed_source_estimates()
            for trial in stcs:
                if trial in sub_trial_dict:
                    sub_trial_dict[trial].append(stcs[trial])
                else:
                    sub_trial_dict.update({trial: [stcs[trial]]})

        # Average chunks
        for trial in sub_trial_dict:
            if len(sub_trial_dict[trial]) != 0:
                print(f'grand_average for {trial}-chunk {i}-{i + n_chunks}')
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
            print(f'grand_average for {group.name}-{trial}')
            trial_average = fusion_dict[trial][0].copy()
            n_subjects = len(fusion_dict[trial])

            for trial_index in range(1, n_subjects):
                trial_average.data += fusion_dict[trial][trial_index].data

            trial_average.data /= n_subjects
            trial_average.comment = trial

            ga_stcs[trial] = trial_average

    group.save_ga_source_estimate(ga_stcs)


def grand_avg_ltc(group):
    ltc_average_dict = {}
    times = None
    for name in group.group_list:
        meeg = MEEG(name, group.mw)
        print(f'Add {name} to grand_average')
        ltc_dict = meeg.load_ltc()
        for trial in ltc_dict:
            if trial not in ltc_average_dict:
                ltc_average_dict[trial] = {}
            for label in ltc_dict[trial]:
                # First row of array is label-time-course-data, second row is time-array
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
                print(f'grand_average for {trial}-{label}')
                ltc_list = ltc_average_dict[trial][label]
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
        meeg = MEEG(name, group.mw)
        print(f'Add {name} to grand_average')
        con_dict = meeg.load_connectivity()
        for trial in con_dict:
            if trial not in con_average_dict:
                con_average_dict[trial] = {}
            for con_method in con_dict[trial]:
                if con_method in con_average_dict[trial]:
                    con_average_dict[trial][con_method].append(con_dict[trial][con_method])
                else:
                    con_average_dict[trial][con_method] = [con_dict[trial][con_method]]

    ga_con = {}
    for trial in con_average_dict:
        ga_con[trial] = {}
        for con_method in con_average_dict[trial]:
            if len(con_average_dict[trial][con_method]) != 0:
                print(f'grand_average for {trial}-{con_method}')
                con_list = con_average_dict[trial][con_method]
                n_subjects = len(con_list)
                average = con_list[0]
                for idx in range(1, n_subjects):
                    average += con_list[idx]

                average /= n_subjects

                ga_con[trial][con_method] = average

    group.save_ga_connect(ga_con)
