# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2020, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
from __future__ import print_function

import gc
import multiprocessing
from os.path import join

import matplotlib.pyplot as plt
import mne
import mne_connectivity
import numpy as np

# Make use of program also possible with sensor-space installation of mne
try:
    from mayavi import mlab
    from nilearn.plotting import plot_anat
    from surfer import Brain
except (ModuleNotFoundError, ValueError):
    pass

from mne_pipeline_hd.basic_functions import operations as op


# ==============================================================================
# PLOTTING FUNCTIONS
# ==============================================================================

def plot_raw(meeg, show_plots):
    raw = meeg.load_raw()

    try:
        events = meeg.load_events()
    except FileNotFoundError:
        events = None
        print('No events found')

    raw.plot(events=events, n_channels=30, bad_color='red', scalings='auto', title=f'{meeg.name}', show=show_plots)


def plot_filtered(meeg, show_plots):
    raw = meeg.load_filtered()

    try:
        events = meeg.load_events()
    except FileNotFoundError:
        events = None
        print('No events found')

    raw.plot(events=events, n_channels=30, bad_color='red',
             scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1),
             title=f'{meeg.name}_highpass={meeg.pa["highpass"]}_lowpass={meeg.pa["lowpass"]}', show=show_plots)


def plot_sensors(meeg, plot_sensors_kind, ch_types, show_plots):
    loaded_info = meeg.load_info()
    if len(ch_types) > 1:
        ch_types = 'all'
    elif len(ch_types) == 1:
        ch_types = ch_types[0]
    else:
        ch_types = None
    mne.viz.plot_sensors(loaded_info, kind=plot_sensors_kind, ch_type=ch_types, title=meeg.name, show_names=True,
                         show=show_plots)


def plot_events(meeg, show_plots):
    events = meeg.load_events()

    fig = mne.viz.plot_events(events, event_id=meeg.event_id, show=show_plots)
    fig.suptitle(meeg.name)

    meeg.plot_save('events', matplotlib_figure=fig)


def plot_power_spectra(meeg, show_plots, n_jobs):
    raw = meeg.load_filtered()

    # Does not accept -1 for n_jobs
    if n_jobs == -1:
        n_jobs = multiprocessing.cpu_count()

    fig = raw.plot_psd(fmax=raw.info['lowpass'], show=show_plots, n_jobs=n_jobs)
    fig.suptitle(meeg.name)

    meeg.plot_save('power_spectra', subfolder='raw', matplotlib_figure=fig)


def plot_power_spectra_topo(meeg, show_plots, n_jobs):
    raw = meeg.load_filtered()

    # Does not accept -1 for n_jobs
    if n_jobs == -1:
        n_jobs = multiprocessing.cpu_count()

    fig = raw.plot_psd_topo(show=show_plots, n_jobs=n_jobs)

    meeg.plot_save('power_spectra', subfolder='raw_topo', matplotlib_figure=fig)


def plot_power_spectra_epochs(meeg, show_plots, n_jobs):
    epochs = meeg.load_epochs()

    # Does not accept -1 for n_jobs
    if n_jobs == -1:
        n_jobs = multiprocessing.cpu_count()

    for trial in meeg.sel_trials:
        fig = epochs[trial].plot_psd(show=show_plots, n_jobs=n_jobs)
        fig.suptitle(meeg.name + '-' + trial)
        meeg.plot_save('power_spectra', subfolder='epochs', trial=trial, matplotlib_figure=fig)


def plot_power_spectra_epochs_topo(meeg, show_plots, n_jobs):
    epochs = meeg.load_epochs()
    for trial in meeg.sel_trials:
        fig = epochs[trial].plot_psd_topomap(show=show_plots, n_jobs=n_jobs)
        fig.suptitle(meeg.name + '-' + trial)
        meeg.plot_save('power_spectra', subfolder='epochs_topo', trial=trial, matplotlib_figure=fig)


