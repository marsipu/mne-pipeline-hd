# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
from __future__ import print_function

import gc
import pickle
import subprocess
import sys
from collections import Counter
from functools import reduce
from itertools import combinations
from os import environ, listdir, makedirs, remove
from os.path import exists, isdir, isfile, join

import mne
import numpy as np
from autoreject import AutoReject
from matplotlib import pyplot as plt
from nilearn.plotting import plot_anat
from scipy import stats

from mne_pipeline_hd.basic_functions import loading, plot as plot
from mne_pipeline_hd.pipeline_functions import iswin, pipeline_utils as ut
from mne_pipeline_hd.pipeline_functions.decorators import small_func, topline


# Todo: Change normal comments to docstrings
# Naming Conventions
def filter_string(highpass, lowpass):
    # Check for .0
    if '.0' in str(highpass):
        highpass = int(highpass)
    if '.0' in str(lowpass):
        lowpass = int(lowpass)
    if highpass and highpass != 0:
        fs = '_' + str(highpass) + '-' + str(lowpass) + '_Hz'
    else:
        fs = '_' + str(lowpass) + '_Hz'

    return fs


# ==============================================================================
# PREPROCESSING AND GETTING TO EVOKED AND TFR
# ==============================================================================
@topline
def filter_raw(name, save_dir, highpass, lowpass, ermsub,
               data_path, n_jobs, enable_cuda, bad_channels, erm_t_limit,
               enable_ica):
    filter_name = name + filter_string(highpass, lowpass) + '-raw.fif'
    filter_path = join(save_dir, filter_name)

    ica_filter_name = name + filter_string(1, lowpass) + '-raw.fif'
    ica_filter_path = join(save_dir, ica_filter_name)

    if not isfile(filter_path) or not isfile(ica_filter_path):
        raw = loading.read_raw(name, save_dir)
    else:
        raw = None

    if not isfile(filter_path):
        if enable_cuda:  # use cuda for filtering
            n_jobs = 'cuda'
        raw.filter(highpass, lowpass, n_jobs=n_jobs)

        filter_name = name + filter_string(highpass, lowpass) + '-raw.fif'
        filter_path = join(save_dir, filter_name)

        # Save some data in the info-dictionary and finally save it
        raw.info['description'] = name
        raw.info['bads'] = bad_channels

        raw.save(filter_path, overwrite=True)

    else:
        print(f'raw file with Highpass = {highpass} Hz and Lowpass = {lowpass} Hz already exists')
        print('NO OVERWRITE FOR FILTERING, please change settings or delete files for new methods')

    # Filter Empty-Room-Data too
    if ermsub != 'None':
        erm_name = ermsub + '-raw.fif'
        erm_path = join(data_path, 'empty_room_data', ermsub, erm_name)
        erm_filter_name = ermsub + filter_string(highpass, lowpass) + '-raw.fif'
        erm_filter_path = join(data_path, 'empty_room_data', ermsub, erm_filter_name)

        if not isfile(erm_filter_path):
            raw = loading.read_raw(name, save_dir)
            erm_raw = mne.io.read_raw_fif(erm_path, preload=True)

            # Due to channel-deletion sometimes in HPI-Fitting-Process
            ch_list = set(erm_raw.info['ch_names']) & set(raw.info['ch_names'])
            erm_raw.pick_channels(ch_list)
            erm_raw.pick_types(meg=True, exclude=bad_channels)
            erm_raw.filter(highpass, lowpass)

            erm_length = erm_raw.n_times / erm_raw.info['sfreq']  # in s

            if erm_length > erm_t_limit:
                diff = erm_length - erm_t_limit
                tmin = diff / 2
                tmax = erm_length - diff / 2
                erm_raw.crop(tmin=tmin, tmax=tmax)

            erm_raw.save(erm_filter_path, overwrite=True)
            print('ERM-Data filtered and saved')

        else:
            print('erm_raw file: ' + erm_filter_path + ' already exists')

    else:
        print('no erm_file assigned')


@topline
def pipe_find_events(name, save_dir, adjust_timeline_by_msec, overwrite):
    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)

    if overwrite or not isfile(events_path):
        raw = loading.read_raw(name, save_dir)

        # Binary Coding of 6 Stim Channels in Biomagenetism Lab Heidelberg
        # prepare arrays
        events = np.ndarray(shape=(0, 3), dtype=np.int32)
        evs = list()
        evs_tol = list()

        # Find events for each stim channel, append sample values to list
        evs.append(mne.find_events(raw, min_duration=0.002, stim_channel=['STI 001'])[:, 0])
        evs.append(mne.find_events(raw, min_duration=0.002, stim_channel=['STI 002'])[:, 0])
        evs.append(mne.find_events(raw, min_duration=0.002, stim_channel=['STI 003'])[:, 0])
        evs.append(mne.find_events(raw, min_duration=0.002, stim_channel=['STI 004'])[:, 0])
        evs.append(mne.find_events(raw, min_duration=0.002, stim_channel=['STI 005'])[:, 0])
        evs.append(mne.find_events(raw, min_duration=0.002, stim_channel=['STI 006'])[:, 0])

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
        print('unique ID\'s assigned: ', ids)

        if np.size(events) > 0:
            mne.event.write_events(events_path, events)
        else:
            print('No events found')

    else:
        print('event file: ' + events_path + ' already exists')


@topline
def find_eog_events(name, save_dir, eog_channel):
    eog_events_name = name + '_eog-eve.fif'
    eog_events_path = join(save_dir, eog_events_name)

    raw = loading.read_raw(name, save_dir)
    eog_events = mne.preprocessing.find_eog_events(raw, ch_name=eog_channel)

    mne.event.write_events(eog_events_path, eog_events)
    print(f'{np.size(eog_events)} detected')


@topline
def epoch_raw(name, save_dir, highpass, lowpass, event_id, t_epoch,
              baseline, reject, flat, autoreject, overwrite_ar,
              pscripts_path, bad_channels, decim,
              reject_eog_epochs, overwrite):
    epochs_name = name + filter_string(highpass, lowpass) + '-epo.fif'
    epochs_path = join(save_dir, epochs_name)
    if overwrite or not isfile(epochs_path):

        raw = loading.read_filtered(name, save_dir, highpass, lowpass)
        raw.info['bads'] = bad_channels

        events = loading.read_events(name, save_dir)

        # Choose only included event_ids
        actual_event_id = {}
        for i in event_id:
            if event_id[i] in np.unique(events[:, 2]):
                actual_event_id.update({i: event_id[i]})

        print('Event_ids included:')
        for i in actual_event_id:
            print(i)

        picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False,
                               eog=False, ecg=False, exclude='bads')

        if reject_eog_epochs:
            eog_events = loading.read_eog_events(name, save_dir)

            n_blinks = len(eog_events)
            onset = eog_events[:, 0] / raw.info['sfreq'] - 0.25
            duration = np.repeat(0.5, n_blinks)
            description = ['bad blink'] * n_blinks

            annotations = mne.Annotations(onset, duration, description)

            eog_annot_name = name + '-eog-annot.fif'
            eog_annot_path = join(save_dir, eog_annot_name)
            annotations.save(eog_annot_path)

            raw.set_annotations(annotations)
            print(f'{n_blinks} blinks detected and annotated')

        epochs = mne.Epochs(raw, events, actual_event_id, t_epoch[0], t_epoch[1], baseline,
                            preload=True, picks=picks, proj=False, reject=None,
                            decim=decim, on_missing='ignore', reject_by_annotation=True)

        if autoreject:
            reject = ut.autoreject_handler(name, epochs, highpass, lowpass, pscripts_path, overwrite_ar=overwrite_ar)

        print(f'Rejection Threshold: {reject}')

        epochs.drop_bad(reject=reject, flat=flat)
        epochs.save(epochs_path, overwrite=True)

        reject_channels = []
        log = epochs.drop_log

        for a in log:
            if a:
                for b in a:
                    reject_channels.append(b)
        c = Counter(reject_channels).most_common()

        # noinspection PyTypeChecker
        c.insert(0, (len(epochs), epochs.drop_log_stats()))

        ut.dict_filehandler(name, f'reject_channels_{highpass}-{lowpass}_Hz',
                            pscripts_path, values=c)

    else:
        print('epochs file: ' + epochs_path + ' already exists')


