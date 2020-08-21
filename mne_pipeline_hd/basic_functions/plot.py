# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
from __future__ import print_function

import gc
from os import makedirs
from os.path import isdir, join
from pathlib import Path

import matplotlib.pyplot as plt
import mne
import numpy as np
from mayavi import mlab
from nilearn.plotting import plot_anat
from surfer import Brain

from . import operations as op
from ..pipeline_functions.decorators import topline


def plot_save(sub, plot_name, subfolder=None, trial=None, idx=None, matplotlib_figure=None, mayavi=False,
              mayavi_figure=None, brain=None, dpi=None):
    # Take DPI from Settings if not defined by call
    if not dpi:
        dpi = sub.dpi

    # Todo: Move all possible settings to home-dict (settings-capabilities, e.g boolean, different between os)
    if sub.save_plots and sub.save_plots != 'false':
        # Folder is named by plot_name
        dir_path = join(sub.figures_path, plot_name)

        # Create Subfolder if necessary
        if subfolder:
            dir_path = join(dir_path, subfolder)

        # Create Subfolder for trial if necessary
        if trial:
            dir_path = join(dir_path, trial)

        # Create not existent folders
        if not isdir(dir_path):
            makedirs(dir_path)

        if subfolder and trial and idx:
            file_name = f'{sub.name}-{trial}_{sub.p_preset}_{plot_name}-{subfolder}-{idx}{sub.img_format}'
        elif subfolder and trial:
            file_name = f'{sub.name}-{trial}_{sub.p_preset}_{plot_name}-{subfolder}{sub.img_format}'
        elif trial and idx:
            file_name = f'{sub.name}-{trial}_{sub.p_preset}_{plot_name}-{idx}{sub.img_format}'
        elif trial:
            file_name = f'{sub.name}-{trial}_{sub.p_preset}_{plot_name}{sub.img_format}'
        elif idx:
            file_name = f'{sub.name}_{sub.p_preset}_{plot_name}-{idx}{sub.img_format}'
        else:
            file_name = f'{sub.name}_{sub.p_preset}_{plot_name}{sub.img_format}'

        save_path = join(dir_path, file_name)

        if matplotlib_figure:
            matplotlib_figure.savefig(save_path, dpi=dpi)
        elif mayavi_figure:
            mayavi_figure.savefig(save_path)
        elif brain:
            brain.save_image(save_path)
        elif mayavi:
            mlab.savefig(save_path, figure=mlab.gcf())
        else:
            plt.savefig(save_path, dpi=dpi)

        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')


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
    # Make sure, that only events from event_id are displayed
    actual_event_id = {}
    for ev_id in [evid for evid in sub.p['event_id'] if sub.p['event_id'][evid] in np.unique(events[:, 2])]:
        actual_event_id.update({ev_id: sub.p['event_id'][ev_id]})

    actual_event_values = list(actual_event_id.values())
    events = events[np.isin(events[:, 2], actual_event_values)]

    fig = mne.viz.plot_events(events, event_id=actual_event_id)
    fig.suptitle(sub.name)

    plot_save(sub, 'events', matplotlib_figure=fig)


@topline
def plot_power_spectra(sub):
    raw = sub.load_filtered()
    picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False, eog=False, ecg=False,
                           exclude=sub.bad_channels)

    fig = raw.plot_psd(fmax=sub.p['lowpass'], picks=picks, n_jobs=1)
    fig.suptitle(sub.name)

    plot_save(sub, 'power_spectra', subfolder='raw', matplotlib_figure=fig)


@topline
def plot_power_spectra_epochs(sub):
    epochs = sub.load_epochs()

    for trial in epochs.event_id:
        fig = epochs[trial].plot_psd(fmax=sub.p['lowpass'], n_jobs=-1)
        fig.suptitle(sub.name + '-' + trial)
        plot_save(sub, 'power_spectra', subfolder='epochs', trial=trial, matplotlib_figure=fig)


