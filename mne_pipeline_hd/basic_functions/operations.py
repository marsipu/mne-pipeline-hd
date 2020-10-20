# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
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

from .loading import CurrentSub
from ..pipeline_functions import ismac, iswin, pipeline_utils as ut
from ..pipeline_functions.decorators import small_func, topline


# Todo: Change normal comments to docstrings

# ==============================================================================
# PREPROCESSING AND GETTING TO EVOKED AND TFR
# ==============================================================================
@topline
def filter_raw(sub, highpass, lowpass, n_jobs, enable_cuda, erm_t_limit):
    # Prevent error for "raw might not be assigned" below
    if not isfile(sub.raw_filtered_path):
        # Get raw from Subject-class
        raw = sub.load_raw()
        if enable_cuda and enable_cuda != 'false':  # use cuda for filtering, boolean-string due to QSettings
            n_jobs = 'cuda'
        raw.filter(highpass, lowpass, n_jobs=n_jobs)

        # Save some data in the info-dictionary and finally save it
        raw.info['description'] = sub.name
        raw.info['bads'] = sub.bad_channels

        sub.save_filtered(raw)

    else:
        print(f'raw file with Highpass = {highpass} Hz and Lowpass = {lowpass} Hz already exists')

    # Filter Empty-Room-Data too
    if sub.ermsub != 'None':
        if not isfile(sub.erm_filtered_path):

            raw = sub.load_raw()
            erm_raw = sub.load_erm()

            # Due to channel-deletion sometimes in HPI-Fitting-Process
            ch_list = set(erm_raw.info['ch_names']) & set(raw.info['ch_names'])
            erm_raw.pick_channels(ch_list)
            erm_raw.pick_types(meg=True, exclude=sub.bad_channels)
            erm_raw.filter(highpass, lowpass)

            erm_length = erm_raw.n_times / erm_raw.info['sfreq']  # in s

            if erm_length > erm_t_limit:
                diff = erm_length - erm_t_limit
                tmin = diff / 2
                tmax = erm_length - diff / 2
                erm_raw.crop(tmin=tmin, tmax=tmax)

            sub.save_erm_filtered(erm_raw)
            print('ERM-Data filtered and saved')

        else:
            print(f'erm-raw file with Highpass = {highpass} Hz and Lowpass = {lowpass} Hz already exists')

    else:
        print('no erm_file assigned')


@topline
def find_events(sub, stim_channels, min_duration, shortest_event, adjust_timeline_by_msec):
    raw = sub.load_raw()

    events = mne.find_events(raw, min_duration=min_duration, shortest_event=shortest_event,
                             stim_channel=stim_channels)

    # apply latency correction
    events[:, 0] = [ts + np.round(adjust_timeline_by_msec * 10 ** -3 *
                                  raw.info['sfreq']) for ts in events[:, 0]]

    ids = np.unique(events[:, 2])
    print('unique ID\'s found: ', ids)

    if np.size(events) > 0:
        sub.save_events(events)
    else:
        print('No events found')


@topline
def find_6ch_binary_events(sub, min_duration, shortest_event, adjust_timeline_by_msec):
    raw = sub.load_raw()

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
        sub.save_events(events)
    else:
        print('No events found')


