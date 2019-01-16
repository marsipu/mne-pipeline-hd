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
from os.path import join, isfile, isdir
from scipy import stats
from os import makedirs, listdir, environ
import sys
from . import io_functions as io
from . import decorators as decor
import pickle
import subprocess
import autoreject as ar
from collections import Counter
from nilearn.plotting import plot_anat
from matplotlib import pyplot as plt
from itertools import combinations
from functools import reduce


def filter_string(lowpass, highpass):

    if highpass!=None and highpass!=0:
        filter_string = '_' + str(highpass) + '-' + str(lowpass) + '_Hz'
    else:
        filter_string = '_' + str(lowpass) + '_Hz'

    return filter_string

#==============================================================================
# OPERATING SYSTEM COMMANDS
#==============================================================================
@decor.topline
def populate_data_directory(home_path, project_name, data_path, figures_path,
                            subjects_dir, subjects, all_event_ids):
    
    ## create MEG and MRI paths
    for subject in subjects:

        full_path_MEG = join(home_path, project_name, data_path, subject)

        ## create MEG dirs
        try:
            makedirs(full_path_MEG)
            print(full_path_MEG + ' has been created')
        except OSError as exc:
            if exc.errno == 17: ## dir already exists
                pass

    ## also create grand averages path with a statistics folder
    grand_average_path = join(home_path, project_name, data_path,
                              'grand_averages/statistics')
    try:
        makedirs(grand_average_path)
        print(grand_average_path + ' has been created')
    except OSError as exc:
        if exc.errno == 17: ## dir already exists
            pass

    ##also create erm(empty_room_measurements)paths
    erm_path = join(home_path, project_name, data_path,
                              'empty_room_data')
    try:
        makedirs(erm_path)
        print(erm_path + ' has been created')
    except OSError as exc:
        if exc.errno == 17: ## dir already exists
            pass

    ## also create figures path
    figure_subfolders = ['epochs', 'epochs_image', 'epochs_topo', 'evoked_image',
                         'power_spectra_raw', 'power_spectra_epochs',
                         'power_spectra_topo', 'evoked_butterfly', 'evoked_field',
                         'evoked_topo', 'evoked_topomap', 'evoked_joint', 'evoked_white',
                         'ica', 'ssp', 'stcs', 'vec_stcs', 'transformation', 'source_space',
                         'noise_covariance', 'events', 'label_time_course', 'ECD',
                         'stcs_movie', 'bem', 'snr', 'statistics']
    
    for figure_subfolder in figure_subfolders:
        full_path_figures = join(home_path, project_name, figures_path, figure_subfolder)
        ## create figure paths
        try:
            makedirs(full_path_figures)
            print(full_path_figures + ' has been created')
        except OSError as exc:
            if exc.errno == 17: ## dir already exists
                pass
    
    # create subfolders for event_ids
    trialed_folders = ['epochs', 'power_spectra_epochs', 'epochs_image', 'epochs_topo', 'evoked_butterfly',
                     'evoked_field', 'evoked_topo', 'evoked_topomap', 'evoked_image',
                     'evoked_joint', 'evoked_white', 'label_time_course', 'ECD',
                     'stcs', 'vec_stcs','stcs_movie', 'snr']   
    
    for ev_id in all_event_ids:
        for tr in trialed_folders:
            subfolder_path = join(home_path, project_name, figures_path, tr, ev_id)
            try:
                makedirs(subfolder_path)
                print(subfolder_path + ' has been created')
            except OSError as exc:
                if exc.errno == 17: ## dir already exists
                    pass
    
    ## also create grand average figures path
    grand_averages_figures_path = join(home_path, project_name, figures_path,
                                      'grand_averages')
    figure_subfolders = ['sensor_space', 'source_space/statistics']
    for figure_subfolder in figure_subfolders:
        try:
            full_path = join(grand_averages_figures_path, figure_subfolder)
            makedirs(full_path)
            print(full_path + ' has been created')
        except OSError as exc:
            if exc.errno == 17: ## dir already exists
                pass

    ## also create FreeSurfer path
    freesurfer_path = join(home_path, project_name, subjects_dir)
    try:
        makedirs(freesurfer_path)
        print(freesurfer_path + ' has been created')
    except OSError as exc:
        if exc.errno == 17: ## dir already exists
            pass

@decor.topline
def populate_data_directory_small(home_path, project_name, data_path, figures_path,
                                  subjects_dir, subjects):

    ## create MEG and MRI paths
    for subject in subjects:

        full_path_MEG = join(home_path, project_name, data_path, subject)

        ## create MEG dirs
        try:
            makedirs(full_path_MEG)
            print(full_path_MEG + ' has been created')
        except OSError as exc:
            if exc.errno == 17: ## dir already exists
                pass

    ## also create grand averages path with a statistics folder
    grand_average_path = join(home_path, project_name, data_path,
                              'grand_averages/statistics')
    try:
        makedirs(grand_average_path)
        print(grand_average_path + ' has been created')
    except OSError as exc:
        if exc.errno == 17: ## dir already exists
            pass

    ##also create erm(empty_room_measurements)paths
    erm_path = join(home_path, project_name, data_path,
                              'empty_room_data')
    try:
        makedirs(erm_path)
        print(erm_path + ' has been created')
    except OSError as exc:
        if exc.errno == 17: ## dir already exists
            pass

    ## also create figures path
    figure_subfolders = ['epochs', 'epochs_image', 'epochs_topo', 'evoked_image',
                         'power_spectra_raw', 'power_spectra_epochs',
                         'power_spectra_topo', 'evoked_butterfly', 'evoked_field',
                         'evoked_topo', 'evoked_topomap', 'evoked_joint', 'evoked_white',
                         'ica', 'ssp', 'stcs', 'vec_stcs', 'transformation', 'source_space',
                         'noise_covariance', 'events', 'label_time_course', 'ECD',
                         'stcs_movie', 'bem', 'snr', 'statistics']
    
    for figure_subfolder in figure_subfolders:
        full_path_figures = join(home_path, project_name, figures_path, figure_subfolder)
        ## create figure paths
        try:
            makedirs(full_path_figures)
            print(full_path_figures + ' has been created')
        except OSError as exc:
            if exc.errno == 17: ## dir already exists
                pass
    
    ## also create grand average figures path
    grand_averages_figures_path = join(home_path, project_name, figures_path,
                                      'grand_averages')
    figure_subfolders = ['sensor_space', 'source_space/statistics']
    for figure_subfolder in figure_subfolders:
        try:
            full_path = join(grand_averages_figures_path, figure_subfolder)
            makedirs(full_path)
            print(full_path + ' has been created')
        except OSError as exc:
            if exc.errno == 17: ## dir already exists
                pass

    ## also create FreeSurfer path
    freesurfer_path = join(home_path, project_name, subjects_dir)
    try:
        makedirs(freesurfer_path)
        print(freesurfer_path + ' has been created')
    except OSError as exc:
        if exc.errno == 17: ## dir already exists
            pass
        
