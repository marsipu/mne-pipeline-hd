import mne
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