def plot_tfr(meeg, show_plots):
    powers = meeg.load_power_tfr_average()

    for power in powers:
        print('Plotting TFR')
        fig1 = power.plot(title=f'{meeg.name}-{power.comment}', combine='mean', show=show_plots)
        print('Plotting TFR-Topo')
        fig2 = power.plot_topo(title=f'{meeg.name}-{power.comment}', show=show_plots)
        print('Plotting TFR-Joint')
        fig3 = power.plot_joint(title=f'{meeg.name}-{power.comment}', show=show_plots)
        print('Plotting TFR-Topomap')
        fig4 = power.plot_topomap(title=f'{meeg.name}-{power.comment}', show=show_plots)

        meeg.plot_save('time_frequency', subfolder='plot', trial=power.comment, matplotlib_figure=fig1)
        meeg.plot_save('time_frequency', subfolder='topo', trial=power.comment, matplotlib_figure=fig2)
        meeg.plot_save('time_frequency', subfolder='joint', trial=power.comment, matplotlib_figure=fig3)
        meeg.plot_save('time_frequency', subfolder='topomap', trial=power.comment, matplotlib_figure=fig4)

    try:
        itcs = meeg.load_itc_tfr_average()
    except (FileNotFoundError, UnboundLocalError):
        print(f'{meeg.itc_tfr_average_path} not found!')
    else:
        for itc in itcs:
            fig5 = itc.plot_topo(title=f'{meeg.name}-{itc.comment}-itc',
                                 vmin=0., vmax=1., cmap='Reds', show=show_plots)
            meeg.plot_save('time_frequency', subfolder='itc', trial=itc.comment, matplotlib_figure=fig5)


def plot_epochs(meeg, show_plots):
    epochs = meeg.load_epochs()

    for trial in meeg.sel_trials:
        fig = mne.viz.plot_epochs(epochs[trial], title=meeg.name, show=show_plots)
        fig.suptitle(trial)


def plot_epochs_image(meeg, show_plots):
    epochs = meeg.load_epochs()
    for trial in meeg.sel_trials:
        figures = mne.viz.plot_epochs_image(epochs[trial], title=meeg.name + '_' + trial, show=show_plots)

        for idx, fig in enumerate(figures):
            meeg.plot_save('epochs', subfolder='image', trial=trial, idx=idx, matplotlib_figure=fig)


def plot_epochs_topo(meeg, show_plots):
    epochs = meeg.load_epochs()
    for trial in meeg.sel_trials:
        fig = mne.viz.plot_topo_image_epochs(epochs, title=meeg.name, show=show_plots)

        meeg.plot_save('epochs', subfolder='topo', trial=trial, matplotlib_figure=fig)


def plot_epochs_drop_log(meeg, show_plots):
    epochs = meeg.load_epochs()
    fig = epochs.plot_drop_log(subject=meeg.name, show=show_plots)

    meeg.plot_save('epochs', subfolder='drop_log', matplotlib_figure=fig)


def plot_autoreject_log(meeg, show_plots):
    reject_log = meeg.load_reject_log()
    epochs = meeg.load_epochs()

    fig1 = reject_log.plot(show=show_plots)
    meeg.plot_save('epochs', subfolder='autoreject_log', idx='reject', matplotlib_figure=fig1)
    try:
        fig2 = reject_log.plot_epochs(epochs)
        meeg.plot_save('epochs', subfolder='autoreject_log', idx='epochs', matplotlib_figure=fig2)
    except ValueError:
        print(f'{meeg.name}: No epochs-plot for autoreject-log')


def plot_evoked_topo(meeg, show_plots):
    evokeds = meeg.load_evokeds()
    fig = mne.viz.plot_evoked_topo(evokeds, title=meeg.name, show=show_plots)

    meeg.plot_save('evokeds', subfolder='topo', matplotlib_figure=fig, dpi=800)


def plot_evoked_topomap(meeg, show_plots):
    evokeds = meeg.load_evokeds()
    for evoked in evokeds:
        fig = mne.viz.plot_evoked_topomap(evoked, times='auto',
                                          title=meeg.name + '-' + evoked.comment, show=show_plots)

        meeg.plot_save('evokeds', subfolder='topomap', trial=evoked.comment, matplotlib_figure=fig)


def plot_evoked_joint(meeg, show_plots):
    evokeds = meeg.load_evokeds()

    for evoked in evokeds:
        fig = mne.viz.plot_evoked_joint(evoked, times='peaks',
                                        title=meeg.name + ' - ' + evoked.comment, show=show_plots)

        meeg.plot_save('evokeds', subfolder='joint', trial=evoked.comment, matplotlib_figure=fig)