# TODO: Organize run_ica properly
@topline
def run_ica(name, save_dir, highpass, lowpass, eog_channel, ecg_channel,
            reject, flat, bad_channels, overwrite, autoreject,
            save_plots, figures_path, pscripts_path):
    info = loading.read_info(name, save_dir)

    ica_dict = ut.dict_filehandler(name, f'ica_components{filter_string(highpass, lowpass)}', pscripts_path,
                                   onlyread=True)

    ica_name = name + filter_string(highpass, lowpass) + '-ica.fif'
    ica_path = join(save_dir, ica_name)

    if overwrite or not isfile(ica_path):

        # Make Raw-Version with 1 Hz Highpass-Filter if not existent
        ica_filter_path = join(save_dir, name + filter_string(lowpass, 1) + '-raw.fif')

        if highpass < 1 and not isfile(ica_filter_path):
            raw = loading.read_raw(name, save_dir)
            raw.filter(1, lowpass)

            filter_name = name + filter_string(lowpass, 1) + '-raw.fif'
            filter_path = join(save_dir, filter_name)

            # Save some data in the info-dictionary and finally save it
            raw.info['description'] = name
            raw.info['bads'] = bad_channels

            raw.save(filter_path, overwrite=True)

        raw = loading.read_filtered(name, save_dir, 1, lowpass)

        epochs = loading.read_epochs(name, save_dir, highpass, lowpass)
        picks = mne.pick_types(raw.info, meg=True, eeg=False, eog=False,
                               stim=False, exclude=bad_channels)

        ica = mne.preprocessing.ICA(n_components=25, method='fastica', random_state=8)

        if autoreject:
            reject = ut.autoreject_handler(name, epochs, highpass, lowpass, pscripts_path, overwrite_ar=False,
                                           only_read=True)

        print('Rejection Threshold: %s' % reject)

        ica.fit(raw, picks, reject=reject, flat=flat,
                reject_by_annotation=True)

        if name in ica_dict and ica_dict[name] != [] and ica_dict[name]:
            indices = ica_dict[name]
            ica.exclude += indices
            print(f'{indices} added to ica.exclude from ica_components.py')
            ica.save(ica_path)

            comp_list = []
            for c in range(ica.n_components):
                comp_list.append(c)
            fig1 = ica.plot_components(picks=comp_list, title=name, show=False)
            fig3 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name, show=False)
            fig4 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name, show=False)
            fig5 = ica.plot_overlay(epochs.average(), title=name, show=False)
            if save_plots:

                save_path = join(figures_path, 'ica', name +
                                 '_ica_comp' + filter_string(highpass, lowpass) + '.jpg')
                fig1.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name +
                                 '_ica_src' + filter_string(highpass, lowpass) + '_0.jpg')
                fig3.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name +
                                 '_ica_src' + filter_string(highpass, lowpass) + '_1.jpg')
                fig4.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')
                if not exists(join(figures_path, 'ica/evoked_overlay')):
                    makedirs(join(figures_path, 'ica/evoked_overlay'))
                save_path = join(figures_path, 'ica/evoked_overlay', name +
                                 '_ica_ovl' + filter_string(highpass, lowpass) + '.jpg')
                fig5.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

        elif 'EEG 001' in info['ch_names']:
            eeg_picks = mne.pick_types(raw.info, meg=True, eeg=True, eog=True,
                                       stim=False, exclude=bad_channels)

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
                    fig3 = ica.plot_scores(eog_scores, title=name + '_eog', show=False)
                    fig2 = ica.plot_properties(eog_epochs, eog_indices, psd_args={'fmax': lowpass},
                                               image_args={'sigma': 1.}, show=False)
                    fig7 = ica.plot_overlay(eog_epochs.average(), exclude=eog_indices, title=name + '_eog', show=False)
                    if save_plots:
                        for f in fig2:
                            save_path = join(figures_path, 'ica', name +
                                             '_ica_prop_eog' + filter_string(highpass, lowpass) +
                                             f'_{fig2.index(f)}.jpg')
                            f.savefig(save_path, dpi=300)
                            print('figure: ' + save_path + ' has been saved')

                        save_path = join(figures_path, 'ica', name +
                                         '_ica_scor_eog' + filter_string(highpass, lowpass) + '.jpg')
                        fig3.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

                        save_path = join(figures_path, 'ica', name +
                                         '_ica_ovl_eog' + filter_string(highpass, lowpass) + '.jpg')
                        fig7.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

            if len(ecg_epochs) != 0:
                ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs, ch_name=ecg_channel)
                ica.exclude.extend(ecg_indices)
                print('ECG-Components: ', ecg_indices)
                print(len(ecg_indices))
                if len(ecg_indices) != 0:
                    # Plot ECG-Plots
                    fig4 = ica.plot_scores(ecg_scores, title=name + '_ecg', show=False)
                    fig9 = ica.plot_properties(ecg_epochs, ecg_indices, psd_args={'fmax': lowpass},
                                               image_args={'sigma': 1.}, show=False)
                    fig8 = ica.plot_overlay(ecg_epochs.average(), exclude=ecg_indices, title=name + '_ecg', show=False)
                    if save_plots:
                        for f in fig9:
                            save_path = join(figures_path, 'ica', name +
                                             '_ica_prop_ecg' + filter_string(highpass, lowpass) +
                                             f'_{fig9.index(f)}.jpg')
                            f.savefig(save_path, dpi=300)
                            print('figure: ' + save_path + ' has been saved')

                        save_path = join(figures_path, 'ica', name +
                                         '_ica_scor_ecg' + filter_string(highpass, lowpass) + '.jpg')
                        fig4.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

                        save_path = join(figures_path, 'ica', name +
                                         '_ica_ovl_ecg' + filter_string(highpass, lowpass) + '.jpg')
                        fig8.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

            ica.save(ica_path)

            # Reading and Writing ICA-Components to a .py-file
            exes = ica.exclude
            indices = []
            for i in exes:
                indices.append(int(i))

            ut.dict_filehandler(name, f'ica_components{filter_string(highpass, lowpass)}', pscripts_path,
                                values=indices, overwrite=True)

            # Plot ICA integrated
            comp_list = []
            for c in range(ica.n_components):
                comp_list.append(c)
            fig1 = ica.plot_components(picks=comp_list, title=name, show=False)
            fig5 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name, show=False)
            fig6 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name, show=False)
            fig10 = ica.plot_overlay(epochs.average(), title=name, show=False)

            if save_plots:
                save_path = join(figures_path, 'ica', name +
                                 '_ica_comp' + filter_string(highpass, lowpass) + '.jpg')
                fig1.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')
                if not exists(join(figures_path, 'ica/evoked_overlay')):
                    makedirs(join(figures_path, 'ica/evoked_overlay'))
                save_path = join(figures_path, 'ica/evoked_overlay', name +
                                 '_ica_ovl' + filter_string(highpass, lowpass) + '.jpg')
                fig10.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name +
                                 '_ica_src' + filter_string(highpass, lowpass) + '_0.jpg')
                fig5.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name +
                                 '_ica_src' + filter_string(highpass, lowpass) + '_1.jpg')
                fig6.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

        # No EEG was acquired during the measurement,
        # components have to be selected manually in the ica_components.py
        else:
            print('No EEG-Channels to read EOG/EEG from')
            meg_picks = mne.pick_types(raw.info, meg=True, eeg=False, eog=False,
                                       stim=False, exclude=bad_channels)
            ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, picks=meg_picks,
                                                             reject=reject, flat=flat)

            if len(ecg_epochs) != 0:
                ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs)
                print('ECG-Components: ', ecg_indices)
                if len(ecg_indices) != 0:
                    fig4 = ica.plot_scores(ecg_scores, title=name + '_ecg', show=False)
                    fig5 = ica.plot_properties(ecg_epochs, ecg_indices, psd_args={'fmax': lowpass},
                                               image_args={'sigma': 1.}, show=False)
                    fig6 = ica.plot_overlay(ecg_epochs.average(), exclude=ecg_indices, title=name + '_ecg', show=False)

                    save_path = join(figures_path, 'ica', name +
                                     '_ica_scor_ecg' + filter_string(highpass, lowpass) + '.jpg')
                    fig4.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')
                    for f in fig5:
                        save_path = join(figures_path, 'ica', name +
                                         '_ica_prop_ecg' + filter_string(highpass, lowpass)
                                         + f'_{fig5.index(f)}.jpg')
                        f.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')
                    save_path = join(figures_path, 'ica', name +
                                     '_ica_ovl_ecg' + filter_string(highpass, lowpass) + '.jpg')
                    fig6.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

            ut.dict_filehandler(name, f'ica_components{filter_string(highpass, lowpass)}', pscripts_path, values=[])

            ica.save(ica_path)
            comp_list = []
            for c in range(ica.n_components):
                comp_list.append(c)
            fig1 = ica.plot_components(picks=comp_list, title=name, show=False)
            fig2 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name, show=False)
            fig3 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name, show=False)

            if save_plots:
                save_path = join(figures_path, 'ica', name +
                                 '_ica_comp' + filter_string(highpass, lowpass) + '.jpg')
                fig1.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name +
                                 '_ica_src' + filter_string(highpass, lowpass) + '_0.jpg')
                fig2.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name +
                                 '_ica_src' + filter_string(highpass, lowpass) + '_1.jpg')
                fig3.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

    else:
        print('ica file: ' + ica_path + ' already exists')