@topline
def epoch_raw(sub, ch_types, t_epoch, baseline, reject, flat, autoreject_interpolation, consensus_percs, n_interpolates,
              autoreject_threshold, overwrite_ar, decim, n_jobs):
    raw = sub.load_filtered()
    events = sub.load_events()

    raw_picked = raw.pick(ch_types, exclude=sub.bad_channels)

    epochs = mne.Epochs(raw_picked, events, sub.event_id, t_epoch[0], t_epoch[1], baseline,
                        preload=True, proj=False, reject=None,
                        decim=decim, on_missing='ignore', reject_by_annotation=True)

    if autoreject_interpolation:
        ar_object = ar.AutoReject(n_interpolates, consensus_percs, random_state=8,
                                  n_jobs=n_jobs)
        epochs, reject_log = ar_object.fit_transform(epochs, return_log=True)
        sub.save_reject_log(reject_log)

    elif autoreject_threshold:
        reject = ut.autoreject_handler(sub.name, epochs, sub.p["highpass"], sub.p["lowpass"],
                                       sub.pr.pscripts_path, overwrite_ar=overwrite_ar)
        print(f'Autoreject Rejection-Threshold: {reject}')
        epochs.drop_bad(reject=reject, flat=flat)
    else:
        print(f'Chosen Rejection-Threshold: {reject}')
        epochs.drop_bad(reject=reject, flat=flat)

    sub.save_epochs(epochs)


