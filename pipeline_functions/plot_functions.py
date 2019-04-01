
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
from surfer import Brain
import gc
import statistics as stats

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

    diff_mean = stats.mean(l1)
    diff_stdev = stats.stdev(l1)

    figure = plt.figure()
    plt.plot(l1)
    plt.title(f'{name}_StartMot-LBT, mean={diff_mean}, stdev={diff_stdev}')

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
def plot_power_spectra(name, save_dir, lowpass, highpass, save_plots,
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
def plot_power_spectra_epochs(name, save_dir, lowpass, highpass, save_plots,
                        figures_path, bad_channels):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)

    for trial_type in epochs.event_id:

        psd_figure = epochs[trial_type].plot_psd(fmax=lowpass, n_jobs=-1)
        plt.title(name + '-' + trial_type)

        if save_plots:
            save_path = join(figures_path, 'power_spectra_epochs', trial_type, name + '_' +\
                                 trial_type + '_psde' + filter_string(lowpass, highpass) + '.jpg')
            psd_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_power_spectra_topo(name, save_dir, lowpass, highpass, save_plots,
                            figures_path, bad_channels):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)
    for trial_type in epochs.event_id:
        psd_figure = epochs[trial_type].plot_psd_topomap(n_jobs=-1)
        plt.title(name + '-' + trial_type)
        
        if save_plots:
            save_path = join(figures_path, 'power_spectra_topo', trial_type, name + '_' +\
                                 trial_type + '_psdtop' + filter_string(lowpass, highpass) + '.jpg')
            psd_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_tfr(name, save_dir, lowpass, highpass, tmin, tmax, baseline,
             tfr_method, save_plots, figures_path):

    powers = io.read_tfr_power(name, save_dir, lowpass, highpass, tfr_method)
    itcs = io.read_tfr_itc(name, save_dir, lowpass, highpass, tfr_method)

    for power in powers:
        fig1 = power.plot(baseline=baseline, mode='logratio', tmin=tmin,
                          tmax=tmax, title=f'{name}-{power.comment}')
        fig2 = power.plot_topo(baseline=baseline, mode='logratio', tmin=tmin,
                               tmax=tmax, title=f'{name}-{power.comment}')    
        fig3 = power.plot_joint(baseline=baseline, mode='mean', tmin=tmin,
                                tmax=tmax, title=f'{name}-{power.comment}')
    
        fig4, axis = plt.subplots(1, 5, figsize=(15,2))
        power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=5, fmax=8,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[0],
                           title='Theta 5-8 Hz', show=False)
        power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=8, fmax=12,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[1],
                           title='Alpha 8-12 Hz', show=False)
        power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=13, fmax=30,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[2],
                           title='Beta 13-30 Hz', show=False)
        power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=31, fmax=60,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[3],
                           title='Low Gamma 30-60 Hz', show=False)
        power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=61, fmax=100,
                           baseline=(-0.5, 0), mode='logratio', axes=axis[4],
                           title='High Gamma 60-100 Hz', show=False)
        mne.viz.tight_layout()
        plt.title(f'{name}-{power.comment}')
        plt.show()

        if save_plots:
            save_path1 = join(figures_path, 'tf_sensor_space/plot',
                              power.comment, name + '_tf' + \
                              filter_string(lowpass, highpass) + \
                              '-' + power.comment + '.jpg')
            fig1.savefig(save_path1, dpi=600)
            print('figure: ' + save_path1 + ' has been saved')
            save_path2 = join(figures_path, 'tf_sensor_space/topo',
                              power.comment, name + '_tf_topo' + \
                              filter_string(lowpass, highpass) + \
                              '-' + power.comment + '.jpg')
            fig2.savefig(save_path2, dpi=600)
            print('figure: ' + save_path2 + ' has been saved')
            save_path3 = join(figures_path, 'tf_sensor_space/joint',
                              power.comment, name + '_tf_joint' + \
                              filter_string(lowpass, highpass) + \
                              '-' + power.comment + '.jpg')
            fig3.savefig(save_path3, dpi=600)
            print('figure: ' + save_path3 + ' has been saved')
            save_path4 = join(figures_path, 'tf_sensor_space/oscs',
                              power.comment, name + '_tf_oscs' + \
                              filter_string(lowpass, highpass) + \
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
                              power.comment, name + '_tf_itc' + \
                              filter_string(lowpass, highpass) + \
                              '-' + itc.comment + '.jpg')
            fig5.savefig(save_path5, dpi=600)        
            print('figure: ' + save_path5 + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')
        
@decor.topline
def tfr_event_dynamics(name, save_dir, tmin, tmax, save_plots, figures_path,
                      bad_channels, n_jobs):
    
    iter_freqs = [
    ('Theta', 4, 7),
    ('Alpha', 8, 12),
    ('Beta', 13, 30),
    ('l_Gamma', 30, 60)
    ]
    
    event_id = {'LBT':1}
    baseline = None
    
    raw = io.read_raw(name, save_dir)
    events = io.read_events(name, save_dir)
    
    frequency_map = list()

    for band, fmin, fmax in iter_freqs:
        # (re)load the data to save memory
        raw = io.read_raw(name, save_dir)
    
        # bandpass filter and compute Hilbert
        raw.filter(fmin, fmax, n_jobs=n_jobs,  # use more jobs to speed up.
                   l_trans_bandwidth=1,  # make sure filter params are the same
                   h_trans_bandwidth=1,  # in each band and skip "auto" option.
                   fir_design='firwin')
        raw.apply_hilbert(n_jobs=n_jobs, envelope=False)

        picks = mne.pick_types(raw.info, meg=True, eeg=False, stim=False,
                               eog=False, ecg=False, exclude=bad_channels)   
        
        epochs = mne.Epochs(raw, events, event_id, tmin, tmax, baseline=baseline,
                            picks=picks, reject=dict(grad=4000e-13), preload=True)
        # remove evoked response and get analytic signal (envelope)
        epochs.subtract_evoked()  # for this we need to construct new epochs.
        epochs = mne.EpochsArray(
            data=np.abs(epochs.get_data()), info=epochs.info, tmin=epochs.tmin)
        # now average and move on
        frequency_map.append(((band, fmin, fmax), epochs.average()))    


    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True, sharey=True)
    colors = plt.get_cmap('winter_r')(np.linspace(0, 1, 4))
    for ((freq_name, fmin, fmax), average), color, ax in zip(
            frequency_map, colors, axes.ravel()[::-1]):
        times = average.times * 1e3
        gfp = np.sum(average.data ** 2, axis=0)
        gfp = mne.baseline.rescale(gfp, times, baseline=(None, 0))
        ax.plot(times, gfp, label=freq_name, color=color, linewidth=2.5)
        ax.axhline(0, linestyle='--', color='grey', linewidth=2)
        ci_low, ci_up = mne.stats._bootstrap_ci(average.data, random_state=0,
                                      stat_fun=lambda x: np.sum(x ** 2, axis=0))
        ci_low = mne.baseline.rescale(ci_low, average.times, baseline=(None, 0))
        ci_up = mne.baseline.rescale(ci_up, average.times, baseline=(None, 0))
        ax.fill_between(times, gfp + ci_up, gfp - ci_low, color=color, alpha=0.3)
        ax.grid(True)
        ax.set_ylabel('GFP')
        ax.annotate('%s (%d-%dHz)' % (freq_name, fmin, fmax),
                    xy=(0.95, 0.8),
                    horizontalalignment='right',
                    xycoords='axes fraction')
        ax.set_xlim(tmin*1000, tmax*1000)
    
    axes.ravel()[-1].set_xlabel('Time [ms]')


    if save_plots:
        save_path = join(figures_path, 'tf_sensor_space/dynamics', name + '_tf_dynamics' + '.jpg')
        fig.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')
        