@topline
def apply_ica(name, save_dir, highpass, lowpass, overwrite):
    ica_epochs_name = name + filter_string(highpass, lowpass) + '-ica-epo.fif'
    ica_epochs_path = join(save_dir, ica_epochs_name)

    if overwrite or not isfile(ica_epochs_path):

        epochs = loading.read_epochs(name, save_dir, highpass, lowpass)
        ica = loading.read_ica(name, save_dir, highpass, lowpass)

        if len(ica.exclude) == 0:
            print('No components excluded here')

        ica_epochs = ica.apply(epochs)
        ica_epochs.save(ica_epochs_path, overwrite=True)

    else:
        print('ica epochs file: ' + ica_epochs_path + ' already exists')


@topline
def autoreject_interpolation(name, save_dir, highpass, lowpass, enable_ica):
    if enable_ica:
        ica_epochs_name = name + filter_string(highpass, lowpass) + '-ica-epo.fif'
        save_path = join(save_dir, ica_epochs_name)
        epochs = loading.read_ica_epochs(name, save_dir, highpass, lowpass)
        print('Evokeds from ICA-Epochs')
    else:
        epochs_name = name + filter_string(highpass, lowpass) + '-epo.fif'
        save_path = join(save_dir, epochs_name)
        epochs = loading.read_epochs(name, save_dir, highpass, lowpass)
        print('Evokeds from (normal) Epochs')
    autor = AutoReject(n_jobs=-1)
    epochs_clean = autor.fit_transform(epochs)

    epochs_clean.save(save_path, overwrite=True)


@topline
def get_evokeds(name, save_dir, highpass, lowpass, enable_ica, overwrite):
    evokeds_name = name + filter_string(highpass, lowpass) + '-ave.fif'
    evokeds_path = join(save_dir, evokeds_name)

    if overwrite or not isfile(evokeds_path):
        if enable_ica:
            epochs = loading.read_ica_epochs(name, save_dir, highpass, lowpass)
            print('Evokeds from ICA-Epochs')
        else:
            epochs = loading.read_epochs(name, save_dir, highpass, lowpass)
            print('Evokeds from (normal) Epochs')
        evokeds = []
        for trial_type in epochs.event_id:
            print(f'Evoked for {trial_type}')
            evoked = epochs[trial_type].average()
            evokeds.append(evoked)

        mne.evoked.write_evokeds(evokeds_path, evokeds)

    else:
        print('evokeds file: ' + evokeds_path + ' already exists')


@small_func
def calculate_gfp(evoked):
    d = evoked.data
    gfp = np.sqrt((d * d).mean(axis=0))

    return gfp


@topline
def grand_avg_evokeds(data_path, grand_avg_dict, sel_ga_groups, save_dir_averages,
                      highpass, lowpass):
    for key in grand_avg_dict:
        if key in sel_ga_groups:
            trial_dict = {}
            print(f'grand_average for {key}')
            for name in grand_avg_dict[key]:
                save_dir = join(data_path, name)
                print(f'Add {name} to grand_average')
                evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)
                for evoked in evokeds:
                    if evoked.nave != 0:
                        if evoked.comment in trial_dict:
                            trial_dict[evoked.comment].append(evoked)
                        else:
                            trial_dict.update({evoked.comment: [evoked]})
                    else:
                        print(f'{evoked.comment} for {name} got nave=0')

            for trial in trial_dict:
                if len(trial_dict[trial]) != 0:
                    ga = mne.grand_average(trial_dict[trial],
                                           interpolate_bads=True,
                                           drop_bads=True)
                    ga.comment = trial
                    ga_path = join(save_dir_averages, 'evoked',
                                   key + '_' + trial +
                                   filter_string(highpass, lowpass) + '-grand_avg-ave.fif')
                    ga.save(ga_path)


@topline
def tfr(name, save_dir, highpass, lowpass, enable_ica, tfr_freqs, overwrite_tfr,
        tfr_method, multitaper_bandwith, stockwell_width, n_jobs):
    power_name = name + filter_string(highpass, lowpass) + '_' + tfr_method + '_pw-tfr.h5'
    power_path = join(save_dir, power_name)
    itc_name = name + filter_string(highpass, lowpass) + '_' + tfr_method + '_itc-tfr.h5'
    itc_path = join(save_dir, itc_name)

    n_cycles = [freq / 2 for freq in tfr_freqs]
    powers = []
    itcs = []

    if overwrite_tfr or not isfile(power_path) or not isfile(itc_path):
        if enable_ica:
            epochs = loading.read_ica_epochs(name, save_dir, highpass, lowpass)
        else:
            epochs = loading.read_epochs(name, save_dir, highpass, lowpass)

        for trial_type in epochs.event_id:
            if tfr_method == 'morlet':
                power, itc = mne.time_frequency.tfr_morlet(epochs[trial_type],
                                                           freqs=tfr_freqs,
                                                           n_cycles=n_cycles,
                                                           n_jobs=n_jobs)
            elif tfr_method == 'multitaper':
                power, itc = mne.time_frequency.tfr_multitaper(epochs[trial_type],
                                                               freqs=tfr_freqs,
                                                               n_cycles=n_cycles,
                                                               time_bandwith=multitaper_bandwith,
                                                               n_jobs=n_jobs)
            elif tfr_method == 'stockwell':
                fmin, fmax = tfr_freqs[[0, -1]]
                power, itc = mne.time_frequency.tfr_stockwell(epochs[trial_type],
                                                              fmin=fmin, fmax=fmax,
                                                              width=stockwell_width,
                                                              n_jobs=n_jobs)
            else:
                power, itc = [], []
                print('No appropriate tfr_method defined in pipeline')

            power.comment = trial_type
            itc.comment = trial_type

            powers.append(power)
            itcs.append(itc)

        mne.time_frequency.write_tfrs(power_path, powers, overwrite=True)
        mne.time_frequency.write_tfrs(itc_path, itcs, overwrite=True)