# TODO: Organize run_ica properly
# Todo: Choices for: Fit(Raw, Epochs, Evokeds), Apply (Raw, Epochs, Evokeds)
@topline
def run_ica(sub, eog_channel, ecg_channel, reject, flat, autoreject_interpolation,
            autoreject_threshold, save_plots, figures_path, pscripts_path):
    info = sub.load_info()

    ica_dict = ut.dict_filehandler(sub.name, f'ica_components_{sub.p_preset}',
                                   pscripts_path,
                                   onlyread=True)

    raw = sub.load_filtered()
    if raw.info['highpass'] < 1:
        raw.filter(l_freq=1., h_freq=None)
    epochs = sub.load_epochs()
    picks = mne.pick_types(raw.info, meg=True, eeg=False, eog=False,
                           stim=False, exclude=sub.bad_channels)

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
        reject = ut.autoreject_handler(sub.name, epochs, sub.p["highpass"], sub.p["lowpass"], sub.pr.pscripts_path,
                                       overwrite_ar=False, only_read=True)
        print(f'Autoreject Rejection-Threshold: {reject}')
    else:
        print(f'Chosen Rejection-Threshold: {reject}')

    ica.fit(raw, picks, reject=reject, flat=flat,
            reject_by_annotation=True)

    if sub.name in ica_dict and ica_dict[sub.name] != [] and ica_dict[sub.name]:
        indices = ica_dict[sub.name]
        ica.exclude += indices
        print(f'{indices} added to ica.exclude from ica_components.py')
        sub.save_ica(ica)

        comp_list = []
        for c in range(ica.n_components):
            comp_list.append(c)
        fig1 = ica.plot_components(picks=comp_list, title=sub.name, show=False)
        fig3 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=sub.name, show=False)
        fig4 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=sub.name, show=False)
        for trial in sub.sel_trials:
            fig = ica.plot_overlay(epochs[trial].average(), title=sub.name + '-' + trial, show=False)
            if not exists(join(figures_path, 'ica/evoked_overlay')):
                makedirs(join(figures_path, 'ica/evoked_overlay'))
            save_path = join(figures_path, 'ica/evoked_overlay', sub.name + '-' + trial +
                             '_ica_ovl' + '_' + sub.pr.p_preset + '.jpg')
            fig.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')
        if save_plots and save_plots != 'false':

            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_comp' + '_' + sub.pr.p_preset + '.jpg')
            fig1.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_src' + '_' + sub.pr.p_preset + '_0.jpg')
            fig3.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_src' + '_' + sub.pr.p_preset + '_1.jpg')
            fig4.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')

    elif eog_channel in info['ch_names']:
        eeg_picks = mne.pick_types(raw.info, meg=True, eeg=True, eog=True,
                                   stim=False, exclude=sub.bad_channels)

        eog_epochs = mne.preprocessing.create_eog_epochs(raw, picks=eeg_picks,
                                                         reject=reject, flat=flat, ch_name=eog_channel)
        ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, picks=eeg_picks,
                                                         reject=reject, flat=flat, ch_name=ecg_channel)

        if len(eog_epochs) != 0:
            eog_indices, eog_scores = ica.find_bads_eog(eog_epochs, ch_name=eog_channel)
            ica.exclude.extend(eog_indices)
            print('EOG-Components: ', eog_indices)
            if len(eog_indices) != 0:
                # Plot EOG-Plots
                fig3 = ica.plot_scores(eog_scores, title=sub.name + '_eog', show=False)
                fig2 = ica.plot_properties(eog_epochs, eog_indices, psd_args={'fmax': sub.p["lowpass"]},
                                           image_args={'sigma': 1.}, show=False)
                fig7 = ica.plot_overlay(eog_epochs.average(), exclude=eog_indices, title=sub.name + '_eog',
                                        show=False)
                if save_plots and save_plots != 'false':
                    for f in fig2:
                        save_path = join(figures_path, 'ica', sub.name +
                                         '_ica_prop_eog' + '_' + sub.pr.p_preset +
                                         f'_{fig2.index(f)}.jpg')
                        f.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

                    save_path = join(figures_path, 'ica', sub.name +
                                     '_ica_scor_eog' + '_' + sub.pr.p_preset + '.jpg')
                    fig3.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

                    save_path = join(figures_path, 'ica', sub.name +
                                     '_ica_ovl_eog' + '_' + sub.pr.p_preset + '.jpg')
                    fig7.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

        if len(ecg_epochs) != 0:
            ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs, ch_name=ecg_channel)
            ica.exclude.extend(ecg_indices)
            print('ECG-Components: ', ecg_indices)
            print(len(ecg_indices))
            if len(ecg_indices) != 0:
                # Plot ECG-Plots
                fig4 = ica.plot_scores(ecg_scores, title=sub.name + '_ecg', show=False)
                fig9 = ica.plot_properties(ecg_epochs, ecg_indices, psd_args={'fmax': sub.p["lowpass"]},
                                           image_args={'sigma': 1.}, show=False)
                fig8 = ica.plot_overlay(ecg_epochs.average(), exclude=ecg_indices, title=sub.name + '_ecg',
                                        show=False)
                if save_plots and save_plots != 'false':
                    for f in fig9:
                        save_path = join(figures_path, 'ica', sub.name +
                                         '_ica_prop_ecg' + '_' + sub.pr.p_preset +
                                         f'_{fig9.index(f)}.jpg')
                        f.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

                    save_path = join(figures_path, 'ica', sub.name +
                                     '_ica_scor_ecg' + '_' + sub.pr.p_preset + '.jpg')
                    fig4.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

                    save_path = join(figures_path, 'ica', sub.name +
                                     '_ica_ovl_ecg' + '_' + sub.pr.p_preset + '.jpg')
                    fig8.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

        sub.save_ica(ica)

        # Reading and Writing ICA-Components to a .py-file
        exes = ica.exclude
        indices = []
        for i in exes:
            indices.append(int(i))

        ut.dict_filehandler(sub.name, f'ica_components_{sub.pr.p_preset}', pscripts_path,
                            values=indices, overwrite=True)

        # Plot ICA integrated
        comp_list = []
        for c in range(ica.n_components):
            comp_list.append(c)
        fig1 = ica.plot_components(picks=comp_list, title=sub.name, show=False)
        fig5 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=sub.name, show=False)
        fig6 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=sub.name, show=False)
        fig10 = ica.plot_overlay(epochs.average(), title=sub.name, show=False)

        if save_plots and save_plots != 'false':
            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_comp' + '_' + sub.pr.p_preset + '.jpg')
            fig1.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')
            if not exists(join(figures_path, 'ica/evoked_overlay')):
                makedirs(join(figures_path, 'ica/evoked_overlay'))
            save_path = join(figures_path, 'ica/evoked_overlay', sub.name +
                             '_ica_ovl' + '_' + sub.pr.p_preset + '.jpg')
            fig10.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_src' + '_' + sub.pr.p_preset + '_0.jpg')
            fig5.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_src' + '_' + sub.pr.p_preset + '_1.jpg')
            fig6.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')

    # No EEG was acquired during the measurement,
    # components have to be selected manually in the ica_components.py
    else:
        print('No EEG-Channels to read EOG/EEG from')
        meg_picks = mne.pick_types(raw.info, meg=True, eeg=False, eog=False,
                                   stim=False, exclude=sub.bad_channels)
        ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, picks=meg_picks,
                                                         reject=reject, flat=flat)

        if len(ecg_epochs) != 0:
            ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs)
            print('ECG-Components: ', ecg_indices)
            if len(ecg_indices) != 0:
                fig4 = ica.plot_scores(ecg_scores, title=sub.name + '_ecg', show=False)
                fig5 = ica.plot_properties(ecg_epochs, ecg_indices, psd_args={'fmax': sub.p["lowpass"]},
                                           image_args={'sigma': 1.}, show=False)
                fig6 = ica.plot_overlay(ecg_epochs.average(), exclude=ecg_indices, title=sub.name + '_ecg',
                                        show=False)

                save_path = join(figures_path, 'ica', sub.name +
                                 '_ica_scor_ecg' + '_' + sub.pr.p_preset + '.jpg')
                fig4.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')
                for f in fig5:
                    save_path = join(figures_path, 'ica', sub.name +
                                     '_ica_prop_ecg' + '_' + sub.pr.p_preset
                                     + f'_{fig5.index(f)}.jpg')
                    f.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')
                save_path = join(figures_path, 'ica', sub.name +
                                 '_ica_ovl_ecg' + '_' + sub.pr.p_preset + '.jpg')
                fig6.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

        ut.dict_filehandler(sub.name, f'ica_components_{sub.pr.p_preset}', pscripts_path, values=[])

        sub.save_ica(ica)
        comp_list = []
        for c in range(ica.n_components):
            comp_list.append(c)
        fig1 = ica.plot_components(picks=comp_list, title=sub.name, show=False)
        fig2 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=sub.name, show=False)
        fig3 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=sub.name, show=False)

        if save_plots and save_plots != 'false':
            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_comp' + '_' + sub.pr.p_preset + '.jpg')
            fig1.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_src' + '_' + sub.pr.p_preset + '_0.jpg')
            fig2.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

            save_path = join(figures_path, 'ica', sub.name +
                             '_ica_src' + '_' + sub.pr.p_preset + '_1.jpg')
            fig3.savefig(save_path, dpi=300)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@topline
