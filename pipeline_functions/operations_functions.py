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
from scipy import stats
from os import makedirs, listdir, environ
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
from itertools import combinations
from functools import reduce
import random
import gc
import statistics as st
from mayavi import mlab

# Naming Conventions
def filter_string(lowpass, highpass):

    if highpass!=None and highpass!=0:
        filter_string = '_' + str(highpass) + '-' + str(lowpass) + '_Hz'
    else:
        filter_string = '_' + str(lowpass) + '_Hz'

    return filter_string

#==============================================================================
# OPERATING SYSTEM COMMANDS
#==============================================================================
def populate_directories(data_path, figures_path, event_id):

    ## create grand averages path with a statistics folder
    ga_folders = ['statistics', 'evoked', 'stc', 'tfr', 'connect']
    for subfolder in ga_folders:
        grand_average_path = join(data_path, 'grand_averages', subfolder)
        if not exists(grand_average_path):
            makedirs(grand_average_path)
            print(grand_average_path + ' has been created')

    ## create erm(empty_room_measurements)paths
    erm_path = join(data_path, 'empty_room_data')
    if not exists(erm_path):
        makedirs(erm_path)
        print(erm_path + ' has been created')

    ## create figures path
    folders = ['epochs', 'epochs_image', 'epochs_topo', 'evoked_image',
               'power_spectra_raw', 'power_spectra_epochs',
               'power_spectra_topo', 'evoked_butterfly', 'evoked_field',
               'evoked_topo', 'evoked_topomap', 'evoked_joint', 'evoked_white',
               'ica', 'ssp', 'stcs', 'vec_stcs', 'transformation', 'source_space',
               'noise_covariance', 'events', 'label_time_course', 'ECD',
               'stcs_movie', 'bem', 'snr', 'statistics', 'correlation_ntr',
               'labels', 'tf_sensor_space/plot', 'tf_source_space/label_power',
               'tf_sensor_space/topo', 'tf_sensor_space/joint',
               'tf_sensor_space/oscs','tf_sensor_space/itc',
               'tf_sensor_space/dynamics', 'tf_source_space/connectivity',
               'epochs_drop_log']

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
                       'evoked_joint', 'evoked_white', 'label_time_course', 'ECD',
                       'stcs', 'vec_stcs','stcs_movie', 'snr',
                       'tf_sensor_space/plot', 'tf_sensor_space/topo',
                       'tf_sensor_space/joint', 'tf_sensor_space/oscs',
                       'tf_sensor_space/itc']

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
                
    ## create grand average figures path
    grand_averages_figures_path = join(figures_path, 'grand_averages')
    figure_subfolders = ['sensor_space/evoked', 'sensor_space/tfr',
                         'source_space/statistics', 'source_space/stc',
                         'source_space/connectivity', 'source_space/stc_movie']
    
    for figure_subfolder in figure_subfolders:
        folder_path = join(grand_averages_figures_path, figure_subfolder)
        if not exists(folder_path):
            makedirs(folder_path)
            print(folder_path + ' has been created')
#==============================================================================
# PREPROCESSING AND GETTING TO EVOKED AND TFR
#==============================================================================
@decor.topline
def filter_raw(name, save_dir, lowpass, highpass, overwrite, ermsub,
               data_path, n_jobs, enable_cuda, bad_channels):

    filter_name = name  + filter_string(lowpass, highpass) + '-raw.fif'
    filter_path = join(save_dir, filter_name)

    if not isfile(filter_path):
        
        raw = io.read_raw(name, save_dir)
        if enable_cuda: #use cuda for filtering
            n_jobs = 'cuda'
        raw.filter(highpass, lowpass, n_jobs=n_jobs)

        filter_name = name  + filter_string(lowpass, highpass) + '-raw.fif'
        filter_path = join(save_dir, filter_name)
        
        raw.save(filter_path, overwrite=True)

    else:
        print('raw file: ' + filter_path + ' already exists')
        print('NO OVERWRITE FOR FILTERING, please change settings or delete files for new methods')

    if ermsub!='None':
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
            erm_raw.pick_types(meg=True,exclude=bad_channels)
            erm_raw.filter(highpass, lowpass)

            erm_raw.save(erm_filter_path, overwrite=True)
            print('ERM-Data filtered and saved')

        else:
            print('erm_raw file: ' + erm_filter_path + ' already exists')

    else:
        print('no erm_file assigned')

