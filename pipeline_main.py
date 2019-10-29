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
import shutil
import os
from os.path import join, isfile, exists
from importlib import reload, util
import re
import mne

from pipeline_functions import io_functions as io
from pipeline_functions import operations_functions as op
from pipeline_functions import plot_functions as plot
from pipeline_functions import subject_organisation as suborg
from pipeline_functions import utilities as ut
from pipeline_functions import operations_dict as opd
from pipeline_functions import decorators as decor

from custom_functions import pinprick_functions as ppf
from custom_functions import melofix_functions as mff

def reload_all():
    reload(io)
    reload(op)
    reload(plot)
    reload(suborg)
    reload(ut)
    reload(opd)
    reload(decor)


reload_all()
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
# Todo: Pipeline 2.0
#  QT-Windows
#  Parameters in own script
#  Label-Selection-GUI
#  Choose-Subject-Window
#  Default Function-Buttons selected
#  Assistant for Regular Expressions
which_file = '1'  # Has to be a string/enclosed in apostrophs-
quality = ['all']
modality = ['all']
which_mri_subject = 'all'  # Has to be a string/enclosed in apostrophs
which_erm_file = 'all'  # Has to be a string/enclosed in apostrophs
which_motor_erm_file = 'all'  # Has to be a string/enclosed in apostrophs
# %%============================================================================
# GUI CALL
# ==============================================================================
exec_ops = ut.choose_function()
# %%============================================================================
# PATHS (TO SET)
# ==============================================================================
# specify the path to a general analysis folder according to your OS
if sys.platform == 'win32':
    # home_path = 'Z:/Promotion'  # Windows-Path
    home_path = 'Y:/Pinprick-Offline'
elif sys.platform == 'linux':
    home_path = '/mnt/z/Promotion'  # Linux-Path
elif sys.platform == 'darwin':
    home_path = 'Users/'  # Mac-Path
else:
    home_path = 'Z:/Promotion'  # some other path
project_name = 'Andre_Test'  # specify the name for your project as a folder
orig_data_path = join(home_path, project_name, 'meg')  # location of original-data
subjects_dir = join(home_path, 'Freesurfer/Output')  # name of your Freesurfer
# %%============================================================================
# LOAD PARAMETERS
# ==============================================================================
script_path = os.path.dirname(os.path.realpath(__file__))
if not isfile(join(home_path, project_name, 'parameters.py')):
    from templates.parameters_template import *

    shutil.copy2(join(script_path, 'templates/parameters_template.py'), join(home_path, project_name, 'parameters.py'))
    print('Hugi')
else:
    # sys.path.append(join(home_path, project_name))
    # this is generally not recommended for good style, but facilitates here
    # maintenance of the parameters file.
    # Be careful not to reassign variables of the parameters-file in this file
    spec = util.spec_from_file_location('parameters', join(home_path, project_name, 'parameters.py'))
    module = util.module_from_spec(spec)
    sys.modules['parameters'] = module
    spec.loader.exec_module(module)
    from parameters import *

    print('Wugi')
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
    figures_path = join(home_path, project_name, f'Figures/{highpass}-{lowpass}_Hz')

# add file_names, mri_subjects, sub_dict, bad_channels_dict
file_list_path = join(sub_script_path, 'file_list.py')
erm_list_path = join(sub_script_path, 'erm_list.py')  # ERM means Empty-Room
motor_erm_list_path = join(sub_script_path, 'motor_erm_list.py')  # Special for Pinprick
mri_sub_list_path = join(sub_script_path, 'mri_sub_list_pp.py')
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
        os.makedirs(p)
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
run_mrisf = False
for msop in opd.mri_subject_operations:
    if exec_ops[msop]:
        run_mrisf = True
if run_mrisf:
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

        if exec_ops['prepare_bem']:
            op.prepare_bem(mri_subject, subjects_dir)

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

        if exec_ops['setup_vol_src']:
            op.setup_vol_src(mri_subject, subjects_dir)

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
try:
    quality_dict = ut.read_dict_file('quality', sub_script_path)
except FileNotFoundError:
    print('No quality_dict yet created')
    quality_dict = dict()

basic_pattern = r'(pp[0-9][0-9]*[a-z]*)_([0-9]{0,3}t?)_([a,b]$)'
if not exec_ops['erm_analysis'] and not exec_ops['motor_erm_analysis']:
    silenced_files = set()
    for file in files:
        if 'all' not in quality:
            file_quality = int(quality_dict[file])
            if file_quality not in quality:
                silenced_files.add(file)

        if 'all' not in modality:
            match = re.match(basic_pattern, file)
            file_modality = match.group(2)
            if file_modality not in modality:
                silenced_files.add(file)

    for df in silenced_files:
        files.remove(df)