#==============================================================================
# PREPROCESSING AND GETTING TO EVOKED AND TFR
#==============================================================================
@decor.topline
def filter_raw(name, save_dir, lowpass, highpass, overwrite, ermsub,
               data_path, n_jobs, enable_cuda):

    filter_name = name  + filter_string(lowpass, highpass) + '-raw.fif'
    filter_path = join(save_dir, filter_name)
    if overwrite or not isfile(filter_path):

        raw = io.read_raw(name, save_dir)

        if enable_cuda: #use cuda for filtering
            n_jobs = 'cuda'
        raw.filter(highpass, lowpass, n_jobs=n_jobs)

        filter_name = name  + filter_string(lowpass, highpass) + '-raw.fif'
        filter_path = join(save_dir, filter_name)
        raw.save(filter_path, overwrite=True)

    else:
        print('raw file: ' + filter_path + ' already exists')

    if ermsub!='None':
        erm_name = ermsub + '.fif'
        erm_path = join(data_path, 'empty_room_data', erm_name)
        erm_filter_name = ermsub + filter_string(lowpass, highpass) + '-raw.fif'
        erm_filter_path = join(data_path, 'empty_room_data', erm_filter_name)

        if not isfile(erm_filter_path) and ermsub!='None':

            erm_raw = mne.io.read_raw_fif(erm_path, preload=True)

            # Due to channel-deletion sometimes in HPI-Fitting-Process
            ch_list = set(erm_raw.info['ch_names']) & set(raw.info['ch_names'])
            erm_raw.pick_channels(ch_list)

            erm_raw.filter(highpass, lowpass)

            erm_raw.save(erm_filter_path, overwrite=True)
            print('ERM-Data filtered and saved')

        else:
            print('erm_raw file: ' + filter_path + ' already exists')

    else:
        print('no erm_file assigned')

@decor.topline
def find_events(name, save_dir, min_duration,
                adjust_timeline_by_msec, lowpass, highpass, overwrite):

    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)

    if overwrite or not isfile(events_path):
        
        try:
            raw = io.read_filtered(name, save_dir, lowpass, highpass)
        except FileNotFoundError:
            raw = io.read_raw(name, save_dir)

        # By Martin Schulz
        # Binary Coding of 6 Stim Channels in Biomagenetism Lab Heidelberg

        # prepare arrays
        events = np.ndarray(shape=(0,3), dtype=np.int32)
        evs = list()
        evs_tol = list()


        # Find events for each stim channel, append sample values to list
        evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 001'])[:,0])
        evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 002'])[:,0])
        evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 003'])[:,0])
        evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 004'])[:,0])
        evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 005'])[:,0])
        evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 006'])[:,0])

        """
        #test events
        evs = [np.array([1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47,49,51,53,55,57,59,61,63])*10,
               np.array([2,3,6,7,10,11,14,15,18,19,22,23,26,27,30,31,34,35,38,39,42,43,46,47,50,51,54,55,58,59,62,63])*10,
               np.array([4,5,6,7,12,13,14,15,20,21,22,23,28,29,30,31,36,37,38,39,44,45,46,47,52,53,54,55,60,61,62,63])*10,
               np.array([8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,40,41,42,43,44,45,46,47,56,57,58,59,60,61,62,63])*10,
               np.array([16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63])*10,
               np.array([32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63])*10]
        """

        for i in evs:

            # delete events in each channel, which are too close too each other (1ms)
            too_close = np.where(np.diff(i)<=1)
            if np.size(too_close)>=1:
                print(f'Two close events (1ms) at samples {i[too_close] + raw.first_samp}, first deleted')
                i = np.delete(i,too_close,0)
                evs[evs.index(i)] = i

            # add tolerance to each value
            i_tol = np.ndarray(shape = (0,1), dtype=np.int32)
            for t in i:
                i_tol = np.append(i_tol, t-1)
                i_tol = np.append(i_tol, t)
                i_tol = np.append(i_tol, t+1)

            evs_tol.append(i_tol)


        # Get events from combinated Stim-Channels
        equals = reduce(np.intersect1d, (evs_tol[0], evs_tol[1], evs_tol[2],
                                         evs_tol[3], evs_tol[4], evs_tol[5]))
        #elimnate duplicated events
        too_close = np.where(np.diff(equals)<=1)
        if np.size(too_close)>=1:
            equals = np.delete(equals,too_close,0)
            equals -= 1 # correction, because of shift with deletion

        for q in equals:
            if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
                events = np.append(events, [[q,0,63]], axis=0)


        for a,b,c,d,e in combinations(range(6), 5):
            equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c],
                                             evs_tol[d], evs_tol[e]))
            too_close = np.where(np.diff(equals)<=1)
            if np.size(too_close)>=1:
                equals = np.delete(equals,too_close,0)
                equals -= 1

            for q in equals:
                if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
                    events = np.append(events, [[q,0,int(2**a + 2**b + 2**c + 2**d + 2**e)]], axis=0)


        for a,b,c,d in combinations(range(6), 4):
            equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c], evs_tol[d]))
            too_close = np.where(np.diff(equals)<=1)
            if np.size(too_close)>=1:
                equals = np.delete(equals,too_close,0)
                equals -= 1

            for q in equals:
                if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
                    events = np.append(events, [[q,0,int(2**a + 2**b + 2**c + 2**d)]], axis=0)


        for a,b,c in combinations(range(6), 3):
            equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c]))
            too_close = np.where(np.diff(equals)<=1)
            if np.size(too_close)>=1:
                equals = np.delete(equals,too_close,0)
                equals -= 1

            for q in equals:
                if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
                    events = np.append(events, [[q,0,int(2**a + 2**b + 2**c)]], axis=0)


        for a,b in combinations(range(6), 2):
            equals = np.intersect1d(evs_tol[a], evs_tol[b])
            too_close = np.where(np.diff(equals)<=1)
            if np.size(too_close)>=1:
                equals = np.delete(equals,too_close,0)
                equals -= 1

            for q in equals:
                if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
                    events = np.append(events, [[q,0,int(2**a + 2**b)]], axis=0)


        # Get single-channel events
        for i in range(6):
            for e in evs[i]:
                if not e in events[:,0] and not e in events[:,0]+1 and not e in events[:,0]-1:
                    events = np.append(events, [[e,0,2**i]], axis=0)

        # stackoverflow way of sorting by only one column
        events[events[:,0].argsort()]

        # apply latency correction
        events[:, 0] = [ts + np.round(adjust_timeline_by_msec * 10**-3 * \
                    raw.info['sfreq']) for ts in events[:, 0]]

        ids = np.unique(events[:,2])
        print('unique ID\'s assigned: ',ids)

        if np.size(events)>0:
            mne.event.write_events(events_path, events)
        else:
            print('No events found')


    else:
        print('event file: '+ events_path + ' already exists')

