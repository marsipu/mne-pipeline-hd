# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""

from multiprocessing import Pool

mp_pool = None


def close_mp_pool():
    if mp_pool is not None:
        mp_pool.close()
        mp_pool.join()


def init_mp_pool():
    global mp_pool

    close_mp_pool()
    mp_pool = Pool(1)