def apply_ica(sub):
    epochs = sub.load_epochs()
    ica = sub.load_ica()

    if len(ica.exclude) == 0:
        print('No components excluded here')

    ica_epochs = ica.apply(epochs)
    sub.save_ica_epochs(ica_epochs)


@topline
def interpolate_bad_chs(sub, bad_interpolation, enable_ica):
    if bad_interpolation == 'Raw':
        raw = sub.load_raw_filtered()
        new_raw = raw.interpolate_bads(reset_bads=False)
        sub.save_filtered(new_raw)
    elif bad_interpolation == 'Epochs':
        if enable_ica:
            epochs = sub.load_ica_epochs()
        else:
            epochs = sub.load_epochs()
        new_epochs = epochs.interpolate_bads(reset_bads=False)
        sub.save_epochs(new_epochs)
    elif bad_interpolation == 'Evokeds':
        evokeds = sub.load_evokeds()
        new_evokeds = []
        for evoked in evokeds:
            new_evokeds.append(evoked.interpolate_bdas(reset_bads=False))
        sub.save_evokeds(new_evokeds)


@topline
def get_evokeds(sub, enable_ica):
    if enable_ica:
        epochs = sub.load_ica_epochs()
        print('Evokeds from ICA-Epochs')
    else:
        epochs = sub.load_epochs()
        print('Evokeds from (normal) Epochs')
    evokeds = []
    for trial in sub.sel_trials:
        print(f'Evoked for {trial}')
        evoked = epochs[trial].average()
        # Todo: optional if you want weights in your evoked.comment?!
        evoked.comment = trial
        evokeds.append(evoked)

    sub.save_evokeds(evokeds)


