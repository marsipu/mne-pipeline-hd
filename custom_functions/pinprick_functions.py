import mne
import re
import numpy as np
import statistics as st
from matplotlib import pyplot as plt
from os import makedirs, listdir, environ, remove
from os.path import join, isfile, isdir, exists

from pipeline_functions import io_functions as io
from pipeline_functions import operations_functions as op
from pipeline_functions import plot_functions as plot
from pipeline_functions import utilities as ut
from pipeline_functions import decorators as decor


@decor.topline
def pp_event_handling(name, save_dir, adjust_timeline_by_msec, overwrite,
                      sub_script_path, save_plots, figures_path, exec_ops):

    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)

    try:
        events = io.read_events(name, save_dir)
    except FileNotFoundError:
        print('No events found, running find_events...')
        op.find_events(name, save_dir, adjust_timeline_by_msec, overwrite, exec_ops)
        events = io.read_events(name, save_dir)

    assert len(events) != 0, 'No events found'

    # delete Trigger 1 if not after Trigger 2 (due to mistake with light-barrier)
    removes = np.array([], dtype=int)
    for n in range(len(events)):
        if events[n, 2] == 1:
            if events[n - 1, 2] != 2:
                removes = np.append(removes, n)
                print(f'{events[n, 0]} removed Trigger 1')
    events = np.delete(events, removes, axis=0)

    # Rating
    pre_ratings = events[np.nonzero(np.logical_and(9 < events[:, 2], events[:, 2] < 20))]
    if len(pre_ratings) != 0:
        first_idx = np.nonzero(np.diff(pre_ratings[:, 0], axis=0) < 200)[0]
        last_idx = first_idx + 1
        ratings = pre_ratings[first_idx]
        ratings[:, 2] = (ratings[:, 2] - 10) * 10 + pre_ratings[last_idx][:, 2] - 10

        diff_ratings = np.copy(ratings)
        diff_ratings[np.nonzero(np.diff(ratings[:, 2]) < 0)[0] + 1, 2] = 5
        diff_ratings[np.nonzero(np.diff(ratings[:, 2]) == 0)[0] + 1, 2] = 6
        diff_ratings[np.nonzero(np.diff(ratings[:, 2]) > 0)[0] + 1, 2] = 7
        diff_ratings = np.delete(diff_ratings, [0], axis=0)

        pre_events = events[np.nonzero(events[:, 2] == 1)][:, 0]
        for n in range(len(diff_ratings)):
            diff_ratings[n, 0] = pre_events[np.nonzero(pre_events - diff_ratings[n, 0] < 0)][-1] + 3

        # Eliminate Duplicates
        diff_removes = np.array([], dtype=int)
        for n in range(1, len(diff_ratings)):
            if diff_ratings[n, 0] == diff_ratings[n - 1, 0]:
                diff_removes = np.append(diff_removes, n)
                print(f'{diff_ratings[n, 0]} removed as Duplicate')
        diff_ratings = np.delete(diff_ratings, diff_removes, axis=0)

        events = np.append(events, diff_ratings, axis=0)
        events = events[events[:, 0].argsort()]

        if save_plots:
            fig, ax1 = plt.subplots(figsize=(20, 10))
            ax1.plot(ratings[:, 2], 'b')
            ax1.set_ylim(0, 100)

            ax2 = ax1.twinx()
            ax2.plot(diff_ratings, 'og')
            ax2.set_ylim(4.5, 7.5)

            fig.tight_layout()
            plt.title(name + ' - rating')
            fig.show()

            save_path = join(figures_path, 'events', name + '-ratings.jpg')
            fig.savefig(save_path, dpi=600, overwrite=True)
            print('figure: ' + save_path + ' has been saved')

            plt.close(fig)
        else:
            print('Not saving plots; set "save_plots" to "True" to save')

    else:
        print('No Rating in Trig-Channels 10-19')

    # Calculate and Save Latencies
    l1 = []
    l2 = []
    for x in range(np.size(events, axis=0)):
        if events[x, 2] == 2:
            if events[x + 1, 2] == 1:
                l1.append(events[x + 1, 0] - events[x, 0])
    diff1_mean = st.mean(l1)
    diff1_stdev = st.stdev(l1)
    ut.dict_filehandler(name, 'MotStart-LBT_diffs',
                        sub_script_path, values={'mean': diff1_mean,
                                                 'stdev': diff1_stdev})

    if exec_ops['motor_erm_analysis']:
        for x in range(np.size(events, axis=0) - 3):
            if events[x, 2] == 2:
                if events[x + 2, 2] == 4:
                    l2.append(events[x + 2, 0] - events[x, 0])
        diff2_mean = st.mean(l2)
        diff2_stdev = st.stdev(l2)
        ut.dict_filehandler(name, 'MotStart1-MotStart2_diffs',
                            sub_script_path, values={'mean': diff2_mean,
                                                     'stdev': diff2_stdev})
    else:
        for x in range(np.size(events, axis=0) - 3):
            if events[x, 2] == 2:
                if events[x + 3, 2] == 4:
                    l2.append(events[x + 3, 0] - events[x, 0])
        diff2_mean = st.mean(l2)
        diff2_stdev = st.stdev(l2)
        ut.dict_filehandler(name, 'MotStart1-MotStart2_diffs',
                            sub_script_path, values={'mean': diff2_mean,
                                                     'stdev': diff2_stdev})

    # Latency-Correction for Offset-Trigger[4]
    for x in range(np.size(events, axis=0) - 3):
        if events[x, 2] == 2:
            if events[x + 1, 2] == 1:
                if events[x + 3, 2] == 4:
                    corr = diff1_mean - (events[x + 1, 0] - events[x, 0])
                    events[x + 3, 0] = events[x + 3, 0] + corr

    # unique event_ids
    ids = np.unique(events[:, 2])
    print('unique ID\'s assigned: ', ids)

    mne.event.write_events(events_path, events)


