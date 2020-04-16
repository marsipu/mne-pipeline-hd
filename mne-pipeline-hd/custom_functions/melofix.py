from os.path import join

import mne
import numpy as np

from basic_functions import loading, operations as op
from pipeline_functions import decorators as decor


@decor.topline
def melofix_event_handling(name, save_dir, adjust_timeline_by_msec, overwrite):
    events_name = name + '-eve.fif'
    events_path = join(save_dir, events_name)

    try:
        events = loading.read_events(name, save_dir)
    except FileNotFoundError:
        print('No events found, running find_events...')
        op.find_events(name, save_dir, adjust_timeline_by_msec, overwrite)
        events = loading.read_events(name, save_dir)

    assert len(events) != 0, 'No events found'

    # Event-ID assignment for Melody-Fixed-Paradigm
    for n in range(len(events)):
        if events[n, 2] == 58:
            # Fixed Paradigm
            if events[n - 1, 2] == events[n - 2, 2] == events[n - 3, 2] == events[n - 4, 2]:
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

@decor.topline
def evokeds_apply_baseline(name, save_dir, highpass, lowpass):
    evokeds = loading.read_evokeds(name, save_dir, highpass, lowpass)
    new_evokeds = []
    evokeds_name = name + op.filter_string(highpass, lowpass) + '-ave.fif'
    evokeds_path = join(save_dir, evokeds_name)
    for evoked in evokeds:
        evoked = evoked.apply_baseline((-0.1, 0))
        new_evokeds.append(evoked)
    mne.write_evokeds(evokeds_path, new_evokeds)
