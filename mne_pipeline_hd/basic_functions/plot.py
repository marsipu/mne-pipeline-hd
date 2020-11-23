# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
Copyright © 2011-2019, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
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


def plot_save(meeg, plot_name, subfolder=None, trial=None, idx=None, matplotlib_figure=None, mayavi=False,
              mayavi_figure=None, brain=None, dpi=None):
    # Take DPI from Settings if not defined by call
    if not dpi:
        dpi = meeg.dpi

    # Todo: Move all possible settings to home-dict (settings-capabilities, e.g boolean, different between os)
    if meeg.save_plots and meeg.save_plots != 'false':
        # Folder is named by plot_name
        dir_path = join(meeg.figures_path, plot_name)

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
            file_name = f'{meeg.name}-{trial}_{meeg.p_preset}_{plot_name}-{subfolder}-{idx}{meeg.img_format}'
        elif subfolder and trial:
            file_name = f'{meeg.name}-{trial}_{meeg.p_preset}_{plot_name}-{subfolder}{meeg.img_format}'
        elif trial and idx:
            file_name = f'{meeg.name}-{trial}_{meeg.p_preset}_{plot_name}-{idx}{meeg.img_format}'
        elif trial:
            file_name = f'{meeg.name}-{trial}_{meeg.p_preset}_{plot_name}{meeg.img_format}'
        elif idx:
            file_name = f'{meeg.name}_{meeg.p_preset}_{plot_name}-{idx}{meeg.img_format}'
        else:
            file_name = f'{meeg.name}_{meeg.p_preset}_{plot_name}{meeg.img_format}'

        save_path = join(dir_path, file_name)

        if matplotlib_figure:
            if isinstance(matplotlib_figure, list):
                for idx, figure in enumerate(matplotlib_figure):
                    figure.savefig(join(dir_path, f'{idx}_' + file_name))
            else:
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

def plot_raw(meeg):
    raw = meeg.load_raw()

    try:
        events = meeg.load_events()
    except FileNotFoundError:
        events = None
        print('No events found')

    raw.plot(events=events, n_channels=30, bad_color='red',
             scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
             title=f'{meeg.name}')


def plot_filtered(meeg):
    raw = meeg.load_filtered()

    try:
        events = meeg.load_events()
    except FileNotFoundError:
        events = None
        print('No events found')

    raw.plot(events=events, n_channels=30, bad_color='red',
             scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
             title=f'{meeg.name}_highpass={meeg.p["highpass"]}_lowpass={meeg.p["lowpass"]}')


def plot_sensors(meeg):
    loaded_info = meeg.load_info()
    mne.viz.plot_sensors(loaded_info, kind='topomap', title=meeg.name, show_names=True, ch_groups='position')


def plot_events(meeg):
    events = meeg.load_events()

    fig = mne.viz.plot_events(events, event_id=meeg.event_id)
    fig.suptitle(meeg.name)

    plot_save(meeg, 'events', matplotlib_figure=fig)


def plot_power_spectra(meeg):
    raw = meeg.load_filtered()
    picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False, eog=False, ecg=False,
                           exclude=meeg.bad_channels)

    fig = raw.plot_psd(fmax=meeg.p['lowpass'], picks=picks, n_jobs=1)
    fig.suptitle(meeg.name)

    plot_save(meeg, 'power_spectra', subfolder='raw', matplotlib_figure=fig)


def plot_power_spectra_epochs(meeg):
    epochs = meeg.load_epochs()

    for trial in meeg.sel_trials:
        fig = epochs[trial].plot_psd(fmax=meeg.p['lowpass'], n_jobs=-1)
        fig.suptitle(meeg.name + '-' + trial)
        plot_save(meeg, 'power_spectra', subfolder='epochs', trial=trial, matplotlib_figure=fig)


