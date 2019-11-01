import numpy as np

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

# Pinprick-specific
pinprick = True  # Events including Rating
combine_ab = True  # pinprick-specific
cmp_cond = ['high', 'tactile']  # Specify two conditions, which will be compared

# raw
predefined_bads = [6, 7, 8, 26, 27, 103]  # Default bad channels
eog_digitized = True  # Set True, if the last 4 digitized points where EOG
ch_types = ['grad']
lowpass = 100  # Hz
highpass = 1  # Hz
erm_t_limit = 300  # Limits Empty-Room-Measurement-Length [s]

# events
adjust_timeline_by_msec = -100  # custom delay to stimulus in ms

# epochs
# Pinprick: Add 100ms Puffer on each side to allow latency alignment with group-averages
# Leave baseline at -0.100 to allow shift
etmin = -0.600  # start of epoch [s]
etmax = 1.600  # end of epoch [s]
baseline = (-0.600, -0.100)  # has to be a tuple [s]
enable_ica = True  # Use ica-epochs, create 1Hz-Highpass-Raw if not existent
autoreject = False  # set True to use autoreject
overwrite_ar = False  # if to calculate new thresholds or to use previously calculated
reject = dict(grad=8e-10)  # default reject parameter if not reject with autoreject
flat = dict(grad=1e-15)  # default flat parameter
reject_eog_epochs = False  # function to reject eog_epochs after use of find_eog_events
decim = 1  # downsampling factor
event_id = {'LBT': 1}  # dictionary to assign strings to the event_ids
# {'LBT':1, 'offset':4, 'lower_R':5, 'same_R':6, 'higher_R':7}

# evokeds
detrend = True  # sometimes not working
ana_h1h2 = True

# Time-Frequency-Analysis
tfr_freqs = np.arange(10, 100, 5)  # Frequencies to analyze
overwrite_tfr = True  # Recalculate and overwrite tfr
tfr_method = 'morlet'
multitaper_bandwith = 4.0
stockwell_width = 1.0

# ICA
eog_channel = 'EEG 001'  # Set Vertical EOG-Channel
ecg_channel = 'EEG 003'  # Set ECG-Channel

# forward modeling
source_space_method = 'ico5'  # See the MNE-Documentation for further details
eeg_fwd = False  # set True if working with EEG-Data

# source reconstruction
erm_noise_cov = True
calm_noise_cov = False  # Use of a specific time interval in a measurement for noise covariance
erm_ica = False  # Causes sometimes errors
inverse_method = 'dSPM'
toi = [-0.1, 0.5]  # Time of Interest for analysis
mne_evoked_time = [0.1, 0.15, 0.2]  # time points to be displayed in several plots [s]
stc_interactive = False  # interactive stc-plots
mixn_dip = True
stc_animation = (0, 0.5)  # time span for stc-animation [s]
parcellation = 'aparc'
parcellation_orig = 'aparc_sub'
ev_ids_label_analysis = ['LBT']
n_std = 4  # Determing the amount of standard-deviations, the prominence must have
corr_threshold = 0.95

# connectivity
con_methods = ['pli', 'wpli2_debiased', 'plv']  # methods for connectivity plots
con_fmin = 30  # fmin for connectivity plot
con_fmax = 80  # fmax for connectivity plot

# Dipole-fit
ecds = {'pp1a_128_a': {'Dip1': [0, 0.5]},
        'pp20_512_a': {'Dip1': [0.05, 0.15]},
        'pp20_512_b': {'Dip1': [-0.075, 0.05]}}  # Assign manually time points [s] to each file to make a dipole fit

# grand averages
morph_to = 'fsaverage'  # name of the freesurfer subject to be morphed to

# statistics (still original from Andersen, may not work)
independent_variable_1 = 'standard_3'
independent_variable_2 = 'non_stimulation'
time_window = (0.050, 0.060)
n_permutations = 10000  # specify as integer

# statistics plotting
p_threshold = 1e-15  # 1e-15 is the smallest it can get for the way it is coded

# freesurfer and MNE-C commands
n_jobs_freesurfer = 4  # change according to amount of processors you have available

target_labels = {'lh': ['postcentral-lh']}

# target_labels = {'lh': ['Somatosensory and Motor Cortex-lh',
#                         'Posterior Opercular Cortex-lh',
#                         'Insular and Frontal Opercular Cortex-lh'],
#                  'rh': ['Somatosensory and Motor Cortex-rh',
#                         'Posterior Opercular Cortex-rh',
#                         'Insular and Frontal Opercular Cortex-rh']}

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
