# -*- coding: utf-8 -*-
"""
Created on Mon Feb 11 03:11:47 2019

@author: Martin Schulz
"""

# subject_operations = dict(add_files=0,
#                           add_mri_subjects=0,
#                           add_sub_dict=0,
#                           add_erm_dict=0,
#                           add_bad_channels=0)

basic_operations = dict(erm_analysis=0,
                        close_plots=1,
                        shutdown=0)

pinprick_functions = dict(pp_event_handling=0,
                          pp_combine_evokeds_ab=0,
                          pp_alignment=0,
                          motor_erm_analysis=0,
                          plot_ab_combined=0)

custom_functions = dict(melofix_event_handling=0,
                        kristin_event_handling=0)

sensor_space_operations = dict(filter_raw=0,
                               find_events=0,
                               find_eog_events=0,
                               epoch_raw=0,
                               run_ssp_er=0,  # on Empty-Room-Data
                               apply_ssp_er=0,
                               run_ssp_clm=0,  # on 1-Minute-Calm-Data
                               apply_ssp_clm=0,
                               run_ssp_eog=0,  # EOG-Projection-Computation
                               apply_ssp_eog=0,
                               run_ssp_ecg=0,  # ECG-Projection-Computation
                               apply_ssp_ecg=0,
                               run_ica=0,  # HIGPASS-FILTER RECOMMENDED!!!
                               apply_ica=0,
                               get_evokeds=0,
                               get_h1h2_evokeds=0,
                               tfr=0)

mri_subject_operations = dict(apply_watershed=0,
                              make_dense_scalp_surfaces=0,  # until here all bash scripts!
                              prepare_bem=0,
                              setup_src=0,
                              compute_src_distances=0,
                              setup_vol_src=0,
                              morph_subject=0,
                              morph_labels_from_fsaverage=0,
                              plot_source_space=0,
                              plot_bem=0,
                              plot_labels=0)

source_space_operations = dict(mri_coreg=0,
                               create_forward_solution=0,
                               # I disabled eeg here for pinprick, delete eeg=False in 398 operations_functions.py to reactivate
                               estimate_noise_covariance=0,
                               create_inverse_operator=0,
                               source_estimate=0,
                               vector_source_estimate=0,
                               mixed_norm_estimate=0,
                               ecd_fit=0,
                               create_func_label=0,
                               func_label_processing=0,
                               func_label_ctf_ps=0,
                               label_power_phlck=0,
                               apply_morph=0,
                               apply_morph_normal=0,
                               source_space_connectivity=0)

grand_average_operations = dict(grand_avg_evokeds=0,  # sensor space
                                grand_avg_tfr=0,
                                grand_avg_morphed=0,
                                grand_avg_normal_morphed=0,
                                grand_avg_connect=0,
                                grand_avg_label_power=0,
                                grand_avg_func_labels=0,
                                grand_avg_func_labels_processing=0)  # source space

sensor_space_plots = dict(plot_raw=0,
                          plot_sensors=0,
                          plot_events=0,
                          plot_events_diff=0,
                          plot_eog_events=0,
                          plot_filtered=0,
                          plot_power_spectra=0,
                          plot_power_spectra_epochs=0,
                          plot_power_spectra_topo=0,
                          plot_tfr=0,
                          tfr_event_dynamics=0,
                          plot_ssp=0,  #
                          plot_ssp_eog=0,  # EOG-Elektrodes have to be digitized and assigned to type 3
                          plot_ssp_ecg=0,  # ECG-Elektrodes have to be digitized and assigned to type 3
                          plot_epochs=0,
                          plot_epochs_image=0,
                          plot_epochs_topo=0,
                          plot_epochs_drop_log=0,
                          plot_evoked_butterfly=0,
                          plot_evoked_topo=0,
                          plot_evoked_topomap=0,
                          plot_evoked_field=0,
                          plot_evoked_joint=0,
                          plot_evoked_white=0,
                          plot_evoked_image=0,
                          plot_evoked_compare=0,
                          plot_evoked_h1h2=0,
                          plot_gfp=0,
                          corr_ntr=0)

source_space_plots = dict(plot_transformation=0,
                          plot_sensitivity_maps=0,
                          plot_noise_covariance=0,
                          plot_stc=0,
                          plot_normal_stc=0,
                          plot_vector_stc=0,
                          plot_mixn=0,
                          plot_animated_stc=0,
                          plot_snr=0,
                          plot_label_time_course=0,
                          cmp_label_time_course=0,
                          sub_func_label_analysis=0,
                          all_func_label_analysis=0,
                          plot_label_power_phlck=0,
                          plot_source_space_connectivity=0)

grand_average_plots = dict(
    # plotting sensor space (between subjects)
    plot_grand_avg_evokeds=0,
    plot_grand_avg_evokeds_h1h2=0,
    plot_grand_avg_tfr=0,

    # plotting source space (between subjects)
    plot_grand_avg_stc=0,
    plot_grand_avg_stc_anim=0,
    plot_grand_avg_connect=0,
    plot_grand_avg_label_power=0,

    # statistics in source space
    statistics_source_space=0,

    # plot source space with statistics mask
    plot_grand_averages_source_estimates_cluster_masked=0,

    pp_plot_latency_S1_corr=0)

# 'subject_operations': subject_operations,
all_fs_gs = {'basic_operations': basic_operations,
             'pinprick_functions': pinprick_functions,
             'custom_functions': custom_functions,
             'sensor_space_operations': sensor_space_operations,
             'mri_subject_operations': mri_subject_operations,
             'source_space_operations': source_space_operations,
             'grand_average_operations': grand_average_operations,
             'sensor_space_plots': sensor_space_plots,
             'source_space_plots': source_space_plots,
             'grand_average_plots': grand_average_plots}

all_fs = {}
for fg in all_fs_gs:
    for f, v in all_fs_gs[fg].items():
        all_fs.update({f: v})
