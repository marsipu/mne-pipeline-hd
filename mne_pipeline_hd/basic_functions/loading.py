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
from os import listdir, makedirs, remove
from os.path import exists, join
from pathlib import Path

import mne
import numpy as np


# ==============================================================================
# LOADING FUNCTIONS
# ==============================================================================

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
    raw_name = name + filter_string(highpass, lowpass) + '-raw.fif'
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
    epochs_name = name + filter_string(highpass, lowpass) + '-epo.fif'
    epochs_path = join(save_dir, epochs_name)
    epochs = mne.read_epochs(epochs_path)

    return epochs


def read_ica(name, save_dir, highpass, lowpass):
    ica_name = name + filter_string(highpass, lowpass) + '-ica.fif'
    ica_path = join(save_dir, ica_name)
    ica = mne.preprocessing.read_ica(ica_path)

    return ica


def read_ica_epochs(name, save_dir, highpass, lowpass):
    ica_epochs_name = name + filter_string(highpass, lowpass) + '-ica-epo.fif'
    ica_epochs_path = join(save_dir, ica_epochs_name)
    ica_epochs = mne.read_epochs(ica_epochs_path)

    return ica_epochs


def read_evokeds(name, save_dir, highpass, lowpass):
    evokeds_name = name + filter_string(highpass, lowpass) + '-ave.fif'
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
                           filter_string(highpass, lowpass) + '-grand_avg-ave.fif')
            evoked = mne.read_evokeds(ga_path)[0]
            trial_dict.update({trial: evoked})
        ga_dict.update({key: trial_dict})
        print(f'Add {key} to ga_dict')

    return ga_dict


def read_tfr_power(name, save_dir, highpass, lowpass, tfr_method):
    power_name = name + filter_string(highpass, lowpass) + '_' + tfr_method + '_pw-tfr.h5'
    power_path = join(save_dir, power_name)
    powers = mne.time_frequency.read_tfrs(power_path)

    return powers


def read_tfr_itc(name, save_dir, highpass, lowpass, tfr_method):
    itc_name = name + filter_string(highpass, lowpass) + '_' + tfr_method + '_itc-tfr.h5'
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
                           filter_string(highpass, lowpass) +
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
        covariance_name = name + filter_string(highpass, lowpass) + '-clm-cov.fif'
        covariance_path = join(save_dir, covariance_name)
        noise_covariance = mne.read_cov(covariance_path)
        print('Reading Noise-Covariance from 1-min Calm in raw')
    elif ermsub == 'None' or 'leer' in name or erm_noise_cov is False:
        covariance_name = name + filter_string(highpass, lowpass) + '-cov.fif'
        covariance_path = join(save_dir, covariance_name)
        noise_covariance = mne.read_cov(covariance_path)
        print('Reading Noise-Covariance from Epochs')
    else:
        covariance_name = name + filter_string(highpass, lowpass) + '-erm-cov.fif'
        covariance_path = join(save_dir, covariance_name)
        noise_covariance = mne.read_cov(covariance_path)
        print('Reading Noise-Covariance from Empty-Room-Data')

    return noise_covariance


def read_inverse_operator(name, save_dir, highpass, lowpass):
    inverse_operator_name = name + filter_string(highpass, lowpass) + '-inv.fif'
    inverse_operator_path = join(save_dir, inverse_operator_name)
    inverse_operator = mne.minimum_norm.read_inverse_operator(inverse_operator_path)

    return inverse_operator


def read_source_estimates(name, save_dir, highpass, lowpass, method,
                          event_id):
    stcs = dict()

    for trial in event_id:
        stc_name = name + filter_string(highpass, lowpass) + \
                   '_' + trial + '_' + method
        stc_path = join(save_dir, stc_name)
        stc = mne.source_estimate.read_source_estimate(stc_path)
        stcs.update({trial: stc})

    return stcs


def read_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                 event_id):
    n_stcs = dict()

    for trial in event_id:
        n_stc_name = name + filter_string(highpass, lowpass) + \
                     '_' + trial + '_' + inverse_method + '-normal'
        n_stc_path = join(save_dir, n_stc_name)
        n_stc = mne.source_estimate.read_source_estimate(n_stc_path)
        n_stcs.update({trial: n_stc})

    return n_stcs


def read_vector_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                 event_id):
    v_stcs = dict()

    for trial in event_id:
        v_stc_name = name + filter_string(highpass, lowpass) + \
                     '_' + trial + '_' + inverse_method + '-vector-stc.h5'
        v_stc_path = join(save_dir, v_stc_name)
        v_stc = mne.source_estimate.read_source_estimate(v_stc_path)
        v_stcs.update({trial: v_stc})

    return v_stcs