@topline
def grand_avg_tfr(data_path, grand_avg_dict, save_dir_averages,
                  highpass, lowpass, tfr_method):
    for key in grand_avg_dict:
        trial_dict = {}
        print(f'grand_average for {key}')
        for name in grand_avg_dict[key]:
            save_dir = join(data_path, name)
            print(f'Add {name} to grand_average')
            powers = loading.read_tfr_power(name, save_dir, highpass,
                                            lowpass, tfr_method)
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
                ga_path = join(save_dir_averages, 'tfr',
                               key + '_' + trial +
                               filter_string(highpass, lowpass) +
                               '-grand_avg-tfr.h5')

                ga.save(ga_path)


# ==============================================================================
# BASH OPERATIONS
# ==============================================================================
# These functions do not work on Windows

# local function used in the bash commands below
def run_process_and_write_output(command, subjects_dir):
    environment = environ.copy()
    environment["SUBJECTS_DIR"] = subjects_dir

    if iswin:
        raise RuntimeError('mri_subject_functions are currently not working on Windows, please run them on Linux')
        # command.insert(0, 'wsl')

    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               env=environment)

    # write bash output in python console
    for c in iter(lambda: process.stdout.read(1), b''):
        sys.stdout.write(c.decode('utf-8'))


def import_mri(dicom_path, mri_subject, subjects_dir, n_jobs_freesurfer):
    files = listdir(dicom_path)
    first_file = files[0]
    # check if import has already been done
    if not isdir(join(subjects_dir, mri_subject)):
        # run bash command
        print('Importing MRI data for subject: ' + mri_subject +
              ' into FreeSurfer folder.\nBash output follows below.\n\n')

        command = ['recon-all',
                   '-subjid', mri_subject,
                   '-i', join(dicom_path, first_file),
                   '-openmp', str(n_jobs_freesurfer)]

        run_process_and_write_output(command, subjects_dir)
    else:
        print('FreeSurfer folder for: ' + mri_subject + ' already exists.' +
              ' To import data from the beginning, you would have to ' +
              "delete this subject's FreeSurfer folder")


# Todo: Get Freesurfer-Functions ready
def segment_mri(mri_subject, subjects_dir, n_jobs_freesurfer):
    print('Segmenting MRI data for subject: ' + mri_subject +
          ' using the Freesurfer "recon-all" pipeline.' +
          'Bash output follows below.\n\n')

    command = ['recon-all',
               '-subjid', mri_subject,
               '-all',
               '-openmp', str(n_jobs_freesurfer)]

    run_process_and_write_output(command, subjects_dir)


def apply_watershed(mri_subject, subjects_dir, overwrite):
    # mne.bem.make_watershed_bem(mri_subject, subjects_dir)

    print('Running Watershed algorithm for: ' + mri_subject +
          ". Output is written to the bem folder " +
          "of the subject's FreeSurfer folder.\n" +
          'Bash output follows below.\n\n')

    if overwrite:
        overwrite_string = '--overwrite'
    else:
        overwrite_string = ''
    # watershed command
    command = ['mne', 'watershed_bem',
               '--subject', mri_subject,
               overwrite_string]

    run_process_and_write_output(command, subjects_dir)
    # copy commands
    surfaces = dict(
            inner_skull=dict(
                    origin=mri_subject + '_inner_skull_surface',
                    destination='inner_skull.surf'),
            outer_skin=dict(origin=mri_subject + '_outer_skin_surface',
                            destination='outer_skin.surf'),
            outer_skull=dict(origin=mri_subject + '_outer_skull_surface',
                             destination='outer_skull.surf'),
            brain=dict(origin=mri_subject + '_brain_surface',
                       destination='brain_surface.surf')
    )

    for surface in surfaces:
        this_surface = surfaces[surface]
        # copy files from watershed into bem folder where MNE expects to
        # find them
        command = ['cp', '-v',
                   join(subjects_dir, mri_subject, 'bem', 'watershed',
                        this_surface['origin']),
                   join(subjects_dir, mri_subject, 'bem',
                        this_surface['destination'])
                   ]
        run_process_and_write_output(command, subjects_dir)


def make_dense_scalp_surfaces(mri_subject, subjects_dir, overwrite):
    print('Making dense scalp surfacing easing co-registration for ' +
          'subject: ' + mri_subject +
          ". Output is written to the bem folder" +
          " of the subject's FreeSurfer folder.\n" +
          'Bash output follows below.\n\n')

    if overwrite:
        overwrite_string = '--overwrite'
    else:
        overwrite_string = ''

    command = ['mne', 'make_scalp_surfaces',
               '--subject', mri_subject,
               overwrite_string]

    run_process_and_write_output(command, subjects_dir)


# ==============================================================================
# MNE SOURCE RECONSTRUCTIONS
# ==============================================================================
@topline
def setup_src(mri_subject, subjects_dir, source_space_method, n_jobs,
              overwrite):
    src_name = mri_subject + '_' + source_space_method + '-src.fif'
    src_path = join(subjects_dir, mri_subject, 'bem', src_name)

    if overwrite or not isfile(src_path):
        src = mne.setup_source_space(mri_subject, spacing=source_space_method,
                                     surface='white', subjects_dir=subjects_dir,
                                     add_dist=False, n_jobs=n_jobs)
        src.save(src_path, overwrite=True)


@topline
def compute_src_distances(mri_subject, subjects_dir, source_space_method,
                          n_jobs):
    src = loading.read_source_space(mri_subject, subjects_dir, source_space_method)
    src_computed = mne.add_source_space_distances(src, n_jobs=n_jobs)

    src_name = mri_subject + '_' + source_space_method + '-src.fif'
    src_path = join(subjects_dir, mri_subject, 'bem', src_name)

    src_computed.save(src_path, overwrite=True)


@topline
def prepare_bem(mri_subject, subjects_dir):
    bem_model_name = mri_subject + '-bem.fif'
    bem_model_path = join(subjects_dir, mri_subject, 'bem', bem_model_name)
    model = mne.make_bem_model(mri_subject, conductivity=[0.3], subjects_dir=subjects_dir)
    mne.write_bem_surfaces(bem_model_path, model)
    print(bem_model_path + ' written')

    solution_name = mri_subject + '-bem-sol.fif'
    solution_path = join(subjects_dir, mri_subject, 'bem', solution_name)
    solution = mne.make_bem_solution(model)
    mne.write_bem_solution(solution_path, solution)
    print(solution_path + ' written')


@topline
def setup_vol_src(mri_subject, subjects_dir):
    bem = loading.read_bem_solution(mri_subject, subjects_dir)
    vol_src = mne.setup_volume_source_space(mri_subject, bem=bem, pos=5.0, subjects_dir=subjects_dir)
    vol_src_name = mri_subject + '-vol-src.fif'
    vol_src_path = join(subjects_dir, mri_subject, 'bem', vol_src_name)
    vol_src.save(vol_src_path, overwrite=True)


@topline
def morph_subject(mri_subject, subjects_dir, morph_to, source_space_method,
                  overwrite):
    morph_name = mri_subject + '--to--' + morph_to + '-' + source_space_method
    morph_path = join(subjects_dir, mri_subject, morph_name)

    src = loading.read_source_space(mri_subject, subjects_dir, source_space_method)

    morph = mne.compute_source_morph(src, subject_from=mri_subject,
                                     subject_to=morph_to, subjects_dir=subjects_dir)

    if overwrite or not isfile(morph_path):
        morph.save(morph_path, overwrite=True)
        print(f'{morph_path} written')


@topline
def morph_labels_from_fsaverage(mri_subject, subjects_dir, overwrite):
    parcellations = ['aparc_sub', 'HCPMMP1_combined', 'HCPMMP1']
    if not isfile(join(subjects_dir, 'fsaverage/label',
                       'lh.' + parcellations[0] + '.annot')):
        mne.datasets.fetch_hcp_mmp_parcellation(subjects_dir=subjects_dir,
                                                verbose=True)

        mne.datasets.fetch_aparc_sub_parcellation(subjects_dir=subjects_dir,
                                                  verbose=True)
    else:
        print('You\'ve already downloaded the parcellations, splendid!')

    if not isfile(join(subjects_dir, mri_subject, 'label',
                       'lh.' + parcellations[0] + '.annot')) or overwrite:
        for pc in parcellations:
            labels = mne.read_labels_from_annot('fsaverage', pc, hemi='both')

            m_labels = mne.morph_labels(labels, mri_subject, 'fsaverage', subjects_dir,
                                        surf_name='pial')

            mne.write_labels_to_annot(m_labels, subject=mri_subject, parc=pc,
                                      subjects_dir=subjects_dir, overwrite=True)

    else:
        print(f'{parcellations} already exist')


