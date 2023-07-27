# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

import pathlib

from setuptools import find_packages, setup


# Get version and requirements as in mne-tools/mne-qt-browser
def parse_requirements():
    requirements = list()
    with open('requirements.txt', 'r') as fid:
        for line in fid:
            req = line.strip()
            if req.startswith('#'):
                continue
            # strip end-of-line comments
            req = req.split('#', maxsplit=1)[0].strip()
            requirements.append(req)
    return requirements


def parse_version():
    version = None
    with open(pathlib.Path(__file__).parent /
              'mne_pipeline_hd/_version.py', 'r') as fid:
        for line in (line.strip() for line in fid):
            if line.startswith('__version__'):
                version = line.split('=')[1].strip().strip('\'')
                break
    if version is None:
        raise RuntimeError('Could not determine version')

    return version


long_description = (pathlib.Path(__file__).parent /
                    "README.md").read_text('UTF-8')

setup(name='mne-pipeline-hd',
      version=parse_version(),
      description='A pipeline-GUI for brain-data analysis with MNE-Python',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/marsipu/mne-pipeline-hd',
      author='Martin Schulz',
      author_email='dev@earthman-music.de',
      python_requires='>=3.7',
      install_requires=[parse_requirements()],
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
