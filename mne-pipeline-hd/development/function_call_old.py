import os
import re
import shutil
import sys
from importlib import util
from os.path import isfile, join

import pandas as pd

from basic_functions import loading, operations, plot
from custom_functions import kristin, melofix, pinprick
from pipeline_functions import pipeline_utils as ut
from gui import subject_widgets as subs
from gui.subject_widgets import CurrentMRISubject
from development import operations_dict as opd


# TODO: Ideas for improved function calling:
#   1. Put Main-Window as only arg in all functions and get variables from attributes
#   2. Make all Arguments as keyword-arguments and use module-attributes for calling


def func_from_def(func_name, pd_funcs, subject, project, parameters):
    module_name = pd_funcs[func_name]['module']

    # Read Listitems from Strings from functions.csv
    subarg_string = pd_funcs[func_name]['subject_arguments']
    subarg_names = subarg_string.split(',')
    proarg_string = pd_funcs[func_name]['project_arguments']
    proarg_names = proarg_string.split(',')
    addarg_string = pd_funcs[func_name]['arguments']
    addarg_names = addarg_string.split(',')

    # Get attributes from Subject/Project-Class
    subject_attributes = vars(subject)
    project_attributes = vars(project)

    keyword_arguments = dict()

    for subarg_name in subarg_names:
        # Remove trailing spaces
        subarg_name = subarg_name.replace(' ', '')
        keyword_arguments.update({subarg_name: subject_attributes[subarg_name]})
    for proarg_name in proarg_names:
        # Remove trailing spaces
        proarg_name = proarg_name.replace(' ', '')
        keyword_arguments.update({proarg_name: project_attributes[proarg_name]})
    for addarg_name in addarg_names:
        # Remove trailing spaces
        addarg_name = addarg_name.replace(' ', '')
        keyword_arguments.update({addarg_name: parameters[addarg_name]})

    # Get module, has to specified in functions.csv as it is imported
    module = globals()[module_name]
    # Call Function from specified module with arguments from unpacked list/dictionary
    return_value = getattr(module, func_name)(**keyword_arguments)

    return return_value