@small_func
def calculate_gfp(evoked):
    d = evoked.data
    gfp = np.sqrt((d * d).mean(axis=0))

    return gfp


@topline
def grand_avg_evokeds(ga_group):
    trial_dict = {}
    for name in ga_group.group_list:
        sub = CurrentSub(name, ga_group.mw)
        print(f'Add {name} to grand_average')
        evokeds = sub.load_evokeds()
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

    ga_group.save_ga_evokeds(ga_evokeds)


@topline
def tfr(sub, enable_ica, tfr_freqs, overwrite_tfr,
        tfr_method, multitaper_bandwith, stockwell_width, n_jobs):
    n_cycles = [freq / 2 for freq in tfr_freqs]
    powers = []
    itcs = []

    if overwrite_tfr or not isfile(sub.power_tfr_path) or not isfile(sub.itc_tfr_path):
        if enable_ica:
            epochs = sub.load_ica_epochs()
        else:
            epochs = sub.load_epochs()

        for trial in sub.sel_trials:
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

        sub.save_power_tfr(powers)
        sub.save_itc_tfr(itcs)


@topline
def grand_avg_tfr(ga_group):
    trial_dict = {}
    for name in ga_group.group_list:
        sub = CurrentSub(name, ga_group.mw)
        print(f'Add {name} to grand_average')
        powers = sub.load_power_tfr()
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

            ga_group.save_ga_tfr(ga, trial)


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


def apply_watershed(mri_sub):

    print('Running Watershed algorithm for: ' + mri_sub.name +
          ". Output is written to the bem folder " +
          "of the subject's FreeSurfer folder.\n" +
          'Bash output follows below.\n\n')

    # watershed command
    command = ['mne', 'watershed_bem',
               '--subject', mri_sub.name,
               '--overwrite']

    run_freesurfer_subprocess(command, mri_sub.subjects_dir, mri_sub.fs_path, mri_sub.mne_path)

    if iswin:
        # Copy Watershed-Surfaces because the Links don't work under Windows when made in WSL
        surfaces = [(f'{mri_sub.name}_inner_skull_surface', 'inner_skull.surf'),
                    (f'{mri_sub.name}_outer_skin_surface', 'outer_skin.surf'),
                    (f'{mri_sub.name}_outer_skull_surface', 'outer_skull.surf'),
                    (f'{mri_sub.name}_brain_surface', 'brain.surf')]

        for surface_tuple in surfaces:
            # Remove faulty link
            os.remove(join(mri_sub.subjects_dir, mri_sub.name, 'bem', surface_tuple[1]))
            # Copy files
            source = join(mri_sub.subjects_dir, mri_sub.name, 'bem', 'watershed', surface_tuple[0])
            destination = join(mri_sub.subjects_dir, mri_sub.name, 'bem', surface_tuple[1])
            shutil.copy2(source, destination)

            print(f'{surface_tuple[1]} was created')


def make_dense_scalp_surfaces(mri_sub):
    print('Making dense scalp surfacing easing co-registration for ' +
          'subject: ' + mri_sub.name +
          ". Output is written to the bem folder" +
          " of the subject's FreeSurfer folder.\n" +
          'Bash output follows below.\n\n')

    command = ['mne', 'make_scalp_surfaces',
               '--subject', mri_sub.name,
               '--overwrite']

    run_freesurfer_subprocess(command, mri_sub.subjects_dir, mri_sub.fs_path, mri_sub.mne_path)


