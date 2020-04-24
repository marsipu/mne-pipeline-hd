# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis of MEG data
based on: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: mne.pipeline@gmail.com
@github: marsipu/mne_pipeline_hd
"""
import functools


def topline(func):
    @functools.wraps(func)
    def wrapper_topline(*args, **kwargs):
        print('-' * 60)
        print(func.__name__)
        return func(*args, **kwargs)

    return wrapper_topline


def small_func(func):
    @functools.wraps(func)
    def wrapper_topline(*args, **kwargs):
        print(f'_______{func.__name__}_______')
        return func(*args, **kwargs)

    return wrapper_topline