@decor.topline
def pp_combine_evokeds_ab(data_path, save_dir_averages, lowpass, highpass, ab_dict):
    for title in ab_dict:
        print(f'abs for {title}')
        ab_ev_dict = dict()
        channels = list()
        trials = set()
        for name in ab_dict[title]:
            save_dir = join(data_path, name)
            evokeds = io.read_evokeds(name, save_dir, lowpass, highpass)
            channels.append(set(evokeds[0].ch_names))
            for evoked in evokeds:
                trial = evoked.comment
                trials.add(trial)
                if trial in ab_ev_dict:
                    ab_ev_dict[trial].append(evoked)
                else:
                    ab_ev_dict.update({trial: [evoked]})

        # Make sure, that both evoked datasets got the same channels (Maybe some channels were discarded between measurements)
        channels = list(set.intersection(*channels))
        for trial in ab_ev_dict:
            ab_ev_dict[trial] = [evoked.pick_channels(channels) for evoked in ab_ev_dict[trial]]

        evokeds = list()
        for trial in ab_ev_dict:
            cmb_evokeds = mne.combine_evoked(ab_ev_dict[trial], weights='equal')
            evokeds.append(cmb_evokeds)
        evokeds_name = f'{title}{op.filter_string(lowpass, highpass)}-ave.fif'
        evokeds_path = join(save_dir_averages, 'ab_combined', evokeds_name)
        mne.write_evokeds(evokeds_path, evokeds)


