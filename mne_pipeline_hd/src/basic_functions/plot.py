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
from nilearn.plotting import plot_anat
from surfer import Brain

from src.basic_functions import operations as op
from src.pipeline_functions.decorators import topline


# ==============================================================================
# PLOTTING FUNCTIONS
# ==============================================================================
@topline
def plot_filtered(sub):
    loaded_raw = sub.load_filtered()

    try:
        loaded_events = sub.load_events()
        mne.viz.plot_raw(raw=loaded_raw, events=loaded_events, n_channels=30, bad_color='red',
                         scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
                         title=f'{sub.name}_highpass={sub.p["highpass"]}_lowpass={sub.p["lowpass"]}')

    except FileNotFoundError:
        print('No events found')
        mne.viz.plot_raw(raw=loaded_raw, n_channels=30, bad_color='red',
                         scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
                         title=f'{sub.name}_highpass={sub.p["highpass"]}_lowpass={sub.p["lowpass"]}')


@topline
def plot_sensors(sub):
    loaded_info = sub.load_info()
    mne.viz.plot_sensors(loaded_info, kind='topomap', title=sub.name, show_names=True, ch_groups='position')


@topline
def plot_events(sub):
    events = sub.load_events()
    actual_event_id = {}
    for ev_id in [evid for evid in sub.p['event_id'] if evid in np.unique(events[:, 2])]:
        actual_event_id.update({ev_id: sub.p['event_id'][ev_id]})

    events_figure = mne.viz.plot_events(events, sfreq=1000, event_id=actual_event_id)
    plt.title(sub.name)

    if sub.save_plots:
        save_path = join(sub.figures_path, 'events', sub.name + sub.img_format)
        events_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_power_spectra(sub):
    raw = sub.load_filtered()
    picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False, eog=False, ecg=False,
                           exclude='bads')

    psd_figure = raw.plot_psd(fmax=sub.p['lowpass'], picks=picks, n_jobs=1)
    plt.title(sub.name)

    if sub.save_plots:
        save_path = join(sub.figures_path, 'power_spectra_raw', f'{sub.name}_{sub.p_preset}-power_raw{sub.img_format}')
        psd_figure.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_power_spectra_epochs(sub):
    epochs = sub.load_epochs()

    for trial in epochs.event_id:

        psd_figure = epochs[trial].plot_psd(fmax=sub.p['lowpass'], n_jobs=-1)
        plt.title(sub.name + '-' + trial)

        if sub.save_plots:
            save_path = join(sub.figures_path, 'power_spectra_epochs', trial,
                             f'{sub.name}_{trial}_{sub.p_preset}-power_epochs{sub.img_format}')
            psd_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_power_spectra_topo(sub):
    epochs = sub.load_epochs()
    for trial in epochs.event_id:
        psd_figure = epochs[trial].plot_psd_topomap(n_jobs=-1)
        plt.title(sub.name + '-' + trial)

        if sub.save_plots:
            save_path = join(sub.figures_path, 'power_spectra_topo', trial,
                             f'{sub.name}_{trial}_{sub.p_preset}-power_epochs_topo{sub.img_format}')
            psd_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_tfr(sub, t_epoch, baseline):
    powers = sub.load_power_tfr()
    itcs = sub.load_itc_tfr()

    for power in powers:
        fig1 = power.plot(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                          tmax=t_epoch[1], title=f'{sub.name}-{power.comment}')
        fig2 = power.plot_topo(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                               tmax=t_epoch[1], title=f'{sub.name}-{power.comment}')
        fig3 = power.plot_joint(baseline=baseline, mode='mean', tmin=t_epoch[0],
                                tmax=t_epoch[1], title=f'{sub.name}-{power.comment}')

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
        plt.title(f'{sub.name}-{power.comment}')
        plt.show()

        if sub.save_plots:
            save_path1 = join(sub.figures_path, 'tf_sensor_space/plot',
                              f'{sub.name}_{power.comment}_{sub.p_preset}-tfr{sub.img_format}')
            fig1.savefig(save_path1, dpi=600)
            print('figure: ' + save_path1 + ' has been saved')
            save_path2 = join(sub.figures_path, 'tf_sensor_space/topo',
                              f'{sub.name}_{power.comment}_{sub.p_preset}-tfr_topo{sub.img_format}')
            fig2.savefig(save_path2, dpi=600)
            print('figure: ' + save_path2 + ' has been saved')
            save_path3 = join(sub.figures_path, 'tf_sensor_space/joint',
                              f'{sub.name}_{power.comment}_{sub.p_preset}-tfr_joint{sub.img_format}')
            fig3.savefig(save_path3, dpi=600)
            print('figure: ' + save_path3 + ' has been saved')
            save_path4 = join(sub.figures_path, 'tf_sensor_space/oscs',
                              f'{sub.name}_{power.comment}_{sub.p_preset}-tfr_osc{sub.img_format}')
            fig4.savefig(save_path4, dpi=600)
            print('figure: ' + save_path4 + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')

    for itc in itcs:
        fig5 = itc.plot_topo(title=f'{sub.name}-{itc.comment}-itc',
                             vmin=0., vmax=1., cmap='Reds')

        if sub.save_plots:
            save_path5 = join(sub.figures_path, 'tf_sensor_space/itc',
                              f'{sub.name}_{itc.comment}_{sub.p_preset}-tfr_itc{sub.img_format}')
            fig5.savefig(save_path5, dpi=600)
            print('figure: ' + save_path5 + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_epochs(sub):
    epochs = sub.load_epochs()

    for trial in epochs.event_id:
        mne.viz.plot_epochs(epochs[trial], title=sub.name)
        plt.title(trial)


@topline
def plot_epochs_image(sub):
    epochs = sub.load_epochs()
    for trial in epochs.event_id:
        epochs_image = mne.viz.plot_epochs_image(epochs[trial], title=sub.name + '_' + trial)

        if sub.save_plots:
            save_path = join(sub.figures_path, 'epochs_image', trial,
                             f'{sub.name}_{trial}_{sub.p_preset}-epochs_image{sub.img_format}')

            epochs_image[0].savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_epochs_topo(sub):
    epochs = sub.load_epochs()
    for trial in epochs.event_id:
        epochs_topo = mne.viz.plot_topo_image_epochs(epochs, title=sub.name)

        if sub.save_plots:
            save_path = join(sub.figures_path, 'epochs_topo', trial,
                             f'{sub.name}_{trial}_{sub.p_preset}-epochs_topo{sub.img_format}')

            epochs_topo.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_epochs_drop_log(sub):
    epochs = sub.load_epochs()

    fig = epochs.plot_drop_log(subject=sub.name)

    if sub.save_plots:
        save_path = join(sub.figures_path, 'epochs_drop_log',
                         f'{sub.name}_{sub.p_preset}-epochs_drop_log{sub.img_format}')

        fig.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_evoked_topo(sub):
    evokeds = sub.load_evokeds()

    evoked_figure = mne.viz.plot_evoked_topo(evokeds, title=sub.name)

    if sub.save_plots:
        save_path = join(sub.figures_path, 'evoked_topo', f'{sub.name}_{sub.p_preset}-evoked_topo{sub.img_format}')
        evoked_figure.savefig(save_path, dpi=1200)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_evoked_topomap(sub):
    evokeds = sub.load_evokeds()
    for evoked in evokeds:
        evoked_figure = mne.viz.plot_evoked_topomap(evoked, times='auto',
                                                    title=sub.name + '-' + evoked.comment)

        if sub.save_plots:
            save_path = join(sub.figures_path, 'evoked_topomap', evoked.comment,
                             f'{sub.name}_{evoked.comment}_{sub.p_preset}-evoked_topomap{sub.img_format}')
            evoked_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_evoked_joint(sub):
    evokeds = sub.load_evokeds()

    for evoked in evokeds:
        figure = mne.viz.plot_evoked_joint(evoked, times='peaks',
                                           title=sub.name + ' - ' + evoked.comment)

        if sub.save_plots:
            save_path = join(sub.figures_path, 'evoked_joint', evoked.comment,
                             f'{sub.name}_{evoked.comment}_{sub.p_preset}-evoked_joint{sub.img_format}')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_evoked_butterfly(sub):
    evokeds = sub.load_evokeds()

    for evoked in evokeds:
        figure = evoked.plot(spatial_colors=True,
                             window_title=sub.name + ' - ' + evoked.comment,
                             selectable=True, gfp=True, zorder='std')

        if sub.save_plots:
            save_path = join(sub.figures_path, 'evoked_butterfly', evoked.comment,
                             f'{sub.name}_{evoked.comment}_{sub.p_preset}-evoked_butterfly{sub.img_format}')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_evoked_white(sub):
    evokeds = sub.load_evokeds()
    noise_covariance = sub.load_noise_covariance()

    for evoked in evokeds:
        # Check, if evokeds and noise covariance got the same channels
        channels = set(evoked.ch_names) & set(noise_covariance.ch_names)
        evoked.pick_channels(channels)

        figure = mne.viz.plot_evoked_white(evoked, noise_covariance)
        plt.title(sub.name + ' - ' + evoked.comment, loc='center')

        if sub.save_plots:
            save_path = join(sub.figures_path, 'evoked_white', evoked.comment,
                             f'{sub.name}_{evoked.comment}_{sub.p_preset}-evoked_white{sub.img_format}')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_evoked_image(sub):
    evokeds = sub.load_evokeds()

    for evoked in evokeds:
        figure = mne.viz.plot_evoked_image(evoked)
        plt.title(sub.name + ' - ' + evoked.comment, loc='center')

        if sub.save_plots:
            save_path = join(sub.figures_path, 'evoked_image', evoked.comment,
                             f'{sub.name}_{evoked.comment}_{sub.p_preset}-evoked_image{sub.img_format}')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_gfp(sub):
    evokeds = sub.load_evokeds()
    for evoked in evokeds:
        gfp = op.calculate_gfp(evoked)
        t = evoked.times
        trial = evoked.comment
        plt.figure()
        plt.plot(t, gfp)
        plt.title(f'GFP of {sub.name}-{trial}')
        plt.show()
        if sub.save_plots:
            save_path = join(sub.figures_path, 'gfp', trial,
                             f'{sub.name}_{trial}_{sub.p_preset}-gfp{sub.img_format}')
            plt.savefig(save_path, dpi=600)
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_transformation(sub):
    info = sub.load_info()
    trans = sub.load_transformation()

    mne.viz.plot_alignment(info, trans, sub.subtomri, sub.subjects_dir,
                           surfaces=['head-dense', 'inner_skull', 'brain'],
                           show_axes=True, dig=True)

    mlab.view(45, 90, distance=0.6, focalpoint=(0., 0., 0.025))

    if sub.save_plots:
        save_path = join(sub.figures_path, 'transformation', f'{sub.name}_{sub.p_preset}-trans{sub.img_format}')
        mlab.savefig(save_path)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_source_space(mri_sub):
    source_space = mri_sub.load_source_space()
    source_space.plot()
    mlab.view(-90, 7)

    if mri_sub.save_plots:
        save_path = join(mri_sub.figures_path, 'source_space',
                         f'{mri_sub.name}_{mri_sub.p_preset}-source_space{mri_sub.img_format}')
        mlab.savefig(save_path)
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_bem(mri_sub):
    source_space = mri_sub.load_source_space()
    fig1 = mne.viz.plot_bem(mri_sub.name, mri_sub.subjects_dir, src=source_space)
    if mri_sub.save_plots:
        save_path1 = join(mri_sub.figures_path, 'bem',
                          f'{mri_sub.name}_{mri_sub.p_preset}-bem{mri_sub.img_format}')
        fig1.savefig(save_path1, dpi=600)
        print('figure: ' + save_path1 + ' has been saved')

    try:
        vol_src = mri_sub.load_vol_source_space()
        fig2 = mne.viz.plot_bem(mri_sub.name, mri_sub.subjects_dir, src=vol_src)
        if mri_sub.save_plots:
            save_path2 = join(mri_sub.figures_path, 'bem',
                              f'{mri_sub.name}_{mri_sub.p_preset}-vol_bem{mri_sub.img_format}')
            fig2.savefig(save_path2, dpi=600)
            print('figure: ' + save_path2 + ' has been saved')
    except FileNotFoundError:
        pass


@topline
def plot_sensitivity_maps(sub, ch_types):
    fwd = sub.load_forward()

    for ch_type in ch_types:
        sens_map = mne.sensitivity_map(fwd, ch_type=ch_type, mode='fixed')
        brain = sens_map.plot(title=f'{ch_type}-Sensitivity for {sub.name}', subjects_dir=sub.subjects_dir,
                              clim=dict(lims=[0, 50, 100]))

        if sub.save_plots:
            save_path = join(sub.figures_path, 'sensitivity_maps',
                             f'{sub.name}_{sub.p_preset}_{ch_type}-sensitivity_map{sub.img_format}')
            brain.save_image(save_path)


@topline
def plot_noise_covariance(sub):
    noise_covariance = sub.load_noise_covariance()
    info = sub.load_info()

    fig_cov = noise_covariance.plot(info, show_svd=False)

    if sub.save_plots:
        save_path = join(sub.figures_path, 'noise_covariance', f'{sub.name}_{sub.p_preset}-noise_cov{sub.img_format}')
        fig_cov[0].savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "sub.save_plots" to "True" to save')


# Todo: Bug with interactive-mode
@topline
def plot_stc(sub, stc_interactive, mne_evoked_time):
    stcs = sub.load_source_estimates()
    for trial in stcs:
        stc = stcs[trial]
        if stc_interactive:
            stc.plot(subject=sub.subtomri, surface='inflated', subjects_dir=sub.subjects_dir,
                     time_viewer=True, hemi='split', views='lat',
                     title=f'{sub.name}-{trial}', size=(1600, 800))
        else:
            for idx, t in enumerate(mne_evoked_time):
                figures_list = [mlab.figure(figure=idx * 2, size=(800, 800)),
                                mlab.figure(figure=idx * 2 + 1, size=(800, 800))]

                brain = stc.plot(subject=sub.subtomri, surface='inflated', subjects_dir=sub.subjects_dir,
                                 time_viewer=False, hemi='split', views='lat', initial_time=t,
                                 title=f'{sub.name}-{trial}', size=(1600, 800), figure=figures_list)
                brain.title = f'{sub.name}-{trial}'

                if sub.save_plots:
                    save_path = join(sub.figures_path, 'stcs', trial,
                                     f'{sub.name}_{sub.p_preset}-stc{str(idx)}{sub.img_format}')
                    brain.save_image(save_path)
                    print('figure: ' + save_path + ' has been saved')

                else:
                    print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_mixn(sub, mne_evoked_time, stc_interactive, parcellation):
    trans = sub.load_transformation()
    dipole_dict = sub.load_mxn_dipoles()
    for trial in dipole_dict:
        dipoles = dipole_dict[trial]
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
        if sub.save_plots:
            save_path = join(sub.figures_path, 'mxn_dipoles', trial,
                             f'{sub.name}_{trial}_{sub.p_preset}-mixn_dip{sub.img_format}')
            fig1.savefig(save_path)

        for idx, dipole in enumerate(dipoles):
            # Assumption right in Head Coordinates?
            if dipole.pos[0, 0] < 0:
                side = 'left'
                hemi = 'lh'
            else:
                side = 'right'
                hemi = 'rh'
            fig2 = mne.viz.plot_dipole_locations(dipole, trans=trans, subject=sub.subtomri,
                                                 subjects_dir=sub.subjects_dir, coord_frame='mri')
            fig2.suptitle(f'Dipole {idx + 1} {side}', fontsize=16)
            if sub.save_plots:
                save_path = join(sub.figures_path, 'mxn_dipoles', trial,
                                 f'{sub.name}_{trial}_{sub.p_preset}-mixn_dip{str(idx)}{sub.img_format}')

                fig2.savefig(save_path)

            brain = Brain(sub.subtomri, hemi=hemi, surf='pial', views='lat')
            dip_loc = mne.head_to_mri(dipole.pos, sub.subtomri, trans, subjects_dir=sub.subjects_dir)
            brain.add_foci(dip_loc[0])
            brain.add_annotation(parcellation)
            # Todo: Comparision with label
            if sub.save_plots:
                save_path = join(sub.figures_path, 'mxn_dipoles', trial,
                                 f'{sub.name}_{trial}_{sub.p_preset}-mixn_srfdip{str(idx)}{sub.img_format}')
                brain.save_image(save_path)

    plot_mixn_stc(sub, mne_evoked_time, stc_interactive)


def plot_mixn_stc(sub, mne_evoked_time, stc_interactive):
    stcs = sub.load_mixn_source_estimates()
    for trial in stcs:
        for idx, t in enumerate(mne_evoked_time):
            stc = stcs[trial]
            figures_list = [mlab.figure(figure=idx * 2, size=(800, 800)),
                            mlab.figure(figure=idx * 2 + 1, size=(800, 800))]
            if stc_interactive:
                brain = stc.plot(subject=sub.subtomri, surface='inflated', subjects_dir=sub.subjects_dir,
                                 time_viewer=True, hemi='split', views='lat', initial_time=t,
                                 title=f'{sub.name}-{trial}_mixn', size=(1600, 800), figure=figures_list)
            else:
                brain = stc.plot(subject=sub.subtomri, surface='inflated', subjects_dir=sub.subjects_dir,
                                 time_viewer=False, hemi='split', views='lat', initial_time=t,
                                 title=f'{sub.name}-{trial}_mixn', size=(1600, 800), figure=figures_list)
            brain.title = f'{sub.name}-{trial}_mixn'
            if sub.save_plots:
                save_path = join(sub.figures_path, 'mxne', trial,
                                 f'{sub.name}_{trial}_{sub.p_preset}-mixn{str(idx)}{sub.img_format}')
                brain.save_image(save_path)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "sub.save_plots" to "True" to save')

        if not stc_interactive:
            close_all()


@topline
def plot_animated_stc(sub, stc_animation):
    stcs = sub.load_source_estimates()

    for trial in stcs:
        n_stc = stcs[trial]

        save_path = join(sub.figures_path, 'stcs_movie', trial,
                         f'{sub.name}_{trial}_{sub.p_preset}-stc_movie.mp4')

        brain = mne.viz.plot_source_estimates(stc=n_stc, subject=sub.subtomri, surface='inflated',
                                              subjects_dir=sub.subjects_dir, size=(1600, 800),
                                              hemi='split', views='lat',
                                              title=sub.name + '_movie')

        print('Saving Video')
        brain.save_movie(save_path, time_dilation=10, tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
        mlab.close()


@topline
def plot_ecd(sub):
    ecd_dips = sub.load_ecd()
    trans = sub.load_transformation()

    for trial in ecd_dips:
        for dipole in ecd_dips[trial]:
            figure = dipole.plot_locations(trans, sub.subtomri, sub.pr.subjects_dir,
                                           mode='orthoview', idx='gof')
            plt.title(sub.name, loc='right')

            save_path = join(sub.sub.figures_path, 'ECD', trial,
                             f'{sub.name}_{trial}_{sub.p_preset}_{dipole}_ECD_anat{sub.img_format}')
            figure.savefig(save_path, dpi=600)

            # find time point with highest GOF to plot
            best_idx = np.argmax(dipole.gof)
            best_time = dipole.times[best_idx]

            print(f'Highest GOF {dipole.gof[best_idx]:.2f}% at t={best_time * 1000:.1f} ms with confidence volume'
                  f'{dipole.conf["vol"][best_idx] * 100 ** 3} cm^3')

            mri_pos = mne.head_to_mri(dipole.pos, sub.subtomri, trans, sub.pr.subjects_dir)

            save_path_anat = join(sub.sub.figures_path, 'ECD', trial,
                                  f'{sub.name}_{trial}_{sub.pr.p_preset}_{dipole}-ECD_anat{sub.img_format}')
            t1_path = join(sub.subjects_dir, sub.subtomri, 'mri', 'T1.mgz')
            plot_anat(t1_path, cut_coords=mri_pos[best_idx], output_file=save_path_anat,
                      annotate=True, draw_cross=True)

            plot_anat(t1_path, cut_coords=mri_pos[best_idx],
                      title=f'{sub.name}_{trial}_{dipole}',
                      annotate=True, draw_cross=True)


@topline
def plot_snr(sub):
    evokeds = sub.load_evokeds()
    inv = sub.load_inverse_operator()

    for evoked in evokeds:
        trial = evoked.comment
        # data snr
        figure = mne.viz.plot_snr_estimate(evoked, inv)
        plt.title(f'{sub.name}-{evoked.comment}', loc='center')

        if sub.save_plots:
            save_path = join(sub.figures_path, 'snr', trial,
                             f'{sub.name}_{trial}_{sub.pr.p_preset}-snr{sub.img_format}')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_labels(mri_sub, parcellation):
    brain = Brain(mri_sub.name, hemi='lh', surf='inflated', views='lat')

    brain.add_annotation(parcellation)

    if mri_sub.save_plots:
        save_path = join(mri_sub.figures_path, 'labels',
                         f'{mri_sub.name}_{mri_sub.pr.p_preset}-labels{mri_sub.img_format}')
        mlab.savefig(save_path, figure=mlab.gcf())
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_label_time_course(sub, target_labels, parcellation):
    stcs = sub.load_source_estimates()

    src = sub.mri_sub.load_source_space()

    labels = mne.read_labels_from_annot(sub.subtomri,
                                        subjects_dir=sub.subjects_dir,
                                        parc=parcellation)

    # Annotation Parameters
    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    arrowprops = dict(arrowstyle="->")
    kw = dict(xycoords='data', arrowprops=arrowprops, bbox=bbox_props)
    for trial in stcs:
        stc = stcs[trial]
        for hemi in target_labels:
            for lbl in labels:
                if lbl.name in target_labels[hemi]:
                    print(lbl.name)

                    stc_label = stc.in_label(lbl)
                    gfp = op.calculate_gfp(stc)
                    mean = stc.extract_label_time_course(lbl, src, mode='mean')
                    mean_flip = stc.extract_label_time_course(lbl, src, mode='mean_flip')
                    pca = stc.extract_label_time_course(lbl, src, mode='pca_flip')

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
                    plt.title(f'Activations in Label :{lbl.name}-{trial}')
                    plt.show()

                    if sub.save_plots:
                        save_path = join(sub.figures_path, 'label_time_course', trial,
                                         f'{sub.name}_{trial}_{sub.pr.p_preset}-{lbl.name}{sub.img_format}')
                        plt.savefig(save_path, dpi=600)
                        print('figure: ' + save_path + ' has been saved')
                    else:
                        print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_source_space_connectivity(sub, target_labels, con_fmin, con_fmax):
    con_dict = sub.load_connectivity()
    labels = sub.mri_sub.load_parc_labels()

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
    for trial in con_dict:
        for con_method in con_dict[trial]:
            fig, axes = mne.viz.plot_connectivity_circle(con_dict[trial][con_method], label_names, n_lines=300,
                                                         node_angles=node_angles, node_colors=label_colors,
                                                         title=f'{con_method}: {str(con_fmin)}-{str(con_fmax)}',
                                                         fontsize_names=12)
            if sub.save_plots:
                save_path = join(sub.figures_path, 'tf_source_space/connectivity',
                                 f'{sub.name}_{trial}_{sub.pr.p_preset}-{con_method}{sub.img_format}')
                fig.savefig(save_path, dpi=600, facecolor='k', edgecolor='k')
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "sub.save_plots" to "True" to save')


# %% Grand-Average Plots
@topline
def plot_grand_avg_evokeds(ga_group):
    ga_dict = ga_group.lad_ga_evokeds()

    for trial in ga_dict:
        figure = ga_dict[trial].plot(window_title=f'{ga_group.name}-{trial}',
                                     spatial_colors=True, gfp=True)
        if ga_group.save_plots:
            save_path = join(ga_group.figures_path, 'grand_averages/sensor_space/evoked',
                             f'{ga_group.name}_{trial}_{ga_group.pr.p_preset}-ga_evokeds{ga_group.img_format}')
            figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_grand_avg_tfr(ga_group, baseline, t_epoch):
    ga_dict = ga_group.load_ga_tfr()

    for trial in ga_dict:
        power = ga_dict[trial]
        fig1 = power.plot(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                          tmax=t_epoch[1], title=f'{trial}')
        fig2 = power.plot_topo(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                               tmax=t_epoch[1], title=f'{trial}')
        fig3 = power.plot_joint(baseline=baseline, mode='mean', tmin=t_epoch[0],
                                tmax=t_epoch[1], title=f'{trial}')

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
        plt.title(f'{trial}')
        plt.show()

        if ga_group.save_plots:
            save_path1 = join(ga_group.figures_path, 'grand_averages/sensor_space/tfr',
                              f'{ga_group.name}_{trial}_{ga_group.pr.p_preset}-tf{ga_group.img_format}')
            fig1.savefig(save_path1, dpi=600)
            print('figure: ' + save_path1 + ' has been saved')
            save_path2 = join(ga_group.figures_path, 'grand_averages/sensor_space/tfr',
                              f'{ga_group.name}_{trial}_{ga_group.pr.p_preset}-tf_topo{ga_group.img_format}')
            fig2.savefig(save_path2, dpi=600)
            print('figure: ' + save_path2 + ' has been saved')
            save_path3 = join(ga_group.figures_path, 'grand_averages/sensor_space/tfr',
                              f'{ga_group.name}_{trial}_{ga_group.pr.p_preset}-tf_joint{ga_group.img_format}')
            fig3.savefig(save_path3, dpi=600)
            print('figure: ' + save_path3 + ' has been saved')
            save_path4 = join(ga_group.figures_path, 'grand_averages/sensor_space/tfr',
                              f'{ga_group.name}_{trial}_{ga_group.pr.p_preset}-tf_oscs{ga_group.img_format}')
            fig4.savefig(save_path4, dpi=600)
            print('figure: ' + save_path4 + ' has been saved')
        else:
            print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_grand_avg_stc(ga_group, morph_to, mne_evoked_time, stc_interactive):
    ga_dict = ga_group.load_ga_source_estimate()

    for trial in ga_dict:
        if stc_interactive:
            ga_dict[trial](subject=ga_group.subtomri, surface='inflated',
                           subjects_dir=ga_group.subjects_dir,
                           time_viewer=True, hemi='split', views='lat',
                           title=f'{ga_group.name}-{trial}', size=(1600, 800))
        else:
            for idx, t in enumerate(mne_evoked_time):
                brain = ga_dict[trial].plot(subject=morph_to,
                                            subjects_dir=ga_group.subjects_dir, size=(1600, 800),
                                            title=f'{ga_group.name}-{trial}', hemi='split',
                                            views='lat', initial_time=t)

                if ga_group.save_plots:
                    save_path = join(ga_group.figures_path, 'grand_averages/source_space/stc',
                                     f'{ga_group.name}_{trial}_{ga_group.pr.p_preset}'
                                     f'-ga_stc{str(idx)}{ga_group.img_format}')
                    brain.save_image(save_path)
                    print('figure: ' + save_path + ' has been saved')

                else:
                    print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def plot_grand_avg_stc_anim(ga_group, stc_animation, morph_to):
    ga_dict = ga_group.load_ga_source_estimate()

    for trial in ga_dict:
        brain = ga_dict[trial].plot(subject=morph_to,
                                    subjects_dir=ga_group.subjects_dir, size=(1600, 800),
                                    title=f'{ga_group.name}-{trial}', hemi='split',
                                    views='lat')
        brain.title = f'{ga_group.name}-{trial}'

        print('Saving Video')
        save_path = join(ga_group.figures_path, 'grand_averages/source_space/stc_movie',
                         f'{ga_group.name}_{trial}_{ga_group.pr.p_preset}-stc_movie.mp4')
        brain.save_movie(save_path, time_dilation=30,
                         tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
        mlab.close()


@topline
def plot_grand_avg_connect(ga_group, con_fmin, con_fmax, parcellation, target_labels, morph_to):
    ga_dict = ga_group.load_ga_connect()

    # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
    labels_parc = mne.read_labels_from_annot(morph_to, parc=parcellation,
                                             subjects_dir=ga_group.subjects_dir)

    labels = [labl for labl in labels_parc if labl.name in target_labels['lh']
              or labl.name in target_labels['rh']]

    label_colors = [label.color for label in labels]
    for labl in labels:
        if labl.name == 'unknown-lh':
            del labels[labels.index(labl)]
            print('unknown-lh removed')

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

    for trial in ga_dict:
        for method in ga_dict[trial]:
            fig, axes = mne.viz.plot_connectivity_circle(ga_dict[trial][method],
                                                         label_names, n_lines=300,
                                                         node_angles=node_angles,
                                                         node_colors=label_colors,
                                                         title=f'{method}: {str(con_fmin)}-{str(con_fmax)}',
                                                         fontsize_names=16)
            if ga_group.save_plots:
                save_path = join(ga_group.figures_path, 'grand_averages/source_space/connectivity',
                                 f'{ga_group.name}_{trial}_{ga_group.pr.p_preset}-{method}{ga_group.img_format}')
                fig.savefig(save_path, dpi=600, facecolor='k', edgecolor='k')
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "sub.save_plots" to "True" to save')


@topline
def close_all():
    plt.close('all')
    mlab.close(all=True)
    gc.collect()
