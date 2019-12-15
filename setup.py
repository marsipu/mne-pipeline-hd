import sys
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='mne-pipeline-hd',
      version='0.1',
      description='A pipeline for brain-data analysis with MNE-Python',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/marsipu/mne_pipeline_hd',
      author='Martin Schulz',
      author_email='martin.schulz@stud.uni-heidelberg.de',
      python_requires='>=3.7',
      install_requirements=['mne', 'autoreject', 'imageio-ffmpeg',
                            'pyobjc-framework-Cocoa; sys_platform == "darwin"'],
      license='GPL-3.0',
      packages=find_packages(exclude=['docs', 'tests']),
      classifiers=["Programming Language :: Python :: 3",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Intended Audience :: Science/Research"
                   'Topic :: Scientific/Engineering'])