if len(all_files) == 0:
    print('No files in file_list!')
    print('Add some folders(the ones with the date) to your orig_data_path-folder and check "add_files"')
else:
    print(f'Selected {len(files)} Subjects:')
    for f in files:
        print(f)

# Get dicts grouping the files together depending on their names to allow grand_averaging:
ab_dict, comp_dict, grand_avg_dict, sub_files_dict, cond_dict = ut.get_subject_groups(files, combine_ab,
                                                                                      unspecified_names)
morphed_data_all = dict(LBT=[], offset=[], lower_R=[], same_R=[], higher_R=[])

if exec_ops['plot_ab_combined']:
    files = [f for f in ab_dict]

for name in files:

    # Print Subject Console Header
    print(60 * '=' + '\n' + name)
    prog = round((files.index(name)) / len(files) * 100, 2)
    print(f'Progress: {prog} %')

    if exec_ops['erm_analysis'] or exec_ops['motor_erm_analysis']:
        save_dir = join(home_path, project_name, 'Daten/empty_room_data')
        data_path = join(home_path, project_name, 'Daten/empty_room_data')
    elif exec_ops['plot_ab_combined']:
        save_dir = join(save_dir_averages, 'ab_combined')
    else:
        save_dir = join(data_path, name)

    if print_info:
        info = io.read_info(name, save_dir)
        print(info)

    # Use Regular Expressions to make ermsub and subtomri assignement easier
    if not unspecified_names:
        pattern = r'pp[0-9]+[a-z]?'
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
        if exec_ops['plot_ab_combined']:
            bad_channels = []
        else:
            try:
                bad_channels = bad_channels_dict[name]
            except KeyError as k:
                print(f'No bad channels for {k}')
                bad_channels = []
                suborg.add_bad_channels_dict(bad_channels_dict_path, file_list_path,
                                             erm_list_path, motor_erm_list_path,
                                             data_path, predefined_bads,
                                             sub_script_path)
    else:
        ermsub = erm_dict[name]
        subtomri = sub_dict[name]
        bad_channels = bad_channels_dict[name]

    # ==========================================================================
    # FILTER RAW
    # ==========================================================================

    if exec_ops['filter_raw']:
        op.filter_raw(name, save_dir, lowpass, highpass, ermsub,
                      data_path, n_jobs, enable_cuda, bad_channels, erm_t_limit,
                      enable_ica, eog_digitized)

    # ==========================================================================
    # FIND EVENTS
    # ==========================================================================

    if exec_ops['find_events']:
        op.find_events(name, save_dir, adjust_timeline_by_msec, overwrite, exec_ops)

    if exec_ops['pp_event_handling']:
        ppf.pp_event_handling(name, save_dir, adjust_timeline_by_msec, overwrite,
                              sub_script_path, save_plots, figures_path, exec_ops)

    if exec_ops['melofix_event_handling']:
        mff.melofix_event_handling(name, save_dir, adjust_timeline_by_msec, overwrite,
                                   sub_script_path, save_plots, figures_path, exec_ops)

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
    # if exec_ops['run_ssp_er']:
    #     op.run_ssp_er(name, save_dir, lowpass, highpass, data_path, ermsub, bad_channels,
    #                   overwrite)
    #
    # if exec_ops['apply_ssp_er']:
    #     op.apply_ssp_er(name, save_dir, lowpass, highpass, overwrite)
    #
    # if exec_ops['run_ssp_clm']:
    #     op.run_ssp_clm(name, save_dir, lowpass, highpass, bad_channels, overwrite)
    #
    # if exec_ops['apply_ssp_clm']:
    #     op.apply_ssp_clm(name, save_dir, lowpass, highpass, overwrite)
    #
    # if exec_ops['run_ssp_eog']:
    #     op.run_ssp_eog(name, save_dir, n_jobs, eog_channel,
    #                    bad_channels, overwrite)
    #
    # if exec_ops['apply_ssp_eog']:
    #     op.apply_ssp_eog(name, save_dir, lowpass, highpass, overwrite)
    #
    # if exec_ops['run_ssp_ecg']:
    #     op.run_ssp_ecg(name, save_dir, n_jobs, ecg_channel,
    #                    bad_channels, overwrite)
    #
    # if exec_ops['apply_ssp_ecg']:
    #     op.apply_ssp_ecg(name, save_dir, lowpass, highpass, overwrite)
    #
    # if exec_ops['plot_ssp']:
    #     plot.plot_ssp(name, save_dir, lowpass, highpass, save_plots,
    #                   figures_path, ermsub)
    #
    # if exec_ops['plot_ssp_eog']:
    #     plot.plot_ssp_eog(name, save_dir, lowpass, highpass, save_plots,
    #                       figures_path)
    #
    # if exec_ops['plot_ssp_ecg']:
    #     plot.plot_ssp_ecg(name, save_dir, lowpass, highpass, save_plots,
    #                       figures_path)

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
                       detrend, enable_ica, overwrite)

    if exec_ops['get_h1h2_evokeds']:
        op.get_h1h2_evokeds(name, save_dir, lowpass, highpass, enable_ica,
                            exec_ops, ermsub, detrend)

    # ==========================================================================
    # TIME-FREQUENCY-ANALASYS
    # ==========================================================================

    if exec_ops['tfr']:
        op.tfr(name, save_dir, lowpass, highpass, enable_ica, tfr_freqs, overwrite_tfr,
               tfr_method, multitaper_bandwith, stockwell_width, n_jobs)

    # ==========================================================================
    # NOISE COVARIANCE MATRIX
    # ==========================================================================

    if exec_ops['estimate_noise_covariance']:
        op.estimate_noise_covariance(name, save_dir, lowpass, highpass, overwrite,
                                     ermsub, data_path, baseline, bad_channels,
                                     n_jobs, erm_noise_cov, calm_noise_cov,
                                     enable_ica, erm_ica)

    if exec_ops['plot_noise_covariance']:
        plot.plot_noise_covariance(name, save_dir, lowpass, highpass,
                                   save_plots, figures_path, erm_noise_cov, ermsub,
                                   calm_noise_cov)

    # ==========================================================================
    # CO-REGISTRATION
    # ==========================================================================

    # use mne.gui.coregistration()

    if exec_ops['mri_coreg']:
        op.mri_coreg(name, save_dir, subtomri, subjects_dir)

    if exec_ops['plot_transformation']:
        plot.plot_transformation(name, save_dir, subtomri, subjects_dir,
                                 save_plots, figures_path)

    if exec_ops['plot_sensitivity_maps']:
        plot.plot_sensitivity_maps(name, save_dir, subjects_dir, ch_types,
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
                                   overwrite, ermsub, calm_noise_cov,
                                   erm_noise_cov)

    # ==========================================================================
    # SOURCE ESTIMATE MNE
    # ==========================================================================

    if exec_ops['source_estimate']:
        op.source_estimate(name, save_dir, lowpass, highpass, inverse_method, toi,
                           overwrite)

    if exec_ops['vector_source_estimate']:
        op.vector_source_estimate(name, save_dir, lowpass, highpass,
                                  inverse_method, toi, overwrite)

    if exec_ops['mixed_norm_estimate']:
        op.mixed_norm_estimate(name, save_dir, lowpass, highpass, toi, inverse_method, erm_noise_cov,
                               ermsub, calm_noise_cov, event_id, mixn_dip, overwrite)

    if exec_ops['ecd_fit']:
        op.ecd_fit(name, save_dir, lowpass, highpass, ermsub, subjects_dir,
                   subtomri, erm_noise_cov, calm_noise_cov, ecds,
                   save_plots, figures_path)

    if exec_ops['apply_morph']:
        stcs = op.apply_morph(name, save_dir, lowpass, highpass,
                              subjects_dir, subtomri, inverse_method,
                              overwrite, morph_to,
                              source_space_method, event_id)

    if exec_ops['apply_morph_normal']:
        stcs = op.apply_morph_normal(name, save_dir, lowpass, highpass,
                                     subjects_dir, subtomri, inverse_method,
                                     overwrite, morph_to,
                                     source_space_method, event_id)

    if not combine_ab:
        if exec_ops['create_func_label']:
            op.create_func_label(name, save_dir, lowpass, highpass,
                                 inverse_method, event_id, subtomri, subjects_dir,
                                 source_space_method, label_origin,
                                 parcellation_orig, ev_ids_label_analysis,
                                 save_plots, figures_path, sub_script_path,
                                 n_std, combine_ab)

    if not combine_ab:
        if exec_ops['func_label_processing']:
            op.func_label_processing(name, save_dir, lowpass, highpass,
                                     save_plots, figures_path, subtomri, subjects_dir,
                                     sub_script_path, ev_ids_label_analysis,
                                     corr_threshold, combine_ab)

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
        plot.plot_raw(name, save_dir, bad_channels)

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
                               figures_path, quality_dict)

    if exec_ops['plot_evoked_white']:
        plot.plot_evoked_white(name, save_dir, lowpass, highpass,
                               save_plots, figures_path, erm_noise_cov, ermsub, calm_noise_cov)

    if exec_ops['plot_evoked_image']:
        plot.plot_evoked_image(name, save_dir, lowpass, highpass,
                               save_plots, figures_path)

    if exec_ops['plot_evoked_h1h2']:
        plot.plot_evoked_h1h2(name, save_dir, lowpass, highpass, event_id,
                              save_plots, figures_path)

    if exec_ops['plot_gfp']:
        plot.plot_gfp(name, save_dir, lowpass, highpass, save_plots,
                      figures_path)
    # ==========================================================================
    # PLOT SOURCE ESTIMATES MNE
    # ==========================================================================

    if exec_ops['plot_stc']:
        plot.plot_stc(name, save_dir, lowpass, highpass,
                      subtomri, subjects_dir,
                      inverse_method, mne_evoked_time, event_id,
                      stc_interactive, save_plots, figures_path)

    if exec_ops['plot_normal_stc']:
        plot.plot_normal_stc(name, save_dir, lowpass, highpass,
                             subtomri, subjects_dir,
                             inverse_method, mne_evoked_time, event_id,
                             stc_interactive, save_plots, figures_path)

    if exec_ops['plot_vector_stc']:
        plot.plot_vector_stc(name, save_dir, lowpass, highpass, subtomri, subjects_dir,
                             inverse_method, mne_evoked_time, event_id, stc_interactive,
                             save_plots, figures_path)

    if exec_ops['plot_mixn']:
        plot.plot_mixn(name, save_dir, lowpass, highpass, subtomri, subjects_dir,
                       mne_evoked_time, event_id, stc_interactive,
                       save_plots, figures_path, mixn_dip, parcellation)

    if exec_ops['plot_animated_stc']:
        plot.plot_animated_stc(name, save_dir, lowpass, highpass, subtomri,
                               subjects_dir, inverse_method, stc_animation, event_id,
                               figures_path, ev_ids_label_analysis)

    if exec_ops['plot_snr']:
        plot.plot_snr(name, save_dir, lowpass, highpass, save_plots, figures_path,
                      inverse_method, event_id)

    if exec_ops['plot_label_time_course']:
        plot.plot_label_time_course(name, save_dir, lowpass, highpass,
                                    subtomri, subjects_dir, inverse_method, source_space_method,
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
                                     n_jobs, overwrite, enable_ica,
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
                    ermsub, subtomri, enable_ica, save_plots, figures_path)

    # close all plots
    if exec_ops['close_plots']:
        plot.close_all()

