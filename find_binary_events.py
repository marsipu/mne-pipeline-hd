import numpy as np
from itertools import combinations
from functools import reduce
import mne

# By Martin Schulz
# Binary Coding of 6 Stim Channels in Biomagenetism Lab Heidelberg

# prepare arrays
events = np.ndarray(shape=(0,3), dtype=np.int32)
evs = list()
evs_tol = list()


# Find events for each stim channel, append sample values to list
evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 001'])[:,0])
evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 002'])[:,0])
evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 003'])[:,0])
evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 004'])[:,0])
evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 005'])[:,0])
evs.append(mne.find_events(raw,min_duration=0.002,stim_channel=['STI 006'])[:,0])

"""
#test events
evs = [np.array([1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47,49,51,53,55,57,59,61,63])*10,
       np.array([2,3,6,7,10,11,14,15,18,19,22,23,26,27,30,31,34,35,38,39,42,43,46,47,50,51,54,55,58,59,62,63])*10,
       np.array([4,5,6,7,12,13,14,15,20,21,22,23,28,29,30,31,36,37,38,39,44,45,46,47,52,53,54,55,60,61,62,63])*10,
       np.array([8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,40,41,42,43,44,45,46,47,56,57,58,59,60,61,62,63])*10,
       np.array([16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63])*10,
       np.array([32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63])*10]
"""

for i in evs:

    # delete events in each channel, which are too close too each other (1ms)
    too_close = np.where(np.diff(i)<=1)
    if np.size(too_close)>=1:
        print(f'Two close events (1ms) at samples {i[too_close] + raw.first_samp}, first deleted')
        i = np.delete(i,too_close,0)
        evs[evs.index(i)] = i

    # add tolerance to each value
    i_tol = np.ndarray(shape = (0,1), dtype=np.int32)
    for t in i:
        i_tol = np.append(i_tol, t-1)
        i_tol = np.append(i_tol, t)
        i_tol = np.append(i_tol, t+1)

    evs_tol.append(i_tol)


# Get events from combinated Stim-Channels
equals = reduce(np.intersect1d, (evs_tol[0], evs_tol[1], evs_tol[2],
                                 evs_tol[3], evs_tol[4], evs_tol[5]))
#elimnate duplicated events
too_close = np.where(np.diff(equals)<=1)
if np.size(too_close)>=1:
    equals = np.delete(equals,too_close,0)
    equals -= 1 # correction, because of shift with deletion

for q in equals:
    if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
        events = np.append(events, [[q,0,63]], axis=0)


for a,b,c,d,e in combinations(range(6), 5):
    equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c],
                                     evs_tol[d], evs_tol[e]))
    too_close = np.where(np.diff(equals)<=1)
    if np.size(too_close)>=1:
        equals = np.delete(equals,too_close,0)
        equals -= 1

    for q in equals:
        if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
            events = np.append(events, [[q,0,int(2**a + 2**b + 2**c + 2**d + 2**e)]], axis=0)


for a,b,c,d in combinations(range(6), 4):
    equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c], evs_tol[d]))
    too_close = np.where(np.diff(equals)<=1)
    if np.size(too_close)>=1:
        equals = np.delete(equals,too_close,0)
        equals -= 1

    for q in equals:
        if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
            events = np.append(events, [[q,0,int(2**a + 2**b + 2**c + 2**d)]], axis=0)


for a,b,c in combinations(range(6), 3):
    equals = reduce(np.intersect1d, (evs_tol[a], evs_tol[b], evs_tol[c]))
    too_close = np.where(np.diff(equals)<=1)
    if np.size(too_close)>=1:
        equals = np.delete(equals,too_close,0)
        equals -= 1

    for q in equals:
        if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
            events = np.append(events, [[q,0,int(2**a + 2**b + 2**c)]], axis=0)


for a,b in combinations(range(6), 2):
    equals = np.intersect1d(evs_tol[a], evs_tol[b])
    too_close = np.where(np.diff(equals)<=1)
    if np.size(too_close)>=1:
        equals = np.delete(equals,too_close,0)
        equals -= 1

    for q in equals:
        if not q in events[:,0] and not q in events[:,0]+1 and not q in events[:,0]-1:
            events = np.append(events, [[q,0,int(2**a + 2**b)]], axis=0)


# Get single-channel events
for i in range(6):
    for e in evs[i]:
        if not e in events[:,0] and not e in events[:,0]+1 and not e in events[:,0]-1:
            events = np.append(events, [[e,0,2**i]], axis=0)

# stackoverflow way of sorting by only one column
events[events[:,0].argsort()]
