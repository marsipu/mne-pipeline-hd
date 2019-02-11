# -*- coding: utf-8 -*-
"""
Created on Mon Feb 11 03:11:47 2019

@author: Martin Schulz
"""

subject_operations = dict(add_subjects = 0,
                          add_mri_subjects = 0,
                          add_sub_dict = 0,
                          add_erm_dict = 0,
                          add_bad_channels = 0)

basic_operations = dict(populate_data_directory = 0, #don't do it in Linux if you're using also Windows!
                        mri_preprocessing = 0, # enable to do any of the mri_subject-related functions
                        erm_analysis = 0,
                        print_pipeline_analysis = 0)


sensor_space_operations = dict(filter_raw = 0,
                               find_events = 0,
                               find_eog_events = 0,
                               epoch_raw = 0,
                               run_ssp_er = 0, # on Empty-Room-Data
                               apply_ssp_er = 0,
                               run_ssp_clm = 0, # on 1-Minute-Calm-Data
                               apply_ssp_clm = 0,
                               run_ssp_eog = 0, # EOG-Projection-Computation
                               apply_ssp_eog = 0,
                               run_ssp_ecg = 0, # ECG-Projection-Computation
                               apply_ssp_ecg = 0,
                               run_ica = 0, # HIGPASS-FILTER RECOMMENDED!!!
                               apply_ica = 0,
                               ica_pure = 0,
                               get_evokeds = 0,
                               TF_Morlet = 0)


source_space_operations = dict(mri_coreg = 0,
                               create_forward_solution = 0, # I disabled eeg here for pinprick, delete eeg=False in 398 operations_functions.py to reactivate
                               estimate_noise_covariance = 0,
                               create_inverse_operator = 0,
                               source_estimate = 0,
                               vector_source_estimate = 0,
                               ECD_fit = 0,
                               morph_to_fsaverage = 0,
                               morph_to_fsaverage_precomputed = 0) # for slower Computers


mri_subject_operations = dict(import_mri = 0,
                              segment_mri = 0, # long process (>10 h)
                              Test = 0,
                              apply_watershed = 0,
                              make_dense_scalp_surfaces = 0, #until here all bash scripts!
                              prepare_bem = 0,
                              setup_source_space = 0)


grand_average_operations = dict(grand_averages_evokeds = 0, # sensor space
                                average_morphed_data = 0) # source space


sensor_space_plots = dict(plot_raw = 0,
                          print_info = 0,
                          plot_sensors = 0,
                          plot_events = 0,
                          plot_events_diff = 0,
                          plot_eog_events = 0,
                          plot_filtered = 0,
                          plot_power_spectra = 0,
                          plot_power_spectra_epochs = 0,
                          plot_power_spectra_topo = 0,
                          plot_ssp = 0, #
                          plot_ssp_eog = 0, #EOG-Elektrodes have to be digitized and assigned to type 3
                          plot_ssp_ecg = 0, #ECG-Elektrodes have to be digitized and assigned to type 3
                          plot_ica = 0,
                          plot_ica_sources = 0,
                          plot_epochs = 0,
                          plot_epochs_image = 0,
                          plot_epochs_topo = 0,
                          plot_butterfly_evokeds = 0,
                          plot_evoked_topo = 0,
                          plot_evoked_topomap = 0,
                          plot_evoked_field = 0,
                          plot_evoked_joint = 0,
                          plot_evoked_white = 0,
                          plot_evoked_image = 0,
                          animate_topomap = 0,
                          corr_ntr = 0,
                          avg_ntr = 0) # in evoked

source_space_plots = dict(plot_transformation = 0,
                          plot_source_space = 0,
                          plot_bem = 0,
                          plot_noise_covariance = 0,
                          plot_source_estimates = 0,
                          plot_animated_stc = 0,
                          plot_vector_source_estimates = 0, # plots in same window as plot_source_estimate
                          plot_snr = 0,
                          plot_labels = 0,
                          label_time_course = 0,
                          label_time_course_avg = 0)

grand_average_plots = dict(
                    # plotting sensor space (between subjects)
                    plot_grand_averages_evokeds = 0,
                    plot_grand_averages_butterfly_evokeds = 0,

                    # plotting source space (between subjects)
                    plot_grand_averages_source_estimates = 0,

                    # statistics in source space
                    statistics_source_space = 0,

                    # plot source space with statistics mask
                    plot_grand_averages_source_estimates_cluster_masked = 0)

all_fs = {'subject_operations':subject_operations,
                 'basic_operations':basic_operations,
                 'sensor_space_operations':sensor_space_operations,
                 'source_space_operations':source_space_operations,
                 'mri_subject_operations':mri_subject_operations,
                 'grand_average_operations':grand_average_operations,
                 'sensor_space_plots':sensor_space_plots,
                 'source_space_plots':source_space_plots,
                 'grand_average_plots':grand_average_plots}