def read_mixn_source_estimates(name, save_dir, highpass, lowpass, event_id):
    mx_stcs = dict()

    for trial in event_id:
        mx_stc_name = name + filter_string(highpass, lowpass) + \
                      '_' + trial + '-mixn'
        mx_stc_path = join(save_dir, mx_stc_name)
        mx_stc = mne.source_estimate.read_source_estimate(mx_stc_path)
        mx_stcs.update({trial: mx_stc})

    return mx_stcs


def read_morphed_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                  event_id):
    stcs = dict()

    for trial in event_id:
        stc_name = name + filter_string(highpass, lowpass) + \
                   '_' + trial + '_' + inverse_method + '_morphed'
        stc_path = join(save_dir, stc_name)
        stcs.update({trial: mne.source_estimate.read_source_estimate(stc_path)})

    return stcs


def read_morphed_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                         event_id):
    stcs = dict()

    for trial in event_id:
        stc_name = name + filter_string(highpass, lowpass) + \
                   '_' + trial + '_' + inverse_method + '_morphed_normal'
        stc_path = join(save_dir, stc_name)
        stcs.update({trial: mne.source_estimate.read_source_estimate(stc_path)})

    return stcs


def read_mixn_dipoles(name, save_dir, highpass, lowpass, event_id):
    dipoles = dict()
    for trial in event_id:
        idx = 0
        dip_list = list()
        try:
            while True:
                mixn_dip_name = name + filter_string(highpass, lowpass) + '_' + trial + '-mixn-dip-' + str(idx)
                mixn_dip_path = join(save_dir, 'dipoles', mixn_dip_name)
                dip_list.append(mne.read_dipole(mixn_dip_path))
                idx += 1
        except OSError:
            dipoles.update({trial: dip_list})
            print(f'{idx + 1} dipoles read for {trial}')

    return dipoles


def read_connect(name, save_dir, highpass, lowpass, con_methods, con_fmin, con_fmax,
                 event_id):
    con_dict = dict()
    for ev_id in event_id:
        trial_dict = {}
        for con_method in con_methods:
            file_name = name + filter_string(highpass, lowpass) + \
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
                           filter_string(highpass, lowpass) +
                           '-grand_avg')
            trial_dict[trial] = mne.source_estimate.read_source_estimate(ga_path)
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
                           filter_string(highpass, lowpass) +
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
                               filter_string(highpass, lowpass) +
                               '-grand_avg_connect' + '-' + ev_id + '.npy')
                con = np.load(ga_path)
                con_methods_dict.update({con_method: con})
            ev_id_dict.update({ev_id: con_methods_dict})
        ga_dict.update({key: ev_id_dict})
        print(f'Add {key} to ga_dict')

    return ga_dict


def read_source_space(subtomri, subjects_dir, source_space_spacing):
    src_name = subtomri + '_' + source_space_spacing + '-src.fif'
    source_space_path = join(subjects_dir, subtomri, 'bem',
                             src_name)
    source_space = mne.source_space.read_source_spaces(source_space_path)

    return source_space


def read_vol_source_space(subtomri, subjects_dir):
    vol_src_name = subtomri + '-vol-src.fif'
    vol_src_path = join(subjects_dir, subtomri, 'bem', vol_src_name)
    vol_src = mne.source_space.read_source_spaces(vol_src_path)

    return vol_src


def read_morph(mri_subject, morph_to, source_space_spacing,
               subjects_dir):
    morph_name = mri_subject + '--to--' + morph_to + '-' + \
                 source_space_spacing + '-morph.h5'
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
                   filter_string(highpass, lowpass) + '_time_' + \
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


class BaseSub:
    """ Base-Class for Sub (The current File/MRI-File/Grand-Average-Group, which is executed)"""

    def __init__(self, name, main_win):
        # Basic Attributes (partly taking parameters or main-win-attributes for easier access)
        self.name = name
        self.mw = main_win
        self.pr = main_win.pr
        self.p_preset = self.pr.p_preset
        self.p = main_win.pr.parameters[self.p_preset]
        self.subjects_dir = self.pr.subjects_dir
        self.save_plots = self.mw.settings.value('save_plots')
        self.figures_path = self.pr.figures_path
        self.img_format = self.mw.settings.value('img_format')

    def save_file_params(self, path):
        file_name = Path(path).name
        for p_name in self.pr.parameters[self.p_preset]:
            self.pr.file_parameters.loc[file_name, p_name] = str(self.pr.parameters[self.p_preset][p_name])