@topline
def create_forward_solution(name, save_dir, subtomri, subjects_dir,
                            source_space_method, overwrite, n_jobs, eeg_fwd):
    forward_name = name + '-fwd.fif'
    forward_path = join(save_dir, forward_name)

    if overwrite or not isfile(forward_path):

        info = loading.read_info(name, save_dir)
        trans = loading.read_transformation(save_dir, subtomri)
        bem = loading.read_bem_solution(subtomri, subjects_dir)
        source_space = loading.read_source_space(subtomri, subjects_dir, source_space_method)

        forward = mne.make_forward_solution(info, trans, source_space, bem,
                                            n_jobs=n_jobs, eeg=eeg_fwd)

        mne.write_forward_solution(forward_path, forward, overwrite)

    else:
        print('forward solution: ' + forward_path + ' already exists')


@topline
def estimate_noise_covariance(name, save_dir, highpass, lowpass,
                              overwrite, ermsub, data_path, baseline,
                              bad_channels, n_jobs, erm_noise_cov,
                              calm_noise_cov, enable_ica):
    if calm_noise_cov:

        print('Noise Covariance on 1-Minute-Calm')
        covariance_name = name + filter_string(highpass, lowpass) + '-clm-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            raw = loading.read_filtered(name, save_dir, highpass, lowpass)
            raw.crop(tmin=5, tmax=50)
            raw.pick_types(exclude=bad_channels)

            noise_covariance = mne.compute_raw_covariance(raw, n_jobs=n_jobs,
                                                          method='empirical')
            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: ' + covariance_path +
                  ' already exists')

    elif ermsub == 'None' or 'leer' in name or erm_noise_cov is False:

        print('Noise Covariance on Epochs')
        covariance_name = name + filter_string(highpass, lowpass) + '-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            if enable_ica:
                epochs = loading.read_ica_epochs(name, save_dir, highpass, lowpass)
            else:
                epochs = loading.read_epochs(name, save_dir, highpass, lowpass)

            tmin, tmax = baseline
            noise_covariance = mne.compute_covariance(epochs, tmin=tmin, tmax=tmax,
                                                      method='empirical', n_jobs=n_jobs)

            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: ' + covariance_path +
                  ' already exists')

    else:
        print('Noise Covariance on ERM')
        covariance_name = name + filter_string(highpass, lowpass) + '-erm-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            erm_name = ermsub + filter_string(highpass, lowpass) + '-raw.fif'
            erm_path = join(data_path, 'empty_room_data', ermsub, erm_name)

            erm = mne.io.read_raw_fif(erm_path, preload=True)
            erm.pick_types(exclude=bad_channels)

            noise_covariance = mne.compute_raw_covariance(erm, n_jobs=n_jobs,
                                                          method='empirical')
            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: ' + covariance_path +
                  ' already exists')


@topline
def create_inverse_operator(name, save_dir, highpass, lowpass,
                            overwrite, ermsub, calm_noise_cov, erm_noise_cov):
    inverse_operator_name = name + filter_string(highpass, lowpass) + '-inv.fif'
    inverse_operator_path = join(save_dir, inverse_operator_name)

    if overwrite or not isfile(inverse_operator_path):

        info = loading.read_info(name, save_dir)
        noise_covariance = loading.read_noise_covariance(name, save_dir, highpass, lowpass,
                                                         erm_noise_cov, ermsub, calm_noise_cov)

        forward = loading.read_forward(name, save_dir)

        inverse_operator = mne.minimum_norm.make_inverse_operator(info, forward, noise_covariance)

        mne.minimum_norm.write_inverse_operator(inverse_operator_path, inverse_operator)

    else:
        print('inverse operator file: ' + inverse_operator_path +
              ' already exists')


# noinspection PyShadowingNames
@topline
def source_estimate(name, save_dir, highpass, lowpass, inverse_method, overwrite):
    inverse_operator = loading.read_inverse_operator(name, save_dir, highpass, lowpass)
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)

    snr = 3.0
    lambda2 = 1.0 / snr ** 2

    for evoked in evokeds:
        trial_type = evoked.comment

        stc_name = name + filter_string(highpass, lowpass) + '_' + trial_type + '_' + inverse_method
        stc_path = join(save_dir, stc_name)
        if overwrite or not isfile(stc_path + '-lh.stc'):
            stc = mne.minimum_norm.apply_inverse(evoked, inverse_operator, lambda2, method=inverse_method)
            stc.save(stc_path)
        else:
            print('source estimates for: ' + name +
                  ' already exists')

        n_stc_name = name + filter_string(highpass, lowpass) + '_' + trial_type + '_' + inverse_method + '-normal'
        n_stc_path = join(save_dir, n_stc_name)
        if overwrite or not isfile(n_stc_path + '-lh.stc'):
            normal_stc = mne.minimum_norm.apply_inverse(evoked, inverse_operator, lambda2,
                                                        method=inverse_method, pick_ori='normal')
            normal_stc.save(n_stc_path)
        else:
            print('normal-source estimates for: ' + name +
                  ' already exists')


@topline
def vector_source_estimate(name, save_dir, highpass, lowpass, inverse_method, overwrite):
    inverse_operator = loading.read_inverse_operator(name, save_dir, highpass, lowpass)
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)

    snr = 3.0
    lambda2 = 1.0 / snr ** 2

    for evoked in evokeds:
        # Crop evoked to Time of Interest for Analysis
        trial_type = evoked.comment

        v_stc_name = name + filter_string(highpass, lowpass) + '_' + trial_type + '_' + inverse_method + '-vector'
        v_stc_path = join(save_dir, v_stc_name)
        if overwrite or not isfile(v_stc_path + '-stc.h5'):
            v_stc = mne.minimum_norm.apply_inverse(evoked, inverse_operator, lambda2,
                                                   method=inverse_method, pick_ori='vector')
            v_stc.save(v_stc_path)
        else:
            print('vector source estimates for: ' + name + ' already exists')


