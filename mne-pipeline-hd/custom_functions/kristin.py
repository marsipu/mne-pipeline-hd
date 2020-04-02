from os.path import join

import mne
import numpy as np

from basic_functions import io, operations as op
from pipeline_functions import decorators as decor


@decor.topline
def kristin_event_handling(name, save_dir, adjust_timeline_by_msec, overwrite,
                           pscripts_path, save_plots, figures_path, func_dict):
    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)

    try:
        events = io.read_events(name, save_dir)
    except FileNotFoundError:
        print('No events found, running find_events...')
        op.find_events(name, save_dir, adjust_timeline_by_msec, overwrite, func_dict)
        events = io.read_events(name, save_dir)

    assert len(events) != 0, 'No events found'

    # Event-ID assignment for Melody-Fixed-Paradigm

    for n in range(len(events)):
        if events[n, 2] == 1:
            events[n, 2] = 8
        if events[n, 2] == 2:
            events[n, 2] = 8
        if events[n, 2] == 3:
            events[n, 2] = 8
        if events[n, 2] == 5:
            events[n, 2] = 9
        if events[n, 2] == 6:
            events[n, 2] = 9
        if events[n, 2] == 7:
            events[n, 2] = 9

    # unique event_ids
    ids = np.unique(events[:, 2])
    print('unique ID\'s assigned: ', ids)

    mne.event.write_events(events_path, events)