def plot_power_spectra_topo(meeg):
    epochs = meeg.load_epochs()
    for trial in meeg.sel_trials:
        fig = epochs[trial].plot_psd_topomap(n_jobs=-1)
        fig.suptitle(meeg.name + '-' + trial)
        plot_save(meeg, 'power_spectra', subfolder='topo', trial=trial, matplotlib_figure=fig)


def plot_tfr(meeg, t_epoch, baseline):
    powers = meeg.load_power_tfr()
    itcs = meeg.load_itc_tfr()

    for power in powers:
        fig1 = power.plot(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                          tmax=t_epoch[1], title=f'{meeg.name}-{power.comment}')
        fig2 = power.plot_topo(baseline=baseline, mode='logratio', tmin=t_epoch[0],
                               tmax=t_epoch[1], title=f'{meeg.name}-{power.comment}')
        fig3 = power.plot_joint(baseline=baseline, mode='mean', tmin=t_epoch[0],
                                tmax=t_epoch[1], title=f'{meeg.name}-{power.comment}')

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
        fig4.suptitle(f'{meeg.name}-{power.comment}')
        plt.show()

        plot_save(meeg, 'time_frequency', subfolder='plot', trial=power.comment, matplotlib_figure=fig1)
        plot_save(meeg, 'time_frequency', subfolder='topo', trial=power.comment, matplotlib_figure=fig2)
        plot_save(meeg, 'time_frequency', subfolder='joint', trial=power.comment, matplotlib_figure=fig3)
        plot_save(meeg, 'time_frequency', subfolder='osc', trial=power.comment, matplotlib_figure=fig4)
        for itc in itcs:
            fig5 = itc.plot_topo(title=f'{meeg.name}-{itc.comment}-itc',
                                 vmin=0., vmax=1., cmap='Reds')
            plot_save(meeg, 'time_frequency', subfolder='itc', trial=itc.comment, matplotlib_figure=fig5)


def plot_epochs(meeg):
    epochs = meeg.load_epochs()

    for trial in meeg.sel_trials:
        fig = mne.viz.plot_epochs(epochs[trial], title=meeg.name)
        fig.suptitle(trial)


def plot_epochs_image(meeg):
    epochs = meeg.load_epochs()
    for trial in meeg.sel_trials:
        figures = mne.viz.plot_epochs_image(epochs[trial], title=meeg.name + '_' + trial)

        for idx, fig in enumerate(figures):
            plot_save(meeg, 'epochs', subfolder='image', trial=trial, idx=idx, matplotlib_figure=fig)


def plot_epochs_topo(meeg):
    epochs = meeg.load_epochs()
    for trial in meeg.sel_trials:
        fig = mne.viz.plot_topo_image_epochs(epochs, title=meeg.name)

        plot_save(meeg, 'epochs', subfolder='topo', trial=trial, matplotlib_figure=fig)


def plot_epochs_drop_log(meeg):
    epochs = meeg.load_epochs()
    fig = epochs.plot_drop_log(subject=meeg.name)

    plot_save(meeg, 'epochs', subfolder='drop_log', matplotlib_figure=fig)


def plot_autoreject_log(meeg):
    reject_log = meeg.load_reject_log()
    epochs = meeg.load_epochs()

    fig1 = reject_log.plot()
    plot_save(meeg, 'epochs', subfolder='autoreject_log', idx='reject', matplotlib_figure=fig1)
    try:
        fig2 = reject_log.plot_epochs(epochs)
        plot_save(meeg, 'epochs', subfolder='autoreject_log', idx='epochs', matplotlib_figure=fig2)
    except ValueError:
        print(f'{meeg.name}: No epochs-plot for autoreject-log')


def plot_evoked_topo(meeg):
    evokeds = meeg.load_evokeds()
    fig = mne.viz.plot_evoked_topo(evokeds, title=meeg.name)

    plot_save(meeg, 'evokeds', subfolder='topo', matplotlib_figure=fig, dpi=800)