@decor.topline
def find_eog_events(name, save_dir, eog_channel, eog_contamination):

    eog_events_name = name + '_eog-eve.fif'
    eog_events_path = join(save_dir, eog_events_name)

    raw = io.read_raw(name, save_dir)
    eog_events = mne.preprocessing.find_eog_events(raw, ch_name=eog_channel)

    mne.event.write_events(eog_events_path, eog_events)

    print(f'{len(eog_events)} detected')

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
              baseline, reject, flat, autoreject, overwrite_ar, bad_channels, decim,
              n_events, epoch_rejection, all_reject_channels, reject_eog_epochs, overwrite):

    epochs_name = name + filter_string(lowpass, highpass) + '-epo.fif'
    epochs_path = join(save_dir, epochs_name)
    if overwrite or not isfile(epochs_path):

        events = io.read_events(name, save_dir)
        raw = io.read_filtered(name, save_dir, lowpass, highpass)

        picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False,
                               eog=False, ecg=False, exclude=bad_channels)

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

        epochs = mne.Epochs(raw, events, event_id, tmin, tmax, baseline,
                            preload=True, picks=picks, proj=False,
                            decim=decim, on_missing='warning',reject_by_annotation=True)

        if autoreject:
            reject_value_path = join(save_dir, filter_string(lowpass, highpass) \
                                     + '_reject_value.py')
            print('Rejection with Autoreject')
            if overwrite_ar or not isfile(reject_value_path):

                reject = ar.get_rejection_threshold(epochs)

                with open(reject_value_path, 'w') as rv:
                    for key,value in reject.items():
                        rv.write(f'{key}:{value}\n')

            else:
                with open(reject_value_path, 'r') as rv:
                    reject = {}
                    for item in rv:
                        if ':' in item:
                            key,value = item.split(':', 1)
                            value = value[:-1]
                            reject[key] = float(value)

                print('Reading Rejection-Threshold from file')

        print('Rejection Threshold: %s' % reject)

        epochs.drop_bad(reject=reject, flat=flat)
        epochs.save(epochs_path)

        n_events.update({name:len(epochs)})
        epoch_rejection.update({name:epochs.drop_log_stats()})

        reject_channels = []
        log = epochs.drop_log

        for a in log:
            if a != []:
                for b in a:
                    reject_channels.append(b)
        c = Counter(reject_channels).most_common()
        all_reject_channels.update({name:c})

    else:
        print('epochs file: '+ epochs_path + ' already exists')

@decor.topline
def run_ssp_er(name, save_dir, lowpass, highpass, data_path, ermsub, bad_channels,
            eog_channel, ecg_channel, overwrite):

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
            print('ssp_epochs file: '+ ssp_epochs_path + ' already exists')

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
            print('ssp_epochs file: '+ ssp_epochs_path + ' already exists')

@decor.topline
def run_ssp_eog(name, save_dir, lowpass, highpass, n_jobs, eog_channel,
                    bad_channels, overwrite):

    info = io.read_info(name, save_dir)
    eog_events_name = name + '_eog-eve.fif'
    eog_events_path = join(save_dir, eog_events_name)

    if (eog_channel) in info['ch_names']:
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
            print('ssp_epochs file: '+ ssp_epochs_path + ' already exists')

