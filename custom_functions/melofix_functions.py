import mne
import numpy as np
from os.path import join

from pipeline_functions import io_functions as io
from pipeline_functions import operations_functions as op


def melofix_event_handling(name, save_dir, adjust_timeline_by_msec, overwrite,
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

    # Event-ID assignment for Melody-Fixed-Paradigm
    for n in range(len(events)):
        if events[n, 2] == 58:
            # Fixed Paradigm
            if events[n - 1, 2] == events[n-2, 2] == events[n-3, 2] == events[n-4, 2]:
                # Fixed-Onset = 1
                events[n - 4, 2] = 1
                # Fixed 2-4
                events[n - 3, 2] = 2
                events[n - 2, 2] = 2
                events[n - 1, 2] = 2
            else:
                # Melody-Onset = 3
                events[n - 4, 2] = 3
                # Melody 2-4
                events[n - 3, 2] = 4
                events[n - 2, 2] = 4
                events[n - 1, 2] = 4

    # unique event_ids
    ids = np.unique(events[:, 2])
    print('unique ID\'s assigned: ', ids)

    mne.event.write_events(events_path, events)