def plot_evoked_butterfly(meeg, apply_proj, show_plots):
    evokeds = meeg.load_evokeds()
    for evoked in evokeds:
        titles_dict = {cht: f'{cht}: {meeg.name}-{evoked.comment}'
                       for cht in evoked.get_channel_types(unique=True, only_data_chs=True)}
        fig = evoked.plot(spatial_colors=True, proj=apply_proj, titles=titles_dict,
                          window_title=meeg.name + ' - ' + evoked.comment,
                          selectable=True, gfp=True, zorder='std', show=show_plots)
        meeg.plot_save('evokeds', subfolder='butterfly', trial=evoked.comment, matplotlib_figure=fig)


def plot_evoked_white(meeg, show_plots):
    evokeds = meeg.load_evokeds()
    noise_covariance = meeg.load_noise_covariance()

    for evoked in evokeds:
        # Check, if evokeds and noise covariance got the same channels
        channels = set(evoked.ch_names) & set(noise_covariance.ch_names)
        evoked.pick_channels(channels)
        noise_covariance.pick_channels(channels)

        fig = evoked.plot_white(noise_covariance, show=show_plots)
        fig.suptitle(meeg.name + ' - ' + evoked.comment, horizontalalignment='center')

        meeg.plot_save('evokeds', subfolder='white', trial=evoked.comment, matplotlib_figure=fig)


def plot_evoked_image(meeg, show_plots):
    evokeds = meeg.load_evokeds()

    for evoked in evokeds:
        fig = evoked.plot_image(show=show_plots)
        fig.suptitle(meeg.name + ' - ' + evoked.comment, horizontalalignment='center')

        meeg.plot_save('evokeds', subfolder='image', trial=evoked.comment, matplotlib_figure=fig)


def plot_compare_evokeds(meeg, show_plots):
    evokeds = meeg.load_evokeds()

    evokeds = {evoked.comment: evoked for evoked in evokeds}

    fig = mne.viz.plot_compare_evokeds(evokeds, show=show_plots)

    meeg.plot_save('evokeds', subfolder='compare', matplotlib_figure=fig)


def plot_gfp(meeg, show_plots):
    evokeds = meeg.load_evokeds()
    for evoked in evokeds:
        gfp_dict = op.calculate_gfp(evoked)
        t = evoked.times
        trial = evoked.comment

        fig, ax = plt.subplots(len(gfp_dict), 1)
        for idx, ch_type in enumerate(gfp_dict):
            gfp = gfp_dict[ch_type]
            ax[idx].plot(t, gfp)
            ax[idx].set_title(f'GFP of {meeg.name}-{trial}-{ch_type}')

        if show_plots:
            fig.show()

        meeg.plot_save('evokeds', subfolder='gfp', trial=trial, matplotlib_figure=fig)


def plot_transformation(meeg):
    info = meeg.load_info()
    trans = meeg.load_transformation()

    mne.viz.plot_alignment(info, trans, meeg.fsmri.name, meeg.subjects_dir,
                           surfaces=['head-dense', 'inner_skull', 'brain'],
                           show_axes=True, dig=True)

    mlab.view(45, 90, distance=0.6, focalpoint=(0., 0., 0.025))

    meeg.plot_save('transformation', mayavi=True)


def plot_source_space(fsmri):
    source_space = fsmri.load_source_space()
    source_space.plot()
    mlab.view(-90, 7)

    fsmri.plot_save('source_space', mayavi=True)


def plot_bem(fsmri, show_plots):
    source_space = fsmri.load_source_space()
    fig1 = mne.viz.plot_bem(fsmri.name, fsmri.subjects_dir, src=source_space, show=show_plots)

    fsmri.plot_save('bem', subfolder='source-space', matplotlib_figure=fig1)

    try:
        vol_src = fsmri.load_vol_source_space()
        fig2 = mne.viz.plot_bem(fsmri.name, fsmri.subjects_dir, src=vol_src, show=show_plots)

        fsmri.plot_save('bem', subfolder='volume-source-space', matplotlib_figure=fig2)

    except FileNotFoundError:
        pass


