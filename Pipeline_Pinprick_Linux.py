# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data
@author: Lau Møller Andersen
@email: lau.moller.andersen@ki.se | lau.andersen@cnru.dk
@github: https://github.com/ualsbombe/omission_frontiers.git

Adapted to Sektion Biomagnetismus Kopfklinik by Martin Schulz
@email: martin.schulz@stud.uni-heidelberg.de

Functions to implement:
- File search and copy function for new files
- plot compare evokeds
- Sensitivity Analysys
- bad epochs handling?
- Baseline SSP?
- Group analasys with condition-list(picking file and trial_type)
- except watershed_bem refurbish the bash commands
- Condition tags for subject/Grand Average Customizing
    - Comparative Plots
- Epoch rejection, when EOG/ECG exceeds certain value
- Source Estimate with MRI-Slides?
- Parameters in File und auf Cond/File angepasst (save params?)
- name --> subject
- beamformer
- evoked dict noch notwendig?
- Subjects as Classes?
"""

#==============================================================================
# IMPORTS
#%%============================================================================
import sys
from os.path import join, isfile
from datetime import datetime
import numpy as np
import mne

from pipeline_functions import io_functions as io
from pipeline_functions import operations_functions as op
from pipeline_functions import plot_functions as plot
from pipeline_functions import subject_organisation as suborg
from pipeline_functions import utilities as ut

#==============================================================================
# PATHS
#%%============================================================================
if sys.platform == 'win32':
    home_path = 'Z:/Promotion' # change this according to needs

if sys.platform == 'linux':
    home_path = '/mnt/z/Promotion' # change this according to needs

project_name = 'Pin-Prick-Projekt/PP_Messungen'
data_path = join(home_path, project_name, 'Daten')
subjects_dir = join(home_path, 'Freesurfer/Output')
mne.utils.set_config("SUBJECTS_DIR", subjects_dir, set_env=True)
save_dir_averages = join(data_path,'grand_averages')
figures_path = join(home_path, project_name, 'Figures/')


#add subjects, mri_subjects, sub_dict, bad_channels_dict
sub_list_path = join(data_path, '_Subject_scripts/sub_list.py')
mri_sub_list_path = join(data_path, '_Subject_scripts/mri_sub_list.py')
sub_dict_path = join(data_path, '_Subject_scripts/sub_dict.py')
erm_dict_path = join(data_path, '_Subject_scripts/erm_dict.py')
bad_channels_dict_path = join(data_path, '_Subject_scripts/bad_channels_dict.py')
sub_cond_dict_path = join(data_path, '_Subject_scripts/sub_cond_dict.py')

#==============================================================================
# SUBJECT ORGANISATION
#%%============================================================================
orig_data_path = join(home_path, 'Messungen_Dateien')
orig_mri_data_path = join(home_path, 'Freesurfer/Output')

if 0: # set 1 to run
    suborg.add_subjects(sub_list_path, home_path, project_name, data_path,
                        figures_path, subjects_dir, orig_data_path)

if 0: # set 1 to run
    suborg.add_mri_subjects(mri_sub_list_path, data_path)

if 0: # set 1 to run
    suborg.add_sub_dict(sub_dict_path, sub_list_path, data_path)

if 0: #set 1 to run
    suborg.add_erm_dict(erm_dict_path, sub_list_path, data_path)

predefined_bads = ['MEG 006', 'MEG 026', 'MEG 027', 'MEG 103']
if 0: # set 1 to run, # add like this:MEG 001,MEG 002,MEG 003,...;
      # for no bad channels don't type anything and assign
    suborg.add_bad_channels_dict(bad_channels_dict_path, sub_list_path, data_path,
                                 predefined_bads)

if 0:
    suborg.add_sub_cond_dict(sub_cond_dict_path, sub_list_path, data_path)

#Functions

all_subjects = suborg.read_subjects(sub_list_path)
all_mri_subjects = suborg.read_mri_subjects(mri_sub_list_path)
sub_to_mri = suborg.read_sub_dict(sub_dict_path)
erm_dict = suborg.read_sub_dict(erm_dict_path) # add None if not available
bad_channels_dict = suborg.read_bad_channels_dict(bad_channels_dict_path)
sub_cond_dict = suborg.read_sub_cond_dict(sub_cond_dict_path)
#==============================================================================
# WHICH SUBJECT?
#%%============================================================================

# Which File do you want to run?
# Type in the Number of the File in your sub_list.py = Line
    #possible input(examples):
        #'5'
        #'1,7,28'
        #'1-5'
        #'1-4,7,20-26'
        #'all'
"""['38,47,55,64',
   '39,48,56',
   '42,49,57,65',
   '43,50,58',
   '40,51,59,68',
   '41,52,60',
   '44,53,61,69',
   '45,54,62',
   '46,66']