@decor.topline
def run_ssp_ecg(name, save_dir, lowpass, highpass, n_jobs, ecg_channel,
                    bad_channels, overwrite):

    info = io.read_info(name, save_dir)
    ecg_events_name = name + '_ecg-eve.fif'
    ecg_events_path = join(save_dir, ecg_events_name)

    if (ecg_channel) in info['ch_names']:
        raw = io.read_raw(name, save_dir)

        ecg_proj, ecg_events = mne.preprocessing.compute_proj_ecg(
                raw, n_grad=1, average=True, n_jobs=n_jobs, bads=bad_channels,
                ch_name=ecg_channel, reject={'eeg':5e-3})

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
            print('ssp_epochs file: '+ ssp_epochs_path + ' already exists')
@decor.topline
def run_ica(name, save_dir, lowpass, highpass, eog_channel, ecg_channel,
            reject, flat, bad_channels, overwrite, autoreject):

    info = io.read_info(name, save_dir)

    if ('EEG 001') in info['ch_names']:

        ica_name = name + filter_string(lowpass, highpass) + '-ica.fif'
        ica_path = join(save_dir, ica_name)

        if overwrite or not isfile(ica_path):

            raw = io.read_filtered(name, save_dir, lowpass, highpass)
            picks = mne.pick_types(raw.info, meg=True, eeg=False, eog=False,
                           stim=False, exclude=bad_channels)

            ica = mne.preprocessing.ICA(n_components=10, method='fastica')

            if autoreject:
                reject_value_path = join(save_dir, filter_string(lowpass, highpass) \
                                     + '_reject_value.py')
                print('Rejection with Autoreject')
                with open(reject_value_path, 'r') as rv:
                    reject = {}
                    for item in rv:
                        if ':' in item:
                            key,value = item.split(':', 1)
                            value = value[:-1]
                            reject[key] = float(value)

                print('Reading Rejection-Threshold from file')

            print('Rejection Threshold: %s' % reject)

            ica.fit(raw, picks, reject=reject, flat=flat, reject_by_annotation=True)

            eog_epochs = mne.preprocessing.create_eog_epochs(raw, ch_name=eog_channel)
            ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, ch_name=ecg_channel)

            eog_indices, eog_scores = ica.find_bads_eog(eog_epochs, ch_name=eog_channel)
            ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs, ch_name=ecg_channel)
            print('EOG-Components: ', eog_indices)
            print('ECG-Components: ', ecg_indices)

            ica.exclude += eog_indices
            ica.exclude += ecg_indices

            ica.save(ica_path)

        else:
            print('ica file: '+ ica_path + ' already exists')
    else:
        print('No EEG-Channels to read EOG/EEG from')
        pass

@decor.topline
def apply_ica(name, save_dir, lowpass, highpass, overwrite):

    info = io.read_info(name, save_dir)

    if ('EEG 001') in info['ch_names']:

        ica_epochs_name = name + filter_string(lowpass, highpass) + '-ica-epo.fif'
        ica_epochs_path = join(save_dir, ica_epochs_name)

        if overwrite or not isfile(ica_epochs_path):

            epochs = io.read_epochs(name, save_dir, lowpass, highpass)
            ica = io.read_ica(name, save_dir, lowpass, highpass)

            ica_epochs = ica.apply(epochs)

            ica_epochs.save(ica_epochs_path)

        else:
            print('ica epochs file: '+ ica_epochs_path + ' already exists')

    else:
        print('No EEG-Channels to read EOG/EEG from')
        pass

@decor.topline
def ica_pure(name, save_dir, lowpass, highpass, overwrite, eog_channel,
             ecg_channel, layout, reject, flat, bad_channels, autoreject,
             overwrite_ar):

    ica_name = name + filter_string(lowpass, highpass) + '-pure-ica.fif'
    ica_path = join(save_dir, ica_name)

    if overwrite or not isfile(ica_path):

        raw = io.read_filtered(name, save_dir, lowpass, highpass)
        picks = mne.pick_types(raw.info, meg=True, eeg=False, eog=False,
                               stim=False, exclude=bad_channels)

        ica = mne.preprocessing.ICA(n_components=25, method='fastica')

        if autoreject:
            reject_value_path = join(save_dir, filter_string(lowpass, highpass) \
                                     + '_reject_value.py')
            print('Rejection with Autoreject')
            if overwrite_ar or not isfile(reject_value_path):

                reject = ar.get_rejection_threshold(raw)

                with open(reject_value_path, 'w') as rv:
                    for key,value in reject.items():
                        rv.write(f'{key}:{value}\n')     
                        
            else:
                with open(reject_value_path, 'r') as rv:
                    reject = {}
                    for item in rv:
                        if ':' in item:
                            key,value = item.split(':', 1)
                            value = value[:-1]
                            reject[key] = float(value)

            print('Reading Rejection-Threshold from file')

        ica.fit(raw, picks, reject=reject, flat=flat, reject_by_annotation=True)
        ica.save(ica_path)
        print(ica)
        
        
        ica.plot_components()
        ica.plot_overlay(raw)
        ica.plot_properties(raw)
        ica.plot_sourcesr(raw)
        
        """
        eog_epochs = mne.preprocessing.create_eog_epochs(raw, ch_name=eog_channel)
        ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, ch_name=ecg_channel)
        eog_average = eog_epochs.average()
        ecg_average = ecg_epochs.average()

        eog_indices, eog_scores = ica.find_bads_eog(eog_epochs, ch_name=eog_channel)
        ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs, ch_name=ecg_channel)
        

        ica.plot_scores(ecg_scores, exclude=ecg_indices, title=name)
        ica.plot_sources(ecg_average, exclude=ecg_indices)
        ica.plot_properties(ecg_epochs, picks=ecg_indices, topomap_args={'layout':layout})
        ica.plot_overlay(ecg_average, exclude=ecg_indices, show=False)

        ica.plot_scores(eog_scores, exclude=eog_indices, title=name)
        ica.plot_sources(eog_average, exclude=eog_indices)
        ica.plot_properties(eog_epochs, picks=eog_indices, topomap_args={'layout':layout})
        ica.plot_overlay(eog_average, exclude=eog_indices, show=False)

        ica.plot_sources(raw, title=name)

        try:
            ica.plot_components(title=name, layout=layout)

        except RuntimeError:
            print('No EEG-Electrodes(kind=3)digitized')
            pass
        """
    else:
        print('pure-ica file: '+ ica_path + ' already exists')