class CurrentSub(BaseSub):
    """ Class for File-Data in File-Loop"""

    def __init__(self, name, main_win, mri_sub=None):

        super().__init__(name, main_win)

        # Additional Attributes
        self.save_dir = join(self.pr.data_path, name)

        # Attributes, which are needed to run the subject
        try:
            self.ermsub = self.mw.pr.erm_dict[name]
        except KeyError as k:
            print(f'No erm_measurement assigned for {k}')
            raise RuntimeError(f'No erm_measurement assigned for {k}')
        try:
            self.subtomri = self.mw.pr.sub_dict[name]
        except KeyError as k:
            print(f'No mri_subject assigned to {k}')
            raise RuntimeError(f'No mri_subject assigned to {k}')
        try:
            self.bad_channels = self.mw.pr.bad_channels_dict[name]
        except KeyError as k:
            print(f'No bad channels for {k}')
            raise RuntimeError(f'No bad channels for {k}')

        self.mri_sub = mri_sub or CurrentMRISub(self.subtomri, main_win)

        ################################################################################################################
        # Data-Attributes (not to be called directly)
        ################################################################################################################

        self._info = None
        self._raw = None
        self._raw_filtered = None
        self._erm_filtered = None
        self._events = None
        self._epochs = None
        self._ar_epochs = None
        self._ica = None
        self._ica_epochs = None
        self._evokeds = None
        self._power_tfr = None
        self._itc_tfr = None

        self._trans = None
        self._forward = None
        self._noise_cov = None
        self._inverse = None
        self._stcs = None
        self._ltc = None
        self._mxn_stcs = None
        self._mxn_dips = None
        self._ecd_dips = None

        ################################################################################################################
        # Paths
        ################################################################################################################

        self.raw_path = join(self.save_dir, f'{name}-raw.fif')
        self.raw_filtered_path = join(self.save_dir, f'{name}_{self.p_preset}-filtered-raw.fif')
        self.old_raw_filtered_path = join(self.save_dir,
                                          f'{name}{filter_string(self.p["highpass"], self.p["lowpass"])}-raw.fif')

        self.erm_path = join(self.pr.erm_data_path, self.ermsub, f'{self.ermsub}-raw.fif')
        self.erm_filtered_path = join(self.pr.erm_data_path, self.ermsub, f'{self.ermsub}_{self.p_preset}-raw.fif')
        self.old_erm_filtered_path = join(self.pr.erm_data_path, self.ermsub,
                                          self.ermsub + filter_string(self.p["highpass"], self.p["lowpass"])
                                          + '-raw.fif')

        self.events_path = join(self.save_dir, f'{name}_{self.p_preset}-eve.fif')
        self.old_events_path = join(self.save_dir, f'{name}-eve.fif')

        self.epochs_path = join(self.save_dir, f'{name}_{self.p_preset}-epo.fif')
        self.old_epochs_path = join(self.save_dir,
                                    name + filter_string(self.p["highpass"], self.p["lowpass"]) + '-epo.fif')

        self.ar_epochs_path = join(self.save_dir, f'{name}_{self.p_preset}-ar-epo.fif')

        self.ica_path = join(self.save_dir, f'{name}_{self.p_preset}-ica.fif')
        self.old_ica_path = join(self.save_dir,
                                 name + filter_string(self.p["highpass"], self.p["lowpass"]) + '-ica.fif')

        self.ica_epochs_path = join(self.save_dir, f'{name}_{self.p_preset}-ica-epo.fif')
        self.old_ica_epochs_path = join(self.save_dir,
                                        name + filter_string(self.p["highpass"], self.p["lowpass"]) + '-ica-epo.fif')

        self.evokeds_path = join(self.save_dir, f'{name}_{self.p_preset}-ave.fif')
        self.old_evokeds_path = join(self.save_dir,
                                     name + filter_string(self.p["highpass"], self.p["lowpass"]) + '-ave.fif')

        self.power_tfr_path = join(self.save_dir, f'{name}_{self.p_preset}_{self.p["tfr_method"]}-pw-tfr.h5')
        self.itc_tfr_path = join(self.save_dir, f'{name}_{self.p_preset}_{self.p["tfr_method"]}-itc-tfr.h5')

        self.trans_path = join(self.save_dir, f'{self.subtomri}-trans.fif')

        self.old_forward_path = join(self.save_dir, f'{self.name}_{self.p_preset}-fwd.fif')
        self.forward_path = join(self.save_dir, f'{self.name}-fwd.fif')

        self.calm_cov_path = join(self.save_dir, f'{name}_{self.p_preset}-calm-cov.fif')
        self.old_calm_cov_path = join(self.save_dir,
                                      name + filter_string(self.p["highpass"], self.p["lowpass"]) + '-clm-cov.fif')
        self.erm_cov_path = join(self.save_dir, f'{name}_{self.p_preset}-erm-cov.fif')
        self.old_erm_cov_path = join(self.save_dir,
                                     name + filter_string(self.p["highpass"], self.p["lowpass"]) + '-erm-cov.fif')

        self.cov_path = join(self.save_dir, f'{name}_{self.p_preset}-cov.fif')
        self.old_cov_path = join(self.save_dir,
                                 name + filter_string(self.p["highpass"], self.p["lowpass"]) + '-cov.fif')

        self.inverse_path = join(self.save_dir, f'{name}_{self.p_preset}-inv.fif')
        self.old_inverse_path = join(self.save_dir,
                                     name + filter_string(self.p["highpass"], self.p["lowpass"]) + '-inv.fif')

    ####################################################################################################################
    # Load- & Save-Methods
    ####################################################################################################################
    def load_info(self):
        """Get raw-info, either from info_dict in project or from raw-file if not in info_dict"""
        if self._info is None:
            self._info = mne.io.read_info(self.raw_path)

        return self._info

    def load_raw(self):
        if self._raw is None:
            self._raw = mne.io.read_raw_fif(self.raw_path, preload=True)

        return self._raw

    def load_filtered(self):
        if self._raw_filtered is None:
            try:
                self._raw_filtered = mne.io.read_raw_fif(self.raw_filtered_path, preload=True)
            except FileNotFoundError:
                self._raw_filtered = mne.io.read_raw_fif(self.old_raw_filtered_path, preload=True)

        return self._raw_filtered

    # Todo: Save Storage with GUI (and also look to
    def save_filtered(self, raw_filtered):
        self._raw_filtered = raw_filtered
        if not self.mw.settings.value('save_storage', defaulValue=0):
            raw_filtered.save(self.raw_filtered_path, overwrite=True)
            self.save_file_params(self.raw_filtered_path)

    def load_erm(self):
        # unfiltered erm is not considered important enough to be a sub-attribute
        erm = mne.io.read_raw_fif(self.erm_path, preload=True)

        return erm

    def load_erm_filtered(self):
        if self._erm_filtered is None:
            try:
                self._erm_filtered = mne.io.read_raw_fif(self.erm_filtered_path, preload=True)
            except FileNotFoundError:
                self._erm_filtered = mne.io.read_raw_fif(self.old_erm_filtered_path, preload=True)

        return self._erm_filtered

    def save_erm_filtered(self, erm_filtered):
        self._erm_filtered = erm_filtered
        if not self.mw.settings.value('save_storage', defaulValue=0):
            self._erm_filtered.save(self.erm_filtered_path)
            self.save_file_params(self.erm_filtered_path)

    def load_events(self):
        if self._events is None:
            self._events = mne.read_events(self.events_path)

        return self._events

    def save_events(self, events):
        self._events = events
        mne.event.write_events(self.events_path, events)
        self.save_file_params(self.events_path)

    def load_epochs(self):
        if self._epochs is None:
            try:
                self._epochs = mne.read_epochs(self.epochs_path)
            except FileNotFoundError:
                self._epochs = mne.read_epochs(self.old_epochs_path)

        return self._epochs

    def save_epochs(self, epochs):
        self._epochs = epochs
        epochs.save(self.epochs_path, overwrite=True)
        self.save_file_params(self.epochs_path)

    def load_ar_epochs(self):
        if self._ar_epochs is None:
            self._ar_epochs = mne.read_epochs(self.ar_epochs_path)

        return self._ar_epochs

    def save_ar_epochs(self, ar_epochs):
        self._ar_epochs = ar_epochs
        ar_epochs.save(self.ar_epochs_path, overwrite=True)
        self.save_file_params(self.ar_epochs_path)

    def load_ica(self):
        if self._ica is None:
            try:
                self._ica = mne.preprocessing.read_ica(self.ica_path)
            except FileNotFoundError:
                self._ica = mne.preprocessing.read_ica(self.old_ica_path)

        return self._ica

    def save_ica(self, ica):
        self._ica = ica
        ica.save(self.ica_path)
        self.save_file_params(self.ica_path)

    def load_ica_epochs(self):
        if self._ica_epochs is None:
            try:
                self._ica_epochs = mne.read_epochs(self.ica_epochs_path)
            except FileNotFoundError:
                self._ica_epochs = mne.read_epochs(self.old_ica_epochs_path)

        return self._ica_epochs

    def save_ica_epochs(self, ica_epochs):
        self._ica_epochs = ica_epochs
        ica_epochs.save(self.ica_epochs_path, overwrite=True)
        self.save_file_params(self.ica_epochs_path)

    def load_evokeds(self):
        if self._evokeds is None:
            try:
                self._evokeds = mne.read_evokeds(self.evokeds_path)
            except FileNotFoundError:
                self._evokeds = mne.read_evokeds(self.old_evokeds_path)

        return self._evokeds

    def save_evokeds(self, evokeds):
        self._evokeds = evokeds
        mne.evoked.write_evokeds(self.evokeds_path, evokeds)
        self.save_file_params(self.evokeds_path)

    def load_power_tfr(self):
        if self._power_tfr is None:
            self._power_tfr = mne.time_frequency.read_tfrs(self.power_tfr_path)

        return self._power_tfr

    def save_power_tfr(self, powers):
        self._power_tfr = powers
        mne.time_frequency.write_tfrs(self.power_tfr_path, powers, overwrite=True)
        self.save_file_params(self.power_tfr_path)

    def load_itc_tfr(self):
        if self._itc_tfr is None:
            self._itc_tfr = mne.time_frequency.read_tfrs(self.itc_tfr_path)

        return self._itc_tfr

    def save_itc_tfr(self, itcs):
        self._itc_tfr = itcs
        mne.time_frequency.write_tfrs(self.itc_tfr_path, itcs, overwrite=True)
        self.save_file_params(self.itc_tfr_path)

    # Source-Space
    def load_transformation(self):
        if self._trans is None:
            self._trans = mne.read_trans(self.trans_path)

        return self._trans

    def load_forward(self):
        if self._forward is None:
            self._forward = mne.read_forward_solution(self.forward_path, verbose='WARNING')

        return self._forward

    def save_forward(self, forward):
        self._forward = forward
        mne.write_forward_solution(self.forward_path, forward, overwrite=True)
        self.save_file_params(self.forward_path)

    def load_noise_covariance(self):
        if self._noise_cov is None:
            if self.p['calm_noise_cov']:
                try:
                    self._noise_cov = mne.read_cov(self.calm_cov_path)
                    print('Reading Noise-Covariance from 1-min Calm in raw')
                except FileNotFoundError:
                    self._noise_cov = mne.read_cov(self.old_calm_cov_path)
                    print('Reading Noise-Covariance from 1-min Calm in raw')
            elif self.ermsub == 'None' or self.p['erm_noise_cov'] is False:
                try:
                    self._noise_cov = mne.read_cov(self.cov_path)
                    print('Reading Noise-Covariance from Epochs')
                except FileNotFoundError:
                    self._noise_cov = mne.read_cov(self.old_cov_path)
                    print('Reading Noise-Covariance from Epochs')
            else:
                try:
                    self._noise_cov = mne.read_cov(self.erm_cov_path)
                    print('Reading Noise-Covariance from Empty-Room-Data')
                except FileNotFoundError:
                    self._noise_cov = mne.read_cov(self.erm_cov_path)
                    print('Reading Noise-Covariance from Empty-Room-Data')

        return self._noise_cov

    def save_noise_covariance(self, noise_cov, cov_type):
        self._noise_cov = noise_cov
        if cov_type == 'calm':
            mne.cov.write_cov(self.calm_cov_path, noise_cov)
            self.save_file_params(self.calm_cov_path)
        elif cov_type == 'epochs':
            mne.cov.write_cov(self.cov_path, noise_cov)
            self.save_file_params(self.cov_path)
        elif cov_type == 'erm':
            mne.cov.write_cov(self.erm_cov_path, noise_cov)
            self.save_file_params(self.erm_cov_path)

    def load_inverse_operator(self):
        if self._inverse is None:
            try:
                self._inverse = mne.minimum_norm.read_inverse_operator(self.inverse_path, verbose='WARNING')
            except FileNotFoundError:
                self._inverse = mne.minimum_norm.read_inverse_operator(self.old_inverse_path, verbose='WARNING')

        return self._inverse

    def save_inverse_operator(self, inverse):
        self._inverse = inverse
        mne.minimum_norm.write_inverse_operator(self.inverse_path, inverse)
        self.save_file_params(self.inverse_path)

    def load_source_estimates(self):
        if self._stcs is None:
            self._stcs = dict()
            for trial in self.p['event_id']:
                try:
                    stc_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}')
                    stc = mne.source_estimate.read_source_estimate(stc_path)
                except OSError:
                    old_stc_path = join(self.save_dir,
                                        f'{self.name}{filter_string(self.p["highpass"], self.p["lowpass"])}'
                                        f'_{trial}_{self.p["inverse_method"]}')
                    stc = mne.source_estimate.read_source_estimate(old_stc_path)
                self._stcs[trial] = stc

        return self._stcs

    def save_source_estimates(self, stcs):
        self._stcs = stcs
        for trial in stcs:
            stc_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}')
            stcs[trial].save(stc_path)
            self.save_file_params(stc_path)

    def load_morphed_source_estimates(self):
        if self._morphed_stcs is None:
            self._morphed_stcs = dict()
            for trial in self.p['event_id']:
                try:
                    morphed_stc_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}-morphed')
                    morphed_stc = mne.source_estimate.read_source_estimate(morphed_stc_path)
                except FileNotFoundError:
                    old_morphed_stc_path = join(self.save_dir,
                                                f'{self.name}{filter_string(self.p["highpass"], self.p["lowpass"])}'
                                                f'_{trial}_{self.p["inverse_method"]} + _morphed')
                    morphed_stc = mne.source_estimate.read_source_estimate(old_morphed_stc_path)
                self._morphed_stcs[trial] = morphed_stc

    def save_morphed_source_estimates(self, morphed_stcs):
        self._morphed_stcs = morphed_stcs
        for trial in morphed_stcs:
            morphed_stc_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}-morphed')
            morphed_stcs[trial].save(morphed_stc_path)
            self.save_file_params(morphed_stc_path)

    def load_mixn_dipoles(self):
        if self._mixn_dips is None:
            self._mixn_dips = dict()
            for trial in self.p['event_id']:
                idx = 0
                dip_list = list()
                try:
                    for idx in range(len(listdir(join(self.save_dir, 'mixn_dipoles')))):
                        mixn_dip_path = join(self.save_dir, 'mixn_dipoles',
                                             f'{self.name}_{trial}_{self.p_preset}-mixn-dip{idx}.dip')
                        dip_list.append(mne.read_dipole(mixn_dip_path))
                        idx += 1
                except FileNotFoundError:
                    pass
                self._mixn_dips[trial] = dip_list
                print(f'{idx + 1} dipoles read for {self.name}-{trial}')

        return self._mixn_dips

    def save_mixn_dipoles(self, mixn_dips):
        self._mxn_dips = mixn_dips

        # Remove old dipoles
        if not exists(join(self.save_dir, 'mixn_dipoles')):
            makedirs(join(self.save_dir, 'mixn_dipoles'))
        old_dipoles = listdir(join(self.save_dir, 'mixn_dipoles'))
        for file in old_dipoles:
            remove(join(self.save_dir, 'mixn_dipoles', file))

        for trial in mixn_dips:
            for idx, dip in enumerate(mixn_dips[trial]):
                mxn_dip_path = join(self.save_dir, 'mixn_dipoles',
                                    f'{self.name}_{trial}_{self.p_preset}-mixn-dip{idx}.dip')
                dip.save(mxn_dip_path)
                self.save_file_params(mxn_dip_path)

    def load_mixn_source_estimates(self):
        if self._mxn_stcs is None:
            self._mxn_stcs = dict()
            for trial in self.p['event_id']:
                try:
                    mx_stc_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}-mixn')
                    mx_stc = mne.source_estimate.read_source_estimate(mx_stc_path)
                except FileNotFoundError:
                    mx_stc_name = self.name + filter_string(self.p["highpass"], self.p["lowpass"]) + \
                                  '_' + trial + '-mixn'
                    mx_stc_path = join(self.save_dir, mx_stc_name)
                    mx_stc = mne.source_estimate.read_source_estimate(mx_stc_path)
                self._mxn_stcs.update({trial: mx_stc})

        return self._mxn_stcs

    def save_mixn_source_estimates(self, stcs):
        self._mxn_stcs = stcs
        for trial in stcs:
            stc_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}-mixn')
            stcs[trial].save(stc_path)
            self.save_file_params(stc_path)

    def load_ecd(self):
        if self._ecd_dips is None:
            self._ecd_dips = {}
            for trial in self.p['event_id']:
                self._ecd_dips[trial] = {}
                for dip in self.p['ecd_times'][self.name]:
                    ecd_dip_path = join(self.save_dir, 'ecd_dipoles',
                                        f'{self.name}_{trial}_{self.p_preset}_{dip}-ecd-dip.dip')
                    self._ecd_dips[trial][dip] = mne.read_dipole(ecd_dip_path)
        return self._ecd_dips

    def save_ecd(self, ecd_dips):
        self._ecd_dips = ecd_dips
        if not exists(join(self.save_dir, 'ecd_dipoles')):
            makedirs(join(self.save_dir, 'ecd_dipoles'))

        for trial in ecd_dips:
            for dip in ecd_dips[trial]:
                ecd_dip_path = join(self.save_dir, 'ecd_dipoles',
                                    f'{self.name}_{trial}_{self.p_preset}_{dip}-ecd-dip.dip')
                ecd_dips[trial][dip].save(ecd_dip_path, overwrite=True)
                self.save_file_params(ecd_dip_path)

    def load_ltc(self):
        if self._ltc is None:
            self._ltc = {}
            for trial in self.p['event_id']:
                self._ltc[trial] = {}
                for label in self.p['target_labels']:
                    ltc_path = join(self.save_dir, 'label_time_course',
                                    f'{self.name}_{trial}_{self.p_preset}_{label}.npy')
                    self._ltc[trial][label] = np.load(ltc_path)

        return self._ltc

    def save_ltc(self, ltc):
        self._ltc = ltc
        if not exists(join(self.save_dir, 'label_time_course')):
            makedirs(join(self.save_dir, 'label_time_course'))

        for trial in ltc:
            for label in ltc[trial]:
                ltc_path = join(self.save_dir, 'label_time_course',
                                f'{self.name}_{trial}_{self.p_preset}_{label}.npy')
                np.save(ltc_path, ltc[trial][label])
                self.save_file_params(ltc_path)

    def load_connectivity(self):
        if self._connectivity is None:
            self._connectivity = dict()
            for trial in self.p['event_id']:
                self._connectivity[trial] = {}
                for con_method in self.p['con_methods']:
                    try:
                        con_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}_{con_method}.npy')
                        self._connectivity[trial][con_method] = np.load(con_path)
                    except FileNotFoundError:
                        pass

        return self._connectivity

    def save_connectivity(self, con_dict):
        for trial in con_dict:
            for con_method in con_dict[trial]:
                con_path = join(self.save_dir, f'{self.name}_{trial}_{self.p_preset}_{con_method}.npy')
                np.save(con_path)
                self.save_file_params(con_path)

    # Todo: Better solution for Current-File call and update together with function-call
    def update_file_data(self):
        self.ermsub = self.mw.pr.erm_dict[self.name]
        self.subtomri = self.mw.pr.sub_dict[self.name]
        self.bad_channels = self.mw.pr.bad_channels_dict[self.name]