def plot_evoked_topomap(meeg):
    evokeds = meeg.load_evokeds()
    for evoked in evokeds:
        fig = mne.viz.plot_evoked_topomap(evoked, times='auto',
                                          title=meeg.name + '-' + evoked.comment)

        plot_save(meeg, 'evokeds', subfolder='topomap', trial=evoked.comment, matplotlib_figure=fig)


def plot_evoked_joint(meeg):
    evokeds = meeg.load_evokeds()

    for evoked in evokeds:
        fig = mne.viz.plot_evoked_joint(evoked, times='peaks',
                                        title=meeg.name + ' - ' + evoked.comment)

        plot_save(meeg, 'evokeds', subfolder='joint', trial=evoked.comment, matplotlib_figure=fig)


def plot_evoked_butterfly(meeg):
    evokeds = meeg.load_evokeds()
    titles_dict = {'eeg': f'{meeg.name} - EEG'}
    for evoked in evokeds:
        fig = evoked.plot(spatial_colors=True, titles=titles_dict,
                          window_title=meeg.name + ' - ' + evoked.comment,
                          selectable=True, gfp=True, zorder='std')

        plot_save(meeg, 'evokeds', subfolder='butterfly', trial=evoked.comment, matplotlib_figure=fig)


def plot_evoked_white(meeg):
    evokeds = meeg.load_evokeds()
    noise_covariance = meeg.load_noise_covariance()

    for evoked in evokeds:
        # Check, if evokeds and noise covariance got the same channels
        channels = set(evoked.ch_names) & set(noise_covariance.ch_names)
        evoked.pick_channels(channels)

        fig = mne.viz.plot_evoked_white(evoked, noise_covariance)
        fig.suptitle(meeg.name + ' - ' + evoked.comment, horizontalalignment='center')

        plot_save(meeg, 'evokeds', subfolder='white', trial=evoked.comment, matplotlib_figure=fig)


def plot_evoked_image(meeg):
    evokeds = meeg.load_evokeds()

    for evoked in evokeds:
        fig = mne.viz.plot_evoked_image(evoked)
        fig.suptitle(meeg.name + ' - ' + evoked.comment, horizontalalignment='center')

        plot_save(meeg, 'evokeds', subfolder='image', trial=evoked.comment, matplotlib_figure=fig)


def plot_gfp(meeg):
    evokeds = meeg.load_evokeds()
    for evoked in evokeds:
        gfp = op.calculate_gfp(evoked)
        t = evoked.times
        trial = evoked.comment
        plt.figure()
        plt.plot(t, gfp)
        plt.title(f'GFP of {meeg.name}-{trial}')
        plt.show()

        plot_save(meeg, 'evokeds', subfolder='gfp', trial=trial)


def plot_transformation(meeg):
    info = meeg.load_info()
    trans = meeg.load_transformation()

    mne.viz.plot_alignment(info, trans, meeg.fsmri, meeg.subjects_dir,
                           surfaces=['head-dense', 'inner_skull', 'brain'],
                           show_axes=True, dig=True)

    mlab.view(45, 90, distance=0.6, focalpoint=(0., 0., 0.025))

    plot_save(meeg, 'transformation', mayavi=True)


def plot_source_space(fsmri):
    source_space = fsmri.load_source_space()
    source_space.plot()
    mlab.view(-90, 7)

    plot_save(fsmri, 'source_space', mayavi=True)


def plot_bem(fsmri):
    source_space = fsmri.load_source_space()
    fig1 = mne.viz.plot_bem(fsmri.name, fsmri.subjects_dir, src=source_space)

    plot_save(fsmri, 'bem', subfolder='source-space', matplotlib_figure=fig1)

    try:
        vol_src = fsmri.load_vol_source_space()
        fig2 = mne.viz.plot_bem(fsmri.name, fsmri.subjects_dir, src=vol_src)

        plot_save(fsmri, 'bem', subfolder='volume-source-space', matplotlib_figure=fig2)

    except FileNotFoundError:
        pass


