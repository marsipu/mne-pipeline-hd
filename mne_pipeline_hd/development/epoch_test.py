import mne

from basic_functions import loading as ld

raw_path = 'D:/Rächner/Desktop/TestPath/TestProject1/data/pp12_t_a/pp12_t_a_1-100_Hz-raw.fif'
events_path = 'D:/Rächner/Desktop/TestPath/TestProject1/data/pp12_t_a/pp12_t_a-eve.fif'
name = 'pp12_t_a'
save_dir = 'D:/Rächner/Desktop/TestPath/TestProject1/data/pp12_t_a/'
raw = mne.io.read_raw_fif(raw_path, preload=True)
events = mne.read_events(events_path)
event_id1 = {'Test1': 1, 'Test2': 2, 'Test3': 3, 'Test4': 4}
event_id2 = {'Test2': 2}

epo_1 = mne.Epochs(raw, events, event_id1, picks=['grad'], tmin=-0.5, tmax=1.5, baseline=(-0.5, 0))
epo_2 = mne.Epochs(raw, events, event_id2, picks=['grad'], tmin=-0.5, tmax=1.5, baseline=(-0.5, 0))
epo_3 = mne.Epochs(raw, events, event_id2, picks=['grad'], tmin=-0.5, tmax=1.5, baseline=None)

epo_pipe = ld.read_epochs(name, save_dir, 1, 100)

a1 = epo_1['Test2'].average().plot()
a2 = epo_2['Test2'].average().plot()
a3 = epo_pipe['Test2'].average().plot()