def plot_sensitivity_maps(meeg, ch_types):
    fwd = meeg.load_forward()

    for ch_type in [ct for ct in ch_types if ct in ['grad', 'mag', 'eeg']]:
        sens_map = mne.sensitivity_map(fwd, ch_type=ch_type, mode='fixed')
        brain = sens_map.plot(title=f'{ch_type}-Sensitivity for {meeg.name}', subjects_dir=meeg.subjects_dir,
                              clim=dict(lims=[0, 50, 100]))

        meeg.plot_save('sensitivity', trial=ch_type, brain=brain)


def plot_noise_covariance(meeg, show_plots):
    noise_covariance = meeg.load_noise_covariance()
    info = meeg.load_info()

    fig1, fig2 = noise_covariance.plot(info, show_svd=False, show=show_plots)

    meeg.plot_save('noise-covariance', subfolder='covariance', matplotlib_figure=fig1)
    meeg.plot_save('noise-covariance', subfolder='svd-spectra', matplotlib_figure=fig2)


def brain_plot(meeg, stcs, folder_name, subject, mne_evoked_time=None):
    # backend = mne.viz.get_3d_backend()
    # mne_evoked_time = mne_evoked_time or list()
    mne.viz.use_3d_backend('pyvista')
    for trial in stcs:
        stc = stcs[trial]
        # file_patternlh = join(meeg.figures_path, meeg.p_preset, folder_name, trial,
        #                       f'{meeg.name}-{trial}_{meeg.p_preset}_lh-%s{meeg.img_format}')
        # file_patternrh = join(meeg.figures_path, meeg.p_preset, folder_name, trial,
        #                       f'{meeg.name}-{trial}_{meeg.p_preset}_rh-%s{meeg.img_format}')
        # # Check, if folder exists
        # parent_path = Path(file_patternlh).parent
        # if not isdir(parent_path):
        #     makedirs(parent_path)
        #
        # if backend == 'mayavi':
        #     brain = stc.plot(subject=subject, surface='inflated', subjects_dir=meeg.subjects_dir,
        #                      hemi='lh', title=f'{meeg.name}-{trial}-lh')
        #     brain.save_image_sequence(mne_evoked_time, fname_pattern=file_patternlh)
        #     brain = stc.plot(subject=subject, surface='inflated', subjects_dir=meeg.subjects_dir,
        #                      hemi='rh', title=f'{meeg.name}-{trial}-lh')
        #     brain.save_image_sequence(mne_evoked_time, fname_pattern=file_patternrh)
        #
        # else:
        brain = stc.plot(subject=subject, surface='inflated', subjects_dir=meeg.subjects_dir,
                         hemi='split', title=f'{meeg.name}-{trial}', size=(1200, 600),
                         initial_time=0)
        brain.add_text(0, 0.9, f'{meeg.name}-{trial}', 'title',
                       font_size=14)
        meeg.plot_save(folder_name, trial=trial, brain=brain)
        if not meeg.ct.settings['show_plots']:
            brain.close()


def plot_stc(meeg, mne_evoked_time):
    stcs = meeg.load_source_estimates()
    brain_plot(meeg, stcs, 'source-estimate', meeg.fsmri.name, mne_evoked_time)


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

        meeg.plot_save('mixed-norm-estimate', subfolder='dipoles', trial=trial, matplotlib_figure=fig1)

        for idx, dipole in enumerate(dipoles):
            # Assumption right in Head Coordinates?
            if dipole.pos[0, 0] < 0:
                side = 'left'
                hemi = 'lh'
            else:
                side = 'right'
                hemi = 'rh'
            fig2 = mne.viz.plot_dipole_locations(dipole, trans=trans, subject=meeg.fsmri.name,
                                                 subjects_dir=meeg.subjects_dir, coord_frame='mri')
            fig2.suptitle(f'Dipole {idx + 1} {side}', fontsize=16)

            meeg.plot_save('mixed-norm-estimate', subfolder='dipoles', trial=trial, idx=idx, matplotlib_figure=fig2)

            brain = Brain(meeg.fsmri.name, hemi=hemi, surf='pial', views='lat')
            dip_loc = mne.head_to_mri(dipole.pos, meeg.fsmri.name, trans, subjects_dir=meeg.subjects_dir)
            brain.add_foci(dip_loc[0])
            brain.add_annotation(parcellation)
            # Todo: Comparision with label
            meeg.plot_save('mixed-norm-estimate', subfolder='dipoles', trial=trial, idx=idx, brain=brain)

    stcs = meeg.load_mixn_source_estimates()
    brain_plot(meeg, stcs, 'mixed-norm-estimate/stc', meeg.fsmri.name, mne_evoked_time)