class CurrentMRISub(BaseSub):
    # Todo: Store available parcellations, surfaces, etc. (maybe already loaded with import?)
    def __init__(self, name, main_win):

        super().__init__(name, main_win)

        # Additional Attributes
        self.save_dir = join(self.pr.subjects_dir, self.name)

        ################################################################################################################
        # Data-Attributes (not to be called directly)
        ################################################################################################################

        self._source_space = None
        self._bem_model = None
        self._bem_solution = None
        self._vol_source_space = None
        self._source_morph = None
        self._labels = None

        ################################################################################################################
        # Paths
        ################################################################################################################

        self.source_space_path = join(self.save_dir, 'bem', f'{self.name}_{self.p["source_space_spacing"]}-src.fif')
        self.bem_model_path = join(self.save_dir, 'bem', f'{self.name}-bem.fif')
        self.bem_solution_path = join(self.save_dir, 'bem', f'{self.name}-bem-sol.fif')
        self.vol_source_space_path = join(self.save_dir, 'bem', f'{self.name}-vol-src.fif')
        self.source_morph_path = join(self.save_dir,
                                      f'{self.name}--to--{self.p["morph_to"]}_'
                                      f'{self.p["source_space_spacing"]}-morph.h5')
        self.old_source_morph_path = join(self.save_dir,
                                          f'{self.name}--to--{self.p["morph_to"]}-'
                                          f'{self.p["source_space_spacing"]}-morph.h5')

    ####################################################################################################################
    # Load- & Save-Methods
    ####################################################################################################################
    def load_source_space(self):
        if self._source_space is None:
            self._source_space = mne.source_space.read_source_spaces(self.source_space_path)

        return self._source_space

    def save_source_space(self, src):
        self._source_space = src
        src.save(self.source_space_path, overwrite=True)
        self.save_file_params(self.source_space_path)

    def load_bem_model(self):
        if self._bem_model is None:
            self._bem_model = mne.read_bem_surfaces(self.bem_model_path)

        return self._bem_model

    def save_bem_model(self, bem_model):
        self._bem_model = bem_model
        mne.write_bem_surfaces(self.bem_model_path, bem_model)
        self.save_file_params(self.bem_model_path)

    def load_bem_solution(self):
        if self._bem_solution is None:
            self._bem_solution = mne.read_bem_solution(self.bem_solution_path)

        return self._bem_solution

    def save_bem_solution(self, bem_solution):
        self._bem_solution = bem_solution
        mne.write_bem_solution(self.bem_solution_path, bem_solution)
        self.save_file_params(self.bem_solution_path)

    def load_vol_source_space(self):
        if self._vol_source_space is None:
            self._vol_source_space = mne.source_space.read_source_spaces(self.vol_source_space_path)

        return self._vol_source_space

    def save_vol_source_space(self, vol_source_space):
        self._vol_source_space = vol_source_space
        vol_source_space.save(self.vol_source_space_path, overwrite=True)
        self.save_file_params(self.vol_source_space_path)

    def load_source_morph(self):
        if self._source_morph is None:
            try:
                self._source_morph = mne.read_source_morph(self.source_morph_path)
            except FileNotFoundError:
                self._source_morph = mne.read_source_morph(self.old_source_morph_path)

        return self._source_morph

    def save_source_morph(self, source_morph):
        self._source_morph = source_morph
        source_morph.save(self.source_morph_path, overwrite=True)
        self.save_file_params(self.source_morph_path)

    def load_parc_labels(self):
        if self._labels is None:
            self._labels = mne.read_labels_from_annot(self.name, parc=self.p['parcellation'],
                                                      subjects_dir=self.subjects_dir)
        return self._labels