@decor.topline
def find_events(name, save_dir, adjust_timeline_by_msec, lowpass, highpass, overwrite,
                save_plots, figures_path, exec_ops):

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

        # sort only along samples(column 0)
        events = events[events[:,0].argsort()]

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

        # sort only along samples(column 0)
        events = events[events[:,0].argsort()]
        
        # delete Trigger 1 if not after Trigger 2 (due to mistake with light-barrier)
        remove = np.array([], dtype=int)
        for n in range(len(events)):
            if events[n,2] == 1:
                if events[n-1,2] != 2:
                    remove = np.append(remove, n)
                    print(f'{events[n,0]} removed Trigger 1')
        events = np.delete(events, remove, axis=0)
        
        # Rating
        pre_ratings = events[np.nonzero(np.logical_and(9<events[:,2],events[:,2]<20))]
        if len(pre_ratings)!=0:    
            first_idx = np.nonzero(np.diff(pre_ratings[:,0], axis=0)<200)[0]
            last_idx = first_idx + 1
            ratings = pre_ratings[first_idx]
            ratings[:,2] = (ratings[:,2]-10)*10 + pre_ratings[last_idx][:,2]-10

            diff_ratings = np.copy(ratings)
            diff_ratings[np.nonzero(np.diff(ratings[:,2])<0)[0] + 1 ,2] = 5
            diff_ratings[np.nonzero(np.diff(ratings[:,2])==0)[0] + 1 ,2] = 6
            diff_ratings[np.nonzero(np.diff(ratings[:,2])>0)[0] + 1 ,2] = 7
            diff_ratings = np.delete(diff_ratings, [0], axis=0)

            pre_events = events[np.nonzero(events[:,2]==1)][:,0]
            for n in range(len(diff_ratings)):
                diff_ratings[n,0] = pre_events[np.nonzero(pre_events-diff_ratings[n,0] < 0)][-1] + 3
            
            # Eliminate Duplicates
            diff_remove = np.array([], dtype=int)
            for n in range(1,len(diff_ratings)):
                if diff_ratings[n,0] == diff_ratings[n-1,0]:
                    diff_remove = np.append(diff_remove, n)
                    print(f'{diff_ratings[n,0]} removed as Duplicate')
            diff_ratings = np.delete(diff_ratings, diff_remove, axis=0)
              
            events = np.append(events, diff_ratings, axis=0)
            events = events[events[:,0].argsort()]
            
            if save_plots:
                fig, ax1 = plt.subplots(figsize=(20,10))
                ax1.plot(ratings[:,2], 'b')
                ax1.set_ylim(0,100)
                
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
        events[:, 0] = [ts + np.round(adjust_timeline_by_msec * 10**-3 * \
                        raw.info['sfreq']) for ts in events[:, 0]]
        
        # General Latency-Correction based on Latency-Tests
        if 't' in name: # applies to tactile and motor_erm
            events[:, 0] = [ts + np.round(-98 * 10**-3 * \
                        raw.info['sfreq']) for ts in events[:, 0]]
        else:
            events[:, 0] = [ts + np.round(-90 * 10**-3 * \
                        raw.info['sfreq']) for ts in events[:, 0]]
        

        l1 = []
        l2 = []
        for x in range(np.size(events, axis=0)):
            if events[x,2]==2:
                if events[x+1,2]==1:
                    l1.append(events[x+1,0] - events[x,0])
        diff1_mean = st.mean(l1)
        diff1_stdev = st.stdev(l1)
        ut.dict_filehandler(name, 'MotStart-LBT_diffs.py',
                            sub_script_path, values={'mean':diff1_mean,
                                                     'stdev':diff1_stdev})
        
        if exec_ops['motor_erm_analysis']:
            for x in range(np.size(events, axis=0)-3):
                if events[x,2]==2:
                    if events[x+2,2]==4:
                        l2.append(events[x+2,0] - events[x,0])
            diff2_mean = st.mean(l2)
            diff2_stdev = st.stdev(l2)
            ut.dict_filehandler(name, 'MotStart1-MotStart2_diffs.py',
                                sub_script_path, values={'mean':diff2_mean,
                                                         'stdev':diff2_stdev})
        else:
            for x in range(np.size(events, axis=0)-3):
                if events[x,2]==2:
                    if events[x+3,2]==4:
                        l2.append(events[x+3,0] - events[x,0])
            diff2_mean = st.mean(l2)
            diff2_stdev = st.stdev(l2)
            ut.dict_filehandler(name, 'MotStart1-MotStart2_diffs.py',
                                sub_script_path, values={'mean':diff2_mean,
                                                         'stdev':diff2_stdev})       
        # Latency-Correction for Offset-Trigger[4]
        for x in range(np.size(events, axis=0)-3):
            if events[x,2]==2:
                if events[x+1,2]==1:
                    if events[x+3,2]==4:
                        corr = diff1_mean - (events[x+1,0] - events[x,0])
                        events[x+3,0] = events[x+3,0] + corr
                    
        # unique event_ids    
        ids = np.unique(events[:,2])
        print('unique ID\'s assigned: ',ids)


        if np.size(events)>0:
            mne.event.write_events(events_path, events)
        else:
            print('No events found')


    else:
        print('event file: '+ events_path + ' already exists')