def plot_animated_stc(meeg, stc_animation, stc_animation_dilat):
    stcs = meeg.load_source_estimates()

    for trial in stcs:
        n_stc = stcs[trial]

        save_path = join(meeg.figures_path, meeg.p_preset, 'stcs_movie', trial,
                         f'{meeg.name}_{trial}_{meeg.p_preset}-stc_movie.mp4')

        brain = mne.viz.plot_source_estimates(stc=n_stc, subject=meeg.fsmri.name, surface='inflated',
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
            fig = dipole.plot_locations(trans, meeg.fsmri.name, meeg.subjects_dir,
                                        mode='orthoview', idx='gof')
            fig.suptitle(meeg.name, horizontalalignment='right')

            meeg.plot_save('ECD', subfolder=dipole, trial=trial, matplotlib_figure=fig)

            # find time point with highest GOF to plot
            best_idx = np.argmax(dipole.gof)
            best_time = dipole.times[best_idx]

            print(f'Highest GOF {dipole.gof[best_idx]:.2f}% at t={best_time * 1000:.1f} ms with confidence volume'
                  f'{dipole.conf["vol"][best_idx] * 100 ** 3} cm^3')

            mri_pos = mne.head_to_mri(dipole.pos, meeg.fsmri.name, trans, meeg.subjects_dir)

            save_path_anat = join(meeg.obj.figures_path, meeg.p_preset, 'ECD', dipole, trial,
                                  f'{meeg.name}-{trial}_{meeg.pr.p_preset}_ECD-{dipole}{meeg.img_format}')
            t1_path = join(meeg.subjects_dir, meeg.fsmri.name, 'mri', 'T1.mgz')
            plot_anat(t1_path, cut_coords=mri_pos[best_idx], output_file=save_path_anat,
                      title=f'{meeg.name}-{trial}_{dipole}',
                      annotate=True, draw_cross=True)

            plot_anat(t1_path, cut_coords=mri_pos[best_idx],
                      title=f'{meeg.name}-{trial}_{dipole}',
                      annotate=True, draw_cross=True)


def plot_snr(meeg, show_plots):
    evokeds = meeg.load_evokeds()
    inv = meeg.load_inverse_operator()

    for evoked in evokeds:
        trial = evoked.comment
        # data snr
        fig = mne.viz.plot_snr_estimate(evoked, inv, show=show_plots)
        fig.suptitle(f'{meeg.name}-{evoked.comment}', horizontalalignment='center')

        meeg.plot_save('snr', trial=trial, matplotlib_figure=fig)


def plot_annotation(fsmri, parcellation):
    brain = Brain(fsmri.name, hemi='lh', surf='inflated', views='lat')
    brain.add_annotation(parcellation)

    fsmri.plot_save('Labels', brain=brain)


def plot_label_time_course(meeg, show_plots):
    ltcs = meeg.load_ltc()
    for trial in ltcs:
        for label in ltcs[trial]:
            plt.figure()
            plt.plot(ltcs[trial][label][1], ltcs[trial][label][0])
            plt.title(f'{meeg.name}-{trial}-{label}\n'
                      f'Extraction-Mode: {meeg.pa["extract_mode"]}')
            plt.xlabel('Time in s')
            plt.ylabel('Source amplitude')
            if show_plots:
                plt.show()

            meeg.plot_save('label-time-course', subfolder=label, trial=trial)


def plot_source_space_connectivity(meeg, target_labels, parcellation, con_fmin, con_fmax, show_plots):
    con_dict = meeg.load_connectivity()
    labels = mne.read_labels_from_annot(meeg.fsmri.name, parc=parcellation, subjects_dir=meeg.subjects_dir)

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

    node_angles = mne_connectivity.viz.circular_layout(label_names, node_order, start_pos=90,
                                                       group_boundaries=[0, len(label_names) / 2])

    # Plot the graph using node colors from the FreeSurfer parcellation. We only
    # show the 300 strongest connections.
    for trial in con_dict:
        for con_method in con_dict[trial]:
            fig, axes = mne_connectivity.viz.plot_connectivity_circle(con_dict[trial][con_method], label_names,
                                                                      n_lines=300, node_angles=node_angles,
                                                                      node_colors=label_colors,
                                                                      title=f'{con_method}: '
                                                                            f'{str(con_fmin)}-{str(con_fmax)}',
                                                                      fontsize_names=12, show=show_plots)

            meeg.plot_save('connectivity', subfolder=con_method, trial=trial, matplotlib_figure=fig)


# %% Grand-Average Plots

def plot_grand_avg_evokeds(group, show_plots):
    ga_evokeds = group.load_ga_evokeds()

    for trial in ga_evokeds:
        fig = ga_evokeds[trial].plot(window_title=f'{group.name}-{trial}',
                                     spatial_colors=True, gfp=True, show=show_plots)

        group.plot_save('ga_evokeds', trial=trial, matplotlib_figure=fig)


def plot_grand_avg_tfr(group, show_plots):
    ga_dict = group.load_ga_tfr()

    for trial in ga_dict:
        power = ga_dict[trial]
        fig1 = power.plot(title=f'{group.name}-{power.comment}', show=show_plots)
        fig2 = power.plot_topo(title=f'{group.name}-{power.comment}', show=show_plots)
        fig3 = power.plot_joint(title=f'{group.name}-{power.comment}', show=show_plots)
        fig4 = power.plot_topomap(title=f'{group.name}-{power.comment}', show=show_plots)

        group.plot_save('ga_tfr', subfolder='plot', trial=power.comment, matplotlib_figure=fig1)
        group.plot_save('ga_tfr', subfolder='topo', trial=power.comment, matplotlib_figure=fig2)
        group.plot_save('ga_tfr', subfolder='joint', trial=power.comment, matplotlib_figure=fig3)
        group.plot_save('ga_tfr', subfolder='topomap', trial=power.comment, matplotlib_figure=fig4)


def plot_grand_avg_stc(group, morph_to):
    ga_stcs = group.load_ga_stc()
    brain_plot(group, ga_stcs, 'ga_source_estimate', morph_to, )


def plot_grand_avg_stc_anim(group, stc_animation, stc_animation_dilat, morph_to):
    ga_dict = group.load_ga_stc()

    for trial in ga_dict:
        brain = ga_dict[trial].plot(subject=morph_to,
                                    subjects_dir=group.subjects_dir, size=(1600, 800),
                                    title=f'{group.name}-{trial}', hemi='split',
                                    views='lat')
        brain.title = f'{group.name}-{trial}'

        print('Saving Video')
        save_path = join(group.figures_path, group.p_preset, 'grand_averages/source_space/stc_movie',
                         f'{group.name}_{trial}_{group.pr.p_preset}-stc_movie.mp4')
        brain.save_movie(save_path, time_dilation=stc_animation_dilat,
                         tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
        mlab.close()


def plot_grand_avg_ltc(group, show_plots):
    ga_ltc = group.load_ga_ltc()
    for trial in ga_ltc:
        for label in ga_ltc[trial]:
            plt.figure()
            plt.plot(ga_ltc[trial][label][1], ga_ltc[trial][label][0])
            plt.title(f'Label-Time-Course for {group.name}-{trial}-{label}\n'
                      f'with Extraction-Mode: {group.pa["extract_mode"]}')
            plt.xlabel('Time in ms')
            plt.ylabel('Source amplitude')
            if show_plots:
                plt.show()

            group.plot_save('ga_label-time-course', subfolder=label, trial=trial)


def plot_grand_avg_connect(group, con_fmin, con_fmax, parcellation, target_labels, morph_to, show_plots):
    ga_dict = group.load_ga_con()

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
                                                         fontsize_names=16, show=show_plots)

            group.plot_save('ga_connectivity', subfolder=method, trial=trial, matplotlib_figure=fig)


def close_all():
    plt.close('all')
    mlab.close(all=True)
    gc.collect()