@decor.topline
def pp_alignment(ab_dict, cond_dict, sub_dict, data_path, lowpass, highpass, sub_script_path,
                 event_id, subjects_dir, inverse_method, source_space_method,
                 parcellation, figures_path):

    # Noch problematisch: pp9_64, pp19_64
    # Mit ab-average werden die nicht alignierten falsch gemittelt, Annahme lag zu Mitte zwischen ab

    ab_gfp_data = dict()
    ab_ltc_data = dict()
    ab_lags = dict()

    for title in ab_dict:
        print('--------' + title + '--------')
        names = ab_dict[title]
        pattern = r'pp[0-9]+[a-z]?'
        match = re.match(pattern, title)
        prefix = match.group()
        subtomri = sub_dict[prefix]
        src = io.read_source_space(subtomri, subjects_dir, source_space_method)

        for name in ab_dict[title]:
            # Assumes, that first evoked in evokeds is LBT
            save_dir = join(data_path, name)
            e = io.read_evokeds(name, save_dir, lowpass, highpass)[0]
            e.crop(-0.1, 0.3)
            gfp = op.calculate_gfp(e)
            ab_gfp_data[name] = gfp

            n_stc = io.read_normal_source_estimates(name, save_dir, lowpass, highpass, inverse_method, event_id)['LBT']
            # get peaks from label-time-course
            labels = mne.read_labels_from_annot(subtomri, subjects_dir=subjects_dir, parc=parcellation)
            label = None
            for l in labels:
                if l.name == 'postcentral-lh':
                    label = l
            # Crop here only possible, if toi is set to (-0.1, ...) according to gfp.crop(-0.1, ...)
            ltc = n_stc.extract_label_time_course(label, src, mode='pca_flip')[0][:400]
            ab_ltc_data[name] = ltc

        # Cross-Correlate a and b
        if len(ab_dict[title]) > 1:
            # Plot Time-Course for a and b
            n1, n2 = names
            g1, g2 = ab_gfp_data[n1], ab_gfp_data[n2]
            l1, l2 = ab_ltc_data[n1], ab_ltc_data[n2]

            # cross-correlation of ab-gfps
            ab_glags, ab_gcorr, ab_gmax_lag, ab_gmax_val = cross_correlation(g1, g2)

            # cross-correlation of ab-label-time-courses in postcentral-lh
            llags, lcorr, ab_lmax_lag, ab_lmax_val = cross_correlation(l1, l2)

            # Evaluate appropriate lags, threshold: normed correlation >= 0.8
            if ab_gmax_lag != 0 and ab_lmax_lag != 0:
                if ab_gmax_val >= 0.7 and ab_lmax_val >= 0.7:
                    ab_lag = ab_lmax_lag
                    # if ab_gmax_lag != ab_lmax_lag:
                    #     if ab_gmax_val > ab_lmax_val:
                    #         ab_lag = ab_gmax_lag
                    #     else:
                    #         ab_lag = ab_lmax_lag
                    # else:
                    #     ab_lag = ab_gmax_lag
                elif ab_gmax_val >= 0.7:
                    ab_lag = ab_gmax_lag
                elif ab_lmax_val >= 0.7:
                    ab_lag = ab_lmax_lag
                else:
                    ab_lag = 0
            elif ab_gmax_lag != 0:
                if ab_gmax_val >= 0.7:
                    ab_lag = ab_gmax_lag
                else:
                    ab_lag = 0
            elif ab_lmax_lag != 0:
                if ab_lmax_val >= 0.7:
                    ab_lag = ab_lmax_lag
                else:
                    ab_lag = 0
            else:
                ab_lag = 0
                print('No lags in gfp or ltc')

            # Make ab-averages to improve SNR
            # The partner-data is aligned with ab_lag and averaged
            # The single overhang of the base-data is added to the partner-data, thus avg=base_data at overhang
            if ab_lag < 0:
                g1_applag = np.append(g1[:int(ab_lag)], g2[:-int(ab_lag)])
                g2_applag = np.append(g2[-int(ab_lag):], g1[int(ab_lag):])
                g1_avg = (g1 + g2_applag) / 2
                g2_avg = (g2 + g1_applag) / 2

                l1_applag = np.append(l1[:int(ab_lag)], l2[:-int(ab_lag)])
                l2_applag = np.append(l2[-int(ab_lag):], l1[int(ab_lag):])
                l1_avg = (l1 + l2_applag) / 2
                l2_avg = (l2 + l1_applag) / 2
            elif ab_lag > 0:
                g1_applag = np.append(g1[int(ab_lag):], g2[-int(ab_lag):])
                g2_applag = np.append(g2[:-int(ab_lag)], g1[:int(ab_lag)])
                g1_avg = (g1 + g2_applag) / 2
                g2_avg = (g2 + g1_applag) / 2

                l1_applag = np.append(l1[int(ab_lag):], l2[-int(ab_lag):])
                l2_applag = np.append(l2[:-int(ab_lag)], l1[:int(ab_lag)])
                l1_avg = (l1 + l2_applag) / 2
                l2_avg = (l2 + l1_applag) / 2
            else:
                g1_avg = g1
                g2_avg = g2
                l1_avg = l1
                l2_avg = l2

                # g1_avg = (g1 + g2) / 2
                # g2_avg = (g1 + g2) / 2
                # l1_avg = (l1 + l2) / 2
                # l2_avg = (l1 + l2) / 2

            ab_gfp_data[n1] = g1_avg
            ab_gfp_data[n2] = g2_avg
            ab_ltc_data[n1] = l1_avg
            ab_ltc_data[n2] = l2_avg
            # Save lags to dict, ab_lag applies to data_b
            ut.dict_filehandler(title, 'ab_lags', sub_script_path,
                                {'gfp_lag': ab_gmax_lag, 'gfp_val': round(ab_gmax_val, 2),
                                 'ltc_lag': ab_lmax_lag, 'ltc_val': round(ab_lmax_val, 2),
                                 'ab_lag': ab_lag})

            # Plot Compare Plot
            if ab_lag != 0:
                fig, axes = plt.subplots(nrows=2, ncols=3, sharex='col',
                                         gridspec_kw={'hspace': 0.1, 'wspace': 0.1,
                                                      'left': 0.05, 'right': 0.95,
                                                      'top': 0.95, 'bottom': 0.05},
                                         figsize=(18, 8))
            else:
                fig, axes = plt.subplots(nrows=2, ncols=2, sharex='col',
                                         gridspec_kw={'hspace': 0.1, 'wspace': 0.1,
                                                      'left': 0.05, 'right': 0.95,
                                                      'top': 0.95, 'bottom': 0.05},
                                         figsize=(18, 8))
            axes[0, 0].plot(g1, label=n1)
            axes[0, 0].plot(g2, label=n2)
            axes[0, 0].legend()
            axes[0, 0].set_title(f'GFP\'s')

            axes[0, 1].plot(ab_glags, ab_gcorr)
            axes[0, 1].plot(ab_gmax_lag, ab_gmax_val, 'rx')
            axes[0, 1].set_title(f'Cross-Correlation, lag = {ab_gmax_lag}')

            # Plot label-time-courses of postcentral-lh
            axes[1, 0].plot(l1, label=n1)
            axes[1, 0].plot(l2, label=n2)
            axes[1, 0].legend()
            axes[1, 0].set_title(f'Label-Time-Course in postcentral-lh')

            axes[1, 1].plot(llags, lcorr)
            axes[1, 1].plot(ab_lmax_lag, ab_lmax_val, 'rx')
            axes[1, 1].set_title(f'Cross-Correlation, lag = {ab_lmax_lag}')

            if ab_lag != 0:
                # Apply ab_lag for comparision (lag applies to data_b)
                if ab_lag < 0:
                    g1a = g1[:int(ab_lag)]
                    g2a = g2[-int(ab_lag):]
                elif ab_lag > 0:
                    g1a = g1[int(ab_lag):]
                    g2a = g2[:-int(ab_lag)]
                else:
                    g1a = g1
                    g2a = g2

                axes[0, 2].plot(g1a, label=n1)
                axes[0, 2].plot(g2a, label=n2)
                axes[0, 2].legend()
                axes[0, 2].set_title(f'GFP\'s corrected with ab_lag = {ab_lag}')

                # Apply ab_lag for comparision (lag applies to data_b)
                if ab_lmax_lag < 0:
                    l1a = l1[:int(ab_lag)]
                    l2a = l2[-int(ab_lag):]
                elif ab_lmax_lag > 0:
                    l1a = l1[int(ab_lag):]
                    l2a = l2[:-int(ab_lag)]
                else:
                    l1a = l1
                    l2a = l2

                axes[1, 2].plot(l1a, label=n1)
                axes[1, 2].plot(l2a, label=n2)
                axes[1, 2].legend()
                axes[1, 2].set_title(f'LTC\'s corrected with ab_lag = {ab_lag}')

            filename = join(figures_path, 'align_peaks', f'{title}{op.filter_string(lowpass, highpass)}_xcorr_ab.jpg')
            plt.savefig(filename)

        else:
            print('No b-measurement available')
            ut.dict_filehandler(title, 'ab_lags', sub_script_path,
                                {'gfp_lag': 0, 'gfp_val': 1, 'ltc_lag': 0, 'ltc_val': 1, 'ab_lag': 0})

    plot.close_all()


@decor.small_func
def cross_correlation(x, y):
    nx = len(x) + len(y)
    # if nx != len(y):
    #     raise ValueError('x and y must be equal length')
    correls = np.correlate(x, y, mode="full")
    # Normed correlation values
    correls /= np.sqrt(np.dot(x, x) * np.dot(y, y))
    # maxlags = int(nx/2) - 1
    maxlags = int(len(correls) / 2)
    lags = np.arange(-maxlags, maxlags + 1)

    max_lag = lags[np.argmax(np.abs(correls))]
    max_val = correls[np.argmax(np.abs(correls))]

    return lags, correls, max_lag, max_val


# def apply_alignment():
#     # Apply alignment over changing the
#     det_peaks = ut.read_dict_file('peak_alignment', sub_script_path)
#     for name in det_peaks:
#         save_dir = join(data_path, name)