'46,45,42,65,53,62'
"""

which_file_list = ['30-42']  # Has to be strings!

which_mri_subject = '59' # Has to be a string!

#==============================================================================
# OPERATIONS
#%%============================================================================
operations_to_apply = dict(

                    # OS commands

                    populate_data_directory=0, #don't do it in Linux if you're using also Windows!
                    mri_preprocessing=1, # enable to do any of the mri_subject-related functions
                    print_pipeline_analysis=0,

                    # WITHIN SUBJECT

                    # sensor space operations
                    filter_raw=0,
                    find_events=0,
                    find_eog_events=0,
                    epoch_raw=0,
                    run_ssp_er=0, # on Empty-Room-Data
                    apply_ssp_er=0,
                    run_ssp_clm=0, # on 1-Minute-Calm-Data
                    apply_ssp_clm=0,
                    run_ssp_eog=0, # EOG-Projection-Computation
                    apply_ssp_eog=0,
                    run_ssp_ecg=0, # ECG-Projection-Computation
                    apply_ssp_ecg=0,
                    run_ica=0, # only if EOG/EEG-Channels available, HIGPASS-FILTER RECOMMENDED!!!
                    apply_ica=0,
                    ica_pure=0,
                    get_evokeds=0,
                    TF_Morlet=0,

                    # source space operations (bash/Linux)
                    import_mri=0,
                    segment_mri=0, # long process (>10 h)
                    Test=0,
                    apply_watershed=1,
                    make_dense_scalp_surfaces=1, #until here all bash scripts!

                    mri_coreg=0,
                    setup_source_space=0,
                    create_forward_solution=0, # I disabled eeg here for pinprick, delete eeg=False in 398 operations_functions.py to reactivate
                    estimate_noise_covariance=0,
                    create_inverse_operator=0,
                    source_estimate=0,
                    vector_source_estimate=0,
                    ECD_fit=0,
                    morph_to_fsaverage=0,
                    morph_to_fsaverage_precomputed=0, # for slower Computers

                    # BETWEEN SUBJECTS

                    # compute grand averages
                    grand_averages_evokeds=0, # sensor space
                    average_morphed_data=0, # source space


                    # PLOTTING

                    # plotting sensor space (within subject)
                    plot_raw=0,
                    print_info=0,
                    plot_sensors=0,
                    plot_events=0,
                    plot_eog_events=0,
                    plot_filtered=0,
                    plot_power_spectra=0,
                    plot_power_spectra_epochs=0,
                    plot_power_spectra_topo=0,
                    plot_ssp=0, #
                    plot_ssp_eog=0, #EOG-Elektrodes have to be digitized and assigned to type 3
                    plot_ssp_ecg=0, #ECG-Elektrodes have to be digitized and assigned to type 3
                    plot_ica=0,
                    plot_ica_sources=0,
                    plot_epochs=0,
                    plot_epochs_image=0,
                    plot_epochs_topo=0,
                    plot_butterfly_evokeds=0,
                    plot_evoked_topo=0,
                    plot_evoked_topomap=0,
                    plot_evoked_field=0,
                    plot_evoked_joint=0,
                    plot_evoked_white=0,
                    plot_evoked_image=0,
                    animate_topomap=0, # in evoked


                    # plotting source space (within subject)
                    plot_transformation=0,
                    plot_source_space=0,
                    plot_bem=0,
                    plot_noise_covariance=0,
                    plot_source_estimates=0,
                    # added float() in 2549 surfer\viz.py to avoid error
                    # changed render_window.size to get_size() in mayavi/tools/figure.py
                    plot_animated_stc=0,
                    plot_vector_source_estimates=0, # plots in same window as plot_source_estimate
                    plot_snr=0,
                    plot_labels=0,
                    label_time_course=0,
                    label_time_course_avg=0,

                    # plotting sensor space (between subjects)
                    plot_grand_averages_evokeds=0,
                    plot_grand_averages_butterfly_evokeds=0,

                    # plotting source space (between subjects)
                    plot_grand_averages_source_estimates=0,

                    # statistics in source space
                    statistics_source_space=0,

                    # plot source space with statistics mask
                    plot_grand_averages_source_estimates_cluster_masked=0,

                    #general statistics
                    corr_ntr=0,
                    avg_ntr=0
                    )

#==============================================================================
# PARAMETERS
#%%============================================================================
#parameters_start
#OS
n_jobs = -1 #number of processor-cores to use, -1 for auto
enable_cuda = False # Using CUDA on supported graphics card e.g. for filtering
                    # cupy and appropriate CUDA-Drivers have to be installed
                    # https://mne-tools.github.io/dev/advanced_setup.html#advanced-setup
                    
# should files be overwritten
overwrite = True # this counts for all operations below that save output
save_plots = True # should plots be saved
close_plots = True # close plots after one subjects batch

# raw
lowpass = 80 # Hz
highpass = 1 # Hz # at least 1 if to apply ICA

# events
adjust_timeline_by_msec = -47 #delay to stimulus in ms

# epochs
min_duration = 0.005 # s
time_unit = 's'
tmin = -1.000 # s
tmax = 2.000 # s
baseline = (-0.800, -0.500) # [s]
autoreject = 1 # set 1 for autoreject
overwrite_ar = 0 # if to calculate new thresholds or to use previously calculated
reject = dict(grad=8000e-13) # if not reject with autoreject
flat = dict(grad=1e-15)
reject_eog_epochs=False
decim = 1 # downsampling factor
event_id = {'LBT':1,'mot_start':2,'offset':4,'start':32,'start2':41}
"""all_event_ids = {'35':1,'40':2,'45':4,'50':8,'55':16,'60':3,'65':5,
                 '70':9,'75':17,'80':6,'85':10,'90':18,'95':12}"""

# evokeds
detrend = False # somehow not working on all data

#TFA
TF_Morlet_Freqs = np.logspace(*np.log10([6, 35]), num=8)

#ICA
eog_channel = 'EEG 001'
ecg_channel = 'EEG 003'

# Layout (our special Neuromag-122-Layout, should be in same directory as script)
layout = mne.channels.read_layout('Neuromag_122', path = './')

# forward modeling
source_space_method = 'ico5'

# source reconstruction
use_calm_cov = False
method = 'MNE'
fixed_src = False # if the source is fixed(normal to cortex) or loose
mne_evoked_time = [0.050, 0.100, 0.200] # s
stc_animation = [0,0.5] # s
eeg_fwd = False

# Dipole-fit
ECDs = {}


ECD_min = 0.200
ECD_max = 0.250

target_labels = ['postcentral-lh']

# morph maps
morph_to='fsaverage'
vertices_to = [np.arange(10242), np.arange(10242)]

# grand averages
# empty containers to the put the single subjects data in
ga_conditions = ['ER']

# statistics
independent_variable_1 = 'standard_3'
independent_variable_2 = 'non_stimulation'
time_window = (0.050, 0.060)
n_permutations = 10000 # specify as integer

# statistics plotting
p_threshold = 1e-15 # 1e-15 is the smallest it can get for the way it is coded

# freesurfer and MNE-C commands
n_jobs_freesurfer = -1 # change according to amount of processors you have
                        # available
 # supply a method and a spacing/grade
                                  # see mne_setup_source_space --help in bash
                                  # methods 'spacing', 'ico', 'oct'

#parameters_stop
#==============================================================================
# PROCESSING LOOP
#%%============================================================================
# Pipeline Analysis
error_list = []
epoch_rejection = {}
n_events = {}
eog_contamination = {}
ar_values = {}
all_reject_channels = {}

#==========================================================================
# MRI-Subjects
#==========================================================================
if operations_to_apply['mri_preprocessing']:

    mri_subjects = suborg.mri_subject_selection(which_mri_subject, all_mri_subjects)

    print('Selected MRI-Subjects:')
    for i in mri_subjects:
        print(i)

    for mri_subject in mri_subjects:
        print('='*60 + '\n', mri_subject)

        #==========================================================================
        # BASH SCRIPTS
        #==========================================================================
        if operations_to_apply['segment_mri']:
            op.segment_mri(mri_subject, subjects_dir, n_jobs_freesurfer)

        if operations_to_apply['apply_watershed']:
            op.apply_watershed(mri_subject, subjects_dir, overwrite)

        if operations_to_apply['make_dense_scalp_surfaces']:
            op.make_dense_scalp_surfaces(mri_subject, subjects_dir, overwrite)

        #==========================================================================
        # Forward Modeling
        #==========================================================================
        if operations_to_apply['setup_source_space']:
            op.setup_source_space(mri_subject, subjects_dir, source_space_method,
                           overwrite, n_jobs)

        #==========================================================================
        # PLOT SOURCE SPACES
        #==========================================================================

        if operations_to_apply['plot_source_space']:
            plot.plot_source_space(mri_subject, subjects_dir, source_space_method, save_plots, figures_path)

        if operations_to_apply['plot_bem']:
            plot.plot_bem(mri_subject, subjects_dir, source_space_method, figures_path,
                          save_plots)

        # close plots
        if close_plots:
            plot.close_all()
#==========================================================================
# Subjects
#==========================================================================
for which_file in which_file_list:
    print('#'*60 + '\n' + f'Group {which_file} begun')

    subjects = suborg.file_selection(which_file, all_subjects)

    print('Selected Subjects:')
    for i in subjects:
        print(i)

    evoked_data_all = dict(pinprick=[], WU_First=[], WU_Last=[])
    morphed_data_all = dict(pinprick=[], WU_First=[], WU_Last=[])


    for subject in subjects:
        name = subject #changed for Kopfklinik-naming-convention
        subject_index = subjects.index(subject)
        save_dir = join(data_path, subject)
        try:
            bad_channels = bad_channels_dict[subject]
        except KeyError as k:
            print(f'No bad channels for {k}')
            suborg.add_bad_channels_dict(bad_channels_dict_path, sub_list_path, data_path,
                                         predefined_bads)
            continue
        subtomri = sub_to_mri[subject]
        ermsub = erm_dict[subject]
        event_id_list = []
        """
        # Handle event-id's
        event_id = dict()

        try:
            events = io.read_events(name, save_dir)

        except (FileNotFoundError, AttributeError):
            op.find_events(name, save_dir, min_duration,
                    adjust_timeline_by_msec,lowpass, highpass, overwrite)

            try:
                events = io.read_events(name, save_dir)
                u = np.unique(events[:,2])

                for t_name, value in all_event_ids.items():
                    if value in u:
                        event_id.update({t_name:value})

            except (FileNotFoundError, AttributeError):
                print('No events in this File')

        """
        # Print Subject Console Header
        print(60*'='+'\n'+name)

        #==========================================================================
        # POPULATE SUBJECT DIRECTORIES
        #==========================================================================

        if operations_to_apply['populate_data_directory']:
            op.populate_data_directory(home_path, project_name, data_path,
                                               figures_path, subjects_dir, subjects,
                                               event_id)

        #==========================================================================
        # FILTER RAW (MAXFILTERED)
        #==========================================================================

        if operations_to_apply['filter_raw']:
            op.filter_raw(name, save_dir, lowpass, highpass, overwrite, ermsub,
                                  data_path, n_jobs, enable_cuda)

        #==========================================================================
        # PRINT INFO
        #==========================================================================
        if operations_to_apply['print_info']:
            plot.print_info(name, save_dir, save_plots)

        if operations_to_apply['plot_sensors']:
            plot.plot_sensors(name, save_dir)

        #==========================================================================
        # FIND EVENTS
        #==========================================================================

        if operations_to_apply['find_events']:
            op.find_events(name, save_dir, min_duration,
                    adjust_timeline_by_msec,lowpass, highpass, overwrite)

        if operations_to_apply['find_eog_events']:
            op.find_eog_events(name, save_dir, eog_channel, eog_contamination)

        #==========================================================================
        # PLOT RAW DATA
        #==========================================================================

        if operations_to_apply['plot_raw']:
            plot.plot_raw(name, save_dir, overwrite, bad_channels, bad_channels_dict)

        if operations_to_apply['plot_filtered']:
            plot.plot_filtered(name, save_dir, lowpass, highpass, bad_channels)

        if operations_to_apply['plot_events']:
            plot.plot_events(name, save_dir,lowpass, highpass, save_plots, figures_path, subject, event_id)

        if operations_to_apply['plot_eog_events']:
            plot.plot_eog_events(name, save_dir)

        #==========================================================================
        # EPOCHS
        #==========================================================================

        if operations_to_apply['epoch_raw']:
            op.epoch_raw(name, save_dir,lowpass, highpass, event_id, tmin,
                              tmax, baseline, reject, flat, autoreject, overwrite_ar,
                              bad_channels, decim, n_events, epoch_rejection,
                              all_reject_channels, reject_eog_epochs, overwrite)

        #==========================================================================
        # PLOT POWER SPECTRA
        #==========================================================================

        if operations_to_apply['plot_power_spectra']:
            plot.plot_power_spectra(name, save_dir,lowpass, highpass, subject, save_plots,
                                    figures_path, bad_channels)

        if operations_to_apply['plot_power_spectra_epochs']:
            plot.plot_power_spectra_epochs(name, save_dir,lowpass, highpass, subject, save_plots,
                                    figures_path, bad_channels)

        if operations_to_apply['plot_power_spectra_topo']:
            plot.plot_power_spectra_topo(name, save_dir,lowpass, highpass, subject, save_plots,
                            figures_path, bad_channels, layout)

        #==========================================================================
        # SIGNAL SPACE PROJECTION
        #==========================================================================
        if operations_to_apply['run_ssp_er']:
            op.run_ssp_er(name, save_dir,lowpass, highpass, data_path, ermsub, bad_channels,
                                  eog_channel, ecg_channel, overwrite)

        if operations_to_apply['apply_ssp_er']:
            op.apply_ssp_er(name, save_dir,lowpass, highpass, overwrite)

        if operations_to_apply['run_ssp_clm']:
            op.run_ssp_clm(name, save_dir,lowpass, highpass, bad_channels, overwrite)

        if operations_to_apply['apply_ssp_clm']:
            op.apply_ssp_clm(name, save_dir,lowpass, highpass, overwrite)

        if operations_to_apply['run_ssp_eog']:
            op.run_ssp_eog(name, save_dir,lowpass, highpass, n_jobs, eog_channel,
                                       bad_channels, overwrite)

        if operations_to_apply['apply_ssp_eog']:
            op.apply_ssp_eog(name, save_dir,lowpass, highpass, overwrite)

        if operations_to_apply['run_ssp_ecg']:
            op.run_ssp_ecg(name, save_dir,lowpass, highpass, n_jobs, ecg_channel,
                                       bad_channels, overwrite)

        if operations_to_apply['apply_ssp_ecg']:
            op.apply_ssp_ecg(name, save_dir,lowpass, highpass, overwrite)

        if operations_to_apply['plot_ssp']:
            plot.plot_ssp(name, save_dir,lowpass, highpass, subject, save_plots,
                          figures_path, bad_channels, layout, ermsub)

        if operations_to_apply['plot_ssp_eog']:
            plot.plot_ssp_eog(name, save_dir,lowpass, highpass, subject, save_plots,
                                  figures_path, bad_channels, layout)

        if operations_to_apply['ica_pure']:
            op.ica_pure(name, save_dir,lowpass, highpass, overwrite, eog_channel,
                                ecg_channel, layout, reject, flat, bad_channels, autoreject,
                                overwrite_ar)

        if operations_to_apply['run_ica']:
            op.run_ica(name, save_dir,lowpass, highpass, eog_channel, ecg_channel,
                               reject, flat, bad_channels, overwrite, autoreject)

        #===========================================================================
        # PLOT COMPONENTS TO BE REMOVED
        #===========================================================================

        if operations_to_apply['plot_ica']:
            plot.plot_ica(name, save_dir,lowpass, highpass, subject, save_plots,
                          figures_path, layout)

        if operations_to_apply['plot_ica_sources']:
            plot.plot_ica_sources(name, save_dir,lowpass, highpass, subject, save_plots,
                          figures_path)

        #==========================================================================
        # LOAD NON-ICA'ED EPOCHS AND APPLY ICA
        #==========================================================================

        if operations_to_apply['apply_ica']:
            op.apply_ica(name, save_dir,lowpass, highpass, overwrite)

        #==========================================================================
        # PLOT CLEANED EPOCHS
        #==========================================================================
        if operations_to_apply['plot_epochs']:
            plot.plot_epochs(name, save_dir,lowpass, highpass, subject, save_plots,
                                   figures_path)

        if operations_to_apply['plot_epochs_image']:
            plot.plot_epochs_image(name, save_dir,lowpass, highpass, subject, save_plots,
                                   figures_path)

        if operations_to_apply['plot_epochs_topo']:
            plot.plot_epochs_topo(name, save_dir,lowpass, highpass, subject, save_plots,
                          figures_path, layout)

        #==========================================================================
        # EVOKEDS
        #==========================================================================

        if operations_to_apply['get_evokeds']:
            op.get_evokeds(name, save_dir,lowpass, highpass, operations_to_apply, ermsub,
                                   detrend, overwrite)

        #==========================================================================
        # PLOT EVOKEDS
        #==========================================================================

        if operations_to_apply['plot_evoked_topo']:
            plot.plot_evoked_topo(name, save_dir,lowpass, highpass, subject, save_plots,
                                  figures_path)

        if operations_to_apply['plot_evoked_topomap']:
            plot.plot_evoked_topomap(name, save_dir,lowpass, highpass, subject, save_plots,
                                     figures_path, layout)

        if operations_to_apply['plot_butterfly_evokeds']:
            plot.plot_butterfly_evokeds(name, save_dir,lowpass, highpass, subject, save_plots, figures_path,
                                        time_unit, ermsub, use_calm_cov)

        if operations_to_apply['plot_evoked_field']:
            plot.plot_evoked_field(name, save_dir,lowpass, highpass, subject, subtomri, subjects_dir,
                                   save_plots, figures_path, mne_evoked_time, n_jobs)

        if operations_to_apply['plot_evoked_joint']:
            plot.plot_evoked_joint(name, save_dir,lowpass, highpass, subject, save_plots,
                                   layout, figures_path, ECDs)

        if operations_to_apply['plot_evoked_white']:
            plot.plot_evoked_white(name, save_dir,lowpass, highpass, subject, save_plots, figures_path,
                                   ermsub, use_calm_cov)

        if operations_to_apply['plot_evoked_image']:
            plot.plot_evoked_image(name, save_dir,lowpass, highpass, subject, save_plots, figures_path)

        if operations_to_apply['animate_topomap']:
            plot.animate_topmap()

        #==========================================================================
        # TIME-FREQUENCY-ANALASYS
        #==========================================================================

        if operations_to_apply['TF_Morlet']:
            op.TF_Morlet(name, save_dir,lowpass, highpass, TF_Morlet_Freqs, decim, n_jobs)

        #==========================================================================
        # NOISE COVARIANCE MATRIX
        #==========================================================================

        if operations_to_apply['estimate_noise_covariance']:
            op.estimate_noise_covariance(name, save_dir,lowpass, highpass, overwrite, ermsub, data_path, bad_channels, n_jobs, use_calm_cov)

        if operations_to_apply['plot_noise_covariance']:
            plot.plot_noise_covariance(name, save_dir,lowpass, highpass, subject, subtomri, save_plots, figures_path, ermsub, use_calm_cov)

        #==========================================================================
        # CO-REGISTRATION
        #==========================================================================

        # use mne.gui.coregistration()

        if operations_to_apply['mri_coreg']:
            op.mri_coreg(name, save_dir, subtomri, subjects_dir)

        if operations_to_apply['plot_transformation']:
            plot.plot_transformation(name, save_dir, subtomri, subjects_dir, save_plots, figures_path)

        #==========================================================================
        # CREATE FORWARD MODEL
        #==========================================================================

        if operations_to_apply['create_forward_solution']:
            op.create_forward_solution(name, save_dir, subtomri, subjects_dir,
                                               source_space_method, overwrite, n_jobs, eeg_fwd)

        #==========================================================================
        # CREATE INVERSE OPERATOR
        #==========================================================================

        if operations_to_apply['create_inverse_operator']:
            op.create_inverse_operator(name, save_dir,lowpass, highpass,
                                            overwrite, ermsub, use_calm_cov, fixed_src)

        #==========================================================================
        # SOURCE ESTIMATE MNE
        #==========================================================================

        if operations_to_apply['source_estimate']:
            op.source_estimate(name, save_dir,lowpass, highpass, method, overwrite)

        if operations_to_apply['vector_source_estimate']:
            op.vector_source_estimate(name, save_dir,lowpass, highpass, method, overwrite)

        if operations_to_apply['ECD_fit']:
            op.ECD_fit(name, save_dir,lowpass, highpass, ermsub, subject, subjects_dir,
                               subtomri, use_calm_cov, ECDs, n_jobs, target_labels,
                               save_plots, figures_path)



        #==========================================================================
        # PLOT SOURCE ESTIMATES MNE
        #==========================================================================

        if operations_to_apply['plot_source_estimates']:
            plot.plot_source_estimates(name, save_dir,lowpass, highpass,
                                          subtomri, subjects_dir, subject,
                                          method, mne_evoked_time,
                                          save_plots, figures_path)

        if operations_to_apply['plot_vector_source_estimates']:
            plot.plot_vector_source_estimates(name, save_dir,lowpass, highpass,
                                          subtomri, subjects_dir, subject,
                                          method, mne_evoked_time,
                                          save_plots, figures_path)

        if operations_to_apply['plot_animated_stc']:
            plot.plot_animated_stc(name, save_dir,lowpass, highpass, subtomri, subjects_dir, subject,
                      method, mne_evoked_time, stc_animation, tmin, tmax,
                      save_plots, figures_path)

        if operations_to_apply['plot_snr']:
            plot.plot_snr(name, save_dir,lowpass, highpass, save_plots, figures_path)
        if operations_to_apply['plot_labels']:
            plot.plot_labels(subtomri, subjects_dir)
        if operations_to_apply['label_time_course']:
            plot.label_time_course(name, save_dir, lowpass, highpass, subtomri, target_labels,
                                   save_plots, figures_path)
        
        #==========================================================================
        # MORPH TO FSAVERAGE
        #==========================================================================

        if operations_to_apply['morph_to_fsaverage']:
            stcs = op.morph_data_to_fsaverage(name, save_dir,lowpass, highpass,
                                            subjects_dir, subject, subtomri,
                                            method,
                                            overwrite, n_jobs, vertices_to, morph_to)


        if operations_to_apply['morph_to_fsaverage_precomputed']:
            stcs = op.morph_data_to_fsaverage_precomputed(name, save_dir,lowpass, highpass, subjects_dir, subject,
                                                                  subtomri, method, overwrite, n_jobs, morph_to, vertices_to)

        #==========================================================================
        # GRAND AVERAGE EVOKEDS (within-subject part)
        #==========================================================================

        if operations_to_apply['grand_averages_evokeds']:
            evoked_data = io.read_evokeds(name, save_dir, lowpass, highpass)
            for evoked in evoked_data:
                trial_type = evoked.comment
                evoked_data_all[trial_type].append(evoked)

        #==========================================================================
        # GRAND AVERAGE MORPHED DATA (within-subject part)
        #==========================================================================

        if operations_to_apply['average_morphed_data'] or \
            operations_to_apply['statistics_source_space']:
            morphed_data = io.read_avg_source_estimates(name, save_dir,lowpass, highpass,
                                                        method)
            for trial_type in morphed_data:
                morphed_data_all[trial_type].append(morphed_data[trial_type])


        # close all plots
        if close_plots:
            plot.close_all()

        if autoreject and operations_to_apply['print_pipeline_analysis']:
            try:
                reject_value_path = join(save_dir, op.filter_string(lowpass, highpass) \
                                         + '_reject_value.py')
                with open(reject_value_path, 'r') as rv:
                    reject = {}
                    for item in rv:
                        if ':' in item:
                            key,value = item.split(':', 1)
                            value = value[:-1]
                            reject[key] = float(value)
        
                ar_values.update({name:reject})
            except FileNotFoundError:
                print('Autorejection not applied yet')
                continue

        #==========================================================================
        # General Statistics
        #==========================================================================
        if operations_to_apply['corr_ntr']:
            op.corr_ntr(name, save_dir, lowpass, highpass, operations_to_apply,
                        ermsub, subtomri, save_plots, figures_path)
            
        if operations_to_apply['avg_ntr']:
            op.avg_ntr(name, save_dir, lowpass, highpass, bad_channels, event_id,
                                tmin, tmax, baseline, figures_path, save_plots, autoreject,
                                overwrite_ar, reject, flat)


    # GOING OUT OF SUBJECT LOOP (FOR AVERAGES)

    #==============================================================================
    # GRAND AVERAGES (sensor space and source space)
    #==============================================================================

    if operations_to_apply['grand_averages_evokeds']:
        op.grand_average_evokeds(evoked_data_all, save_dir_averages,
                                        lowpass, highpass, which_file)

    if operations_to_apply['average_morphed_data']:
        op.average_morphed_data(morphed_data_all, method,
                                     save_dir_averages,lowpass, highpass, which_file)

    #==============================================================================
    # GRAND AVERAGES PLOTS (sensor space and source space)
    #==============================================================================

    if operations_to_apply['plot_grand_averages_evokeds']:
        plot.plot_grand_average_evokeds(name,lowpass, highpass, save_dir_averages,
                                        evoked_data_all, event_id_list,
                                        save_plots, figures_path, which_file)

    if operations_to_apply['plot_grand_averages_butterfly_evokeds']:
        plot.plot_grand_averages_butterfly_evokeds(name,lowpass, highpass, save_dir_averages,
                                                   event_id_list, save_plots, figures_path,
                                                   which_file)

    if operations_to_apply['plot_grand_averages_source_estimates']:
        plot.plot_grand_averages_source_estimates(name, save_dir_averages,lowpass, highpass,
                                                  subjects_dir, method,
                                                  mne_evoked_time, event_id_list, save_plots,
                                                  figures_path, which_file)

    if operations_to_apply['label_time_course_avg']:
        plot.label_time_course_avg(morphed_data_all, save_dir_averages,lowpass, highpass, method,
                          which_file, subjects_dir, source_space_method,
                          target_labels, save_plots, event_id_list, figures_path)
    #==============================================================================
    # STATISTICS SOURCE SPACE
    #==============================================================================

    if operations_to_apply['statistics_source_space']:
        op.statistics_source_space(morphed_data_all, save_dir_averages,
                                           independent_variable_1,
                                           independent_variable_2,
                                           time_window, n_permutations,lowpass, highpass,
                                           overwrite)

    #==============================================================================
    # PLOT GRAND AVERAGES OF SOURCE ESTIMATES WITH STATISTICS CLUSTER MASK
    #==============================================================================

    if operations_to_apply['plot_grand_averages_source_estimates_cluster_masked']:
        plot.plot_grand_averages_source_estimates_cluster_masked(
            name, save_dir_averages,lowpass, highpass, subjects_dir, method, time_window,
            save_plots, figures_path, independent_variable_1,
            independent_variable_2, mne_evoked_time, p_threshold)

#==============================================================================
# Print Pipeline Analysis
#==============================================================================
# Create a file from the Pipeline Analysis Console Output
if operations_to_apply['print_pipeline_analysis']:

    pa_path = join(data_path, '_Subject_scripts',
                   str(highpass) + '-' + str(lowpass) + 'Hz_' + 'PA.py')

    if not isfile(pa_path):
        pa_file = open(pa_path,'w')
        print(str(highpass) + '-' + str(lowpass) + 'Hz_' + 'PA.py', 'has been created')
        print('#'*60 + '\n' + 'Pipeline-Output-Analysis:', file=pa_file)

    else:
        pa_file = open(join(data_path, '_Subject_scripts',
                     str(highpass) + '-' + str(lowpass) + 'Hz_' + 'PA.py'),'a')
        print(4*'\n' + '#'*60 + '\n' + 'Pipeline-Output-Analysis:', file=pa_file)

    now = datetime.now()
    print(f'Executed on {now.date()} at {now.time()}', file=pa_file)

    print('-'*60 + '\n' + 'Parameters:', file=pa_file)
    # Get current Parameters from Pipeline_Pinprick.py
    with open('./Pipeline_Pinprick.py', 'r') as p:
        p = list(p)
        for l in p:
            if '#parameters_start\n' == l:
                start = p.index(l) + 1
            if '#parameters_stop\n' == l:
                stop = p.index(l)
        for l in p[start:stop]:
            if l!='\n' and l[0]!='#':
                print(l[:-1], file=pa_file)

    print('-'*60 + '\n' + 'Pipeline-Output-Analysis:', file=pa_file)
    for i in error_list:
        print(i, file=pa_file)

    print('-'*60 + '\n' + 'Percentage of rejected epochs:', file=pa_file)
    for i in epoch_rejection:
        print(i, ':', epoch_rejection[i], '%', file=pa_file)

    print('-'*60 + '\n' + 'n_events in Epochs', file=pa_file)
    for i in n_events:
        print(i, ':', n_events[i], 'events', file=pa_file)

    """
    print('-'*60 + '\n' + 'Epochs contaminated with EOG', file=pa_file)
    for i in eog_contamination:
        print(i,':',eog_contamination[i], file=pa_file)
    """
    if autoreject:
        print('-'*60 + '\n' + 'Autoreject-values', file=pa_file)
        for i in ar_values:
            print(i,':',ar_values[i], file=pa_file)

    print('-'*60 + '\n' + 'Channels responsible for rejection', file=pa_file)
    for i in all_reject_channels:
        print(i, ':', all_reject_channels[i], '\n', file=pa_file)

    pa_file.close()