@decor.topline
def find_eog_events(name, save_dir, eog_channel):

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
              baseline, reject, flat, autoreject, overwrite_ar,
              sub_script_path, bad_channels, decim,
              reject_eog_epochs, overwrite, exec_ops):

    epochs_name = name + filter_string(lowpass, highpass) + '-epo.fif'
    epochs_path = join(save_dir, epochs_name)
    if overwrite or not isfile(epochs_path):

        raw = io.read_filtered(name, save_dir, lowpass, highpass)
        
        if exec_ops['erm_analysis']:
            n_times = raw.n_times
            sfreq = raw.info['sfreq']
            step = (n_times-10*sfreq)/200 # Numer of events in motor_erm
            events = np.ndarray((200,3), dtype='int32')
            times = np.arange(5*sfreq, n_times-5*sfreq, step)[:200]
            events[:,0] = times
            events[:,1] = 0
            events[:,2] = 1
        else:
            events = io.read_events(name, save_dir)
        
        # Choose only included event_ids
        actual_event_id = {}
        for i in event_id:
            if event_id[i] in np.unique(events[:,2]):
                actual_event_id.update({i:event_id[i]})
        
        print('Event_ids included:')
        for i in actual_event_id:
            print(i)

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


        epochs = mne.Epochs(raw, events, actual_event_id, tmin, tmax, baseline,
                            preload=True, picks=picks, proj=False,
                            decim=decim, on_missing='ignore',reject_by_annotation=True)


        if autoreject:
            reject = ut.autoreject_handler(name, epochs, sub_script_path,
                                           overwrite_ar)

        print(f'Rejection Threshold: {reject}')

        epochs.drop_bad(reject=reject, flat=flat)
        epochs.save(epochs_path, overwrite=True)

        reject_channels = []
        log = epochs.drop_log

        for a in log:
            if a != []:
                for b in a:
                    reject_channels.append(b)
        c = Counter(reject_channels).most_common()
        
        c.insert(0, (len(epochs), epochs.drop_log_stats()))
        
        ut.dict_filehandler(name, 'reject_channels',
                            sub_script_path, values=c)
        
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
            reject, flat, bad_channels, overwrite, autoreject,
            save_plots, figures_path, sub_script_path, erm_analysis):
    
    ica_comp_file_path = join(sub_script_path, 'ica_components.py')
    info = io.read_info(name, save_dir)
    
    ica_dict = ut.dict_filehandler(name, 'ica_components', sub_script_path,
                                   onlyread=True)
    
    ica_name = name + filter_string(lowpass, highpass) + '-ica.fif'
    ica_path = join(save_dir, ica_name)

    if overwrite or not isfile(ica_path):

        raw = io.read_filtered(name, save_dir, lowpass, highpass)
        epochs = io.read_epochs(name, save_dir, lowpass, highpass)
        picks = mne.pick_types(raw.info, meg=True, eeg=False, eog=False,
                       stim=False, exclude=bad_channels)
        

        ica = mne.preprocessing.ICA(n_components=25, method='fastica', random_state = 8)

        if autoreject:
            reject = ut.autoreject_handler(name, epochs, sub_script_path, overwrite_ar=False,
                                  only_read=True)

        print('Rejection Threshold: %s' % reject)

        ica.fit(raw, picks, reject=dict(grad=4000e-13), flat=flat,
                reject_by_annotation=True)
        
        if name in ica_dict and ica_dict[name]!=[]:
            indices = ica_dict[name]
            ica.exclude += indices
            print(f'{indices} added to ica.exclude from ica_components.py')
            ica.save(ica_path)
            
            comp_list = []
            for c in range(ica.n_components):
                comp_list.append(c)
            fig1 = ica.plot_components(picks=comp_list, title=name)
            if ica.exclude != []:
                fig2 = ica.plot_properties(raw, ica.exclude,psd_args={'fmax':lowpass})                
            fig3 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name)
            fig4 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name)   
            fig5 = ica.plot_overlay(epochs.average(), title=name)
            if save_plots:
            
                save_path = join(figures_path, 'ica', name + \
                                 '_ica_comp' + filter_string(lowpass, highpass) + '.jpg')
                fig1.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
                if ica.exclude != []:
                    for f in fig2:
                        save_path = join(figures_path, 'ica', name + \
                                         '_ica_prop' + filter_string(lowpass, highpass) + f'_{fig2.index(f)}.jpg')
                        f.savefig(save_path, dpi=600)
                        print('figure: ' + save_path + ' has been saved')
            
                save_path = join(figures_path, 'ica', name + \
                    '_ica_src' + filter_string(lowpass, highpass) + '_0.jpg')
                fig3.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
                
                save_path = join(figures_path, 'ica', name + \
                    '_ica_src' + filter_string(lowpass, highpass) + '_1.jpg')
                fig4.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved') 

                save_path = join(figures_path, 'ica', name + \
                    '_ica_ovl' + filter_string(lowpass, highpass) + '.jpg')
                fig5.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
            
            else:
                print('Not saving plots; set "save_plots" to "True" to save')
                    
        elif ('EEG 001') in info['ch_names'] and not erm_analysis:            
            eeg_picks = mne.pick_types(raw.info, meg=True, eeg=True, eog=True,
                           stim=False, exclude=bad_channels)
            
            eog_epochs = mne.preprocessing.create_eog_epochs(raw, picks=eeg_picks,
                                                             reject=reject, flat=flat, ch_name=eog_channel)
            ecg_epochs = mne.preprocessing.create_ecg_epochs(raw, picks=eeg_picks,
                                                             reject=reject, flat=flat, ch_name=ecg_channel)
            
            eog_indices = []
            ecg_indices = []
            
            if len(eog_epochs)!=0:
                eog_indices, eog_scores = ica.find_bads_eog(eog_epochs, ch_name=eog_channel)
                ica.exclude.extend(eog_indices)
                print('EOG-Components: ', eog_indices)
            if len(ecg_epochs)!=0:
                ecg_indices, ecg_scores = ica.find_bads_ecg(ecg_epochs, ch_name=ecg_channel)
                ica.exclude.extend(ecg_indices)
                print('ECG-Components: ', ecg_indices)
            
            ica.save(ica_path)
            
            # Reading and Writing ICA-Components to a .py-file
            exes = ica.exclude
            indices = []
            for i in exes:
                indices.append(int(i))
            
            ut.dict_filehandler(name, 'ica_components', sub_script_path,
                                values=indices, overwrite=False)
           
            # Plot ICA integrated
            comp_list = []
            for c in range(ica.n_components):
                comp_list.append(c)
            fig1 = ica.plot_components(picks=comp_list, title=name)
            if ica.exclude != []:
                fig2 = ica.plot_properties(raw, indices, psd_args={'fmax':lowpass})          
            fig5 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name)
            fig6 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name)
            if eog_indices != []:
                fig3 = ica.plot_scores(eog_scores, title=name+'_eog')
                fig7 = ica.plot_overlay(epochs.average(), exclude=eog_indices, title=name+'_eog')
            if ecg_indices != []:
                fig4 = ica.plot_scores(ecg_scores, title=name+'_ecg')                  
                fig8 = ica.plot_overlay(epochs.average(), exclude=ecg_indices, title=name+'_ecg')            
            
            if save_plots:

                save_path = join(figures_path, 'ica', name + \
                                 '_ica_comp' + filter_string(lowpass, highpass) + '.jpg')
                fig1.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
                if ica.exclude != []:
                    for f in fig2:
                        save_path = join(figures_path, 'ica', name + \
                                         '_ica_prop' + filter_string(lowpass, highpass) + f'_{fig2.index(f)}.jpg')
                        f.savefig(save_path, dpi=600)
                        print('figure: ' + save_path + ' has been saved')
                if eog_indices != []:
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_scor_eog' + filter_string(lowpass, highpass) + '.jpg')
                    fig3.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                if ecg_indices != []:
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_scor_ecg' + filter_string(lowpass, highpass) + '.jpg')
                    fig4.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name + \
                    '_ica_src' + filter_string(lowpass, highpass) + '_0.jpg')
                fig5.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')

                save_path = join(figures_path, 'ica', name + \
                    '_ica_src' + filter_string(lowpass, highpass) + '_1.jpg')
                fig6.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
                
                if eog_indices != []:
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_ovl_eog' + filter_string(lowpass, highpass) + '.jpg')
                    fig7.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                if ecg_indices != []:
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_ovl_ecg' + filter_string(lowpass, highpass) + '.jpg')
                    fig8.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')


            else:
                print('Not saving plots; set "save_plots" to "True" to save')
        
        # No EEG was acquired during the measurement,
        # components have to be selected manually in the ica_components.py
        else:
            print('No EEG-Channels to read EOG/EEG from')
            ica_dict = {}
            if not isfile(ica_comp_file_path):
                if not exists(sub_script_path):
                    makedirs(sub_script_path)
                    print(sub_script_path + ' created')
                with open(ica_comp_file_path, 'w') as ica_f:   
                    ica_f.write(f'{name}:[]\n')
                    print(ica_comp_file_path + ' created')           
            else:
                with open(ica_comp_file_path, 'r') as ica_f:
                    for item in ica_f:
                        if ':' in item:
                            key,value = item.split(':', 1)
                            value = eval(value)
                            ica_dict[key]=value
            
            if not name in ica_dict:
                ica_dict.update({name:[]})
                with open(ica_comp_file_path, 'w') as ica_f:
                    for name, indices in ica_dict.items():
                        ica_f.write(f'{name}:{indices}\n')
                        
            if len(ica_dict[name])>0:
                indices = ica_dict[name]
                ica.exclude += indices
                print(f'{indices} added to ica.exclude')
                ica.save(ica_path)
                
                comp_list = []
                for c in range(ica.n_components):
                    comp_list.append(c)
                fig1 = ica.plot_components(picks=comp_list, title=name)
                if ica.exclude != []:
                    fig2 = ica.plot_properties(raw, ica.exclude,psd_args={'fmax':lowpass})                
                fig3 = ica.plot_sources(raw, picks=comp_list[:12], start=150, stop=200, title=name)
                fig4 = ica.plot_sources(raw, picks=comp_list[12:], start=150, stop=200, title=name)   
                fig5 = ica.plot_overlay(epochs.average(), title=name)
                if save_plots:
                
                    save_path = join(figures_path, 'ica', name + \
                                     '_ica_comp' + filter_string(lowpass, highpass) + '.jpg')
                    fig1.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                    if ica.exclude != []:
                        for f in fig2:
                            save_path = join(figures_path, 'ica', name + \
                                             '_ica_prop' + filter_string(lowpass, highpass) + f'_{fig2.index(f)}.jpg')
                            f.savefig(save_path, dpi=600)
                            print('figure: ' + save_path + ' has been saved')
                
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_src' + filter_string(lowpass, highpass) + '_0.jpg')
                    fig3.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                    
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_src' + filter_string(lowpass, highpass) + '_1.jpg')
                    fig4.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved') 
    
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_ovl' + filter_string(lowpass, highpass) + '.jpg')
                    fig5.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')
            else:
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
                    fig1.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                    
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_src' + filter_string(lowpass, highpass) + '_0.jpg')
                    fig2.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                    
                    save_path = join(figures_path, 'ica', name + \
                        '_ica_src' + filter_string(lowpass, highpass) + '_1.jpg')
                    fig3.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')                    
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')               
    
        plt.close('all')
    
    else:
        print('ica file: '+ ica_path + ' already exists')

