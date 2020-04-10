import re
import statistics as st
from os.path import join

import mne
import numpy as np
from matplotlib import pyplot as plt

from basic_functions import io, operations as op, plot as plot
from pipeline_functions import decorators as decor, utilities as ut


@decor.topline
def add_motor_erm_files():
    pass


@decor.topline
def pp_eog_digitize_handling(name, save_dir, highpass, lowpass, project):
    raw = io.read_filtered(name, save_dir, highpass, lowpass)
    eeg_in_data = False
    for ch in raw.info['chs']:
        if ch['kind'] == 2:
            eeg_in_data = True

    if project.parameters['eog_digitized'] and eeg_in_data:
        digi = raw.info['dig']
        if len(digi) >= 108:
            if digi[-1]['kind'] != 3:
                for i in digi[-4:]:
                    i['kind'] = 3
                raw.info['dig'] = digi
                print('Set EOG-Digitization-Points to kind 3 and saved')
            else:
                print('EOG-Digitization-Points already set to kind 3')

    filter_name = name + op.filter_string(highpass, lowpass) + '-raw.fif'
    filter_path = join(save_dir, filter_name)
    raw.save(filter_path, overwrite=True)


@decor.topline
def pp_event_handling(name, save_dir, adjust_timeline_by_msec, overwrite,
                      pscripts_path, save_plots, figures_path):
    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)

    try:
        events = io.read_events(name, save_dir)
    except FileNotFoundError:
        print('No events found, running find_events...')
        op.find_events(name, save_dir, adjust_timeline_by_msec, overwrite)
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
                        pscripts_path, values={'mean': diff1_mean,
                                               'stdev': diff1_stdev})

    # if func_dict['motor_erm_analysis']:
    #     for x in range(np.size(events, axis=0) - 3):
    #         if events[x, 2] == 2:
    #             if events[x + 2, 2] == 4:
    #                 l2.append(events[x + 2, 0] - events[x, 0])
    #     diff2_mean = st.mean(l2)
    #     diff2_stdev = st.stdev(l2)
    #     ut.dict_filehandler(name, 'MotStart1-MotStart2_diffs',
    #                         pscripts_path, values={'mean': diff2_mean,
    #                                                  'stdev': diff2_stdev})
    # else:
    for x in range(np.size(events, axis=0) - 3):
        if events[x, 2] == 2:
            if events[x + 3, 2] == 4:
                l2.append(events[x + 3, 0] - events[x, 0])
    diff2_mean = st.mean(l2)
    diff2_stdev = st.stdev(l2)
    ut.dict_filehandler(name, 'MotStart1-MotStart2_diffs',
                        pscripts_path, values={'mean': diff2_mean,
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
def pp_combine_evokeds_ab(data_path, save_dir_averages, highpass, lowpass, ab_dict):
    for title in ab_dict:
        print(f'abs for {title}')
        ab_ev_dict = dict()
        channels = list()
        trials = set()
        for name in ab_dict[title]:
            save_dir = join(data_path, name)
            evokeds = io.read_evokeds(name, save_dir, highpass, lowpass)
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
        evokeds_name = f'{title}{op.filter_string(highpass, lowpass)}-ave.fif'
        evokeds_path = join(save_dir_averages, 'ab_combined', evokeds_name)
        mne.write_evokeds(evokeds_path, evokeds)


@decor.topline
def pp_alignment(ab_dict, cond_dict, sub_dict, data_path, highpass, lowpass, pscripts_path,
                 event_id, subjects_dir, inverse_method, source_space_method,
                 parcellation, figures_path):
    # Noch problematisch: pp9_64, pp19_64
    # Mit ab-average werden die nicht alignierten falsch gemittelt, Annahme lag zu Mitte zwischen ab

    ab_gfp_data = dict()
    ab_ltc_data = dict()
    ab_gfp_avg_data = dict()
    ab_ltc_avg_data = dict()
    ab_gfp_max_dict = dict()
    ab_ltc_max_dict = dict()

    for title in ab_dict:
        print('--------' + title + '--------')
        names = ab_dict[title]
        pattern = r'pp[0-9]+[a-z]?'
        match = re.match(pattern, title)
        prefix = match.group()
        subtomri = sub_dict[prefix]
        src = io.read_source_space(subtomri, subjects_dir, source_space_method)
        cond = cond_dict[ab_dict[title][0]]
        for name in ab_dict[title]:
            # Assumes, that first evoked in evokeds is LBT
            save_dir = join(data_path, name)
            e = io.read_evokeds(name, save_dir, highpass, lowpass)[0]
            e.crop(-0.1, 0.3)
            gfp = op.calculate_gfp(e)
            ab_gfp_data[name] = gfp

            n_stc = io.read_normal_source_estimates(name, save_dir, highpass, lowpass, inverse_method, event_id)['LBT']
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
            ab_llags, ab_lcorr, ab_lmax_lag, ab_lmax_val = cross_correlation(l1, l2)

            # Evaluate appropriate lags, threshold: normed correlation >= 0.8
            if ab_gmax_lag != 0 and ab_lmax_lag != 0:
                if abs(ab_gmax_val) >= 0.7 and abs(ab_lmax_val) >= 0.7:
                    ab_lag = ab_lmax_lag  # Arbitrary choice for ltc being more specific
                elif abs(ab_gmax_val) >= 0.7:
                    ab_lag = ab_gmax_lag
                elif abs(ab_lmax_val) >= 0.7:
                    ab_lag = ab_lmax_lag
                else:
                    ab_lag = 0
            elif ab_gmax_lag != 0:
                if abs(ab_gmax_val) >= 0.7:
                    ab_lag = ab_gmax_lag
                else:
                    ab_lag = 0
            elif ab_lmax_lag != 0:
                if abs(ab_lmax_val) >= 0.7:
                    ab_lag = ab_lmax_lag
                else:
                    ab_lag = 0
            else:
                ab_lag = 0
                print('No lags in gfp or ltc')

            # ab_lag hast to be even to make all resulting averages the same length
            if ab_lag % 2 == 0:
                abl = int(ab_lag)
                ablh = int(ab_lag / 2)
            else:
                if ab_lag > 0:
                    abl = int(ab_lag - 1)
                elif ab_lag < 0:
                    abl = int(ab_lag + 1)
                else:
                    abl = int(ab_lag)
                ablh = int(ab_lag / 2)

            # Method 1: Applying Lag to single-files for each round (ab, sub, cond)
            # Make ab-averages to improve SNR
            # The partner-data is aligned with ab_lag and averaged
            # The single overhang of the base-data is added to the partner-data, thus avg=base_data at overhang

            # if ab_lag < 0:
            #     g1_applag = np.append(g2[:-abl], g1[:abl])
            #     g2_applag = np.append(g2[-abl:], g1[abl:])
            #     g1_avg = (g1 + g2_applag) / 2
            #     g2_avg = (g2 + g1_applag) / 2
            #
            #     l1_applag = np.append(l2[:-abl], l1[:abl])
            #     l2_applag = np.append(l2[-abl:], l1[abl:])
            #     l1_avg = (l1 + l2_applag) / 2
            #     l2_avg = (l2 + l1_applag) / 2
            # elif ab_lag > 0:
            #     g1_applag = np.append(g1[abl:], g2[-abl:])
            #     g2_applag = np.append(g1[:abl], g2[:-abl])
            #     g1_avg = (g1 + g2_applag) / 2
            #     g2_avg = (g2 + g1_applag) / 2
            #
            #     l1_applag = np.append(l1[abl:], l2[-abl:])
            #     l2_applag = np.append(l1[:abl], l2[:-abl])
            #     l1_avg = (l1 + l2_applag) / 2
            #     l2_avg = (l2 + l1_applag) / 2
            # else:
            #     g1_avg = (g1 + g2) / 2
            #     g2_avg = (g1 + g2) / 2
            #     l1_avg = (l1 + l2) / 2
            #     l2_avg = (l1 + l2) / 2

            # ab_gfp_avg_data[n1] = g1_avg
            # ab_gfp_avg_data[n2] = g2_avg
            # ab_ltc_avg_data[n1] = l1_avg
            # ab_ltc_avg_data[n2] = l2_avg

            # Method 2: Align abs and create ab-average of orig-length (cut ab_lag//2 at end of each file)
            # then continue next rounds (sub, cond) with the average of the preceding round

            if abl < 0:
                g1_applag = np.append(g2[-ablh:-abl], g1[:ablh])
                g2_applag = np.append(g2[-ablh:], g1[abl:ablh])
                g_ab_avg = (g1_applag + g2_applag) / 2

                l1_applag = np.append(l2[-ablh:-abl], l1[:ablh])
                l2_applag = np.append(l2[-ablh:], l1[abl:ablh])
                l_ab_avg = (l1_applag + l2_applag) / 2
            elif abl > 0:
                g1_applag = np.append(g1[ablh:], g2[-abl:-ablh])
                g2_applag = np.append(g1[ablh:abl], g2[:-ablh])
                g_ab_avg = (g1_applag + g2_applag) / 2

                l1_applag = np.append(l1[ablh:], l2[-abl:-ablh])
                l2_applag = np.append(l1[ablh:abl], l2[:-ablh])
                l_ab_avg = (l1_applag + l2_applag) / 2
            else:
                g_ab_avg = (g1 + g2) / 2
                l_ab_avg = (l1 + l2) / 2

            g_ab_max = max(abs(g_ab_avg))
            l_ab_max = max(abs(l_ab_avg))

            if cond in ab_gfp_avg_data:
                ab_gfp_avg_data[cond].update({title: g_ab_avg})
            else:
                ab_gfp_avg_data[cond] = {title: g_ab_avg}
            if cond in ab_gfp_max_dict:
                ab_gfp_max_dict[cond].update({title: g_ab_max})
            else:
                ab_gfp_max_dict[cond] = {title: g_ab_max}

            if cond in ab_ltc_avg_data:
                ab_ltc_avg_data[cond].update({title: l_ab_avg})
            else:
                ab_ltc_avg_data[cond] = {title: l_ab_avg}
            if cond in ab_ltc_max_dict:
                ab_ltc_max_dict[cond].update({title: l_ab_max})
            else:
                ab_ltc_max_dict[cond] = {title: l_ab_max}

            # Save lags to dict, ab_lag applies to data_b
            ut.dict_filehandler(title, 'ab_lags', pscripts_path,
                                {'gfp_lag': ab_gmax_lag, 'gfp_val': round(ab_gmax_val, 2),
                                 'ltc_lag': ab_lmax_lag, 'ltc_val': round(ab_lmax_val, 2),
                                 'ab_lag': abl})

            # Plot ab_compare
            plot_latency_alignment(f'{title}_ab', abl, n1, n2,
                                   g1, g2, g_ab_avg,
                                   l1, l2, l_ab_avg,
                                   ab_glags, ab_gcorr, ab_gmax_lag, ab_gmax_val,
                                   ab_llags, ab_lcorr, ab_lmax_lag, ab_lmax_val,
                                   figures_path, highpass, lowpass)
            plot.close_all()
        else:
            print('No b-measurement available')
            ut.dict_filehandler(title, 'ab_lags', pscripts_path,
                                {'gfp_lag': 0, 'gfp_val': 1, 'ltc_lag': 0, 'ltc_val': 1, 'ab_lag': 0})
            if cond in ab_gfp_avg_data:
                ab_gfp_avg_data[cond].update({title: ab_gfp_data[names[0]]})
            else:
                ab_gfp_avg_data[cond] = {title: ab_gfp_data[names[0]]}

            if cond in ab_ltc_avg_data:
                ab_ltc_avg_data[cond].update({title: ab_ltc_data[names[0]]})
            else:
                ab_ltc_avg_data[cond] = {title: ab_ltc_data[names[0]]}

    ga_avg_gfp_data = dict()
    ga_avg_ltc_data = dict()

    for cond in ab_gfp_avg_data:
        print('%%%%%%%%%' + cond + '%%%%%%%%%')
        cond_avg_gfp_data = dict()
        cond_avg_ltc_data = dict()

        # Comparision of absolute max in each ab-average to determine
        # best signal to cross-correlate all signals on
        title_max_gfp = max(ab_gfp_max_dict[cond], key=ab_gfp_max_dict[cond].get)
        title_max_ltc = max(ab_ltc_max_dict[cond], key=ab_ltc_max_dict[cond].get)

        print(f'{title_max_gfp} as best signal for gfp-condition-average')
        print(f'{title_max_ltc} as best signal for ltc-condition-average')

        gc1 = ab_gfp_avg_data[cond][title_max_gfp]
        lc1 = ab_ltc_avg_data[cond][title_max_ltc]

        for title in ab_gfp_avg_data[cond]:
            print('--------' + title + '--------')
            gc2 = ab_gfp_avg_data[cond][title]
            lc2 = ab_ltc_avg_data[cond][title]

            # cross-correlation of cond-gfps
            cond_glags, cond_gcorr, cond_gmax_lag, cond_gmax_val = cross_correlation(gc1, gc2)

            # cross-correlation of cond-ltcs in postcentral-lh
            cond_llags, cond_lcorr, cond_lmax_lag, cond_lmax_val = cross_correlation(lc1, lc2)

            # Evaluate appropriate lags, threshold: normed correlation >= 0.8
            if cond_gmax_lag != 0 and cond_lmax_lag != 0:
                if abs(cond_gmax_val) >= 0.7 and abs(cond_lmax_val) >= 0.7:
                    cond_lag = cond_lmax_lag  # Arbitrary choice for ltc being more specific
                elif abs(cond_gmax_val) >= 0.7:
                    cond_lag = cond_gmax_lag
                elif abs(cond_lmax_val) >= 0.7:
                    cond_lag = cond_lmax_lag
                else:
                    cond_lag = 0
            elif cond_gmax_lag != 0:
                if abs(cond_gmax_val) >= 0.7:
                    cond_lag = cond_gmax_lag
                else:
                    cond_lag = 0
            elif cond_lmax_lag != 0:
                if abs(cond_lmax_val) >= 0.7:
                    cond_lag = cond_lmax_lag
                else:
                    cond_lag = 0
            else:
                cond_lag = 0
                print('No lags in gfp or ltc')

            cl = int(cond_lag)
            # apply lag to title-signal with adding missing signal from best-signal
            if cond_lag < 0:
                gc2_applag = np.append(gc2[-cl:], gc1[cl:])
                lc2_applag = np.append(lc2[-cl:], lc1[cl:])

            elif cond_lag > 0:
                gc2_applag = np.append(gc1[:cl], gc2[:-cl])
                lc2_applag = np.append(lc1[:cl], lc2[:-cl])
            else:
                gc2_applag = gc2
                lc2_applag = lc2

            if title == title_max_gfp:
                pass
            else:
                cond_avg_gfp_data[title] = gc2_applag
            if title == title_max_ltc:
                pass
            else:
                cond_avg_ltc_data[title] = lc2_applag

            plot_latency_alignment(f'{title}_{cond}', cl, {'gfp': title_max_gfp, 'ltc': title_max_ltc}, title,
                                   gc1, gc2, None, lc1, lc2, None,
                                   cond_glags, cond_gcorr, cond_gmax_lag, cond_gmax_val,
                                   cond_llags, cond_lcorr, cond_lmax_lag, cond_lmax_val,
                                   figures_path, highpass, lowpass)
            plot.close_all()

            # Save lags to dict, cond-lag applies to best-signal
            ut.dict_filehandler(title, 'cond_lags', pscripts_path,
                                {'gfp_lag': cond_gmax_lag, 'gfp_val': round(cond_gmax_val, 2),
                                 'ltc_lag': cond_lmax_lag, 'ltc_val': round(cond_lmax_val, 2),
                                 'cond_lag': cl})
        cond_avg_gfp_data[title_max_gfp] = gc1
        cond_avg_ltc_data[title_max_ltc] = lc1

        cond_avg_gfp = 0
        for k in cond_avg_gfp_data:
            cond_avg_gfp += cond_avg_gfp_data[k]
        cond_avg_gfp /= len(cond_avg_gfp_data)
        ga_avg_gfp_data[cond] = cond_avg_gfp

        cond_avg_ltc = 0
        for k in cond_avg_ltc_data:
            cond_avg_ltc += cond_avg_ltc_data[k]
        cond_avg_ltc /= len(cond_avg_ltc_data)
        ga_avg_ltc_data[cond] = cond_avg_ltc

    cond_max_gfp = max(ga_avg_gfp_data, key=ga_avg_gfp_data.get)
    cond_max_ltc = max(ga_avg_ltc_data, key=ga_avg_ltc_data.get)

    ga1 = ga_avg_gfp_data[cond_max_gfp]
    la1 = ga_avg_ltc_data[cond_max_ltc]

    for cond in ga_avg_gfp_data:
        print('--------' + cond + '--------')
        ga2 = ga_avg_gfp_data[cond]
        la2 = ga_avg_ltc_data[cond]

        # cross-correlation of cond-gfps
        ga_glags, ga_gcorr, ga_gmax_lag, ga_gmax_val = cross_correlation(ga1, ga2)

        # cross-correlation of cond-ltcs in postcentral-lh
        ga_llags, ga_lcorr, ga_lmax_lag, ga_lmax_val = cross_correlation(la1, la2)

        # Evaluate appropriate lags, threshold: normed correlation >= 0.8
        if ga_gmax_lag != 0 and ga_lmax_lag != 0:
            if abs(ga_gmax_val) >= 0.7 and abs(ga_lmax_val) >= 0.7:
                ga_lag = ga_lmax_val  # Arbitrary choice for ltc being more specific
            elif abs(ga_gmax_val) >= 0.7:
                ga_lag = ga_gmax_lag
            elif abs(ga_lmax_val) >= 0.7:
                ga_lag = ga_lmax_lag
            else:
                ga_lag = 0
        elif ga_gmax_lag != 0:
            if abs(ga_gmax_val) >= 0.7:
                ga_lag = ga_gmax_lag
            else:
                ga_lag = 0
        elif ga_lmax_lag != 0:
            if abs(ga_lmax_val) >= 0.7:
                ga_lag = ga_lmax_lag
            else:
                ga_lag = 0
        else:
            ga_lag = 0
            print('No lags in gfp or ltc')


@decor.small_func
def cross_correlation(x, y):
    nx = (len(x) + len(y)) // 2
    if nx != len(y):
        raise ValueError('x and y must be equal length')
    correls = np.correlate(x, y, mode="full")
    # Normed correlation values
    correls /= np.sqrt(np.dot(x, x) * np.dot(y, y))
    # maxlags = int(nx/2) - 1
    maxlags = int(len(correls) / 2)
    lags = np.arange(-maxlags, maxlags + 1)

    max_lag = lags[np.argmax(np.abs(correls))]
    max_val = correls[np.argmax(np.abs(correls))]

    return lags, correls, max_lag, max_val


@decor.small_func
def plot_latency_alignment(layer, lag, n1, n2,
                           g1, g2, g_avg,
                           l1, l2, l_avg,
                           glags, gcorr, gmax_lag, gmax_val,
                           llags, lcorr, lmax_lag, lmax_val,
                           figures_path, highpass, lowpass):
    if lag != 0:
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
    if isinstance(n1, dict):
        n1a = n1['gfp']
        n1b = n1['ltc']
    else:
        n1a = n1
        n1b = n1

    axes[0, 0].plot(g1, label=n1a)
    axes[0, 0].plot(g2, label=n2)
    if g_avg:
        axes[0, 0].plot(g_avg, label='ab_average')
    axes[0, 0].legend()
    axes[0, 0].set_title(f'GFP\'s')

    axes[0, 1].plot(glags, gcorr)
    axes[0, 1].plot(gmax_lag, gmax_val, 'rx')
    axes[0, 1].set_title(f'Cross-Correlation, lag = {gmax_lag}')

    # Plot label-time-courses of postcentral-lh
    axes[1, 0].plot(l1, label=n1b)
    axes[1, 0].plot(l2, label=n2)
    if l_avg:
        axes[1, 0].plot(l_avg, label='ab_average')
    axes[1, 0].legend()
    axes[1, 0].set_title(f'Label-Time-Course in postcentral-lh')

    axes[1, 1].plot(llags, lcorr)
    axes[1, 1].plot(lmax_lag, lmax_val, 'rx')
    axes[1, 1].set_title(f'Cross-Correlation, lag = {lmax_lag}')

    if lag != 0:
        # Apply lag for comparision to gfps (lag applies to data_b)
        if lag < 0:
            g1a = g1[:lag]
            g2a = g2[-lag:]
        elif lag > 0:
            g1a = g1[lag:]
            g2a = g2[:-lag]
        else:
            g1a = g1
            g2a = g2
        axes[0, 2].plot(g1a, label=n1a)
        axes[0, 2].plot(g2a, label=n2)
        axes[0, 2].legend()
        axes[0, 2].set_title(f'GFP\'s corrected with ab_lag = {lag}')

        # Apply lag for comparision to ltcs(lag applies to data_b)
        if lmax_lag < 0:
            l1a = l1[:lag]
            l2a = l2[-lag:]
        elif lmax_lag > 0:
            l1a = l1[lag:]
            l2a = l2[:-lag]
        else:
            l1a = l1
            l2a = l2
        axes[1, 2].plot(l1a, label=n1b)
        axes[1, 2].plot(l2a, label=n2)
        axes[1, 2].legend()
        axes[1, 2].set_title(f'LTC\'s corrected with ab_lag = {lag}')

    filename = join(figures_path, 'align_peaks', f'{layer}{op.filter_string(highpass, lowpass)}_xcorr.jpg')
    plt.savefig(filename)


# def apply_alignment():
#     # Apply alignment over changing the
#     det_peaks = ut.read_dict_file('peak_alignment', pscripts_path)
#     for name in det_peaks:
#         save_dir = join(data_path, name)


def pp_get_subject_groups(mw, pr, all_files, combine_ab):
    files = list()

    pre_order_dict = dict()
    order_dict = dict()
    ab_dict = dict()
    comp_dict = dict()
    avg_dict = dict()
    sub_files_dict = dict()
    cond_dict = dict()

    # pattern = r'pp[0-9][0-9]*[a-z]*_[0-9]{0,3}t?_[a,b]$'
    basic_pattern = r'(pp[0-9][0-9]*[a-z]*)_([0-9]{0,3}t?)_([a,b]$)'
    for s in all_files:
        match = re.match(basic_pattern, s)
        if match:
            files.append(s)

    # prepare order_dict
    for s in files:
        match = re.match(basic_pattern, s)
        key = match.group(1) + '_' + match.group(3)
        if key in pre_order_dict:
            pre_order_dict[key].append(match.group(2))
        else:
            pre_order_dict.update({key: [match.group(2)]})

    # Assign string-groups to modalities
    for key in pre_order_dict:
        v_list = pre_order_dict[key]
        order_dict.update({key: dict()})
        for it in v_list:
            if it == '16' or it == '32':
                order_dict[key].update({it: 'low'})
            if it == '64' or it == '128':
                order_dict[key].update({it: 'middle'})
            if it == '256' or it == '512':
                order_dict[key].update({it: 'high'})
            if it == 't':
                order_dict[key].update({it: 'tactile'})

    # Make a dict, where a/b-files are grouped together
    for s in files:
        match = re.match(basic_pattern, s)
        key = match.group(1) + '_' + match.group(2)
        if key in ab_dict:
            ab_dict[key].append(s)
        else:
            ab_dict.update({key: [s]})

    # Make a dict for each subject, where the files are ordere by their modality
    for s in files:
        match = re.match(basic_pattern, s)
        key = match.group(1) + '_' + match.group(3)
        sub_key = order_dict[key][match.group(2)]
        if combine_ab:
            key = match.group(1)
            if key in comp_dict:
                if sub_key in comp_dict[key]:
                    comp_dict[key][sub_key].append(s)
                else:
                    comp_dict[key].update({sub_key: [s]})
            else:
                comp_dict.update({key: {sub_key: [s]}})
        else:
            if key in comp_dict:
                comp_dict[key].update({sub_key: [s]})
            else:
                comp_dict.update({key: {sub_key: [s]}})

    # Make a dict, where each file get its modality as value
    for s in files:
        match = re.match(basic_pattern, s)
        val = order_dict[match.group(1) + '_' + match.group(3)][match.group(2)]
        cond_dict[s] = val

    # Make a grand-avg-dict with all files of a modality in one list together
    for s in files:
        match = re.match(basic_pattern, s)
        if combine_ab:
            key = order_dict[match.group(1) + '_' + match.group(3)][match.group(2)]
        else:
            key = order_dict[match.group(1) + '_' + match.group(3)][match.group(2)] + '_' + match.group(3)
        if key in avg_dict:
            avg_dict[key].append(s)
        else:
            avg_dict.update({key: [s]})

    # Make a dict with all the files for one subject
    for s in files:
        match = re.match(basic_pattern, s)
        key = match.group(1)
        if key in sub_files_dict:
            sub_files_dict[key].append(s)
        else:
            sub_files_dict.update({key: [s]})

    pr.grand_avg_dict = avg_dict
    pr.ab_dict = ab_dict
    pr.comp_dict = comp_dict
    pr.sub_files_dict = sub_files_dict
    pr.cond_dict = cond_dict

    mw.subject_dock.ga_widget.update_treew()


def pp_file_selection():
    mw = None
    files = []
    quality = None
    modality = None
    quality_dict = {}
    basic_pattern = r'(pp[0-9][0-9]*[a-z]*)_([0-9]{0,3}t?)_([a,b]$)'
    if not mw.func_dict['erm_analysis'] and not mw.func_dict['motor_erm_analysis']:
        silenced_files = set()
        for file in files:
            if 'all' not in quality and quality is not '':
                file_quality = int(quality_dict[file])
                if file_quality not in quality:
                    silenced_files.add(file)

            if 'all' not in modality:
                match = re.match(basic_pattern, file)
                file_modality = match.group(2)
                if file_modality not in modality:
                    silenced_files.add(file)

        for df in silenced_files:
            files.remove(df)


def pp_load_old_sub_dicts(pr, all_files, sub_dict, erm_dict):
    new_sub_dict = {}
    new_erm_dict = {}
    for file in all_files:
        for key in sub_dict:
            if key in file:
                new_sub_dict.update({file: sub_dict[key]})
        for key in erm_dict:
            if key in file:
                new_erm_dict.update({file: erm_dict[key]})

    pr.sub_dict = new_sub_dict
    pr.erm_dict = new_erm_dict
