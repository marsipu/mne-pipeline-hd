
# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data - IO functions
@author: Lau Møller Andersen
@email: lau.moller.andersen@ki.se | lau.andersen@cnru.dk
@github: https://github.com/ualsbombe/omission_frontiers.git

Edited by Martin Schulz
martin@stud.uni-heidelberg.de
"""
from __future__ import print_function

import mne
from os.path import join
import pickle
import numpy as np

def filter_string(lowpass, highpass):
    
    if highpass!=None and highpass!=0:
        filter_string = '_' + str(highpass) + '-' + str(lowpass) + '_Hz'
    else:
        filter_string = '_' + str(lowpass) + '_Hz'

    return filter_string

#==============================================================================
# IO FUNCTIONS
#==============================================================================
def read_info(name, save_dir):

    raw_name = name + '-raw.fif'
    raw_path = join(save_dir, raw_name)
    info = mne.io.read_info(raw_path)

    return info

def read_raw(name, save_dir):
    
    try:
        raw_name = name + '-raw.fif'
        raw_path = join(save_dir, raw_name)
        raw = mne.io.read_raw_fif(raw_path, preload=True)
    except FileNotFoundError:
        raw_name = name + '.fif'
        raw_path = join(save_dir, raw_name)
        raw = mne.io.read_raw_fif(raw_path, preload=True)
        print('Imported Raw without -raw.fif')

    return raw

def read_maxfiltered(name, save_dir):
#obsolet if you only have one file per measurement
    split_string_number = 0
    read_all_files = False
    raws = []
    while not read_all_files:

        if split_string_number > 0:
            split_string_part = '-' + str(split_string_number)
        else:
            split_string_part = ''

        raw_name = name + split_string_part + '.fif'
        raw_path = join(save_dir, raw_name)
        try:
            raw_part = mne.io.Raw(raw_path, preload=True)
            raws.append(raw_part)
            split_string_number += 1
        except:
            read_all_files = True
            print(str(split_string_number) + ' raw files were read')

    raw = mne.concatenate_raws(raws)

    return raw

def read_filtered(name, save_dir, lowpass, highpass):

    raw_name = name + filter_string(lowpass, highpass) + '-raw.fif'
    raw_path = join(save_dir, raw_name)
    raw = mne.io.Raw(raw_path, preload=True)

    return raw

def read_events(name, save_dir):

    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)
    events = mne.read_events(events_path, mask=None)

    return events

def read_eog_events(name, save_dir):
    
    eog_events_name = name + '_eog-eve.fif'
    eog_events_path = join(save_dir, eog_events_name)
    eog_events = mne.read_events(eog_events_path)
    
    return eog_events

def read_epochs(name, save_dir, lowpass, highpass):


    epochs_name = name + filter_string(lowpass, highpass) + '-epo.fif'
    epochs_path = join(save_dir, epochs_name)
    epochs = mne.read_epochs(epochs_path)

    return epochs


def read_ica(name, save_dir, lowpass, highpass):

    ica_name = name + filter_string(lowpass, highpass) + '-ica.fif'
    ica_path = join(save_dir, ica_name)
    ica = mne.preprocessing.read_ica(ica_path)

    return ica

def read_ica_epochs(name, save_dir, lowpass, highpass):

    ica_epochs_name = name + filter_string(lowpass, highpass) + '-ica-epo.fif'
    ica_epochs_path = join(save_dir, ica_epochs_name)
    ica_epochs = mne.read_epochs(ica_epochs_path)

    return(ica_epochs)

def read_ssp_epochs(name, save_dir, lowpass, highpass):

    ssp_epochs_name = name + filter_string(lowpass, highpass) + '-ssp-epo.fif'
    ssp_epochs_path = join(save_dir, ssp_epochs_name)
    ssp_epochs = mne.read_epochs(ssp_epochs_path)

    return(ssp_epochs)

def read_ssp_clm_epochs(name, save_dir, lowpass, highpass):

    ssp_epochs_name = name + filter_string(lowpass, highpass) + '-ssp_clm-epo.fif'
    ssp_epochs_path = join(save_dir, ssp_epochs_name)
    ssp_epochs = mne.read_epochs(ssp_epochs_path)

    return(ssp_epochs)
    
def read_ssp_eog_epochs(name, save_dir, lowpass, highpass):

    ssp_epochs_name = name + filter_string(lowpass, highpass) + '-eog_ssp-epo.fif'
    ssp_epochs_path = join(save_dir, ssp_epochs_name)
    ssp_epochs = mne.read_epochs(ssp_epochs_path)

    return(ssp_epochs)

def read_ssp_ecg_epochs(name, save_dir, lowpass, highpass):

    ssp_epochs_name = name + filter_string(lowpass, highpass) + '-ecg_ssp-epo.fif'
    ssp_epochs_path = join(save_dir, ssp_epochs_name)
    ssp_epochs = mne.read_epochs(ssp_epochs_path)

    return(ssp_epochs)
    
def read_evokeds(name, save_dir, lowpass, highpass):

    evokeds_name = name + filter_string(lowpass, highpass) + '-ave.fif'
    evokeds_path = join(save_dir, evokeds_name)
    evokeds = mne.read_evokeds(evokeds_path)

    return evokeds

def read_grand_avg_evokeds(lowpass, highpass, save_dir_averages, grand_avg_dict,
                           event_id):
    ga_dict = {}
    for key in grand_avg_dict:
        trial_dict = {}
        for trial in event_id:
            ga_path = join(save_dir_averages, 'evoked', key + '_'  + trial + \
                           filter_string(lowpass, highpass) + \
                           '-grand_avg-ave.fif')
            evoked = mne.read_evokeds(ga_path)[0]
            trial_dict.update({trial:evoked})
        ga_dict.update({key:trial_dict})
        print(f'Add {key} to ga_dict')
    
    return ga_dict
        
def read_tfr_power(name, save_dir, lowpass, highpass, tfr_method):
    
    power_name = name + filter_string(lowpass, highpass) + '_' + tfr_method + '_pw-tfr.h5'
    power_path = join(save_dir, power_name)
    powers = mne.time_frequency.read_tfrs(power_path)
        
    return powers

def read_tfr_itc(name, save_dir, lowpass, highpass, tfr_method):
    
    itc_name = name + filter_string(lowpass, highpass) + '_' + tfr_method + '_itc-tfr.h5'
    itc_path = join(save_dir, itc_name)
    itcs = mne.time_frequency.read_tfrs(itc_path)
        
    return itcs

def read_grand_avg_tfr(lowpass, highpass, save_dir_averages, grand_avg_dict,
                       event_id):
    ga_dict = {}
    for key in grand_avg_dict:
        trial_dict = {}
        for trial in event_id:
            ga_path = join(save_dir_averages, 'tfr', key + '_'  + trial + \
                           filter_string(lowpass, highpass) + \
                           '-grand_avg-tfr.h5')
            power = mne.time_frequency.read_tfrs(ga_path)[0]
            trial_dict.update({trial:power})
        ga_dict.update({key:trial_dict})
        print(f'Add {key} to ga_dict')
        
    return ga_dict
   
def read_forward(name, save_dir):

    forward_name = name + '-fwd.fif'
    forward_path = join(save_dir, forward_name)
    forward = mne.read_forward_solution(forward_path)

    return forward

def read_noise_covariance(name, save_dir, lowpass, highpass):

    covariance_name = name + filter_string(lowpass, highpass) + '-cov.fif'
    covariance_path = join(save_dir, covariance_name)
    noise_covariance = mne.read_cov(covariance_path)

    return noise_covariance

def read_clm_noise_covariance(name, save_dir, lowpass, highpass):

    covariance_name = name + filter_string(lowpass, highpass) + '-clm-cov.fif'
    covariance_path = join(save_dir, covariance_name)
    noise_covariance = mne.read_cov(covariance_path)

    return noise_covariance

def read_erm_noise_covariance(name, save_dir, lowpass, highpass):

    covariance_name = name + filter_string(lowpass, highpass) + '-erm-cov.fif'
    covariance_path = join(save_dir, covariance_name)
    noise_covariance = mne.read_cov(covariance_path)

    return noise_covariance

def read_inverse_operator(name, save_dir, lowpass, highpass):

    inverse_operator_name = name + filter_string(lowpass, highpass) +  '-inv.fif'
    inverse_operator_path = join(save_dir, inverse_operator_name)
    inverse_operator = mne.minimum_norm.read_inverse_operator(inverse_operator_path)

    return inverse_operator


def read_source_estimates(name, save_dir, lowpass, highpass, method,
                          event_id):
    stcs = dict()

    for trial_type in event_id:
        stc_name = name + filter_string(lowpass, highpass) + \
            '_' + trial_type + '_' + method
        stc_path = join(save_dir, stc_name)
        stcs.update({trial_type:mne.source_estimate.read_source_estimate(stc_path)})

    return stcs

def read_morphed_source_estimates(name, save_dir, lowpass, highpass, method,
                                  event_id):
    stcs = dict()

    for trial_type in event_id:
        stc_name = name + filter_string(lowpass, highpass) + \
            '_' + trial_type + '_' + method + '_morphed'
        stc_path = join(save_dir, stc_name)
        stcs.update({trial_type:mne.source_estimate.read_source_estimate(stc_path)})

    return stcs

def read_connect(name, save_dir, lowpass, highpass, con_methods, con_fmin, con_fmax):
    con_dict = dict()

    for con_method in con_methods:
        file_name = name + filter_string(lowpass, highpass) + \
        '_' + str(con_fmin) + '-' + str(con_fmax) + '_' + con_method + '.npy'
        file_path = join(save_dir, file_name)
        
        con = np.load(file_path)
        con_dict.update({con_method:con})
    
    return con_dict

def read_grand_avg_stcs(lowpass, highpass, save_dir_averages, grand_avg_dict,
                        event_id):
    ga_dict = {}
    for key in grand_avg_dict:
        trial_dict = {}
        for trial in event_id:
            ga_path = join(save_dir_averages, 'stc', key + '_'  + trial + \
                               filter_string(lowpass, highpass) + \
                               '-grand_avg')
            stcs = mne.source_estimate.read_source_estimate(ga_path)
            trial_dict.update({trial:stcs})
        ga_dict.update({key:trial_dict})
        print(f'Add {key} to ga_dict')
        
    return ga_dict

def read_grand_avg_connect(lowpass, highpass, save_dir_averages, grand_avg_dict,
                           con_methods, con_fmin, con_fmax):
    ga_dict = {}
    for key in grand_avg_dict:
        con_methods_dict = {}
        for con_method in con_methods:
            ga_path = join(save_dir_averages, 'connect', key + '_'  + con_method + \
                           filter_string(lowpass, highpass) + \
                           '-grand_avg_connect.npy')
            con = np.load(ga_path)
            con_methods_dict.update({con_method:con})
        ga_dict.update({key:con_methods_dict})
        print(f'Add {key} to ga_dict')
        
    return ga_dict
        
def read_vector_source_estimates(name, save_dir, lowpass, highpass, method):

    evokeds = read_evokeds(name, save_dir, lowpass, highpass)
    stcs = dict()
    for evoked in evokeds:
        trial_type = evoked.comment
        stcs[trial_type] = None
        for stc in stcs:
            stc_name = name + filter_string(lowpass, highpass) + \
                '_' + trial_type + '_' + method + '_vector'
            stc_path = join(save_dir, stc_name)
            stcs[stc] = mne.source_estimate.read_source_estimate(stc_path)

        
    return stcs

def read_source_space(subtomri, subjects_dir, source_space_method):
    
    src_name = subtomri + '_' + source_space_method + '-src.fif'
    source_space_path = join(subjects_dir, subtomri, 'bem',
                             src_name)
    source_space = mne.source_space.read_source_spaces(source_space_path)

    return source_space

def read_morph(mri_subject, morph_to, source_space_method,
               subjects_dir):
    
    morph_name = mri_subject + '--to--' + morph_to + '-' + \
    source_space_method + '-morph.h5'
    morph_path = join(subjects_dir, mri_subject, morph_name)

    morph = mne.read_source_morph(morph_path)
    
    return morph

def read_transformation(save_dir, subtomri):

    trans_name = subtomri + '-trans.fif'
    trans_path = join(save_dir, trans_name)
    trans = mne.read_trans(trans_path)

    return trans

def read_bem_solution(mri_subject, subjects_dir):

    bem_path = join(subjects_dir, mri_subject, 'bem',
                    mri_subject + '-bem-sol.fif')
    bem = mne.read_bem_solution(bem_path)

    return bem

def read_clusters(save_dir_averages, independent_variable_1,
                  independent_variable_2, time_window, lowpass, highpass):

    cluster_name = independent_variable_1 + '_vs_' + independent_variable_2 + \
                    filter_string(lowpass, highpass) + '_time_' + \
                    str(int(time_window[0] * 1e3)) + '-' + \
                    str(int(time_window[1] * 1e3)) + '_msec.cluster'
    cluster_path = join(save_dir_averages, 'statistics', cluster_name)

    with open(cluster_path, 'rb') as filename:
        cluster_dict = pickle.load(filename)

    return cluster_dict

def path_fs_volume(vol_name, subtomri, subjects_dir):
    
    vol_path = join(subjects_dir, subtomri, 'mri', vol_name + '.mgz')
    
    return vol_path

def plot_fs_surf(surf_name, subtomri, subjects_dir):
    
    surf_path = join(subjects_dir, subtomri, 'surf', surf_name)
    
    return surf_path
