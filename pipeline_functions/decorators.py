# -*- coding: utf-8 -*-
"""
Created on Wed Sep 19 15:21:50 2018

@author: Stumpi
"""
import functools

def topline(func):
    @functools.wraps(func)
    def wrapper_topline(*args, **kwargs):
        print('-'*60)
        print(func.__name__)
        return func(*args, **kwargs)
    return wrapper_topline