@topline
def plot_power_spectra_topo(sub):
    epochs = sub.load_epochs()
    for trial in epochs.event_id:
        fig = epochs[trial].plot_psd_topomap(n_jobs=-1)
        fig.suptitle(sub.name + '-' + trial)
        plot_save(sub, 'power_spectra', subfolder='topo', trial=trial, matplotlib_figure=fig)


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
        fig4.suptitle(f'{sub.name}-{power.comment}')
        plt.show()

        plot_save(sub, 'time_frequency', subfolder='plot', trial=power.comment, matplotlib_figure=fig1)
        plot_save(sub, 'time_frequency', subfolder='topo', trial=power.comment, matplotlib_figure=fig2)
        plot_save(sub, 'time_frequency', subfolder='joint', trial=power.comment, matplotlib_figure=fig3)
        plot_save(sub, 'time_frequency', subfolder='osc', trial=power.comment, matplotlib_figure=fig4)
        for itc in itcs:
            fig5 = itc.plot_topo(title=f'{sub.name}-{itc.comment}-itc',
                                 vmin=0., vmax=1., cmap='Reds')
            plot_save(sub, 'time_frequency', subfolder='itc', trial=itc.comment, matplotlib_figure=fig5)


@topline
def plot_epochs(sub):
    epochs = sub.load_epochs()

    for trial in epochs.event_id:
        fig = mne.viz.plot_epochs(epochs[trial], title=sub.name)
        fig.suptitle(trial)


@topline
def plot_epochs_image(sub):
    epochs = sub.load_epochs()
    for trial in epochs.event_id:
        figures = mne.viz.plot_epochs_image(epochs[trial], title=sub.name + '_' + trial)

        for idx, fig in enumerate(figures):
            plot_save(sub, 'epochs', subfolder='image', trial=trial, idx=idx, matplotlib_figure=fig)


@topline
def plot_epochs_topo(sub):
    epochs = sub.load_epochs()
    for trial in epochs.event_id:
        fig = mne.viz.plot_topo_image_epochs(epochs, title=sub.name)

        plot_save(sub, 'epochs', subfolder='topo', trial=trial, matplotlib_figure=fig)


@topline
def plot_epochs_drop_log(sub):
    epochs = sub.load_epochs()
    fig = epochs.plot_drop_log(subject=sub.name)

    plot_save(sub, 'epochs', subfolder='drop_log', matplotlib_figure=fig)


@topline
def plot_autoreject_log(sub):
    reject_log = sub.load_reject_log()
    epochs = sub.load_epochs()

    fig1 = reject_log.plot()
    plot_save(sub, 'epochs', subfolder='autoreject_log', idx='reject', matplotlib_figure=fig1)
    try:
        fig2 = reject_log.plot_epochs(epochs)
        plot_save(sub, 'epochs', subfolder='autoreject_log', idx='epochs', matplotlib_figure=fig2)
    except ValueError:
        print(f'{sub.name}: No epochs-plot for autoreject-log')


@topline
def plot_evoked_topo(sub):
    evokeds = sub.load_evokeds()
    fig = mne.viz.plot_evoked_topo(evokeds, title=sub.name)

    plot_save(sub, 'evokeds', subfolder='topo', matplotlib_figure=fig, dpi=800)


@topline
def plot_evoked_topomap(sub):
    evokeds = sub.load_evokeds()
    for evoked in evokeds:
        fig = mne.viz.plot_evoked_topomap(evoked, times='auto',
                                          title=sub.name + '-' + evoked.comment)

        plot_save(sub, 'evokeds', subfolder='topomap', trial=evoked.comment, matplotlib_figure=fig)


@topline
def plot_evoked_joint(sub):
    evokeds = sub.load_evokeds()

    for evoked in evokeds:
        fig = mne.viz.plot_evoked_joint(evoked, times='peaks',
                                        title=sub.name + ' - ' + evoked.comment)

        plot_save(sub, 'evokeds', subfolder='joint', trial=evoked.comment, matplotlib_figure=fig)


@topline
def plot_evoked_butterfly(sub):
    evokeds = sub.load_evokeds()

    for evoked in evokeds:
        fig = evoked.plot(spatial_colors=True,
                          window_title=sub.name + ' - ' + evoked.comment,
                          selectable=True, gfp=True, zorder='std')

        plot_save(sub, 'evokeds', subfolder='butterfly', trial=evoked.comment, matplotlib_figure=fig)


@topline
def plot_evoked_white(sub):
    evokeds = sub.load_evokeds()
    noise_covariance = sub.load_noise_covariance()

    for evoked in evokeds:
        # Check, if evokeds and noise covariance got the same channels
        channels = set(evoked.ch_names) & set(noise_covariance.ch_names)
        evoked.pick_channels(channels)

        fig = mne.viz.plot_evoked_white(evoked, noise_covariance)
        fig.suptitle(sub.name + ' - ' + evoked.comment, horizontalalignment='center')

        plot_save(sub, 'evokeds', subfolder='white', trial=evoked.comment, matplotlib_figure=fig)