@topline
def mixed_norm_estimate(name, save_dir, highpass, lowpass, inverse_method, erm_noise_cov,
                        ermsub, calm_noise_cov, event_id, mixn_dip, overwrite):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)
    forward = loading.read_forward(name, save_dir)
    noise_cov = loading.read_noise_covariance(name, save_dir, highpass, lowpass,
                                              erm_noise_cov, ermsub, calm_noise_cov)
    inv_op = loading.read_inverse_operator(name, save_dir, highpass, lowpass)
    if inverse_method == 'dSPM':
        print('dSPM-Inverse-Solution existent, loading...')
        stcs = loading.read_source_estimates(name, save_dir, highpass, lowpass, inverse_method, event_id)
    else:
        print('No dSPM-Inverse-Solution available, calculating...')
        stcs = dict()
        snr = 3.0
        lambda2 = 1.0 / snr ** 2
        for evoked in evokeds:
            trial_type = evoked.comment
            stcs[trial_type] = mne.minimum_norm.apply_inverse(evoked, inv_op, lambda2, method='dSPM')
            stc_name = name + filter_string(highpass, lowpass) + '_' + trial_type + '_' + inverse_method
            stc_path = join(save_dir, stc_name)
            stcs[trial_type].save(stc_path)

    for evoked in evokeds:
        trial_type = evoked.comment
        alpha = 30  # regularization parameter between 0 and 100 (100 is high)
        n_mxne_iter = 10  # if > 1 use L0.5/L2 reweighted mixed norm solver
        # if n_mxne_iter > 1 dSPM weighting can be avoided.

        # Remove old dipoles
        if not exists(join(save_dir, 'dipoles')):
            makedirs(join(save_dir, 'dipoles'))
        old_dipoles = listdir(join(save_dir, 'dipoles'))
        for file in old_dipoles:
            remove(join(save_dir, 'dipoles', file))

        if mixn_dip:
            mixn, residual = mne.inverse_sparse.mixed_norm(evoked, forward, noise_cov, alpha,
                                                           maxit=3000, tol=1e-4, active_set_size=10, debias=True,
                                                           weights=stcs[trial_type], n_mxne_iter=n_mxne_iter,
                                                           return_residual=True, return_as_dipoles=True)

            for idx, dip in enumerate(mixn):
                mixn_dip_name = name + filter_string(highpass, lowpass) + '_' + trial_type + '-mixn-dip-' + str(idx)
                mixn_dip_path = join(save_dir, 'dipoles', mixn_dip_name)
                dip.save(mixn_dip_path)
        else:
            mixn, residual = mne.inverse_sparse.mixed_norm(evoked, forward, noise_cov, alpha,
                                                           maxit=3000, tol=1e-4, active_set_size=10, debias=True,
                                                           weights=stcs[trial_type], n_mxne_iter=n_mxne_iter,
                                                           return_residual=True, return_as_dipoles=True)

            mixn_stc_name = name + filter_string(highpass, lowpass) + '_' + trial_type + '-mixn'
            mixn_stc_path = join(save_dir, mixn_stc_name)
            if overwrite or not isfile(mixn_stc_path + '-lh.stc'):
                mixn.save(mixn_stc_path)
            else:
                print('mixed-norm source estimates for: ' + name +
                      ' already exists')

        mixn_res_name = name + filter_string(highpass, lowpass) + '_' + trial_type + '-mixn-res-ave.fif'
        mixn_res_path = join(save_dir, mixn_res_name)
        if overwrite or not isfile(mixn_res_path):
            residual.save(mixn_res_path)
        else:
            print('mixed-norm source estimate residual for: ' + name +
                  ' already exists')


# Todo: Separate Plot-Functions (better responsivness of GUI during fit, when running in QThread)
@topline
def ecd_fit(name, save_dir, highpass, lowpass, ermsub, subjects_dir,
            subtomri, erm_noise_cov, calm_noise_cov, ecds, save_plots, figures_path):
    try:
        ecd = ecds[name]

        evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)
        bem = loading.read_bem_solution(subtomri, subjects_dir)
        trans = loading.read_transformation(save_dir, subtomri)
        t1_path = loading.path_fs_volume('T1', subtomri, subjects_dir)

        noise_covariance = loading.read_noise_covariance(name, save_dir, highpass, lowpass,
                                                         erm_noise_cov, ermsub, calm_noise_cov)

        for evoked in evokeds:
            trial_type = evoked.comment
            for Dip in ecd:
                tmin, tmax = ecd[Dip]
                evoked_full = evoked.copy()
                cevk = evoked.copy().crop(tmin, tmax)

                dipole, data = mne.fit_dipole(cevk, noise_covariance, bem, trans,
                                              min_dist=3.0, n_jobs=4)

                figure = dipole.plot_locations(trans, subtomri, subjects_dir,
                                               mode='orthoview', idx='gof')
                plt.title(name, loc='right')

                # find time point with highest GOF to plot
                best_idx = np.argmax(dipole.gof)
                best_time = dipole.times[best_idx]

                print(f'Highest GOF {dipole.gof[best_idx]:.2f}% at t={best_time * 1000:.1f} ms with confidence volume'
                      f'{dipole.conf["vol"][best_idx] * 100 ** 3} cm^3')

                mri_pos = mne.head_to_mri(dipole.pos, subtomri, trans, subjects_dir)

                save_path_anat = join(figures_path, 'ECD', name +
                                      filter_string(highpass, lowpass) + '_' +
                                      cevk.comment + Dip + '_ECD_anat.jpg')

                plot_anat(t1_path, cut_coords=mri_pos[best_idx], output_file=save_path_anat,
                          title=name + '_' + cevk.comment + '_' + Dip,
                          annotate=True, draw_cross=True)

                plot_anat(t1_path, cut_coords=mri_pos[best_idx],
                          title=name + '_' + cevk.comment + '_' + Dip,
                          annotate=True, draw_cross=True)

                # remember to create a subplot for the colorbar
                """fig, axes = plt.subplots(nrows=1, ncols=4, figsize=[10., 3.4])
                # first plot the topography at the time of the best fitting (single) dipole
                plot_params = dict(times=best_time, ch_type='grad', outlines='skirt',
                                   colorbar=False, time_unit='s')
                cevk.plot_topomap(time_format='Measured field', axes=axes[0], **plot_params)
    
                pred_evoked.plot_topomap(time_format='Predicted field', axes=axes[1],
                                         **plot_params)"""

                if save_plots:
                    save_path = join(figures_path, 'ECD', trial_type, name +
                                     filter_string(highpass, lowpass) + '_' +
                                     cevk.comment + '_ECD_' + Dip + '.jpg')
                    figure.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

                # Subtract predicted from measured data (apply equal weights)
                """diff = mne.evoked.combine_evoked([cevk, -pred_evoked], weights='equal')
                plot_params['colorbar'] = True
                diff.plot_topomap(time_format='Difference', axes=axes[2], **plot_params)
                plt.suptitle('Comparison of measured and predicted fields '
                             'at {:.0f} ms'.format(best_time * 1000.), fontsize=16)"""

                dip_fixed = mne.fit_dipole(evoked_full, noise_covariance, bem, trans,
                                           pos=dipole.pos[best_idx], ori=dipole.ori[best_idx])[0]
                dip_fixed.plot(time_unit='s')

    except KeyError:
        print('No Dipole times assigned to this file')
        pass


