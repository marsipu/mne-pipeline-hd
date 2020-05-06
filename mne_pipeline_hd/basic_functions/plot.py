# -*- coding: utf-8 -*-
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
from os.path import join

import matplotlib.pyplot as plt
import mne
import numpy as np
from mayavi import mlab
from scipy import stats
from surfer import Brain

from mne_pipeline_hd.basic_functions import loading, operations as op
from mne_pipeline_hd.pipeline_functions import decorators as decor


# ==============================================================================
# PLOTTING FUNCTIONS
# ==============================================================================
@decor.topline
def print_info(name, save_dir):
    info = loading.read_info(name, save_dir)
    print(info)


# Todo: Plot Raw with block to mark bads on the fly, test on all OS (hangs on Spyder?!)
@decor.topline
def plot_raw(name, save_dir, bad_channels):
    raw = loading.read_raw(name, save_dir)
    raw.info['bads'] = bad_channels
    print(f"Pre-Bads:, {raw.info['bads']}")
    try:
        events = loading.read_events(name, save_dir)
        mne.viz.plot_raw(raw=raw, n_channels=30, bad_color='red', events=events,
                         scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
                         title=name)
    except (FileNotFoundError, AttributeError):
        mne.viz.plot_raw(raw=raw, n_channels=30, bad_color='red',
                         scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
                         title=name)


@decor.topline
def plot_filtered(name, save_dir, highpass, lowpass, bad_channels):
    raw = loading.read_filtered(name, save_dir, highpass, lowpass)

    raw.info['bads'] = bad_channels
    try:
        events = loading.read_events(name, save_dir)
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
    info = loading.read_info(name, save_dir)
    mne.viz.plot_sensors(info, kind='topomap', title=name, show_names=True, ch_groups='position')


@decor.topline
def plot_events(name, save_dir, save_plots, figures_path, event_id):
    events = loading.read_events(name, save_dir)
    actual_event_id = {}
    for i in event_id:
        if event_id[i] in np.unique(events[:, 2]):
            actual_event_id.update({i: event_id[i]})

    events_figure = mne.viz.plot_events(events, sfreq=1000, event_id=actual_event_id)
    plt.title(name)

    if save_plots:
        save_path = join(figures_path, 'events', name + '.jpg')
        events_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_eog_events(name, save_dir, eog_channel):
    events = loading.read_events(name, save_dir)
    eog_events = loading.read_eog_events(name, save_dir)
    raw = loading.read_raw(name, save_dir)
    raw.pick_channels([eog_channel])

    comb_events = np.append(events, eog_events, axis=0)
    eog_epochs = mne.Epochs(raw, eog_events)
    eog_epochs.plot(events=comb_events, title=name)