def plot_sensitivity_maps(meeg, ch_types):
    fwd = meeg.load_forward()

    for ch_type in [ct for ct in ch_types if ct in ['grad', 'mag', 'eeg']]:
        sens_map = mne.sensitivity_map(fwd, ch_type=ch_type, mode='fixed')
        brain = sens_map.plot(title=f'{ch_type}-Sensitivity for {meeg.name}', subjects_dir=meeg.subjects_dir,
                              clim=dict(lims=[0, 50, 100]))

        plot_save(meeg, 'sensitivity', trial=ch_type, brain=brain)


def plot_noise_covariance(meeg):
    noise_covariance = meeg.load_noise_covariance()
    info = meeg.load_info()

    fig1, fig2 = noise_covariance.plot(info, show_svd=False)

    plot_save(meeg, 'noise-covariance', subfolder='covariance', matplotlib_figure=fig1)
    plot_save(meeg, 'noise-covariance', subfolder='svd-spectra', matplotlib_figure=fig2)


def brain_plot(meeg, stcs, folder_name, subject, mne_evoked_time):
    backend = mne.viz.get_3d_backend()
    for trial in stcs:
        stc = stcs[trial]
        file_patternlh = join(meeg.figures_path, folder_name, trial,
                              f'{meeg.name}-{trial}_{meeg.p_preset}_lh-%s{meeg.img_format}')
        file_patternrh = join(meeg.figures_path, folder_name, trial,
                              f'{meeg.name}-{trial}_{meeg.p_preset}_rh-%s{meeg.img_format}')
        # Check, if folder exists
        parent_path = Path(file_patternlh).parent
        if not isdir(parent_path):
            makedirs(parent_path)

        if backend == 'mayavi':
            brain = stc.plot(subject=subject, surface='inflated', subjects_dir=meeg.subjects_dir,
                             hemi='lh', title=f'{meeg.name}-{trial}-lh')
            brain.save_image_sequence(mne_evoked_time, fname_pattern=file_patternlh)
            brain = stc.plot(subject=subject, surface='inflated', subjects_dir=meeg.subjects_dir,
                             hemi='rh', title=f'{meeg.name}-{trial}-lh')
            brain.save_image_sequence(mne_evoked_time, fname_pattern=file_patternrh)

        else:
            stc.plot(subject=meeg.fsmri, surface='inflated', subjects_dir=meeg.subjects_dir,
                     hemi='split', title=f'{meeg.name}-{trial}', size=(1200, 600),
                     initial_time=0)


def plot_stc(meeg, mne_evoked_time):
    stcs = meeg.load_source_estimates()
    brain_plot(meeg, stcs, 'source-estimate', meeg.fsmri, mne_evoked_time)


def plot_mixn(meeg, mne_evoked_time, parcellation):
    trans = meeg.load_transformation()
    dipole_dict = meeg.load_mixn_dipoles()
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

        plot_save(meeg, 'mixed-norm-estimate', subfolder='dipoles', trial=trial, matplotlib_figure=fig1)

        for idx, dipole in enumerate(dipoles):
            # Assumption right in Head Coordinates?
            if dipole.pos[0, 0] < 0:
                side = 'left'
                hemi = 'lh'
            else:
                side = 'right'
                hemi = 'rh'
            fig2 = mne.viz.plot_dipole_locations(dipole, trans=trans, subject=meeg.fsmri,
                                                 subjects_dir=meeg.subjects_dir, coord_frame='mri')
            fig2.suptitle(f'Dipole {idx + 1} {side}', fontsize=16)

            plot_save(meeg, 'mixed-norm-estimate', subfolder='dipoles', trial=trial, idx=idx, matplotlib_figure=fig2)

            brain = Brain(meeg.fsmri, hemi=hemi, surf='pial', views='lat')
            dip_loc = mne.head_to_mri(dipole.pos, meeg.fsmri, trans, subjects_dir=meeg.subjects_dir)
            brain.add_foci(dip_loc[0])
            brain.add_annotation(parcellation)
            # Todo: Comparision with label
            plot_save(meeg, 'mixed-norm-estimate', subfolder='dipoles', trial=trial, idx=idx, brain=brain)

    stcs = meeg.load_mixn_source_estimates()
    brain_plot(meeg, stcs, 'mixed-norm-estimate/stc', meeg.fsmri, mne_evoked_time)