# Todo: Not working, needs work (maybe shift in MNE-Examples-Package)
@topline
def label_power_phlck(name, save_dir, highpass, lowpass, baseline, tfr_freqs,
                      subtomri, target_labels, parcellation, event_id, n_jobs,
                      save_plots, figures_path):
    # Compute a source estimate per frequency band including and excluding the
    # evoked response
    n_cycles = [freq / 3. for freq in tfr_freqs]  # different number of cycle per frequency
    labels = mne.read_labels_from_annot(subtomri, parc=parcellation)
    inverse_operator = loading.read_inverse_operator(name, save_dir, highpass, lowpass)

    for ev_id in event_id:
        epochs = loading.read_epochs(name, save_dir, highpass, lowpass)[ev_id]
        # subtract the evoked response in order to exclude evoked activity
        epochs_induced = epochs.copy().subtract_evoked()

        for hemi in target_labels:
            for label in [lb for lb in labels if lb.name in target_labels[hemi]]:
                print(label.name)
                # compute the source space power and the inter-trial coherence
                #                power, itc = mne.minimum_norm.source_induced_power(
                #                    epochs, inverse_operator, freqs, label, baseline=baseline,
                #                    baseline_mode='percent', n_cycles=n_cycles, n_jobs=n_jobs)

                power_ind, itc_ind = mne.minimum_norm.source_induced_power(
                        epochs_induced, inverse_operator, tfr_freqs, label, baseline=baseline,
                        baseline_mode='percent', n_cycles=n_cycles, n_jobs=n_jobs)

                #                power = np.mean(power, axis=0)  # average over sources
                #                itc = np.mean(itc, axis=0)  # average over sources

                power_ind = np.mean(power_ind, axis=0)  # average over sources
                itc_ind = np.mean(itc_ind, axis=0)  # average over sources

                # power_path = join(save_dir, f'{name}_{label.name}_{filter_string(highpass, lowpass)}_{ev_id}_pw-tfr.npy')
                # itc_path = join(save_dir, f'{name}_{label.name}_{filter_string(highpass, lowpass)}_{ev_id}_itc-tfr.npy')
                power_ind_path = join(save_dir,
                                      f'{name}_{label.name}_{filter_string(highpass, lowpass)}_{ev_id}_pw-ind-tfr.npy')
                itc_ind_path = join(save_dir,
                                    f'{name}_{label.name}_{filter_string(highpass, lowpass)}_{ev_id}_itc-ind-tfr.npy')

                #                np.save(power_path, power)
                #                np.save(itc_path, itc)
                np.save(power_ind_path, power_ind)
                np.save(itc_ind_path, itc_ind)

                # Plot
                times = epochs.times

                plt.figure(figsize=(18, 8))
                plt.subplots_adjust(0.1, 0.08, 0.96, 0.94, 0.2, 0.43)
                plt.subplot(1, 2, 1)
                plt.imshow(20 * power_ind,
                           extent=[times[0], times[-1], tfr_freqs[0], tfr_freqs[-1]],
                           aspect='auto', origin='lower', vmin=0., vmax=10., cmap='RdBu_r')
                plt.xlabel('Time (s)')
                plt.ylabel('Frequency (Hz)')
                plt.title('Power induced')
                plt.colorbar()

                plt.subplot(1, 2, 2)
                plt.imshow(itc_ind,
                           extent=[times[0], times[-1], tfr_freqs[0], tfr_freqs[-1]],
                           aspect='auto', origin='lower', vmin=0, vmax=0.4,
                           cmap='RdBu_r')
                plt.xlabel('Time (s)')
                plt.ylabel('Frequency (Hz)')
                plt.title('ITC induced')
                plt.colorbar()

                #                plt.subplots_adjust(0.1, 0.08, 0.96, 0.94, 0.2, 0.43)
                #                plt.subplot(2, 2, 3)
                #                plt.imshow(20 * power_ind,
                #                           extent=[times[0], times[-1], freqs[0], freqs[-1]],
                #                           aspect='auto', origin='lower', vmin=0., vmax=10., cmap='RdBu_r')
                #                plt.xlabel('Time (s)')
                #                plt.ylabel('Frequency (Hz)')
                #                plt.title('Power induced')
                #                plt.colorbar()
                #
                #                plt.subplot(2, 2, 4)
                #                plt.imshow(itc_ind,
                #                           extent=[times[0], times[-1], freqs[0], freqs[-1]],
                #                           aspect='auto', origin='lower', vmin=0, vmax=0.4,
                #                           cmap='RdBu_r')
                #                plt.xlabel('Time (s)')
                #                plt.ylabel('Frequency (Hz)')
                #                plt.title('ITC induced')
                #                plt.colorbar()

                plt.show()

                if save_plots:
                    save_path = join(figures_path, 'tf_source_space/label_power',
                                     name + '_' + label.name + '_power_' +
                                     ev_id + filter_string(highpass, lowpass) + '.jpg')
                    plt.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

                plot.close_all()


@topline
def apply_morph(name, save_dir, highpass, lowpass, subjects_dir, subtomri,
                inverse_method, overwrite, morph_to, source_space_method,
                event_id):
    stcs = loading.read_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                         event_id)
    morph = loading.read_morph(subtomri, morph_to, source_space_method, subjects_dir)

    for trial_type in stcs:
        stc_morphed_name = name + filter_string(highpass, lowpass) + '_' + \
                           trial_type + '_' + inverse_method + '_morphed'
        stc_morphed_path = join(save_dir, stc_morphed_name)

        if overwrite or not isfile(stc_morphed_path + '-lh.stc'):
            stc_morphed = morph.apply(stcs[trial_type])
            stc_morphed.save(stc_morphed_path)

        else:
            print('morphed source estimates for: ' + stc_morphed_path +
                  ' already exists')


@topline
def apply_morph_normal(name, save_dir, highpass, lowpass, subjects_dir, subtomri,
                       inverse_method, overwrite, morph_to, source_space_method,
                       event_id):
    stcs = loading.read_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                                event_id)
    morph = loading.read_morph(subtomri, morph_to, source_space_method, subjects_dir)

    for trial_type in stcs:
        stc_morphed_name = name + filter_string(highpass, lowpass) + '_' + \
                           trial_type + '_' + inverse_method + '_morphed_normal'
        stc_morphed_path = join(save_dir, stc_morphed_name)

        if overwrite or not isfile(stc_morphed_path + '-lh.stc'):
            stc_morphed = morph.apply(stcs[trial_type])
            stc_morphed.save(stc_morphed_path)

        else:
            print('morphed source estimates for: ' + stc_morphed_path +
                  ' already exists')


@topline
def source_space_connectivity(name, save_dir, highpass, lowpass,
                              subtomri, subjects_dir, parcellation,
                              target_labels, con_methods, con_fmin, con_fmax,
                              n_jobs, overwrite, enable_ica, event_id):
    info = loading.read_info(name, save_dir)
    if enable_ica:
        all_epochs = loading.read_ica_epochs(name, save_dir, highpass, lowpass)
    else:
        all_epochs = loading.read_epochs(name, save_dir, highpass, lowpass)
    inverse_operator = loading.read_inverse_operator(name, save_dir, highpass, lowpass)
    src = inverse_operator['src']

    for ev_id in event_id:
        epochs = all_epochs[ev_id]
        # Compute inverse solution and for each epoch. By using "return_generator=True"
        # stcs will be a generator object instead of a list.
        snr = 1.0  # use lower SNR for single epochs
        lambda2 = 1.0 / snr ** 2
        inverse_method = "dSPM"  # use dSPM inverse_method (could also be MNE or sLORETA)
        stcs = mne.minimum_norm.apply_inverse_epochs(epochs, inverse_operator, lambda2, inverse_method,
                                                     pick_ori="normal", return_generator=True)

        # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
        labels = mne.read_labels_from_annot(subtomri, parc=parcellation,
                                            subjects_dir=subjects_dir)

        actual_labels = [lb for lb in labels if lb.name in target_labels['lh']
                         or lb.name in target_labels['rh']]

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
        con_res = dict()
        for con_method, c in zip(con_methods, con):
            con_res[con_method] = c

            # save to .npy file
            file_name = name + filter_string(highpass, lowpass) + \
                        '_' + str(con_fmin) + '-' + str(con_fmax) + '_' + con_method \
                        + '-' + ev_id
            file_path = join(save_dir, file_name)
            if overwrite or not isfile(file_path):
                np.save(file_path, con_res[con_method])
            else:
                print('connectivity_measures for for: ' + file_path +
                      ' already exists')


@topline
def grand_avg_morphed(grand_avg_dict, sel_ga_groups, data_path, inverse_method, save_dir_averages,
                      highpass, lowpass, event_id):
    # for less memory only import data from stcs and add it to one fsaverage-stc in the end!!!
    n_chunks = 8
    for key in grand_avg_dict:
        if key in sel_ga_groups:
            print(f'grand_average for {key}')
            # divide in chunks to save memory
            fusion_dict = {}
            for i in range(0, len(grand_avg_dict[key]), n_chunks):
                sub_trial_dict = {}
                ga_chunk = grand_avg_dict[key][i:i + n_chunks]
                print(ga_chunk)
                for name in ga_chunk:
                    save_dir = join(data_path, name)
                    print(f'Add {name} to grand_average')
                    stcs = loading.read_morphed_source_estimates(name, save_dir, highpass,
                                                                 lowpass, inverse_method, event_id)
                    for trial_type in stcs:
                        if trial_type in sub_trial_dict:
                            sub_trial_dict[trial_type].append(stcs[trial_type])
                        else:
                            sub_trial_dict.update({trial_type: [stcs[trial_type]]})

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

            for trial in fusion_dict:
                if len(fusion_dict[trial]) != 0:
                    print(f'grand_average for {key}-{trial}')
                    trial_average = fusion_dict[trial][0].copy()
                    n_subjects = len(fusion_dict[trial])

                    for trial_index in range(1, n_subjects):
                        trial_average.data += fusion_dict[trial][trial_index].data

                    trial_average.data /= n_subjects
                    trial_average.comment = trial
                    ga_path = join(save_dir_averages, 'stc',
                                   key + '_' + trial +
                                   filter_string(highpass, lowpass) +
                                   '-grand_avg')
                    trial_average.save(ga_path)
            # clear memory
            gc.collect()