@decor.topline
def plot_power_spectra(name, save_dir, highpass, lowpass, save_plots,
                       figures_path, bad_channels):
    raw = loading.read_raw(name, save_dir)
    raw.info['bads'] = bad_channels
    picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False, eog=False, ecg=False,
                           exclude='bads')

    psd_figure = raw.plot_psd(fmax=lowpass, picks=picks, n_jobs=1)
    plt.title(name)

    if save_plots:
        save_path = join(figures_path, 'power_spectra_raw', name +
                         '_psdr' + op.filter_string(highpass, lowpass) + '.jpg')
        psd_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_power_spectra_epochs(name, save_dir, highpass, lowpass, save_plots,
                              figures_path):
    epochs = loading.read_epochs(name, save_dir, highpass, lowpass)

    for trial_type in epochs.event_id:

        psd_figure = epochs[trial_type].plot_psd(fmax=lowpass, n_jobs=-1)
        plt.title(name + '-' + trial_type)

        if save_plots:
            save_path = join(figures_path, 'power_spectra_epochs', trial_type, name + '_' +
                             trial_type + '_psde' + op.filter_string(highpass, lowpass) + '.jpg')
            psd_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_power_spectra_topo(name, save_dir, highpass, lowpass, save_plots,
                            figures_path):
    epochs = loading.read_epochs(name, save_dir, highpass, lowpass)
    for trial_type in epochs.event_id:
        psd_figure = epochs[trial_type].plot_psd_topomap(n_jobs=-1)
        plt.title(name + '-' + trial_type)

        if save_plots:
            save_path = join(figures_path, 'power_spectra_topo', trial_type, name + '_' +
                             trial_type + '_psdtop' + op.filter_string(highpass, lowpass) + '.jpg')
            psd_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_tfr(name, save_dir, highpass, lowpass, t_epoch, baseline,
             tfr_method, save_plots, figures_path):
    powers = loading.read_tfr_power(name, save_dir, highpass, lowpass, tfr_method)
    itcs = loading.read_tfr_itc(name, save_dir, highpass, lowpass, tfr_method)

    for power in powers:
        fig1 = power.plot(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                          tmax=t_epoch[1], title=f'{name}-{power.comment}')
        fig2 = power.plot_topo(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                               tmax=t_epoch[1], title=f'{name}-{power.comment}')
        fig3 = power.plot_joint(baseline=baseline, mode='mean', tmin=t_epoch[0],
                                tmax=t_epoch[1], title=f'{name}-{power.comment}')

        fig4, axis = plt.subplots(1, 5, figsize=(15, 2))
        power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=5, fmax=8,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[0],
                           title='Theta 5-8 Hz', show=False)
        power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=8, fmax=12,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[1],
                           title='Alpha 8-12 Hz', show=False)
        power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=13, fmax=30,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[2],
                           title='Beta 13-30 Hz', show=False)
        power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=31, fmax=60,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[3],
                           title='Low Gamma 30-60 Hz', show=False)
        power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=61, fmax=100,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[4],
                           title='High Gamma 60-100 Hz', show=False)
        mne.viz.tight_layout()
        plt.title(f'{name}-{power.comment}')
        plt.show()

        if save_plots:
            save_path1 = join(figures_path, 'tf_sensor_space/plot',
                              power.comment, name + '_tf' +
                              op.filter_string(highpass, lowpass) +
                              '-' + power.comment + '.jpg')
            fig1.savefig(save_path1, dpi=600)
            print('figure: ' + save_path1 + ' has been saved')
            save_path2 = join(figures_path, 'tf_sensor_space/topo',
                              power.comment, name + '_tf_topo' +
                              op.filter_string(highpass, lowpass) +
                              '-' + power.comment + '.jpg')
            fig2.savefig(save_path2, dpi=600)
            print('figure: ' + save_path2 + ' has been saved')
            save_path3 = join(figures_path, 'tf_sensor_space/joint',
                              power.comment, name + '_tf_joint' +
                              op.filter_string(highpass, lowpass) +
                              '-' + power.comment + '.jpg')
            fig3.savefig(save_path3, dpi=600)
            print('figure: ' + save_path3 + ' has been saved')
            save_path4 = join(figures_path, 'tf_sensor_space/oscs',
                              power.comment, name + '_tf_oscs' +
                              op.filter_string(highpass, lowpass) +
                              '-' + power.comment + '.jpg')
            fig4.savefig(save_path4, dpi=600)
            print('figure: ' + save_path4 + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

    for itc in itcs:
        fig5 = itc.plot_topo(title=f'{name}-{itc.comment}-itc',
                             vmin=0., vmax=1., cmap='Reds')

        if save_plots:
            save_path5 = join(figures_path, 'tf_sensor_space/itc',
                              power.comment, name + '_tf_itc' +
                              op.filter_string(highpass, lowpass) +
                              '-' + itc.comment + '.jpg')
            fig5.savefig(save_path5, dpi=600)
            print('figure: ' + save_path5 + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_epochs(name, save_dir, highpass, lowpass, save_plots,
                figures_path):
    epochs = loading.read_epochs(name, save_dir, highpass, lowpass)

    for trial_type in epochs.event_id:

        epochs_image_full = mne.viz.plot_epochs(epochs[trial_type], title=name)
        plt.title(trial_type)

        if save_plots:
            save_path = join(figures_path, 'epochs', trial_type, name + '_epochs' +
                             op.filter_string(highpass, lowpass) + '.jpg')

            epochs_image_full.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_epochs_image(name, save_dir, highpass, lowpass, save_plots,
                      figures_path):
    epochs = loading.read_epochs(name, save_dir, highpass, lowpass)
    for trial_type in epochs.event_id:

        epochs_image = mne.viz.plot_epochs_image(epochs[trial_type], title=name + '_' + trial_type)

        if save_plots:
            save_path = join(figures_path, 'epochs_image', trial_type, name + '_epochs_image' +
                             op.filter_string(highpass, lowpass) + '.jpg')

            epochs_image[0].savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_epochs_topo(name, save_dir, highpass, lowpass, save_plots,
                     figures_path):
    epochs = loading.read_epochs(name, save_dir, highpass, lowpass)
    for trial_type in epochs.event_id:

        epochs_topo = mne.viz.plot_topo_image_epochs(epochs, title=name)

        if save_plots:
            save_path = join(figures_path, 'epochs_topo', trial_type, name + '_epochs_topo' +
                             op.filter_string(highpass, lowpass) + '.jpg')

            epochs_topo.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_epochs_drop_log(name, save_dir, highpass, lowpass, save_plots,
                         figures_path):
    epochs = loading.read_epochs(name, save_dir, highpass, lowpass)

    fig = epochs.plot_drop_log(subject=name)

    if save_plots:
        save_path = join(figures_path, 'epochs_drop_log', name + '_drop_log' +
                         op.filter_string(highpass, lowpass) + '.jpg')

        fig.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_evoked_topo(name, save_dir, highpass, lowpass, save_plots, figures_path):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)

    evoked_figure = mne.viz.plot_evoked_topo(evokeds, title=name)

    if save_plots:
        save_path = join(figures_path, 'evoked_topo',
                         name + '_evk_topo' +
                         op.filter_string(highpass, lowpass) + '.jpg')
        evoked_figure.savefig(save_path, dpi=1200)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_evoked_topomap(name, save_dir, highpass, lowpass, save_plots, figures_path):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)
    for evoked in evokeds:
        evoked_figure = mne.viz.plot_evoked_topomap(evoked, times='auto',
                                                    title=name + '-' + evoked.comment)

        if save_plots:
            save_path = join(figures_path, 'evoked_topomap', evoked.comment,
                             name + '_' + evoked.comment + '_evoked_topomap' +
                             op.filter_string(highpass, lowpass) + '.jpg')
            evoked_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_evoked_joint(name, save_dir, highpass, lowpass, save_plots,
                      figures_path):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)

    for evoked in evokeds:
        figure = mne.viz.plot_evoked_joint(evoked, times='peaks',
                                           title=name + ' - ' + evoked.comment)

        if save_plots:
            save_path = join(figures_path, 'evoked_joint', evoked.comment,
                             name + '_' + evoked.comment + '_joint' +
                             op.filter_string(highpass, lowpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_evoked_butterfly(name, save_dir, highpass, lowpass, save_plots,
                          figures_path):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)

    for evoked in evokeds:
        figure = evoked.plot(spatial_colors=True,
                             window_title=name + ' - ' + evoked.comment,
                             selectable=True, gfp=True, zorder='std')

        if save_plots:
            save_path = join(figures_path, 'evoked_butterfly', evoked.comment,
                             name + '_' + evoked.comment + '_butterfly' +
                             op.filter_string(highpass, lowpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_evoked_white(name, save_dir, highpass, lowpass, save_plots, figures_path, erm_noise_cov, ermsub,
                      calm_noise_cov):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)

    noise_covariance = loading.read_noise_covariance(name, save_dir, highpass, lowpass,
                                                     erm_noise_cov, ermsub, calm_noise_cov)

    for evoked in evokeds:
        # Check, if evokeds and noise covariance got the same channels
        channels = set(evoked.ch_names) & set(noise_covariance.ch_names)
        evoked.pick_channels(channels)

        figure = mne.viz.plot_evoked_white(evoked, noise_covariance)
        plt.title(name + ' - ' + evoked.comment, loc='center')

        if save_plots:
            save_path = join(figures_path, 'evoked_white', evoked.comment,
                             name + '_' + evoked.comment + '_white' +
                             op.filter_string(highpass, lowpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_evoked_image(name, save_dir, highpass, lowpass, save_plots, figures_path):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)

    for evoked in evokeds:
        figure = mne.viz.plot_evoked_image(evoked)
        plt.title(name + ' - ' + evoked.comment, loc='center')

        if save_plots:
            save_path = join(figures_path, 'evoked_image', evoked.comment,
                             name + '_' + evoked.comment + '_image' +
                             op.filter_string(highpass, lowpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')



@decor.topline
def plot_gfp(name, save_dir, highpass, lowpass, save_plots, figures_path):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)
    for evoked in evokeds:
        gfp = op.calculate_gfp(evoked)
        t = evoked.times
        trial_type = evoked.comment
        plt.figure()
        plt.plot(t, gfp)
        plt.title(f'GFP of {name}-{trial_type}')
        plt.show()
        if save_plots:
            save_path = join(figures_path, 'gfp', trial_type,
                             f'{name}-{trial_type}_gfp{op.filter_string(highpass, lowpass)}.jpg')
            plt.savefig(save_path, dpi=600)
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_transformation(name, save_dir, subtomri, subjects_dir, save_plots,
                        figures_path):
    info = loading.read_info(name, save_dir)

    trans = loading.read_transformation(save_dir, subtomri)

    mne.viz.plot_alignment(info, trans, subtomri, subjects_dir,
                           surfaces=['head-dense', 'inner_skull', 'brain'],
                           show_axes=True, dig=True)

    mlab.view(45, 90, distance=0.6, focalpoint=(0., 0., 0.025))

    if save_plots:
        save_path = join(figures_path, 'transformation', name + '_trans' +
                         '.jpg')
        mlab.savefig(save_path)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_source_space(mri_subject, subjects_dir, source_space_method, save_plots, figures_path):
    source_space = loading.read_source_space(mri_subject, subjects_dir, source_space_method)
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
    source_space = loading.read_source_space(mri_subject, subjects_dir, source_space_method)
    vol_src = loading.read_vol_source_space(mri_subject, subjects_dir)
    fig1 = mne.viz.plot_bem(mri_subject, subjects_dir, src=source_space)
    fig2 = mne.viz.plot_bem(mri_subject, subjects_dir, src=vol_src)
    if save_plots:
        save_path1 = join(figures_path, 'bem', mri_subject + '_bem' + '.jpg')
        fig1.savefig(save_path1, dpi=600)
        print('figure: ' + save_path1 + ' has been saved')
        save_path2 = join(figures_path, 'bem', mri_subject + 'vol_bem' + '.jpg')
        fig2.savefig(save_path2, dpi=600)
        print('figure: ' + save_path2 + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_sensitivity_maps(name, save_dir, subjects_dir, ch_types, save_plots, figures_path):
    fwd = loading.read_forward(name, save_dir)

    for ch_type in ch_types:
        sens_map = mne.sensitivity_map(fwd, ch_type=ch_type, mode='fixed')
        brain = sens_map.plot(title=f'{ch_type}-Sensitivity for {name}', subjects_dir=subjects_dir,
                              clim=dict(lims=[0, 50, 100]))

        if save_plots:
            save_path = join(figures_path, 'sensitivity_maps', f'{name}_{ch_type}_sens-map.jpg')
            brain.save_image(save_path)


@decor.topline
def plot_noise_covariance(name, save_dir, highpass, lowpass, save_plots, figures_path, erm_noise_cov, ermsub,
                          calm_noise_cov):
    noise_covariance = loading.read_noise_covariance(name, save_dir, highpass, lowpass,
                                                     erm_noise_cov, ermsub, calm_noise_cov)

    info = loading.read_info(name, save_dir)

    fig_cov = noise_covariance.plot(info, show_svd=False)

    if save_plots:
        save_path = join(figures_path, 'noise_covariance', name +
                         op.filter_string(highpass, lowpass) + '.jpg')
        fig_cov[0].savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')


# Todo: Bug with interactive-mode
@decor.topline
def plot_stc(name, save_dir, highpass, lowpass, subtomri, subjects_dir,
             inverse_method, mne_evoked_time, event_id, stc_interactive,
             save_plots, figures_path):
    stcs = loading.read_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                         event_id)
    for trial_type in stcs:
        stc = stcs[trial_type]
        if stc_interactive:
            brain = stc.plot(subject=subtomri, surface='inflated', subjects_dir=subjects_dir,
                             time_viewer=True, hemi='split', views='lat',
                             title=f'{name}-{trial_type}', size=(1600, 800))
            brain.title = f'{name}-{trial_type}'
        else:
            for idx, t in enumerate(mne_evoked_time):
                figures_list = [mlab.figure(figure=idx * 2, size=(800, 800)),
                                mlab.figure(figure=idx * 2 + 1, size=(800, 800))]

                brain = stc.plot(subject=subtomri, surface='inflated', subjects_dir=subjects_dir,
                                 time_viewer=False, hemi='split', views='lat', initial_time=t,
                                 title=f'{name}-{trial_type}', size=(1600, 800), figure=figures_list)
                brain.title = f'{name}-{trial_type}'

                if save_plots:
                    save_path = join(figures_path, 'stcs', trial_type,
                                     name + '_' + trial_type +
                                     op.filter_string(highpass, lowpass) + '_' + str(idx) + '.jpg')
                    brain.save_image(save_path)
                    print('figure: ' + save_path + ' has been saved')

                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

# Todo: Figure-Conflict when running consecutively with other mayavi-plots
@decor.topline
def plot_normal_stc(name, save_dir, highpass, lowpass, subtomri, subjects_dir,
                    inverse_method, mne_evoked_time, event_id, stc_interactive,
                    save_plots, figures_path):
    stcs = loading.read_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                                event_id)
    for trial_type in stcs:
        for idx, t in enumerate(mne_evoked_time):
            stc = stcs[trial_type]
            figures_list = [mlab.figure(figure=idx * 2, size=(800, 800)),
                            mlab.figure(figure=idx * 2 + 1, size=(800, 800))]
            if stc_interactive:
                brain = stc.plot(subject=subtomri, surface='inflated', subjects_dir=subjects_dir,
                                 time_viewer=True, hemi='split', views='lat', initial_time=t,
                                 title=f'{name}-{trial_type}_normal', size=(1600, 800), figure=figures_list)
            else:
                brain = stc.plot(subject=subtomri, surface='inflated', subjects_dir=subjects_dir,
                                 time_viewer=False, hemi='split', views='lat', initial_time=t,
                                 title=f'{name}-{trial_type}_normal', size=(1600, 800), figure=figures_list)
            brain.title = f'{name}-{trial_type}_normal'
            if save_plots:
                save_path = join(figures_path, 'stcs', trial_type,
                                 name + '_' + trial_type +
                                 op.filter_string(highpass, lowpass) + '_normal_' + str(idx) + '.jpg')
                brain.save_image(save_path)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_vector_stc(name, save_dir, highpass, lowpass, subtomri, subjects_dir,
                    inverse_method, mne_evoked_time, event_id, stc_interactive,
                    save_plots, figures_path):
    stcs = loading.read_vector_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                                event_id)
    for trial_type in stcs:
        for idx, t in enumerate(mne_evoked_time):
            stc = stcs[trial_type]
            figures_list = [mlab.figure(figure=idx * 2, size=(800, 800)),
                            mlab.figure(figure=idx * 2 + 1, size=(800, 800))]
            if stc_interactive:
                brain = stc.plot(subject=subtomri, subjects_dir=subjects_dir,
                                 time_viewer=True, hemi='split', views='lat', initial_time=t,
                                 size=(1600, 800), figure=figures_list)
            else:
                brain = stc.plot(subject=subtomri, subjects_dir=subjects_dir,
                                 time_viewer=False, hemi='split', views='lat', initial_time=t,
                                 size=(1600, 800), figure=figures_list)
            brain.title = f'{name}-{trial_type}_vector'
            if save_plots:
                save_path = join(figures_path, 'vec_stcs', trial_type,
                                 name + '_' + trial_type +
                                 op.filter_string(highpass, lowpass) + '_vector_' + str(idx) + '.jpg')
                brain.save_image(save_path)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_mixn(name, save_dir, highpass, lowpass, subtomri, subjects_dir,
              mne_evoked_time, event_id, stc_interactive,
              save_plots, figures_path, mixn_dip, parcellation):
    if mixn_dip:
        trans = loading.read_transformation(save_dir, subtomri)
        dipole_dict = loading.read_mixn_dipoles(name, save_dir, highpass, lowpass, event_id)
        for trial_type in event_id:
            dipoles = dipole_dict[trial_type]
            # Plot Dipole Amplitues (derived from Source Code with added legend)
            colors = plt.cm.get_cmap(name='hsv', lut=len(dipoles) + 1)
            fig1, ax = plt.subplots(1, 1)
            xlim = [np.inf, -np.inf]
            for i, dip in enumerate(dipoles):
                ax.plot(dip.times, dip.amplitude * 1e9, color=colors(i), linewidth=1.5, label=f'dipole {i + 1}')
                xlim[0] = min(xlim[0], dip.times[0])
                xlim[1] = max(xlim[1], dip.times[-1])
            ax.set(xlim=xlim, xlabel='Time (s)', ylabel='Amplitude (nAm)')
            ax.legend()
            fig1.suptitle(f'Dipoles Amplitudes', fontsize=16)
            fig1.show(warn=False)
            if save_plots:
                save_path = join(figures_path, 'mxn_dipoles', trial_type,
                                 name + '_' + trial_type +
                                 op.filter_string(highpass, lowpass) + '_mixn-amp.jpg')
                fig1.savefig(save_path)

            labels = mne.read_labels_from_annot(subtomri, subjects_dir=subjects_dir,
                                                parc=parcellation)
            for idx, dipole in enumerate(dipoles):
                # Assumption right in Head Coordinates?
                if dipole.pos[0, 0] < 0:
                    side = 'left'
                    hemi = 'lh'
                else:
                    side = 'right'
                    hemi = 'rh'
                fig2 = mne.viz.plot_dipole_locations(dipole, trans=trans, subject=subtomri, subjects_dir=subjects_dir,
                                                     coord_frame='mri')
                fig2.suptitle(f'Dipole {idx + 1} {side}', fontsize=16)
                if save_plots:
                    save_path = join(figures_path, 'mxn_dipoles', trial_type,
                                     name + '_' + trial_type +
                                     op.filter_string(highpass, lowpass) + '_mixn-dip-' + str(idx) + '.jpg')
                    fig2.savefig(save_path)

                brain = Brain(subtomri, hemi=hemi, surf='pial', views='lat')
                dip_loc = mne.head_to_mri(dipole.pos, subtomri, trans, subjects_dir=subjects_dir)
                brain.add_foci(dip_loc[0])
                brain.add_annotation(parcellation)
                # Todo: Comparision with label
                if save_plots:
                    save_path = join(figures_path, 'mxn_dipoles', trial_type,
                                     name + '_' + trial_type +
                                     op.filter_string(highpass, lowpass) + '_mixn-srfdip-' + str(idx) + '.jpg')
                    brain.save_image(save_path)

    else:
        plot_mixn_stc(name, save_dir, highpass, lowpass, subtomri, subjects_dir,
                      mne_evoked_time, event_id, stc_interactive,
                      save_plots, figures_path)
    plot_mixn_res(name, save_dir, highpass, lowpass, event_id, save_plots, figures_path)


def plot_mixn_stc(name, save_dir, highpass, lowpass, subtomri, subjects_dir,
                  mne_evoked_time, event_id, stc_interactive,
                  save_plots, figures_path):
    stcs = loading.read_mixn_source_estimates(name, save_dir, highpass, lowpass, event_id)
    for trial_type in stcs:
        for idx, t in enumerate(mne_evoked_time):
            stc = stcs[trial_type]
            figures_list = [mlab.figure(figure=idx * 2, size=(800, 800)),
                            mlab.figure(figure=idx * 2 + 1, size=(800, 800))]
            if stc_interactive:
                brain = stc.plot(subject=subtomri, surface='inflated', subjects_dir=subjects_dir,
                                 time_viewer=True, hemi='split', views='lat', initial_time=t,
                                 title=f'{name}-{trial_type}_mixn', size=(1600, 800), figure=figures_list)
            else:
                brain = stc.plot(subject=subtomri, surface='inflated', subjects_dir=subjects_dir,
                                 time_viewer=False, hemi='split', views='lat', initial_time=t,
                                 title=f'{name}-{trial_type}_mixn', size=(1600, 800), figure=figures_list)
            brain.title = f'{name}-{trial_type}_mixn'
            if save_plots:
                save_path = join(figures_path, 'mxne', trial_type,
                                 name + '_' + trial_type +
                                 op.filter_string(highpass, lowpass) + '_mixn_' + str(idx) + '.jpg')
                brain.save_image(save_path)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

        if not stc_interactive:
            close_all()


# Todo: Ordner anpassen
@decor.topline
def plot_mixn_res(name, save_dir, highpass, lowpass, event_id, save_plots, figures_path):
    for trial_type in event_id:
        mixn_res_name = name + op.filter_string(highpass, lowpass) + '_' + trial_type + '-mixn-res-ave.fif'
        mixn_res_path = join(save_dir, mixn_res_name)

        fig = mne.read_evokeds(mixn_res_path)[0].plot(spatial_colors=True)
        if save_plots:
            save_path = join(figures_path, 'stcs', trial_type,
                             name + '_' + trial_type +
                             op.filter_string(highpass, lowpass) + '_mixn-res.jpg')
            fig.savefig(save_path)
        else:
            print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_animated_stc(name, save_dir, highpass, lowpass, subtomri, subjects_dir,
                      inverse_method, stc_animation, event_id,
                      figures_path):
    n_stcs = loading.read_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method,
                                                  event_id)

    for ev_id in event_id:
        n_stc = n_stcs[ev_id]

        save_path = join(figures_path, 'stcs_movie', name +
                         op.filter_string(highpass, lowpass) + '.mp4')

        brain = mne.viz.plot_source_estimates(stc=n_stc, subject=subtomri, surface='inflated',
                                              subjects_dir=subjects_dir, size=(1600, 800),
                                              hemi='split', views='lat',
                                              title=name + '_movie')

        print('Saving Video')
        brain.save_movie(save_path, time_dilation=10,
                         tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
        mlab.close()


@decor.topline
def plot_snr(name, save_dir, highpass, lowpass, save_plots, figures_path, inverse_method, event_id):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)

    inv = loading.read_inverse_operator(name, save_dir, highpass, lowpass)
    # stcs = io.read_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method, event_id)

    for evoked in evokeds:
        trial_type = evoked.comment
        # data snr
        figure = mne.viz.plot_snr_estimate(evoked, inv)
        plt.title(name + ' - ' + evoked.comment, loc='center')

        if save_plots:
            save_path = join(figures_path, 'snr', trial_type,
                             name + '_' + evoked.comment + '_snr' +
                             op.filter_string(highpass, lowpass) + '.jpg')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')
        # source-space snr
        # fixed orientation and MNE-solution needed
        # stc = stcs[trial_type]
        # stc.estimate_snr(evoked.info)


@decor.topline
def plot_labels(mri_subject, save_plots, figures_path,
                parcellation):
    brain = Brain(mri_subject, hemi='lh', surf='inflated', views='lat')

    brain.add_annotation(parcellation)

    if save_plots:
        save_path = join(figures_path, 'labels',
                         mri_subject + '_' + parcellation + '.jpg')
        mlab.savefig(save_path, figure=mlab.gcf())
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "save_plots" to "True" to save')



@decor.topline
def plot_label_time_course(name, save_dir, highpass, lowpass, subtomri,
                           subjects_dir, inverse_method, source_space_method,
                           target_labels, save_plots, figures_path,
                           parcellation, event_id):
    stcs = loading.read_normal_source_estimates(name, save_dir, highpass, lowpass,
                                                inverse_method, event_id)

    src = loading.read_source_space(subtomri, subjects_dir, source_space_method)

    labels = mne.read_labels_from_annot(subtomri,
                                        subjects_dir=subjects_dir,
                                        parc=parcellation)

    # Annotation Parameters
    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    arrowprops = dict(arrowstyle="->")
    kw = dict(xycoords='data', arrowprops=arrowprops, bbox=bbox_props)
    for trial in event_id:
        stc = stcs[trial]
        for hemi in target_labels:
            for l in labels:
                if l.name in target_labels[hemi]:
                    print(l.name)

                    stc_label = stc.in_label(l)
                    gfp = op.calculate_gfp(stc)
                    mean = stc.extract_label_time_course(l, src, mode='mean')
                    mean_flip = stc.extract_label_time_course(l, src, mode='mean_flip')
                    pca = stc.extract_label_time_course(l, src, mode='pca_flip')

                    t = 1e3 * stc_label.times
                    tmax = t[np.argmax(pca)]
                    tmin = t[np.argmin(pca)]
                    print(tmin)
                    print(tmax)

                    plt.figure()
                    plt.plot(t, stc_label.data.T, 'k', linewidth=0.5)
                    h0, = plt.plot(t, mean.T, 'r', linewidth=3)
                    h1, = plt.plot(t, mean_flip.T, 'g', linewidth=3)
                    h2, = plt.plot(t, pca.T, 'b', linewidth=3)
                    h3, = plt.plot(t, gfp, 'y', linewidth=3)

                    if -200 < tmax < 500:
                        plt.annotate(f'max_lat={int(tmax)}ms',
                                     xy=(tmax, pca.max()),
                                     xytext=(tmax + 200, pca.max() + 2), **kw)
                    if -200 < tmin < 500:
                        plt.annotate(f'min_lat={int(tmin)}ms',
                                     xy=(tmin, pca.min()),
                                     xytext=(tmin + 200, pca.min() - 2), **kw)
                    plt.legend([h0, h1, h2, h3], ['mean', 'mean flip', 'PCA flip', 'GFP'])
                    plt.xlabel('Time (ms)')
                    plt.ylabel('Source amplitude')
                    plt.title(f'Activations in Label :{l.name}-{trial}')
                    plt.show()

                    if save_plots:
                        save_path = join(figures_path, 'label_time_course', trial, name +
                                         op.filter_string(highpass, lowpass) + '_' +
                                         trial + '_' + l.name + '.jpg')
                        plt.savefig(save_path, dpi=600)
                        print('figure: ' + save_path + ' has been saved')
                    else:
                        print('Not saving plots; set "save_plots" to "True" to save')



@decor.topline
def plot_label_power_phlck(name, save_dir, highpass, lowpass, subtomri, parcellation,
                           baseline, tfr_freqs, save_plots, figures_path, n_jobs,
                           target_labels, event_id):
    # Compute a source estimate per frequency band including and excluding the
    # evoked response
    freqs = tfr_freqs  # define frequencies of interest
    n_cycles = freqs / 3.  # different number of cycle per frequency
    labels = mne.read_labels_from_annot(subtomri, parc=parcellation)

    for ev_id in event_id:
        epochs = loading.read_epochs(name, save_dir, highpass, lowpass)[ev_id]
        inverse_operator = loading.read_inverse_operator(name, save_dir, highpass, lowpass)
        # subtract the evoked response in order to exclude evoked activity
        epochs_induced = epochs.copy().subtract_evoked()

        for hemi in target_labels:
            for label in [labl for labl in labels if labl.name in target_labels[hemi]]:

                print(label.name)

                plt.close('all')
                mlab.close(all=True)

                for ii, (this_epochs, title) in enumerate(zip([epochs, epochs_induced],
                                                              ['evoked + induced',
                                                               'induced only'])):
                    # compute the source space power and the inter-trial coherence
                    power, itc = mne.minimum_norm.source_induced_power(
                            this_epochs, inverse_operator, freqs, label, baseline=baseline,
                            baseline_mode='percent', n_cycles=n_cycles, n_jobs=n_jobs)

                    power = np.mean(power, axis=0)  # average over sources
                    itc = np.mean(itc, axis=0)  # average over sources
                    times = epochs.times

                    # View time-frequency plots
                    plt.subplots_adjust(0.1, 0.08, 0.96, 0.94, 0.2, 0.43)
                    plt.subplot(2, 2, 2 * ii + 1)
                    plt.imshow(20 * power,
                               extent=[times[0], times[-1], freqs[0], freqs[-1]],
                               aspect='auto', origin='lower', vmin=0., vmax=10., cmap='RdBu_r')
                    plt.xlabel('Time (s)')
                    plt.ylabel('Frequency (Hz)')
                    plt.title('Power (%s)' % title)
                    plt.colorbar()

                    plt.subplot(2, 2, 2 * ii + 2)
                    plt.imshow(itc,
                               extent=[times[0], times[-1], freqs[0], freqs[-1]],
                               aspect='auto', origin='lower', vmin=0, vmax=0.4,
                               cmap='RdBu_r')
                    plt.xlabel('Time (s)')
                    plt.ylabel('Frequency (Hz)')
                    plt.title('ITC (%s)' % title)
                    plt.colorbar()

                plt.show()

                if save_plots:
                    save_path = join(figures_path, 'tf_source_space/label_power', name + '_' + label.name + '_power_' +
                                     ev_id + op.filter_string(highpass, lowpass) + '.jpg')
                    plt.savefig(save_path, dpi=600)
                    print('figure: ' + save_path + ' has been saved')
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_grand_avg_label_power(grand_avg_dict, event_id, target_labels,
                               save_dir_averages, tfr_freqs, t_epoch, highpass,
                               lowpass, save_plots, figures_path):
    ga_dict = loading.read_ga_label_power(grand_avg_dict, event_id, target_labels,
                                          save_dir_averages)
    freqs = tfr_freqs
    for key in ga_dict:
        for ev_id in event_id:
            for hemi in target_labels:
                for label_name in target_labels[hemi]:
                    power_ind = ga_dict[key][ev_id][label_name]['power']
                    itc_ind = ga_dict[key][ev_id][label_name]['itc']

                    times = np.arange(t_epoch[0], t_epoch[1] + 0.001, 0.001)

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

                    plt.show()

                    if save_plots:
                        save_path = join(figures_path, 'grand_averages/source_space/tfr',
                                         f'{key}_{ev_id}_{label_name}_{op.filter_string(highpass, lowpass)}_power.jpg')
                        plt.savefig(save_path, dpi=600)
                        print('figure: ' + save_path + ' has been saved')
                    else:
                        print('Not saving plots; set "save_plots" to "True" to save')
                    close_all()


#        nrows = len(target_labels)
#        ncols = len(target_labels['lh'])
#        fig, axes = plt.subplots(nrows=nrows, ncols=ncols,
#                                 sharex='all', sharey='all',
#                                 gridspec_kw={'hspace':0.1, 'wspace':0.1,
#                                              'left':0.05, 'right':0.95,
#                                              'top':0.95, 'bottom':0.05},
#                                 figsize=(18,8))
#
#        # Nasty workaround to set label-titles on axes
#        # key in target_labels = row in plot
#        r_cnt = 0
#        for tl in target_labels:
#            c_cnt = 0
#            for t in target_labels[tl]:
#                axes[r_cnt, c_cnt].set_title(t)
#                c_cnt += 1
#            r_cnt += 1
#
#        for ev_id in ev_ids_label_analysis:
#            for hemi in target_labels:
#                for label_name in target_labels[hemi]:
#                    ga_dict
#
#                    
#
#                    
#                    # Nasty workaround to set label-titles on axes
#                    # key in target_labels = row in plot
#                    r_cnt = 0
#                    for tl in target_labels:
#                        c_cnt = 0
#                        for t in target_labels[tl]:
#                            axes[r_cnt, c_cnt].set_title(t)
#                            c_cnt += 1
#                        r_cnt += 1

@decor.topline
def plot_source_space_connectivity(name, save_dir, highpass, lowpass,
                                   subtomri, subjects_dir, parcellation,
                                   target_labels, con_methods, con_fmin,
                                   con_fmax, save_plots, figures_path, event_id):
    con_dict = loading.read_connect(name, save_dir, highpass, lowpass, con_methods,
                                    con_fmin, con_fmax, event_id)
    # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
    labels = mne.read_labels_from_annot(subtomri, parc=parcellation,
                                        subjects_dir=subjects_dir)

    actual_labels = [lb for lb in labels if lb.name in target_labels['lh']
                     or lb.name in target_labels['rh']]

    label_colors = [label.color for label in actual_labels]

    # First, we reorder the labels based on their location in the left hemi
    label_names = [label.name for label in actual_labels]

    lh_labels = [l_name for l_name in label_names if l_name.endswith('lh')]
    rh_labels = [l_name for l_name in label_names if l_name.endswith('rh')]

    # Get the y-location of the label
    lh_label_ypos = list()
    for l_name in lh_labels:
        idx = label_names.index(l_name)
        ypos = np.mean(actual_labels[idx].pos[:, 1])
        lh_label_ypos.append(ypos)

    rh_label_ypos = list()
    for l_name in lh_labels:
        idx = label_names.index(l_name)
        ypos = np.mean(actual_labels[idx].pos[:, 1])
        rh_label_ypos.append(ypos)

    # Reorder the labels based on their location
    lh_labels = [label for (yp, label) in sorted(zip(lh_label_ypos, lh_labels))]
    rh_labels = [label for (yp, label) in sorted(zip(rh_label_ypos, rh_labels))]
    # For the right hemi
    # rh_labels = [label[:-2] + 'rh' for label in lh_labels]

    # Save the plot order and create a circular layout
    node_order = list()
    node_order.extend(lh_labels[::-1])  # reverse the order
    node_order.extend(rh_labels)

    node_angles = mne.viz.circular_layout(label_names, node_order, start_pos=90,
                                          group_boundaries=[0, len(label_names) / 2])

    # Plot the graph using node colors from the FreeSurfer parcellation. We only
    # show the 300 strongest connections.
    for ev_id in event_id:
        for con_method in con_methods:
            fig, axes = mne.viz.plot_connectivity_circle(con_dict[ev_id][con_method], label_names, n_lines=300,
                                                         node_angles=node_angles, node_colors=label_colors,
                                                         title=con_method + '_' + str(con_fmin) + '-' + str(con_fmax),
                                                         fontsize_names=12)
            if save_plots:
                save_path = join(figures_path, 'tf_source_space/connectivity', name +
                                 op.filter_string(highpass, lowpass) +
                                 '_' + str(con_fmin) + '-' + str(con_fmax) + 'Hz' +
                                 '_' + con_method + '_' + ev_id + '.jpg')
                fig.savefig(save_path, dpi=600, facecolor='k', edgecolor='k')
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')


# %% Grand-Average Plots
@decor.topline
def plot_grand_avg_evokeds(highpass, lowpass, save_dir_averages, grand_avg_dict,
                           event_id, save_plots, figures_path):
    ga_dict = loading.read_grand_avg_evokeds(highpass, lowpass, save_dir_averages,
                                             grand_avg_dict, event_id)

    for stim_type in ga_dict:
        for trial in ga_dict[stim_type]:
            figure = ga_dict[stim_type][trial].plot(window_title=stim_type + '_' + trial,
                                                    spatial_colors=True, gfp=True)  # ylim={'grad': [-80, 35]},
            if save_plots:
                save_path = join(figures_path, 'grand_averages/sensor_space/evoked',
                                 stim_type + '_' + trial +
                                 op.filter_string(highpass, lowpass) + '.jpg')
                figure.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_grand_avg_tfr(highpass, lowpass, baseline, t_epoch,
                       save_dir_averages, grand_avg_dict,
                       event_id, save_plots, figures_path):
    ga_dict = loading.read_grand_avg_tfr(highpass, lowpass, save_dir_averages,
                                         grand_avg_dict, event_id)

    for stim_type in ga_dict:
        for trial in ga_dict[stim_type]:
            power = ga_dict[stim_type][trial]
            fig1 = power.plot(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                              tmax=t_epoch[1], title=f'{stim_type}-{trial}')
            fig2 = power.plot_topo(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                                   tmax=t_epoch[1], title=f'{stim_type}-{trial}')
            fig3 = power.plot_joint(baseline=baseline, mode='mean', tmin=t_epoch[0],
                                    tmax=t_epoch[1], title=f'{stim_type}-{trial}')

            fig4, axis = plt.subplots(1, 5, figsize=(15, 2))
            power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=5, fmax=8,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[0],
                               title='Theta 5-8 Hz', show=False)
            power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=8, fmax=12,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[1],
                               title='Alpha 8-12 Hz', show=False)
            power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=13, fmax=30,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[2],
                               title='Beta 13-30 Hz', show=False)
            power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=31, fmax=60,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[3],
                               title='Low Gamma 30-60 Hz', show=False)
            power.plot_topomap(ch_type='grad', tmin=t_epoch[0], tmax=t_epoch[1], fmin=61, fmax=100,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[4],
                               title='High Gamma 60-100 Hz', show=False)
            mne.viz.tight_layout()
            plt.title(f'{stim_type}-{trial}')
            plt.show()

            if save_plots:
                save_path1 = join(figures_path, 'grand_averages/sensor_space/tfr',
                                  stim_type + '_' + trial + '_tf' +
                                  op.filter_string(highpass, lowpass) + '.jpg')
                fig1.savefig(save_path1, dpi=600)
                print('figure: ' + save_path1 + ' has been saved')
                save_path2 = join(figures_path, 'grand_averages/sensor_space/tfr',
                                  stim_type + '_' + trial + '_tf_topo' +
                                  op.filter_string(highpass, lowpass) + '.jpg')
                fig2.savefig(save_path2, dpi=600)
                print('figure: ' + save_path2 + ' has been saved')
                save_path3 = join(figures_path, 'grand_averages/sensor_space/tfr',
                                  stim_type + '_' + trial + '_tf_joint' +
                                  op.filter_string(highpass, lowpass) + '.jpg')
                fig3.savefig(save_path3, dpi=600)
                print('figure: ' + save_path3 + ' has been saved')
                save_path4 = join(figures_path, 'grand_averages/sensor_space/tfr',
                                  stim_type + '_' + trial + '_tf_oscs' +
                                  op.filter_string(highpass, lowpass) + '.jpg')
                fig4.savefig(save_path4, dpi=600)
                print('figure: ' + save_path4 + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')

            close_all()


@decor.topline
def plot_grand_avg_stc(highpass, lowpass, save_dir_averages,
                       grand_avg_dict, mne_evoked_time, morph_to,
                       subjects_dir, event_id, save_plots,
                       figures_path):
    ga_dict = loading.read_grand_avg_stcs(highpass, lowpass, save_dir_averages,
                                          grand_avg_dict, event_id)

    for group in ga_dict:
        for trial in ga_dict[group]:
            for idx, t in enumerate(mne_evoked_time):
                brain = ga_dict[group][trial].plot(subject=morph_to,
                                                   subjects_dir=subjects_dir, size=(1600, 800),
                                                   title=f'{group}-{trial}', hemi='split',
                                                   views='lat', initial_time=t)
                brain.title = group + '-' + trial

                if save_plots:
                    save_path = join(figures_path, 'grand_averages/source_space/stc',
                                     group + '_' + trial +
                                     op.filter_string(highpass, lowpass) +
                                     '_' + str(idx) + '.jpg')
                    brain.save_image(save_path)
                    print('figure: ' + save_path + ' has been saved')

                else:
                    print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_grand_avg_stc_normal(highpass, lowpass, save_dir_averages,
                              grand_avg_dict, mne_evoked_time, morph_to,
                              subjects_dir, event_id, save_plots,
                              figures_path):
    ga_dict = loading.read_grand_avg_stcs_normal(highpass, lowpass, save_dir_averages,
                                                 grand_avg_dict, event_id)

    for group in ga_dict:
        for trial in ga_dict[group]:
            for idx, t in enumerate(mne_evoked_time):
                brain = ga_dict[group][trial].plot(subject=morph_to,
                                                   subjects_dir=subjects_dir, size=(1600, 800),
                                                   title=f'{group}-{trial}', hemi='split',
                                                   views='lat', initial_time=t)
                brain.title = group + '-' + trial

                if save_plots:
                    save_path = join(figures_path, 'grand_averages/source_space/stc',
                                     group + '_' + trial +
                                     op.filter_string(highpass, lowpass) +
                                     '_' + str(idx) + '.jpg')
                    brain.save_image(save_path)
                    print('figure: ' + save_path + ' has been saved')

                else:
                    print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def plot_grand_avg_stc_anim(highpass, lowpass, save_dir_averages,
                            grand_avg_dict, stc_animation,
                            morph_to, subjects_dir, event_id,
                            figures_path):
    ga_dict = loading.read_grand_avg_stcs(highpass, lowpass, save_dir_averages,
                                          grand_avg_dict, event_id)

    for stim_type in ga_dict:
        for trial in ga_dict[stim_type]:
            brain = ga_dict[stim_type][trial].plot(subject=morph_to,
                                                   subjects_dir=subjects_dir, size=(1600, 800),
                                                   title=f'{stim_type}-{trial}', hemi='split',
                                                   views='lat')
            brain.title = stim_type + '-' + trial

            print('Saving Video')
            save_path = join(figures_path, 'grand_averages/source_space/stc_movie',
                             stim_type + '_' + trial +
                             op.filter_string(highpass, lowpass) + '.mp4')
            brain.save_movie(save_path, time_dilation=30,
                             tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
            mlab.close()


@decor.topline
def plot_grand_avg_connect(highpass, lowpass, save_dir_averages,
                           grand_avg_dict, subjects_dir, morph_to, parcellation, con_methods, con_fmin, con_fmax,
                           save_plots, figures_path, event_id,
                           target_labels):
    ga_dict = loading.read_grand_avg_connect(highpass, lowpass, save_dir_averages,
                                             grand_avg_dict, con_methods, event_id)

    # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
    labels_parc = mne.read_labels_from_annot(morph_to, parc=parcellation,
                                             subjects_dir=subjects_dir)

    labels = [labl for labl in labels_parc if labl.name in target_labels['lh']
              or labl.name in target_labels['rh']]

    label_colors = [label.color for label in labels]
    for labl in labels:
        if labl.name == 'unknown-lh':
            del labels[labels.index(labl)]
            print('unknown-lh removed')

    # First, we reorder the labels based on their location in the left hemi
    label_names = [label.name for label in labels]

    lh_labels = [l_name for l_name in label_names if l_name.endswith('lh')]
    rh_labels = [l_name for l_name in label_names if l_name.endswith('rh')]

    # Get the y-location of the label
    lh_label_ypos = list()
    for l_name in lh_labels:
        idx = label_names.index(l_name)
        ypos = np.mean(labels[idx].pos[:, 1])
        lh_label_ypos.append(ypos)

    rh_label_ypos = list()
    for l_name in lh_labels:
        idx = label_names.index(l_name)
        ypos = np.mean(labels[idx].pos[:, 1])
        rh_label_ypos.append(ypos)

    # Reorder the labels based on their location
    lh_labels = [label for (yp, label) in sorted(zip(lh_label_ypos, lh_labels))]
    rh_labels = [label for (yp, label) in sorted(zip(rh_label_ypos, rh_labels))]

    # For the right hemi
    # rh_labels = [label[:-2] + 'rh' for label in lh_labels]

    # Save the plot order and create a circular layout
    node_order = list()
    node_order.extend(lh_labels[::-1])  # reverse the order
    node_order.extend(rh_labels)

    node_angles = mne.viz.circular_layout(label_names, node_order, start_pos=90,
                                          group_boundaries=[0, len(label_names) / 2])

    for stim_type in ga_dict:
        for ev_id in event_id:
            for method in ga_dict[stim_type][ev_id]:
                fig, axes = mne.viz.plot_connectivity_circle(ga_dict[stim_type][ev_id][method],
                                                             label_names, n_lines=300,
                                                             node_angles=node_angles,
                                                             node_colors=label_colors,
                                                             title=method + '_' + str(con_fmin) + '-' + str(con_fmax),
                                                             fontsize_names=16)
                if save_plots:
                    save_path = join(figures_path, 'grand_averages/source_space/connectivity', stim_type +
                                     op.filter_string(highpass, lowpass) +
                                     '_' + str(con_fmin) + '-' + str(con_fmax) +
                                     '_' + method + '-' + ev_id + '.jpg')
                    fig.savefig(save_path, dpi=600, facecolor='k', edgecolor='k')
                    print('figure: ' + save_path + ' has been saved')
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')
            close_all()


@decor.topline
def plot_grand_averages_source_estimates_cluster_masked(name,
                                                        save_dir_averages, highpass, lowpass,
                                                        subjects_dir, inverse_method, time_window,
                                                        save_plots, figures_path,
                                                        independent_variable_1, independent_variable_2,
                                                        mne_evoked_time, p_threshold):
    if mne_evoked_time < time_window[0] or mne_evoked_time > time_window[1]:
        raise ValueError('"mne_evoked_time" must be within "time_window"')
    n_subjects = 20  # should be corrected
    independent_variables = [independent_variable_1, independent_variable_2]
    stcs = dict()
    for stc_type in independent_variables:
        filename = join(save_dir_averages,
                        stc_type + op.filter_string(highpass, lowpass) +
                        '_morphed_data_' + inverse_method)
        stc = mne.read_source_estimate(filename)
        stc.comment = stc_type
        stcs[stc_type] = stc

    difference_stc = stcs[independent_variable_1] - stcs[independent_variable_2]

    # load clusters

    cluster_dict = loading.read_clusters(save_dir_averages, independent_variable_1,
                                         independent_variable_2, time_window, highpass, lowpass)
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
    clim = dict(kind='value', lims=[cutoff, 2 * cutoff, 4 * cutoff])

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
                         message + '_' + name +
                         op.filter_string(highpass, lowpass) + '.jpg' + '_' + str(time * 1e3) +
                         '_msec.jpg')
        brain.save_single_image(save_path)
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "save_plots" to "True" to save')


@decor.topline
def close_all():
    plt.close('all')
    mlab.close(all=True)
    gc.collect()