@decor.topline
def plot_ssp(name, save_dir, lowpass, highpass, save_plots,
                        figures_path, bad_channels, ermsub):

    if ermsub == 'None':
        print('no empty_room_data found for' + name)
        pass

    else:
        epochs = io.read_ssp_epochs(name, save_dir, lowpass, highpass)

        ssp_figure = epochs.plot_projs_topomap()

        if save_plots:
            save_path = join(figures_path, 'ssp', name + '_ssp' + \
                                 filter_string(lowpass, highpass) + '.jpg')
            ssp_figure.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_ssp_eog(name, save_dir, lowpass, highpass, save_plots,
                        figures_path, bad_channels):
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
def plot_ssp_ecg(name, save_dir, lowpass, highpass, save_plots,
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
def plot_epochs(name, save_dir, lowpass, highpass, save_plots,
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
def plot_epochs_image(name, save_dir, lowpass, highpass, save_plots,
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
def plot_epochs_topo(name, save_dir, lowpass, highpass, save_plots,
                      figures_path):

    epochs = io.read_epochs(name, save_dir, lowpass, highpass)
    for trial_type in epochs.event_id:

        epochs_topo = mne.viz.plot_topo_image_epochs(epochs, title=name)

        if save_plots:
            save_path = join(figures_path, 'epochs_topo', trial_type, name + '_epochs_topo' + \
            filter_string(lowpass, highpass) +  '.jpg')

            epochs_topo.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')

        else:
            print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_epochs_drop_log(name, save_dir, lowpass, highpass, save_plots,
                         figures_path):
    
    epochs = io.read_epochs(name, save_dir, lowpass, highpass)
    
    fig = epochs.plot_drop_log(subject=name)

    if save_plots:
        save_path = join(figures_path, 'epochs_drop_log', name + '_drop_log' + \
        filter_string(lowpass, highpass) + '.jpg')

        fig.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "save_plots" to "True" to save')    
    
@decor.topline
def plot_evoked_topo(name, save_dir, lowpass, highpass, save_plots, figures_path):

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
def plot_evoked_topomap(name, save_dir, lowpass, highpass, save_plots, figures_path,
                        layout):

    evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)
    for evoked in evokeds:
        evoked_figure = mne.viz.plot_evoked_topomap(evoked, times='auto',
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
def plot_evoked_field(name, save_dir, lowpass, highpass,
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
def plot_evoked_joint(name, save_dir, lowpass, highpass, save_plots,
                      figures_path, ECDs):

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
                           title=name + ' - ' + evoked.comment)

    else:
        for evoked in evokeds:
            figure = mne.viz.plot_evoked_joint(evoked, times='peaks',
                                               title=name + ' - ' + evoked.comment)

            if save_plots:
                save_path = join(figures_path, 'evoked_joint', evoked.comment,
                                 name + '_' + evoked.comment + '_joint' + \
                                 filter_string(lowpass, highpass) + '.jpg')
                figure.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_butterfly_evokeds(name, save_dir, lowpass, highpass, save_plots,
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
def plot_evoked_white(name, save_dir, lowpass, highpass, save_plots, figures_path, ermsub, use_calm_cov):

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
        # Check, if evokeds and noise covariance got the same channels
        channels = set(evoked.ch_names) & set(noise_covariance.ch_names)
        evoked.pick_channels(channels)
        
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
def plot_evoked_image(name, save_dir, lowpass, highpass, save_plots, figures_path):

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
def plot_transformation(name, save_dir, subtomri, subjects_dir, save_plots,
                        figures_path):
        info = io.read_info(name, save_dir)

        trans = io.read_transformation(save_dir, subtomri)

        mne.viz.plot_alignment(info, trans, subtomri, subjects_dir,
                               surfaces=['head-dense', 'inner_skull', 'brain'],
                               show_axes=True, dig=True)

        mlab.view(45, 90, distance=0.6, focalpoint=(0., 0., 0.025))

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
def plot_noise_covariance(name, save_dir, lowpass, highpass, subtomri, save_plots, figures_path, ermsub, use_calm_cov):

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
def plot_source_estimates(name, save_dir, lowpass, highpass, subtomri, subjects_dir,
                          method, mne_evoked_time, event_id, stc_interactive,
                          save_plots, figures_path):
    stcs = io.read_source_estimates(name, save_dir,lowpass, highpass, method,
                                    event_id)
    for trial_type in stcs:
        for idx, t in enumerate(mne_evoked_time):
            stc = stcs[trial_type]
            if stc_interactive:
                figures = (mlab.figure(size=(800,800)),mlab.figure(size=(800,800)))
                brain = stc.plot(subject=subtomri, surface='inflated', subjects_dir=subjects_dir,
                                 time_viewer=True, hemi='both', views='lat', initial_time=t,
                                 title=name+'-'+trial_type, figure=figures)
            else:
                brain = stc.plot(subject=subtomri, surface='inflated', subjects_dir=subjects_dir,
                                 time_viewer=False, hemi='split', views='lat', initial_time=t,
                                 title=name+'-'+trial_type, size=(1600,800))
            brain.title = name+'-'+trial_type
            if save_plots:
                save_path = join(figures_path, 'stcs', trial_type,
                                 name + '_' + trial_type + \
                                 filter_string(lowpass, highpass) + '_' + str(idx) + '.jpg')
                brain.save_image(save_path)
                print('figure: ' + save_path + ' has been saved')

            else:
                print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_vector_source_estimates(name, save_dir, lowpass, highpass, subtomri, subjects_dir,
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
def plot_animated_stc(name, save_dir, lowpass, highpass, subtomri, subjects_dir,
                      method, mne_evoked_time, stc_animation, tmin, tmax, event_id,
                      save_plots, figures_path):

    stcs = io.read_source_estimates(name, save_dir,lowpass, highpass, method,
                                    event_id)

    stc = stcs['LBT']
    save_path = join(figures_path, 'stcs_movie', 'LBT', name + '_' + 'LBT' +\
						      filter_string(lowpass, highpass) + '.mp4')

    brain = mne.viz.plot_source_estimates(stc=stc,subject=subtomri, surface='inflated',
                                subjects_dir=subjects_dir, size=(1600,800),
                                hemi='split', views='lat',
                                title=name + '_' + 'LBT' + '_movie')

    print('Saving Video')
    brain.save_movie(save_path, time_dilation=8,
                     tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
    mlab.close()

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
def plot_labels(mri_subject, subjects_dir, save_plots, figures_path,
                parcellation):

    brain = Brain(mri_subject, hemi='lh', surf='inflated', views='lat')
    
    labels = mne.read_labels_from_annot(mri_subject, parc=parcellation,
                                        hemi='lh')

    for label in labels:
        brain.add_label(label)
    
    if save_plots:
        save_path = join(figures_path, 'labels',
                         mri_subject + '_' + parcellation + '.jpg')
        mlab.savefig(save_path, figure=mlab.gcf())
        print('figure: ' + save_path + ' has been saved')

    else:
        print('Not saving plots; set "save_plots" to "True" to save')
        

@decor.topline
def label_time_course(name, save_dir, lowpass, highpass, subtomri, target_labels,
                      save_plots, figures_path, parcellation):

    snr = 3.0
    lambda2 = 1.0 / snr ** 2
    method = "dSPM"

    evoked = io.read_evokeds(name, save_dir, lowpass, highpass)[0]
    inv_op = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    src = inv_op['src']
    # pick_ori has to be normal to plot bipolar time course
    stc = mne.minimum_norm.apply_inverse(evoked, inv_op, lambda2, method,
                                         pick_ori='normal')    
    
    labels = mne.read_labels_from_annot(subtomri, parc=parcellation)
    
    # Annotation Parameters
    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    arrowprops=dict(arrowstyle="->")
    kw = dict(xycoords='data', arrowprops=arrowprops, bbox=bbox_props)

    for hemi in target_labels:
        for l in labels:
            if l.name in target_labels[hemi]:
                print(l.name)
    
                stc_label = stc.in_label(l)
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
                
                if -200<tmax<500:
                    plt.annotate(f'max_lat={int(tmax)}ms',
                                 xy=(tmax, pca.max()),
                                 xytext=(tmax+200, pca.max()+2), **kw)
                if -200<tmin<500:
                    plt.annotate(f'min_lat={int(tmin)}ms',
                                 xy=(tmin, pca.min()),
                                 xytext=(tmin+200, pca.min()-2), **kw)
                plt.legend([h0, h1, h2], ['mean', 'mean flip', 'PCA flip'])
                plt.xlabel('Time (ms)')
                plt.ylabel('Source amplitude')
                plt.title(f'Activations in Label :{l.name}-{evoked.comment}')
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
def cmp_label_time_course(data_path, lowpass, highpass, sub_to_mri, comp_dict,
                          parcellation, target_labels, save_plots, figures_path):
    
    snr = 3.0
    lambda2 = 1.0 / snr ** 2
    method = "dSPM"
    color_dict = {'low':'g', 'middle':'y', 'high':'r', 't':'b'}
   
    # Differentiate a and b
    for ab_key in comp_dict:
        
        subtomri = sub_to_mri[ab_key[:-2]]
        labels = mne.read_labels_from_annot(subtomri, parc=parcellation)
        nrows = len(target_labels)
        ncols = len(target_labels['lh'])
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols,
                                 sharex='all', sharey='all',
                                 gridspec_kw={'hspace':0.1, 'wspace':0.1,
                                              'left':0.05, 'right':0.95,
                                              'top':0.95, 'bottom':0.05},
                                 figsize=(18,8))
        # Nasty workaround to set label-titles on axes
        # key in target_labels = row in plot
        r_cnt = 0
        for tl in target_labels:
            c_cnt = 0
            for t in target_labels[tl]:
                axes[r_cnt, c_cnt].set_title(t)
                c_cnt += 1
            r_cnt += 1
            
        # Trials(low,middle,high,t)
        for trial in comp_dict[ab_key]:
            
            name = comp_dict[ab_key][trial]
            save_dir = join(data_path, name)
            color = color_dict[trial]
             
            evoked = io.read_evokeds(name, save_dir, lowpass, highpass)[0]
            evoked = evoked.crop(tmax=1)
            inv_op = io.read_inverse_operator(name, save_dir, lowpass, highpass)
            src = inv_op['src']
            stc = mne.minimum_norm.apply_inverse(evoked, inv_op, lambda2, method,
                                                 pick_ori='normal')
            
            #choose target labels
            for hemi in target_labels:
                for l in labels:
                    if l.name in target_labels[hemi]:
                        print(l.name)                        
                        stc_label = stc.in_label(l)
                        pca = stc.extract_label_time_course(l, src, mode='pca_flip')
                        
                        t = 1e3 * stc_label.times
                        # Ensure, that plot gets in the axe with the right title
                        axe = None
                        for ax in axes.flatten():
                            if ax.get_title() == l.name:
                                axe = ax
                        axe.plot(t, pca.T, color, label=trial)
                        axe.legend()
        fig.suptitle(ab_key, size=16, weight=4)
        fig.text(0.5, 0.01, 'Time [ms]', ha='center')
        fig.text(0.01, 0.5, 'Source Amplitude', va='center', rotation='vertical')
        plt.show()
        
        if save_plots:
            save_path = join(figures_path, 'label_time_course', ab_key + \
                                 filter_string(lowpass, highpass) + 'label-cmp.jpg')
            plt.savefig(save_path, dpi=600)
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')    
        close_all()
@decor.topline
def tf_label_power_phlck(name, save_dir, lowpass, highpass, subtomri, parcellation,
                         save_plots, figures_path, n_jobs):
    
    # Compute a source estimate per frequency band including and excluding the
    # evoked response
    freqs = np.arange(7, 30, 2)  # define frequencies of interest
    n_cycles = freqs / 3.  # different number of cycle per frequency
    labels = mne.read_labels_from_annot(subtomri, parc=parcellation)

    for l in labels:
        if l.name == 'S_postcentral-lh':
            label = l
    
    epochs = io.read_epochs(name, save_dir, lowpass, highpass)['LBT']
    inverse_operator = io.read_inverse_operator(name, save_dir, lowpass, highpass)
    # subtract the evoked response in order to exclude evoked activity
    epochs_induced = epochs.copy().subtract_evoked()
    
    plt.close('all')
    mlab.close(all=True)
            
    for ii, (this_epochs, title) in enumerate(zip([epochs, epochs_induced],
                                                  ['evoked + induced',
                                                   'induced only'])):
        # compute the source space power and the inter-trial coherence
        power, itc = mne.minimum_norm.source_induced_power(
            this_epochs, inverse_operator, freqs, label, baseline=(-0.1, 0),
            baseline_mode='percent', n_cycles=n_cycles, n_jobs=n_jobs)
    
        power = np.mean(power, axis=0)  # average over sources
        itc = np.mean(itc, axis=0)  # average over sources
        times = epochs.times
    
        ##########################################################################
        # View time-frequency plots
        plt.subplots_adjust(0.1, 0.08, 0.96, 0.94, 0.2, 0.43)
        plt.subplot(2, 2, 2 * ii + 1)
        plt.imshow(20 * power,
                   extent=[times[0], times[-1], freqs[0], freqs[-1]],
                   aspect='auto', origin='lower', vmin=0., vmax=30., cmap='RdBu_r')
        plt.xlabel('Time (s)')
        plt.ylabel('Frequency (Hz)')
        plt.title('Power (%s)' % title)
        plt.colorbar()
    
        plt.subplot(2, 2, 2 * ii + 2)
        plt.imshow(itc,
                   extent=[times[0], times[-1], freqs[0], freqs[-1]],
                   aspect='auto', origin='lower', vmin=0, vmax=0.7,
                   cmap='RdBu_r')
        plt.xlabel('Time (s)')
        plt.ylabel('Frequency (Hz)')
        plt.title('ITC (%s)' % title)
        plt.colorbar()
    
    plt.show()   

    if save_plots:
        save_path = join(figures_path, 'tf_source_space/label_power', name + '_label_power' + \
                         filter_string(lowpass, highpass) + '.jpg')
        plt.savefig(save_path, dpi=600)
        print('figure: ' + save_path + ' has been saved')
    else:
        print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_source_space_connectivity(name, save_dir, lowpass, highpass,
                                   subtomri, subjects_dir,
                                   con_methods, con_fmin,
                                   con_fmax, save_plots, figures_path, n_jobs):
    
    con_dict = io.read_connect(name, save_dir, lowpass, highpass, con_methods,
                    con_fmin, con_fmax)
    # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
    labels = mne.read_labels_from_annot(subtomri, parc='aparc',
                                        subjects_dir=subjects_dir)
    label_colors = [label.color for label in labels]


    # First, we reorder the labels based on their location in the left hemi
    label_names = [label.name for label in labels]
    
    lh_labels = [l_name for l_name in label_names if l_name.endswith('lh')]
    
    # Get the y-location of the label
    label_ypos = list()
    for l_name in lh_labels:
        idx = label_names.index(l_name)
        ypos = np.mean(labels[idx].pos[:, 1])
        label_ypos.append(ypos)
    
    # Reorder the labels based on their location
    lh_labels = [label for (yp, label) in sorted(zip(label_ypos, lh_labels))]
    
    # For the right hemi
    rh_labels = [label[:-2] + 'rh' for label in lh_labels]
    
    # Save the plot order and create a circular layout
    node_order = list()
    node_order.extend(lh_labels[::-1])  # reverse the order
    node_order.extend(rh_labels)
    
    node_angles = mne.viz.circular_layout(label_names, node_order, start_pos=90,
                                          group_boundaries=[0, len(label_names) / 2])
    
    # Plot the graph using node colors from the FreeSurfer parcellation. We only
    # show the 300 strongest connections.
    for method in con_methods:
        fig, axes = mne.viz.plot_connectivity_circle(con_dict[method], label_names, n_lines=300,
                                               node_angles=node_angles, node_colors=label_colors,
                                               title=method+'_'+str(con_fmin)+'-'+str(con_fmax))
        if save_plots:
            save_path = join(figures_path, 'tf_source_space/connectivity', name + \
                             filter_string(lowpass, highpass) + \
                             '_' + str(con_fmin) + '-' + str(con_fmax) + \
                             '_' + method + '.jpg')
            fig.savefig(save_path, dpi=600, facecolor='k', edgecolor='k')
            print('figure: ' + save_path + ' has been saved')
        else:
            print('Not saving plots; set "save_plots" to "True" to save')
        
@decor.topline
def plot_grand_avg_evokeds(lowpass, highpass, save_dir_averages, grand_avg_dict,
                               event_id, save_plots, figures_path):

    ga_dict = io.read_grand_avg_evokeds(lowpass, highpass, save_dir_averages,
                                        grand_avg_dict, event_id)
    
    for stim_type in ga_dict:
        for trial in ga_dict[stim_type]:
            figure = ga_dict[stim_type][trial].plot_joint(title=stim_type + '_' + trial,
                            ts_args={'ylim':{'grad':[-50,20]}})
            if save_plots:
                save_path = join(figures_path, 'grand_averages/sensor_space/evoked',
                                 stim_type + '_' + trial + \
                                 filter_string(lowpass, highpass) + '.jpg')
                figure.savefig(save_path, dpi=600)
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_grand_avg_tfr(lowpass, highpass, baseline, tmin, tmax,
                           save_dir_averages, grand_avg_dict,
                           event_id, save_plots, figures_path):
    
    ga_dict = io.read_grand_avg_tfr(lowpass, highpass, save_dir_averages,
                                    grand_avg_dict, event_id)
    
    for stim_type in ga_dict:
        for trial in ga_dict[stim_type]:
            power = ga_dict[stim_type][trial]
            fig1 = power.plot(baseline=baseline, mode='logratio', tmin=tmin,
                              tmax=tmax, title=f'{stim_type}-{trial}')
            fig2 = power.plot_topo(baseline=baseline, mode='logratio', tmin=tmin,
                                   tmax=tmax, title=f'{stim_type}-{trial}')    
            fig3 = power.plot_joint(baseline=baseline, mode='mean', tmin=tmin,
                                    tmax=tmax, title=f'{stim_type}-{trial}')
        
            fig4, axis = plt.subplots(1, 5, figsize=(15,2))
            power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=5, fmax=8,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[0],
                               title='Theta 5-8 Hz', show=False)
            power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=8, fmax=12,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[1],
                               title='Alpha 8-12 Hz', show=False)
            power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=13, fmax=30,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[2],
                               title='Beta 13-30 Hz', show=False)
            power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=31, fmax=60,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[3],
                               title='Low Gamma 30-60 Hz', show=False)
            power.plot_topomap(ch_type='grad', tmin=tmin, tmax=tmax, fmin=61, fmax=100,
                               baseline=(-0.5, 0), mode='logratio', axes=axis[4],
                               title='High Gamma 60-100 Hz', show=False)
            mne.viz.tight_layout()
            plt.title(f'{stim_type}-{trial}')
            plt.show()
    
            if save_plots:
                save_path1 = join(figures_path, 'grand_averages/sensor_space/tfr',
                                  stim_type + '_' + trial + '_tf' + \
                                  filter_string(lowpass, highpass) + '.jpg')
                fig1.savefig(save_path1, dpi=600)
                print('figure: ' + save_path1 + ' has been saved')
                save_path2 = join(figures_path, 'grand_averages/sensor_space/tfr',
                                  stim_type + '_' + trial + '_tf_topo' + \
                                  filter_string(lowpass, highpass) + '.jpg')
                fig2.savefig(save_path2, dpi=600)
                print('figure: ' + save_path2 + ' has been saved')
                save_path3 = join(figures_path, 'grand_averages/sensor_space/tfr',
                                  stim_type + '_' + trial + '_tf_joint' + \
                                  filter_string(lowpass, highpass) + '.jpg')
                fig3.savefig(save_path3, dpi=600)
                print('figure: ' + save_path3 + ' has been saved')
                save_path4 = join(figures_path, 'grand_averages/sensor_space/tfr',
                                  stim_type + '_' + trial + '_tf_oscs' + \
                                  filter_string(lowpass, highpass) + '.jpg')
                fig4.savefig(save_path4, dpi=600)
                print('figure: ' + save_path4 + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')
            
            close_all()

@decor.topline
def plot_grand_avg_stc(lowpass, highpass, save_dir_averages,
                       grand_avg_dict, mne_evoked_time, morph_to,
                       subjects_dir, event_id, save_plots,
                       figures_path):
    
    ga_dict = io.read_grand_avg_stcs(lowpass, highpass, save_dir_averages,
                                     grand_avg_dict, event_id)

    for stim_type in ga_dict:
        for trial in ga_dict[stim_type]:
            for idx, t in enumerate(mne_evoked_time):
                brain = ga_dict[stim_type][trial].plot(subject=morph_to,
                                subjects_dir=subjects_dir, size=(1600,800),
                                title=f'{stim_type}-{trial}', hemi='split',
                                views='lat', initial_time=t)
                brain.title = stim_type+'-'+trial

                if save_plots:
                    save_path = join(figures_path, 'grand_averages/source_space/stc',
                                     stim_type + '_' + trial + \
                                     filter_string(lowpass, highpass) + \
                                     '_' + str(idx) + '.jpg')
                    brain.save_image(save_path)
                    print('figure: ' + save_path + ' has been saved')
    
                else:
                    print('Not saving plots; set "save_plots" to "True" to save')

@decor.topline
def plot_grand_avg_stc_anim(lowpass, highpass, save_dir_averages,
                                grand_avg_dict, stc_animation,
                                morph_to, subjects_dir, event_id,
                                save_plots, figures_path):
    
    ga_dict = io.read_grand_avg_stcs(lowpass, highpass, save_dir_averages,
                                     grand_avg_dict, event_id)

    for stim_type in ga_dict:
        for trial in ga_dict[stim_type]:
            brain = ga_dict[stim_type][trial].plot(subject=morph_to,
                            subjects_dir=subjects_dir, size=(1600,800),
                            title=f'{stim_type}-{trial}', hemi='split',
                            views='lat')
            brain.title = stim_type+'-'+trial
            
            print('Saving Video')
            save_path = join(figures_path, 'grand_averages/source_space/stc_movie',
                             stim_type + '_' + trial + \
                             filter_string(lowpass, highpass) + '.mp4')
            brain.save_movie(save_path, time_dilation=30,
                             tmin=stc_animation[0], tmax=stc_animation[1], framerate=30)
            mlab.close()

@decor.topline
def plot_grand_avg_connect(lowpass, highpass, save_dir_averages,
                           grand_avg_dict, subjects_dir, morph_to, event_id,
                           con_methods, con_fmin, con_fmax,
                           save_plots, figures_path):
    
    ga_dict = io.read_grand_avg_connect(lowpass, highpass, save_dir_averages,
                                        grand_avg_dict, con_methods,
                                        con_fmin, con_fmax)

    # Get labels for FreeSurfer 'aparc' cortical parcellation with 34 labels/hemi
    labels = mne.read_labels_from_annot(morph_to, parc='aparc',
                                        subjects_dir=subjects_dir)
    label_colors = [label.color for label in labels]
    for l in labels:
        if l.name=='unknown-lh':
            del labels[labels.index(l)]
            print('unknown-lh removed')
            


    # First, we reorder the labels based on their location in the left hemi
    label_names = [label.name for label in labels]
    
    lh_labels = [l_name for l_name in label_names if l_name.endswith('lh')]
    
    # Get the y-location of the label
    label_ypos = list()
    for l_name in lh_labels:
        idx = label_names.index(l_name)
        ypos = np.mean(labels[idx].pos[:, 1])
        label_ypos.append(ypos)
    
    # Reorder the labels based on their location
    lh_labels = [label for (yp, label) in sorted(zip(label_ypos, lh_labels))]
    
    # For the right hemi
    rh_labels = [label[:-2] + 'rh' for label in lh_labels]
    
    # Save the plot order and create a circular layout
    node_order = list()
    node_order.extend(lh_labels[::-1])  # reverse the order
    node_order.extend(rh_labels)
    
    node_angles = mne.viz.circular_layout(label_names, node_order, start_pos=90,
                                          group_boundaries=[0, len(label_names) / 2])

    for stim_type in ga_dict:
        for method in ga_dict[stim_type]:
            fig, axes = mne.viz.plot_connectivity_circle(ga_dict[stim_type][method],
                                                         label_names, n_lines=300,
                                                         node_angles=node_angles,
                                                         node_colors=label_colors,
                                                         title=method+'_'+str(con_fmin)+'-'+str(con_fmax))
            if save_plots:
                save_path = join(figures_path, 'grand_averages/source_space/connectivity', stim_type + \
                                 filter_string(lowpass, highpass) + \
                                 '_' + str(con_fmin) + '-' + str(con_fmax) + \
                                 '_' + method + '.jpg')
                fig.savefig(save_path, dpi=600, facecolor='k', edgecolor='k')
                print('figure: ' + save_path + ' has been saved')
            else:
                print('Not saving plots; set "save_plots" to "True" to save')
        close_all()

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
    gc.collect()