def plot_animated_stc(meeg, stc_animation, stc_animation_dilat):
    stcs = meeg.load_source_estimates()

    for trial in stcs:
        n_stc = stcs[trial]

        save_path = join(meeg.figures_path, 'stcs_movie', trial,
                         f'{meeg.name}_{trial}_{meeg.p_preset}-stc_movie.mp4')

        brain = mne.viz.plot_source_estimates(stc=n_stc, subject=meeg.fsmri, surface='inflated',
                                              subjects_dir=meeg.subjects_dir, size=(1600, 800),
                                              hemi='split', views='lat',
                                              title=meeg.name + '_movie')

        print('Saving Video')
        brain.save_movie(save_path, time_dilation=stc_animation_dilat,
                         tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
        mlab.close()


def plot_ecd(meeg):
    ecd_dips = meeg.load_ecd()
    trans = meeg.load_transformation()

    for trial in ecd_dips:
        for dipole in ecd_dips[trial]:
            fig = dipole.plot_locations(trans, meeg.fsmri, meeg.subjects_dir,
                                        mode='orthoview', idx='gof')
            fig.suptitle(meeg.name, horizontalalignment='right')

            plot_save(meeg, 'ECD', subfolder=dipole, trial=trial, matplotlib_figure=fig)

            # find time point with highest GOF to plot
            best_idx = np.argmax(dipole.gof)
            best_time = dipole.times[best_idx]

            print(f'Highest GOF {dipole.gof[best_idx]:.2f}% at t={best_time * 1000:.1f} ms with confidence volume'
                  f'{dipole.conf["vol"][best_idx] * 100 ** 3} cm^3')

            mri_pos = mne.head_to_mri(dipole.pos, meeg.fsmri, trans, meeg.subjects_dir)

            save_path_anat = join(meeg.obj.figures_path, 'ECD', dipole, trial,
                                  f'{meeg.name}-{trial}_{meeg.pr.p_preset}_ECD-{dipole}{meeg.img_format}')
            t1_path = join(meeg.subjects_dir, meeg.fsmri, 'mri', 'T1.mgz')
            plot_anat(t1_path, cut_coords=mri_pos[best_idx], output_file=save_path_anat,
                      title=f'{meeg.name}-{trial}_{dipole}',
                      annotate=True, draw_cross=True)

            plot_anat(t1_path, cut_coords=mri_pos[best_idx],
                      title=f'{meeg.name}-{trial}_{dipole}',
                      annotate=True, draw_cross=True)


def plot_snr(meeg):
    evokeds = meeg.load_evokeds()
    inv = meeg.load_inverse_operator()

    for evoked in evokeds:
        trial = evoked.comment
        # data snr
        fig = mne.viz.plot_snr_estimate(evoked, inv)
        fig.suptitle(f'{meeg.name}-{evoked.comment}', horizontalalignment='center')

        plot_save(meeg, 'snr', trial=trial, matplotlib_figure=fig)


def plot_annotation(fsmri, parcellation):
    brain = Brain(fsmri.name, hemi='lh', surf='inflated', views='lat')
    brain.add_annotation(parcellation)

    plot_save(fsmri, 'Labels', brain=brain)


def plot_label_time_course(meeg):
    ltcs = meeg.load_ltc()
    for trial in ltcs:
        for label in ltcs[trial]:
            plt.figure()
            plt.plot(ltcs[trial][label][1], ltcs[trial][label][0])
            plt.title(f'{meeg.name}-{trial}-{label}\n'
                      f'Extraction-Mode: {meeg.p["extract_mode"]}')
            plt.xlabel('Time in s')
            plt.ylabel('Source amplitude')
            plt.show()

            plot_save(meeg, 'label-time-course', subfolder=label, trial=trial)


def plot_source_space_connectivity(meeg, target_labels, con_fmin, con_fmax):
    con_dict = meeg.load_connectivity()
    labels = meeg.fsmri.load_parc_labels()

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

            plot_save(meeg, 'connectivity', subfolder=con_method, trial=trial, matplotlib_figure=fig)


# %% Grand-Average Plots

def plot_grand_avg_evokeds(group):
    ga_evokeds = group.load_ga_evokeds()

    for evoked in ga_evokeds:
        fig = evoked.plot(window_title=f'{group.name}-{evoked.comment}',
                          spatial_colors=True, gfp=True)

        plot_save(group, 'ga_evokeds', trial=evoked.comment, matplotlib_figure=fig)


def plot_grand_avg_tfr(group, baseline, t_epoch):
    ga_dict = group.load_ga_tfr()

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

        plot_save(group, 'ga_tfr', subfolder='plot', trial=power.comment, matplotlib_figure=fig1)
        plot_save(group, 'ga_tfr', subfolder='topo', trial=power.comment, matplotlib_figure=fig2)
        plot_save(group, 'ga_tfr', subfolder='joint', trial=power.comment, matplotlib_figure=fig3)
        plot_save(group, 'ga_tfr', subfolder='osc', trial=power.comment, matplotlib_figure=fig4)


def plot_grand_avg_stc(group, morph_to, mne_evoked_time):
    ga_dict = group.load_ga_source_estimate()
    brain_plot(group, ga_dict, 'ga_source-estimate', morph_to, mne_evoked_time)


def plot_grand_avg_stc_anim(group, stc_animation, stc_animation_dilat, morph_to):
    ga_dict = group.load_ga_source_estimate()

    for trial in ga_dict:
        brain = ga_dict[trial].plot(subject=morph_to,
                                    subjects_dir=group.subjects_dir, size=(1600, 800),
                                    title=f'{group.name}-{trial}', hemi='split',
                                    views='lat')
        brain.title = f'{group.name}-{trial}'

        print('Saving Video')
        save_path = join(group.figures_path, 'grand_averages/source_space/stc_movie',
                         f'{group.name}_{trial}_{group.pr.p_preset}-stc_movie.mp4')
        brain.save_movie(save_path, time_dilation=stc_animation_dilat,
                         tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
        mlab.close()


def plot_grand_avg_ltc(group):
    ga_ltc = group.load_ga_ltc()
    for trial in ga_ltc:
        for label in ga_ltc[trial]:
            plt.figure()
            plt.plot(ga_ltc[trial][label][1], ga_ltc[trial][label][0])
            plt.title(f'Label-Time-Course for {group.name}-{trial}-{label}\n'
                      f'with Extraction-Mode: {group.p["extract_mode"]}')
            plt.xlabel('Time in ms')
            plt.ylabel('Source amplitude')
            plt.show()

            plot_save(group, 'ga_label-time-course', subfolder=label, trial=trial)


def plot_grand_avg_connect(group, con_fmin, con_fmax, parcellation, target_labels, morph_to):
    ga_dict = group.load_ga_connect()

    # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
    labels_parc = mne.read_labels_from_annot(morph_to, parc=parcellation,
                                             subjects_dir=group.subjects_dir)

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

            plot_save(group, 'ga_connectivity', subfolder=method, trial=trial, matplotlib_figure=fig)


def close_all():
    plt.close('all')
    mlab.close(all=True)
    gc.collect()
