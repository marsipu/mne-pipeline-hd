# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2020, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
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