@decor.topline
def get_evokeds(name, save_dir, lowpass, highpass, operations_to_apply, ermsub,
                detrend, overwrite):

    evokeds_name = name + filter_string(lowpass, highpass) + '-ave.fif'
    evokeds_path = join(save_dir, evokeds_name)
    info = io.read_info(name, save_dir)

    if overwrite or not isfile(evokeds_path):
        if operations_to_apply['apply_ica'] and operations_to_apply['apply_ssp_er'] \
        and 'EEG 001' in info['ch_names']:
            epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from ICA-Epochs after applied SSP')
        elif operations_to_apply['apply_ica'] and 'EEG 001' in info['ch_names']:
            epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from ICA-Epochs')
        elif operations_to_apply['apply_ssp_er'] and ermsub!='None':
            epochs = io.read_ssp_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from SSP_ER-Epochs')
        elif operations_to_apply['apply_ssp_clm']:
            epochs = io.read_ssp_clm_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds form SSP_Clm-Epochs')
        elif operations_to_apply['apply_ssp_eog'] and 'EEG 001' in info['ch_names']:
            epochs = io.read_ssp_eog_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from SSP_EOG-Epochs')
        elif operations_to_apply['apply_ssp_ecg'] and 'EEG 001' in info['ch_names']:
            epochs = io.read_ssp_ecg_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from SSP_ECG-Epochs')
        else:
            epochs = io.read_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from (normal) Epochs')

        evokeds = []

        for trial_type in epochs.event_id:
            evoked = epochs[trial_type].average()
            if detrend:
                evoked.detrend(order=1)
            evokeds.append(evoked)

        mne.evoked.write_evokeds(evokeds_path, evokeds)

    else:
        print('evokeds file: '+ evokeds_path + ' already exists')

@decor.topline
def grand_average_evokeds(evoked_data_all, save_dir_averages, lowpass, highpass, which_file):

    grand_averages = dict()
    for trial_type in evoked_data_all:
        if evoked_data_all[trial_type]!=[]:
            grand_averages[trial_type] = \
                mne.grand_average(evoked_data_all[trial_type], interpolate_bads=False,
                                  drop_bads=True)

    for trial_type in grand_averages:
        grand_average_path = save_dir_averages + \
            trial_type +  filter_string(lowpass, highpass) + \
            '_' + which_file + '_grand_average-ave.fif'
        mne.evoked.write_evokeds(grand_average_path,
                                 grand_averages[trial_type])

@decor.topline
def TF_Morlet(name, save_dir, lowpass, highpass, TF_Morlet_Freqs, decim, n_jobs):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)
    n_cycles = TF_Morlet_Freqs / 2.
    power, itc = mne.time_frequency.tfr_morlet(epochs, freqs=TF_Morlet_Freqs, n_cycles=n_cycles)

    power.plot_topo(baseline=(-0.5, 0), mode='logratio', title='Average power')
    power.plot([82], baseline=(-0.5, 0), mode='logratio', title=power.ch_names[82])

#==============================================================================
# BASH OPERATIONS
#==============================================================================

## local function used in the bash commands below
def run_process_and_write_output(command, subjects_dir):
    environment = environ.copy()
    environment["SUBJECTS_DIR"] = subjects_dir
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               env=environment)
    ## write bash output in python console
    for c in iter(lambda: process.stdout.read(1), b''):
        sys.stdout.write(c.decode('utf-8'))

def win_run_process_and_write_output(command, subjects_dir):
# possible in shell to run bash -c or wsl, but calling freesurfer-functions is not possible
    win_command = 'wsl&ls'
    environment = environ.copy()
    environment["SUBJECTS_DIR"] = subjects_dir
    process = subprocess.run(win_command,stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,shell=True,env=environment)
    ## write bash output in python console
    print(process.stdout.decode('utf_8'))

def Test(subject, subjects_dir):

    command = 'echo ' + subject

    win_run_process_and_write_output(command, subjects_dir)

def import_mri(dicom_path, mri_subject, subjects_dir, n_jobs_freesurfer):
    files = listdir(dicom_path)
    first_file = files[0]
    ## check if import has already been done
    if not isdir(join(subjects_dir, mri_subject)):
        ## run bash command
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

    print('Running Watershed algorithm for: ' + mri_subject + \
          ". Output is written to the bem folder " + \
          "of the subject's FreeSurfer folder.\n" + \
          'Bash output follows below.\n\n')

    if overwrite:
        overwrite_string = '--overwrite'
    else:
        overwrite_string = ''
    ## watershed command
    command = ['mne_watershed_bem',
               '--subject', mri_subject,
               overwrite_string]

    run_process_and_write_output(command, subjects_dir)
    ## copy commands
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
        ## copy files from watershed into bem folder where MNE expects to
        # find them
        command = ['cp', '-v',
                   join(subjects_dir, mri_subject, 'bem', 'watershed',
                        this_surface['origin']),
                   join(subjects_dir, mri_subject, 'bem'    ,
                        this_surface['destination'])
                   ]
        run_process_and_write_output(command, subjects_dir)