# ==============================================================================
# MNE SOURCE RECONSTRUCTIONS
# ==============================================================================
@topline
def setup_src(mri_sub, source_space_spacing, surface, n_jobs):
    src = mne.setup_source_space(mri_sub.name, spacing=source_space_spacing,
                                 surface=surface, subjects_dir=mri_sub.subjects_dir,
                                 add_dist=False, n_jobs=n_jobs)
    mri_sub.save_source_space(src)


@topline
def setup_vol_src(mri_sub, vol_source_space_spacing):
    bem = mri_sub.load_bem_solution()
    vol_src = mne.setup_volume_source_space(mri_sub.name, pos=vol_source_space_spacing, bem=bem,
                                            subjects_dir=mri_sub.subjects_dir)
    mri_sub.save_vol_source_space(vol_src)


@topline
def compute_src_distances(mri_sub, n_jobs):
    src = mri_sub.load_source_space()
    src_computed = mne.add_source_space_distances(src, n_jobs=n_jobs)
    mri_sub.save_source_space(src_computed)


@topline
def prepare_bem(mri_sub, bem_spacing):
    bem_model = mne.make_bem_model(mri_sub.name, subjects_dir=mri_sub.subjects_dir,
                                   ico=bem_spacing)
    mri_sub.save_bem_model(bem_model)

    bem_solution = mne.make_bem_solution(bem_model)
    mri_sub.save_bem_solution(bem_solution)


@topline
def morph_subject(mri_sub, morph_to):
    src = mri_sub.load_source_space()
    morph = mne.compute_source_morph(src, subject_from=mri_sub.name,
                                     subject_to=morph_to, subjects_dir=mri_sub.subjects_dir)
    mri_sub.save_source_morph(morph)


@topline
def morph_labels_from_fsaverage(mri_sub):
    parcellations = ['aparc_sub', 'HCPMMP1_combined', 'HCPMMP1']
    if not isfile(join(mri_sub.subjects_dir, 'fsaverage/label',
                       'lh.' + parcellations[0] + '.annot')):
        mne.datasets.fetch_hcp_mmp_parcellation(subjects_dir=mri_sub.subjects_dir,
                                                verbose=True)

        mne.datasets.fetch_aparc_sub_parcellation(subjects_dir=mri_sub.subjects_dir,
                                                  verbose=True)
    else:
        print('You\'ve already downloaded the parcellations, splendid!')

    if not isfile(join(mri_sub.subjects_dir, mri_sub.name, 'label',
                       'lh.' + parcellations[0] + '.annot')):
        for pc in parcellations:
            labels = mne.read_labels_from_annot('fsaverage', pc, hemi='both')

            m_labels = mne.morph_labels(labels, mri_sub.name, 'fsaverage', mri_sub.subjects_dir,
                                        surf_name='pial')

            mne.write_labels_to_annot(m_labels, subject=mri_sub.name, parc=pc,
                                      subjects_dir=mri_sub.subjects_dir, overwrite=True)

    else:
        print(f'{parcellations} already exist')


@topline
def create_forward_solution(sub, n_jobs, eeg_fwd):
    info = sub.load_info()
    trans = sub.load_transformation()
    bem = sub.mri_sub.load_bem_solution()
    source_space = sub.mri_sub.load_source_space()

    forward = mne.make_forward_solution(info, trans, source_space, bem,
                                        n_jobs=n_jobs, eeg=eeg_fwd)

    sub.save_forward(forward)