@topline
def plot_evoked_image(sub):
    evokeds = sub.load_evokeds()

    for evoked in evokeds:
        fig = mne.viz.plot_evoked_image(evoked)
        fig.suptitle(sub.name + ' - ' + evoked.comment, horizontalalignment='center')

        plot_save(sub, 'evokeds', subfolder='image', trial=evoked.comment, matplotlib_figure=fig)


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

        plot_save(sub, 'evokeds', subfolder='gfp', trial=trial)


@topline
def plot_transformation(sub):
    info = sub.load_info()
    trans = sub.load_transformation()

    mne.viz.plot_alignment(info, trans, sub.subtomri, sub.subjects_dir,
                           surfaces=['head-dense', 'inner_skull', 'brain'],
                           show_axes=True, dig=True)

    mlab.view(45, 90, distance=0.6, focalpoint=(0., 0., 0.025))

    plot_save(sub, 'transformation', mayavi=True)


@topline
def plot_source_space(mri_sub):
    source_space = mri_sub.load_source_space()
    source_space.plot()
    mlab.view(-90, 7)

    plot_save(mri_sub, 'source_space', mayavi=True)


@topline
def plot_bem(mri_sub):
    source_space = mri_sub.load_source_space()
    fig1 = mne.viz.plot_bem(mri_sub.name, mri_sub.subjects_dir, src=source_space)

    plot_save(mri_sub, 'bem', subfolder='source-space', matplotlib_figure=fig1)

    try:
        vol_src = mri_sub.load_vol_source_space()
        fig2 = mne.viz.plot_bem(mri_sub.name, mri_sub.subjects_dir, src=vol_src)

        plot_save(mri_sub, 'bem', subfolder='volume-source-space', matplotlib_figure=fig2)

    except FileNotFoundError:
        pass


@topline
def plot_sensitivity_maps(sub, ch_types):
    fwd = sub.load_forward()

    for ch_type in ch_types:
        sens_map = mne.sensitivity_map(fwd, ch_type=ch_type, mode='fixed')
        brain = sens_map.plot(title=f'{ch_type}-Sensitivity for {sub.name}', subjects_dir=sub.subjects_dir,
                              clim=dict(lims=[0, 50, 100]))

        plot_save(sub, 'sensitivity', trial=ch_type, brain=brain)


@topline
def plot_noise_covariance(sub):
    noise_covariance = sub.load_noise_covariance()
    info = sub.load_info()

    fig1, fig2 = noise_covariance.plot(info, show_svd=False)

    plot_save(sub, 'noise-covariance', subfolder='covariance', matplotlib_figure=fig1)
    plot_save(sub, 'noise-covariance', subfolder='svd-spectra', matplotlib_figure=fig2)


def brain_plot(sub, stcs, folder_name, subject, mne_evoked_time):
    backend = mne.viz.get_3d_backend()
    for trial in stcs:
        stc = stcs[trial]
        file_patternlh = join(sub.figures_path, folder_name, trial,
                              f'{sub.name}-{trial}_{sub.p_preset}_lh-%s{sub.img_format}')
        file_patternrh = join(sub.figures_path, folder_name, trial,
                              f'{sub.name}-{trial}_{sub.p_preset}_rh-%s{sub.img_format}')
        # Check, if folder exists
        parent_path = Path(file_patternlh).parent
        if not isdir(parent_path):
            makedirs(parent_path)

        if backend == 'mayavi':
            brain = stc.plot(subject=subject, surface='inflated', subjects_dir=sub.subjects_dir,
                             hemi='lh', title=f'{sub.name}-{trial}-lh')
            brain.save_image_sequence(mne_evoked_time, fname_pattern=file_patternlh)
            brain = stc.plot(subject=subject, surface='inflated', subjects_dir=sub.subjects_dir,
                             hemi='rh', title=f'{sub.name}-{trial}-lh')
            brain.save_image_sequence(mne_evoked_time, fname_pattern=file_patternrh)

        else:
            stc.plot(subject=sub.subtomri, surface='inflated', subjects_dir=sub.subjects_dir,
                     hemi='split', title=f'{sub.name}-{trial}', size=(1200, 600),
                     initial_time=0)