def call_functions(main_window, project):
    """
    Call activated functions in main_window, read function-parameters from functions_empty.csv
    :param main_window:
    :param project:
    :return:
    """
    mw = main_window
    pr = project

    # Read functions from csv (Transform -> in Excel better readable with functions as rows but shorter code in python
    #   for iterating over functions as columns, separator ";" for editing with Excel)
    pd_funcs = pd.read_csv(join(os.getcwd(), 'mne-pipeline-hd/resources/functions.csv'), sep=';', index_col=0).T

    # Todo: Serialize parameters-dict with json
    # Todo: Problem: Noch sind figures_path und mw.func_dict mit in subject-attributes dabei, die müssen irgendwie raus
    #   (vielleicht doch keine Plots nach Filtern getrennt (nach Filtern in Ordnern trennen (optional)))
    #
    # Read parameters
    if not isfile(join(pr.project_path, f'parameters_{pr.project_name}.py')):

        shutil.copy2(join(os.getcwd(), 'resources/parameters_template.py'),
                     join(pr.project_path, f'parameters_{pr.project_name}.py'))
        print(f'parameters_{pr.project_name}.py created in {pr.project_path}'
              f' from parameters_template.py')
    else:
        spec = util.spec_from_file_location('parameters', join(pr.project_path,
                                                               f'parameters_{pr.project_name}.py'))
        p = util.module_from_spec(spec)
        sys.modules['parameters'] = p
        spec.loader.exec_module(p)
        print(f'Read Parameters from parameters_{pr.project_name}.py in {pr.project_path}')

    figures_path = join(pr.project_path, f'figures/{p.highpass}-{p.lowpass}_Hz')

    operations.populate_directories(pr.data_path, figures_path, p.event_id)

    # Update the lists for changes made in Subject-GUIs
    pr.load_sub_lists()

    # Find out, if a mri-subject-function is activated
    run_mrisf = False
    for msop in opd.mri_subject_operations:
        if mw.func_dict[msop]:
            run_mrisf = True
    if run_mrisf:
        mri_subjects = pr.sel_mri_files

        print(f'Selected {len(mri_subjects)} MRI-Subjects:')
        for i in mri_subjects:
            print(i)

        for mri_subject in mri_subjects:
            print('=' * 60 + '\n', mri_subject)
            prog = round((mri_subjects.index(mri_subject)) / len(mri_subjects) * 100, 2)
            print(f'Progress: {prog} %')

            msub = CurrentMRISubject(mri_subject, mw)
            for mri_func in opd.mri_subject_operations:
                if mw.func_dict[mri_func]:
                    func_from_def(mri_func, pd_funcs)
            # ==========================================================================
            # BASH SCRIPTS
            # ==========================================================================
            if mw.func_dict['apply_watershed']:
                operations.apply_watershed(mri_subject, pr.subjects_dir, p.overwrite)

            if mw.func_dict['prepare_bem']:
                operations.prepare_bem(mri_subject, pr.subjects_dir)

            if mw.func_dict['make_dense_scalp_surfaces']:
                operations.make_dense_scalp_surfaces(mri_subject, pr.subjects_dir, p.overwrite)

            # ==========================================================================
            # Forward Modeling
            # ==========================================================================
            if mw.func_dict['setup_src']:
                operations.setup_src(mri_subject, pr.subjects_dir, p.source_space_method,
                                     p.overwrite, p.n_jobs)
            if mw.func_dict['compute_src_distances']:
                operations.compute_src_distances(mri_subject, pr.subjects_dir,
                                                 p.source_space_method, p.n_jobs)

            if mw.func_dict['setup_vol_src']:
                operations.setup_vol_src(mri_subject, pr.subjects_dir)

            if mw.func_dict['morph_subject']:
                operations.morph_subject(mri_subject, pr.subjects_dir, p.morph_to,
                                         p.source_space_method, p.overwrite)

            if mw.func_dict['morph_labels_from_fsaverage']:
                operations.morph_labels_from_fsaverage(mri_subject, pr.subjects_dir, p.overwrite)
            # ==========================================================================
            # PLOT SOURCE SPACES
            # ==========================================================================

            if mw.func_dict['plot_source_space']:
                plot.plot_source_space(mri_subject, pr.subjects_dir, p.source_space_method, p.save_plots, figures_path)

            if mw.func_dict['plot_bem']:
                plot.plot_bem(mri_subject, pr.subjects_dir, p.source_space_method, pr.figures_path,
                              p.save_plots)

            if mw.func_dict['plot_labels']:
                plot.plot_labels(mri_subject, p.save_plots, pr.figures_path,
                                 p.p.parcellation)

            # close plots
            if mw.func_dict['close_plots']:
                plot.close_all()
    # %%========================================================================
    # Files (NOT TO SET)
    # ===========================================================================
    sel_files = pr.sel_files

    quality_dict = ut.read_dict_file('quality', mw.pr.pscripts_path)

    if len(pr.all_files) == 0:
        print('No sel_files in file_list!')
        print('Add some Files with "AddFiles" from the Input-Menu')
    else:
        print(f'Selected {len(sel_files)} Subjects:')
        for f in sel_files:
            print(f)

    # Get dicts grouping the sel_files together depending on their names to allow grand_averaging:
    ab_dict, comp_dict, grand_avg_dict, sub_files_dict, cond_dict = pinprick.pp_get_subject_groups(sel_files, p.combine_ab,
                                                                                                   p.unspecified_names)
    morphed_data_all = dict(LBT=[], offset=[], lower_R=[], same_R=[], higher_R=[])

    if mw.func_dict['plot_ab_combined']:
        sel_files = [f for f in ab_dict]

    for name in sel_files:

        # Print Subject Console Header
        print(60 * '=' + '\n' + name)
        prog = round((sel_files.index(name)) / len(sel_files) * 100, 2)
        print(f'Progress: {prog} %')

        save_dir = join(pr.data_path, name)

        if p.print_info:
            info = loading.read_info(name, save_dir)
            print(info)
        # Todo: Somehow include check in Subject and manage pause execution (threading)
        try:
            ermsub = pr.erm_dict[name]
        except KeyError as k:
            print(f'No erm_measurement assigned for {k}')
            subs.SubDictDialog(mw, 'erm')
            break
        try:
            subtomri = pr.sub_dict[name]
        except KeyError as k:
            print(f'No mri_subject assigned to {k}')
            subs.SubDictDialog(mw, 'mri')
            break
        try:
            bad_channels = pr.bad_channels_dict[name]
        except KeyError as k:
            print(f'No bad channels for {k}')
            subs.SubBadsDialog(mw)
            break

        # ==========================================================================
        # FILTER RAW
        # ==========================================================================

        if mw.func_dict['filter_raw']:
            operations.filter_raw(name, save_dir, p.highpass, p.lowpass, ermsub,
                                  pr.data_path, p.n_jobs, p.enable_cuda, bad_channels, p.erm_t_limit,
                                  p.enable_ica, p.eog_digitized)

        # ==========================================================================
        # FIND EVENTS
        # ==========================================================================

        if mw.func_dict['find_events']:
            operations.find_events(name, save_dir, p.adjust_timeline_by_msec, p.overwrite, mw.func_dict)

        if mw.func_dict['pp_event_handling']:
            pinprick.pp_event_handling(name, save_dir, p.adjust_timeline_by_msec, p.overwrite,
                                       pr.pscripts_path, p.save_plots, figures_path, mw.func_dict)

        if mw.func_dict['melofix_event_handling']:
            melofix.melofix_event_handling(name, save_dir, p.adjust_timeline_by_msec, p.overwrite,
                                           pr.pscripts_path, p.save_plots, figures_path, mw.func_dict)

        if mw.func_dict['kristin_event_handling']:
            kristin.kristin_event_handling(name, save_dir, p.adjust_timeline_by_msec, p.overwrite,
                                           pr.pscripts_path, p.save_plots, figures_path, mw.func_dict)

        if mw.func_dict['find_eog_events']:
            operations.find_eog_events(name, save_dir, p.eog_channel)

        # ==========================================================================
        # EPOCHS
        # ==========================================================================

        if mw.func_dict['epoch_raw']:
            operations.epoch_raw(name, save_dir, p.highpass, p.lowpass, p.event_id, p.etmin, p.etmax,
                                 p.baseline, p.reject, p.flat, p.autoreject, p.overwrite_ar,
                                 pr.pscripts_path, bad_channels, p.decim,
                                 p.reject_eog_epochs, p.overwrite, mw.func_dict)

        # ==========================================================================
        # SIGNAL SPACE PROJECTION
        # ==========================================================================
        if mw.func_dict['run_ssp_er']:
            operations.run_ssp_er(name, save_dir, p.highpass, p.lowpass, pr.data_path, ermsub, bad_channels,
                                  p.overwrite)

        if mw.func_dict['apply_ssp_er']:
            operations.apply_ssp_er(name, save_dir, p.highpass, p.lowpass, p.overwrite)

        if mw.func_dict['run_ssp_clm']:
            operations.run_ssp_clm(name, save_dir, p.highpass, p.lowpass, bad_channels, p.overwrite)

        if mw.func_dict['apply_ssp_clm']:
            operations.apply_ssp_clm(name, save_dir, p.highpass, p.lowpass, p.overwrite)

        if mw.func_dict['run_ssp_eog']:
            operations.run_ssp_eog(name, save_dir, p.n_jobs, p.eog_channel,
                                   bad_channels, p.overwrite)

        if mw.func_dict['apply_ssp_eog']:
            operations.apply_ssp_eog(name, save_dir, p.highpass, p.lowpass, p.overwrite)

        if mw.func_dict['run_ssp_ecg']:
            operations.run_ssp_ecg(name, save_dir, p.n_jobs, p.ecg_channel,
                                   bad_channels, p.overwrite)

        if mw.func_dict['apply_ssp_ecg']:
            operations.apply_ssp_ecg(name, save_dir, p.highpass, p.lowpass, p.overwrite)

        if mw.func_dict['plot_ssp']:
            plot.plot_ssp(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                          figures_path, ermsub)

        if mw.func_dict['plot_ssp_eog']:
            plot.plot_ssp_eog(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                              figures_path)

        if mw.func_dict['plot_ssp_ecg']:
            plot.plot_ssp_ecg(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                              figures_path)

        if mw.func_dict['run_ica']:
            operations.run_ica(name, save_dir, p.highpass, p.lowpass, p.eog_channel, p.ecg_channel,
                               p.reject, p.flat, bad_channels, p.overwrite, p.autoreject,
                               p.save_plots, figures_path, pr.pscripts_path)

        # ==========================================================================
        # LOAD NON-ICA'ED EPOCHS AND APPLY ICA
        # ==========================================================================

        if mw.func_dict['apply_ica']:
            operations.apply_ica(name, save_dir, p.highpass, p.lowpass, p.overwrite)

        # ==========================================================================
        # EVOKEDS
        # ==========================================================================

        if mw.func_dict['get_evokeds']:
            operations.get_evokeds(name, save_dir, p.highpass, p.lowpass, mw.func_dict, ermsub,
                                   p.detrend, p.enable_ica, p.overwrite)

        if mw.func_dict['get_h1h2_evokeds']:
            operations.get_h1h2_evokeds(name, save_dir, p.highpass, p.lowpass, p.enable_ica,
                                        mw.func_dict, ermsub, p.detrend)

        # ==========================================================================
        # TIME-FREQUENCY-ANALASYS
        # ==========================================================================

        if mw.func_dict['tfr']:
            operations.tfr(name, save_dir, p.highpass, p.lowpass, p.enable_ica, p.tfr_freqs, p.overwrite_tfr,
                           p.tfr_method, p.multitaper_bandwith, p.stockwell_width, p.n_jobs)

        # ==========================================================================
        # NOISE COVARIANCE MATRIX
        # ==========================================================================

        if mw.func_dict['estimate_noise_covariance']:
            operations.estimate_noise_covariance(name, save_dir, p.highpass, p.lowpass, p.overwrite,
                                                 ermsub, pr.data_path, p.baseline, bad_channels,
                                                 p.n_jobs, p.erm_noise_cov, p.calm_noise_cov,
                                                 p.enable_ica, p.erm_ica)

        if mw.func_dict['plot_noise_covariance']:
            plot.plot_noise_covariance(name, save_dir, p.highpass, p.lowpass,
                                       p.save_plots, figures_path, p.erm_noise_cov, ermsub,
                                       p.calm_noise_cov)

        # ==========================================================================
        # CO-REGISTRATION
        # ==========================================================================

        # use mne.gui.coregistration()

        if mw.func_dict['mri_coreg']:
            operations.mri_coreg(name, save_dir, subtomri, pr.subjects_dir)

        if mw.func_dict['plot_transformation']:
            plot.plot_transformation(name, save_dir, subtomri, pr.subjects_dir,
                                     p.save_plots, figures_path)

        if mw.func_dict['plot_sensitivity_maps']:
            plot.plot_sensitivity_maps(name, save_dir, pr.subjects_dir, p.ch_types,
                                       p.save_plots, figures_path)

        # ==========================================================================
        # CREATE FORWARD MODEL
        # ==========================================================================

        if mw.func_dict['create_forward_solution']:
            operations.create_forward_solution(name, save_dir, subtomri, pr.subjects_dir,
                                               p.source_space_method, p.overwrite,
                                               p.n_jobs, p.eeg_fwd)

        # ==========================================================================
        # CREATE INVERSE OPERATOR
        # ==========================================================================

        if mw.func_dict['create_inverse_operator']:
            operations.create_inverse_operator(name, save_dir, p.highpass, p.lowpass,
                                               p.overwrite, ermsub, p.calm_noise_cov,
                                               p.erm_noise_cov)

        # ==========================================================================
        # SOURCE ESTIMATE MNE
        # ==========================================================================

        if mw.func_dict['source_estimate']:
            operations.source_estimate(name, save_dir, p.highpass, p.lowpass, p.inverse_method, p.toi,
                                       p.overwrite)

        if mw.func_dict['vector_source_estimate']:
            operations.vector_source_estimate(name, save_dir, p.highpass, p.lowpass,
                                              p.inverse_method, p.toi, p.overwrite)

        if mw.func_dict['mixed_norm_estimate']:
            operations.mixed_norm_estimate(name, save_dir, p.highpass, p.lowpass, p.toi, p.inverse_method,
                                           p.erm_noise_cov,
                                           ermsub, p.calm_noise_cov, p.event_id, p.mixn_dip, p.overwrite)

        if mw.func_dict['ecd_fit']:
            operations.ecd_fit(name, save_dir, p.highpass, p.lowpass, ermsub, pr.subjects_dir,
                               subtomri, p.erm_noise_cov, p.calm_noise_cov, p.ecds,
                               p.save_plots, figures_path)

        if mw.func_dict['apply_morph']:
            operations.apply_morph(name, save_dir, p.highpass, p.lowpass,
                                   pr.subjects_dir, subtomri, p.inverse_method,
                                   p.overwrite, p.morph_to,
                                   p.source_space_method, p.event_id)

        if mw.func_dict['apply_morph_normal']:
            operations.apply_morph_normal(name, save_dir, p.highpass, p.lowpass,
                                          pr.subjects_dir, subtomri, p.inverse_method,
                                          p.overwrite, p.morph_to,
                                          p.source_space_method, p.event_id)

        if not p.combine_ab:
            if mw.func_dict['create_func_label']:
                operations.create_func_label(name, save_dir, p.highpass, p.lowpass,
                                             p.inverse_method, p.event_id, subtomri, pr.subjects_dir,
                                             p.source_space_method, p.label_origin,
                                             p.parcellation_orig, p.ev_ids_label_analysis,
                                             p.save_plots, figures_path, pr.pscripts_path,
                                             p.n_std, p.combine_ab)

        if not p.combine_ab:
            if mw.func_dict['func_label_processing']:
                operations.func_label_processing(name, save_dir, p.highpass, p.lowpass,
                                                 p.save_plots, figures_path, subtomri, pr.subjects_dir,
                                                 pr.pscripts_path, p.ev_ids_label_analysis,
                                                 p.corr_threshold, p.combine_ab)

        if mw.func_dict['func_label_ctf_ps']:
            operations.func_label_ctf_ps(name, save_dir, p.highpass, p.lowpass, subtomri,
                                         pr.subjects_dir, p.parcellation_orig)
        # ==========================================================================
        # PRINT INFO
        # ==========================================================================

        if mw.func_dict['plot_sensors']:
            plot.plot_sensors(name, save_dir)

        # ==========================================================================
        # PLOT RAW DATA
        # ==========================================================================

        if mw.func_dict['plot_raw']:
            plot.plot_raw(name, save_dir, bad_channels)

        if mw.func_dict['plot_filtered']:
            plot.plot_filtered(name, save_dir, p.highpass, p.lowpass, bad_channels)

        if mw.func_dict['plot_events']:
            plot.plot_events(name, save_dir, p.save_plots, figures_path, p.event_id)

        if mw.func_dict['plot_events_diff']:
            plot.plot_events_diff(name, save_dir, p.save_plots, figures_path)

        if mw.func_dict['plot_eog_events']:
            plot.plot_eog_events(name, save_dir)

        # ==========================================================================
        # PLOT POWER SPECTRA
        # ==========================================================================

        if mw.func_dict['plot_power_spectra']:
            plot.plot_power_spectra(name, save_dir, p.highpass, p.lowpass,
                                    p.save_plots, figures_path, bad_channels)

        if mw.func_dict['plot_power_spectra_epochs']:
            plot.plot_power_spectra_epochs(name, save_dir, p.highpass, p.lowpass,
                                           p.save_plots, figures_path)

        if mw.func_dict['plot_power_spectra_topo']:
            plot.plot_power_spectra_topo(name, save_dir, p.highpass, p.lowpass,
                                         p.save_plots, figures_path)

        # ==========================================================================
        # PLOT TIME-FREQUENCY-ANALASYS
        # ==========================================================================

        if mw.func_dict['plot_tfr']:
            plot.plot_tfr(name, save_dir, p.highpass, p.lowpass, p.etmin, p.etmax, p.baseline,
                          p.tfr_method, p.save_plots, figures_path)

        if mw.func_dict['tfr_event_dynamics']:
            plot.tfr_event_dynamics(name, save_dir, p.etmin, p.etmax, p.save_plots,
                                    figures_path, bad_channels, p.n_jobs)

        # ==========================================================================
        # PLOT CLEANED EPOCHS
        # ==========================================================================
        if mw.func_dict['plot_epochs']:
            plot.plot_epochs(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                             figures_path)

        if mw.func_dict['plot_epochs_image']:
            plot.plot_epochs_image(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                                   figures_path)

        if mw.func_dict['plot_epochs_topo']:
            plot.plot_epochs_topo(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                                  figures_path)

        if mw.func_dict['plot_epochs_drop_log']:
            plot.plot_epochs_drop_log(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                                      figures_path)
        # ==========================================================================
        # PLOT EVOKEDS
        # ==========================================================================

        if mw.func_dict['plot_evoked_topo']:
            plot.plot_evoked_topo(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                                  figures_path)

        if mw.func_dict['plot_evoked_topomap']:
            plot.plot_evoked_topomap(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                                     figures_path)

        if mw.func_dict['plot_evoked_butterfly']:
            plot.plot_evoked_butterfly(name, save_dir, p.highpass, p.lowpass,
                                       p.save_plots, figures_path)

        if mw.func_dict['plot_evoked_field']:
            plot.plot_evoked_field(name, save_dir, p.highpass, p.lowpass, subtomri,
                                   pr.subjects_dir, p.save_plots, figures_path,
                                   p.mne_evoked_time, p.n_jobs)

        if mw.func_dict['plot_evoked_joint']:
            plot.plot_evoked_joint(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                                   figures_path)

        if mw.func_dict['plot_evoked_white']:
            plot.plot_evoked_white(name, save_dir, p.highpass, p.lowpass,
                                   p.save_plots, figures_path, p.erm_noise_cov, ermsub, p.calm_noise_cov)

        if mw.func_dict['plot_evoked_image']:
            plot.plot_evoked_image(name, save_dir, p.highpass, p.lowpass,
                                   p.save_plots, figures_path)

        if mw.func_dict['plot_evoked_h1h2']:
            plot.plot_evoked_h1h2(name, save_dir, p.highpass, p.lowpass, p.event_id,
                                  p.save_plots, figures_path)

        if mw.func_dict['plot_gfp']:
            plot.plot_gfp(name, save_dir, p.highpass, p.lowpass, p.save_plots,
                          figures_path)
        # ==========================================================================
        # PLOT SOURCE ESTIMATES MNE
        # ==========================================================================

        if mw.func_dict['plot_stc']:
            plot.plot_stc(name, save_dir, p.highpass, p.lowpass,
                          subtomri, pr.subjects_dir,
                          p.inverse_method, p.mne_evoked_time, p.event_id,
                          p.stc_interactive, p.save_plots, figures_path)

        if mw.func_dict['plot_normal_stc']:
            plot.plot_normal_stc(name, save_dir, p.highpass, p.lowpass,
                                 subtomri, pr.subjects_dir,
                                 p.inverse_method, p.mne_evoked_time, p.event_id,
                                 p.stc_interactive, p.save_plots, figures_path)

        if mw.func_dict['plot_vector_stc']:
            plot.plot_vector_stc(name, save_dir, p.highpass, p.lowpass, subtomri, pr.subjects_dir,
                                 p.inverse_method, p.mne_evoked_time, p.event_id, p.stc_interactive,
                                 p.save_plots, figures_path)

        if mw.func_dict['plot_mixn']:
            plot.plot_mixn(name, save_dir, p.highpass, p.lowpass, subtomri, pr.subjects_dir,
                           p.mne_evoked_time, p.event_id, p.stc_interactive,
                           p.save_plots, figures_path, p.mixn_dip, p.parcellation)

        if mw.func_dict['plot_animated_stc']:
            plot.plot_animated_stc(name, save_dir, p.highpass, p.lowpass, subtomri,
                                   pr.subjects_dir, p.inverse_method, p.stc_animation, p.event_id,
                                   figures_path, p.ev_ids_label_analysis)

        if mw.func_dict['plot_snr']:
            plot.plot_snr(name, save_dir, p.highpass, p.lowpass, p.save_plots, figures_path,
                          p.inverse_method, p.event_id)

        if mw.func_dict['plot_label_time_course']:
            plot.plot_label_time_course(name, save_dir, p.highpass, p.lowpass,
                                        subtomri, pr.subjects_dir, p.inverse_method, p.source_space_method,
                                        p.target_labels, p.save_plots, figures_path,
                                        p.parcellation, p.event_id, p.ev_ids_label_analysis)

        # ==========================================================================
        # TIME-FREQUENCY IN SOURCE SPACE
        # ==========================================================================

        if mw.func_dict['label_power_phlck']:
            operations.label_power_phlck(name, save_dir, p.highpass, p.lowpass, p.baseline, p.tfr_freqs,
                                         subtomri, p.target_labels, p.parcellation,
                                         p.ev_ids_label_analysis, p.n_jobs,
                                         save_dir, figures_path)

        if mw.func_dict['plot_label_power_phlck']:
            plot.plot_label_power_phlck(name, save_dir, p.highpass, p.lowpass, subtomri, p.parcellation,
                                        p.baseline, p.tfr_freqs, p.save_plots, figures_path, p.n_jobs,
                                        p.target_labels, p.ev_ids_label_analysis)

        if mw.func_dict['source_space_connectivity']:
            operations.source_space_connectivity(name, save_dir, p.highpass, p.lowpass,
                                                 subtomri, pr.subjects_dir, p.parcellation,
                                                 p.target_labels, p.con_methods,
                                                 p.con_fmin, p.con_fmax,
                                                 p.n_jobs, p.overwrite, p.enable_ica,
                                                 p.ev_ids_label_analysis)

        if mw.func_dict['plot_source_space_connectivity']:
            plot.plot_source_space_connectivity(name, save_dir, p.highpass, p.lowpass,
                                                subtomri, pr.subjects_dir, p.parcellation,
                                                p.target_labels, p.con_methods, p.con_fmin,
                                                p.con_fmax, p.save_plots,
                                                figures_path, p.ev_ids_label_analysis)

        # ==========================================================================
        # General Statistics
        # ==========================================================================
        if mw.func_dict['corr_ntr']:
            operations.corr_ntr(name, save_dir, p.highpass, p.lowpass, mw.func_dict,
                                ermsub, subtomri, p.enable_ica, p.save_plots, figures_path)

        # close all plots
        if mw.func_dict['close_plots']:
            plot.close_all()

    # GOING OUT OF SUBJECT LOOP
    # %%============================================================================
    # All-Subject-Analysis
    # ==============================================================================
    if mw.func_dict['pp_alignment']:
        pinprick.pp_alignment(ab_dict, cond_dict, pr.sub_dict, pr.data_path, p.highpass, p.lowpass, pr.pscripts_path,
                              p.event_id, pr.subjects_dir, p.inverse_method, p.source_space_method,
                              p.parcellation, figures_path)

    if mw.func_dict['cmp_label_time_course']:
        plot.cmp_label_time_course(pr.data_path, p.highpass, p.lowpass, pr.sub_dict, comp_dict,
                                   pr.subjects_dir, p.inverse_method, p.source_space_method, p.parcellation,
                                   p.target_labels, p.save_plots, figures_path,
                                   p.event_id, p.ev_ids_label_analysis, p.combine_ab,
                                   pr.pscripts_path, mw.func_dict)

    if p.combine_ab:
        if mw.func_dict['create_func_label']:
            for key in ab_dict:
                print(60 * '=' + '\n' + key)
                if len(ab_dict[key]) > 1:
                    name = (ab_dict[key][0], ab_dict[key][1])
                    save_dir = (join(pr.data_path, name[0]), join(pr.data_path, name[1]))
                    pattern = r'pp[0-9]+[a-z]?'
                    if p.unspecified_names:
                        pattern = r'.*'
                    match = re.match(pattern, name[0])
                    prefix = match.group()
                    subtomri = pr.sub_dict[prefix]
                else:
                    name = ab_dict[key][0]
                    save_dir = join(pr.data_path, name)
                    pattern = r'pp[0-9]+[a-z]?'
                    if p.unspecified_names:
                        pattern = r'.*'
                    match = re.match(pattern, name)
                    prefix = match.group()
                    subtomri = pr.sub_dict[prefix]
                operations.create_func_label(name, save_dir, p.highpass, p.lowpass,
                                             p.inverse_method, p.event_id, subtomri, pr.subjects_dir,
                                             p.source_space_method, p.label_origin,
                                             p.parcellation_orig, p.ev_ids_label_analysis,
                                             p.save_plots, figures_path, pr.pscripts_path,
                                             p.n_std, p.combine_ab)

    if p.combine_ab:
        if mw.func_dict['func_label_processing']:
            for key in ab_dict:
                print(60 * '=' + '\n' + key)
                if len(ab_dict[key]) > 1:
                    name = (ab_dict[key][0], ab_dict[key][1])
                    save_dir = (join(pr.data_path, name[0]), join(pr.data_path, name[1]))
                    pattern = r'pp[0-9]+[a-z]?'
                    if p.unspecified_names:
                        pattern = r'.*'
                    match = re.match(pattern, name[0])
                    prefix = match.group()
                    subtomri = pr.sub_dict[prefix]
                else:
                    name = ab_dict[key][0]
                    save_dir = join(pr.data_path, name)
                    pattern = r'pp[0-9]+[a-z]?'
                    if p.unspecified_names:
                        pattern = r'.*'
                    match = re.match(pattern, name)
                    prefix = match.group()
                    subtomri = pr.sub_dict[prefix]
                operations.func_label_processing(name, save_dir, p.highpass, p.lowpass,
                                                 p.save_plots, figures_path, subtomri, pr.subjects_dir,
                                                 pr.pscripts_path, p.ev_ids_label_analysis,
                                                 p.corr_threshold, p.combine_ab)

    if mw.func_dict['sub_func_label_analysis']:
        plot.sub_func_label_analysis(p.highpass, p.lowpass, p.etmax, sub_files_dict,
                                     pr.pscripts_path, p.label_origin, p.ev_ids_label_analysis, p.save_plots,
                                     figures_path, mw.func_dict)

    if mw.func_dict['all_func_label_analysis']:
        plot.all_func_label_analysis(p.highpass, p.lowpass, p.etmax, sel_files, pr.pscripts_path,
                                     p.label_origin, p.ev_ids_label_analysis, p.save_plots,
                                     figures_path)

    # %%============================================================================
    # GRAND AVERAGES (sensor space and source space)
    # ==============================================================================

    if mw.func_dict['grand_avg_evokeds']:
        operations.grand_avg_evokeds(pr.data_path, grand_avg_dict, pr.save_dir_averages,
                                     p.highpass, p.lowpass, mw.func_dict, mw.quality,
                                     p.ana_h1h2)

    if mw.func_dict['pp_combine_evokeds_ab']:
        pinprick.pp_combine_evokeds_ab(pr.data_path, pr.save_dir_averages, p.highpass, p.lowpass, ab_dict)

    if mw.func_dict['grand_avg_tfr']:
        operations.grand_avg_tfr(pr.data_path, grand_avg_dict, pr.save_dir_averages,
                                 p.highpass, p.lowpass, p.tfr_method)

    if mw.func_dict['grand_avg_morphed']:
        operations.grand_avg_morphed(grand_avg_dict, pr.data_path, p.inverse_method, pr.save_dir_averages,
                                     p.highpass, p.lowpass, p.event_id)

    if mw.func_dict['grand_avg_normal_morphed']:
        operations.grand_avg_normal_morphed(grand_avg_dict, pr.data_path, p.inverse_method, pr.save_dir_averages,
                                            p.highpass, p.lowpass, p.event_id)

    if mw.func_dict['grand_avg_connect']:
        operations.grand_avg_connect(grand_avg_dict, pr.data_path, p.con_methods,
                                     p.con_fmin, p.con_fmax, pr.save_dir_averages,
                                     p.lowpass, p.highpass)

    if mw.func_dict['grand_avg_label_power']:
        operations.grand_avg_label_power(grand_avg_dict, p.ev_ids_label_analysis,
                                         pr.data_path, p.highpass, p.lowpass,
                                         p.target_labels, pr.save_dir_averages)

    if mw.func_dict['grand_avg_func_labels']:
        operations.grand_avg_func_labels(grand_avg_dict, p.highpass, p.lowpass,
                                         pr.save_dir_averages, p.event_id, p.ev_ids_label_analysis,
                                         pr.subjects_dir, p.source_space_method,
                                         p.parcellation_orig, pr.pscripts_path, p.save_plots,
                                         p.label_origin, figures_path, p.n_std)

    # %%============================================================================
    # GRAND AVERAGES PLOTS (sensor space and source space)
    # ================================================================================

    if mw.func_dict['plot_grand_avg_evokeds']:
        plot.plot_grand_avg_evokeds(p.highpass, p.lowpass, pr.save_dir_averages, grand_avg_dict,
                                    p.event_id, p.save_plots, figures_path, mw.quality)

    if mw.func_dict['plot_grand_avg_evokeds_h1h2']:
        plot.plot_grand_avg_evokeds_h1h2(p.highpass, p.lowpass, pr.save_dir_averages, grand_avg_dict,
                                         p.event_id, p.save_plots, figures_path, mw.quality)

    if mw.func_dict['plot_evoked_compare']:
        plot.plot_evoked_compare(pr.data_path, pr.save_dir_averages, p.highpass, p.lowpass, comp_dict, p.combine_ab,
                                 p.event_id)

    if mw.func_dict['plot_grand_avg_tfr']:
        plot.plot_grand_avg_tfr(p.highpass, p.lowpass, p.baseline, p.etmin, p.etmax,
                                pr.save_dir_averages, grand_avg_dict,
                                p.event_id, p.save_plots, figures_path)

    if mw.func_dict['plot_grand_avg_stc']:
        plot.plot_grand_avg_stc(p.highpass, p.lowpass, pr.save_dir_averages,
                                grand_avg_dict, p.mne_evoked_time, p.morph_to,
                                pr.subjects_dir, p.event_id, p.save_plots,
                                figures_path)

    if mw.func_dict['plot_grand_avg_stc_anim']:
        plot.plot_grand_avg_stc_anim(p.highpass, p.lowpass, pr.save_dir_averages,
                                     grand_avg_dict, p.stc_animation, p.morph_to,
                                     pr.subjects_dir, p.event_id, figures_path)

    if mw.func_dict['plot_grand_avg_connect']:
        plot.plot_grand_avg_connect(p.highpass, p.lowpass, pr.save_dir_averages,
                                    grand_avg_dict, pr.subjects_dir, p.morph_to, p.parcellation,
                                    p.con_methods, p.con_fmin, p.con_fmax,
                                    p.save_plots, figures_path, p.ev_ids_label_analysis, p.target_labels)

    if mw.func_dict['plot_grand_avg_label_power']:
        plot.plot_grand_avg_label_power(grand_avg_dict, p.ev_ids_label_analysis, p.target_labels,
                                        pr.save_dir_averages, p.tfr_freqs, p.etmin, p.etmax, p.lowpass,
                                        p.highpass, p.save_plots, figures_path)

    # ==============================================================================
    # STATISTICS SOURCE SPACE
    # ==============================================================================

    if mw.func_dict['statistics_source_space']:
        operations.statistics_source_space(morphed_data_all, pr.save_dir_averages,
                                           p.independent_variable_1,
                                           p.independent_variable_2,
                                           p.time_window, p.n_permutations, p.highpass, p.lowpass,
                                           p.overwrite)

    # ==============================================================================
    # PLOT GRAND AVERAGES OF SOURCE ESTIMATES WITH STATISTICS CLUSTER MASK
    # ==============================================================================

    if mw.func_dict['plot_grand_averages_source_estimates_cluster_masked']:
        plot.plot_grand_averages_source_estimates_cluster_masked(
                pr.save_dir_averages, p.highpass, p.lowpass, pr.subjects_dir, p.inverse_method, p.time_window,
                p.save_plots, figures_path, p.independent_variable_1,
                p.independent_variable_2, p.mne_evoked_time, p.p_threshold)
    # ==============================================================================
    # MISCELLANEOUS
    # ==============================================================================

    if mw.func_dict['pp_plot_latency_S1_corr']:
        plot.pp_plot_latency_s1_corr(pr.data_path, sel_files, p.highpass, p.lowpass,
                                     p.save_plots, figures_path)

    # close all plots
    if mw.func_dict['close_plots']:
        plot.close_all()

    if mw.func_dict['shutdown']:
        ut.shutdown()