def make_source_space(mri_subject, subjects_dir, source_space_method, overwrite):

    print('Making source space for ' + \
          'subject: ' + mri_subject + \
          ". Output is written to the bem folder" + \
          " of the subject's FreeSurfer folder.\n" + \
          'Bash output follows below.\n\n')

    if overwrite:
        overwrite_string = '--overwrite'
    else:
        overwrite_string = ''

    command = ['mne_setup_source_space',
               '--subject', mri_subject,
               '--' + source_space_method[0], str(source_space_method[1]),
               overwrite_string
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

    command = ['mne_make_scalp_surfaces',
               '--subject', mri_subject,
               overwrite_string]

    run_process_and_write_output(command, subjects_dir)

def make_bem_solutions(mri_subject, subjects_dir):

    print('Writing volume conductor for ' + \
          'subject: ' + mri_subject + \
          ". Output is written to the bem folder" + \
          " of the subject's FreeSurfer folder.\n" + \
          'Bash output follows below.\n\n')

    command = ['mne_setup_forward_model',
               '--subject', mri_subject,
               '--homog',
               '--surf',
               '--ico', '4'
               ]

    run_process_and_write_output(command, subjects_dir)

def make_morph_map(mri_subject, morph_to, subjects_dir):
    print('Writing morph map for ' + \
          'subject: ' + mri_subject + \
          ". Output is written to the Subjects_dir folder" + \
          'Bash output follows below.\n\n')

    command = ['mne_make_morph_maps',
    '--from', mri_subject,
    '--to', morph_to,]

    run_process_and_write_output(command, subjects_dir)

#==============================================================================
# MNE SOURCE RECONSTRUCTIONS
#==============================================================================
@decor.topline
def setup_source_space(mri_subject, subjects_dir, source_space_method, n_jobs,
                       overwrite):
    src_name = mri_subject + '_' + source_space_method + '-src.fif'
    src_path = join(subjects_dir, mri_subject, 'bem', src_name)

    if overwrite or not isfile(src_path):
        src = mne.setup_source_space(mri_subject, spacing=source_space_method,
                               surface='white', subjects_dir=subjects_dir,
                               add_dist=False, n_jobs=n_jobs)
        src.save(src_path, overwrite=True)

@decor.topline
def mri_coreg(name, save_dir, subtomri, subjects_dir):

    raw_name = name + '.fif'
    raw_path = join(save_dir, raw_name)
    
    try:
        trans = io.read_transformation(save_dir, subtomri)
        mne.gui.coregistration(subject=subtomri, inst=raw_path, trans=trans,
                               subjects_dir=subjects_dir, guess_mri_subject=False)
        
    except FileNotFoundError:
        print('No trans-File found')
        mne.gui.coregistration(subject=subtomri, inst=raw_path,
                               subjects_dir=subjects_dir, guess_mri_subject=False)        
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

        forward = mne.convert_forward_solution(forward, surf_ori=True)

        mne.write_forward_solution(forward_path, forward, overwrite)

    else:
        print('forward solution: ' + forward_path + ' already exists')

@decor.topline
def estimate_noise_covariance(name, save_dir, lowpass, highpass, overwrite, ermsub, data_path,
                              bad_channels, n_jobs, use_calm_cov):

    if use_calm_cov==True:

        print('Noise Covariance on 1-Minute-Calm')
        covariance_name = name + filter_string(lowpass, highpass) + '-clm-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            raw = io.read_filtered(name, save_dir, lowpass, highpass)
            raw.crop(tmin=5, tmax=50)
            raw.pick_types(exclude=bad_channels)

            noise_covariance = mne.compute_raw_covariance(raw, n_jobs=n_jobs)
            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: '+ covariance_path + \
                  ' already exists')

    elif ermsub=='None':

        print('Noise Covariance on Epochs')
        covariance_name = name + filter_string(lowpass, highpass) + '-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            epochs = io.read_epochs(name, save_dir, lowpass, highpass)

            noise_covariance = mne.compute_covariance(epochs, n_jobs=n_jobs)

            noise_covariance = mne.cov.regularize(noise_covariance,
                                                  epochs.info)

            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: '+ covariance_path + \
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

            noise_covariance = mne.compute_raw_covariance(erm, n_jobs=n_jobs)
            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: '+ covariance_path + \
                  ' already exists')

@decor.topline
def create_inverse_operator(name, save_dir, lowpass, highpass, overwrite, ermsub, use_calm_cov, fixed_src):

    inverse_operator_name = name + filter_string(lowpass, highpass) +  '-inv.fif'
    inverse_operator_path = join(save_dir, inverse_operator_name)

    if overwrite or not isfile(inverse_operator_path):

        info = io.read_info(name, save_dir)
        if use_calm_cov==True:
            noise_covariance = io.read_clm_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from 1-min Calm in raw')
        elif ermsub=='None':
            noise_covariance = io.read_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from Epochs')
        else:
            noise_covariance = io.read_erm_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from Empty-Room-Data')

        forward = io.read_forward(name, save_dir)

        inverse_operator = mne.minimum_norm.make_inverse_operator(
                            info, forward, noise_covariance, fixed=fixed_src)

        mne.minimum_norm.write_inverse_operator(inverse_operator_path,
                                                    inverse_operator)

    else:
        print('inverse operator file: '+ inverse_operator_path + \
              ' already exists')

@decor.topline
def source_estimate(name, save_dir, lowpass, highpass, method,
                    overwrite):

    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    to_reconstruct = io.read_evokeds(name, save_dir, lowpass, highpass)
    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    stcs = dict()

    snr = 3.0
    lambda2 = 1.0 / snr ** 2

    for to_reconstruct_index, evoked in enumerate(evokeds):
        stc_name = name + filter_string(lowpass, highpass) + '_' + evoked.comment + \
                '_' + method + '-lh.stc'
        stc_path = join(save_dir, stc_name)
        if overwrite or not isfile(stc_path):
            trial_type = evoked.comment

            stcs[trial_type] = mne.minimum_norm.apply_inverse(
                                        to_reconstruct[to_reconstruct_index],
                                        inverse_operator, lambda2,
                                        method=method, pick_ori=None)
        else:
            print('source estimates for: '+  stc_path + \
                  ' already exists')

    for stc in stcs:
        stc_name = name + filter_string(lowpass, highpass) + '_' + stc + '_' + method
        stc_path = join(save_dir, stc_name)
        if overwrite or not isfile(stc_path + '-lh.stc'):
            stcs[stc].save(stc_path)

@decor.topline
def vector_source_estimate(name, save_dir, lowpass, highpass, method,
                    overwrite):

    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    to_reconstruct = io.read_evokeds(name, save_dir, lowpass, highpass)
    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    stcs = dict()
    for to_reconstruct_index, evoked in enumerate(evokeds):
        stc_name = name + filter_string(lowpass, highpass) + '_' + evoked.comment + \
                '_' + method + '_vector' + '-lh.stc'
        stc_path = join(save_dir, stc_name)
        if overwrite or not isfile(stc_path):
            trial_type = evoked.comment

            stcs[trial_type] = mne.minimum_norm.apply_inverse(
                                        to_reconstruct[to_reconstruct_index],
                                        inverse_operator,
                                        method=method, pick_ori='vector')
        else:
            print('source estimates for: '+  stc_path + \
                  ' already exists')

    for stc in stcs:
        stc_name = name + filter_string(lowpass, highpass) + '_' + stc + '_' + method + '_vector'
        stc_path = join(save_dir, stc_name)
        if overwrite or not isfile(stc_path + '-lh.stc'):
            stcs[stc].save(stc_path)

@decor.topline
def ECD_fit(name, save_dir, lowpass, highpass, ermsub, subject, subjects_dir,
            subtomri, use_calm_cov, ECDs, n_jobs,
            target_labels, save_plots, figures_path):

    try:
        ECD = ECDs[name]

        evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)
        bem = io.read_bem_solution(subtomri, subjects_dir)
        trans = io.read_transformation(save_dir, subtomri)
        t1_path = io.path_fs_volume('T1', subtomri, subjects_dir)

        if use_calm_cov==True:
            noise_covariance = io.read_clm_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from 1-min Calm in raw')
        elif ermsub=='None':
            noise_covariance = io.read_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from Epochs')
        else:
            noise_covariance = io.read_erm_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from Empty-Room-Data')

        evoked = evokeds[0]
        for Dip in ECD:
            tmin, tmax = ECD[Dip]
            evoked_full = evoked.copy()
            cevk = evoked.copy().crop(tmin, tmax)

            dipole, data = mne.fit_dipole(cevk, noise_covariance, bem, trans,
                                    min_dist=3.0, n_jobs=4)

            figure = dipole.plot_locations(trans, subtomri, subjects_dir,
                                           mode='orthoview', idx='gof')
            plt.title(name, loc='right')

            fwd, stc = mne.make_forward_dipole(dipole, bem, cevk.info, trans)
            """pred_evoked = mne.simulation.simulate_evoked(fwd, stc, cevk.info, cov=None, nave=np.inf)
            """
            # find time point with highest GOF to plot
            best_idx = np.argmax(dipole.gof)
            best_time = dipole.times[best_idx]

            print(f'Highest GOF {dipole.gof[best_idx]:.2f}% at t={best_time*1000:.1f} ms with confidence volume {dipole.conf["vol"][best_idx]*100**3} cm^3')

            mri_pos = mne.head_to_mri(dipole.pos, subtomri, trans, subjects_dir)

            save_path_anat = join(figures_path, 'ECD', name + \
                                  filter_string(lowpass, highpass) + '_' + \
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
                    save_path = join(figures_path, 'ECD', name + \
                                         filter_string(lowpass, highpass) + '_' + \
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
def morph_data_to_fsaverage(name, save_dir, lowpass, highpass, subjects_dir, subject, subtomri,
                            method, overwrite, n_jobs, vertices_to, morph_to):

    stcs = io.read_source_estimates(name, save_dir,lowpass, highpass, method)

    subject_from = subtomri
    subject_to = morph_to
    stcs_morph = dict()

    for trial_type in stcs:
        stc_morph_name = name + filter_string(lowpass, highpass) + '_' + \
        trial_type +  '_' + method + '_morph'
        stc_morph_path = join(save_dir, stc_morph_name)

        if overwrite or not isfile(stc_morph_path + '-lh.stc'):
            stc_from = stcs[trial_type]
            stcs_morph[trial_type] = mne.morph_data(subject_from, subject_to,
                                                    stc_from, grade=vertices_to,
                                                    subjects_dir=subjects_dir,
                                                    n_jobs=n_jobs)
        else:
            print('morphed source estimates for: '+  stc_morph_path + \
                  ' already exists')

    for trial_type in stcs_morph:
        stc_morph_name = name + filter_string(lowpass, highpass) + '_' + \
        trial_type +  '_' + method + '_morph'
        stc_morph_path = join(save_dir, stc_morph_name)
        if overwrite or not isfile(stc_morph_path + '-lh.stc'):
            stcs_morph[trial_type].save(stc_morph_path)

@decor.topline
def morph_data_to_fsaverage_precomputed(name, save_dir, lowpass, highpass, subjects_dir, subject, subtomri,
                            method, overwrite, n_jobs, morph_to, vertices_to):

    stcs = io.read_source_estimates(name, save_dir,lowpass, highpass, method)
    subject_from = subtomri
    subject_to = morph_to

    for trial_type in stcs:
        stc_morph_name = name + filter_string(lowpass, highpass) + '_' + \
        trial_type +  '_' + method + '_morph'
        stc_morph_path = join(save_dir, stc_morph_name)

        stc_from = stcs[trial_type]

        morph_mat = mne.compute_morph_matrix(subject_from=subject_from, subject_to=subject_to,
                                            vertices_from=stc_from.vertices, vertices_to=vertices_to,
                                            subjects_dir=subjects_dir, warn=True)


        if overwrite or not isfile(stc_morph_path + '-lh.stc'):
            stcs_morph = mne.morph_data_precomputed(subject_from, subject_to,
                                                    stc_from, vertices_to, morph_mat)
            stcs_morph.save(stc_morph_path)

        else:
            print('morphed source estimates for: '+  stc_morph_path + \
                  ' already exists')

@decor.topline
def average_morphed_data(morphed_data_all, method, save_dir_averages, lowpass, highpass,
                         which_file):

    averaged_morphed_data = dict()

    n_subjects = len(morphed_data_all['pinprick'])
    for trial_type in morphed_data_all:
        if morphed_data_all[trial_type]!=[]:
            trial_morphed_data = morphed_data_all[trial_type]
            trial_average = trial_morphed_data[0].copy()#get copy of first instance

        for trial_index in range(1, n_subjects):
            trial_average._data += trial_morphed_data[trial_index].data

        trial_average._data /= n_subjects
        averaged_morphed_data[trial_type] = trial_average

    for trial_type in averaged_morphed_data:
        stc_path = save_dir_averages  + \
            trial_type + filter_string(lowpass, highpass) + '_morphed_data_' + method + \
            '_' + which_file
        averaged_morphed_data[trial_type].save(stc_path)


#==============================================================================
# STATISTICS
#==============================================================================
@decor.topline
def statistics_source_space(morphed_data_all, save_dir_averages,
                            independent_variable_1,
                            independent_variable_2,
                            time_window, n_permutations,lowpass, highpass, overwrite):

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

        ## get data in the right format
        statistics_data_1 = np.zeros((n_subjects, n_sources, n_samples))
        statistics_data_2 = np.zeros((n_subjects, n_sources, n_samples))

        for subject_index in range(n_subjects):
            statistics_data_1[subject_index, :, :] = input_data['iv_1'][subject_index].data
            statistics_data_2[subject_index, :, :] = input_data['iv_2'][subject_index].data
            print('processing data from subject: ' + str(subject_index))

        ## crop data on the time dimension
        times = info_data[0].times
        time_indices = np.logical_and(times >= time_window[0],
                                      times <= time_window[1])

        statistics_data_1 = statistics_data_1[:, :, time_indices]
        statistics_data_2 = statistics_data_2[:, :, time_indices]

        ## set up cluster analysis
        p_threshold = 0.05
        t_threshold = stats.distributions.t.ppf(1 - p_threshold / 2, n_subjects - 1)
        seed = 7 ## my lucky number

        statistics_list = [statistics_data_1, statistics_data_2]

        T_obs, clusters, cluster_p_values, H0 =  \
            mne.stats.permutation_cluster_test(statistics_list,
                                                     n_permutations=n_permutations,
                                                     threshold=t_threshold,
                                                     seed=seed,
                                                     n_jobs=-1)

        cluster_dict = dict(T_obs=T_obs, clusters=clusters,
                            cluster_p_values=cluster_p_values, H0=H0)

        with open(cluster_path, 'wb') as filename:
            pickle.dump(cluster_dict, filename)

        print('finished saving cluster at path: ' + cluster_path)

    else:
        print('cluster permutation: '+ cluster_path + \
              ' already exists')



"""
How to really make a correlation analysis:
Separate your trials in odd and even. Then calculate the correlation between odd and even
for ascending number of trials"""
@decor.topline
def corr_ntr(name, save_dir, lowpass, highpass, bad_channels, event_id,
             tmin, tmax, baseline, figures_path, save_plots, autoreject,
             overwrite_ar, reject, flat):

    # correlation analysis
    events = io.read_events(name, save_dir)
    raw = io.read_filtered(name, save_dir, lowpass, highpass)

    picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False,
                           eog=False, ecg=False, exclude=bad_channels)

    n_events = np.size(events,0)
    print(n_events)

    evokeds = []
    peaks = []
    times = []

    for x in range(1,n_events//10+1): # analyse in 10-steps of nave how the average gets better
        npick = 10*x
        idx = np.random.choice(n_events,size=npick,replace=False)
        picked_events = events[idx,:]

        picked_epochs = mne.Epochs(raw, picked_events, event_id, tmin, tmax,
                          baseline, picks)

        if autoreject:
            reject_value_path = join(save_dir, filter_string(lowpass, highpass) \
                                     + '_reject_value.py')
            print('Rejection with Autoreject')
            if overwrite_ar or not isfile(reject_value_path):

                reject = ar.get_rejection_threshold(picked_epochs)

                with open(reject_value_path, 'w') as rv:
                    for key,value in reject.items():
                        rv.write(f'{key}:{value}\n')

            else:
                with open(reject_value_path, 'r') as rv:
                    reject = {}
                    for item in rv:
                        if ':' in item:
                            key,value = item.split(':', 1)
                            value = value[:-1]
                            reject[key] = float(value)

                print('Reading Rejection-Threshold from file')

        print('Rejection Threshold: %s' % reject)

        picked_epochs.drop_bad(reject=reject, flat=flat)

        picked_avg = picked_epochs.average()
        evokeds.append(picked_avg)

        peak = picked_avg.get_peak(return_amplitude=True)
        times.append(peak[1])
        peaks.append(peak[2])
    """
    n_plots = len(peaks)//10 + 1 # compare_evokeds has only 10 standard colors otherwise you had to assign them for yourself
    for x in range(1, n_plots + 1):
        mne.viz.plot_compare_evokeds(evokeds[x*10-10:x*10],gfp=True)
    """
    fig, ax1 = plt.subplots()
    ax1.plot(peaks)
    fig.show()

    if save_plots:
        save_path =join(figures_path, 'statistics', name + \
                        filter_string(lowpass, highpass) + '_corr_ntr.jpg')
        fig.savefig(save_path)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')
