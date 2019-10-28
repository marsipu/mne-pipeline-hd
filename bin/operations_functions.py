# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data - operations functions
@author: Lau Møller Andersen
@email: lau.moller.andersen@ki.se | lau.andersen@cnru.dk
@github: https://github.com/ualsbombe/omission_frontiers.git

Edited by Martin Schulz
martin@stud.uni-heidelberg.de
"""
from __future__ import print_function

import mne
import numpy as np
from os.path import join, isfile, isdir, exists
from scipy import stats, signal
from os import makedirs, listdir, environ, remove
import sys
from . import io_functions as io
from . import plot_functions as plot
from . import utilities as ut
from . import decorators as decor
import pickle
import subprocess
from collections import Counter
from nilearn.plotting import plot_anat
from matplotlib import pyplot as plt
from mayavi import mlab
from itertools import combinations
from functools import reduce
from surfer import Brain
import random
import gc
import statistics as st
import re

try:
    from autoreject import AutoReject
except ImportError:
    print('#%§&$$ autoreject-Import-Bug is not corrected in latest dev')
    AutoReject = 0


# Naming Conventions
def filter_string(lowpass, highpass):
    if highpass is not None and highpass != 0:
        fs = '_' + str(highpass) + '-' + str(lowpass) + '_Hz'
    else:
        fs = '_' + str(lowpass) + '_Hz'

    return fs


# ==============================================================================
# OPERATING SYSTEM COMMANDS
# ==============================================================================
def populate_directories(data_path, figures_path, event_id):
    # create grand averages path with a statistics folder
    ga_folders = ['statistics', 'evoked', 'stc', 'tfr', 'connect']
    for subfolder in ga_folders:
        grand_average_path = join(data_path, 'grand_averages', subfolder)
        if not exists(grand_average_path):
            makedirs(grand_average_path)
            print(grand_average_path + ' has been created')

    # create erm(empty_room_measurements)paths
    erm_path = join(data_path, 'empty_room_data')
    if not exists(erm_path):
        makedirs(erm_path)
        print(erm_path + ' has been created')

    # create figures path
    folders = ['epochs', 'epochs_image', 'epochs_topo', 'evoked_image',
               'power_spectra_raw', 'power_spectra_epochs',
               'power_spectra_topo', 'evoked_butterfly', 'evoked_field',
               'evoked_topo', 'evoked_topomap', 'evoked_joint', 'evoked_white', 'gfp',
               'ica', 'ssp', 'stcs', 'vec_stcs', 'mxne', 'transformation', 'source_space',
               'noise_covariance', 'events', 'label_time_course', 'ECD',
               'stcs_movie', 'bem', 'snr', 'statistics', 'correlation_ntr',
               'labels', 'tf_sensor_space/plot', 'tf_source_space/label_power',
               'tf_sensor_space/topo', 'tf_sensor_space/joint',
               'tf_sensor_space/oscs', 'tf_sensor_space/itc',
               'tf_sensor_space/dynamics', 'tf_source_space/connectivity',
               'epochs_drop_log', 'func_labels', 'evoked_h1h2', 'Various',
               'sensitivity_maps', 'mxn_dipoles']

    for folder in folders:
        folder_path = join(figures_path, folder)
        if not exists(folder_path):
            makedirs(folder_path)
            print(folder_path + ' has been created')

        # create erm_figure
        erm_folders = join(figures_path, 'ERM_Figures', folder)
        if not exists(erm_folders):
            makedirs(erm_folders)
            print(erm_folders + ' has been created')

    # create subfolders for for event_ids
    trialed_folders = ['epochs', 'power_spectra_epochs', 'power_spectra_topo',
                       'epochs_image', 'epochs_topo', 'evoked_butterfly',
                       'evoked_field', 'evoked_topomap', 'evoked_image',
                       'evoked_joint', 'evoked_white', 'gfp', 'label_time_course', 'ECD',
                       'stcs', 'vec_stcs', 'stcs_movie', 'snr',
                       'tf_sensor_space/plot', 'tf_sensor_space/topo',
                       'tf_sensor_space/joint', 'tf_sensor_space/oscs',
                       'tf_sensor_space/itc', 'evoked_h1h2', 'mxn_dipoles']

    for ev_id in event_id:
        for tr in trialed_folders:
            subfolder = join(figures_path, tr, ev_id)
            if not exists(subfolder):
                makedirs(subfolder)
                print(subfolder + ' has been created')

            # for erm
            erm_subfolder = join(figures_path, 'ERM_Figures', tr, ev_id)
            if not exists(erm_subfolder):
                makedirs(erm_subfolder)
                print(erm_subfolder + ' has been created')

    # create grand average figures path
    grand_averages_figures_path = join(figures_path, 'grand_averages')
    figure_subfolders = ['sensor_space/evoked', 'sensor_space/tfr',
                         'source_space/statistics', 'source_space/stc',
                         'source_space/connectivity', 'source_space/stc_movie',
                         'source_space/tfr']

    for figure_subfolder in figure_subfolders:
        folder_path = join(grand_averages_figures_path, figure_subfolder)
        if not exists(folder_path):
            makedirs(folder_path)
            print(folder_path + ' has been created')


# ==============================================================================
# PREPROCESSING AND GETTING TO EVOKED AND TFR
# ==============================================================================
@decor.topline
def filter_raw(name, save_dir, lowpass, highpass, ermsub,
               data_path, n_jobs, enable_cuda, bad_channels, erm_t_limit,
               enable_ica, eog_digitized):
    filter_name = name + filter_string(lowpass, highpass) + '-raw.fif'
    filter_path = join(save_dir, filter_name)

    ica_filter_name = name + filter_string(lowpass, 1) + '-raw.fif'
    ica_filter_path = join(save_dir, ica_filter_name)

    if not isfile(filter_path) or not isfile(ica_filter_path):
        raw = io.read_raw(name, save_dir)
    else:
        raw = None

    if not isfile(filter_path):
        if enable_cuda:  # use cuda for filtering
            n_jobs = 'cuda'
        raw.filter(highpass, lowpass, n_jobs=n_jobs)

        filter_name = name + filter_string(lowpass, highpass) + '-raw.fif'
        filter_path = join(save_dir, filter_name)

        # Save some data in the info-dictionary and finally save it
        raw.info['description'] = name
        raw.info['bads'] = bad_channels

        eeg_in_data = False
        for ch in raw.info['chs']:
            if ch['kind'] == 2:
                eeg_in_data = True

        if eog_digitized and eeg_in_data:
            digi = raw.info['dig']
            if len(digi) >= 108:
                if digi[-1]['kind'] != 3:
                    for i in digi[-4:]:
                        i['kind'] = 3
                    raw.info['dig'] = digi
                    print('Set EOG-Digitization-Points to kind 3 and saved')
                else:
                    print('EOG-Digitization-Points already set to kind 3')

        raw.save(filter_path, overwrite=True)

    else:
        print(f'raw file with Highpass = {highpass} Hz and Lowpass = {lowpass} Hz already exists')
        print('NO OVERWRITE FOR FILTERING, please change settings or delete files for new methods')

    # Make Raw-Version with 1 Hz Highpass-Filter if not existent
    if enable_ica and highpass < 1:
        ica_filter_name = name + filter_string(lowpass, 1) + '-raw.fif'
        ica_filter_path = join(save_dir, ica_filter_name)

        if not isfile(ica_filter_path):
            if enable_cuda:  # use cuda for filtering
                n_jobs = 'cuda'
            raw.filter(1, lowpass, n_jobs=n_jobs)

            filter_name = name + filter_string(lowpass, 1) + '-raw.fif'
            filter_path = join(save_dir, filter_name)

            # Save some data in the info-dictionary and finally save it
            raw.info['description'] = name
            raw.info['bads'] = bad_channels

            raw.save(filter_path, overwrite=True)

        else:
            print(f'raw file with Highpass = {1} Hz and Lowpass = {lowpass} Hz already exists')
            print('NO OVERWRITE FOR FILTERING, please change settings or delete files for new methods')

    if ermsub != 'None':
        erm_name = ermsub + '-raw.fif'
        erm_path = join(data_path, 'empty_room_data', erm_name)
        erm_filter_name = ermsub + filter_string(lowpass, highpass) + '-raw.fif'
        erm_filter_path = join(data_path, 'empty_room_data', erm_filter_name)

        if not isfile(erm_filter_path):
            raw = io.read_raw(name, save_dir)
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


@decor.topline
def find_events(name, save_dir, adjust_timeline_by_msec, lowpass, highpass, overwrite,
                exec_ops):
    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)

    if exec_ops['erm_analysis']:
        print('No events for erm-data')
        return

    if overwrite or not isfile(events_path):

        try:
            raw = io.read_filtered(name, save_dir, lowpass, highpass)
        except FileNotFoundError:
            raw = io.read_raw(name, save_dir)

        # By Martin Schulz
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


@decor.topline
def find_events_pp(name, save_dir, adjust_timeline_by_msec, lowpass, highpass, overwrite,
                   sub_script_path, save_plots, figures_path, exec_ops):
    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)

    if exec_ops['erm_analysis']:
        print('No events for erm-data')
        return

    if overwrite or not isfile(events_path):

        try:
            raw = io.read_filtered(name, save_dir, lowpass, highpass)
        except FileNotFoundError:
            raw = io.read_raw(name, save_dir)

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

        """#test events evs = [np.array([1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47,49,51,53,
        55,57,59,61,63])*10, np.array([2,3,6,7,10,11,14,15,18,19,22,23,26,27,30,31,34,35,38,39,42,43,46,47,50,51,54,
        55,58,59,62,63])*10, np.array([4,5,6,7,12,13,14,15,20,21,22,23,28,29,30,31,36,37,38,39,44,45,46,47,52,53,54,
        55,60,61,62,63])*10, np.array([8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,40,41,42,43,44,45,46,47,56,57,
        58,59,60,61,62,63])*10, np.array([16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,48,49,50,51,52,53,54,55,56,
        57,58,59,60,61,62,63])*10, np.array([32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,
        56,57,58,59,60,61,62,63])*10] """

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

        # delete Trigger 1 if not after Trigger 2 (due to mistake with light-barrier)
        removes = np.array([], dtype=int)
        for n in range(len(events)):
            if events[n, 2] == 1:
                if events[n - 1, 2] != 2:
                    removes = np.append(removes, n)
                    print(f'{events[n, 0]} removed Trigger 1')
        events = np.delete(events, removes, axis=0)

        # Rating
        pre_ratings = events[np.nonzero(np.logical_and(9 < events[:, 2], events[:, 2] < 20))]
        if len(pre_ratings) != 0:
            first_idx = np.nonzero(np.diff(pre_ratings[:, 0], axis=0) < 200)[0]
            last_idx = first_idx + 1
            ratings = pre_ratings[first_idx]
            ratings[:, 2] = (ratings[:, 2] - 10) * 10 + pre_ratings[last_idx][:, 2] - 10

            diff_ratings = np.copy(ratings)
            diff_ratings[np.nonzero(np.diff(ratings[:, 2]) < 0)[0] + 1, 2] = 5
            diff_ratings[np.nonzero(np.diff(ratings[:, 2]) == 0)[0] + 1, 2] = 6
            diff_ratings[np.nonzero(np.diff(ratings[:, 2]) > 0)[0] + 1, 2] = 7
            diff_ratings = np.delete(diff_ratings, [0], axis=0)

            pre_events = events[np.nonzero(events[:, 2] == 1)][:, 0]
            for n in range(len(diff_ratings)):
                diff_ratings[n, 0] = pre_events[np.nonzero(pre_events - diff_ratings[n, 0] < 0)][-1] + 3

            # Eliminate Duplicates
            diff_removes = np.array([], dtype=int)
            for n in range(1, len(diff_ratings)):
                if diff_ratings[n, 0] == diff_ratings[n - 1, 0]:
                    diff_removes = np.append(diff_removes, n)
                    print(f'{diff_ratings[n, 0]} removed as Duplicate')
            diff_ratings = np.delete(diff_ratings, diff_removes, axis=0)

            events = np.append(events, diff_ratings, axis=0)
            events = events[events[:, 0].argsort()]

            if save_plots:
                fig, ax1 = plt.subplots(figsize=(20, 10))
                ax1.plot(ratings[:, 2], 'b')
                ax1.set_ylim(0, 100)

                ax2 = ax1.twinx()
                ax2.plot(diff_ratings, 'og')
                ax2.set_ylim(4.5, 7.5)

                fig.tight_layout()
                plt.title(name + ' - rating')
                fig.show()

                save_path = join(figures_path, 'events', name + '-ratings.jpg')
                fig.savefig(save_path, dpi=600, overwrite=True)
                print('figure: ' + save_path + ' has been saved')

                plt.close(fig)
            else:
                print('Not saving plots; set "save_plots" to "True" to save')

        else:
            print('No Rating in Trig-Channels 10-19')

        # apply custom latency correction
        events[:, 0] = [ts + np.round(adjust_timeline_by_msec * 10 ** -3 *
                                      raw.info['sfreq']) for ts in events[:, 0]]

        # Calculate and Save Latencies
        l1 = []
        l2 = []
        for x in range(np.size(events, axis=0)):
            if events[x, 2] == 2:
                if events[x + 1, 2] == 1:
                    l1.append(events[x + 1, 0] - events[x, 0])
        diff1_mean = st.mean(l1)
        diff1_stdev = st.stdev(l1)
        ut.dict_filehandler(name, 'MotStart-LBT_diffs',
                            sub_script_path, values={'mean': diff1_mean,
                                                     'stdev': diff1_stdev})

        if exec_ops['motor_erm_analysis']:
            for x in range(np.size(events, axis=0) - 3):
                if events[x, 2] == 2:
                    if events[x + 2, 2] == 4:
                        l2.append(events[x + 2, 0] - events[x, 0])
            diff2_mean = st.mean(l2)
            diff2_stdev = st.stdev(l2)
            ut.dict_filehandler(name, 'MotStart1-MotStart2_diffs',
                                sub_script_path, values={'mean': diff2_mean,
                                                         'stdev': diff2_stdev})
        else:
            for x in range(np.size(events, axis=0) - 3):
                if events[x, 2] == 2:
                    if events[x + 3, 2] == 4:
                        l2.append(events[x + 3, 0] - events[x, 0])
            diff2_mean = st.mean(l2)
            diff2_stdev = st.stdev(l2)
            ut.dict_filehandler(name, 'MotStart1-MotStart2_diffs',
                                sub_script_path, values={'mean': diff2_mean,
                                                         'stdev': diff2_stdev})

        # Latency-Correction for Offset-Trigger[4]
        for x in range(np.size(events, axis=0) - 3):
            if events[x, 2] == 2:
                if events[x + 1, 2] == 1:
                    if events[x + 3, 2] == 4:
                        corr = diff1_mean - (events[x + 1, 0] - events[x, 0])
                        events[x + 3, 0] = events[x + 3, 0] + corr

        # unique event_ids
        ids = np.unique(events[:, 2])
        print('unique ID\'s assigned: ', ids)

        if np.size(events) > 0:
            mne.event.write_events(events_path, events)
        else:
            print('No events found')

    else:
        print('event file: ' + events_path + ' already exists')


@decor.topline
def find_eog_events(name, save_dir, eog_channel):
    eog_events_name = name + '_eog-eve.fif'
    eog_events_path = join(save_dir, eog_events_name)

    raw = io.read_raw(name, save_dir)
    eog_events = mne.preprocessing.find_eog_events(raw, ch_name=eog_channel)

    mne.event.write_events(eog_events_path, eog_events)

    # noinspection PyTypeChecker
    print(f'{np.size(eog_events)} detected')

    """"
    # quantitative analaysy of epoch contamination by eog-events
    # before epoch rejection

    events = io.read_events(name, save_dir)
    counter = 0
    all = np.append(events, eog_events, axis=0)
    all.sort(0)

    for n in range(0,np.size(eog_events,0)):
        if np.any(eog_events[n,0]-events[:,0]<500):# if one eog_event occurs 500ms or less after an event
            if np.any(eog_events[n,0]-events[:,0]>0):
                counter + 1

    contam = counter/np.size(events,0) * 100
    eog_contamination.update({name:contam})

    print(f'{contam} % of the epochs contaminated with eog events 500ms after the event')
    """


@decor.topline
def epoch_raw(name, save_dir, lowpass, highpass, event_id, tmin, tmax,
              baseline, reject, flat, autoreject, overwrite_ar,
              sub_script_path, bad_channels, decim,
              reject_eog_epochs, overwrite, exec_ops):
    epochs_name = name + filter_string(lowpass, highpass) + '-epo.fif'
    epochs_path = join(save_dir, epochs_name)
    if overwrite or not isfile(epochs_path):

        raw = io.read_filtered(name, save_dir, lowpass, highpass)
        raw.info['bads'] = bad_channels

        if exec_ops['erm_analysis']:
            # create some artificial events similar to those in motor-erm
            n_times = raw.n_times
            sfreq = raw.info['sfreq']
            step = (n_times - 10 * sfreq) / 200  # Numer of events in motor_erm
            events = np.ndarray((200, 3), dtype='int32')
            times = np.arange(5 * sfreq, n_times - 5 * sfreq, step)[:200]
            events[:, 0] = times
            events[:, 1] = 0
            events[:, 2] = 1
        else:
            events = io.read_events(name, save_dir)

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
            eog_events = io.read_eog_events(name, save_dir)

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

        epochs = mne.Epochs(raw, events, actual_event_id, tmin, tmax, baseline,
                            preload=True, picks=picks, proj=False, reject=None,
                            decim=decim, on_missing='ignore', reject_by_annotation=True)

        if autoreject:
            reject = ut.autoreject_handler(name, epochs, highpass, lowpass, sub_script_path, overwrite_ar=overwrite_ar)

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
                            sub_script_path, values=c)

    else:
        print('epochs file: ' + epochs_path + ' already exists')


@decor.topline
def run_ssp_er(name, save_dir, lowpass, highpass, data_path, ermsub, bad_channels,
               overwrite):
    if ermsub == 'None':
        print('no empty_room_data found for' + name)
        pass
    else:
        erm_name = ermsub + filter_string(lowpass, highpass) + '-raw.fif'
        erm_path = join(data_path, 'empty_room_data', erm_name)

        erm = mne.io.read_raw_fif(erm_path, preload=True)
        erm.pick_types(exclude=bad_channels)
        ssp_proj = mne.compute_proj_raw(erm)

        proj_name = name + '_ssp-proj.fif'
        proj_path = join(save_dir, proj_name)

        if overwrite or not isfile(proj_path):
            mne.write_proj(proj_path, ssp_proj)

            print(proj_name + ' written')
        else:
            print(proj_name + ' already exists')


@decor.topline
def apply_ssp_er(name, save_dir, lowpass, highpass, overwrite):
    proj_name = name + '_ssp-proj.fif'
    proj_path = join(save_dir, proj_name)

    if not isfile(proj_path):
        print('no ssp_proj_file found for' + name)
        pass
    else:
        projs = mne.read_proj(proj_path)
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)

        ssp_epochs_name = name + filter_string(lowpass, highpass) + '-ssp-epo.fif'
        ssp_epochs_path = join(save_dir, ssp_epochs_name)

        if overwrite or not isfile(ssp_epochs_path):

            epochs.add_proj(projs)
            epochs.save(ssp_epochs_path)

        else:
            print('ssp_epochs file: ' + ssp_epochs_path + ' already exists')


@decor.topline
def run_ssp_clm(name, save_dir, lowpass, highpass, bad_channels, overwrite):
    raw = io.read_filtered(name, save_dir, lowpass, highpass)
    raw.pick_types(exclude=bad_channels)
    raw.crop(tmin=5, tmax=50)

    ssp_proj = mne.compute_proj_raw(raw)

    proj_name = name + '_ssp_clm-proj.fif'
    proj_path = join(save_dir, proj_name)

    if overwrite or not isfile(proj_path):
        mne.write_proj(proj_path, ssp_proj)

        print(proj_name + ' written')
    else:
        print(proj_name + ' already exists')


@decor.topline
def apply_ssp_clm(name, save_dir, lowpass, highpass, overwrite):
    proj_name = name + '_ssp_clm-proj.fif'
    proj_path = join(save_dir, proj_name)

    if not isfile(proj_path):
        print('no ssp_proj_file found for' + name)
        pass
    else:
        projs = mne.read_proj(proj_path)
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)

        ssp_epochs_name = name + filter_string(lowpass, highpass) + '-ssp_clm-epo.fif'
        ssp_epochs_path = join(save_dir, ssp_epochs_name)

        if overwrite or not isfile(ssp_epochs_path):

            epochs.add_proj(projs)
            epochs.save(ssp_epochs_path)

        else:
            print('ssp_epochs file: ' + ssp_epochs_path + ' already exists')


@decor.topline
def run_ssp_eog(name, save_dir, n_jobs, eog_channel,
                bad_channels, overwrite):
    info = io.read_info(name, save_dir)
    eog_events_name = name + '_eog-eve.fif'
    eog_events_path = join(save_dir, eog_events_name)

    if eog_channel in info['ch_names']:
        raw = io.read_raw(name, save_dir)

        eog_proj, eog_events = mne.preprocessing.compute_proj_eog(
            raw, n_grad=1, average=True, n_jobs=n_jobs, bads=bad_channels,
            ch_name=eog_channel)

        if not isfile(eog_events_path):
            mne.event.write_events(eog_events_path, eog_events)

        proj_name = name + '_eog-proj.fif'
        proj_path = join(save_dir, proj_name)

        if overwrite or not isfile(proj_path):
            mne.write_proj(proj_path, eog_proj)

            print(proj_name + ' written')
        else:
            print(proj_name + ' already exists')

    else:
        print('No EEG-Channels to read EOG from')
        pass


@decor.topline
def apply_ssp_eog(name, save_dir, lowpass, highpass, overwrite):
    proj_name = name + '_eog-proj.fif'
    proj_path = join(save_dir, proj_name)

    if not isfile(proj_path):
        print('no ssp_proj_file found for' + name)
        pass
    else:
        projs = mne.read_proj(proj_path)
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)

        ssp_epochs_name = name + filter_string(lowpass, highpass) + '-eog_ssp-epo.fif'
        ssp_epochs_path = join(save_dir, ssp_epochs_name)

        if overwrite or not isfile(ssp_epochs_path):

            epochs.add_proj(projs)
            epochs.save(ssp_epochs_path)

        else:
            print('ssp_epochs file: ' + ssp_epochs_path + ' already exists')


@decor.topline
def run_ssp_ecg(name, save_dir, n_jobs, ecg_channel,
                bad_channels, overwrite):
    info = io.read_info(name, save_dir)
    ecg_events_name = name + '_ecg-eve.fif'
    ecg_events_path = join(save_dir, ecg_events_name)

    if ecg_channel in info['ch_names']:
        raw = io.read_raw(name, save_dir)

        ecg_proj, ecg_events = mne.preprocessing.compute_proj_ecg(
            raw, n_grad=1, average=True, n_jobs=n_jobs, bads=bad_channels,
            ch_name=ecg_channel, reject={'eeg': 5e-3})

        if not isfile(ecg_events_path):
            mne.event.write_events(ecg_events_path, ecg_events)

        proj_name = name + '_ecg-proj.fif'
        proj_path = join(save_dir, proj_name)

        if overwrite or not isfile(proj_path):
            mne.write_proj(proj_path, ecg_proj)

            print(proj_name + ' written')
        else:
            print(proj_name + ' already exists')

    else:
        print('No EEG-Channels to read EOG/EEG from')
        pass


@decor.topline
def apply_ssp_ecg(name, save_dir, lowpass, highpass, overwrite):
    proj_name = name + '_ecg-proj.fif'
    proj_path = join(save_dir, proj_name)

    if not isfile(proj_path):
        print('no ssp_proj_file found for' + name)
        pass
    else:
        projs = mne.read_proj(proj_path)
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)

        ssp_epochs_name = name + filter_string(lowpass, highpass) + '-ecg_ssp-epo.fif'
        ssp_epochs_path = join(save_dir, ssp_epochs_name)

        if overwrite or not isfile(ssp_epochs_path):

            epochs.add_proj(projs)
            epochs.save(ssp_epochs_path)

        else:
            print('ssp_epochs file: ' + ssp_epochs_path + ' already exists')


# TODO: Organize run_ica properly
@decor.topline
def run_ica(name, save_dir, lowpass, highpass, eog_channel, ecg_channel,
            reject, flat, bad_channels, overwrite, autoreject,
            save_plots, figures_path, sub_script_path, erm_analysis):
    info = io.read_info(name, save_dir)

    ica_dict = ut.dict_filehandler(name, f'ica_components{filter_string(lowpass, highpass)}', sub_script_path,
                                   onlyread=True)

    ica_name = name + filter_string(lowpass, highpass) + '-ica.fif'
    ica_path = join(save_dir, ica_name)

    if overwrite or not isfile(ica_path):

        try:
            raw = io.read_filtered(name, save_dir, lowpass, 1)
        except FileNotFoundError:
            raise RuntimeError(
                'No Raw with Highpass=1-Filter found,set "enable_ica" to true and run "filter_raw" again')

        epochs = io.read_epochs(name, save_dir, lowpass, highpass)
        picks = mne.pick_types(raw.info, meg=True, eeg=False, eog=False,
                               stim=False, exclude=bad_channels)

        ica = mne.preprocessing.ICA(n_components=25, method='fastica', random_state=8)

        if autoreject:
            reject = ut.autoreject_handler(name, epochs, highpass, lowpass, sub_script_path, overwrite_ar=False,
                                           only_read=True)

        print('Rejection Threshold: %s' % reject)

        ica.fit(raw, picks, reject=reject, flat=flat,
                reject_by_annotation=True)

        if name in ica_dict and ica_dict[name] != []:
            indices = ica_dict[name]
            ica.exclude += indices
            print(f'{indices} added to ica.exclude from ica_components.py')
            ica.save(ica_path)

            comp_list = []
            for c in range(ica.n_components):
                comp_list.append(c)
            fig1 = ica.plot_components(picks=comp_list, title=name)
            fig3 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name)
            fig4 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name)
            fig5 = ica.plot_overlay(epochs.average(), title=name)
            if save_plots:

                save_path = join(figures_path, 'ica', name +
                                 '_ica_comp' + filter_string(lowpass, highpass) + '.jpg')
                fig1.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name +
                                 '_ica_src' + filter_string(lowpass, highpass) + '_0.jpg')
                fig3.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name +
                                 '_ica_src' + filter_string(lowpass, highpass) + '_1.jpg')
                fig4.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')
                if not exists(join(figures_path, 'ica/evoked_overlay')):
                    makedirs(join(figures_path, 'ica/evoked_overlay'))
                save_path = join(figures_path, 'ica/evoked_overlay', name + \
                                 '_ica_ovl' + filter_string(lowpass, highpass) + '.jpg')
                fig5.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

        elif 'EEG 001' in info['ch_names'] and not erm_analysis:
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
                    fig3 = ica.plot_scores(eog_scores, title=name + '_eog')
                    fig2 = ica.plot_properties(eog_epochs, eog_indices, psd_args={'fmax': lowpass},
                                               image_args={'sigma': 1.})
                    fig7 = ica.plot_overlay(eog_epochs.average(), exclude=eog_indices, title=name + '_eog')
                    if save_plots:
                        for f in fig2:
                            save_path = join(figures_path, 'ica', name + \
                                             '_ica_prop_eog' + filter_string(lowpass, highpass) + \
                                             f'_{fig2.index(f)}.jpg')
                            f.savefig(save_path, dpi=300)
                            print('figure: ' + save_path + ' has been saved')

                        save_path = join(figures_path, 'ica', name + \
                                         '_ica_scor_eog' + filter_string(lowpass, highpass) + '.jpg')
                        fig3.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

                        save_path = join(figures_path, 'ica', name + \
                                         '_ica_ovl_eog' + filter_string(lowpass, highpass) + '.jpg')
                        fig7.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

            if len(ecg_epochs) != 0:
                ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs, ch_name=ecg_channel)
                ica.exclude.extend(ecg_indices)
                print('ECG-Components: ', ecg_indices)
                print(len(ecg_indices))
                if len(ecg_indices) != 0:
                    # Plot ECG-Plots
                    fig4 = ica.plot_scores(ecg_scores, title=name + '_ecg')
                    fig9 = ica.plot_properties(ecg_epochs, ecg_indices, psd_args={'fmax': lowpass},
                                               image_args={'sigma': 1.})
                    fig8 = ica.plot_overlay(ecg_epochs.average(), exclude=ecg_indices, title=name + '_ecg')
                    if save_plots:
                        for f in fig9:
                            save_path = join(figures_path, 'ica', name + \
                                             '_ica_prop_ecg' + filter_string(lowpass, highpass) + \
                                             f'_{fig9.index(f)}.jpg')
                            f.savefig(save_path, dpi=300)
                            print('figure: ' + save_path + ' has been saved')

                        save_path = join(figures_path, 'ica', name + \
                                         '_ica_scor_ecg' + filter_string(lowpass, highpass) + '.jpg')
                        fig4.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

                        save_path = join(figures_path, 'ica', name + \
                                         '_ica_ovl_ecg' + filter_string(lowpass, highpass) + '.jpg')
                        fig8.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')

            ica.save(ica_path)

            # Reading and Writing ICA-Components to a .py-file
            exes = ica.exclude
            indices = []
            for i in exes:
                indices.append(int(i))

            ut.dict_filehandler(name, f'ica_components{filter_string(lowpass, highpass)}', sub_script_path,
                                values=indices, overwrite=True)

            # Plot ICA integrated
            comp_list = []
            for c in range(ica.n_components):
                comp_list.append(c)
            fig1 = ica.plot_components(picks=comp_list, title=name)
            fig5 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name)
            fig6 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name)
            fig10 = ica.plot_overlay(epochs.average(), title=name)

            if save_plots:
                save_path = join(figures_path, 'ica', name + \
                                 '_ica_comp' + filter_string(lowpass, highpass) + '.jpg')
                fig1.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')
                if not exists(join(figures_path, 'ica/evoked_overlay')):
                    makedirs(join(figures_path, 'ica/evoked_overlay'))
                save_path = join(figures_path, 'ica/evoked_overlay', name + \
                                 '_ica_ovl' + filter_string(lowpass, highpass) + '.jpg')
                fig10.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name + \
                                 '_ica_src' + filter_string(lowpass, highpass) + '_0.jpg')
                fig5.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name + \
                                 '_ica_src' + filter_string(lowpass, highpass) + '_1.jpg')
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
                    fig4 = ica.plot_scores(ecg_scores, title=name + '_ecg')
                    fig5 = ica.plot_properties(ecg_epochs, ecg_indices, psd_args={'fmax': lowpass},
                                               image_args={'sigma': 1.})
                    fig6 = ica.plot_overlay(ecg_epochs.average(), exclude=ecg_indices, title=name + '_ecg')

                    save_path = join(figures_path, 'ica', name + \
                                     '_ica_scor_ecg' + filter_string(lowpass, highpass) + '.jpg')
                    fig4.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')
                    for f in fig5:
                        save_path = join(figures_path, 'ica', name + \
                                         '_ica_prop_ecg' + filter_string(lowpass, highpass) \
                                         + f'_{fig5.index(f)}.jpg')
                        f.savefig(save_path, dpi=300)
                        print('figure: ' + save_path + ' has been saved')
                    save_path = join(figures_path, 'ica', name + \
                                     '_ica_ovl_ecg' + filter_string(lowpass, highpass) + '.jpg')
                    fig6.savefig(save_path, dpi=300)
                    print('figure: ' + save_path + ' has been saved')

            ut.dict_filehandler(name, f'ica_components{filter_string(lowpass, highpass)}', sub_script_path, values=[])

            ica.save(ica_path)
            comp_list = []
            for c in range(ica.n_components):
                comp_list.append(c)
            fig1 = ica.plot_components(picks=comp_list, title=name)
            fig2 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name)
            fig3 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name)

            if save_plots:
                save_path = join(figures_path, 'ica', name + \
                                 '_ica_comp' + filter_string(lowpass, highpass) + '.jpg')
                fig1.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name + \
                                 '_ica_src' + filter_string(lowpass, highpass) + '_0.jpg')
                fig2.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name + \
                                 '_ica_src' + filter_string(lowpass, highpass) + '_1.jpg')
                fig3.savefig(save_path, dpi=300)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

        plt.close('all')

    else:
        print('ica file: ' + ica_path + ' already exists')


@decor.topline
def apply_ica(name, save_dir, lowpass, highpass, overwrite):
    ica_epochs_name = name + filter_string(lowpass, highpass) + '-ica-epo.fif'
    ica_epochs_path = join(save_dir, ica_epochs_name)

    if overwrite or not isfile(ica_epochs_path):

        epochs = io.read_epochs(name, save_dir, lowpass, highpass)
        ica = io.read_ica(name, save_dir, lowpass, highpass)

        if len(ica.exclude) == 0:
            print('No components excluded here')

        ica_epochs = ica.apply(epochs)
        ica_epochs.save(ica_epochs_path, overwrite=True)

    else:
        print('ica epochs file: ' + ica_epochs_path + ' already exists')


@decor.topline
def autoreject_interpolation(name, save_dir, lowpass, highpass, ica_evokeds):
    if ica_evokeds:
        ica_epochs_name = name + filter_string(lowpass, highpass) + '-ica-epo.fif'
        save_path = join(save_dir, ica_epochs_name)
        epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from ICA-Epochs')
    else:
        epochs_name = name + filter_string(lowpass, highpass) + '-epo.fif'
        save_path = join(save_dir, epochs_name)
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from (normal) Epochs')
    autor = AutoReject(n_jobs=-1)
    epochs_clean = autor.fit_transform(epochs)

    epochs_clean.save(save_path, overwrite=True)


@decor.topline
def get_evokeds(name, save_dir, lowpass, highpass, exec_ops, ermsub,
                detrend, enable_ica, overwrite):
    evokeds_name = name + filter_string(lowpass, highpass) + '-ave.fif'
    evokeds_path = join(save_dir, evokeds_name)
    info = io.read_info(name, save_dir)

    if overwrite or not isfile(evokeds_path):
        if enable_ica:
            epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from ICA-Epochs')
        elif exec_ops['apply_ssp_er'] and ermsub != 'None':
            epochs = io.read_ssp_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from SSP_ER-Epochs')
        elif exec_ops['apply_ssp_clm']:
            epochs = io.read_ssp_clm_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds form SSP_Clm-Epochs')
        elif exec_ops['apply_ssp_eog'] and 'EEG 001' in info['ch_names']:
            epochs = io.read_ssp_eog_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from SSP_EOG-Epochs')
        elif exec_ops['apply_ssp_ecg'] and 'EEG 001' in info['ch_names']:
            epochs = io.read_ssp_ecg_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from SSP_ECG-Epochs')
        else:
            epochs = io.read_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from (normal) Epochs')

        evokeds = []

        for trial_type in epochs.event_id:
            evoked = epochs[trial_type].average()
            if detrend:
                evoked = evoked.detrend(order=1)
            evokeds.append(evoked)

        mne.evoked.write_evokeds(evokeds_path, evokeds)

    else:
        print('evokeds file: ' + evokeds_path + ' already exists')


@decor.topline
def get_h1h2_evokeds(name, save_dir, lowpass, highpass, enable_ica, exec_ops, ermsub,
                     detrend):
    info = io.read_info(name, save_dir)

    if enable_ica:
        epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from ICA-Epochs')
    elif exec_ops['apply_ssp_er'] and ermsub != 'None':
        epochs = io.read_ssp_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from SSP_ER-Epochs')
    elif exec_ops['apply_ssp_clm']:
        epochs = io.read_ssp_clm_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds form SSP_Clm-Epochs')
    elif exec_ops['apply_ssp_eog'] and 'EEG 001' in info['ch_names']:
        epochs = io.read_ssp_eog_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from SSP_EOG-Epochs')
    elif exec_ops['apply_ssp_ecg'] and 'EEG 001' in info['ch_names']:
        epochs = io.read_ssp_ecg_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from SSP_ECG-Epochs')
    else:
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from (normal) Epochs')

    h1_evokeds_name = name + filter_string(lowpass, highpass) + '_h1-ave.fif'
    h1_evokeds_path = join(save_dir, h1_evokeds_name)
    h2_evokeds_name = name + filter_string(lowpass, highpass) + '_h2-ave.fif'
    h2_evokeds_path = join(save_dir, h2_evokeds_name)

    h1_evokeds = []
    h2_evokeds = []

    for trial_type in epochs.event_id:
        pre_epochs = epochs[trial_type]
        h1_evoked = pre_epochs[:int(len(epochs[trial_type]) / 2)].average()
        h2_evoked = pre_epochs[int(len(epochs[trial_type]) / 2):].average()
        if detrend:
            h1_evoked = h1_evoked.detrend(order=1)
            h2_evoked = h1_evoked.detrend(order=1)
        h1_evokeds.append(h1_evoked)
        h2_evokeds.append(h2_evoked)

    mne.evoked.write_evokeds(h1_evokeds_path, h1_evokeds)
    mne.evoked.write_evokeds(h2_evokeds_path, h2_evokeds)


@decor.small_func
def calculate_gfp(evoked):
    d = evoked.data
    gfp = np.sqrt((d * d).mean(axis=0))

    return gfp


@decor.topline
def combine_evokeds_ab(data_path, save_dir_averages, lowpass, highpass, ab_dict):
    for title in ab_dict:
        print(f'abs for {title}')
        ab_ev_dict = dict()
        channels = list()
        trials = set()
        for name in ab_dict[title]:
            save_dir = join(data_path, name)
            evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)
            channels.append(set(evokeds[0].ch_names))
            for evoked in evokeds:
                trial = evoked.comment
                trials.add(trial)
                if trial in ab_ev_dict:
                    ab_ev_dict[trial].append(evoked)
                else:
                    ab_ev_dict.update({trial: [evoked]})

        # Make sure, that both evoked datasets got the same channels (Maybe some channels were discarded between measurements)
        channels = list(set.intersection(*channels))
        for trial in ab_ev_dict:
            ab_ev_dict[trial] = [evoked.pick_channels(channels) for evoked in ab_ev_dict[trial]]

        evokeds = list()
        for trial in ab_ev_dict:
            cmb_evokeds = mne.combine_evoked(ab_ev_dict[trial], weights='equal')
            evokeds.append(cmb_evokeds)
        evokeds_name = f'{title}{filter_string(lowpass, highpass)}-ave.fif'
        evokeds_path = join(save_dir_averages, 'ab_combined', evokeds_name)
        mne.write_evokeds(evokeds_path, evokeds)


@decor.topline
def pp_alignment(ab_dict, cond_dict, sub_dict, data_path, lowpass, highpass, sub_script_path,
                 event_id, subjects_dir, inverse_method, source_space_method,
                 parcellation, figures_path):

    # Noch problematisch: pp9_64, pp19_64
    # Mit ab-average werden die nicht alignierten falsch gemittelt, Annahme lag zu Mitte zwischen ab

    ab_gfp_data = dict()
    ab_ltc_data = dict()
    ab_lags = dict()

    for title in ab_dict:
        print('--------' + title + '--------')
        names = ab_dict[title]
        pattern = r'pp[0-9]+[a-z]?'
        match = re.match(pattern, title)
        prefix = match.group()
        subtomri = sub_dict[prefix]
        src = io.read_source_space(subtomri, subjects_dir, source_space_method)

        for name in ab_dict[title]:
            # Assumes, that first evoked in evokeds is LBT
            save_dir = join(data_path, name)
            e = io.read_evokeds(name, save_dir, lowpass, highpass)[0]
            e.crop(-0.1, 0.3)
            gfp = calculate_gfp(e)
            ab_gfp_data[name] = gfp

            n_stc = io.read_normal_source_estimates(name, save_dir, lowpass, highpass, inverse_method, event_id)['LBT']
            # get peaks from label-time-course
            labels = mne.read_labels_from_annot(subtomri, subjects_dir=subjects_dir, parc=parcellation)
            label = None
            for l in labels:
                if l.name == 'postcentral-lh':
                    label = l
            # Crop here only possible, if toi is set to (-0.1, ...) according to gfp.crop(-0.1, ...)
            ltc = n_stc.extract_label_time_course(label, src, mode='pca_flip')[0][:400]
            ab_ltc_data[name] = ltc

        # Cross-Correlate a and b
        if len(ab_dict[title]) > 1:
            # Plot Time-Course for a and b
            n1, n2 = names
            g1, g2 = ab_gfp_data[n1], ab_gfp_data[n2]
            l1, l2 = ab_ltc_data[n1], ab_ltc_data[n2]

            # cross-correlation of ab-gfps
            ab_glags, ab_gcorr, ab_gmax_lag, ab_gmax_val = cross_correlation(g1, g2)

            # cross-correlation of ab-label-time-courses in postcentral-lh
            llags, lcorr, ab_lmax_lag, ab_lmax_val = cross_correlation(l1, l2)

            # Evaluate appropriate lags, threshold: normed correlation >= 0.8
            if ab_gmax_lag != 0 and ab_lmax_lag != 0:
                if ab_gmax_val >= 0.7 and ab_lmax_val >= 0.7:
                    ab_lag = ab_lmax_lag
                    # if ab_gmax_lag != ab_lmax_lag:
                    #     if ab_gmax_val > ab_lmax_val:
                    #         ab_lag = ab_gmax_lag
                    #     else:
                    #         ab_lag = ab_lmax_lag
                    # else:
                    #     ab_lag = ab_gmax_lag
                elif ab_gmax_val >= 0.7:
                    ab_lag = ab_gmax_lag
                elif ab_lmax_val >= 0.7:
                    ab_lag = ab_lmax_lag
                else:
                    ab_lag = 0
            elif ab_gmax_lag != 0:
                if ab_gmax_val >= 0.7:
                    ab_lag = ab_gmax_lag
                else:
                    ab_lag = 0
            elif ab_lmax_lag != 0:
                if ab_lmax_val >= 0.7:
                    ab_lag = ab_lmax_lag
                else:
                    ab_lag = 0
            else:
                ab_lag = 0
                print('No lags in gfp or ltc')

            # Make ab-averages to improve SNR
            # The partner-data is aligned with ab_lag and averaged
            # The single overhang of the base-data is added to the partner-data, thus avg=base_data at overhang
            if ab_lag < 0:
                g1_applag = np.append(g1[:int(ab_lag)], g2[:-int(ab_lag)])
                g2_applag = np.append(g2[-int(ab_lag):], g1[int(ab_lag):])
                g1_avg = (g1 + g2_applag) / 2
                g2_avg = (g2 + g1_applag) / 2

                l1_applag = np.append(l1[:int(ab_lag)], l2[:-int(ab_lag)])
                l2_applag = np.append(l2[-int(ab_lag):], l1[int(ab_lag):])
                l1_avg = (l1 + l2_applag) / 2
                l2_avg = (l2 + l1_applag) / 2
            elif ab_lag > 0:
                g1_applag = np.append(g1[int(ab_lag):], g2[-int(ab_lag):])
                g2_applag = np.append(g2[:-int(ab_lag)], g1[:int(ab_lag)])
                g1_avg = (g1 + g2_applag) / 2
                g2_avg = (g2 + g1_applag) / 2

                l1_applag = np.append(l1[int(ab_lag):], l2[-int(ab_lag):])
                l2_applag = np.append(l2[:-int(ab_lag)], l1[:int(ab_lag)])
                l1_avg = (l1 + l2_applag) / 2
                l2_avg = (l2 + l1_applag) / 2
            else:
                g1_avg = g1
                g2_avg = g2
                l1_avg = l1
                l2_avg = l2

                # g1_avg = (g1 + g2) / 2
                # g2_avg = (g1 + g2) / 2
                # l1_avg = (l1 + l2) / 2
                # l2_avg = (l1 + l2) / 2

            ab_gfp_data[n1] = g1_avg
            ab_gfp_data[n2] = g2_avg
            ab_ltc_data[n1] = l1_avg
            ab_ltc_data[n2] = l2_avg
            # Save lags to dict, ab_lag applies to data_b
            ut.dict_filehandler(title, 'ab_lags', sub_script_path,
                                {'gfp_lag': ab_gmax_lag, 'gfp_val': round(ab_gmax_val, 2),
                                 'ltc_lag': ab_lmax_lag, 'ltc_val': round(ab_lmax_val, 2),
                                 'ab_lag': ab_lag})

            # Plot Compare Plot
            if ab_lag != 0:
                fig, axes = plt.subplots(nrows=2, ncols=3, sharex='col',
                                         gridspec_kw={'hspace': 0.1, 'wspace': 0.1,
                                                      'left': 0.05, 'right': 0.95,
                                                      'top': 0.95, 'bottom': 0.05},
                                         figsize=(18, 8))
            else:
                fig, axes = plt.subplots(nrows=2, ncols=2, sharex='col',
                                         gridspec_kw={'hspace': 0.1, 'wspace': 0.1,
                                                      'left': 0.05, 'right': 0.95,
                                                      'top': 0.95, 'bottom': 0.05},
                                         figsize=(18, 8))
            axes[0, 0].plot(g1, label=n1)
            axes[0, 0].plot(g2, label=n2)
            axes[0, 0].legend()
            axes[0, 0].set_title(f'GFP\'s')

            axes[0, 1].plot(ab_glags, ab_gcorr)
            axes[0, 1].plot(ab_gmax_lag, ab_gmax_val, 'rx')
            axes[0, 1].set_title(f'Cross-Correlation, lag = {ab_gmax_lag}')

            # Plot label-time-courses of postcentral-lh
            axes[1, 0].plot(l1, label=n1)
            axes[1, 0].plot(l2, label=n2)
            axes[1, 0].legend()
            axes[1, 0].set_title(f'Label-Time-Course in postcentral-lh')

            axes[1, 1].plot(llags, lcorr)
            axes[1, 1].plot(ab_lmax_lag, ab_lmax_val, 'rx')
            axes[1, 1].set_title(f'Cross-Correlation, lag = {ab_lmax_lag}')

            if ab_lag != 0:
                # Apply ab_lag for comparision (lag applies to data_b)
                if ab_lag < 0:
                    g1a = g1[:int(ab_lag)]
                    g2a = g2[-int(ab_lag):]
                elif ab_lag > 0:
                    g1a = g1[int(ab_lag):]
                    g2a = g2[:-int(ab_lag)]
                else:
                    g1a = g1
                    g2a = g2

                axes[0, 2].plot(g1a, label=n1)
                axes[0, 2].plot(g2a, label=n2)
                axes[0, 2].legend()
                axes[0, 2].set_title(f'GFP\'s corrected with ab_lag = {ab_lag}')

                # Apply ab_lag for comparision (lag applies to data_b)
                if ab_lmax_lag < 0:
                    l1a = l1[:int(ab_lag)]
                    l2a = l2[-int(ab_lag):]
                elif ab_lmax_lag > 0:
                    l1a = l1[int(ab_lag):]
                    l2a = l2[:-int(ab_lag)]
                else:
                    l1a = l1
                    l2a = l2

                axes[1, 2].plot(l1a, label=n1)
                axes[1, 2].plot(l2a, label=n2)
                axes[1, 2].legend()
                axes[1, 2].set_title(f'LTC\'s corrected with ab_lag = {ab_lag}')

            filename = join(figures_path, 'align_peaks', f'{title}{filter_string(lowpass, highpass)}_xcorr_ab.jpg')
            plt.savefig(filename)

        else:
            print('No b-measurement available')
            ut.dict_filehandler(title, 'ab_lags', sub_script_path,
                                {'gfp_lag': 0, 'gfp_val': 1, 'ltc_lag': 0, 'ltc_val': 1, 'ab_lag': 0})


    plot.close_all()


@decor.small_func
def cross_correlation(x, y):
    nx = len(x) + len(y)
    # if nx != len(y):
    #     raise ValueError('x and y must be equal length')
    correls = np.correlate(x, y, mode="full")
    # Normed correlation values
    correls /= np.sqrt(np.dot(x, x) * np.dot(y, y))
    # maxlags = int(nx/2) - 1
    maxlags = int(len(correls) / 2)
    lags = np.arange(-maxlags, maxlags + 1)

    max_lag = lags[np.argmax(np.abs(correls))]
    max_val = correls[np.argmax(np.abs(correls))]

    return lags, correls, max_lag, max_val


# def apply_alignment():
#     # Apply alignment over changing the
#     det_peaks = ut.read_dict_file('peak_alignment', sub_script_path)
#     for name in det_peaks:
#         save_dir = join(data_path, name)


@decor.topline
def grand_avg_evokeds(data_path, grand_avg_dict, save_dir_averages,
                      lowpass, highpass, exec_ops, quality, ana_h1h2):
    for key in grand_avg_dict:
        trial_dict = {}
        h1_dict = {}
        h2_dict = {}
        print(f'grand_average for {key}')
        for name in grand_avg_dict[key]:
            if exec_ops['motor_erm_analysis']:
                save_dir = data_path
            else:
                save_dir = join(data_path, name)
            print(f'Add {name} to grand_average')
            evokeds = io.read_evokeds(name, save_dir, lowpass,
                                      highpass)
            for evoked in evokeds:
                if evoked.nave != 0:
                    if evoked.comment in trial_dict:
                        trial_dict[evoked.comment].append(evoked)
                    else:
                        trial_dict.update({evoked.comment: [evoked]})
                else:
                    print(f'{evoked.comment} for {name} got nave=0')

            if ana_h1h2:
                evokeds_dict = io.read_h1h2_evokeds(name, save_dir, lowpass, highpass)
                for evoked in evokeds_dict['h1']:
                    if evoked.comment in h1_dict:
                        h1_dict[evoked.comment].append(evoked)
                    else:
                        h1_dict.update({evoked.comment: [evoked]})

                for evoked in evokeds_dict['h2']:
                    if evoked.comment in h1_dict:
                        h2_dict[evoked.comment].append(evoked)
                    else:
                        h2_dict.update({evoked.comment: [evoked]})

        for trial in trial_dict:
            if len(trial_dict[trial]) != 0:
                ga = mne.grand_average(trial_dict[trial],
                                       interpolate_bads=True,
                                       drop_bads=True)
                ga.comment = trial
                ga_path = join(save_dir_averages, 'evoked',
                               key + '_' + trial + \
                               filter_string(lowpass, highpass) + \
                               '_' + str(quality) + '-grand_avg-ave.fif')
                ga.save(ga_path)

        for trial in h1_dict:
            if len(h1_dict[trial]) != 0:
                ga = mne.grand_average(h1_dict[trial],
                                       interpolate_bads=True,
                                       drop_bads=True)
                ga.comment = trial
                ga_path = join(save_dir_averages, 'evoked',
                               key + '_' + trial + '_' + 'h1' + \
                               filter_string(lowpass, highpass) + \
                               '_' + str(quality) + '-grand_avg-ave.fif')
                ga.save(ga_path)

        for trial in h2_dict:
            if len(h2_dict[trial]) != 0:
                ga = mne.grand_average(h2_dict[trial],
                                       interpolate_bads=True,
                                       drop_bads=True)
                ga.comment = trial
                ga_path = join(save_dir_averages, 'evoked',
                               key + '_' + trial + '_' + 'h2' + \
                               filter_string(lowpass, highpass) + \
                               '_' + str(quality) + '-grand_avg-ave.fif')
                ga.save(ga_path)


@decor.topline
def tfr(name, save_dir, lowpass, highpass, ica_evokeds, tfr_freqs, overwrite_tfr,
        tfr_method, multitaper_bandwith, stockwell_width, n_jobs):
    power_name = name + filter_string(lowpass, highpass) + '_' + tfr_method + '_pw-tfr.h5'
    power_path = join(save_dir, power_name)
    itc_name = name + filter_string(lowpass, highpass) + '_' + tfr_method + '_itc-tfr.h5'
    itc_path = join(save_dir, itc_name)

    n_cycles = tfr_freqs / 2.
    powers = []
    itcs = []

    if overwrite_tfr or not isfile(power_path) or not isfile(itc_path):
        if ica_evokeds:
            epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
        else:
            epochs = io.read_epochs(name, save_dir, lowpass, highpass)

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


@decor.topline
def grand_avg_tfr(data_path, grand_avg_dict, save_dir_averages,
                  lowpass, highpass, tfr_method):
    for key in grand_avg_dict:
        trial_dict = {}
        print(f'grand_average for {key}')
        for name in grand_avg_dict[key]:
            save_dir = join(data_path, name)
            print(f'Add {name} to grand_average')
            powers = io.read_tfr_power(name, save_dir, lowpass,
                                       highpass, tfr_method)
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
                               key + '_' + trial + \
                               filter_string(lowpass, highpass) + \
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

    if sys.platform == 'win32':
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
        print('Importing MRI data for subject: ' + mri_subject + \
              ' into FreeSurfer folder.\nBash output follows below.\n\n')

        command = ['recon-all',
                   '-subjid', mri_subject,
                   '-i', join(dicom_path, first_file),
                   '-openmp', str(n_jobs_freesurfer)]

        run_process_and_write_output(command, subjects_dir)
    else:
        print('FreeSurfer folder for: ' + mri_subject + ' already exists.' + \
              ' To import data from the beginning, you would have to ' + \
              "delete this subject's FreeSurfer folder")


def segment_mri(mri_subject, subjects_dir, n_jobs_freesurfer):
    print('Segmenting MRI data for subject: ' + mri_subject + \
          ' using the Freesurfer "recon-all" pipeline.' + \
          'Bash output follows below.\n\n')

    command = ['recon-all',
               '-subjid', mri_subject,
               '-all',
               '-openmp', str(n_jobs_freesurfer)]

    run_process_and_write_output(command, subjects_dir)


def apply_watershed(mri_subject, subjects_dir, overwrite):
    # mne.bem.make_watershed_bem(mri_subject, subjects_dir)

    print('Running Watershed algorithm for: ' + mri_subject + \
          ". Output is written to the bem folder " + \
          "of the subject's FreeSurfer folder.\n" + \
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
    print('Making dense scalp surfacing easing co-registration for ' + \
          'subject: ' + mri_subject + \
          ". Output is written to the bem folder" + \
          " of the subject's FreeSurfer folder.\n" + \
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
@decor.topline
def setup_src(mri_subject, subjects_dir, source_space_method, n_jobs,
              overwrite):
    src_name = mri_subject + '_' + source_space_method + '-src.fif'
    src_path = join(subjects_dir, mri_subject, 'bem', src_name)

    if overwrite or not isfile(src_path):
        src = mne.setup_source_space(mri_subject, spacing=source_space_method,
                                     surface='white', subjects_dir=subjects_dir,
                                     add_dist=False, n_jobs=n_jobs)
        src.save(src_path, overwrite=True)


@decor.topline
def compute_src_distances(mri_subject, subjects_dir, source_space_method,
                          n_jobs):
    src = io.read_source_space(mri_subject, subjects_dir, source_space_method)
    src_computed = mne.add_source_space_distances(src, n_jobs=n_jobs)

    src_name = mri_subject + '_' + source_space_method + '-src.fif'
    src_path = join(subjects_dir, mri_subject, 'bem', src_name)

    src_computed.save(src_path, overwrite=True)


@decor.topline
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


@decor.topline
def setup_vol_src(mri_subject, subjects_dir):
    bem = io.read_bem_solution(mri_subject, subjects_dir)
    vol_src = mne.setup_volume_source_space(mri_subject, bem=bem, pos=5.0, subjects_dir=subjects_dir)
    vol_src_name = mri_subject + '-vol-src.fif'
    vol_src_path = join(subjects_dir, mri_subject, 'bem', vol_src_name)
    vol_src.save(vol_src_path, overwrite=True)


@decor.topline
def morph_subject(mri_subject, subjects_dir, morph_to, source_space_method,
                  overwrite):
    morph_name = mri_subject + '--to--' + morph_to + '-' + source_space_method
    morph_path = join(subjects_dir, mri_subject, morph_name)

    src = io.read_source_space(mri_subject, subjects_dir, source_space_method)

    morph = mne.compute_source_morph(src, subject_from=mri_subject,
                                     subject_to=morph_to, subjects_dir=subjects_dir)

    if overwrite or not isfile(morph_path):
        morph.save(morph_path, overwrite=True)
        print(f'{morph_path} written')


@decor.topline
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


@decor.topline
def mri_coreg(name, save_dir, subtomri, subjects_dir):
    raw_name = name + '-raw.fif'
    raw_path = join(save_dir, raw_name)

    # fids = mne.coreg.get_mni_fiducials(subtomri, subjects_dir)

    mne.gui.coregistration(subject=subtomri, inst=raw_path,
                           subjects_dir=subjects_dir, guess_mri_subject=False,
                           advanced_rendering=True, mark_inside=True)


@decor.topline
def create_forward_solution(name, save_dir, subtomri, subjects_dir,
                            source_space_method, overwrite, n_jobs, eeg_fwd):
    forward_name = name + '-fwd.fif'
    forward_path = join(save_dir, forward_name)

    if overwrite or not isfile(forward_path):

        info = io.read_info(name, save_dir)
        trans = io.read_transformation(save_dir, subtomri)
        bem = io.read_bem_solution(subtomri, subjects_dir)
        source_space = io.read_source_space(subtomri, subjects_dir, source_space_method)

        forward = mne.make_forward_solution(info, trans, source_space, bem,
                                            n_jobs=n_jobs, eeg=eeg_fwd)

        mne.write_forward_solution(forward_path, forward, overwrite)

    else:
        print('forward solution: ' + forward_path + ' already exists')


@decor.topline
def estimate_noise_covariance(name, save_dir, lowpass, highpass,
                              overwrite, ermsub, data_path, baseline,
                              bad_channels, n_jobs, erm_noise_cov,
                              calm_noise_cov, ica_evokeds, erm_ica):
    if calm_noise_cov:

        print('Noise Covariance on 1-Minute-Calm')
        covariance_name = name + filter_string(lowpass, highpass) + '-clm-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            raw = io.read_filtered(name, save_dir, lowpass, highpass)
            raw.crop(tmin=5, tmax=50)
            raw.pick_types(exclude=bad_channels)

            if erm_ica:
                print('Applying ICA to ERM-Raw')
                ica = io.read_ica(name, save_dir, lowpass, highpass)
                raw = ica.apply(raw)

            noise_covariance = mne.compute_raw_covariance(raw, n_jobs=n_jobs,
                                                          method='empirical')
            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: ' + covariance_path + \
                  ' already exists')

    elif ermsub == 'None' or 'leer' in name or erm_noise_cov is False:

        print('Noise Covariance on Epochs')
        covariance_name = name + filter_string(lowpass, highpass) + '-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            if ica_evokeds:
                epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
            else:
                epochs = io.read_epochs(name, save_dir, lowpass, highpass)

            tmin, tmax = baseline
            noise_covariance = mne.compute_covariance(epochs, tmin=tmin, tmax=tmax,
                                                      inverse_method='empirical', n_jobs=n_jobs)

            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: ' + covariance_path + \
                  ' already exists')

    else:
        print('Noise Covariance on ERM')
        covariance_name = name + filter_string(lowpass, highpass) + '-erm-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            erm_name = ermsub + filter_string(lowpass, highpass) + '-raw.fif'
            erm_path = join(data_path, 'empty_room_data', erm_name)

            erm = mne.io.read_raw_fif(erm_path, preload=True)
            erm.pick_types(exclude=bad_channels)
            if erm_ica:
                print('Applying ICA to ERM-Raw')
                ica = io.read_ica(name, save_dir, lowpass, highpass)
                erm = ica.apply(erm)

            noise_covariance = mne.compute_raw_covariance(erm, n_jobs=n_jobs,
                                                          method='empirical')
            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: ' + covariance_path + \
                  ' already exists')


@decor.topline
def create_inverse_operator(name, save_dir, lowpass, highpass,
                            overwrite, ermsub, calm_noise_cov, erm_noise_cov):
    inverse_operator_name = name + filter_string(lowpass, highpass) + '-inv.fif'
    inverse_operator_path = join(save_dir, inverse_operator_name)

    if overwrite or not isfile(inverse_operator_path):

        info = io.read_info(name, save_dir)
        noise_covariance = io.read_noise_covariance(name, save_dir, lowpass, highpass,
                                                    erm_noise_cov, ermsub, calm_noise_cov)

        forward = io.read_forward(name, save_dir)

        inverse_operator = mne.minimum_norm.make_inverse_operator(info, forward, noise_covariance)

        mne.minimum_norm.write_inverse_operator(inverse_operator_path, inverse_operator)

    else:
        print('inverse operator file: ' + inverse_operator_path + \
              ' already exists')


# noinspection PyShadowingNames
@decor.topline
def source_estimate(name, save_dir, lowpass, highpass, inverse_method, toi,
                    overwrite):
    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    snr = 3.0
    lambda2 = 1.0 / snr ** 2

    for evoked in evokeds:
        # Crop evoked to Time of Interest for Analysis
        evoked = evoked.crop(toi[0], toi[1])
        trial_type = evoked.comment

        stc_name = name + filter_string(lowpass, highpass) + '_' + trial_type + '_' + inverse_method
        stc_path = join(save_dir, stc_name)
        if overwrite or not isfile(stc_path + '-lh.stc'):
            stc = mne.minimum_norm.apply_inverse(evoked, inverse_operator, lambda2, method=inverse_method)
            stc.save(stc_path)
        else:
            print('source estimates for: ' + name + \
                  ' already exists')

        n_stc_name = name + filter_string(lowpass, highpass) + '_' + trial_type + '_' + inverse_method + '-normal'
        n_stc_path = join(save_dir, n_stc_name)
        if overwrite or not isfile(n_stc_path + '-lh.stc'):
            normal_stc = mne.minimum_norm.apply_inverse(evoked, inverse_operator, lambda2,
                                                        method=inverse_method, pick_ori='normal')
            normal_stc.save(n_stc_path)
        else:
            print('normal-source estimates for: ' + name + \
                  ' already exists')


@decor.topline
def vector_source_estimate(name, save_dir, lowpass, highpass, inverse_method, toi, overwrite):
    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    snr = 3.0
    lambda2 = 1.0 / snr ** 2

    for evoked in evokeds:
        # Crop evoked to Time of Interest for Analysis
        evoked = evoked.crop(toi[0], toi[1])
        trial_type = evoked.comment

        v_stc_name = name + filter_string(lowpass, highpass) + '_' + trial_type + '_' + inverse_method + '-vector'
        v_stc_path = join(save_dir, v_stc_name)
        if overwrite or not isfile(v_stc_path + '-stc.h5'):
            v_stc = mne.minimum_norm.apply_inverse(evoked, inverse_operator, lambda2,
                                                   method=inverse_method, pick_ori='vector')
            v_stc.save(v_stc_path)
        else:
            print('vector source estimates for: ' + name + ' already exists')


@decor.topline
def mixed_norm_estimate(name, save_dir, lowpass, highpass, toi, inverse_method, erm_noise_cov,
                        ermsub, calm_noise_cov, event_id, mixn_dip, overwrite):
    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)
    forward = io.read_forward(name, save_dir)
    noise_cov = io.read_noise_covariance(name, save_dir, lowpass, highpass,
                                         erm_noise_cov, ermsub, calm_noise_cov)
    inv_op = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    if inverse_method == 'dSPM':
        print('dSPM-Inverse-Solution existent, loading...')
        stcs = io.read_source_estimates(name, save_dir, lowpass, highpass, inverse_method, event_id)
    else:
        print('No dSPM-Inverse-Solution available, calculating...')
        stcs = dict()
        snr = 3.0
        lambda2 = 1.0 / snr ** 2
        for evoked in evokeds:
            # Crop evoked to Time of Interest for Analysis
            evoked = evoked.crop(toi[0], toi[1])
            trial_type = evoked.comment
            stcs[trial_type] = mne.minimum_norm.apply_inverse(evoked, inv_op, lambda2, method='dSPM')
            stc_name = name + filter_string(lowpass, highpass) + '_' + trial_type + '_' + inverse_method
            stc_path = join(save_dir, stc_name)
            stcs[trial_type].save(stc_path)

    for evoked in evokeds:
        # Crop evoked to Time of Interest for Analysis
        evoked = evoked.crop(toi[0], toi[1])
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
                mixn_dip_name = name + filter_string(lowpass, highpass) + '_' + trial_type + '-mixn-dip-' + str(idx)
                mixn_dip_path = join(save_dir, 'dipoles', mixn_dip_name)
                dip.save(mixn_dip_path)
        else:
            mixn, residual = mne.inverse_sparse.mixed_norm(evoked, forward, noise_cov, alpha,
                                                           maxit=3000, tol=1e-4, active_set_size=10, debias=True,
                                                           weights=stcs[trial_type], n_mxne_iter=n_mxne_iter,
                                                           return_residual=True, return_as_dipoles=True)

            mixn_stc_name = name + filter_string(lowpass, highpass) + '_' + trial_type + '-mixn'
            mixn_stc_path = join(save_dir, mixn_stc_name)
            if overwrite or not isfile(mixn_stc_path + '-lh.stc'):
                mixn.save(mixn_stc_path)
            else:
                print('mixed-norm source estimates for: ' + name + \
                      ' already exists')

        mixn_res_name = name + filter_string(lowpass, highpass) + '_' + trial_type + '-mixn-res-ave.fif'
        mixn_res_path = join(save_dir, mixn_res_name)
        if overwrite or not isfile(mixn_res_path):
            residual.save(mixn_res_path)
        else:
            print('mixed-norm source estimate residual for: ' + name + \
                  ' already exists')


@decor.topline
def ecd_fit(name, save_dir, lowpass, highpass, ermsub, subjects_dir,
            subtomri, erm_noise_cov, calm_noise_cov, ecds, save_plots, figures_path):
    try:
        ecd = ecds[name]

        evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)
        bem = io.read_bem_solution(subtomri, subjects_dir)
        trans = io.read_transformation(save_dir, subtomri)
        t1_path = io.path_fs_volume('T1', subtomri, subjects_dir)

        noise_covariance = io.read_noise_covariance(name, save_dir, lowpass, highpass,
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
                                      filter_string(lowpass, highpass) + '_' +
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
                                     filter_string(lowpass, highpass) + '_' +
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


@decor.topline
def create_func_label(name, save_dir, lowpass, highpass, inverse_method, event_id,
                      subtomri, subjects_dir, source_space_method, label_origin,
                      parcellation_orig, ev_ids_label_analysis,
                      save_plots, figures_path, sub_script_path,
                      n_std, combine_ab, grand_avg=False):
    print(name)
    if combine_ab and isinstance(name, tuple):
        n_stcs_a = io.read_normal_source_estimates(name[0], save_dir[0],
                                                   lowpass, highpass,
                                                   inverse_method, event_id)
        n_stcs_b = io.read_normal_source_estimates(name[1], save_dir[1],
                                                   lowpass, highpass,
                                                   inverse_method, event_id)
        n_stcs = {}
        print('Grand_Averaging a/b')
        for trial in n_stcs_a:
            n_stc_a = n_stcs_a[trial]
            n_stc_b = n_stcs_b[trial]
            n_stc_average = n_stc_a.copy()
            n_stc_average.data += n_stc_b.data
            n_stc_average /= 2
            n_stc_average.comment = trial
            n_stc_average.vertices = n_stc_b.vertices
            n_stcs.update({trial: n_stc_average})

    n_stcs = io.read_normal_source_estimates(name, save_dir,
                                             lowpass, highpass,
                                             inverse_method, event_id)

    src = io.read_source_space(subtomri, subjects_dir, source_space_method)
    labels = mne.read_labels_from_annot(subtomri, subjects_dir=subjects_dir,
                                        parc=parcellation_orig)

    # Delete old func_labels:
    if combine_ab and isinstance(name, tuple):
        for sd in save_dir:
            if not exists(join(sd, 'func_labels')):
                makedirs(join(sd, 'func_labels'))
            files = listdir(join(sd, 'func_labels'))
            for file in files:
                remove(join(sd, 'func_labels', file))
    elif not grand_avg:
        if not exists(join(save_dir, 'func_labels')):
            makedirs(join(save_dir, 'func_labels'))
        files = listdir(join(save_dir, 'func_labels'))
        for file in files:
            remove(join(save_dir, 'func_labels', file))

    for trial in ev_ids_label_analysis:
        # Grand-Avg only working with one ev_id
        if not grand_avg:
            n_stc = n_stcs[trial]
        save_dict = {}
        func_labels_dict = {}
        if combine_ab and isinstance(name, tuple):
            for sd in save_dir:
                if not exists(join(sd, 'func_label_tc')):
                    makedirs(join(sd, 'func_label_tc'))
            # Dirty work around for problem with source space and averaged stcs
            n_stc.subject = subtomri
            n_stc.to_original_src(src, subject_orig=subtomri, subjects_dir=subjects_dir)
        else:
            if not exists(join(save_dir, 'func_label_tc')):
                makedirs(join(save_dir, 'func_label_tc'))

        if label_origin == 'all':
            t_labels = labels
        else:
            t_labels = [l for l in labels if l.name in label_origin]

        for prog, label in enumerate(t_labels):
            print(name)
            print(label.name)
            print(f'Progress: {round(prog / len(t_labels) * 100, 2)}%')

            tc = n_stc.extract_label_time_course(label, src, mode='pca_flip')[0]
            f = signal.savgol_filter(tc, 101, 5)
            std = np.std(f)
            mean = np.mean(f)
            peaks, properties = signal.find_peaks(abs(f), height=n_std * std + mean, distance=10)
            peaks = peaks[:1]  # !!!Discarded possibility of several peaks
            if len(peaks) == 0:  # Only let significant peaks define a label
                print(f'{label.name} doesn\'t wield a significant peak, current setting: prominence>{n_std}*std')
                continue

            # noinspection PyTypeChecker
            fig, axes = plt.subplots(ncols=len(peaks), figsize=(18, 8), sharey=True,
                                     gridspec_kw={'hspace': 0.1, 'wspace': 0.1,
                                                  'left': 0.05, 'right': 0.95,
                                                  'top': 0.95, 'bottom': 0.05})

            for idx, peak in enumerate(peaks):
                max_t = round(n_stc.times[peak], 3)
                tmin = round(max_t - 0.01, 3)
                tmax = round(max_t + 0.01, 3)
                if tmin < n_stc.tmin:
                    diff = n_stc.tmin - tmin
                    tmin += diff
                    tmax += diff
                    print(f'peak too close to start, correcting + {diff}')
                if tmax > n_stc.times[-1]:
                    diff = tmax - n_stc.times[-1]
                    tmin -= diff
                    tmax -= diff
                    print(f'peak too close to start, correcting - {diff}')
                print(f'{tmin} - {tmax}s')
                # Make an STC in the time interval of interest and take the mean
                stc_mean = n_stc.copy().crop(tmin, tmax).mean()

                # use the stc_mean to generate a functional label
                # region growing is halted at 60% of the peak value within the
                # anatomical label / ROI specified by aparc_label_name
                stc_mean_label = stc_mean.in_label(label)
                data = np.abs(stc_mean_label.data)
                stc_mean_label.data[data < 0.6 * np.max(data)] = 0.

                func_labels = mne.stc_to_label(stc_mean_label, src=src, smooth=True,
                                               subjects_dir=subjects_dir, connected=True,
                                               verbose='DEBUG')

                for i in func_labels:
                    if len(i) > 0:
                        func_label = i[0]
                    else:
                        continue
                if combine_ab and isinstance(name, tuple):
                    for sd, n in zip(save_dir, name):
                        if not exists(join(sd, 'func_labels')):
                            makedirs(join(sd, 'func_labels'))

                        label_path = join(sd, 'func_labels', f'{n}_{label.name}_{max_t}s_{trial}_func.label')
                        func_label.name = f'{n}_{label.name}_{max_t}s_{trial}_func'
                        func_label.color = None
                        mne.write_label(label_path, func_label)
                else:
                    if not exists(join(save_dir, 'func_labels')):
                        makedirs(join(save_dir, 'func_labels'))

                    label_path = join(save_dir, 'func_labels', f'{name}_{label.name}_{max_t}s_{trial}_func.label')
                    func_label.name = f'{name}_{label.name}_{max_t}s_{trial}_func'
                    func_label.color = None
                    mne.write_label(label_path, func_label)

                if label.name in save_dict:
                    save_dict[label.name].append(max_t)
                else:
                    save_dict.update({label.name: [max_t]})

                if label.name in func_labels_dict:
                    func_labels_dict[label.name].append(func_label)
                func_labels_dict.update({label.name: [func_label]})

                stc_func_label = n_stc.in_label(func_label)
                pca_func = n_stc.extract_label_time_course(func_label, src, mode='pca_flip')[0]

                # flip the pca so that the max power between tmin and tmax is positive
                tc *= np.sign(tc[np.argmax(np.abs(tc))])
                pca_func *= np.sign(pca_func[np.argmax(np.abs(tc))])

                # Filtering the data with a Savitzky-Golay filter
                tc_f = signal.savgol_filter(tc, 101, 5)
                pca_func_f = signal.savgol_filter(pca_func, 101, 5)

                max_val = tc_f[peak]

                # Save func_label_tc
                if combine_ab and isinstance(name, tuple):
                    for sd in save_dir:
                        tc_path = join(sd, 'func_label_tc', func_label.name)
                        np.save(tc_path, pca_func_f)
                else:
                    tc_path = join(save_dir, 'func_label_tc', func_label.name)
                    np.save(tc_path, pca_func_f)

                if len(peaks) == 1:
                    plt.figure(2)
                    plt.plot(1e3 * n_stc.times, tc_f, 'k',
                             label=f'Anatomical {label.name}')
                    save_path = join(figures_path, 'func_labels', 'label_time_course',
                                     f'{name[0]}_{label.name}{filter_string(lowpass, highpass)}-0.jpg')
                    plt.savefig(save_path, dpi=600)
                    plt.figure(3)
                    plt.plot(1e3 * stc_func_label.times, pca_func_f, 'b',
                             label=f'Functional {label.name}')
                    save_path = join(figures_path, 'func_labels', 'label_time_course',
                                     f'{name[0]}_{label.name}{filter_string(lowpass, highpass)}-1.jpg')
                    plt.savefig(save_path, dpi=600)
                    axes.plot(1e3 * n_stc.times, tc_f, 'k',
                              label=f'Anatomical {label.name}')
                    axes.plot(1e3 * stc_func_label.times, pca_func_f, 'b',
                              label=f'Functional {label.name}')
                    axes.plot(1e3 * max_t, max_val, 'rX',
                              label=f'{1e3 * max_t} ms used')
                    axes.legend()
                    axes.set_xlabel('time [ms]')
                    axes.set_ylabel('source amplitude (normal orientation)')
                    if combine_ab and isinstance(name, tuple):
                        axes.set_title(f'{name[0]}_{label.name}_{max_t}s_{filter_string(lowpass, highpass)}')
                    else:
                        axes.set_title(f'{name}_{label.name}_{max_t}s_{filter_string(lowpass, highpass)}')
                else:
                    axes[idx].plot(1e3 * n_stc.times, tc_f, 'k',
                                   label=f'Anatomical {label.name}')
                    axes[idx].plot(1e3 * stc_func_label.times, pca_func_f, 'b',
                                   label=f'Functional {label.name}')
                    axes[idx].plot(1e3 * max_t, max_val, 'rX',
                                   label=f'{1e3 * max_t} ms used')
                    axes[idx].legend()
                    axes[idx].set_xlabel('time [ms]')
                    axes[0].set_ylabel('source amplitude (normal orientation)')
                    if combine_ab and isinstance(name, tuple):
                        axes[idx].set_title(f'{name[0]}_{label.name}_{max_t}s_{filter_string(lowpass, highpass)}')
                    else:
                        axes[idx].set_title(f'{name}_{label.name}_{max_t}s_{filter_string(lowpass, highpass)}')
            plt.show()

            if save_plots:
                if not exists(join(figures_path, 'func_labels', 'label_time_course')):
                    makedirs(join(figures_path, 'func_labels', 'label_time_course'))
                if combine_ab and isinstance(name, tuple):
                    save_path = join(figures_path, 'func_labels', 'label_time_course',
                                     f'{name[0]}_{label.name}{filter_string(lowpass, highpass)}-tc.jpg')
                else:
                    save_path = join(figures_path, 'func_labels', 'label_time_course',
                                     f'{name}_{label.name}{filter_string(lowpass, highpass)}-tc.jpg')
                print(save_path)
                fig.savefig(save_path, dpi=600)

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

            plt.close('all')
            print('')

        if combine_ab and isinstance(name, tuple):
            title = name[0] + '-' + trial
        else:
            title = name + '-' + trial

        brain = Brain(subtomri, hemi='split', surf='inflated', title=title,
                      size=(1600, 800), subjects_dir=subjects_dir)
        colormap = plt.cm.get_cmap(name='hsv', lut=len(t_labels) + 1)
        # plot the original-labels
        #        for i, label in enumerate(t_labels):
        #            brain.add_label(label, borders=True, color='k', hemi=label.hemi)

        # plot the func_labels
        lh_y_cnt = 0.02
        rh_y_cnt = 0.02
        lh_x_cnt = 0.01
        rh_x_cnt = 0.01
        for i, f_name in enumerate(func_labels_dict):
            color = colormap(i)[:3]
            f_labels = func_labels_dict[f_name]
            for f_label in f_labels:
                brain.add_label(f_label, hemi=f_label.hemi,
                                color=color)
            t = save_dict[f_name]
            try:
                if '-lh' in f_name:
                    # noinspection PyTypeChecker
                    brain.add_text(x=lh_x_cnt, y=lh_y_cnt, text=f_name + ':' + str(t),
                                   color=color, name=f_name, font_size=8,
                                   col=0)
                    if round(lh_x_cnt, 2) == 0.71:
                        lh_x_cnt = 0.01
                        lh_y_cnt += 0.02
                    else:
                        lh_x_cnt += 0.35
                    if round(lh_y_cnt, 2) == 0.24:
                        lh_y_cnt = 0.72

                if '-rh' in f_name:
                    brain.add_text(x=rh_x_cnt, y=rh_y_cnt, text=f_name + ':' + str(t),
                                   color=color, name=f_name, font_size=8,
                                   col=1)
                    if round(rh_x_cnt, 2) == 0.71:
                        rh_x_cnt = 0.01
                        rh_y_cnt += 0.02
                    else:
                        rh_x_cnt += 0.35
                    if round(rh_y_cnt, 2) == 0.3:
                        rh_y_cnt = 0.8

            except ValueError:
                print('Display Space for text exceeded')

        if save_plots:
            if not exists(join(figures_path, 'func_labels', 'brain_plots')):
                makedirs(join(figures_path, 'func_labels', 'brain_plots'))
            if combine_ab and isinstance(name, tuple):
                b_save_path = join(figures_path, 'func_labels', 'brain_plots',
                                   f'{name[0]}-{trial}{filter_string(lowpass, highpass)}-b.jpg')
            else:
                b_save_path = join(figures_path, 'func_labels', 'brain_plots',
                                   f'{name}-{trial}{filter_string(lowpass, highpass)}-b.jpg')
            brain.save_image(b_save_path)
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

        if combine_ab and isinstance(name, tuple):
            ut.dict_filehandler(name[0] + '-' + trial, 'func_label_lat', sub_script_path,
                                values=save_dict)
        else:
            ut.dict_filehandler(name + '-' + trial, 'func_label_lat', sub_script_path,
                                values=save_dict)
        plot.close_all()


# noinspection PyTypeChecker
@decor.topline
def func_label_processing(name, save_dir, lowpass, highpass,
                          save_plots, figures_path, subtomri, subjects_dir,
                          sub_script_path, ev_ids_label_analysis,
                          corr_threshold, fuse_ab):
    #     Label looks for Labels with similar time in area and merges with them
    #     Use the time_course-coherence!!!
    #     The goal is to make locally distinguished and functionally determined labels
    #     Further analysis with mne-source-space_coherence and connectivity

    if fuse_ab and isinstance(name, tuple):
        save_dir = save_dir[1]
    func_labels_dict, lat_dict = io.read_func_labels(save_dir, subtomri,
                                                     sub_script_path,
                                                     ev_ids_label_analysis)
    aparc_labels = mne.read_labels_from_annot(subtomri, parc='aparc',
                                              subjects_dir=subjects_dir)
    for ev_id in ev_ids_label_analysis:
        func_labels = {'lh': [], 'rh': []}
        for f_label in func_labels_dict[ev_id]:
            if f_label.hemi == 'lh':
                func_labels['lh'].append(f_label)
            if f_label.hemi == 'rh':
                func_labels['rh'].append(f_label)

        for hemi in func_labels:
            corr_labels = []
            tc_list = []
            idx_dict = {}
            # Adding the time course for each label and assuring the right assignment from idx to label
            for idx, f_label in enumerate(func_labels[hemi]):
                tc_path = join(save_dir, 'func_label_tc', f_label.name[:-3] + '.npy')
                tc = np.load(tc_path)
                tc_list.append(tc)
                idx_dict.update({str(idx): f_label.name})
            tc_array = np.asarray(tc_list)
            corr_mat = np.corrcoef(tc_array)

            # Make Diagonal and lower half = 0
            np.fill_diagonal(corr_mat, 0)
            for c in range(1, len(corr_mat)):
                corr_mat[c, :c + 1] = 0

            # Finding the correlated groups of subjects
            # First with searching over two dimensions for correlations
            for idx, x in enumerate(corr_mat):
                x_set = set()
                for y in range(len(x)):
                    if x[y] > corr_threshold and idx != y:
                        x_set.add(idx_dict[str(idx)])
                        x_set.add(idx_dict[str(y)])
                        for z_idx, z in enumerate(corr_mat[:, y]):
                            if z > corr_threshold and idx != z_idx and y != z_idx:
                                x_set.add(idx_dict[str(z_idx)])
                if len(x_set) != 0:
                    corr_labels.append(x_set)

            merged = True
            while merged:
                merged = False
                results = []
                while corr_labels:
                    # Here lies the Knackpunkt: When only one set is left, [1:] returns an empty list
                    common, rest = corr_labels[0], corr_labels[1:]
                    corr_labels = []
                    for x in rest:
                        if x.isdisjoint(common):
                            corr_labels.append(x)
                        else:
                            merged = True
                            common |= x
                    results.append(common)
                corr_labels = results

            # Plotting
            y_cnt = 0.02
            x_cnt = 0.01
            figure = mlab.figure(size=(800, 800))
            brain = Brain(subject_id=subtomri, hemi=hemi, surf='inflated',
                          subjects_dir=subjects_dir, figure=figure)
            colormap = plt.cm.get_cmap(name='hsv', lut=len(corr_labels) + 1)
            for i, l_group in enumerate(corr_labels):
                plt.figure()
                color = colormap(i)[:3]
                final_list = []
                for l in l_group:
                    tc_path = join(save_dir, 'func_label_tc', l[:-3] + '.npy')
                    tc = np.load(tc_path)
                    plt.plot(tc, label=l)
                    for label in func_labels[hemi]:
                        if label.name == l:
                            brain.add_label(label, color=color)
                            final_list.append(label)

                # Combine and Save the Label
                while len(final_list) > 1:
                    # !!! Here is a problem, labels seem to have sometimes different positions in the same source_space
                    try:
                        final_list[0] = final_list[0] + final_list[1]
                        final_list.remove(final_list[1])
                    except ValueError:
                        final_list.remove(final_list[1])

                final_label = final_list[0]
                center = final_label.center_of_mass(subject=subtomri,
                                                    restrict_vertices=True)
                #                final_label.smooth(subject=subtomri, subjects_dir=subjects_dir,
                #                                   n_jobs=-1)
                #                brain.add_label(final_label)

                for ap_label in aparc_labels:
                    if center in ap_label.vertices:
                        if fuse_ab and isinstance(name, tuple):
                            final_label_name = f'{name[0]}_{ap_label.name}_final-func'
                        else:
                            final_label_name = f'{name}_{ap_label.name}_final-func'
                        ap_name = ap_label.name

                final_label_path = join(save_dir, 'func_labels',
                                        final_label_name)
                mne.write_label(final_label_path, final_label)

                # noinspection PyTypeChecker
                brain.add_text(x=x_cnt, y=y_cnt, text=ap_name,
                               color=color, font_size=8, name=str(i))
                if round(x_cnt, 2) == 0.71:
                    x_cnt = 0.01
                    y_cnt += 0.02
                else:
                    x_cnt += 0.35
                if round(y_cnt, 2) == 0.24:
                    y_cnt = 0.72
                plt.title(final_label_name)
                plt.legend()
                plt.show()

                # Saving the plots
                if save_plots:
                    if not exists(join(figures_path, 'func_labels', 'group_time_course')):
                        makedirs(join(figures_path, 'func_labels', 'group_time_course'))
                    if fuse_ab and isinstance(name, tuple):
                        save_path = join(figures_path, 'func_labels', 'group_time_course',
                                         f'{name[0]}-{ev_id}{filter_string(lowpass, highpass)}_{str(i)}-{hemi}-tc.jpg')
                    else:
                        save_path = join(figures_path, 'func_labels', 'group_time_course',
                                         f'{name}-{ev_id}{filter_string(lowpass, highpass)}_{str(i)}-{hemi}-tc.jpg')
                    plt.savefig(save_path, dpi=600)

                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

            if save_plots:
                if not exists(join(figures_path, 'func_labels', 'group_brain_plots')):
                    makedirs(join(figures_path, 'func_labels', 'group_brain_plots'))
                if fuse_ab and isinstance(name, tuple):
                    b_save_path = join(figures_path, 'func_labels', 'group_brain_plots',
                                       f'{name[0]}-{ev_id}{filter_string(lowpass, highpass)}-{hemi}-b.jpg')
                else:
                    b_save_path = join(figures_path, 'func_labels', 'group_brain_plots',
                                       f'{name}-{ev_id}{filter_string(lowpass, highpass)}-{hemi}-b.jpg')
                brain.save_image(b_save_path)

            plot.close_all()


@decor.topline
def func_label_ctf_ps(name, save_dir, lowpass, highpass, subtomri,
                      subjects_dir, parcellation_orig):
    label_origin = ['S_central-lh', 'S_central-rh', 'S_circular_insula_sup-lh',
                    'S_circular_insula_sup-rh']

    forward = io.read_forward(name, save_dir)
    labels = mne.read_labels_from_annot(subtomri, subjects_dir=subjects_dir,
                                        parc=parcellation_orig)
    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    labels_list = []
    for label in [l for l in labels if l.name in label_origin]:
        labels_list.append(label)
        print(labels_list)
    snr = 3.0
    lambda2 = 1.0 / snr ** 2
    mode = 'svd'
    n_svd_comp = 1

    inverse_method = 'MNE'  # can be 'MNE', 'dSPM', or 'sLORETA'

    stc_psf_meg, _ = mne.minimum_norm.point_spread_function(
        inverse_operator, forward, inverse_method=inverse_method, labels=labels,
        lambda2=lambda2, pick_ori='normal', mode=mode, n_svd_comp=n_svd_comp)


@decor.topline
def label_power_phlck(name, save_dir, lowpass, highpass, baseline, tfr_freqs,
                      subtomri, target_labels, parcellation,
                      ev_ids_label_analysis, n_jobs,
                      save_plots, figures_path):
    # Compute a source estimate per frequency band including and excluding the
    # evoked response
    freqs = tfr_freqs  # define frequencies of interest
    n_cycles = freqs / 3.  # different number of cycle per frequency
    labels = mne.read_labels_from_annot(subtomri, parc=parcellation)
    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)

    for ev_id in ev_ids_label_analysis:
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)[ev_id]
        # subtract the evoked response in order to exclude evoked activity
        epochs_induced = epochs.copy().subtract_evoked()

        for hemi in target_labels:
            for label in [l for l in labels if l.name in target_labels[hemi]]:
                print(label.name)
                # compute the source space power and the inter-trial coherence
                #                power, itc = mne.minimum_norm.source_induced_power(
                #                    epochs, inverse_operator, freqs, label, baseline=baseline,
                #                    baseline_mode='percent', n_cycles=n_cycles, n_jobs=n_jobs)

                power_ind, itc_ind = mne.minimum_norm.source_induced_power(
                    epochs_induced, inverse_operator, freqs, label, baseline=baseline,
                    baseline_mode='percent', n_cycles=n_cycles, n_jobs=n_jobs)

                #                power = np.mean(power, axis=0)  # average over sources
                #                itc = np.mean(itc, axis=0)  # average over sources

                power_ind = np.mean(power_ind, axis=0)  # average over sources
                itc_ind = np.mean(itc_ind, axis=0)  # average over sources

                # power_path = join(save_dir, f'{name}_{label.name}_{filter_string(lowpass, highpass)}_{ev_id}_pw-tfr.npy')
                # itc_path = join(save_dir, f'{name}_{label.name}_{filter_string(lowpass, highpass)}_{ev_id}_itc-tfr.npy')
                power_ind_path = join(save_dir,
                                      f'{name}_{label.name}_{filter_string(lowpass, highpass)}_{ev_id}_pw-ind-tfr.npy')
                itc_ind_path = join(save_dir,
                                    f'{name}_{label.name}_{filter_string(lowpass, highpass)}_{ev_id}_itc-ind-tfr.npy')

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
                           extent=[times[0], times[-1], freqs[0], freqs[-1]],
                           aspect='auto', origin='lower', vmin=0., vmax=10., cmap='RdBu_r')
                plt.xlabel('Time (s)')
                plt.ylabel('Frequency (Hz)')
                plt.title('Power induced')
                plt.colorbar()

                plt.subplot(1, 2, 2)
                plt.imshow(itc_ind,
                           extent=[times[0], times[-1], freqs[0], freqs[-1]],
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
                                     name + '_' + label.name + '_power_' + \
                                     ev_id + filter_string(lowpass, highpass) + '.jpg')
                    plt.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

                plot.close_all()


@decor.topline
def grand_avg_label_power(grand_avg_dict, ev_ids_label_analysis,
                          data_path, lowpass, highpass,
                          target_labels, save_dir_averages):
    for key in grand_avg_dict:
        #        powers = {}
        #        itcs = {}
        powers_ind = {}
        itcs_ind = {}

        for ev_id in ev_ids_label_analysis:
            #            powers.update({ev_id:{}})
            #            itcs.update({ev_id:{}})
            powers_ind.update({ev_id: {}})
            itcs_ind.update({ev_id: {}})
            for hemi in target_labels:
                for label_name in target_labels[hemi]:
                    #                    powers[ev_id].update({label_name:[]})
                    #                    itcs[ev_id].update({label_name:[]})
                    powers_ind[ev_id].update({label_name: []})
                    itcs_ind[ev_id].update({label_name: []})

        for name in grand_avg_dict[key]:
            save_dir = join(data_path, name)
            power_dict = io.read_label_power(name, save_dir, lowpass, highpass,
                                             ev_ids_label_analysis, target_labels)
            for ev_id in ev_ids_label_analysis:
                for hemi in target_labels:
                    for label_name in target_labels[hemi]:
                        #                        powers[ev_id][label_name].append(power_dict[ev_id][label_name]['power'])
                        #                        itcs[ev_id][label_name].append(power_dict[ev_id][label_name]['itc'])
                        powers_ind[ev_id][label_name].append(power_dict[ev_id][label_name]['power_ind'])
                        itcs_ind[ev_id][label_name].append(power_dict[ev_id][label_name]['itc_ind'])
        for ev_id in ev_ids_label_analysis:
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


@decor.topline
def apply_morph(name, save_dir, lowpass, highpass, subjects_dir, subtomri,
                inverse_method, overwrite, morph_to, source_space_method,
                event_id):
    stcs = io.read_source_estimates(name, save_dir, lowpass, highpass, inverse_method,
                                    event_id)
    morph = io.read_morph(subtomri, morph_to, source_space_method, subjects_dir)

    for trial_type in stcs:
        stc_morphed_name = name + filter_string(lowpass, highpass) + '_' + \
                           trial_type + '_' + inverse_method + '_morphed'
        stc_morphed_path = join(save_dir, stc_morphed_name)

        if overwrite or not isfile(stc_morphed_path + '-lh.stc'):
            stc_morphed = morph.apply(stcs[trial_type])
            stc_morphed.save(stc_morphed_path)

        else:
            print('morphed source estimates for: ' + stc_morphed_path + \
                  ' already exists')


@decor.topline
def apply_morph_normal(name, save_dir, lowpass, highpass, subjects_dir, subtomri,
                       inverse_method, overwrite, morph_to, source_space_method,
                       event_id):
    stcs = io.read_normal_source_estimates(name, save_dir, lowpass, highpass, inverse_method,
                                           event_id)
    morph = io.read_morph(subtomri, morph_to, source_space_method, subjects_dir)

    for trial_type in stcs:
        stc_morphed_name = name + filter_string(lowpass, highpass) + '_' + \
                           trial_type + '_' + inverse_method + '_morphed_normal'
        stc_morphed_path = join(save_dir, stc_morphed_name)

        if overwrite or not isfile(stc_morphed_path + '-lh.stc'):
            stc_morphed = morph.apply(stcs[trial_type])
            stc_morphed.save(stc_morphed_path)

        else:
            print('morphed source estimates for: ' + stc_morphed_path + \
                  ' already exists')


@decor.topline
def source_space_connectivity(name, save_dir, lowpass, highpass,
                              subtomri, subjects_dir, parcellation,
                              target_labels, con_methods, con_fmin, con_fmax,
                              n_jobs, overwrite, ica_evokeds, ev_ids_label_analysis):
    info = io.read_info(name, save_dir)
    if ica_evokeds:
        all_epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
    else:
        all_epochs = io.read_epochs(name, save_dir, lowpass, highpass)
    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    src = inverse_operator['src']

    for ev_id in ev_ids_label_analysis:
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

        actual_labels = [l for l in labels if l.name in target_labels['lh']
                         or l.name in target_labels['rh']]

        # Average the source estimates within each label using sign-flips to reduce
        # signal cancellations, also here we return a generator

        label_ts = mne.extract_label_time_course(stcs, actual_labels,
                                                 src, mode='mean_flip',
                                                 return_generator=True)

        sfreq = info['sfreq']  # the sampling frequency
        con, freqs, times, n_epochs, n_tapers = mne.connectivity.spectral_connectivity(
            label_ts, inverse_method=con_methods, mode='multitaper', sfreq=sfreq, fmin=con_fmin,
            fmax=con_fmax, faverage=True, mt_adaptive=True, n_jobs=n_jobs)

        # con is a 3D array, get the connectivity for the first (and only) freq. band
        # for each con_method
        con_res = dict()
        for con_method, c in zip(con_methods, con):
            con_res[con_method] = c[:, :, 0]

            # save to .npy file
            file_name = name + filter_string(lowpass, highpass) + \
                        '_' + str(con_fmin) + '-' + str(con_fmax) + '_' + con_method \
                        + '-' + ev_id
            file_path = join(save_dir, file_name)
            if overwrite or not isfile(file_path):
                np.save(file_path, con_res[con_method])
            else:
                print('connectivity_measures for for: ' + file_path + \
                      ' already exists')


@decor.topline
def grand_avg_morphed(grand_avg_dict, data_path, inverse_method, save_dir_averages,
                      lowpass, highpass, event_id):
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
                stcs = io.read_morphed_source_estimates(name, save_dir, lowpass,
                                                        highpass, inverse_method, event_id)
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
                               key + '_' + trial + \
                               filter_string(lowpass, highpass) + \
                               '-grand_avg')
                trial_average.save(ga_path)
        # clear memory
        gc.collect()


@decor.topline
def grand_avg_normal_morphed(grand_avg_dict, data_path, inverse_method, save_dir_averages,
                             lowpass, highpass, event_id):
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
                stcs = io.read_morphed_normal_source_estimates(name, save_dir, lowpass,
                                                               highpass, inverse_method, event_id)
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
                               key + '_' + trial + \
                               filter_string(lowpass, highpass) + \
                               '-grand_avg-normal')
                trial_average.save(ga_path)
        # clear memory
        gc.collect()


# noinspection PyTypeChecker,PyTypeChecker
def grand_avg_func_labels(grand_avg_dict, lowpass, highpass,
                          save_dir_averages, event_id, ev_ids_label_analysis,
                          subjects_dir, source_space_method,
                          parcellation_orig, sub_script_path, save_plots,
                          label_origin, figures_path, n_std):
    global func_label
    figures_path_grand_averages = join(figures_path, 'grand_averages/source_space/stc')
    save_dir = join(save_dir_averages, 'stc')
    ga_dict = io.read_grand_avg_stcs_normal(lowpass, highpass, save_dir_averages, grand_avg_dict,
                                            event_id)

    src = io.read_source_space('fsaverage', subjects_dir, source_space_method)
    labels = mne.read_labels_from_annot('fsaverage', subjects_dir=subjects_dir,
                                        parc=parcellation_orig)
    for key in grand_avg_dict:
        for ev_id in ev_ids_label_analysis:
            n_stc = ga_dict[key][ev_id]

            save_dict = {}
            func_labels_dict = {}

            if not exists(join(save_dir, 'func_label_tc')):
                makedirs(join(save_dir, 'func_label_tc'))

            if label_origin == 'all':
                t_labels = labels
            else:
                t_labels = [l for l in labels if l.name in label_origin]

            for prog, label in enumerate(t_labels):
                print(label.name)
                print(f'Progress: {round(prog / len(t_labels) * 100, 2)}%')

                tc = n_stc.extract_label_time_course(label, src, mode='pca_flip')[0]
                f = signal.savgol_filter(tc, 101, 5)
                std = np.std(f)
                mean = np.mean(f)
                peaks, properties = signal.find_peaks(abs(f), height=n_std * std + mean, distance=10)
                peaks = peaks[:1]  # !!!Discarded possibility of several peaks
                if len(peaks) == 0:  # Only let significant peaks define a label
                    print(f'{label.name} doesn\'t wield a significant peak, current setting: prominence>{n_std}*std')
                    continue

                # noinspection PyTypeChecker
                fig, axes = plt.subplots(ncols=len(peaks), figsize=(18, 8), sharey=True,
                                         gridspec_kw={'hspace': 0.1, 'wspace': 0.1,
                                                      'left': 0.05, 'right': 0.95,
                                                      'top': 0.95, 'bottom': 0.05})

                for idx, peak in enumerate(peaks):
                    max_t = round(n_stc.times[peak], 3)
                    tmin = round(max_t - 0.01, 3)
                    tmax = round(max_t + 0.01, 3)
                    if tmin < n_stc.tmin:
                        diff = n_stc.tmin - tmin
                        tmin += diff
                        tmax += diff
                        print(f'peak too close to start, correcting + {diff}')
                    if tmax > n_stc.times[-1]:
                        diff = tmax - n_stc.times[-1]
                        tmin -= diff
                        tmax -= diff
                        print(f'peak too close to start, correcting - {diff}')
                    print(f'{tmin} - {tmax}s')
                    # Make an STC in the time interval of interest and take the mean
                    stc_mean = n_stc.copy().crop(tmin, tmax).mean()

                    # use the stc_mean to generate a functional label
                    # region growing is halted at 60% of the peak value within the
                    # anatomical label / ROI specified by aparc_label_name
                    stc_mean_label = stc_mean.in_label(label)
                    data = np.abs(stc_mean_label.data)
                    stc_mean_label.data[data < 0.6 * np.max(data)] = 0.

                    func_labels = mne.stc_to_label(stc_mean_label, src=src, smooth=True,
                                                   subjects_dir=subjects_dir, connected=True,
                                                   verbose='DEBUG')

                    for i in func_labels:
                        if len(i) > 0:
                            func_label = i[0]
                        else:
                            continue

                    if not exists(join(save_dir, 'func_labels', key)):
                        makedirs(join(save_dir, 'func_labels', key))

                    label_path = join(save_dir, 'func_labels', key, f'{key}_{label.name}_{max_t}s_{ev_id}_func.label')
                    func_label.name = f'{key}_{label.name}_{max_t}s_{ev_id}_func'
                    func_label.color = None
                    mne.write_label(label_path, func_label)

                    if label.name in save_dict:
                        save_dict[label.name].append(max_t)
                    else:
                        save_dict.update({label.name: [max_t]})

                    if label.name in func_labels_dict:
                        func_labels_dict[label.name].append(func_label)
                    func_labels_dict.update({label.name: [func_label]})

                    stc_func_label = n_stc.in_label(func_label)
                    pca_func = n_stc.extract_label_time_course(func_label, src, mode='pca_flip')[0]

                    # flip the pca so that the max power between tmin and tmax is positive
                    tc *= np.sign(tc[np.argmax(np.abs(tc))])
                    pca_func *= np.sign(pca_func[np.argmax(np.abs(tc))])

                    # Filtering the data with a Savitzky-Golay filter
                    tc_f = signal.savgol_filter(tc, 101, 5)
                    pca_func_f = signal.savgol_filter(pca_func, 101, 5)

                    max_val = tc_f[peak]

                    # Save func_label_tc
                    if not exists(join(save_dir, 'func_label_tc', key)):
                        makedirs(join(save_dir, 'func_label_tc', key))
                    tc_path = join(save_dir, 'func_label_tc', key, func_label.name)
                    np.save(tc_path, pca_func_f)

                    if len(peaks) == 1:
                        axes.plot(1e3 * n_stc.times, tc_f, 'k',
                                  label=f'Anatomical {label.name}')
                        axes.plot(1e3 * stc_func_label.times, pca_func_f, 'b',
                                  label=f'Functional {label.name}')
                        axes.plot(1e3 * max_t, max_val, 'rX',
                                  label=f'{1e3 * max_t} ms used')
                        axes.legend()
                        axes.set_xlabel('time [ms]')
                        axes.set_ylabel('source amplitude (normal orientation)')
                        axes.set_title(f'{key}_{label.name}_{max_t}s_{filter_string(lowpass, highpass)}')
                    else:
                        axes[idx].plot(1e3 * n_stc.times, tc_f, 'k',
                                       label=f'Anatomical {label.name}')
                        axes[idx].plot(1e3 * stc_func_label.times, pca_func_f, 'b',
                                       label=f'Functional {label.name}')
                        axes[idx].plot(1e3 * max_t, max_val, 'rX',
                                       label=f'{1e3 * max_t} ms used')
                        axes[idx].legend()
                        axes[idx].set_xlabel('time [ms]')
                        axes[0].set_ylabel('source amplitude (normal orientation)')
                        axes[idx].set_title(f'{key}_{label.name}_{max_t}s_{filter_string(lowpass, highpass)}')
                plt.show()

                if save_plots:
                    if not exists(join(figures_path_grand_averages, 'func_labels', 'label_time_course')):
                        makedirs(join(figures_path_grand_averages, 'func_labels', 'label_time_course'))
                    save_path = join(figures_path_grand_averages, 'func_labels', 'label_time_course',
                                     f'{key}_{label.name}{filter_string(lowpass, highpass)}-tc.jpg')
                    print(save_path)
                    fig.savefig(save_path, dpi=600)

                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

                plt.close('all')
                print('')

            title = key + '-' + ev_id

            brain = Brain('fsaverage', hemi='split', surf='inflated', title=title,
                          size=(1600, 800), subjects_dir=subjects_dir)
            colormap = plt.cm.get_cmap(name='hsv', lut=len(t_labels) + 1)
            # plot the original-labels
            #        for i, label in enumerate(t_labels):
            #            brain.add_label(label, borders=True, color='k', hemi=label.hemi)

            # plot the func_labels
            lh_y_cnt = 0.02
            rh_y_cnt = 0.02
            lh_x_cnt = 0.01
            rh_x_cnt = 0.01
            for i, f_name in enumerate(func_labels_dict):
                color = colormap(i)[:3]
                f_labels = func_labels_dict[f_name]
                for f_label in f_labels:
                    brain.add_label(f_label, hemi=f_label.hemi,
                                    color=color)
                try:
                    if '-lh' in f_name:
                        #                        brain.add_text(x=lh_x_cnt, y=lh_y_cnt, text=f_name+':'+str(t),
                        #                                   color=color, name=f_name, font_size=8,
                        #                                   col=0)
                        if round(lh_x_cnt, 2) == 0.71:
                            lh_x_cnt = 0.01
                            lh_y_cnt += 0.02
                        else:
                            lh_x_cnt += 0.35
                        if round(lh_y_cnt, 2) == 0.24:
                            lh_y_cnt = 0.72

                    if '-rh' in f_name:
                        #                        brain.add_text(x=rh_x_cnt, y=rh_y_cnt, text=f_name+':'+str(t),
                        #                                       color=color, name=f_name, font_size=8,
                        #                                       col=1)
                        if round(rh_x_cnt, 2) == 0.71:
                            rh_x_cnt = 0.01
                            rh_y_cnt += 0.02
                        else:
                            rh_x_cnt += 0.35
                        if round(rh_y_cnt, 2) == 0.3:
                            rh_y_cnt = 0.8

                except ValueError:
                    print('Display Space for text exceeded')

            if save_plots:
                if not exists(join(figures_path_grand_averages, 'func_labels', 'brain_plots')):
                    makedirs(join(figures_path_grand_averages, 'func_labels', 'brain_plots'))
                b_save_path = join(figures_path_grand_averages, 'func_labels', 'brain_plots',
                                   f'{key}-{ev_id}{filter_string(lowpass, highpass)}-b.jpg')
                brain.save_image(b_save_path)
            else:
                print('Not saving plots; set "save_plots" to "True" to save')

            ut.dict_filehandler(key + '-' + ev_id, 'func_label_lat', sub_script_path,
                                values=save_dict)
            plot.close_all()


def grand_avg_func_labels_processing(grand_avg_dict, lowpass, highpass,
                                     save_dir_averages, ev_ids_label_analysis,
                                     subjects_dir, sub_script_path, save_plots,
                                     figures_path, corr_threshold,
                                     tmin, tmax):
    figures_path_grand_averages = join(figures_path, 'grand_averages/source_space/stc')
    save_dir = join(save_dir_averages, 'stc')
    for key in grand_avg_dict:
        save_dir_flabels = join(save_dir, 'func_labels', key)
        func_labels_dict, lat_dict = io.read_func_labels(save_dir_flabels, 'fsaverage',
                                                         sub_script_path,
                                                         ev_ids_label_analysis,
                                                         grand_avg=True)
        #            aparc_labels = mne.read_labels_from_annot('fsaverage', parc='aparc',
        #                                                      subjects_dir=subjects_dir)
        for ev_id in ev_ids_label_analysis:
            func_labels = {'lh': [], 'rh': []}
            for f_label in func_labels_dict[ev_id]:
                if f_label.hemi == 'lh':
                    func_labels['lh'].append(f_label)
                if f_label.hemi == 'rh':
                    func_labels['rh'].append(f_label)

            for hemi in func_labels:
                corr_labels = []
                tc_list = []
                idx_dict = {}
                # Adding the time course for each label and assuring the right assignment from idx to label
                for idx, func_label in enumerate(func_labels[hemi]):
                    tc_path = join(save_dir, 'func_label_tc', key, func_label.name[:-3] + '.npy')
                    tc = np.load(tc_path)
                    tc_list.append(tc)
                    idx_dict.update({str(idx): func_label.name})
                tc_array = np.asarray(tc_list)
                corr_mat = np.corrcoef(tc_array)

                # Make Diagonal and lower half = 0
                np.fill_diagonal(corr_mat, 0)
                for c in range(1, len(corr_mat)):
                    corr_mat[c, :c + 1] = 0

                # Finding the correlated groups of subjects
                # First with searching over two dimensions for correlations
                for idx, x in enumerate(corr_mat):
                    x_set = set()
                    for y in range(len(x)):
                        if x[y] > corr_threshold and idx != y:
                            x_set.add(idx_dict[str(idx)])
                            x_set.add(idx_dict[str(y)])
                            for z_idx, z in enumerate(corr_mat[:, y]):
                                if z > corr_threshold and idx != z_idx and y != z_idx:
                                    x_set.add(idx_dict[str(z_idx)])
                    if len(x_set) != 0:
                        corr_labels.append(x_set)

                merged = True
                while merged:
                    merged = False
                    results = []
                    while corr_labels:
                        # Here lies the Knackpunkt: When only one set is left, [1:] returns an empty list
                        common, rest = corr_labels[0], corr_labels[1:]
                        corr_labels = []
                        for x in rest:
                            if x.isdisjoint(common):
                                corr_labels.append(x)
                            else:
                                merged = True
                                common |= x
                        results.append(common)
                    corr_labels = results

                # Plotting
                #                    y_cnt = 0.02
                #                    x_cnt = 0.01
                figure = mlab.figure(size=(800, 800))
                brain = Brain(subject_id='fsaverage', hemi=hemi, surf='inflated',
                              subjects_dir=subjects_dir, figure=figure)
                colormap = plt.cm.get_cmap(name='hsv', lut=len(corr_labels) + 1)
                brain.add_annotation('aparc')
                tc_avg_labels = []
                for i, l_group in enumerate(corr_labels):
                    #                        plt.figure()
                    color = colormap(i)[:3]
                    final_list = []
                    tcs = []
                    for l in l_group:
                        tc_path = join(save_dir, 'func_label_tc', key, l[:-3] + '.npy')
                        tc = np.load(tc_path)
                        tcs.append(tc)
                        for label in func_labels[hemi]:
                            if label.name == l:
                                final_list.append(label)
                    tcs_avg = tcs[0]
                    for r in range(1, len(tcs)):
                        tcs_avg += tcs[r]
                    tcs_avg /= len(tcs)
                    tc_avg_labels.append(tcs_avg)

                    # Combine and Save the Label
                    while len(final_list) > 1:
                        # !!! Here is a problem, labels seem to have sometimes different positions in same source_space
                        try:
                            final_list[0] = final_list[0] + final_list[1]
                            final_list.remove(final_list[1])
                        except ValueError:
                            final_list.remove(final_list[1])

                    final_label = final_list[0]
                    brain.add_label(final_label, color=color)
                #                        center = final_label.center_of_mass(subject='fsaverage',
                #                                                            restrict_vertices=True)
                #                        final_label.smooth(subject='fsaverage', subjects_dir=subjects_dir,
                #                                           n_jobs=-1)
                #                        brain.add_label(final_label)

                #                        for ap_label in aparc_labels:
                #                            if center in ap_label.vertices:
                #                                final_label_name = f'{key}_{ap_label.name}_final-func'
                #                                ap_name = ap_label.name

                #                        final_label_path = join(save_dir, 'func_labels', key,
                #                                                final_label.name)
                #                        mne.write_label(final_label_path, final_label)

                #                        brain.add_text(x=x_cnt, y=y_cnt, text=ap_name,
                #                                       color=color, font_size=8, name=str(i))
                #                        if round(x_cnt,2) == 0.71:
                #                            x_cnt = 0.01
                #                            y_cnt +=0.02
                #                        else:
                #                            x_cnt += 0.35
                #                        if round(y_cnt,2) == 0.24:
                #                            y_cnt = 0.72
                #                        plt.title(final_label_name)
                #                        plt.legend()
                #                        plt.show()
                plt.figure()
                times = np.arange(tmin, tmax + 0.001, 0.001)
                for i, tca in enumerate(tc_avg_labels):
                    color = colormap(i)[:3]
                    plt.plot(times, tca, color=color)
                    plt.xlabel('Time [ms]')
                    plt.ylabel('Source Amplitude')
                    plt.title = hemi
                # Saving the plots
                if save_plots:
                    if not exists(join(figures_path_grand_averages, 'func_labels', 'group_time_course')):
                        makedirs(join(figures_path_grand_averages, 'func_labels', 'group_time_course'))
                    save_path = join(figures_path_grand_averages, 'func_labels', 'group_time_course',
                                     f'{key}-{ev_id}{filter_string(lowpass, highpass)}_{hemi}-tc.jpg')
                    plt.savefig(save_path, dpi=600)

                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

                if save_plots:
                    if not exists(join(figures_path_grand_averages, 'func_labels', 'group_brain_plots')):
                        makedirs(join(figures_path_grand_averages, 'func_labels', 'group_brain_plots'))
                    b_save_path = join(figures_path_grand_averages, 'func_labels', 'group_brain_plots',
                                       f'{key}-{ev_id}{filter_string(lowpass, highpass)}-{hemi}-b.jpg')
                    brain.save_image(b_save_path)

                plot.close_all()


@decor.topline
def grand_avg_connect(grand_avg_dict, data_path, con_methods,
                      con_fmin, con_fmax, save_dir_averages,
                      lowpass, highpass, ev_ids_label_analysis):
    for key in grand_avg_dict:
        for ev_id in ev_ids_label_analysis:
            con_methods_dict = {}
            print(f'grand_average for {key}')
            for name in grand_avg_dict[key]:
                save_dir = join(data_path, name)
                print(f'Add {name} to grand_average')

                con_dict = io.read_connect(name, save_dir, lowpass,
                                           highpass, con_methods,
                                           con_fmin, con_fmax, ev_ids_label_analysis)[ev_id]

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
                                   key + '_' + inverse_method + \
                                   filter_string(lowpass, highpass) + \
                                   '-grand_avg_connect' + '-' + ev_id)
                    np.save(ga_path, average)


# ==============================================================================
# STATISTICS
# ==============================================================================
@decor.topline
def statistics_source_space(morphed_data_all, save_dir_averages,
                            independent_variable_1,
                            independent_variable_2,
                            time_window, n_permutations, lowpass, highpass, overwrite):
    cluster_name = independent_variable_1 + '_vs_' + independent_variable_2 + \
                   filter_string(lowpass, highpass) + '_time_' + \
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

        t_obs, clusters, cluster_p_values, h0 = \
            mne.stats.permutation_cluster_test(statistics_list,
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
        print('cluster permutation: ' + cluster_path + \
              ' already exists')


@decor.topline
def corr_ntr(name, save_dir, lowpass, highpass, exec_ops, ermsub,
             subtomri, ica_evokeds, save_plots, figures_path):
    info = io.read_info(name, save_dir)

    if ica_evokeds:
        epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from ICA-Epochs after applied SSP')
    elif exec_ops['apply_ssp_er'] and ermsub != 'None':
        epochs = io.read_ssp_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from SSP_ER-Epochs')
    elif exec_ops['apply_ssp_clm']:
        epochs = io.read_ssp_clm_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds form SSP_Clm-Epochs')
    elif exec_ops['apply_ssp_eog'] and 'EEG 001' in info['ch_names']:
        epochs = io.read_ssp_eog_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from SSP_EOG-Epochs')
    elif exec_ops['apply_ssp_ecg'] and 'EEG 001' in info['ch_names']:
        epochs = io.read_ssp_ecg_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from SSP_ECG-Epochs')
    else:
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from (normal) Epochs')
    # Analysis for each trial_type
    labels = mne.read_labels_from_annot(subtomri, parc='aparc.a2009s')
    target_labels = ['S_central-lh']
    ch_labels = []

    for label in labels:
        if label.name in target_labels:
            ch_labels.append(label)

    inv_op = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    src = inv_op['src']

    for l in ch_labels:
        ep_tr = epochs[0]
        ep_tr.crop(0, 0.3)
        ep_len = len(ep_tr) // 2 * 2  # Make sure ep_len is even
        idxs = range(ep_len)

        y = []
        x = []

        # select randomly k epochs for t times

        for k in range(1, int(ep_len / 2)):  # Compare k epochs

            print(f'Iteration {k} of {int(ep_len / 2)}')
            ep_rand = ep_tr[random.sample(idxs, k * 2)]
            ep1 = ep_rand[:k]
            ep2 = ep_rand[k:]
            avg1 = ep1.average()
            avg2 = ep2.average()
            x.append(k)

            stc1 = mne.minimum_norm.apply_inverse(avg1, inv_op, inverse_method='dSPM', pick_ori='normal')
            stc2 = mne.minimum_norm.apply_inverse(avg2, inv_op, inverse_method='dSPM', pick_ori='normal')

            print(f'Label:{l.name}')
            mean1 = stc1.extract_label_time_course(l, src, mode='pca_flip')
            mean2 = stc2.extract_label_time_course(l, src, mode='pca_flip')

            coef = abs(np.corrcoef(mean1, mean2)[0, 1])
            y.append(coef)

        plt.figure()
        plt.plot(x, y)
        plt.title(name)

        if save_plots:
            save_path = join(figures_path, 'correlation_ntr', name + \
                             filter_string(lowpass, highpass) + \
                             '_' + l.name + '.jpg')
            plt.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


def get_meas_order(sub_files_dict, data_path, sub_script_path):
    # Get measurement order in time
    for sub in sub_files_dict:
        ts = list()
        for name in sub_files_dict[sub]:
            save_dir = join(data_path, name)
            i = io.read_info(name, save_dir)
            ts.append(i['meas_date'][0])
        ts.sort()
        for name in sub_files_dict[sub]:
            save_dir = join(data_path, name)
            i = io.read_info(name, save_dir)
            idx = ts.index(i['meas_date'][0])
            ut.dict_filehandler(name, 'meas_order', sub_script_path, values=idx)
