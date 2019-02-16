# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data - plotting functions
@author: Lau Møller Andersen
@email: lau.moller.andersen@ki.se | lau.andersen@cnru.dk
@github: https://github.com/ualsbombe/omission_frontiers.git

Edited by Martin Schulz
martin@stud.uni-heidelberg.de
"""
from __future__ import print_function

import mne
from os.path import join
import matplotlib.pyplot as plt
from mayavi import mlab
from . import io_functions as io
from . import decorators as decor
import numpy as np
from nilearn.plotting import plot_anat
from surfer import Brain

def filter_string(lowpass, highpass):

    if highpass!=None and highpass!=0:
        filter_string = '_' + str(highpass) + '-' + str(lowpass) + '_Hz'
    else:
        filter_string = '_' + str(lowpass) + '_Hz'

    return filter_string
#==============================================================================
# PLOTTING FUNCTIONS
#==============================================================================
@decor.topline
def print_info(name, save_dir, save_plots):

    info = io.read_info(name, save_dir)
    print(info)

@decor.topline
def plot_raw(name, save_dir, overwrite, bad_channels, bad_channels_dict):

    raw = io.read_raw(name, save_dir)
    raw.info['bads'] = bad_channels
    try:
        events = io.read_events(name, save_dir)
        mne.viz.plot_raw(raw=raw, n_channels=30, bad_color='red', events=events,
                        scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
                        title=name)
    except (FileNotFoundError, AttributeError):
        print('No events found')
        mne.viz.plot_raw(raw=raw, n_channels=30, bad_color='red',
                scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
                title=name)

    bad_channels_dict[name] = raw.info['bads'] # would be useful, if block worked properly

@decor.topline
def plot_filtered(name, save_dir, lowpass, highpass, bad_channels):

    raw = io.read_filtered(name, save_dir, lowpass, highpass)

    raw.info['bads'] = bad_channels
    try:
        events = io.read_events(name, save_dir)
        mne.viz.plot_raw(raw=raw, events=events, n_channels=30, bad_color='red',
                    scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
                    title=name + '_filtered')
    except FileNotFoundError:
        print('No events found')
        mne.viz.plot_raw(raw=raw, n_channels=30, bad_color='red',
            scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
            title=name + '_filtered')

@decor.topline
def plot_sensors(name, save_dir):

    info = io.read_info(name, save_dir)
    mne.viz.plot_sensors(info, kind='topomap', title=name, show_names=True, ch_groups='position')

@decor.topline
def plot_events(name, save_dir, save_plots, figures_path, event_id):

    events = io.read_events(name, save_dir)
    actual_event_id = {}
    for i in event_id:
        if event_id[i] in np.unique(events[:,2]):
            actual_event_id.update({i:event_id[i]})

    events_figure = mne.viz.plot_events(events, sfreq=1000, event_id=actual_event_id)
    plt.title(name)

    if save_plots:
        save_path = join(figures_path, 'events', name + '.jpg')
        events_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_events_diff(name, save_dir, save_plots, figures_path):
    # plot the differences between different triggers over time
    events = io.read_events(name, save_dir)
    l1 = []

    for x in range(np.size(events, axis=0)):
        if events[x,2]==2:
            if events[x+1,2]==1:
                l1.append(events[x+1,0] - events[x,0])

    figure = plt.figure()
    plt.plot(l1)
    plt.title(name + '_StartMot-LBT')


    if save_plots:
        save_path = join(figures_path, 'events', name + '_StartMot-LBT.jpg')
        figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')
@decor.topline
def plot_eog_events(name, save_dir):

    events = io.read_events(name, save_dir)
    eog_events = io.read_eog_events(name, save_dir)
    raw = io.read_raw(name, save_dir)
    raw.pick_channels(['EEG 001','EEG 002'])

    comb_events = np.append(events,eog_events,axis=0)
    eog_epochs = mne.Epochs(raw, eog_events)
    eog_epochs.plot(events=comb_events,title=name)

@decor.topline
def plot_power_spectra(name, save_dir, lowpass, highpass, subject, save_plots,
                        figures_path, bad_channels):

    raw = io.read_raw(name, save_dir)
    raw.info['bads'] = bad_channels
    picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False, eog=False, ecg=False,
                           exclude='bads')

    psd_figure = raw.plot_psd(fmax=lowpass, picks=picks, n_jobs=-1)
    plt.title(name)

    if save_plots:
        save_path = join(figures_path, 'power_spectra_raw', name + \
                             '_psdr' + filter_string(lowpass, highpass) + '.jpg')
        psd_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_power_spectra_epochs(name, save_dir, lowpass, highpass, subject, save_plots,
                        figures_path, bad_channels):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)
    raw = io.read_raw(name, save_dir)
    raw.info['bads'] = bad_channels
    picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False, eog=False, ecg=False,
                           exclude='bads')
    for trial_type in epochs.event_id:

        psd_figure = epochs[trial_type].plot_psd(fmax=lowpass, picks=picks, n_jobs=-1)
        plt.title(name)

        if save_plots:
            save_path = join(figures_path, 'power_spectra_epochs', trial_type, name + \
                                 trial_type + '_psde' + filter_string(lowpass, highpass) + '.jpg')
            psd_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_power_spectra_topo(name, save_dir, lowpass, highpass, subject, save_plots,
                        figures_path, bad_channels, layout):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)

    psd_figure = epochs.plot_psd_topomap(layout=layout, n_jobs=-1)
    plt.figure(num=name)

    if save_plots:
        save_path = join(figures_path, 'power_spectra_topo', name + \
                             '_psdtop' + filter_string(lowpass, highpass) + '.jpg')
        psd_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_ssp(name, save_dir, lowpass, highpass, subject, save_plots,
                        figures_path, bad_channels, layout, ermsub):

    if ermsub == 'None':
        print('no empty_room_data found for' + name)
        pass

    else:
        epochs = io.read_ssp_epochs(name, save_dir, lowpass, highpass)

        ssp_figure = epochs.plot_projs_topomap(layout=layout)

        if save_plots:
            save_path = join(figures_path, 'ssp', name + '_ssp' + \
                                 filter_string(lowpass, highpass) + '.jpg')
            ssp_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_ssp_eog(name, save_dir, lowpass, highpass, subject, save_plots,
                        figures_path, bad_channels, layout):
    proj_name = name + '_eog-proj.fif'
    proj_path = join(save_dir, proj_name)

    raw = io.read_raw(name, save_dir)
    eog_projs = mne.read_proj(proj_path)

    ssp_figure = mne.viz.plot_projs_topomap(eog_projs, info=raw.info)

    if save_plots:
        save_path = join(figures_path, 'ssp', name + '_ssp_eog' + \
                             filter_string(lowpass, highpass) + '.jpg')
        ssp_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_ssp_ecg(name, save_dir, lowpass, highpass, subject, save_plots,
                        figures_path, bad_channels, layout):

    proj_name = name + '_ecg-proj.fif'
    proj_path = join(save_dir, proj_name)

    raw = io.read_raw(name, save_dir)
    ecg_projs = mne.read_proj(proj_path)

    ssp_figure = mne.viz.plot_projs_topomap(ecg_projs, info=raw.info)

    if save_plots:
        save_path = join(figures_path, 'ssp', name + '_ssp_ecg' + \
                             filter_string(lowpass, highpass) + '.jpg')
        ssp_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_ica(name, save_dir, lowpass, highpass, subject, save_plots, figures_path,
             layout):

    info = io.read_info(name, save_dir)

    if 'EEG 001' in info['ch_names']:

        ica = io.read_ica(name, save_dir, lowpass, highpass)
        ica_figure = ica.plot_components(ica.exclude, title=name, layout=layout)

        if save_plots:
            save_path = join(figures_path, 'ica', name + \
                '_ica' + filter_string(lowpass, highpass) + '.jpg')
            ica_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')
    else:
        print('No EEG-Channels to read EOG/EEG from, manual ICA?')
        pass

@decor.topline
def plot_ica_sources(name, save_dir, lowpass, highpass, subject, save_plots, figures_path):

    info = io.read_info(name, save_dir)

    if 'EEG 001' in info['ch_names']:

        ica = io.read_ica(name, save_dir, lowpass, highpass)
        raw = io.read_raw(name, save_dir)

        ica_figure = mne.viz.plot_ica_sources(ica, raw, title=name)

        if save_plots:
            save_path = join(figures_path, 'ica', name + \
                '_ica_src' + filter_string(lowpass, highpass) + 'sources' + '.jpg')
            ica_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')
    else:
        print('No EEG-Channels to read EOG/EEG from, manual ICA?')
        pass

@decor.topline
def plot_epochs(name, save_dir, lowpass, highpass, subject, save_plots,
                      figures_path):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)

    for trial_type in epochs.event_id:

        epochs_image_full = mne.viz.plot_epochs(epochs[trial_type], title=name)
        plt.title(trial_type)

        if save_plots:
            save_path = join(figures_path, 'epochs', trial_type, name + '_epochs' + \
                filter_string(lowpass, highpass) +  '.jpg')

            epochs_image_full.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_epochs_image(name, save_dir, lowpass, highpass, subject, save_plots,
                      figures_path):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)
    for trial_type in epochs.event_id:

        epochs_image = mne.viz.plot_epochs_image(epochs[trial_type], title=name + '_' + trial_type)

        if save_plots:
            save_path = join(figures_path, 'epochs_image', trial_type, name + '_epochs_image' + \
            filter_string(lowpass, highpass) +  '.jpg')

            epochs_image[0].savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_epochs_topo(name, save_dir, lowpass, highpass, subject, save_plots,
                      figures_path, layout):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)
    for trial_type in epochs.event_id:

        epochs_topo = mne.viz.plot_topo_image_epochs(epochs, title=name, layout=layout)

        if save_plots:
            save_path = join(figures_path, 'epochs_topo', trial_type, name + '_epochs_topo' + \
            filter_string(lowpass, highpass) +  '.jpg')

            epochs_topo.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_evoked_topo(name, save_dir, lowpass, highpass, subject, save_plots, figures_path):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    evoked_figure = mne.viz.plot_evoked_topo(evokeds, title=name)

    if save_plots:
        save_path = join(figures_path, 'evoked_topo',
                         name + '_evk_topo' +\
                         filter_string(lowpass, highpass) + '.jpg')
        evoked_figure.savefig(save_path, dpi=1200)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_evoked_topomap(name, save_dir, lowpass, highpass, subject, save_plots, figures_path,
                        layout):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)
    for evoked in evokeds:
        evoked_figure = mne.viz.plot_evoked_topomap(evoked, times='auto',
                                                    layout=layout,
                                                    title=name +'-' + evoked.comment)

        if save_plots:
            save_path = join(figures_path, 'evoked_topomap', evoked.comment,
                             name + '_' + evoked.comment + '_evoked_topomap' + \
                             filter_string(lowpass, highpass) + '.jpg')
            evoked_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_evoked_field(name, save_dir, lowpass, highpass, subject,
                      subtomri, subjects_dir, save_plots,
                      figures_path, mne_evoked_time, n_jobs):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)
    trans = io.read_transformation(save_dir, subtomri)

    for evoked in evokeds:

        surf_maps = mne.make_field_map(evoked, trans=trans, subject=subtomri,
                                       subjects_dir=subjects_dir, meg_surf='head',
                                       n_jobs=n_jobs)
        for t in mne_evoked_time:
            mne.viz.plot_evoked_field(evoked, surf_maps, time=t)
            mlab.title(name + ' - ' + evoked.comment + filter_string(lowpass, highpass)\
                       + '-' + str(t), height=0.9)
            mlab.view(azimuth=180)

            if save_plots:
                save_path = join(figures_path, 'evoked_field', evoked.comment,
                                     name + '_' + evoked.comment + '_evoked_field' + \
                                     filter_string(lowpass, highpass) + '-' + str(t) + '.jpg')
                mlab.savefig(save_path)
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_evoked_joint(name, save_dir, lowpass, highpass, subject, save_plots,
                      layout, figures_path, ECDs):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    if name in ECDs:
        ECD = ECDs[name]
        evoked = evokeds[0]
        times = []
        for Dip in ECD:
            for i in ECD[Dip]:
                times.append(i)
        timesarr = np.array(times)
        figure = mne.viz.plot_evoked_joint(evoked, times=timesarr,
                           title=name + ' - ' + evoked.comment,
                           topomap_args={'layout':layout})

    else:
        for evoked in evokeds:
            figure = mne.viz.plot_evoked_joint(evoked, times='peaks',
                                               title=name + ' - ' + evoked.comment,
                                               topomap_args={'layout':layout})

            if save_plots:
                save_path = join(figures_path, 'evoked_joint', evoked.comment,
                                 name + '_' + evoked.comment + '_joint' + \
                                 filter_string(lowpass, highpass) + '.jpg')
                figure.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_butterfly_evokeds(name, save_dir, lowpass, highpass, subject, save_plots,
                                figures_path, time_unit, ermsub, use_calm_cov):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    for evoked in evokeds:
        figure = evoked.plot(spatial_colors=True, time_unit=time_unit,
                             window_title=name + ' - ' + evoked.comment,
                             selectable=True, gfp=True, zorder='std')

        if save_plots:
            save_path = join(figures_path, 'evoked_butterfly', evoked.comment,
                             name + '_' + evoked.comment + '_butterfly' + \
                             filter_string(lowpass, highpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_evoked_white(name, save_dir, lowpass, highpass, subject, save_plots, figures_path, ermsub, use_calm_cov):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    if use_calm_cov==True:
        noise_covariance = io.read_clm_noise_covariance(name, save_dir, lowpass, highpass)
        print('Noise Covariance from 1-min Calm in raw')
    elif ermsub=='None':
        noise_covariance = io.read_noise_covariance(name, save_dir, lowpass, highpass)
        print('Noise Covariance from Epochs')
    else:
        noise_covariance = io.read_erm_noise_covariance(name, save_dir, lowpass, highpass)
        print('Noise Covariance from Empty-Room-Data')

    for evoked in evokeds:
        figure = mne.viz.plot_evoked_white(evoked, noise_covariance)
        plt.title(name + ' - ' + evoked.comment, loc='center')

        if save_plots:
            save_path = join(figures_path, 'evoked_white', evoked.comment,
                             name + '_' + evoked.comment + '_white' + \
                             filter_string(lowpass, highpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_evoked_image(name, save_dir, lowpass, highpass, subject, save_plots, figures_path):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    for evoked in evokeds:
        figure = mne.viz.plot_evoked_image(evoked)
        plt.title(name + ' - ' + evoked.comment, loc='center')

        if save_plots:
            save_path = join(figures_path, 'evoked_image', evoked.comment,
                             name + '_' + evoked.comment + '_image' + \
                             filter_string(lowpass, highpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def animate_topomap():
    print('Not established yet')

@decor.topline
def plot_transformation(name, save_dir, subtomri, subjects_dir, save_plots,
                        figures_path):
        info = io.read_info(name, save_dir)

        trans = io.read_transformation(save_dir, subtomri)

        mne.viz.plot_alignment(info, trans, subtomri, subjects_dir,
                               surfaces=['head-dense', 'inner_skull', 'brain'],
                               show_axes=True, dig=True)

        mlab.view(45, 90, distance=0.6, focalpoint=(0., 0., 0.))

        if save_plots:
            save_path = join(figures_path, 'transformation', name + '_trans' + \
                            '.jpg')
            mlab.savefig(save_path)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_source_space(mri_subject, subjects_dir, source_space_method, save_plots, figures_path):

    source_space = io.read_source_space(mri_subject, subjects_dir, source_space_method)
    source_space.plot()
    mlab.view(-90, 7)

    if save_plots:
        save_path = join(figures_path, 'source_space', mri_subject + '_src' + '.jpg')
        mlab.savefig(save_path)
        print('figure: ' + save_path + ' has been saved')

    else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_bem(mri_subject, subjects_dir, source_space_method, figures_path,
             save_plots):

    source_space = io.read_source_space(mri_subject, subjects_dir, source_space_method)
    fig = mne.viz.plot_bem(mri_subject, subjects_dir, src=source_space)

    if save_plots:
        save_path = join(figures_path, 'bem', mri_subject + '_bem' + '.jpg')
        fig.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_noise_covariance(name, save_dir, lowpass, highpass, subject, subtomri, save_plots, figures_path, ermsub, use_calm_cov):

    if use_calm_cov==True:
        noise_covariance = io.read_clm_noise_covariance(name, save_dir, lowpass, highpass)
        print('Noise Covariance from 1-min Calm in raw')
    elif ermsub=='None':
        noise_covariance = io.read_noise_covariance(name, save_dir, lowpass, highpass)
        print('Noise Covariance from Epochs')
    else:
        noise_covariance = io.read_erm_noise_covariance(name, save_dir, lowpass, highpass)
        print('Noise Covariance from Empty-Room-Data')

    info = io.read_info(name, save_dir)

    fig_cov = noise_covariance.plot(info, show_svd=False)

    if save_plots:
        save_path = join(figures_path, 'noise_covariance', name + \
                    filter_string(lowpass, highpass) + '.jpg')
        fig_cov[0].savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_source_estimates(name, save_dir, lowpass, highpass, subtomri, subjects_dir, subject,
                          method, mne_evoked_time,
                          save_plots, figures_path):
#changed for only one trial type
    stcs = io.read_source_estimates(name, save_dir,lowpass, highpass, method)
    for trial_type in stcs:
        for t in mne_evoked_time:
            stc = stcs[trial_type]
            mlab.figure(figure=name + '_' + trial_type + \
                        filter_string(lowpass, highpass) + '-' + str(t), size=(1000, 800))
            mne.viz.plot_source_estimates(stc=stc,subject=subtomri, surface='inflated',
                                        subjects_dir=subjects_dir, figure=mlab.gcf(),
                                        time_viewer=False, hemi='both',
                                        views='med', initial_time=t)
            mlab.title(name + '_' + trial_type + \
                       filter_string(lowpass, highpass) + '-' + str(t),
                       figure = mlab.gcf(), height=0.9)

            if save_plots:
                save_path = join(figures_path, 'stcs', trial_type,
                                 name + '_' + trial_type + \
                                 filter_string(lowpass, highpass) + str(t) + 'sec.jpg')
                mlab.savefig(save_path, figure=mlab.gcf())
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_vector_source_estimates(name, save_dir, lowpass, highpass, subtomri, subjects_dir, subject,
                          method, mne_evoked_time,
                          save_plots, figures_path):
#changed for only one trial type
    stcs = io.read_vector_source_estimates(name, save_dir,lowpass, highpass, method)
    for trial_type in stcs:
        stc = stcs[trial_type]
        mlab.figure(figure=name + '_' + trial_type + '_vector',size=(800, 800))
        mne.viz.plot_vector_source_estimates(stc=stc,subject=subtomri,
                                    subjects_dir=subjects_dir, figure=mlab.gcf(),
                                    time_viewer=True, hemi='both',
                                    views='med', initial_time=mne_evoked_time)

        if save_plots:
            save_path = join(figures_path, 'vec_stcs', trial_type,
                             name + '_' + trial_type +\
                             filter_string(lowpass, highpass) + str(mne_evoked_time) + 'sec.jpg')
            mlab.savefig(save_path, figure=mlab.gcf())
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_animated_stc(name, save_dir, lowpass, highpass, subtomri, subjects_dir, subject,
                          method, mne_evoked_time, stc_animation, tmin, tmax,
                          save_plots, figures_path):

    stcs = io.read_source_estimates(name, save_dir,lowpass, highpass, method)

    for trial_type in stcs:
        stc = stcs[trial_type]
        save_path = join(figures_path, 'stcs_movie', trial_type, name + '_' + trial_type +\
						      filter_string(lowpass, highpass) + '.mp4')
        brain = mne.viz.plot_source_estimates(stc=stc,subject=subtomri, surface='inflated',
                                    subjects_dir=subjects_dir,
                                    hemi='both', views=['lat','med'],
                                    title=name + '_' + trial_type + '_movie')

        print('Saving Video')
        brain.save_movie(save_path, time_dilation=20,
                         tmin=stc_animation[0], tmax=stc_animation[1])
        mlab.close()
        """
        @mlab.animate(delay=1000)
        def anim():
            while 1:
                for t in range(0, 10):
                    brain.set_data_time_index(t)
                    yield


        anim()


        @mlab.animate
        def anim():
            for x in brain._iter_time()

        anim()
        mlab.show()


        @mlab.animate
        def anim():
            for i in range(stc_animation[0], stc_animation[1]):
                fig.mlab_source.set_data_time_index(i)
                yield
             int((tmax-tmin)*1000)
        anim()
        mlab.show()
        """


@decor.topline
def plot_snr(name, save_dir, lowpass, highpass, save_plots, figures_path):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)

    inv = io.read_inverse_operator(name, save_dir, lowpass, highpass)

    for evoked in evokeds:

        figure = mne.viz.plot_snr_estimate(evoked, inv)
        plt.title(name + ' - ' + evoked.comment, loc='center')

        if save_plots:
            save_path = join(figures_path, 'snr', evoked.comment,
                             name + '_' + evoked.comment + '_snr' + \
                             filter_string(lowpass, highpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_labels(subtomri, subjects_dir):

    brain = Brain(subtomri, hemi='both', surf='smoothwm')

    labels = mne.read_labels_from_annot(subtomri)

    for label in labels:
        brain.add_label(label)

@decor.topline
def label_time_course_old(name, save_dir, lowpass, highpass, method, source_space_method, subtomri,
                      subjects_dir, target_labels, figures_path, save_plots):

    labels = mne.read_labels_from_annot(subtomri, subjects_dir=subjects_dir)
    """labels = []
    for x in target_labels:
        label_path = join(subjects_dir, 'fsaverage', 'label', x + '.label')
        label = mne.read_label(label_path, subject='fsaverage')
        labels.append(label)"""
    stcs = io.read_source_estimates(name, save_dir,lowpass, highpass, method)
    src = io.read_source_space(subtomri, subjects_dir, source_space_method)
    for trial_type in stcs:
        stc = stcs[trial_type]
        for label in labels:
            if label.name in target_labels:

                stc_label = stc.in_label(label)
                """ check the functions here, andre got his bipolar plot
                stc_mean = stc.extract_label_time_course(label, src, mode='mean')
                """
                plt.figure()
                plt.plot(1e3 * stc_label.times, stc_label.data.T, 'k', linewidth=0.5)
                #plt.plot(1e3 * stc_label.times, stc_mean.T, 'r', linewidth=3)
                plt.xlabel('Time (ms)')
                plt.ylabel('Source amplitude')
                plt.title('{} in : {}'.format(trial_type, label.name))
                plt.show()
                if save_plots:
                    save_path = join(figures_path, 'label_time_course', trial_type, name + \
                                         filter_string(lowpass, highpass) + '_' + \
                                         trial_type + '_' + label.name + '.jpg')
                    plt.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')
                    """
                    t_min = 0.095
                    t_max = 0.105
                    stc_mean = stc.copy().crop(t_min, t_max).mean()
                    stc_mean_label = stc_mean.in_label(label)
                    data = np.abs(stc_mean_label.data)
                    stc_mean_label.data[data < 0.6 * np.max(data)] = 0.

                    func_labels, _ = mne.stc_to_label(stc_mean_label, src=src, smooth=True,
                                     subjects_dir=subjects_dir, connected=True,
                                     verbose='error')
                    func_label = func_labels[0]
                    stc_func_label = stc.in_label(func_label)
                    func_mean = stc.extract_label_time_course(func_label, src, mode='mean')[0]

                    plt.figure()

                    plt.plot(1e3 * stc_label.times, stc_mean, 'k',
                             label='Anatomical %s' % label)

                    plt.plot(1e3 * stc_func_label.times, func_mean, 'b',
                             label='Functional %s' % label)
                    plt.legend()
                    plt.show()
                    """

@decor.topline
def label_time_course_avg(morphed_data_all, save_dir_averages, lowpass, highpass, method,
                          which_file, subjects_dir, source_space_method,
                          target_labels, save_plots, event_id_list, figures_path):

    """labels = mne.read_labels_from_annot('fsaverage', subjects_dir=subjects_dir)"""
    labels = []
    for x in target_labels:
        label_path = join(subjects_dir, 'fsaverage', 'label', x + '.label')
        label = mne.read_label(label_path, subject='fsaverage')
        labels.append(label)
    src = io.read_source_space('fsaverage', subjects_dir, source_space_method)

    for trial_type in morphed_data_all:
        if trial_type in event_id_list:
            stc_path = save_dir_averages  + \
                    trial_type + filter_string(lowpass, highpass) + '_morphed_data_' + method + \
                    '_' + which_file
            stc = mne.source_estimate.read_source_estimate(stc_path)
            for label in labels:
                """if label.name in target_labels:"""
                stc_label = stc.in_label(label)
                stc_mean = stc.extract_label_time_course(label, src, mode='mean')

                plt.figure()
                plt.plot(1e3 * stc_label.times, stc_label.data.T, 'k', linewidth=0.5)
                plt.plot(1e3 * stc_label.times, stc_mean.T, 'r', linewidth=3)
                plt.xlabel('Time (ms)')
                plt.ylabel('Source amplitude (10pT)')
                plt.ylim(ymax=5e-11)
                plt.title(label.name)
                plt.show()
                if save_plots:
                    save_path = join(figures_path, 'grand_averages', 'source_space',
                                     trial_type + '_' + \
                                     label.name + '_' + which_file + '_lim' + '.jpg')
                    plt.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def label_time_course(name, save_dir, lowpass, highpass, subtomri, target_labels,
                      save_plots, figures_path):

    snr = 3.0
    lambda2 = 1.0 / snr ** 2
    method = "dSPM"

    evoked = io.read_evokeds(name, save_dir, lowpass, highpass)[0]

    labels = mne.read_labels_from_annot(subtomri)

    for label in labels:
        if label.name in target_labels:
            l = label


            inv_op = io.read_inverse_operator(name, save_dir, lowpass, highpass)

            src = inv_op['src']

            # pick_ori has to be normal to plot bipolar time course
            stc = mne.minimum_norm.apply_inverse(evoked, inv_op, lambda2, method,
                                                 pick_ori='normal')

            stc_label = stc.in_label(l)
            mean = stc.extract_label_time_course(l, src, mode='mean')
            mean_flip = stc.extract_label_time_course(l, src, mode='mean_flip')
            pca = stc.extract_label_time_course(l, src, mode='pca_flip')

            plt.figure()
            plt.plot(1e3 * stc_label.times, stc_label.data.T, 'k', linewidth=0.5)
            h0, = plt.plot(1e3 * stc_label.times, mean.T, 'r', linewidth=3)
            h1, = plt.plot(1e3 * stc_label.times, mean_flip.T, 'g', linewidth=3)
            h2, = plt.plot(1e3 * stc_label.times, pca.T, 'b', linewidth=3)
            plt.legend([h0, h1, h2], ['mean', 'mean flip', 'PCA flip'])
            plt.xlabel('Time (ms)')
            plt.ylabel('Source amplitude')
            plt.title(f'Activations in Label :{l}-{evoked.comment}')
            plt.show()

            if save_plots:
                save_path = join(figures_path, 'label_time_course', evoked.comment, name + \
                                     filter_string(lowpass, highpass) + '_' + \
                                     evoked.comment + '_' + l.name + '.jpg')
                plt.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_grand_average_evokeds(name, lowpass, highpass, save_dir_averages,
                               evoked_data_all, event_id_list,
                               save_plots, figures_path, which_file):

    grand_averages = []
    order = ['pinprick', 'WU_First', 'WU_Last']

    for evoked_type in order:
        if evoked_type in event_id_list:
            filename = join(save_dir_averages,
                            evoked_type + filter_string(lowpass, highpass) + \
                            '_' + which_file + '_grand_average-ave.fif')
            evoked = mne.read_evokeds(filename)[0]
            evoked.comment = evoked_type
            grand_averages.append(evoked)

    # sort evokeds
    plot_evokeds = []

    for evoked_type in order:
        if evoked_type in event_id_list:
            for evoked in grand_averages:
                if evoked.comment == evoked_type:
                    plot_evokeds.append(evoked)

    plt.close('all')

    evoked_figure = mne.viz.plot_evoked_topo(plot_evokeds)
    evoked_figure.comment = 'all_evokeds_'

    figures = [evoked_figure]

    if save_plots:
        for figure in figures:
            save_path = join(figures_path, 'grand_averages', 'sensor_space',
                             figure.comment + '_' + which_file + \
                             filter_string(lowpass, highpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_grand_averages_butterfly_evokeds(name, lowpass, highpass, save_dir_averages, event_id_list,
                                          save_plots, figures_path, which_file):

    grand_averages = []
    order = ['pinprick', 'WU_First', 'WU_Last']

    for evoked_type in order:
        if evoked_type in event_id_list:
            filename = join(save_dir_averages,
                            evoked_type + filter_string(lowpass, highpass) + \
                            '_' + which_file + '_grand_average-ave.fif')
            evoked = mne.read_evokeds(filename)[0]
            evoked.comment = evoked_type
            grand_averages.append(evoked)

    for grand_average in grand_averages:
        figure = grand_average.plot(spatial_colors=True, selectable=True,
                                    gfp=True, zorder='std', window_title=grand_average.comment)

        if save_plots:
            save_path = join(figures_path, 'grand_averages', 'sensor_space',
                             'butterfly_' + grand_average.comment + '_' + which_file + \
                             filter_string(lowpass, highpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_grand_averages_source_estimates(name, save_dir_averages, lowpass, highpass,
                          subjects_dir, method, mne_evoked_time, event_id_list,
                          save_plots, figures_path, which_file):

    stcs = dict()
    order = ['pinprick', 'WU_First', 'WU_Last']

    for stc_type in order:
        if stc_type in event_id_list:
            filename = join(save_dir_averages,
                            stc_type + filter_string(lowpass, highpass) + \
                            '_morphed_data_' + method + '_' + which_file)
            stc = mne.read_source_estimate(filename)
            stc.comment = stc_type
            stcs[stc_type] = stc

    brains = dict()
    for trial_type in list(stcs.keys()):
        brains[trial_type] = None

    mlab.close(None, True)

    for brains_figure_counter, stc in enumerate(stcs):
        for t in mne_evoked_time:
            mlab.figure(figure=name + \
                        filter_string(lowpass, highpass) + '-' + str(t), size=(1000, 800))
            brains[stc] = stcs[stc].plot(subject='fsaverage',
                                        subjects_dir=subjects_dir,
                                        time_viewer=False, hemi='both',
                                        figure=mlab.gcf(),
                                        views='med')
            time = t
            brains[stc].set_time(time)
            message = list(stcs.keys())[brains_figure_counter]
            brains[stc].add_text(0.01, 0.9, message,
                     str(brains_figure_counter), font_size=14)

            if save_plots:
                save_path = join(figures_path, 'grand_averages', 'source_space',
                                 stc + '_' + which_file + '_' + \
                                 filter_string(lowpass, highpass) + '_' + str(time * 1e3) + \
                                     '_msec.jpg')
                brains[stc].save_single_image(save_path)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_grand_averages_source_estimates_cluster_masked(name,
                          save_dir_averages, lowpass, highpass,
                          subjects_dir, method, time_window,
                          save_plots, figures_path,
                          independent_variable_1, independent_variable_2,
                          mne_evoked_time, p_threshold):

    if mne_evoked_time < time_window[0] or mne_evoked_time > time_window[1]:
        raise ValueError('"mne_evoked_time" must be within "time_window"')
    n_subjects = 20 ## should be corrected
    independent_variables = [independent_variable_1, independent_variable_2]
    stcs = dict()
    for stc_type in independent_variables:
        filename = join(save_dir_averages,
                        stc_type + filter_string(lowpass, highpass) + \
                        '_morphed_data_' + method)
        stc = mne.read_source_estimate(filename)
        stc.comment = stc_type
        stcs[stc_type] = stc

    difference_stc = stcs[independent_variable_1] - stcs[independent_variable_2]

    ## load clusters

    cluster_dict = io.read_clusters(save_dir_averages, independent_variable_1,
                  independent_variable_2, time_window, lowpass)
    cluster_p_values = cluster_dict['cluster_p_values']
    clusters = cluster_dict['clusters']
    T_obs = cluster_dict['T_obs']
    n_sources = T_obs.shape[0]

    cluster_p_threshold = 0.05
    indices = np.where(cluster_p_values <= cluster_p_threshold)[0]
    sig_clusters = []
    for index in indices:
        sig_clusters.append(clusters[index])

    cluster_T = np.zeros(n_sources)
    for sig_cluster in sig_clusters:
        # start = sig_cluster[0].start
        # stop = sig_cluster[0].stop
        sig_indices = np.unique(np.where(sig_cluster == 1)[0])
        cluster_T[sig_indices] = 1

    t_mask = np.copy(T_obs)
    t_mask[cluster_T == 0] = 0
    cutoff = stats.t.ppf(1 - p_threshold / 2, df=n_subjects - 1)

    time_index = int(mne_evoked_time * 1e3 + 200)
    time_window_times = np.linspace(time_window[0], time_window[1],
                        int((time_window[1] - time_window[0]) * 1e3) + 2)
    time_index_mask = np.where(time_window_times == mne_evoked_time)[0]
    difference_stc._data[:, time_index] = np.reshape(t_mask[:, time_index_mask], n_sources)

    mlab.close(None, True)
    clim = dict(kind='value', lims=[cutoff, 2*cutoff, 4*cutoff])

    mlab.figure(figure=0,
                        size=(800, 800))
    brain = difference_stc.plot(subject='fsaverage',
                                subjects_dir=subjects_dir,
                                time_viewer=False, hemi='both',
                                figure=0,
                                clim=clim,
                                views='dorsal')
    time = mne_evoked_time
    brain.set_time(time)
    message = independent_variable_1 + ' vs ' + independent_variable_2
    brain.add_text(0.01, 0.9, message,
                str(0), font_size=14)

    if save_plots:
        save_path = join(figures_path, 'grand_averages',
                            'source_space/statistics',
                            message + '_' + name + \
                            filter_string(lowpass, highpass) + '.jpg' + '_' + str(time * 1e3) + \
                                '_msec.jpg')
        brain.save_single_image(save_path)
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def close_all():

    plt.close('all')
    mlab.close(all=True)