@decor.topline
def apply_ica(name, save_dir, lowpass, highpass, data_path,
              overwrite):

    ica_epochs_name = name + filter_string(lowpass, highpass) + '-ica-epo.fif'
    ica_epochs_path = join(save_dir, ica_epochs_name)

    if overwrite or not isfile(ica_epochs_path):

        epochs = io.read_epochs(name, save_dir, lowpass, highpass)
        ica = io.read_ica(name, save_dir, lowpass, highpass)
        
        if len(ica.exclude)==0:
            print('No components excluded here')
        
        ica_epochs = ica.apply(epochs)
        ica_epochs.save(ica_epochs_path)
        
    else:
        print('ica epochs file: '+ ica_epochs_path + ' already exists')

@decor.topline
def get_evokeds(name, save_dir, lowpass, highpass, exec_ops, ermsub,
                detrend, ica_evokeds, overwrite):

    evokeds_name = name + filter_string(lowpass, highpass) + '-ave.fif'
    evokeds_path = join(save_dir, evokeds_name)
    info = io.read_info(name, save_dir)

    if overwrite or not isfile(evokeds_path):
        if ica_evokeds:
            epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
            print('Evokeds from ICA-Epochs')
        elif exec_ops['apply_ssp_er'] and ermsub!='None':
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
                evoked.detrend(order=1)
            evokeds.append(evoked)

        mne.evoked.write_evokeds(evokeds_path, evokeds)

    else:
        print('evokeds file: '+ evokeds_path + ' already exists')