@topline
def estimate_noise_covariance(sub, baseline, n_jobs, erm_noise_cov, calm_noise_cov, enable_ica):
    if calm_noise_cov:
        print('Noise Covariance on 1-Minute-Calm')

        raw = sub.read_filtered()
        raw.crop(tmin=5, tmax=50)
        raw.pick_types(exclude=sub.bad_channels)

        noise_covariance = mne.compute_raw_covariance(raw, n_jobs=n_jobs,
                                                      method='empirical')
        sub.save_noise_covariance(noise_covariance, 'calm')

    elif sub.ermsub == 'None' or erm_noise_cov is False:
        print('Noise Covariance on Epochs')
        if enable_ica:
            epochs = sub.load_ica_epochs()
        else:
            epochs = sub.load_epochs()

        tmin, tmax = baseline
        noise_covariance = mne.compute_covariance(epochs, tmin=tmin, tmax=tmax,
                                                  method='empirical', n_jobs=n_jobs)

        sub.save_noise_covariance(noise_covariance, 'epochs')

    else:
        print('Noise Covariance on ERM')

        erm_filtered = sub.load_erm_filtered()
        erm_filtered.pick_types(exclude=sub.bad_channels)

        noise_covariance = mne.compute_raw_covariance(erm_filtered, n_jobs=n_jobs,
                                                      method='empirical')
        sub.save_noise_covariance(noise_covariance, 'erm')


@topline
def create_inverse_operator(sub):
    info = sub.load_info()
    noise_covariance = sub.load_noise_covariance()
    forward = sub.load_forward()

    inverse_operator = mne.minimum_norm.make_inverse_operator(info, forward, noise_covariance)
    sub.save_inverse_operator(inverse_operator)


@topline
def source_estimate(sub, inverse_method, pick_ori, lambda2):
    inverse_operator = sub.load_inverse_operator()
    evokeds = sub.load_evokeds()

    stcs = {}
    for evoked in [ev for ev in evokeds if ev.comment in sub.sel_trials]:
        stc = mne.minimum_norm.apply_inverse(evoked, inverse_operator, lambda2, method=inverse_method,
                                             pick_ori=pick_ori)
        stcs.update({evoked.comment: stc})

    sub.save_source_estimates(stcs)


@topline
def label_time_course(sub, target_labels, parcellation, extract_mode):
    stcs = sub.load_source_estimates()
    src = sub.mri_sub.load_source_space()

    labels = mne.read_labels_from_annot(sub.subtomri,
                                        subjects_dir=sub.subjects_dir,
                                        parc=parcellation)
    chosen_labels = [label for label in labels if label.name in target_labels]

    ltc_dict = {}

    for trial in stcs:
        ltc_dict[trial] = {}
        times = stcs[trial].times
        for label in chosen_labels:
            ltc = stcs[trial].extract_label_time_course(label, src, mode=extract_mode)[0]
            ltc_dict[trial][label.name] = np.vstack((ltc, times))

    sub.save_ltc(ltc_dict)


# Todo: Make mixed-norm more customizable
@topline
def mixed_norm_estimate(sub, pick_ori, inverse_method):
    evokeds = sub.load_evokeds()
    forward = sub.load_forward()
    noise_cov = sub.load_noise_covariance()
    inv_op = sub.load_inverse_operator()
    if inverse_method == 'dSPM':
        print('dSPM-Inverse-Solution existent, loading...')
        stcs = sub.load_source_estimates()
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

    for evoked in [ev for ev in evokeds if ev.comment in sub.sel_trials]:
        alpha = 30  # regularization parameter between 0 and 100 (100 is high)
        n_mxne_iter = 10  # if > 1 use L0.5/L2 reweighted mixed norm solver
        # if n_mxne_iter > 1 dSPM weighting can be avoided.

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

    sub.save_mixn_dipoles(mixn_dips)
    sub.save_mixn_source_estimates(mixn_stcs)


