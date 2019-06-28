# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data
Adapted from Lau Møller Andersen
@author: Martin Schulz
@email: martin.schulz@stud.uni-heidelberg.de
@github: marsipu/mne_pipeline_hd
"""
# %%============================================================================
# IMPORTS
# ==============================================================================
import sys
from os import makedirs
from os.path import join, isfile, exists
import re
import numpy as np
import mne

from pipeline_functions import io_functions as io
from pipeline_functions import operations_functions as op
from pipeline_functions import plot_functions as plot
from pipeline_functions import subject_organisation as suborg
from pipeline_functions import utilities as ut

# %%============================================================================
# WHICH SUBJECT? (TO SET)
# ==============================================================================
# Which File do you want to run?
# Type in the LINE of the filename in your file_list.py
# Examples:
# '5' (One File)
# '1,7,28' (Several Files)
# '1-5' (From File x to File y)
# '1-4,7,20-26' (The last two combined)
# '1-20,!4-6' (1-20 except 4-6)
# 'all' (All files in file_list.py)
# 'all,!4-6' (All files except 4-6)

which_file = 'all'  # Has to be a string/enclosed in apostrophs
quality = [1]
modality = ['256', 't']
which_mri_subject = '1'  # Has to be a string/enclosed in apostrophs
which_erm_file = 'all'  # !112 Has to be a string/enclosed in apostrophs
which_motor_erm_file = 'all'  # Has to be a string/enclosed in apostrophs

# %%============================================================================
# PARAMETERS (TO SET)
# ==============================================================================
# OS
n_jobs = -1  # number of processor-cores to use, -1 for auto
enable_cuda = False  # Using CUDA on supported graphics card e.g. for filtering
# cupy and appropriate CUDA-Drivers have to be installed
# https://mne-tools.github.io/dev/advanced_setup.html#advanced-setup

# File I/O
unspecified_names = False  # True if you don't use Regular Expressions to handle your filenames
print_info = False  # Print the raw-info of each file in the console

overwrite = True  # should files be overwritten in general
save_plots = True  # should plots be saved

# raw
predefined_bads = [6, 7, 8, 26, 27, 103]  # Default bad channels
eog_digitized = True  # Set True, if the last 4 digitized points where EOG
lowpass = 80  # Hz
highpass = 1  # Hz # at least 1 if to apply ICA
erm_t_limit = 300  # Limits Empty-Room-Measurement-Length [s]

# events
adjust_timeline_by_msec = -200  # custom delay to stimulus in ms
pinprick = True  # Events including Rating

# epochs
tmin = -0.500  # start of epoch [s]
tmax = 1.500  # end of epoch [s]
baseline = (-0.500, 0)  # has to be a tuple [s]
autoreject = True  # set True to use autoreject
overwrite_ar = False  # if to calculate new thresholds or to use previously calculated
reject = dict(grad=8000e-13)  # default reject parameter if not reject with autoreject
flat = dict(grad=1e-15)  # default flat parameter
reject_eog_epochs = False  # function to reject eog_epochs after use of find_eog_events
decim = 1  # downsampling factor
event_id = {'LBT': 1}  # dictionary to assign strings to the event_ids
# {'LBT':1, 'offset':4, 'lower_R':5, 'same_R':6, 'higher_R':7}

# evokeds
ica_evokeds = True  # Apply ICA to evokeds
detrend = False  # sometimes not working
ana_h1h2 = True

# Time-Frequency-Analysis
tfr_freqs = np.arange(30, 80, 5)  # Frequencies to analyze
overwrite_tfr = False  # Recalculate and overwrite tfr
tfr_method = 'morlet'
multitaper_bandwith = 4.0
stockwell_width = 1.0

# ICA
eog_channel = 'EEG 001'  # Set Vertical EOG-Channel
ecg_channel = 'EEG 003'  # Set ECG-Channel

# forward modeling
source_space_method = 'ico5'  # See the MNE-Documentation for further details

# source reconstruction
erm_noise_covariance = True
use_calm_cov = False  # Use of a specific time interval in a measurement for noise covariance
erm_ica = False  # Causes sometimes errors
method = 'dSPM'
mne_evoked_time = [0, 0.05, 0.1, 0.15, 0.2]  # time points to be displayed in several plots [s]
stc_interactive = False  # interactive stc-plots
stc_animation = (0, 0.5)  # time span for stc-animation [s]
eeg_fwd = False  # set True if working with EEG-Data
parcellation = 'HCPMMP1'
parcellation_orig = 'aparc_sub'
ev_ids_label_analysis = ['LBT']
n_std = 4  # Determing the amount of standard-deviations, the prominence must have
corr_threshold = 0.95

target_labels = {'lh': ['Somatosensory and Motor Cortex-lh',
                        'Posterior Opercular Cortex-lh',
                        'Insular and Frontal Opercular Cortex-lh'],
                 'rh': ['Somatosensory and Motor Cortex-rh',
                        'Posterior Opercular Cortex-rh',
                        'Insular and Frontal Opercular Cortex-rh']}

# target_labels= {'lh':['L_3a_ROI-lh', 'L_3b_ROI-lh',
#                'L_43_ROI-lh', 'L_OP4_ROI-lh', 'L_OP2-3_ROI-lh', 'L_MI_ROI-lh',
#                'L_FOP1_ROI-lh', 'L_FOP2_ROI-lh', 'L_FOP1_RO3-lh', 'L_FOP4_ROI-lh',
#                'L_FOP5_ROI-lh',
#                'L_PoI1_ROI-lh', 'L_PoI2_ROI-lh', 'L_Ig_ROI-lh',
#                'L_AAIC_ROI-lh', 'L_AVI_ROI-lh', 'L_IFSa_ROI-lh'],
#                'rh':['R_3a_ROI-rh', 'R_3b_ROI-rh',
#                'R_43_ROI-rh', 'R_OP4_ROI-rh', 'R_OP2-3_ROI-rh', 'R_MI_ROI-rh',
#                'L_FOP1_ROI-rh', 'L_FOP2_ROI-rh', 'L_FOP1_RO3-rh', 'L_FOP4_ROI-rh',
#                'L_FOP5_ROI-rh',
#                'R_PoI1_ROI-rh', 'R_PoI2_ROI-rh', 'R_Ig_ROI-rh',
#                'R_AAIC_ROI-rh', 'R_AVI_ROI-rh', 'R_IFSa_ROI-rh']}

# target_labels =  {'lh':['S_central-lh', 'S_circular_insula_sup-lh'],
#                  'rh':['S_central-rh', 'S_circular_insula_sup-rh']}

# label_origin = ['S_central-lh', 'S_central-rh', 'S_circular_insula_sup-lh',
#                'S_circular_insula_sup-rh', 'G&S_subcentral-lh',
#                'G&S_subcentral-rh', 'G_Ins_lg&S_cent_ins-lh',
#                'G_Ins_lg&S_cent_ins-rh', 'S_circular_insula_inf-lh',
#                'S_circular_insula_inf-rh', 'S_temporal_transverse-lh',
#                'S_temporal_transverse-rh', 'S_temporal_sup-lh',
#                'S_temporal_sup-rh', 'Lat_Fis-post-lh',
#                'Lat_Fis-post-rh', 'S_front_inf-lh', 'S_front_inf-rh',
#                'S_front_middle-lh', 'S_front_middle-rh',
#                'G_front_middle-lh', 'G_front_middle-rh',
#                'S_precentral-inf-part-lh', 'S_precentral-inf-part-rh',
#                'G_postcentral-lh', 'G_postcentral-rh',
#                'G_precentral-lh', 'G_precentral-rh',
#                'S_postcentral-lh', 'S_postcentral-rh',
#                'G_pariet_inf-Supramar-lh', 'G_pariet_inf-Supramar-rh',
#                'G_front_inf-Opercular-lh', 'G_front_inf-Opercular-rh',
#                'Lat_Fis-ant-Vertical-lh', 'Lat_Fis-ant-Vertical-rh',
#                'Lat_Fis-ant-Horizont-lh', 'Lat_Fis-ant-Horizont-lh',
#                'G_temp_sup-G_T_transv-lh', 'G_temp_sup-G_T_transv-rh',
#                'G_insular_short-lh', 'G_insular_short-rh',
#                'G_temp_sup-Lateral-lh', 'G_temp_sup-Lateral-rh',
#                'G_front_inf-Triangul-lh', 'G_front_inf-Triangul-rh',
#                'G_temp_sup-Plan_tempo-lh', 'G_temp_sup-Plan_tempo-rh',
#                'S_interim_prim-Jensen-lh', 'S_interim_prim-Jensen-rh']

label_origin = ['bankssts_1-lh',
                'bankssts_1-rh',
                'bankssts_2-lh',
                'bankssts_2-rh',
                'bankssts_3-lh',
                'bankssts_3-rh',
                'caudalmiddlefrontal_1-lh',
                'caudalmiddlefrontal_1-rh',
                'caudalmiddlefrontal_2-lh',
                'caudalmiddlefrontal_2-rh',
                'caudalmiddlefrontal_3-lh',
                'caudalmiddlefrontal_3-rh',
                'caudalmiddlefrontal_4-lh',
                'caudalmiddlefrontal_4-rh',
                'caudalmiddlefrontal_5-lh',
                'caudalmiddlefrontal_5-rh',
                'caudalmiddlefrontal_6-lh',
                'insula_1-lh',
                'insula_1-rh',
                'insula_2-lh',
                'insula_2-rh',
                'insula_3-lh',
                'insula_3-rh',
                'insula_4-lh',
                'insula_4-rh',
                'insula_5-lh',
                'insula_5-rh',
                'insula_6-lh',
                'insula_6-rh',
                'insula_7-lh',
                'insula_7-rh',
                'lateralorbitofrontal_1-lh',
                'lateralorbitofrontal_1-rh',
                'lateralorbitofrontal_2-lh',
                'lateralorbitofrontal_2-rh',
                'lateralorbitofrontal_3-lh',
                'lateralorbitofrontal_3-rh',
                'lateralorbitofrontal_4-lh',
                'lateralorbitofrontal_4-rh',
                'lateralorbitofrontal_5-lh',
                'lateralorbitofrontal_5-rh',
                'lateralorbitofrontal_6-lh',
                'lateralorbitofrontal_6-rh',
                'lateralorbitofrontal_7-lh',
                'lateralorbitofrontal_7-rh',
                'middletemporal_1-lh',
                'middletemporal_1-rh',
                'middletemporal_2-lh',
                'middletemporal_2-rh',
                'middletemporal_3-lh',
                'middletemporal_3-rh',
                'middletemporal_4-lh',
                'middletemporal_4-rh',
                'middletemporal_5-lh',
                'middletemporal_5-rh',
                'middletemporal_6-lh',
                'middletemporal_6-rh',
                'middletemporal_7-lh',
                'middletemporal_7-rh',
                'middletemporal_8-rh',
                'middletemporal_9-rh',
                'parsopercularis_1-lh',
                'parsopercularis_1-rh',
                'parsopercularis_2-lh',
                'parsopercularis_2-rh',
                'parsopercularis_3-lh',
                'parsopercularis_3-rh',
                'parsopercularis_4-lh',
                'parsopercularis_4-rh',
                'parsorbitalis_1-lh',
                'parsorbitalis_1-rh',
                'parsorbitalis_2-lh',
                'parsorbitalis_2-rh',
                'parstriangularis_1-lh',
                'parstriangularis_1-rh',
                'parstriangularis_2-lh',
                'parstriangularis_2-rh',
                'parstriangularis_3-lh',
                'parstriangularis_3-rh',
                'parstriangularis_4-rh',
                'postcentral_1-lh',
                'postcentral_1-rh',
                'postcentral_10-lh',
                'postcentral_10-rh',
                'postcentral_11-lh',
                'postcentral_11-rh',
                'postcentral_12-lh',
                'postcentral_12-rh',
                'postcentral_13-lh',
                'postcentral_14-lh',
                'postcentral_2-lh',
                'postcentral_2-rh',
                'postcentral_3-lh',
                'postcentral_3-rh',
                'postcentral_4-lh',
                'postcentral_4-rh',
                'postcentral_5-lh',
                'postcentral_5-rh',
                'postcentral_6-lh',
                'postcentral_6-rh',
                'postcentral_7-lh',
                'postcentral_7-rh',
                'postcentral_8-lh',
                'postcentral_8-rh',
                'postcentral_9-lh',
                'postcentral_9-rh',
                'precentral_1-lh',
                'precentral_1-rh',
                'precentral_10-lh',
                'precentral_10-rh',
                'precentral_11-lh',
                'precentral_11-rh',
                'precentral_12-lh',
                'precentral_12-rh',
                'precentral_13-lh',
                'precentral_13-rh',
                'precentral_14-lh',
                'precentral_14-rh',
                'precentral_15-lh',
                'precentral_15-rh',
                'precentral_16-lh',
                'precentral_16-rh',
                'precentral_2-lh',
                'precentral_2-rh',
                'precentral_3-lh',
                'precentral_3-rh',
                'precentral_4-lh',
                'precentral_4-rh',
                'precentral_5-lh',
                'precentral_5-rh',
                'precentral_6-lh',
                'precentral_6-rh',
                'precentral_7-lh',
                'precentral_7-rh',
                'precentral_8-lh',
                'precentral_8-rh',
                'precentral_9-lh',
                'precentral_9-rh',
                'rostralmiddlefrontal_1-lh',
                'rostralmiddlefrontal_1-rh',
                'rostralmiddlefrontal_10-lh',
                'rostralmiddlefrontal_10-rh',
                'rostralmiddlefrontal_11-lh',
                'rostralmiddlefrontal_11-rh',
                'rostralmiddlefrontal_12-lh',
                'rostralmiddlefrontal_12-rh',
                'rostralmiddlefrontal_13-rh',
                'rostralmiddlefrontal_2-lh',
                'rostralmiddlefrontal_2-rh',
                'rostralmiddlefrontal_3-lh',
                'rostralmiddlefrontal_3-rh',
                'rostralmiddlefrontal_4-lh',
                'rostralmiddlefrontal_4-rh',
                'rostralmiddlefrontal_5-lh',
                'rostralmiddlefrontal_5-rh',
                'rostralmiddlefrontal_6-lh',
                'rostralmiddlefrontal_6-rh',
                'rostralmiddlefrontal_7-lh',
                'rostralmiddlefrontal_7-rh',
                'rostralmiddlefrontal_8-lh',
                'rostralmiddlefrontal_8-rh',
                'rostralmiddlefrontal_9-lh',
                'rostralmiddlefrontal_9-rh',
                'superiorfrontal_1-lh',
                'superiorfrontal_1-rh',
                'superiorfrontal_10-lh',
                'superiorfrontal_10-rh',
                'superiorfrontal_11-lh',
                'superiorfrontal_11-rh',
                'superiorfrontal_12-lh',
                'superiorfrontal_12-rh',
                'superiorfrontal_13-lh',
                'superiorfrontal_13-rh',
                'superiorfrontal_14-lh',
                'superiorfrontal_14-rh',
                'superiorfrontal_15-lh',
                'superiorfrontal_15-rh',
                'superiorfrontal_16-lh',
                'superiorfrontal_16-rh',
                'superiorfrontal_17-lh',
                'superiorfrontal_17-rh',
                'superiorfrontal_18-lh',
                'superiorfrontal_2-lh',
                'superiorfrontal_2-rh',
                'superiorfrontal_3-lh',
                'superiorfrontal_3-rh',
                'superiorfrontal_4-lh',
                'superiorfrontal_4-rh',
                'superiorfrontal_5-lh',
                'superiorfrontal_5-rh',
                'superiorfrontal_6-lh',
                'superiorfrontal_6-rh',
                'superiorfrontal_7-lh',
                'superiorfrontal_7-rh',
                'superiorfrontal_8-lh',
                'superiorfrontal_8-rh',
                'superiorfrontal_9-lh',
                'superiorfrontal_9-rh',
                'superiortemporal_1-lh',
                'superiortemporal_1-rh',
                'superiortemporal_10-lh',
                'superiortemporal_10-rh',
                'superiortemporal_11-lh',
                'superiortemporal_11-rh',
                'superiortemporal_2-lh',
                'superiortemporal_2-rh',
                'superiortemporal_3-lh',
                'superiortemporal_3-rh',
                'superiortemporal_4-lh',
                'superiortemporal_4-rh',
                'superiortemporal_5-lh',
                'superiortemporal_5-rh',
                'superiortemporal_6-lh',
                'superiortemporal_6-rh',
                'superiortemporal_7-lh',
                'superiortemporal_7-rh',
                'superiortemporal_8-lh',
                'superiortemporal_8-rh',
                'superiortemporal_9-lh',
                'superiortemporal_9-rh',
                'supramarginal_1-lh',
                'supramarginal_1-rh',
                'supramarginal_10-lh',
                'supramarginal_2-lh',
                'supramarginal_2-rh',
                'supramarginal_3-lh',
                'supramarginal_3-rh',
                'supramarginal_4-lh',
                'supramarginal_4-rh',
                'supramarginal_5-lh',
                'supramarginal_5-rh',
                'supramarginal_6-lh',
                'supramarginal_6-rh',
                'supramarginal_7-lh',
                'supramarginal_7-rh',
                'supramarginal_8-lh',
                'supramarginal_8-rh',
                'supramarginal_9-lh',
                'supramarginal_9-rh',
                'transversetemporal_1-lh',
                'transversetemporal_1-rh',
                'transversetemporal_2-lh']

# connectivity
con_methods = ['pli', 'wpli2_debiased', 'plv']  # methods for connectivity plots
con_fmin = 30  # fmin for connectivity plot
con_fmax = 80  # fmax for connectivity plot

# Dipole-fit
ecds = {}  # Assign manually time points [s] to each file to make a dipole fit

# grand averages
morph_to = 'fsaverage'  # name of the freesurfer subject to be morphed to
fuse_ab = True  # pinprick-specific
align_peaks = True

# statistics (still original from Andersen, may not work)
independent_variable_1 = 'standard_3'
independent_variable_2 = 'non_stimulation'
time_window = (0.050, 0.060)
n_permutations = 10000  # specify as integer

# statistics plotting
p_threshold = 1e-15  # 1e-15 is the smallest it can get for the way it is coded

# freesurfer and MNE-C commands
n_jobs_freesurfer = 4  # change according to amount of processors you have available
# %%============================================================================
# GUI CALL
# ==============================================================================
exec_ops = ut.choose_function()
# %%============================================================================
# PATHS (TO SET)
# ==============================================================================
# specify the path to a general analysis folder according to your OS
if sys.platform == 'win32':
    home_path = 'Z:/Promotion'  # Windows-Path
if sys.platform == 'linux':
    home_path = '/mnt/z/Promotion'  # Linux-Path
if sys.platform == 'darwin':
    home_path = 'Users/'  # Mac-Path
else:
    home_path = 'Z:/Promotion'

project_name = 'Pin-Prick-Projekt/PP_Messungen'  # specify the name for your project as a folder
subjects_dir = join(home_path, 'Freesurfer/Output')  # name of your Freesurfer
orig_data_path = join(home_path, 'Pin-Prick-Projekt/Messungen_Dateien')

# %%============================================================================
# DEPENDING PATHS (NOT TO SET)
# ==============================================================================
data_path = join(home_path, project_name, 'Daten')
sub_script_path = join(data_path, '_Subject_scripts')
mne.utils.set_config("SUBJECTS_DIR", subjects_dir, set_env=True)
save_dir_averages = join(data_path, 'grand_averages')

if exec_ops['erm_analysis'] or exec_ops['motor_erm_analysis']:
    figures_path = join(home_path, project_name, 'Figures/ERM_Figures')
else:
    figures_path = join(home_path, project_name, 'Figures/')

# add file_names, mri_subjects, sub_dict, bad_channels_dict
file_list_path = join(sub_script_path, 'file_list.py')
erm_list_path = join(sub_script_path, 'erm_list.py')  # ERM means Empty-Room
motor_erm_list_path = join(sub_script_path, 'motor_erm_list.py')  # Special for Pinprick
mri_sub_list_path = join(sub_script_path, 'mri_sub_list.py')
sub_dict_path = join(sub_script_path, 'sub_dict.py')
erm_dict_path = join(sub_script_path, 'erm_dict.py')
bad_channels_dict_path = join(sub_script_path, 'bad_channels_dict.py')

path_lists = [subjects_dir, orig_data_path, data_path, sub_script_path,
              figures_path]
file_lists = [file_list_path, erm_list_path, motor_erm_list_path, mri_sub_list_path,
              sub_dict_path, erm_dict_path, bad_channels_dict_path]

if not exists(home_path):
    print('Create home_path manually and set the variable accordingly')

for p in path_lists:
    if not exists(p):
        makedirs(p)
        print(f'{p} created')

for f in file_lists:
    if not isfile(f):
        with open(f, 'w') as file:
            file.write('')
        print(f'{f} created')

op.populate_directories(data_path, figures_path, event_id)
# %%============================================================================
# SUBJECT ORGANISATION (NOT TO SET)
# ==============================================================================
if exec_ops['add_files']:  # set 1 to run
    suborg.add_files(file_list_path, erm_list_path, motor_erm_list_path,
                     data_path, figures_path, subjects_dir, orig_data_path,
                     unspecified_names, gui=False)

if exec_ops['add_mri_subjects']:  # set 1 to run
    suborg.add_mri_subjects(subjects_dir, mri_sub_list_path, data_path, gui=False)

if exec_ops['add_sub_dict']:  # set 1 to run
    suborg.add_sub_dict(sub_dict_path, file_list_path, mri_sub_list_path, data_path)

if exec_ops['add_erm_dict']:  # set 1 to run
    suborg.add_erm_dict(erm_dict_path, file_list_path, erm_list_path, data_path)

if exec_ops['add_bad_channels']:
    suborg.add_bad_channels_dict(bad_channels_dict_path, file_list_path,
                                 erm_list_path, motor_erm_list_path,
                                 data_path, predefined_bads,
                                 sub_script_path)

# Subject-Functions
all_files = suborg.read_files(file_list_path)
all_mri_subjects = suborg.read_mri_subjects(mri_sub_list_path)
erm_files = suborg.read_files(erm_list_path)
motor_erm_files = suborg.read_files(motor_erm_list_path)
sub_dict = suborg.read_sub_dict(sub_dict_path)
erm_dict = suborg.read_sub_dict(erm_dict_path)  # add None if not available
bad_channels_dict = suborg.read_bad_channels_dict(bad_channels_dict_path)
# %%========================================================================
# MRI-Subjects (NOT TO SET)
# ============================================================================
if exec_ops['apply_watershed'] or exec_ops['make_dense_scalp_surfaces'] \
        or exec_ops['prepare_bem'] or exec_ops['setup_src'] \
        or exec_ops['morph_subject'] or exec_ops['plot_source_space'] \
        or exec_ops['plot_bem'] or exec_ops['plot_labels'] \
        or exec_ops['morph_labels_from_fsaverage'] or exec_ops['compute_src_distances']:

    mri_subjects = suborg.file_selection(which_mri_subject, all_mri_subjects)

    print(f'Selected {len(mri_subjects)} MRI-Subjects:')
    for i in mri_subjects:
        print(i)

    for mri_subject in mri_subjects:
        print('=' * 60 + '\n', mri_subject)
        prog = round((mri_subjects.index(mri_subject)) / len(mri_subjects) * 100, 2)
        print(f'Progress: {prog} %')

        # ==========================================================================
        # BASH SCRIPTS
        # ==========================================================================
        if exec_ops['apply_watershed']:
            op.apply_watershed(mri_subject, subjects_dir, overwrite)

        if exec_ops['make_dense_scalp_surfaces']:
            op.make_dense_scalp_surfaces(mri_subject, subjects_dir, overwrite)

        # ==========================================================================
        # Forward Modeling
        # ==========================================================================
        if exec_ops['setup_src']:
            op.setup_src(mri_subject, subjects_dir, source_space_method,
                         overwrite, n_jobs)
        if exec_ops['compute_src_distances']:
            op.compute_src_distances(mri_subject, subjects_dir,
                                     source_space_method, n_jobs)
        if exec_ops['prepare_bem']:
            op.prepare_bem(mri_subject, subjects_dir)

        if exec_ops['morph_subject']:
            op.morph_subject(mri_subject, subjects_dir, morph_to,
                             source_space_method, overwrite)

        if exec_ops['morph_labels_from_fsaverage']:
            op.morph_labels_from_fsaverage(mri_subject, subjects_dir, overwrite)
        # ==========================================================================
        # PLOT SOURCE SPACES
        # ==========================================================================

        if exec_ops['plot_source_space']:
            plot.plot_source_space(mri_subject, subjects_dir, source_space_method, save_plots, figures_path)

        if exec_ops['plot_bem']:
            plot.plot_bem(mri_subject, subjects_dir, source_space_method, figures_path,
                          save_plots)

        if exec_ops['plot_labels']:
            plot.plot_labels(mri_subject, save_plots, figures_path,
                             parcellation)

        # close plots
        if exec_ops['close_plots']:
            plot.close_all()
# %%========================================================================
# Files (NOT TO SET)
# ===========================================================================
if exec_ops['erm_analysis']:
    files = suborg.file_selection(which_erm_file, erm_files)
elif exec_ops['motor_erm_analysis']:
    files = suborg.file_selection(which_motor_erm_file, motor_erm_files)
else:
    files = suborg.file_selection(which_file, all_files)

quality_dict = ut.read_dict_file('quality', sub_script_path)

basic_pattern = r'(pp[0-9][0-9]*[a-z]*)_([0-9]{0,3}t?)_([a,b]$)'
if not exec_ops['erm_analysis'] and not exec_ops['motor_erm_analysis']:
    delete_files = set()
    for file in files:
        file_quality = int(quality_dict[file])
        if file_quality not in quality:
            delete_files.add(file)

        match = re.match(basic_pattern, file)
        file_modality = match.group(2)
        if file_modality not in modality:
            delete_files.add(file)

    for df in delete_files:
        files.remove(df)

if len(all_files) == 0:
    print('No files in file_list!')
    print('Add some folders(the ones with the date) to your orig_data_path-folder and check "add_files"')
else:
    print(f'Selected {len(files)} Subjects:')
    for f in files:
        print(f)

# Get dicts grouping the files together depending on their names to allow grand_averaging:
ab_dict, comp_dict, grand_avg_dict, sub_files_dict = ut.get_subject_groups(files, fuse_ab, unspecified_names)
morphed_data_all = dict(LBT=[], offset=[], lower_R=[], same_R=[], higher_R=[])

for name in files:

    # Print Subject Console Header
    print(60 * '=' + '\n' + name)
    prog = round((files.index(name)) / len(files) * 100, 2)
    print(f'Progress: {prog} %')

    if exec_ops['erm_analysis'] or exec_ops['motor_erm_analysis']:
        save_dir = join(home_path, project_name, 'Daten/empty_room_data')
        data_path = join(home_path, project_name, 'Daten/empty_room_data')
    else:
        save_dir = join(data_path, name)

    if print_info:
        info = io.read_info(name, save_dir)
        print(info)

    # Use Regular Expressions to make ermsub and subtomri assignement easier
    pattern = r'pp[0-9]+[a-z]?'
    if unspecified_names:
        pattern = r'.*'
    match = re.match(pattern, name)
    prefix = match.group()

    try:
        ermsub = erm_dict[prefix]
    except KeyError as k:
        print(f'No erm_measurement for {k}')
        ermsub = []
        suborg.add_erm_dict(erm_dict_path, file_list_path, erm_list_path, data_path)

    try:
        subtomri = sub_dict[prefix]
    except KeyError as k:
        print(f'No mri_subject assigned to {k}')
        subtomri = []
        suborg.add_sub_dict(sub_dict_path, file_list_path, mri_sub_list_path, data_path)

    try:
        bad_channels = bad_channels_dict[name]
    except KeyError as k:
        print(f'No bad channels for {k}')
        bad_channels = []
        suborg.add_bad_channels_dict(bad_channels_dict_path, file_list_path,
                                     erm_list_path, motor_erm_list_path,
                                     data_path, predefined_bads,
                                     sub_script_path)

    # ==========================================================================
    # FILTER RAW
    # ==========================================================================

    if exec_ops['filter_raw']:
        op.filter_raw(name, save_dir, lowpass, highpass, ermsub,
                      data_path, n_jobs, enable_cuda, bad_channels, erm_t_limit)

    # ==========================================================================
    # FIND EVENTS
    # ==========================================================================

    if exec_ops['find_events']:
        if pinprick:
            op.find_events_pp(name, save_dir, adjust_timeline_by_msec, lowpass,
                              highpass, overwrite, sub_script_path,
                              save_plots, figures_path, exec_ops)
        else:
            op.find_events(name, save_dir, adjust_timeline_by_msec, lowpass,
                           highpass, overwrite, exec_ops)

    if exec_ops['find_eog_events']:
        op.find_eog_events(name, save_dir, eog_channel)

    # ==========================================================================
    # EPOCHS
    # ==========================================================================

    if exec_ops['epoch_raw']:
        op.epoch_raw(name, save_dir, lowpass, highpass, event_id, tmin, tmax,
                     baseline, reject, flat, autoreject, overwrite_ar,
                     sub_script_path, bad_channels, decim,
                     reject_eog_epochs, overwrite, exec_ops)

    # ==========================================================================
    # SIGNAL SPACE PROJECTION
    # ==========================================================================
    if exec_ops['run_ssp_er']:
        op.run_ssp_er(name, save_dir, lowpass, highpass, data_path, ermsub, bad_channels,
                      overwrite)

    if exec_ops['apply_ssp_er']:
        op.apply_ssp_er(name, save_dir, lowpass, highpass, overwrite)

    if exec_ops['run_ssp_clm']:
        op.run_ssp_clm(name, save_dir, lowpass, highpass, bad_channels, overwrite)

    if exec_ops['apply_ssp_clm']:
        op.apply_ssp_clm(name, save_dir, lowpass, highpass, overwrite)

    if exec_ops['run_ssp_eog']:
        op.run_ssp_eog(name, save_dir, n_jobs, eog_channel,
                       bad_channels, overwrite)

    if exec_ops['apply_ssp_eog']:
        op.apply_ssp_eog(name, save_dir, lowpass, highpass, overwrite)

    if exec_ops['run_ssp_ecg']:
        op.run_ssp_ecg(name, save_dir, n_jobs, ecg_channel,
                       bad_channels, overwrite)

    if exec_ops['apply_ssp_ecg']:
        op.apply_ssp_ecg(name, save_dir, lowpass, highpass, overwrite)

    if exec_ops['plot_ssp']:
        plot.plot_ssp(name, save_dir, lowpass, highpass, save_plots,
                      figures_path, ermsub)

    if exec_ops['plot_ssp_eog']:
        plot.plot_ssp_eog(name, save_dir, lowpass, highpass, save_plots,
                          figures_path)

    if exec_ops['run_ica']:
        op.run_ica(name, save_dir, lowpass, highpass, eog_channel, ecg_channel,
                   reject, flat, bad_channels, overwrite, autoreject,
                   save_plots, figures_path, sub_script_path,
                   exec_ops['erm_analysis'])

    # ==========================================================================
    # LOAD NON-ICA'ED EPOCHS AND APPLY ICA
    # ==========================================================================

    if exec_ops['apply_ica']:
        op.apply_ica(name, save_dir, lowpass, highpass, overwrite)

    # ==========================================================================
    # EVOKEDS
    # ==========================================================================

    if exec_ops['get_evokeds']:
        op.get_evokeds(name, save_dir, lowpass, highpass, exec_ops, ermsub,
                       detrend, ica_evokeds, overwrite, ana_h1h2)

    if exec_ops['align_peaks']:
        op.align_peaks(name, save_dir, lowpass, highpass, sub_script_path,
                       event_id, tmin, tmax, baseline, reject, flat, autoreject,
                       overwrite_ar, bad_channels, overwrite, decim, exec_ops,
                       eog_channel, save_plots, figures_path, ecg_channel,
                       reject_eog_epochs, ica_evokeds, ermsub, detrend,
                       ana_h1h2)

    # ==========================================================================
    # TIME-FREQUENCY-ANALASYS
    # ==========================================================================

    if exec_ops['tfr']:
        op.tfr(name, save_dir, lowpass, highpass, ica_evokeds, tfr_freqs, overwrite_tfr,
               tfr_method, multitaper_bandwith, stockwell_width, n_jobs)

    # ==========================================================================
    # NOISE COVARIANCE MATRIX
    # ==========================================================================

    if exec_ops['estimate_noise_covariance']:
        op.estimate_noise_covariance(name, save_dir, lowpass, highpass, overwrite,
                                     ermsub, data_path, baseline, bad_channels,
                                     n_jobs, erm_noise_covariance, use_calm_cov,
                                     ica_evokeds, erm_ica)

    if exec_ops['plot_noise_covariance']:
        plot.plot_noise_covariance(name, save_dir, lowpass, highpass,
                                   save_plots, figures_path, ermsub,
                                   use_calm_cov)

    # ==========================================================================
    # CO-REGISTRATION
    # ==========================================================================

    # use mne.gui.coregistration()

    if exec_ops['mri_coreg']:
        op.mri_coreg(name, save_dir, subtomri, subjects_dir, eog_digitized)

    if exec_ops['plot_transformation']:
        plot.plot_transformation(name, save_dir, subtomri, subjects_dir,
                                 save_plots, figures_path)

    # ==========================================================================
    # CREATE FORWARD MODEL
    # ==========================================================================

    if exec_ops['create_forward_solution']:
        op.create_forward_solution(name, save_dir, subtomri, subjects_dir,
                                   source_space_method, overwrite,
                                   n_jobs, eeg_fwd)

    # ==========================================================================
    # CREATE INVERSE OPERATOR
    # ==========================================================================

    if exec_ops['create_inverse_operator']:
        op.create_inverse_operator(name, save_dir, lowpass, highpass,
                                   overwrite, ermsub, use_calm_cov,
                                   erm_noise_covariance)

    # ==========================================================================
    # SOURCE ESTIMATE MNE
    # ==========================================================================

    if exec_ops['source_estimate']:
        op.source_estimate(name, save_dir, lowpass, highpass, method,
                           overwrite)

    if exec_ops['vector_source_estimate']:
        op.vector_source_estimate(name, save_dir, lowpass, highpass,
                                  method, overwrite)

    if exec_ops['ecd_fit']:
        op.ecd_fit(name, save_dir, lowpass, highpass, ermsub, subjects_dir,
                   subtomri, use_calm_cov, ecds,
                   save_plots, figures_path)

    if exec_ops['apply_morph']:
        stcs = op.apply_morph(name, save_dir, lowpass, highpass,
                              subjects_dir, subtomri, method,
                              overwrite, morph_to,
                              source_space_method, event_id)

    if exec_ops['apply_morph_normal']:
        stcs = op.apply_morph_normal(name, save_dir, lowpass, highpass,
                                     subjects_dir, subtomri, method,
                                     overwrite, morph_to,
                                     source_space_method, event_id)

    if not fuse_ab:
        if exec_ops['create_func_label']:
            op.create_func_label(name, save_dir, lowpass, highpass,
                                 method, event_id, subtomri, subjects_dir,
                                 source_space_method, label_origin,
                                 parcellation_orig, ev_ids_label_analysis,
                                 save_plots, figures_path, sub_script_path,
                                 n_std, fuse_ab)

    if not fuse_ab:
        if exec_ops['func_label_processing']:
            op.func_label_processing(name, save_dir, lowpass, highpass,
                                     save_plots, figures_path, subtomri, subjects_dir,
                                     sub_script_path, ev_ids_label_analysis,
                                     corr_threshold, fuse_ab)

    if exec_ops['func_label_ctf_ps']:
        op.func_label_ctf_ps(name, save_dir, lowpass, highpass, subtomri,
                             subjects_dir, parcellation_orig)
    # ==========================================================================
    # PRINT INFO
    # ==========================================================================

    if exec_ops['plot_sensors']:
        plot.plot_sensors(name, save_dir)

    # ==========================================================================
    # PLOT RAW DATA
    # ==========================================================================

    if exec_ops['plot_raw']:
        plot.plot_raw(name, save_dir, bad_channels, bad_channels_dict)

    if exec_ops['plot_filtered']:
        plot.plot_filtered(name, save_dir, lowpass, highpass, bad_channels)

    if exec_ops['plot_events']:
        plot.plot_events(name, save_dir, save_plots, figures_path, event_id)

    if exec_ops['plot_events_diff']:
        plot.plot_events_diff(name, save_dir, save_plots, figures_path)

    if exec_ops['plot_eog_events']:
        plot.plot_eog_events(name, save_dir)

    # ==========================================================================
    # PLOT POWER SPECTRA
    # ==========================================================================

    if exec_ops['plot_power_spectra']:
        plot.plot_power_spectra(name, save_dir, lowpass, highpass,
                                save_plots, figures_path, bad_channels)

    if exec_ops['plot_power_spectra_epochs']:
        plot.plot_power_spectra_epochs(name, save_dir, lowpass, highpass,
                                       save_plots, figures_path)

    if exec_ops['plot_power_spectra_topo']:
        plot.plot_power_spectra_topo(name, save_dir, lowpass, highpass,
                                     save_plots, figures_path)

    # ==========================================================================
    # PLOT TIME-FREQUENCY-ANALASYS
    # ==========================================================================

    if exec_ops['plot_tfr']:
        plot.plot_tfr(name, save_dir, lowpass, highpass, tmin, tmax, baseline,
                      tfr_method, save_plots, figures_path)

    if exec_ops['tfr_event_dynamics']:
        plot.tfr_event_dynamics(name, save_dir, tmin, tmax, save_plots,
                                figures_path, bad_channels, n_jobs)

    # ==========================================================================
    # PLOT CLEANED EPOCHS
    # ==========================================================================
    if exec_ops['plot_epochs']:
        plot.plot_epochs(name, save_dir, lowpass, highpass, save_plots,
                         figures_path)

    if exec_ops['plot_epochs_image']:
        plot.plot_epochs_image(name, save_dir, lowpass, highpass, save_plots,
                               figures_path)

    if exec_ops['plot_epochs_topo']:
        plot.plot_epochs_topo(name, save_dir, lowpass, highpass, save_plots,
                              figures_path)

    if exec_ops['plot_epochs_drop_log']:
        plot.plot_epochs_drop_log(name, save_dir, lowpass, highpass, save_plots,
                                  figures_path)
    # ==========================================================================
    # PLOT EVOKEDS
    # ==========================================================================

    if exec_ops['plot_evoked_topo']:
        plot.plot_evoked_topo(name, save_dir, lowpass, highpass, save_plots,
                              figures_path)

    if exec_ops['plot_evoked_topomap']:
        plot.plot_evoked_topomap(name, save_dir, lowpass, highpass, save_plots,
                                 figures_path)

    if exec_ops['plot_evoked_butterfly']:
        plot.plot_evoked_butterfly(name, save_dir, lowpass, highpass,
                                   save_plots, figures_path)

    if exec_ops['plot_evoked_field']:
        plot.plot_evoked_field(name, save_dir, lowpass, highpass, subtomri,
                               subjects_dir, save_plots, figures_path,
                               mne_evoked_time, n_jobs)

    if exec_ops['plot_evoked_joint']:
        plot.plot_evoked_joint(name, save_dir, lowpass, highpass, save_plots,
                               figures_path, ecds, quality_dict)

    if exec_ops['plot_evoked_white']:
        plot.plot_evoked_white(name, save_dir, lowpass, highpass,
                               save_plots, figures_path, ermsub, use_calm_cov)

    if exec_ops['plot_evoked_image']:
        plot.plot_evoked_image(name, save_dir, lowpass, highpass,
                               save_plots, figures_path)

    if exec_ops['plot_evoked_compare']:
        plot.plot_evoked_compare(data_path, lowpass, highpass, comp_dict)

    if exec_ops['plot_evoked_h1h2']:
        plot.plot_evoked_h1h2(name, save_dir, lowpass, highpass, event_id,
                              save_plots, figures_path)
    # ==========================================================================
    # PLOT SOURCE ESTIMATES MNE
    # ==========================================================================

    if exec_ops['plot_stc']:
        plot.plot_stc(name, save_dir, lowpass, highpass,
                      subtomri, subjects_dir,
                      method, mne_evoked_time, event_id,
                      stc_interactive, save_plots, figures_path)

    if exec_ops['plot_normal_stc']:
        plot.plot_normal_stc(name, save_dir, lowpass, highpass,
                             subtomri, subjects_dir,
                             method, mne_evoked_time, event_id,
                             stc_interactive, save_plots, figures_path)

    if exec_ops['plot_vector_source_estimates']:
        plot.plot_vector_source_estimates(name, save_dir, lowpass, highpass,
                                          subtomri, subjects_dir,
                                          method, mne_evoked_time,
                                          save_plots, figures_path)

    if exec_ops['plot_animated_stc']:
        plot.plot_animated_stc(name, save_dir, lowpass, highpass, subtomri,
                               subjects_dir, method, stc_animation, event_id,
                               figures_path, ev_ids_label_analysis)

    if exec_ops['plot_snr']:
        plot.plot_snr(name, save_dir, lowpass, highpass, save_plots, figures_path)

    if exec_ops['label_time_course']:
        plot.label_time_course(name, save_dir, lowpass, highpass,
                               subtomri, subjects_dir, method, source_space_method,
                               target_labels, save_plots, figures_path,
                               parcellation, event_id, ev_ids_label_analysis)

    # ==========================================================================
    # TIME-FREQUENCY IN SOURCE SPACE
    # ==========================================================================

    if exec_ops['label_power_phlck']:
        op.label_power_phlck(name, save_dir, lowpass, highpass, baseline, tfr_freqs,
                             subtomri, target_labels, parcellation,
                             ev_ids_label_analysis, n_jobs,
                             save_dir, figures_path)

    if exec_ops['plot_label_power_phlck']:
        plot.plot_label_power_phlck(name, save_dir, lowpass, highpass, subtomri, parcellation,
                                    baseline, tfr_freqs, save_plots, figures_path, n_jobs,
                                    target_labels, ev_ids_label_analysis)

    if exec_ops['source_space_connectivity']:
        op.source_space_connectivity(name, save_dir, lowpass, highpass,
                                     subtomri, subjects_dir, parcellation,
                                     target_labels, con_methods,
                                     con_fmin, con_fmax,
                                     n_jobs, overwrite, ica_evokeds,
                                     ev_ids_label_analysis)

    if exec_ops['plot_source_space_connectivity']:
        plot.plot_source_space_connectivity(name, save_dir, lowpass, highpass,
                                            subtomri, subjects_dir, parcellation,
                                            target_labels, con_methods, con_fmin,
                                            con_fmax, save_plots,
                                            figures_path, ev_ids_label_analysis)

    # ==========================================================================
    # General Statistics
    # ==========================================================================
    if exec_ops['corr_ntr']:
        op.corr_ntr(name, save_dir, lowpass, highpass, exec_ops,
                    ermsub, subtomri, ica_evokeds, save_plots, figures_path)

    # close all plots
    if exec_ops['close_plots']:
        plot.close_all()

# GOING OUT OF SUBJECT LOOP
# %%============================================================================
# All-Subject-Analysis
# ==============================================================================
if exec_ops['cmp_label_time_course']:
    plot.cmp_label_time_course(data_path, lowpass, highpass, sub_dict, comp_dict,
                               subjects_dir, method, source_space_method, parcellation,
                               target_labels, save_plots, figures_path,
                               event_id, ev_ids_label_analysis, fuse_ab,
                               sub_script_path, exec_ops)

if fuse_ab:
    if exec_ops['create_func_label']:
        for key in ab_dict:
            print(60 * '=' + '\n' + key)
            if len(ab_dict[key]) > 1:
                name = (ab_dict[key][0], ab_dict[key][1])
                save_dir = (join(data_path, name[0]), join(data_path, name[1]))
                pattern = r'pp[0-9]+[a-z]?'
                if unspecified_names:
                    pattern = r'.*'
                match = re.match(pattern, name[0])
                prefix = match.group()
                subtomri = sub_dict[prefix]
            else:
                name = ab_dict[key][0]
                save_dir = join(data_path, name)
                pattern = r'pp[0-9]+[a-z]?'
                if unspecified_names:
                    pattern = r'.*'
                match = re.match(pattern, name)
                prefix = match.group()
                subtomri = sub_dict[prefix]
            op.create_func_label(name, save_dir, lowpass, highpass,
                                 method, event_id, subtomri, subjects_dir,
                                 source_space_method, label_origin,
                                 parcellation_orig, ev_ids_label_analysis,
                                 save_plots, figures_path, sub_script_path,
                                 n_std, fuse_ab)

if fuse_ab:
    if exec_ops['func_label_processing']:
        for key in ab_dict:
            print(60 * '=' + '\n' + key)
            if len(ab_dict[key]) > 1:
                name = (ab_dict[key][0], ab_dict[key][1])
                save_dir = (join(data_path, name[0]), join(data_path, name[1]))
                pattern = r'pp[0-9]+[a-z]?'
                if unspecified_names:
                    pattern = r'.*'
                match = re.match(pattern, name[0])
                prefix = match.group()
                subtomri = sub_dict[prefix]
            else:
                name = ab_dict[key][0]
                save_dir = join(data_path, name)
                pattern = r'pp[0-9]+[a-z]?'
                if unspecified_names:
                    pattern = r'.*'
                match = re.match(pattern, name)
                prefix = match.group()
                subtomri = sub_dict[prefix]
            op.func_label_processing(name, save_dir, lowpass, highpass,
                                     save_plots, figures_path, subtomri, subjects_dir,
                                     sub_script_path, ev_ids_label_analysis,
                                     corr_threshold, fuse_ab)

if exec_ops['sub_func_label_analysis']:
    plot.sub_func_label_analysis(lowpass, highpass, tmax, sub_files_dict,
                                 sub_script_path, label_origin, ev_ids_label_analysis, save_plots,
                                 figures_path, exec_ops)

if exec_ops['all_func_label_analysis']:
    plot.all_func_label_analysis(lowpass, highpass, tmax, files, sub_script_path,
                                 label_origin, ev_ids_label_analysis, save_plots,
                                 figures_path)

# %%============================================================================
# GRAND AVERAGES (sensor space and source space)
# ==============================================================================

if exec_ops['grand_avg_evokeds']:
    op.grand_avg_evokeds(data_path, grand_avg_dict, save_dir_averages,
                         lowpass, highpass, exec_ops, quality,
                         ana_h1h2)

if exec_ops['grand_avg_tfr']:
    op.grand_avg_tfr(data_path, grand_avg_dict, save_dir_averages,
                     lowpass, highpass, tfr_method)

if exec_ops['grand_avg_morphed']:
    op.grand_avg_morphed(grand_avg_dict, data_path, method, save_dir_averages,
                         lowpass, highpass, event_id)

if exec_ops['grand_avg_normal_morphed']:
    op.grand_avg_normal_morphed(grand_avg_dict, data_path, method, save_dir_averages,
                                lowpass, highpass, event_id)

if exec_ops['grand_avg_connect']:
    op.grand_avg_connect(grand_avg_dict, data_path, con_methods,
                         con_fmin, con_fmax, save_dir_averages,
                         lowpass, highpass)

if exec_ops['grand_avg_label_power']:
    op.grand_avg_label_power(grand_avg_dict, ev_ids_label_analysis,
                             data_path, lowpass, highpass,
                             target_labels, save_dir_averages)

if exec_ops['grand_avg_func_labels']:
    op.grand_avg_func_labels(grand_avg_dict, lowpass, highpass,
                             save_dir_averages, event_id, ev_ids_label_analysis,
                             subjects_dir, source_space_method,
                             parcellation_orig, sub_script_path, save_plots,
                             label_origin, figures_path, n_std)

# %%============================================================================
# GRAND AVERAGES PLOTS (sensor space and source space)
# ================================================================================

if exec_ops['plot_grand_avg_evokeds']:
    plot.plot_grand_avg_evokeds(lowpass, highpass, save_dir_averages, grand_avg_dict,
                                event_id, save_plots, figures_path, quality)

if exec_ops['plot_grand_avg_evokeds_h1h2']:
    plot.plot_grand_avg_evokeds_h1h2(lowpass, highpass, save_dir_averages, grand_avg_dict,
                                     event_id, save_plots, figures_path, quality)

if exec_ops['plot_grand_avg_tfr']:
    plot.plot_grand_avg_tfr(lowpass, highpass, baseline, tmin, tmax,
                            save_dir_averages, grand_avg_dict,
                            event_id, save_plots, figures_path)

if exec_ops['plot_grand_avg_stc']:
    plot.plot_grand_avg_stc(lowpass, highpass, save_dir_averages,
                            grand_avg_dict, mne_evoked_time, morph_to,
                            subjects_dir, event_id, save_plots,
                            figures_path)

if exec_ops['plot_grand_avg_stc_anim']:
    plot.plot_grand_avg_stc_anim(lowpass, highpass, save_dir_averages,
                                 grand_avg_dict, stc_animation, morph_to,
                                 subjects_dir, event_id, figures_path)

if exec_ops['plot_grand_avg_connect']:
    plot.plot_grand_avg_connect(lowpass, highpass, save_dir_averages,
                                grand_avg_dict, subjects_dir, morph_to, parcellation, con_methods, con_fmin, con_fmax,
                                save_plots, figures_path)

if exec_ops['plot_grand_avg_label_power']:
    plot.plot_grand_avg_label_power(grand_avg_dict, ev_ids_label_analysis, target_labels,
                                    save_dir_averages, tfr_freqs, tmin, tmax, lowpass,
                                    highpass, save_plots, figures_path)

# ==============================================================================
# STATISTICS SOURCE SPACE
# ==============================================================================

if exec_ops['statistics_source_space']:
    op.statistics_source_space(morphed_data_all, save_dir_averages,
                               independent_variable_1,
                               independent_variable_2,
                               time_window, n_permutations, lowpass, highpass,
                               overwrite)

# ==============================================================================
# PLOT GRAND AVERAGES OF SOURCE ESTIMATES WITH STATISTICS CLUSTER MASK
# ==============================================================================

if exec_ops['plot_grand_averages_source_estimates_cluster_masked']:
    plot.plot_grand_averages_source_estimates_cluster_masked(
        save_dir_averages, lowpass, highpass, subjects_dir, method, time_window,
        save_plots, figures_path, independent_variable_1,
        independent_variable_2, mne_evoked_time, p_threshold)
# ==============================================================================
# MISCELLANEOUS
# ==============================================================================

if exec_ops['pp_plot_latency_S1_corr']:
    plot.pp_plot_latency_S1_corr(data_path, files, lowpass, highpass,
                                 save_plots, figures_path)

# close all plots
if exec_ops['close_plots']:
    plot.close_all()

if exec_ops['shutdown']:
    ut.shutdown()