@decor.topline
def grand_avg_evokeds(data_path, grand_avg_dict, save_dir_averages,
                      lowpass, highpass, exec_ops):
    
    for key in grand_avg_dict:
        trial_dict = {}
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
                if evoked.nave!=0:
                    if evoked.comment in trial_dict:
                        trial_dict[evoked.comment].append(evoked)
                    else:
                        trial_dict.update({evoked.comment:[evoked]})
                else:
                    print(f'{evoked.comment} for {name} got nave=0')
            

        for trial in trial_dict:
            if len(trial_dict[trial])!=0:
                ga = mne.grand_average(trial_dict[trial],
                                       interpolate_bads=True,
                                       drop_bads=True)
                ga.comment = trial
                ga_path = join(save_dir_averages, 'evoked',
                                          key + '_'  + trial + \
                                          filter_string(lowpass, highpass) + \
                                          '-grand_avg-ave.fif')
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
                fmin, fmax = tfr_freqs[[0,-1]]
                power, itc = mne.time_frequency.tfr_stockwell(epochs[trial_type],
                                                              fmin=fmin, fmax=fmax,
                                                              width=stockwell_width,
                                                              n_jobs=n_jobs)
            else:
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
            for power in powers:
                if power.nave!=0:
                    if power.comment in trial_dict:
                        trial_dict[power.comment].append(power)
                    else:
                        trial_dict.update({power.comment:[power]})
                else:
                    print(f'{power.comment} for {name} got nave=0')
            

        for trial in trial_dict:
            if len(trial_dict[trial])!=0:
                
                # Make sure, all have the same number of channels
                commons = set()
                for power in trial_dict[trial]:
                    if len(commons)==0:
                        for c in power.ch_names:
                            commons.add(c)
                    commons = commons & set(power.ch_names)
                print(f'{trial}:Reducing all n_channels to {len(commons)}')
                for idx, power in enumerate(trial_dict[trial]):
                    trial_dict[trial][idx] = power.pick_channels(list(commons))
                
                ga = mne.grand_average(trial_dict[trial],
                                       interpolate_bads=True,
                                       drop_bads=True)
                ga.comment = trial
                ga_path = join(save_dir_averages, 'tfr',
                                          key + '_'  + trial + \
                                          filter_string(lowpass, highpass) + \
                                          '-grand_avg-tfr.h5')
                
                ga.save(ga_path)

#==============================================================================
# BASH OPERATIONS
#==============================================================================
## These functions do not work on Windows

## local function used in the bash commands below
def run_process_and_write_output(command, subjects_dir):
    environment = environ.copy()
    environment["SUBJECTS_DIR"] = subjects_dir
    
    if sys.platform == 'win32':
        raise RuntimeError('mri_subject_functions are currently not working on Windows, please run them on Linux')
        #command.insert(0, 'wsl')
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               env=environment)
    
    ## write bash output in python console
    for c in iter(lambda: process.stdout.read(1), b''):
        sys.stdout.write(c.decode('utf-8'))

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
    
    #mne.bem.make_watershed_bem(mri_subject, subjects_dir)
    
    print('Running Watershed algorithm for: ' + mri_subject + \
          ". Output is written to the bem folder " + \
          "of the subject's FreeSurfer folder.\n" + \
          'Bash output follows below.\n\n')

    if overwrite:
        overwrite_string = '--overwrite'
    else:
        overwrite_string = ''
    ## watershed command
    command = ['mne', 'watershed_bem',
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

#==============================================================================
# MNE SOURCE RECONSTRUCTIONS
#==============================================================================
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
def prepare_bem(mri_subject, subjects_dir, overwrite):
    
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
def morph_labels(mri_subject, subjects_dir, overwrite):
    
    parcellations = ['aparc_sub','HCPMMP1_combined','HCPMMP1']
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
            
            mne.write_labels_to_annot(m_labels, mri_subject, pc, subjects_dir=subjects_dir,
                                      overwrite=True)
    
    else:
        print(f'{parcellations} already exist')
@decor.topline
def mri_coreg(name, save_dir, subtomri, subjects_dir, eog_digitized):

    raw_name = name + '-raw.fif'
    raw_path = join(save_dir, raw_name)
    #trans-file pre-reading makes an error window
    
    if eog_digitized:
        raw = io.read_raw(name, save_dir)
        digi = raw.info['dig']
        if len(digi)==111:
            if digi[-1]['kind']!=3:
                for i in digi[-4:]:
                    i['kind'] = 3
                raw.info['dig'] = digi
                raw.save(raw_path, overwrite=True)
                print('Set EOG-Digitization-Points to kind 3 and saved')
            else:
                print('EOG-Digitization-Points already set to kind 3')
                
    mne.gui.coregistration(subject=subtomri, inst=raw_path,
                           subjects_dir=subjects_dir, guess_mri_subject=False,
                           advanced_rendering=True)

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
                              overwrite, ermsub, data_path,
                              bad_channels, n_jobs, erm_noise_covariance,
                              use_calm_cov, ica_evokeds, erm_ica):

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

    elif ermsub=='None' or 'leer' in name or erm_noise_covariance==False:

        print('Noise Covariance on Epochs')
        covariance_name = name + filter_string(lowpass, highpass) + '-cov.fif'
        covariance_path = join(save_dir, covariance_name)

        if overwrite or not isfile(covariance_path):

            if ica_evokeds:
                epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
            else:
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
            if erm_ica:
                print('Applying ICA to ERM-Raw')
                ica = io.read_ica(name, save_dir, lowpass, highpass)
                erm = ica.apply(erm)
            
            noise_covariance = mne.compute_raw_covariance(erm, n_jobs=n_jobs)
            mne.cov.write_cov(covariance_path, noise_covariance)

        else:
            print('noise covariance file: '+ covariance_path + \
                  ' already exists')

