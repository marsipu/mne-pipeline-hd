# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
from __future__ import print_function

import pickle
from os.path import join

import mne
import numpy as np

from bin.basic_functions import operations as op


# ==============================================================================
# IO FUNCTIONS
# ==============================================================================
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


def read_filtered(name, save_dir, highpass, lowpass):
    raw_name = name + op.filter_string(highpass, lowpass) + '-raw.fif'
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


def read_epochs(name, save_dir, highpass, lowpass):
    epochs_name = name + op.filter_string(highpass, lowpass) + '-epo.fif'
    epochs_path = join(save_dir, epochs_name)
    epochs = mne.read_epochs(epochs_path)

    return epochs


def read_ica(name, save_dir, highpass, lowpass):
    ica_name = name + op.filter_string(highpass, lowpass) + '-ica.fif'
    ica_path = join(save_dir, ica_name)
    ica = mne.preprocessing.read_ica(ica_path)

    return ica


def read_ica_epochs(name, save_dir, highpass, lowpass):
    ica_epochs_name = name + op.filter_string(highpass, lowpass) + '-ica-epo.fif'
    ica_epochs_path = join(save_dir, ica_epochs_name)
    ica_epochs = mne.read_epochs(ica_epochs_path)

    return ica_epochs


def read_evokeds(name, save_dir, highpass, lowpass):
    evokeds_name = name + op.filter_string(highpass, lowpass) + '-ave.fif'
    evokeds_path = join(save_dir, evokeds_name)
    evokeds = mne.read_evokeds(evokeds_path)

    return evokeds


def read_grand_avg_evokeds(highpass, lowpass, save_dir_averages, grand_avg_dict,
                           event_id):
    ga_dict = {}
    for key in grand_avg_dict:
        trial_dict = {}
        for trial in event_id:
            ga_path = join(save_dir_averages, 'evoked', key + '_' + trial +
                           op.filter_string(highpass, lowpass) + '-grand_avg-ave.fif')
            evoked = mne.read_evokeds(ga_path)[0]
            trial_dict.update({trial: evoked})
        ga_dict.update({key: trial_dict})
        print(f'Add {key} to ga_dict')

    return ga_dict


def read_tfr_power(name, save_dir, highpass, lowpass, tfr_method):
    power_name = name + op.filter_string(highpass, lowpass) + '_' + tfr_method + '_pw-tfr.h5'
    power_path = join(save_dir, power_name)
    powers = mne.time_frequency.read_tfrs(power_path)

    return powers


def read_tfr_itc(name, save_dir, highpass, lowpass, tfr_method):
    itc_name = name + op.filter_string(highpass, lowpass) + '_' + tfr_method + '_itc-tfr.h5'
    itc_path = join(save_dir, itc_name)
    itcs = mne.time_frequency.read_tfrs(itc_path)

    return itcs


def read_grand_avg_tfr(highpass, lowpass, save_dir_averages, grand_avg_dict,
                       event_id):
    ga_dict = {}
    for key in grand_avg_dict:
        trial_dict = {}
        for trial in event_id:
            ga_path = join(save_dir_averages, 'tfr', key + '_' + trial +
                           op.filter_string(highpass, lowpass) +
                           '-grand_avg-tfr.h5')
            power = mne.time_frequency.read_tfrs(ga_path)[0]
            trial_dict.update({trial: power})
        ga_dict.update({key: trial_dict})
        print(f'Add {key} to ga_dict')

    return ga_dict


def read_forward(name, save_dir):
    forward_name = name + '-fwd.fif'
    forward_path = join(save_dir, forward_name)
    forward = mne.read_forward_solution(forward_path)

    return forward


def read_noise_covariance(name, save_dir, highpass, lowpass, erm_noise_cov, ermsub, calm_noise_cov):
    if calm_noise_cov:
        covariance_name = name + op.filter_string(highpass, lowpass) + '-clm-cov.fif'
        covariance_path = join(save_dir, covariance_name)
        noise_covariance = mne.read_cov(covariance_path)
        print('Reading Noise-Covariance from 1-min Calm in raw')
    elif ermsub == 'None' or 'leer' in name or erm_noise_cov is False:
        covariance_name = name + op.filter_string(highpass, lowpass) + '-cov.fif'
        covariance_path = join(save_dir, covariance_name)
        noise_covariance = mne.read_cov(covariance_path)
        print('Reading Noise-Covariance from Epochs')
    else:
        covariance_name = name + op.filter_string(highpass, lowpass) + '-erm-cov.fif'
        covariance_path = join(save_dir, covariance_name)
        noise_covariance = mne.read_cov(covariance_path)
        print('Reading Noise-Covariance from Empty-Room-Data')

    return noise_covariance