class CurrentGAGroup(BaseSub):
    def __init__(self, name, main_win):

        super().__init__(name, main_win)

        # Additional Attributes
        self.save_dir = self.pr.save_dir_averages
        self.group_list = self.pr.grand_avg_dict[name]

        ################################################################################################################
        # Data-Attributes (not to be called directly)
        ################################################################################################################

        self._ga_evokeds = None
        self._ga_tfr = None
        self._ga_stcs = None
        self._ga_ltc = None
        self._ga_connect = None

        ################################################################################################################
        # Paths
        ################################################################################################################

        self.ga_evokeds_path = join(self.save_dir, 'evokeds',
                                    f'{self.name}_{self.p_preset}-ave.fif')

    ####################################################################################################################
    # Load- & Save-Methods
    ####################################################################################################################
    def load_ga_evokeds(self):
        if self._ga_evokeds is None:
            self._ga_evokeds = mne.read_evokeds(self.ga_evokeds_path)

        return self._ga_evokeds

    def save_ga_evokeds(self, ga_evokeds):
        self._ga_evokeds = ga_evokeds
        mne.evoked.write_evokeds(self.ga_evokeds_path, ga_evokeds)
        self.save_file_params(self.ga_evokeds_path)

    def load_ga_tfr(self):
        if self._ga_tfr is None:
            self._ga_tfr = {}
            for trial in self.p['event_id']:
                ga_path = join(self.pr.save_dir_averages, 'tfr',
                               f'{self.name}_{trial}_{self.p_preset}_{self.p["tfr_method"]}-tfr.h5')
                power = mne.time_frequency.read_tfrs(ga_path)[0]
                self._ga_tfr[trial] = power

        return self._ga_tfr

    def save_ga_tfr(self, ga_tfr, trial):
        ga_path = join(self.pr.save_dir_averages, 'tfr',
                       f'{self.name}_{trial}_{self.p_preset}_{self.p["tfr_method"]}-tfr.h5')
        ga_tfr.save(ga_path)
        self.save_file_params(ga_path)

    def load_ga_source_estimate(self):
        if self._ga_stcs is None:
            self._ga_stcs = {}
            for trial in self.p['event_id']:
                ga_stc_path = join(self.save_dir, 'stc', f'{self.name}_{trial}_{self.p_preset}')
                self._ga_stcs[trial] = mne.read_source_estimate(ga_stc_path)

        return self._ga_stcs

    def save_ga_source_estimate(self, ga_stcs):
        self._ga_stcs = ga_stcs
        for trial in ga_stcs:
            ga_stc_path = join(self.save_dir, 'stc', f'{self.name}_{trial}_{self.p_preset}')
            ga_stcs[trial].save(ga_stc_path)
            self.save_file_params(ga_stc_path)

    def load_ga_ltc(self):
        if self._ga_ltc is None:
            self._ga_ltc = {}
            for trial in self.p['event_id']:
                self._ga_ltc[trial] = {}
                for label in self.p['target_labels']:
                    ga_ltc_path = join(self.save_dir, 'ltc', f'{self.name}_{trial}_{self.p_preset}_{label}.npy')
                    try:
                        self._ga_ltc[trial][label] = np.load(ga_ltc_path)
                    except FileNotFoundError:
                        print(f'{ga_ltc_path} not found')

        return self._ga_ltc

    def save_ga_ltc(self, ga_ltc):
        self._ga_ltc = ga_ltc
        for trial in ga_ltc:
            for label in ga_ltc[trial]:
                ga_ltc_path = join(self.save_dir, 'ltc', f'{self.name}_{trial}_{self.p_preset}_{label}.npy')
                np.save(ga_ltc_path, ga_ltc[trial][label])
                self.save_file_params(ga_ltc_path)

    def load_ga_connect(self):
        if self._ga_connect is None:
            self._ga_connect = {}
            for trial in self.p['event_id']:
                self._ga_connect[trial] = {}
                for con_method in self.p['con_methods']:
                    con_path = join(self.save_dir, 'connect', f'{self.name}_{trial}_{self.p_preset}_{con_method}.npy')
                    try:
                        self._ga_connect[trial][con_method] = np.load(con_path)
                    except FileNotFoundError:
                        print(f'{con_path} not found')

        return self._ga_connect

    def save_ga_connect(self, ga_con):
        self._ga_connect = ga_con
        for trial in ga_con:
            for con_method in ga_con[trial]:
                con_path = join(self.save_dir, 'connect', f'{self.name}_{trial}_{self.p_preset}_{con_method}.npy')
                np.save(con_path, ga_con[trial][con_method])
                self.save_file_params(con_path)