@topline
def plot_stc(sub, mne_evoked_time):
    stcs = sub.load_source_estimates()
    brain_plot(sub, stcs, 'source-estimate', sub.subtomri, mne_evoked_time)


@topline
def plot_mixn(sub, mne_evoked_time, parcellation):
    trans = sub.load_transformation()
    dipole_dict = sub.load_mixn_dipoles()
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

        plot_save(sub, 'mixed-norm-estimate', subfolder='dipoles', trial=trial, matplotlib_figure=fig1)

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

            plot_save(sub, 'mixed-norm-estimate', subfolder='dipoles', trial=trial, idx=idx, matplotlib_figure=fig2)

            brain = Brain(sub.subtomri, hemi=hemi, surf='pial', views='lat')
            dip_loc = mne.head_to_mri(dipole.pos, sub.subtomri, trans, subjects_dir=sub.subjects_dir)
            brain.add_foci(dip_loc[0])
            brain.add_annotation(parcellation)
            # Todo: Comparision with label
            plot_save(sub, 'mixed-norm-estimate', subfolder='dipoles', trial=trial, idx=idx, brain=brain)

    stcs = sub.load_mixn_source_estimates()
    brain_plot(sub, stcs, 'mixed-norm-estimate/stc', sub.subtomri, mne_evoked_time)