def read_inverse_operator(name, save_dir, highpass, lowpass):
    inverse_operator_name = name + op.filter_string(highpass, lowpass) + '-inv.fif'
    inverse_operator_path = join(save_dir, inverse_operator_name)
    inverse_operator = mne.minimum_norm.read_inverse_operator(inverse_operator_path)

    return inverse_operator


def read_source_estimates(name, save_dir, highpass, lowpass, method,
                          event_id):
    stcs = dict()

    for trial_type in event_id:
        stc_name = name + op.filter_string(highpass, lowpass) + \
                   '_' + trial_type + '_' + method
        stc_path = join(save_dir, stc_name)
        stc = mne.source_estimate.read_source_estimate(stc_path)
        stcs.update({trial_type: stc})

    return stcs


def read_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                 event_id):
    n_stcs = dict()

    for trial_type in event_id:
        n_stc_name = name + op.filter_string(highpass, lowpass) + \
                     '_' + trial_type + '_' + inverse_method + '-normal'
        n_stc_path = join(save_dir, n_stc_name)
        n_stc = mne.source_estimate.read_source_estimate(n_stc_path)
        n_stcs.update({trial_type: n_stc})

    return n_stcs


def read_vector_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                 event_id):
    v_stcs = dict()

    for trial_type in event_id:
        v_stc_name = name + op.filter_string(highpass, lowpass) + \
                     '_' + trial_type + '_' + inverse_method + '-vector-stc.h5'
        v_stc_path = join(save_dir, v_stc_name)
        v_stc = mne.source_estimate.read_source_estimate(v_stc_path)
        v_stcs.update({trial_type: v_stc})

    return v_stcs


def read_mixn_source_estimates(name, save_dir, highpass, lowpass, event_id):
    mx_stcs = dict()

    for trial_type in event_id:
        mx_stc_name = name + op.filter_string(highpass, lowpass) + \
                      '_' + trial_type + '-mixn'
        mx_stc_path = join(save_dir, mx_stc_name)
        mx_stc = mne.source_estimate.read_source_estimate(mx_stc_path)
        mx_stcs.update({trial_type: mx_stc})

    return mx_stcs


def read_morphed_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                  event_id):
    stcs = dict()

    for trial_type in event_id:
        stc_name = name + op.filter_string(highpass, lowpass) + \
                   '_' + trial_type + '_' + inverse_method + '_morphed'
        stc_path = join(save_dir, stc_name)
        stcs.update({trial_type: mne.source_estimate.read_source_estimate(stc_path)})

    return stcs


def read_morphed_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                         event_id):
    stcs = dict()

    for trial_type in event_id:
        stc_name = name + op.filter_string(highpass, lowpass) + \
                   '_' + trial_type + '_' + inverse_method + '_morphed_normal'
        stc_path = join(save_dir, stc_name)
        stcs.update({trial_type: mne.source_estimate.read_source_estimate(stc_path)})

    return stcs


def read_mixn_dipoles(name, save_dir, highpass, lowpass, event_id):
    dipoles = dict()
    for trial_type in event_id:
        idx = 0
        dip_list = list()
        try:
            while True:
                mixn_dip_name = name + op.filter_string(highpass, lowpass) + '_' + trial_type + '-mixn-dip-' + str(idx)
                mixn_dip_path = join(save_dir, 'dipoles', mixn_dip_name)
                dip_list.append(mne.read_dipole(mixn_dip_path))
                idx += 1
        except OSError:
            dipoles.update({trial_type: dip_list})
            print(f'{idx + 1} dipoles read for {trial_type}')

    return dipoles


def read_connect(name, save_dir, highpass, lowpass, con_methods, con_fmin, con_fmax,
                 event_id):
    con_dict = dict()
    for ev_id in event_id:
        trial_dict = {}
        for con_method in con_methods:
            file_name = name + op.filter_string(highpass, lowpass) + \
                        '_' + str(con_fmin) + '-' + str(con_fmax) + '_' + con_method \
                        + '-' + ev_id + '.npy'
            file_path = join(save_dir, file_name)

            con = np.load(file_path)
            trial_dict.update({con_method: con})
        con_dict.update({ev_id: trial_dict})

    return con_dict


def read_grand_avg_stcs(highpass, lowpass, save_dir_averages, grand_avg_dict,
                        event_id):
    ga_dict = {}
    for key in grand_avg_dict:
        trial_dict = {}
        for trial in event_id:
            ga_path = join(save_dir_averages, 'stc', key + '_' + trial +
                           op.filter_string(highpass, lowpass) +
                           '-grand_avg')
            stcs = mne.source_estimate.read_source_estimate(ga_path)
            trial_dict.update({trial: stcs})
        ga_dict.update({key: trial_dict})
        print(f'Add {key} to ga_dict')

    return ga_dict