# GOING OUT OF SUBJECT LOOP
# %%============================================================================
# All-Subject-Analysis
# ==============================================================================
if exec_ops['pp_alignment']:
    op.pp_alignment(ab_dict, cond_dict, sub_dict, data_path, lowpass, highpass, sub_script_path,
                    event_id, subjects_dir, inverse_method, source_space_method,
                    parcellation, figures_path)

if exec_ops['cmp_label_time_course']:
    plot.cmp_label_time_course(data_path, lowpass, highpass, sub_dict, comp_dict,
                               subjects_dir, inverse_method, source_space_method, parcellation,
                               target_labels, save_plots, figures_path,
                               event_id, ev_ids_label_analysis, combine_ab,
                               sub_script_path, exec_ops)

if combine_ab:
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
                                 inverse_method, event_id, subtomri, subjects_dir,
                                 source_space_method, label_origin,
                                 parcellation_orig, ev_ids_label_analysis,
                                 save_plots, figures_path, sub_script_path,
                                 n_std, combine_ab)

if combine_ab:
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
                                     corr_threshold, combine_ab)

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

if exec_ops['combine_evokeds_ab']:
    op.combine_evokeds_ab(data_path, save_dir_averages, lowpass, highpass, ab_dict)

if exec_ops['grand_avg_tfr']:
    op.grand_avg_tfr(data_path, grand_avg_dict, save_dir_averages,
                     lowpass, highpass, tfr_method)

if exec_ops['grand_avg_morphed']:
    op.grand_avg_morphed(grand_avg_dict, data_path, inverse_method, save_dir_averages,
                         lowpass, highpass, event_id)

if exec_ops['grand_avg_normal_morphed']:
    op.grand_avg_normal_morphed(grand_avg_dict, data_path, inverse_method, save_dir_averages,
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

if exec_ops['plot_evoked_compare']:
    plot.plot_evoked_compare(data_path, save_dir_averages, lowpass, highpass, comp_dict, combine_ab, event_id)

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
        save_dir_averages, lowpass, highpass, subjects_dir, inverse_method, time_window,
        save_plots, figures_path, independent_variable_1,
        independent_variable_2, mne_evoked_time, p_threshold)
# ==============================================================================
# MISCELLANEOUS
# ==============================================================================

if exec_ops['pp_plot_latency_S1_corr']:
    plot.pp_plot_latency_s1_corr(data_path, files, lowpass, highpass,
                                 save_plots, figures_path)

# close all plots
if exec_ops['close_plots']:
    plot.close_all()

if exec_ops['shutdown']:
    ut.shutdown()