@topline
def grand_avg_normal_morphed(grand_avg_dict, data_path, inverse_method, save_dir_averages,
                             highpass, lowpass, event_id):
    # for less memory only import data from stcs and add it to one fsaverage-stc in the end!!!
    n_chunks = 8
    for key in grand_avg_dict:
        print(f'grand_average for {key}')
        # divide in chunks to save memory
        fusion_dict = {}
        for i in range(0, len(grand_avg_dict[key]), n_chunks):
            sub_trial_dict = {}
            ga_chunk = grand_avg_dict[key][i:i + n_chunks]
            print(ga_chunk)
            for name in ga_chunk:
                save_dir = join(data_path, name)
                print(f'Add {name} to grand_average')
                stcs = loading.read_morphed_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                                                    event_id)
                for trial_type in stcs:
                    if trial_type in sub_trial_dict:
                        sub_trial_dict[trial_type].append(stcs[trial_type])
                    else:
                        sub_trial_dict.update({trial_type: [stcs[trial_type]]})

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

        for trial in fusion_dict:
            if len(fusion_dict[trial]) != 0:
                print(f'grand_average for {key}-{trial}')
                trial_average = fusion_dict[trial][0].copy()
                n_subjects = len(fusion_dict[trial])

                for trial_index in range(1, n_subjects):
                    trial_average.data += fusion_dict[trial][trial_index].data

                trial_average.data /= n_subjects
                trial_average.comment = trial
                ga_path = join(save_dir_averages, 'stc',
                               key + '_' + trial +
                               filter_string(highpass, lowpass) +
                               '-grand_avg-normal')
                trial_average.save(ga_path)
        # clear memory
        gc.collect()


@topline
def grand_avg_label_power(grand_avg_dict, event_id,
                          data_path, highpass, lowpass,
                          target_labels, save_dir_averages):
    for key in grand_avg_dict:
        powers_ind = {}
        itcs_ind = {}

        for ev_id in event_id:
            powers_ind.update({ev_id: {}})
            itcs_ind.update({ev_id: {}})
            for hemi in target_labels:
                for label_name in target_labels[hemi]:
                    powers_ind[ev_id].update({label_name: []})
                    itcs_ind[ev_id].update({label_name: []})

        for name in grand_avg_dict[key]:
            save_dir = join(data_path, name)
            power_dict = loading.read_label_power(name, save_dir, highpass, lowpass,
                                                  event_id, target_labels)
            for ev_id in event_id:
                for hemi in target_labels:
                    for label_name in target_labels[hemi]:
                        powers_ind[ev_id][label_name].append(power_dict[ev_id][label_name]['power_ind'])
                        itcs_ind[ev_id][label_name].append(power_dict[ev_id][label_name]['itc_ind'])
        for ev_id in event_id:
            for hemi in target_labels:
                for label_name in target_labels[hemi]:
                    len_power = len(powers_ind[ev_id][label_name])
                    power_average = powers_ind[ev_id][label_name][0]
                    for n in range(1, len_power):
                        power_average += powers_ind[ev_id][label_name][n]
                    power_average /= len_power

                    pw_ga_path = join(save_dir_averages, 'tfr',
                                      f'{key}-{ev_id}_{label_name}_pw-ind.npy')

                    np.save(pw_ga_path, power_average)

                    len_itc = len(itcs_ind[ev_id][label_name])
                    itc_average = itcs_ind[ev_id][label_name][0]
                    for n in range(1, len_itc):
                        itc_average += itcs_ind[ev_id][label_name][n]
                    itc_average /= len_itc

                    itc_ga_path = join(save_dir_averages, 'tfr',
                                       f'{key}-{ev_id}_{label_name}_itc-ind.npy')

                    np.save(itc_ga_path, itc_average)


@topline
def grand_avg_connect(grand_avg_dict, data_path, con_methods,
                      con_fmin, con_fmax, save_dir_averages,
                      highpass, lowpass, event_id):
    for key in grand_avg_dict:
        for ev_id in event_id:
            con_methods_dict = {}
            print(f'grand_average for {key}')
            for name in grand_avg_dict[key]:
                save_dir = join(data_path, name)
                print(f'Add {name} to grand_average')

                con_dict = loading.read_connect(name, save_dir, highpass,
                                                lowpass, con_methods,
                                                con_fmin, con_fmax, event_id)[ev_id]

                for con_method in con_dict:
                    if con_method in con_methods_dict:
                        con_methods_dict[con_method].append(con_dict[con_method])
                    else:
                        con_methods_dict.update({con_method: [con_dict[con_method]]})

            for inverse_method in con_methods_dict:
                if len(con_methods_dict[inverse_method]) != 0:
                    print(f'grand_average for {key}-{inverse_method}')
                    con_list = con_methods_dict[inverse_method]
                    n_subjects = len(con_list)
                    average = con_list[0]
                    for idx in range(1, n_subjects):
                        average += con_list[idx]

                    average /= n_subjects

                    ga_path = join(save_dir_averages, 'connect',
                                   key + '_' + inverse_method +
                                   filter_string(highpass, lowpass) +
                                   '-grand_avg_connect' + '-' + ev_id)
                    np.save(ga_path, average)


# ==============================================================================
# STATISTICS
# ==============================================================================
@topline
def statistics_source_space(morphed_data_all, save_dir_averages,
                            independent_variable_1,
                            independent_variable_2,
                            time_window, n_permutations, highpass, lowpass, overwrite):
    cluster_name = independent_variable_1 + '_vs_' + independent_variable_2 + \
                   filter_string(highpass, lowpass) + '_time_' + \
                   str(int(time_window[0] * 1e3)) + '-' + \
                   str(int(time_window[1] * 1e3)) + '_msec.cluster'
    cluster_path = join(save_dir_averages, 'statistics', cluster_name)

    if overwrite or not isfile(cluster_path):

        input_data = dict(iv_1=morphed_data_all[independent_variable_1],
                          iv_2=morphed_data_all[independent_variable_2])
        info_data = morphed_data_all[independent_variable_1]
        n_subjects = len(info_data)
        n_sources, n_samples = info_data[0].data.shape

        # get data in the right format
        statistics_data_1 = np.zeros((n_subjects, n_sources, n_samples))
        statistics_data_2 = np.zeros((n_subjects, n_sources, n_samples))

        for subject_index in range(n_subjects):
            statistics_data_1[subject_index, :, :] = input_data['iv_1'][subject_index].data
            statistics_data_2[subject_index, :, :] = input_data['iv_2'][subject_index].data
            print('processing data from subject: ' + str(subject_index))

        # crop data on the time dimension
        times = info_data[0].times
        time_indices = np.logical_and(times >= time_window[0],
                                      times <= time_window[1])

        statistics_data_1 = statistics_data_1[:, :, time_indices]
        statistics_data_2 = statistics_data_2[:, :, time_indices]

        # set up cluster analysis
        p_threshold = 0.05
        t_threshold = stats.distributions.t.ppf(1 - p_threshold / 2, n_subjects - 1)
        seed = 7  # my lucky number

        statistics_list = [statistics_data_1, statistics_data_2]

        t_obs, clusters, cluster_p_values, h0 = mne.stats.permutation_cluster_test(statistics_list,
                                                                                   n_permutations=n_permutations,
                                                                                   threshold=t_threshold,
                                                                                   seed=seed,
                                                                                   n_jobs=-1)

        cluster_dict = dict(t_obs=t_obs, clusters=clusters,
                            cluster_p_values=cluster_p_values, h0=h0)

        with open(cluster_path, 'wb') as filename:
            pickle.dump(cluster_dict, filename)

        print('finished saving cluster at path: ' + cluster_path)

    else:
        print('cluster permutation: ' + cluster_path +
              ' already exists')