@topline
def plot_animated_stc(sub, stc_animation, stc_animation_dilat):
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
        brain.save_movie(save_path, time_dilation=stc_animation_dilat,
                         tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
        mlab.close()


@topline
def plot_ecd(sub):
    ecd_dips = sub.load_ecd()
    trans = sub.load_transformation()

    for trial in ecd_dips:
        for dipole in ecd_dips[trial]:
            fig = dipole.plot_locations(trans, sub.subtomri, sub.subjects_dir,
                                        mode='orthoview', idx='gof')
            fig.suptitle(sub.name, horizontalalignment='right')

            plot_save(sub, 'ECD', subfolder=dipole, trial=trial, matplotlib_figure=fig)

            # find time point with highest GOF to plot
            best_idx = np.argmax(dipole.gof)
            best_time = dipole.times[best_idx]

            print(f'Highest GOF {dipole.gof[best_idx]:.2f}% at t={best_time * 1000:.1f} ms with confidence volume'
                  f'{dipole.conf["vol"][best_idx] * 100 ** 3} cm^3')

            mri_pos = mne.head_to_mri(dipole.pos, sub.subtomri, trans, sub.subjects_dir)

            save_path_anat = join(sub.sub.figures_path, 'ECD', dipole, trial,
                                  f'{sub.name}-{trial}_{sub.pr.p_preset}_ECD-{dipole}{sub.img_format}')
            t1_path = join(sub.subjects_dir, sub.subtomri, 'mri', 'T1.mgz')
            plot_anat(t1_path, cut_coords=mri_pos[best_idx], output_file=save_path_anat,
                      title=f'{sub.name}-{trial}_{dipole}',
                      annotate=True, draw_cross=True)

            plot_anat(t1_path, cut_coords=mri_pos[best_idx],
                      title=f'{sub.name}-{trial}_{dipole}',
                      annotate=True, draw_cross=True)


@topline
def plot_snr(sub):
    evokeds = sub.load_evokeds()
    inv = sub.load_inverse_operator()

    for evoked in evokeds:
        trial = evoked.comment
        # data snr
        fig = mne.viz.plot_snr_estimate(evoked, inv)
        fig.suptitle(f'{sub.name}-{evoked.comment}', horizontalalignment='center')

        plot_save(sub, 'snr', trial=trial, matplotlib_figure=fig)


@topline
def plot_annotation(mri_sub, parcellation):
    brain = Brain(mri_sub.name, hemi='lh', surf='inflated', views='lat')
    brain.add_annotation(parcellation)

    plot_save(mri_sub, 'Labels', brain=brain)


@topline
def plot_label_time_course(sub):
    ltcs = sub.load_ltc()
    for trial in ltcs:
        for label in ltcs[trial]:
            plt.figure()
            plt.plot(ltcs[trial][label][1], ltcs[trial][label][0])
            plt.title(f'{sub.name}-{trial}-{label}\n'
                      f'Extraction-Mode: {sub.p["extract_mode"]}')
            plt.xlabel('Time in s')
            plt.ylabel('Source amplitude')
            plt.show()

            plot_save(sub, 'label-time-course', subfolder=label, trial=trial)


@topline
def plot_source_space_connectivity(sub, target_labels, con_fmin, con_fmax):
    con_dict = sub.load_connectivity()
    labels = sub.mri_sub.load_parc_labels()

    actual_labels = [lb for lb in labels if lb.name in target_labels]

    label_colors = [label.color for label in actual_labels]

    # First, we reorder the labels based on their location in the left hemi
    label_names = [label.name for label in actual_labels]

    lh_label_names = [l_name for l_name in label_names if l_name.endswith('lh')]
    rh_label_names = [l_name for l_name in label_names if l_name.endswith('rh')]

    # Get the y-location of the label
    lh_label_ypos = list()
    for l_name in lh_label_names:
        idx = label_names.index(l_name)
        ypos = np.mean(actual_labels[idx].pos[:, 1])
        lh_label_ypos.append(ypos)

    rh_label_ypos = list()
    for l_name in rh_label_names:
        idx = label_names.index(l_name)
        ypos = np.mean(actual_labels[idx].pos[:, 1])
        rh_label_ypos.append(ypos)

    # Reorder the labels based on their location
    lh_labels = [label for (yp, label) in sorted(zip(lh_label_ypos, lh_label_names))]
    rh_labels = [label for (yp, label) in sorted(zip(rh_label_ypos, rh_label_names))]

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

            plot_save(sub, 'connectivity', subfolder=con_method, trial=trial, matplotlib_figure=fig)


# %% Grand-Average Plots
@topline
def plot_grand_avg_evokeds(ga_group):
    ga_evokeds = ga_group.load_ga_evokeds()

    for evoked in ga_evokeds:
        fig = evoked.plot(window_title=f'{ga_group.name}-{evoked.comment}',
                          spatial_colors=True, gfp=True)

        plot_save(ga_group, 'ga_evokeds', trial=evoked.comment, matplotlib_figure=fig)


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

        plot_save(ga_group, 'ga_tfr', subfolder='plot', trial=power.comment, matplotlib_figure=fig1)
        plot_save(ga_group, 'ga_tfr', subfolder='topo', trial=power.comment, matplotlib_figure=fig2)
        plot_save(ga_group, 'ga_tfr', subfolder='joint', trial=power.comment, matplotlib_figure=fig3)
        plot_save(ga_group, 'ga_tfr', subfolder='osc', trial=power.comment, matplotlib_figure=fig4)


@topline
def plot_grand_avg_stc(ga_group, morph_to, mne_evoked_time):
    ga_dict = ga_group.load_ga_source_estimate()
    brain_plot(ga_group, ga_dict, 'ga_source-estimate', morph_to, mne_evoked_time)


@topline
def plot_grand_avg_stc_anim(ga_group, stc_animation, stc_animation_dilat, morph_to):
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
        brain.save_movie(save_path, time_dilation=stc_animation_dilat,
                         tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
        mlab.close()


@topline
def plot_grand_avg_ltc(ga_group):
    ga_ltc = ga_group.load_ga_ltc()
    for trial in ga_ltc:
        for label in ga_ltc[trial]:
            plt.figure()
            plt.plot(ga_ltc[trial][label][1], ga_ltc[trial][label][0])
            plt.title(f'Label-Time-Course for {ga_group.name}-{trial}-{label}\n'
                      f'with Extraction-Mode: {ga_group.p["extract_mode"]}')
            plt.xlabel('Time in ms')
            plt.ylabel('Source amplitude')
            plt.show()

            plot_save(ga_group, 'ga_label-time-course', subfolder=label, trial=trial)


@topline
def plot_grand_avg_connect(ga_group, con_fmin, con_fmax, parcellation, target_labels, morph_to):
    ga_dict = ga_group.load_ga_connect()

    # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
    labels_parc = mne.read_labels_from_annot(morph_to, parc=parcellation,
                                             subjects_dir=ga_group.subjects_dir)

    labels = [labl for labl in labels_parc if labl.name in target_labels]

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

            plot_save(ga_group, 'ga_connectivity', subfolder=method, trial=trial, matplotlib_figure=fig)


@topline
def close_all():
    plt.close('all')
    mlab.close(all=True)
    gc.collect()
