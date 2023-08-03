# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
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