@decor.topline
def create_inverse_operator(name, save_dir, lowpass, highpass,
                            overwrite, ermsub, use_calm_cov, erm_noise_covariance):

    inverse_operator_name = name + filter_string(lowpass, highpass) +  '-inv.fif'
    inverse_operator_path = join(save_dir, inverse_operator_name)

    if overwrite or not isfile(inverse_operator_path):

        info = io.read_info(name, save_dir)
        if use_calm_cov==True:
            noise_covariance = io.read_clm_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from 1-min Calm in raw')
        elif ermsub=='None' or erm_noise_covariance==False:
            noise_covariance = io.read_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from Epochs')
        else:
            noise_covariance = io.read_erm_noise_covariance(name, save_dir, lowpass, highpass)
            print('Noise Covariance from Empty-Room-Data')

        forward = io.read_forward(name, save_dir)
        
        inverse_operator = mne.minimum_norm.make_inverse_operator(
                            info, forward, noise_covariance)

        mne.minimum_norm.write_inverse_operator(inverse_operator_path,
                                                    inverse_operator)

    else:
        print('inverse operator file: '+ inverse_operator_path + \
              ' already exists')

@decor.topline
def source_estimate(name, save_dir, lowpass, highpass, method,
                    event_id, overwrite):

    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    stcs = dict()
    normal_stcs = dict()

    snr = 3.0
    lambda2 = 1.0 / snr ** 2
    
    for evoked in evokeds:
        trial_type = evoked.comment
        stc_name = name + filter_string(lowpass, highpass) + '_' + trial_type + '_' + method
        stc_path = join(save_dir, stc_name)
        if overwrite or not isfile(stc_path):

            stcs[trial_type] = mne.minimum_norm.apply_inverse(
                                        evoked, inverse_operator, lambda2,
                                        method=method)
            
            normal_stcs[trial_type] = mne.minimum_norm.apply_inverse(
                                        evoked, inverse_operator, lambda2,
                                        method=method, pick_ori='normal')
        else:
            print('source estimates for: '+  stc_path + \
                  ' already exists')

    for stc in stcs:
        stc_name = name + filter_string(lowpass, highpass) + '_' + stc + '_' + method
        stc_path = join(save_dir, stc_name)
        if overwrite or not isfile(stc_path + '-lh.stc'):
            stcs[stc].save(stc_path)

    for n_stc in normal_stcs:
        n_stc_name = name + filter_string(lowpass, highpass) + '_' + n_stc + '_' + method + '-normal'
        n_stc_path = join(save_dir, n_stc_name)
        if overwrite or not isfile(n_stc_path + '-lh.stc'):
            normal_stcs[n_stc].save(n_stc_path)

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
def ECD_fit(name, save_dir, lowpass, highpass, ermsub, subjects_dir,
            subtomri, source_space_method, use_calm_cov, ECDs, n_jobs,
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
def create_func_label(name, save_dir, lowpass, highpass, method, event_id,
                      subtomri, subjects_dir, source_space_method, label_origin,
                      parcellation, ev_ids_label_analysis,
                      save_plots, figures_path):
    
    stcs = io.read_source_estimates(name, save_dir, lowpass,
                                    highpass, method, event_id)
    n_stcs = io.read_normal_source_estimates(name, save_dir,
                                             lowpass, highpass,
                                             method, event_id)
    
    src = io.read_source_space(subtomri, subjects_dir, source_space_method)
    labels = mne.read_labels_from_annot(subtomri, subjects_dir=subjects_dir,
                                        parc=parcellation)
    for trial in ev_ids_label_analysis:
        stc = stcs[trial]
        n_stc = n_stcs[trial]
        for label in [l for l in labels if l.name in label_origin]:
            print(label.name)
            stc_label = stc.in_label(label)
            vtx, hemi, t = stc_label.center_of_mass(subtomri, subjects_dir=subjects_dir)
            mni_coords = mne.vertex_to_mni(vtx, hemi, subtomri, subjects_dir=subjects_dir)
            
            tc = n_stc.extract_label_time_course(label, src, mode='pca_flip')
            max_t = stc.times[np.argmax(tc)]
            tmin = (max_t - 0.05)
            tmax = (max_t + 0.05)
            if tmin < stc.tmin:
                diff = stc.tmin - tmin
                tmin += diff
                tmax += diff
            if tmax > stc.times[-1]:
                diff = tmax - stc.times[-1]
                tmin -= diff
                tmax -= diff
            print(f'{tmin} - {tmax}s')
            print('Check1')
            # Make an STC in the time interval of interest and take the mean
            stc_mean = n_stc.copy().crop(tmin, tmax).mean()
            
            # use the stc_mean to generate a functional label
            # region growing is halted at 60% of the peak value within the
            # anatomical label / ROI specified by aparc_label_name
            stc_mean_label = stc_mean.in_label(label)
            data = np.abs(stc_mean_label.data)
            stc_mean_label.data[data < 0.8 * np.max(data)] = 0.
            print('Check2')

            # 8.5% of original source space vertices were omitted during forward
            # calculation, suppress the warning here with verbose='error'
            func_labels = mne.stc_to_label(stc_mean_label, src=src, smooth=True,
                                          subjects_dir=subjects_dir, connected=False,
                                          verbose='DEBUG')
            
            for i in func_labels:
                if i!=None:
                    func_label = i
            
            label_path = join(subjects_dir, subtomri, 'label', label.name + '_func.label')
            mne.write_label(label_path, func_label)
            print('Check3')
            if hemi==0:
                hemi='lh'
            if hemi==1:
                hemi='rh'
            brain = stc_mean.plot(subject=subtomri, hemi=hemi, subjects_dir=subjects_dir,
                                  title=f'{label.name}_{tmin}-{tmax}')
            brain.add_foci(mni_coords)
            brain.add_label(label, borders=True)
            brain.add_label(func_label, color='yellow')
            
            # extract the anatomical time course for each label
            stc_anat_label = n_stc.in_label(label)
            pca_anat = n_stc.extract_label_time_course(label, src, mode='pca_flip')[0]
            
            stc_func_label = n_stc.in_label(func_label)
            pca_func = n_stc.extract_label_time_course(func_label, src, mode='pca_flip')[0]
            
            # flip the pca so that the max power between tmin and tmax is positive
            pca_anat *= np.sign(pca_anat[np.argmax(np.abs(pca_anat))])
            pca_func *= np.sign(pca_func[np.argmax(np.abs(pca_anat))])
            
            plt.figure()
            plt.plot(1e3 * stc_anat_label.times, pca_anat, 'k',
                     label=f'Anatomical {label.name}')
            plt.plot(1e3 * stc_func_label.times, pca_func, 'b',
                     label=f'Functional {label.name}')
            plt.legend()
            plt.show()
            
            if save_plots:
                save_path = join(figures_path, 'label_time_course',
                                 f'{name}_{label.name}{filter_string(lowpass, highpass)}-tc.jpg')
                plt.savefig(save_path, dpi=600)

                b_save_path = join(figures_path, 'labels',
                                   f'{name}_{label.name}{filter_string(lowpass, highpass)}-b.jpg')
                brain.save_image(b_save_path)
            
            else:
                print('Not saving plots; set "save_plots" to "True" to save')
    
    plot.close_all()
@decor.topline
def apply_morph(name, save_dir, lowpass, highpass, subjects_dir, subtomri,
                method, overwrite, n_jobs, morph_to, source_space_method,
                event_id):

    stcs = io.read_source_estimates(name, save_dir,lowpass, highpass, method,
                                    event_id)
    morph = io.read_morph(subtomri, morph_to, source_space_method, subjects_dir)

    for trial_type in stcs:
        stc_morphed_name = name + filter_string(lowpass, highpass) + '_' + \
        trial_type +  '_' + method + '_morphed'
        stc_morphed_path = join(save_dir, stc_morphed_name)

        if overwrite or not isfile(stc_morphed_path + '-lh.stc'):
            stc_morphed = morph.apply(stcs[trial_type])
            stc_morphed.save(stc_morphed_path)
            
        else:
            print('morphed source estimates for: '+  stc_morphed_path + \
                  ' already exists')

@decor.topline
def source_space_connectivity(name, save_dir, lowpass, highpass,
                              subtomri, subjects_dir, method, parcellation,
                              con_methods, con_fmin, con_fmax,
                              n_jobs, overwrite):

    info = io.read_info(name, save_dir)
    epochs = io.read_epochs(name, save_dir, lowpass, highpass)[0]
    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    
    # Compute inverse solution and for each epoch. By using "return_generator=True"
    # stcs will be a generator object instead of a list.
    snr = 1.0  # use lower SNR for single epochs
    lambda2 = 1.0 / snr ** 2
    method = "dSPM"  # use dSPM method (could also be MNE or sLORETA)
    stcs = mne.minimum_norm.apply_inverse_epochs(epochs, inverse_operator, lambda2, method,
                                pick_ori="normal", return_generator=True)
    
    # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
    labels = mne.read_labels_from_annot(subtomri, parc=parcellation,
                                        subjects_dir=subjects_dir)
    
    # Average the source estimates within each label using sign-flips to reduce
    # signal cancellations, also here we return a generator
    src = inverse_operator['src']
    label_ts = mne.extract_label_time_course(stcs, labels, src, mode='mean_flip',
                                             return_generator=True)
    
    sfreq = info['sfreq']  # the sampling frequency
    con, freqs, times, n_epochs, n_tapers = mne.connectivity.spectral_connectivity(
        label_ts, method=con_methods, mode='multitaper', sfreq=sfreq, fmin=con_fmin,
        fmax=con_fmax, faverage=True, mt_adaptive=True, n_jobs=n_jobs)
    

    
    # con is a 3D array, get the connectivity for the first (and only) freq. band
    # for each con_method
    con_res = dict()
    for con_method, c in zip(con_methods, con):
        con_res[con_method] = c[:, :, 0]    

        # save to .npy file
        file_name = name + filter_string(lowpass, highpass) + \
        '_' + str(con_fmin) + '-' + str(con_fmax) + '_' + con_method
        file_path = join(save_dir, file_name)
        if overwrite or not isfile(file_path):
            np.save(file_path, con_res[con_method])
        else:
            print('connectivity_measures for for: '+ file_path + \
                  ' already exists')
@decor.topline
def grand_avg_morphed(grand_avg_dict, data_path, method, save_dir_averages,
                      lowpass, highpass, event_id):
    # for less memory only import data from stcs and add it to one fsaverage-stc in the end!!!
    n_chunks = 8
    for key in grand_avg_dict:
        print(f'grand_average for {key}')
        #divide in chunks to save memory
        fusion_dict = {}
        for i in range(0, len(grand_avg_dict[key]), n_chunks):
            sub_trial_dict = {}
            ga_chunk = grand_avg_dict[key][i:i+n_chunks]
            print(ga_chunk)
            for name in ga_chunk:
                save_dir = join(data_path, name)
                print(f'Add {name} to grand_average')
                stcs = io.read_morphed_source_estimates(name, save_dir, lowpass,
                                                        highpass, method, event_id)
                for trial_type in stcs:
                    if trial_type in sub_trial_dict:
                        sub_trial_dict[trial_type].append(stcs[trial_type])
                    else:
                        sub_trial_dict.update({trial_type:[stcs[trial_type]]})       
    
            # Average chunks
            for trial in sub_trial_dict:
                if len(sub_trial_dict[trial])!=0:
                    print(f'grand_average for {trial}-chunk {i}-{i+n_chunks}')
                    sub_trial_average = sub_trial_dict[trial][0].copy()
                    n_subjects = len(sub_trial_dict[trial])
                    
                    for trial_index in range(1, n_subjects):
                        sub_trial_average._data += sub_trial_dict[trial][trial_index].data
                        
                    sub_trial_average._data /= n_subjects
                    sub_trial_average.comment = trial
                    if trial in fusion_dict:
                        fusion_dict[trial].append(sub_trial_average)
                    else:
                        fusion_dict.update({trial:[sub_trial_average]})
        
        for trial in fusion_dict:
            if len(fusion_dict[trial])!=0:
                print(f'grand_average for {key}-{trial}')
                trial_average = fusion_dict[trial][0].copy()
                n_subjects = len(fusion_dict[trial])
                
                for trial_index in range(1, n_subjects):
                    trial_average._data += fusion_dict[trial][trial_index].data
                    
                trial_average._data /= n_subjects
                trial_average.comment = trial
                ga_path = join(save_dir_averages, 'stc',
                               key + '_'  + trial + \
                               filter_string(lowpass, highpass) + \
                               '-grand_avg')
                trial_average.save(ga_path)
        #clear memory
        gc.collect()
    
@decor.topline
def grand_avg_connect(grand_avg_dict, data_path, con_methods,
                      con_fmin, con_fmax, save_dir_averages,
                      lowpass, highpass):
    
    for key in grand_avg_dict:
        con_methods_dict = {}
        print(f'grand_average for {key}')
        for name in grand_avg_dict[key]:
            save_dir = join(data_path, name)
            print(f'Add {name} to grand_average')
            
            con_dict = io.read_connect(name, save_dir, lowpass,
                                       highpass, con_methods,
                                       con_fmin, con_fmax)
            
            for con_method in con_dict:
                if con_method in con_methods_dict:
                    con_methods_dict[con_method].append(con_dict[con_method])
                else:
                    con_methods_dict.update({con_method:[con_dict[con_method]]})
        
        for method in con_methods_dict:
            if len(con_methods_dict[method])!=0:
                print(f'grand_average for {key}-{method}')
                con_list = con_methods_dict[method]
                n_subjects = len(con_list)
                average = con_list[0]
                for idx in range(1, n_subjects):
                    average += con_list[idx]
                
                average /= n_subjects
                
                ga_path = join(save_dir_averages, 'connect',
                               key + '_'  + method + \
                               filter_string(lowpass, highpass) + \
                               '-grand_avg_connect')
                np.save(ga_path, average)
                
#==============================================================================
# STATISTICS
#==============================================================================
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

@decor.topline
def corr_ntr(name, save_dir, lowpass, highpass, exec_ops, ermsub,
             subtomri, ica_evokeds, save_plots, figures_path):

    info = io.read_info(name, save_dir)

    if ica_evokeds:
        epochs = io.read_ica_epochs(name, save_dir, lowpass, highpass)
        print('Evokeds from ICA-Epochs after applied SSP')
    elif exec_ops['apply_ssp_er'] and ermsub!='None':
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
        ep_tr.crop(0,0.3)
        ep_len = len(ep_tr)//2*2 # Make sure ep_len is even
        idxs = range(ep_len)
        
        y = []
        x = []
        
        #select randomly k epochs for t times

        for k in range(1, int(ep_len/2)): # Compare k epochs
            
            print(f'Iteration {k} of {int(ep_len/2)}')
            ep_rand = ep_tr[random.sample(idxs,k*2)]
            ep1 = ep_rand[:k]
            ep2 = ep_rand[k:]
            avg1 = ep1.average()
            avg2 = ep2.average()
            x.append(k) 
                        
            stc1 = mne.minimum_norm.apply_inverse(avg1, inv_op, method='dSPM', pick_ori='normal')
            stc2 = mne.minimum_norm.apply_inverse(avg2, inv_op, method='dSPM', pick_ori='normal')
            
            print(f'Label:{l.name}')
            mean1 = stc1.extract_label_time_course(l, src, mode='pca_flip')
            mean2 = stc2.extract_label_time_course(l, src, mode='pca_flip')
            
            coef = abs(np.corrcoef(mean1, mean2)[0,1])
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