# Todo: Separate Plot-Functions (better responsivness of GUI during fit, when running in QThread)
@topline
def ecd_fit(sub, ecd_times, ecd_positions, ecd_orientations, t_epoch):
    try:
        ecd_time = ecd_times[sub.name]
    except KeyError:
        ecd_time = {'Dip1': (0, t_epoch[1])}
        print(f'No Dipole times assigned for {sub.name}, Dipole-Times: 0-{t_epoch[1]}')

    evokeds = sub.load_evokeds()
    noise_covariance = sub.load_noise_covariance()
    bem = sub.mri_sub.load_bem_solution()
    trans = sub.load_transformation()

    ecd_dips = {}

    for evoked in evokeds:
        trial = evoked.comment
        ecd_dips[trial] = {}
        for dip in ecd_time:
            tmin, tmax = ecd_time[dip]
            copy_evoked = evoked.copy().crop(tmin, tmax)

            try:
                ecd_position = ecd_positions[sub.name][dip]
                ecd_orientation = ecd_orientations[sub.name][dip]
            except KeyError:
                ecd_position = None
                ecd_orientation = None
                print(f'No Position&Orientation for Dipole for {sub.name} assigned, '
                      f'sequential fitting and free orientation used')

            if ecd_position:
                dipole, residual = mne.fit_dipole(copy_evoked, noise_covariance, bem, trans=trans,
                                                  min_dist=3.0, n_jobs=4, pos=ecd_position, ori=ecd_orientation)
            else:
                dipole, residual = mne.fit_dipole(copy_evoked, noise_covariance, bem, trans=trans, min_dist=3.0,
                                                  n_jobs=4)

            ecd_dips[trial][dip] = dipole

    sub.save_ecd(ecd_dips)


@topline
def apply_morph(sub):
    stcs = sub.load_source_estimates()
    morph = sub.mri_sub.load_source_morph()

    morphed_stcs = {}
    for trial in stcs:
        morphed_stcs[trial] = morph.apply(stcs[trial])
    sub.save_morphed_source_estimates(morphed_stcs)


@topline
def source_space_connectivity(sub, parcellation, target_labels, inverse_method, lambda2, con_methods,
                              con_fmin, con_fmax, n_jobs, enable_ica):
    info = sub.load_info()
    if enable_ica:
        all_epochs = sub.load_ica_epochs()
    else:
        all_epochs = sub.load_epochs()
    inverse_operator = sub.load_inverse_operator()
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
        labels = mne.read_labels_from_annot(sub.subtomri, parc=parcellation,
                                            subjects_dir=sub.subjects_dir)

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

    sub.save_connectivity(con_dict)


@topline
def grand_avg_morphed(ga_group):
    # for less memory only import data from stcs and add it to one fsaverage-stc in the end!!!
    n_chunks = 8
    # divide in chunks to save memory
    fusion_dict = {}
    for i in range(0, len(ga_group.group_list), n_chunks):
        sub_trial_dict = {}
        ga_chunk = ga_group.group_list[i:i + n_chunks]
        print(ga_chunk)
        for name in ga_chunk:
            sub = CurrentSub(name, ga_group.mw)
            print(f'Add {name} to grand_average')
            stcs = sub.load_morphed_source_estimates()
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
            print(f'grand_average for {ga_group.name}-{trial}')
            trial_average = fusion_dict[trial][0].copy()
            n_subjects = len(fusion_dict[trial])

            for trial_index in range(1, n_subjects):
                trial_average.data += fusion_dict[trial][trial_index].data

            trial_average.data /= n_subjects
            trial_average.comment = trial

            ga_stcs[trial] = trial_average

    ga_group.save_ga_source_estimate(ga_stcs)


@topline
def grand_avg_ltc(ga_group):
    ltc_average_dict = {}
    times = None
    for name in ga_group.group_list:
        sub = CurrentSub(name, ga_group.mw)
        print(f'Add {name} to grand_average')
        ltc_dict = sub.load_ltc()
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

    ga_group.save_ga_ltc(ga_ltc)


@topline
def grand_avg_connect(ga_group):
    # Prepare the Average-Dict
    con_average_dict = {}
    for name in ga_group.group_list:
        sub = CurrentSub(name, ga_group.mw)
        print(f'Add {name} to grand_average')
        con_dict = sub.load_connectivity()
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

    ga_group.save_ga_connect(ga_con)