def read_grand_avg_stcs_normal(highpass, lowpass, save_dir_averages, grand_avg_dict,
                               event_id):
    ga_dict = {}
    for key in grand_avg_dict:
        trial_dict = {}
        for trial in event_id:
            ga_path = join(save_dir_averages, 'stc', key + '_' + trial +
                           op.filter_string(highpass, lowpass) +
                           '-grand_avg-normal')
            stcs = mne.source_estimate.read_source_estimate(ga_path)
            trial_dict.update({trial: stcs})
        ga_dict.update({key: trial_dict})
        print(f'Add {key} to ga_dict')

    return ga_dict


def read_grand_avg_connect(highpass, lowpass, save_dir_averages, grand_avg_dict,
                           con_methods, event_id):
    ga_dict = {}
    for key in grand_avg_dict:
        ev_id_dict = {}
        for ev_id in event_id:
            con_methods_dict = {}
            for con_method in con_methods:
                ga_path = join(save_dir_averages, 'connect', key + '_' + con_method +
                               op.filter_string(highpass, lowpass) +
                               '-grand_avg_connect' + '-' + ev_id + '.npy')
                con = np.load(ga_path)
                con_methods_dict.update({con_method: con})
            ev_id_dict.update({ev_id: con_methods_dict})
        ga_dict.update({key: ev_id_dict})
        print(f'Add {key} to ga_dict')

    return ga_dict


def read_label_power(name, save_dir, highpass, lowpass,
                     event_id, target_labels):
    power_dict = {}

    for ev_id in event_id:
        power_dict.update({ev_id: {}})
        for hemi in target_labels:
            for label_name in target_labels[hemi]:
                power_dict[ev_id].update({label_name: {}})

                # power = np.load(join(save_dir, f'{name}_{label_name}_{op.filter_string(highpass, lowpass)}_{ev_id}_pw-tfr.npy'))
                # itc = np.load(join(save_dir, f'{name}_{label_name}_{op.filter_string(highpass, lowpass)}_{ev_id}_itc-tfr.npy'))
                power_ind = np.load(
                        join(save_dir,
                             f'{name}_{label_name}_{op.filter_string(highpass, lowpass)}_{ev_id}_pw-ind-tfr.npy'))
                itc_ind = np.load(
                        join(save_dir,
                             f'{name}_{label_name}_{op.filter_string(highpass, lowpass)}_{ev_id}_itc-ind-tfr.npy'))

                #                power_dict[ev_id][label_name].update({'power':power})
                #                power_dict[ev_id][label_name].update({'itc':itc})
                power_dict[ev_id][label_name].update({'power_ind': power_ind})
                power_dict[ev_id][label_name].update({'itc_ind': itc_ind})

    return power_dict


def read_ga_label_power(grand_avg_dict, event_id, target_labels,
                        save_dir_averages):
    ga_dict = {}
    for key in grand_avg_dict:
        ga_dict.update({key: {}})
        for ev_id in event_id:
            ga_dict[key].update({ev_id: {}})
            for hemi in target_labels:
                for label_name in target_labels[hemi]:
                    ga_dict[key][ev_id].update({label_name: {}})
                    pw_ga_path = join(save_dir_averages, 'tfr',
                                      f'{key}-{ev_id}_{label_name}_pw-ind.npy')
                    pw = np.load(pw_ga_path)
                    ga_dict[key][ev_id][label_name].update({'power': pw})
                    itc_ga_path = join(save_dir_averages, 'tfr',
                                       f'{key}-{ev_id}_{label_name}_itc-ind.npy')
                    itc = np.load(itc_ga_path)

                    ga_dict[key][ev_id][label_name].update({'itc': itc})
        print(f'Added {key} to ga_dict')

    return ga_dict



def read_source_space(subtomri, subjects_dir, source_space_method):
    src_name = subtomri + '_' + source_space_method + '-src.fif'
    source_space_path = join(subjects_dir, subtomri, 'bem',
                             src_name)
    source_space = mne.source_space.read_source_spaces(source_space_path)

    return source_space


def read_vol_source_space(subtomri, subjects_dir):
    vol_src_name = subtomri + '-vol-src.fif'
    vol_src_path = join(subjects_dir, subtomri, 'bem', vol_src_name)
    vol_src = mne.source_space.read_source_spaces(vol_src_path)

    return vol_src


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
                  independent_variable_2, time_window, highpass, lowpass):
    cluster_name = independent_variable_1 + '_vs_' + independent_variable_2 + \
                   op.filter_string(highpass, lowpass) + '_time_' + \
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
