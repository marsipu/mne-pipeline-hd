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
import pathlib

from setuptools import find_packages, setup

# UnicodeDecodeError somehow
# with open("README.md", "r") as fh:
#     long_description = fh.read()

# Get version as in mne-tools/mne-qt-browser
version = None
with open(pathlib.Path('mne_qt_browser') / '_version.py', 'r') as fid:
    for line in (line.strip() for line in fid):
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip('\'')
            break
if version is None:
    raise RuntimeError('Could not determine version')

setup(name='mne_pipeline_hd',
      version=version,
      description='A pipeline-GUI for brain-data analysis with MNE-Python',
      long_description_content_type='text/markdown',
      url='https://github.com/marsipu/mne_pipeline_hd',
      author='Martin Schulz',
      author_email='dev@earthman-music.de',
      python_requires='>=3.7',
      install_requires=['mne',
                        'pandas',
                        'autoreject',
                        'qdarkstyle',
                        'PyQtWebEngine',
                        'joblib',
                        'sklearn',
                        'pyobjc-framework-Cocoa; sys_platform == "darwin"'],
      license='BSD (3-clause)',
      packages=find_packages(exclude=['docs', 'tests', 'development']),
      package_data={},
      classifiers=["Programming Language :: Python :: 3",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Intended Audience :: Science/Research",
                   'Topic :: Scientific/Engineering'],
      include_package_data=True,
      entry_points={
          'console_scripts': [
              'mne_pipeline_hd = mne_pipeline_hd.__main__:main'
          ]
      }

      )
