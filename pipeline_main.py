# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data
Adapted from Lau Møller Andersen
@author: Martin Schulz
@email: martin.schulz@stud.uni-heidelberg.de
@github: marsipu/mne_pipeline_hd
Adapted to Melody Processing of Kim's data
"""
# %%============================================================================
# IMPORTS
# ==============================================================================
import sys
import shutil
import re
import mne
from os.path import join, isfile
from importlib import reload, util
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from basic_functions import operations_functions as op, io_functions as io, plot_functions as plot
from pipeline_functions import gui_functions as guif, subject_organisation as suborg, \
    operations_dict as opd
from pipeline_functions import decorators as decor, utilities as ut

from custom_functions import pinprick_functions as ppf
from custom_functions import melofix_functions as mff
from custom_functions import kristins_functions as kf


def reload_all():
    reload(io)
    reload(op)
    reload(plot)
    reload(suborg)
    reload(ut)
    reload(opd)
    reload(decor)
    reload(guif)
    reload(ppf)
    reload(mff)
    reload(kf)


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
# 'all,!4-6' (All files except 4-6)which
# %%============================================================================
# GUI CALL
# ==============================================================================
# Todo: Call functions from an own module and let the Main-Window stay open while execution
# matplotlib.use("Qt5Agg")
app_name = 'mne_pipeline_hd'
if sys.platform.startswith("darwin"):
    try:  # set bundle name on macOS (app name shown in the menu bar)
        from Foundation import NSBundle

        bundle = NSBundle.mainBundle()
        if bundle:
            info = (bundle.localizedInfoDictionary() or
                    bundle.infoDictionary())
            if info:
                info["CFBundleName"] = app_name
    except ImportError:
        NSBundle = None
        pass
app = QApplication(sys.argv)
app.setApplicationName(app_name)
app.setOrganizationName('marsipu')
if 'darwin' in sys.platform:
    app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
win = guif.MainWindow()
win.show()
win.activateWindow()
# In Pycharm not working but needed for Spyder
# app.lastWindowClosed.connect(app.quit)
app.exec_()

# Variables from the GUI
home_path = win.home_path
project_name = win.project_name
project_path = join(home_path, project_name)
pipeline_path = win.pipeline_path
exec_ops = win.func_dict
make_it_stop = win.make_it_stop
which_file = win.which_file
quality = [win.quality]
modality = [win.modality]
which_mri_subject = win.which_mri_subject
which_erm_file = win.which_erm_file
which_motor_erm_file = win.which_motor_erm_file
pscripts_path = win.pscripts_path
orig_data_path = win.orig_data_path  # location of original-data
subjects_dir = win.subjects_dir  # name of your Freesurfer-Directory
mne.utils.set_config("SUBJECTS_DIR", subjects_dir, set_env=True)
data_path = win.data_path
save_dir_averages = join(data_path, 'grand_averages')

# add file_names, mri_subjects, sub_dict, bad_channels_dict
file_list_path = win.file_list_path
erm_list_path = win.erm_list_path
motor_erm_list_path = win.motor_erm_list_path  # Special for Pinprick
mri_sub_list_path = win.mri_sub_list_path
sub_dict_path = win.sub_dict_path
erm_dict_path = win.erm_dict_path
bad_channels_dict_path = win.bad_channels_dict_path
quality_dict_path = win.quality_dict_path

a = win.pipeline_path
# Needed to prevent exit code -1073741819 (0xC0000005) (probably memory error)
#   after sequential running
del app, win
if make_it_stop:
    raise SystemExit(0)
# %%============================================================================
# LOAD PARAMETERS
# ==============================================================================
if not isfile(join(project_path, f'parameters_{project_name}.py')):
    from templates import parameters_template as p

    shutil.copy2(join(pipeline_path, 'templates/parameters_template.py'),
                 join(project_path, f'parameters_{project_name}.py'))
    print(f'parameters_{project_name}.py created in {project_path} from parameters_template.py')
else:
    spec = util.spec_from_file_location('parameters', join(project_path, f'parameters_{project_name}.py'))
    p = util.module_from_spec(spec)
    sys.modules['parameters'] = p
    spec.loader.exec_module(p)
    print(f'Read Parameters from parameters_{project_name}.py in {project_path}')

if exec_ops['erm_analysis'] or exec_ops['motor_erm_analysis']:
    figures_path = join(project_path, 'Figures/ERM_Figures')
else:
    figures_path = join(project_path, f'Figures/{p.highpass}-{p.lowpass}_Hz')

op.populate_directories(data_path, figures_path, p.event_id)
# %%============================================================================
# SUBJECT ORGANISATION (NOT TO SET)
# ==============================================================================
# if exec_ops['add_files']:  # set 1 to run
#     suborg.add_files(file_list_path, erm_list_path, motor_erm_list_path,
#                      data_path, orig_data_path,
#                      p.unspecified_names, gui=False)
#
# if exec_ops['add_mri_subjects']:  # set 1 to run
#     suborg.add_mri_subjects(subjects_dir, mri_sub_list_path, data_path, gui=False)
#
# if exec_ops['add_sub_dict']:  # set 1 to run
#     suborg.add_sub_dict(sub_dict_path, file_list_path, mri_sub_list_path, data_path)
#
# if exec_ops['add_erm_dict']:  # set 1 to run
#     suborg.add_erm_dict(erm_dict_path, file_list_path, erm_list_path, data_path)
#
# if exec_ops['add_bad_channels']:
#     suborg.add_bad_channels_dict(bad_channels_dict_path, file_list_path,
#                                  erm_list_path, motor_erm_list_path,
#                                  data_path, p.predefined_bads,
#                                  pscripts_path)

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
            op.apply_watershed(mri_subject, subjects_dir, p.overwrite)

        if exec_ops['prepare_bem']:
            op.prepare_bem(mri_subject, subjects_dir)

        if exec_ops['make_dense_scalp_surfaces']:
            op.make_dense_scalp_surfaces(mri_subject, subjects_dir, p.overwrite)

        # ==========================================================================
        # Forward Modeling
        # ==========================================================================
        if exec_ops['setup_src']:
            op.setup_src(mri_subject, subjects_dir, p.source_space_method,
                         p.overwrite, p.n_jobs)
        if exec_ops['compute_src_distances']:
            op.compute_src_distances(mri_subject, subjects_dir,
                                     p.source_space_method, p.n_jobs)

        if exec_ops['setup_vol_src']:
            op.setup_vol_src(mri_subject, subjects_dir)

        if exec_ops['morph_subject']:
            op.morph_subject(mri_subject, subjects_dir, p.morph_to,
                             p.source_space_method, p.overwrite)

        if exec_ops['morph_labels_from_fsaverage']:
            op.morph_labels_from_fsaverage(mri_subject, subjects_dir, p.overwrite)
        # ==========================================================================
        # PLOT SOURCE SPACES
        # ==========================================================================

        if exec_ops['plot_source_space']:
            plot.plot_source_space(mri_subject, subjects_dir, p.source_space_method, p.save_plots, figures_path)

        if exec_ops['plot_bem']:
            plot.plot_bem(mri_subject, subjects_dir, p.source_space_method, figures_path,
                          p.save_plots)

        if exec_ops['plot_labels']:
            plot.plot_labels(mri_subject, p.save_plots, figures_path,
                             p.p.parcellation)

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

quality_dict = ut.read_dict_file('quality', pscripts_path)

basic_pattern = r'(pp[0-9][0-9]*[a-z]*)_([0-9]{0,3}t?)_([a,b]$)'
# Todo: Remove Pinprick-specific parts
# if not exec_ops['erm_analysis'] and not exec_ops['motor_erm_analysis']:
#     silenced_files = set()
#     for file in files:
#         if 'all' not in quality and quality is not '':
#             file_quality = int(quality_dict[file])
#             if file_quality not in quality:
#                 silenced_files.add(file)
#
#         if 'all' not in modality:
#             match = re.match(basic_pattern, file)
#             file_modality = match.group(2)
#             if file_modality not in modality:
#                 silenced_files.add(file)
#
#     for df in silenced_files:
#         files.remove(df)

if len(all_files) == 0:
    print('No files in file_list!')
    print('Add some folders(the ones with the date containing fif-files) to your orig_data_path-folder and check '
          '"add_files"')
else:
    print(f'Selected {len(files)} Subjects:')
    for f in files:
        print(f)

# Get dicts grouping the files together depending on their names to allow grand_averaging:
ab_dict, comp_dict, grand_avg_dict, sub_files_dict, cond_dict = ppf.get_subject_groups(files, p.combine_ab,
                                                                                       p.unspecified_names)
morphed_data_all = dict(LBT=[], offset=[], lower_R=[], same_R=[], higher_R=[])

if exec_ops['plot_ab_combined']:
    files = [f for f in ab_dict]

for name in files:

    # Print Subject Console Header
    print(60 * '=' + '\n' + name)
    prog = round((files.index(name)) / len(files) * 100, 2)
    print(f'Progress: {prog} %')

    if exec_ops['erm_analysis'] or exec_ops['motor_erm_analysis']:
        save_dir = join(project_path, 'Daten/empty_room_data')
        data_path = join(project_path, 'Daten/empty_room_data')
    elif exec_ops['plot_ab_combined']:
        save_dir = join(save_dir_averages, 'ab_combined')
    else:
        save_dir = join(data_path, name)

    if p.print_info:
        info = io.read_info(name, save_dir)
        print(info)

    # Use Regular Expressions to make ermsub and subtomri assignement easier
    if not p.unspecified_names:
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
                                             data_path, p.predefined_bads,
                                             pscripts_path)
    else:
        try:
            ermsub = erm_dict[name]
        except KeyError as k:
            print(f'No erm_measurement for {k}')
            raise RuntimeError('Run again and run add_erm_dict')
        try:
            subtomri = sub_dict[name]
        except KeyError as k:
            print(f'No mri_subject assigned to {k}')
            raise RuntimeError('Run again and run add_mri_dict')
        try:
            bad_channels = bad_channels_dict[name]
        except KeyError as k:
            print(f'No bad channels for {k}')
            raise RuntimeError('Run again and run add_bad_channels_dict')

    # ==========================================================================
    # FILTER RAW
    # ==========================================================================

    if exec_ops['filter_raw']:
        op.filter_raw(name, save_dir, p.highpass, p.lowpass, ermsub,
                      data_path, p.n_jobs, p.enable_cuda, bad_channels, p.erm_t_limit,
                      p.enable_ica, p.eog_digitized)

    # ==========================================================================
    # FIND EVENTS
    # ==========================================================================

    if exec_ops['find_events']:
        op.find_events(name, save_dir, p.adjust_timeline_by_msec, p.overwrite, exec_ops)

    if exec_ops['pp_event_handling']:
        ppf.pp_event_handling(name, save_dir, p.adjust_timeline_by_msec, p.overwrite,
                              pscripts_path, p.save_plots, figures_path, exec_ops)

    if exec_ops['melofix_event_handling']:
        mff.melofix_event_handling(name, save_dir, p.adjust_timeline_by_msec, p.overwrite,
                                   pscripts_path, p.save_plots, figures_path, exec_ops)

    if exec_ops['kristin_event_handling']:
        kf.kristin_event_handling(name, save_dir, p.adjust_timeline_by_msec, p.overwrite,
                                  pscripts_path, p.save_plots, figures_path, exec_ops)

    if exec_ops['find_eog_events']:
        op.find_eog_events(name, save_dir, p.eog_channel)

    # ==========================================================================
    # EPOCHS
    # ==========================================================================

    if exec_ops['epoch_raw']:
        op.epoch_raw(name, save_dir, p.highpass, p.lowpass, p.event_id, p.etmin, p.etmax,
                     p.baseline, p.reject, p.flat, p.autoreject, p.overwrite_ar,
                     pscripts_path, bad_channels, p.decim,
                     p.reject_eog_epochs, p.overwrite, exec_ops)

    # ==========================================================================
    # SIGNAL SPACE PROJECTION
    # ==========================================================================
    if exec_ops['run_ssp_er']:
        op.run_ssp_er(name, save_dir, p.highpass, p.lowpass, data_path, ermsub, bad_channels,
                      p.overwrite)

    if exec_ops['apply_ssp_er']:
        op.apply_ssp_er(name, save_dir, p.highpass, p.lowpass, p.overwrite)

    if exec_ops['run_ssp_clm']:
        op.run_ssp_clm(name, save_dir, p.highpass, p.lowpass, bad_channels, p.overwrite)

    if exec_ops['apply_ssp_clm']:
        op.apply_ssp_clm(name, save_dir, p.highpass, p.lowpass, p.overwrite)

    if exec_ops['run_ssp_eog']:
        op.run_ssp_eog(name, save_dir, p.n_jobs, p.eog_channel,
                       bad_channels, p.overwrite)

    if exec_ops['apply_ssp_eog']:
        op.apply_ssp_eog(name, save_dir, p.highpass, p.lowpass, p.overwrite)

    if exec_ops['run_ssp_ecg']:
        op.run_ssp_ecg(name, save_dir, p.n_jobs, p.ecg_channel,
                       bad_channels, p.overwrite)

    if exec_ops['apply_ssp_ecg']:
        op.apply_ssp_ecg(name, save_dir, p.highpass, p.lowpass, p.overwrite)

    if exec_ops['plot_ssp']:
        plot.plot_ssp(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                      figures_path, ermsub)

    if exec_ops['plot_ssp_eog']:
        plot.plot_ssp_eog(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                          figures_path)

    if exec_ops['plot_ssp_ecg']:
        plot.plot_ssp_ecg(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                          figures_path)

    if exec_ops['run_ica']:
        op.run_ica(name, save_dir, p.highpass, p.lowpass, p.eog_channel, p.ecg_channel,
                   p.reject, p.flat, bad_channels, p.overwrite, p.autoreject,
                   p.save_plots, figures_path, pscripts_path,
                   exec_ops['erm_analysis'])

    # ==========================================================================
    # LOAD NON-ICA'ED EPOCHS AND APPLY ICA
    # ==========================================================================

    if exec_ops['apply_ica']:
        op.apply_ica(name, save_dir, p.highpass, p.lowpass, p.overwrite)

    # ==========================================================================
    # EVOKEDS
    # ==========================================================================

    if exec_ops['get_evokeds']:
        op.get_evokeds(name, save_dir, p.highpass, p.lowpass, exec_ops, ermsub,
                       p.detrend, p.enable_ica, p.overwrite)

    if exec_ops['get_h1h2_evokeds']:
        op.get_h1h2_evokeds(name, save_dir, p.highpass, p.lowpass, p.enable_ica,
                            exec_ops, ermsub, p.detrend)

    # ==========================================================================
    # TIME-FREQUENCY-ANALASYS
    # ==========================================================================

    if exec_ops['tfr']:
        op.tfr(name, save_dir, p.highpass, p.lowpass, p.enable_ica, p.tfr_freqs, p.overwrite_tfr,
               p.tfr_method, p.multitaper_bandwith, p.stockwell_width, p.n_jobs)

    # ==========================================================================
    # NOISE COVARIANCE MATRIX
    # ==========================================================================

    if exec_ops['estimate_noise_covariance']:
        op.estimate_noise_covariance(name, save_dir, p.highpass, p.lowpass, p.overwrite,
                                     ermsub, data_path, p.baseline, bad_channels,
                                     p.n_jobs, p.erm_noise_cov, p.calm_noise_cov,
                                     p.enable_ica, p.erm_ica)

    if exec_ops['plot_noise_covariance']:
        plot.plot_noise_covariance(name, save_dir, p.highpass, p.lowpass,
                                   p.save_plots, figures_path, p.erm_noise_cov, ermsub,
                                   p.calm_noise_cov)

    # ==========================================================================
    # CO-REGISTRATION
    # ==========================================================================

    # use mne.gui.coregistration()

    if exec_ops['mri_coreg']:
        op.mri_coreg(name, save_dir, subtomri, subjects_dir)

    if exec_ops['plot_transformation']:
        plot.plot_transformation(name, save_dir, subtomri, subjects_dir,
                                 p.save_plots, figures_path)

    if exec_ops['plot_sensitivity_maps']:
        plot.plot_sensitivity_maps(name, save_dir, subjects_dir, p.ch_types,
                                   p.save_plots, figures_path)

    # ==========================================================================
    # CREATE FORWARD MODEL
    # ==========================================================================

    if exec_ops['create_forward_solution']:
        op.create_forward_solution(name, save_dir, subtomri, subjects_dir,
                                   p.source_space_method, p.overwrite,
                                   p.n_jobs, p.eeg_fwd)

    # ==========================================================================
    # CREATE INVERSE OPERATOR
    # ==========================================================================

    if exec_ops['create_inverse_operator']:
        op.create_inverse_operator(name, save_dir, p.highpass, p.lowpass,
                                   p.overwrite, ermsub, p.calm_noise_cov,
                                   p.erm_noise_cov)

    # ==========================================================================
    # SOURCE ESTIMATE MNE
    # ==========================================================================

    if exec_ops['source_estimate']:
        op.source_estimate(name, save_dir, p.highpass, p.lowpass, p.inverse_method, p.toi,
                           p.overwrite)

    if exec_ops['vector_source_estimate']:
        op.vector_source_estimate(name, save_dir, p.highpass, p.lowpass,
                                  p.inverse_method, p.toi, p.overwrite)

    if exec_ops['mixed_norm_estimate']:
        op.mixed_norm_estimate(name, save_dir, p.highpass, p.lowpass, p.toi, p.inverse_method, p.erm_noise_cov,
                               ermsub, p.calm_noise_cov, p.event_id, p.mixn_dip, p.overwrite)

    if exec_ops['ecd_fit']:
        op.ecd_fit(name, save_dir, p.highpass, p.lowpass, ermsub, subjects_dir,
                   subtomri, p.erm_noise_cov, p.calm_noise_cov, p.ecds,
                   p.save_plots, figures_path)

    if exec_ops['apply_morph']:
        stcs = op.apply_morph(name, save_dir, p.highpass, p.lowpass,
                              subjects_dir, subtomri, p.inverse_method,
                              p.overwrite, p.morph_to,
                              p.source_space_method, p.event_id)

    if exec_ops['apply_morph_normal']:
        stcs = op.apply_morph_normal(name, save_dir, p.highpass, p.lowpass,
                                     subjects_dir, subtomri, p.inverse_method,
                                     p.overwrite, p.morph_to,
                                     p.source_space_method, p.event_id)

    if not p.combine_ab:
        if exec_ops['create_func_label']:
            op.create_func_label(name, save_dir, p.highpass, p.lowpass,
                                 p.inverse_method, p.event_id, subtomri, subjects_dir,
                                 p.source_space_method, p.label_origin,
                                 p.parcellation_orig, p.ev_ids_label_analysis,
                                 p.save_plots, figures_path, pscripts_path,
                                 p.n_std, p.combine_ab)

    if not p.combine_ab:
        if exec_ops['func_label_processing']:
            op.func_label_processing(name, save_dir, p.highpass, p.lowpass,
                                     p.save_plots, figures_path, subtomri, subjects_dir,
                                     pscripts_path, p.ev_ids_label_analysis,
                                     p.corr_threshold, p.combine_ab)

    if exec_ops['func_label_ctf_ps']:
        op.func_label_ctf_ps(name, save_dir, p.highpass, p.lowpass, subtomri,
                             subjects_dir, p.parcellation_orig)
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
        plot.plot_filtered(name, save_dir, p.highpass, p.lowpass, bad_channels)

    if exec_ops['plot_events']:
        plot.plot_events(name, save_dir, p.save_plots, figures_path, p.event_id)

    if exec_ops['plot_events_diff']:
        plot.plot_events_diff(name, save_dir, p.save_plots, figures_path)

    if exec_ops['plot_eog_events']:
        plot.plot_eog_events(name, save_dir)

    # ==========================================================================
    # PLOT POWER SPECTRA
    # ==========================================================================

    if exec_ops['plot_power_spectra']:
        plot.plot_power_spectra(name, save_dir, p.highpass, p.lowpass,
                                p.save_plots, figures_path, bad_channels)

    if exec_ops['plot_power_spectra_epochs']:
        plot.plot_power_spectra_epochs(name, save_dir, p.highpass, p.lowpass,
                                       p.save_plots, figures_path)

    if exec_ops['plot_power_spectra_topo']:
        plot.plot_power_spectra_topo(name, save_dir, p.highpass, p.lowpass,
                                     p.save_plots, figures_path)

    # ==========================================================================
    # PLOT TIME-FREQUENCY-ANALASYS
    # ==========================================================================

    if exec_ops['plot_tfr']:
        plot.plot_tfr(name, save_dir, p.highpass, p.lowpass, p.etmin, p.etmax, p.baseline,
                      p.tfr_method, p.save_plots, figures_path)

    if exec_ops['tfr_event_dynamics']:
        plot.tfr_event_dynamics(name, save_dir, p.etmin, p.etmax, p.save_plots,
                                figures_path, bad_channels, p.n_jobs)

    # ==========================================================================
    # PLOT CLEANED EPOCHS
    # ==========================================================================
    if exec_ops['plot_epochs']:
        plot.plot_epochs(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                         figures_path)

    if exec_ops['plot_epochs_image']:
        plot.plot_epochs_image(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                               figures_path)

    if exec_ops['plot_epochs_topo']:
        plot.plot_epochs_topo(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                              figures_path)

    if exec_ops['plot_epochs_drop_log']:
        plot.plot_epochs_drop_log(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                                  figures_path)
    # ==========================================================================
    # PLOT EVOKEDS
    # ==========================================================================

    if exec_ops['plot_evoked_topo']:
        plot.plot_evoked_topo(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                              figures_path)

    if exec_ops['plot_evoked_topomap']:
        plot.plot_evoked_topomap(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                                 figures_path)

    if exec_ops['plot_evoked_butterfly']:
        plot.plot_evoked_butterfly(name, save_dir, p.highpass, p.lowpass,
                                   p.save_plots, figures_path)

    if exec_ops['plot_evoked_field']:
        plot.plot_evoked_field(name, save_dir, p.highpass, p.lowpass, subtomri,
                               subjects_dir, p.save_plots, figures_path,
                               p.mne_evoked_time, p.n_jobs)

    if exec_ops['plot_evoked_joint']:
        plot.plot_evoked_joint(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                               figures_path, quality_dict)

    if exec_ops['plot_evoked_white']:
        plot.plot_evoked_white(name, save_dir, p.highpass, p.lowpass,
                               p.save_plots, figures_path, p.erm_noise_cov, ermsub, p.calm_noise_cov)

    if exec_ops['plot_evoked_image']:
        plot.plot_evoked_image(name, save_dir, p.highpass, p.lowpass,
                               p.save_plots, figures_path)

    if exec_ops['plot_evoked_h1h2']:
        plot.plot_evoked_h1h2(name, save_dir, p.highpass, p.lowpass, p.event_id,
                              p.save_plots, figures_path)

    if exec_ops['plot_gfp']:
        plot.plot_gfp(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                      figures_path)
    # ==========================================================================
    # PLOT SOURCE ESTIMATES MNE
    # ==========================================================================

    if exec_ops['plot_stc']:
        plot.plot_stc(name, save_dir, p.highpass, p.lowpass,
                      subtomri, subjects_dir,
                      p.inverse_method, p.mne_evoked_time, p.event_id,
                      p.stc_interactive, p.save_plots, figures_path)

    if exec_ops['plot_normal_stc']:
        plot.plot_normal_stc(name, save_dir, p.highpass, p.lowpass,
                             subtomri, subjects_dir,
                             p.inverse_method, p.mne_evoked_time, p.event_id,
                             p.stc_interactive, p.save_plots, figures_path)

    if exec_ops['plot_vector_stc']:
        plot.plot_vector_stc(name, save_dir, p.highpass, p.lowpass, subtomri, subjects_dir,
                             p.inverse_method, p.mne_evoked_time, p.event_id, p.stc_interactive,
                             p.save_plots, figures_path)

    if exec_ops['plot_mixn']:
        plot.plot_mixn(name, save_dir, p.highpass, p.lowpass, subtomri, subjects_dir,
                       p.mne_evoked_time, p.event_id, p.stc_interactive,
                       p.save_plots, figures_path, p.mixn_dip, p.parcellation)

    if exec_ops['plot_animated_stc']:
        plot.plot_animated_stc(name, save_dir, p.highpass, p.lowpass, subtomri,
                               subjects_dir, p.inverse_method, p.stc_animation, p.event_id,
                               figures_path, p.ev_ids_label_analysis)

    if exec_ops['plot_snr']:
        plot.plot_snr(name, save_dir, p.highpass, p.lowpass, p.save_plots, figures_path,
                      p.inverse_method, p.event_id)

    if exec_ops['plot_label_time_course']:
        plot.plot_label_time_course(name, save_dir, p.highpass, p.lowpass,
                                    subtomri, subjects_dir, p.inverse_method, p.source_space_method,
                                    p.target_labels, p.save_plots, figures_path,
                                    p.parcellation, p.event_id, p.ev_ids_label_analysis)

    # ==========================================================================
    # TIME-FREQUENCY IN SOURCE SPACE
    # ==========================================================================

    if exec_ops['label_power_phlck']:
        op.label_power_phlck(name, save_dir, p.highpass, p.lowpass, p.baseline, p.tfr_freqs,
                             subtomri, p.target_labels, p.parcellation,
                             p.ev_ids_label_analysis, p.n_jobs,
                             save_dir, figures_path)

    if exec_ops['plot_label_power_phlck']:
        plot.plot_label_power_phlck(name, save_dir, p.highpass, p.lowpass, subtomri, p.parcellation,
                                    p.baseline, p.tfr_freqs, p.save_plots, figures_path, p.n_jobs,
                                    p.target_labels, p.ev_ids_label_analysis)

    if exec_ops['source_space_connectivity']:
        op.source_space_connectivity(name, save_dir, p.highpass, p.lowpass,
                                     subtomri, subjects_dir, p.parcellation,
                                     p.target_labels, p.con_methods,
                                     p.con_fmin, p.con_fmax,
                                     p.n_jobs, p.overwrite, p.enable_ica,
                                     p.ev_ids_label_analysis)

    if exec_ops['plot_source_space_connectivity']:
        plot.plot_source_space_connectivity(name, save_dir, p.highpass, p.lowpass,
                                            subtomri, subjects_dir, p.parcellation,
                                            p.target_labels, p.con_methods, p.con_fmin,
                                            p.con_fmax, p.save_plots,
                                            figures_path, p.ev_ids_label_analysis)

    # ==========================================================================
    # General Statistics
    # ==========================================================================
    if exec_ops['corr_ntr']:
        op.corr_ntr(name, save_dir, p.highpass, p.lowpass, exec_ops,
                    ermsub, subtomri, p.enable_ica, p.save_plots, figures_path)

    # close all plots
    if exec_ops['close_plots']:
        plot.close_all()

# GOING OUT OF SUBJECT LOOP
# %%============================================================================
# All-Subject-Analysis
# ==============================================================================
if exec_ops['pp_alignment']:
    ppf.pp_alignment(ab_dict, cond_dict, sub_dict, data_path, p.highpass, p.lowpass, pscripts_path,
                     p.event_id, subjects_dir, p.inverse_method, p.source_space_method,
                     p.parcellation, figures_path)

if exec_ops['cmp_label_time_course']:
    plot.cmp_label_time_course(data_path, p.highpass, p.lowpass, sub_dict, comp_dict,
                               subjects_dir, p.inverse_method, p.source_space_method, p.parcellation,
                               p.target_labels, p.save_plots, figures_path,
                               p.event_id, p.ev_ids_label_analysis, p.combine_ab,
                               pscripts_path, exec_ops)

if p.combine_ab:
    if exec_ops['create_func_label']:
        for key in ab_dict:
            print(60 * '=' + '\n' + key)
            if len(ab_dict[key]) > 1:
                name = (ab_dict[key][0], ab_dict[key][1])
                save_dir = (join(data_path, name[0]), join(data_path, name[1]))
                pattern = r'pp[0-9]+[a-z]?'
                if p.unspecified_names:
                    pattern = r'.*'
                match = re.match(pattern, name[0])
                prefix = match.group()
                subtomri = sub_dict[prefix]
            else:
                name = ab_dict[key][0]
                save_dir = join(data_path, name)
                pattern = r'pp[0-9]+[a-z]?'
                if p.unspecified_names:
                    pattern = r'.*'
                match = re.match(pattern, name)
                prefix = match.group()
                subtomri = sub_dict[prefix]
            op.create_func_label(name, save_dir, p.highpass, p.lowpass,
                                 p.inverse_method, p.event_id, subtomri, subjects_dir,
                                 p.source_space_method, p.label_origin,
                                 p.parcellation_orig, p.ev_ids_label_analysis,
                                 p.save_plots, figures_path, pscripts_path,
                                 p.n_std, p.combine_ab)

if p.combine_ab:
    if exec_ops['func_label_processing']:
        for key in ab_dict:
            print(60 * '=' + '\n' + key)
            if len(ab_dict[key]) > 1:
                name = (ab_dict[key][0], ab_dict[key][1])
                save_dir = (join(data_path, name[0]), join(data_path, name[1]))
                pattern = r'pp[0-9]+[a-z]?'
                if p.unspecified_names:
                    pattern = r'.*'
                match = re.match(pattern, name[0])
                prefix = match.group()
                subtomri = sub_dict[prefix]
            else:
                name = ab_dict[key][0]
                save_dir = join(data_path, name)
                pattern = r'pp[0-9]+[a-z]?'
                if p.unspecified_names:
                    pattern = r'.*'
                match = re.match(pattern, name)
                prefix = match.group()
                subtomri = sub_dict[prefix]
            op.func_label_processing(name, save_dir, p.highpass, p.lowpass,
                                     p.save_plots, figures_path, subtomri, subjects_dir,
                                     pscripts_path, p.ev_ids_label_analysis,
                                     p.corr_threshold, p.combine_ab)

if exec_ops['sub_func_label_analysis']:
    plot.sub_func_label_analysis(p.lowpass, p.highpass, p.etmax, sub_files_dict,
                                 pscripts_path, p.label_origin, p.ev_ids_label_analysis, p.save_plots,
                                 figures_path, exec_ops)

if exec_ops['all_func_label_analysis']:
    plot.all_func_label_analysis(p.lowpass, p.highpass, p.etmax, files, pscripts_path,
                                 p.label_origin, p.ev_ids_label_analysis, p.save_plots,
                                 figures_path)

# %%============================================================================
# GRAND AVERAGES (sensor space and source space)
# ==============================================================================

if exec_ops['grand_avg_evokeds']:
    op.grand_avg_evokeds(data_path, grand_avg_dict, save_dir_averages,
                         p.highpass, p.lowpass, exec_ops, quality,
                         p.ana_h1h2)

if exec_ops['pp_combine_evokeds_ab']:
    ppf.pp_combine_evokeds_ab(data_path, save_dir_averages, p.highpass, p.lowpass, ab_dict)

if exec_ops['grand_avg_tfr']:
    op.grand_avg_tfr(data_path, grand_avg_dict, save_dir_averages,
                     p.highpass, p.lowpass, p.tfr_method)

if exec_ops['grand_avg_morphed']:
    op.grand_avg_morphed(grand_avg_dict, data_path, p.inverse_method, save_dir_averages,
                         p.highpass, p.lowpass, p.event_id)

if exec_ops['grand_avg_normal_morphed']:
    op.grand_avg_normal_morphed(grand_avg_dict, data_path, p.inverse_method, save_dir_averages,
                                p.highpass, p.lowpass, p.event_id)

if exec_ops['grand_avg_connect']:
    op.grand_avg_connect(grand_avg_dict, data_path, p.con_methods,
                         p.con_fmin, p.con_fmax, save_dir_averages,
                         p.lowpass, p.highpass)

if exec_ops['grand_avg_label_power']:
    op.grand_avg_label_power(grand_avg_dict, p.ev_ids_label_analysis,
                             data_path, p.highpass, p.lowpass,
                             p.target_labels, save_dir_averages)

if exec_ops['grand_avg_func_labels']:
    op.grand_avg_func_labels(grand_avg_dict, p.highpass, p.lowpass,
                             save_dir_averages, p.event_id, p.ev_ids_label_analysis,
                             subjects_dir, p.source_space_method,
                             p.parcellation_orig, pscripts_path, p.save_plots,
                             p.label_origin, figures_path, p.n_std)

# %%============================================================================
# GRAND AVERAGES PLOTS (sensor space and source space)
# ================================================================================

if exec_ops['plot_grand_avg_evokeds']:
    plot.plot_grand_avg_evokeds(p.lowpass, p.highpass, save_dir_averages, grand_avg_dict,
                                p.event_id, p.save_plots, figures_path, quality)

if exec_ops['plot_grand_avg_evokeds_h1h2']:
    plot.plot_grand_avg_evokeds_h1h2(p.lowpass, p.highpass, save_dir_averages, grand_avg_dict,
                                     p.event_id, p.save_plots, figures_path, quality)

if exec_ops['plot_evoked_compare']:
    plot.plot_evoked_compare(data_path, save_dir_averages, p.highpass, p.lowpass, comp_dict, p.combine_ab, p.event_id)

if exec_ops['plot_grand_avg_tfr']:
    plot.plot_grand_avg_tfr(p.lowpass, p.highpass, p.baseline, p.etmin, p.etmax,
                            save_dir_averages, grand_avg_dict,
                            p.event_id, p.save_plots, figures_path)

if exec_ops['plot_grand_avg_stc']:
    plot.plot_grand_avg_stc(p.lowpass, p.highpass, save_dir_averages,
                            grand_avg_dict, p.mne_evoked_time, p.morph_to,
                            subjects_dir, p.event_id, p.save_plots,
                            figures_path)

if exec_ops['plot_grand_avg_stc_anim']:
    plot.plot_grand_avg_stc_anim(p.lowpass, p.highpass, save_dir_averages,
                                 grand_avg_dict, p.stc_animation, p.morph_to,
                                 subjects_dir, p.event_id, figures_path)

if exec_ops['plot_grand_avg_connect']:
    plot.plot_grand_avg_connect(p.lowpass, p.highpass, save_dir_averages,
                                grand_avg_dict, subjects_dir, p.morph_to, p.parcellation, p.con_methods, p.con_fmin,
                                p.con_fmax,
                                p.save_plots, figures_path, p.ev_ids_label_analysis, p.target_labels)

if exec_ops['plot_grand_avg_label_power']:
    plot.plot_grand_avg_label_power(grand_avg_dict, p.ev_ids_label_analysis, p.target_labels,
                                    save_dir_averages, p.tfr_freqs, p.etmin, p.etmax, p.lowpass,
                                    p.highpass, p.save_plots, figures_path)

# ==============================================================================
# STATISTICS SOURCE SPACE
# ==============================================================================

if exec_ops['statistics_source_space']:
    op.statistics_source_space(morphed_data_all, save_dir_averages,
                               p.independent_variable_1,
                               p.independent_variable_2,
                               p.time_window, p.n_permutations, p.highpass, p.lowpass,
                               p.overwrite)

# ==============================================================================
# PLOT GRAND AVERAGES OF SOURCE ESTIMATES WITH STATISTICS CLUSTER MASK
# ==============================================================================

if exec_ops['plot_grand_averages_source_estimates_cluster_masked']:
    plot.plot_grand_averages_source_estimates_cluster_masked(
        save_dir_averages, p.highpass, p.lowpass, subjects_dir, p.inverse_method, p.time_window,
        p.save_plots, figures_path, p.independent_variable_1,
        p.independent_variable_2, p.mne_evoked_time, p.p_threshold)
# ==============================================================================
# MISCELLANEOUS
# ==============================================================================

if exec_ops['pp_plot_latency_S1_corr']:
    plot.pp_plot_latency_s1_corr(data_path, files, p.highpass, p.lowpass,
                                 p.save_plots, figures_path)

# close all plots
if exec_ops['close_plots']:
    plot.close_all()

if exec_ops['shutdown']:
    ut.shutdown()
