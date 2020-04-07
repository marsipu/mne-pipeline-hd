import json
from ast import literal_eval
from os import listdir, makedirs
from os.path import exists, isdir, isfile, join

import mne
from PyQt5.QtWidgets import QFileDialog, QInputDialog

from pipeline_functions import subjects as subs


class MyProject:
    """
    A class with attributes for all the paths and parameters of the selected project
    """

    def __init__(self, mainwin):
        self.mw = mainwin

        self.parameters = {}
        # Todo: Solution with func-dicts for functions not optimal
        self.func_dict = mainwin.func_dict

        self.get_paths()
        self.make_paths()
        self.load_parameters()
        # After load_parameters, because event-id is needed
        self.populate_directories()
        self.load_sub_lists()

    def get_paths(self):
        # Get home_path
        self.home_path = self.mw.settings.value('home_path')
        if self.home_path is None:
            hp = QFileDialog.getExistingDirectory(self.mw, 'Select a folder to store your Pipeline-Projects')
            if hp == '':
                self.mw.close()
                raise RuntimeError('You canceled an important step, start over')
            else:
                self.home_path = str(hp)
                self.mw.settings.setValue('home_path', self.home_path)
        else:
            if not isdir(self.home_path):
                hp = QFileDialog.getExistingDirectory(self.mw, f'{self.home_path} not found! '
                                                               f'Select the folder where '
                                                               f'you store your Pipeline-Projects')
                if hp == '':
                    self.mw.close()
                    raise RuntimeError('You canceled an important step, start over')
                else:
                    self.home_path = str(hp)
                    self.mw.settings.setValue('home_path', self.home_path)
            else:
                pass

        # Get project_name
        self.project_name = self.mw.settings.value('project_name')
        self.projects = [p for p in listdir(self.home_path) if isdir(join(self.home_path, p, 'data'))]
        if len(self.projects) == 0:
            self.project_name, ok = QInputDialog.getText(self.mw, 'Project-Selection',
                                                         f'No projects in {self.home_path} found\n'
                                                         'Enter a project-name for your first project')
            if ok:
                self.projects.append(self.project_name)
                self.mw.settings.setValue('project_name', self.project_name)
                self.make_paths()
            else:
                # Problem in Python Console, QInputDialog somehow stays in memory
                self.mw.close()
                raise RuntimeError('You canceled an important step, start over')
        elif self.project_name is None or self.project_name not in self.projects:
            self.project_name = self.projects[0]
            self.mw.settings.setValue('project_name', self.project_name)

        print(f'Home-Path: {self.home_path}')
        print(f'Project-Name: {self.project_name}')
        print(f'Projects-found: {self.projects}')

    def make_paths(self):
        # Initiate other paths
        self.project_path = join(self.home_path, self.project_name)
        self.data_path = join(self.project_path, 'data')
        self.figures_path = join(self.project_path, 'figures')
        self.save_dir_averages = join(self.data_path, 'grand_averages')
        self.erm_data_path = join(self.data_path, 'empty_room_data')
        self.subjects_dir = join(self.home_path, 'Freesurfer')
        mne.utils.set_config("SUBJECTS_DIR", self.subjects_dir, set_env=True)
        # Subject-List/Dict-Path
        self.pscripts_path = join(self.project_path, '_pipeline_scripts')
        self.file_list_path = join(self.pscripts_path, 'file_list.json')
        self.erm_list_path = join(self.pscripts_path, 'erm_list.json')
        self.mri_sub_list_path = join(self.pscripts_path, 'mri_sub_list.json')
        self.sub_dict_path = join(self.pscripts_path, 'sub_dict.json')
        self.erm_dict_path = join(self.pscripts_path, 'erm_dict.json')
        self.bad_channels_dict_path = join(self.pscripts_path, 'bad_channels_dict.json')

        path_lists = [self.subjects_dir, self.data_path, self.erm_data_path, self.pscripts_path]
        file_lists = [self.file_list_path, self.erm_list_path, self.mri_sub_list_path,
                      self.sub_dict_path, self.erm_dict_path, self.bad_channels_dict_path]

        for path in path_lists:
            if not exists(path):
                makedirs(path)
                print(f'{path} created')

        for file in file_lists:
            if not isfile(file):
                with open(file, 'w') as fl:
                    fl.write('')
                print(f'{file} created')

    def load_sub_lists(self):
        self.projects = [p for p in listdir(self.home_path) if isdir(join(self.home_path, p, 'data'))]
        try:
            with open(self.file_list_path, 'r') as file:
                self.all_files = json.load(file)
        except json.decoder.JSONDecodeError:
            self.all_files = []

        try:
            with open(self.mri_sub_list_path, 'r') as file:
                self.all_mri_subjects = json.load(file)
        except json.decoder.JSONDecodeError:
            self.all_mri_subjects = []

        try:
            with open(self.erm_list_path, 'r') as file:
                self.erm_files = json.load(file)
        except json.decoder.JSONDecodeError:
            self.erm_files = []

        try:
            with open(self.sub_dict_path, 'r') as file:
                self.sub_dict = json.load(file)
        except json.decoder.JSONDecodeError:
            self.sub_dict = {}

        try:
            with open(self.erm_dict_path, 'r') as file:
                self.erm_dict = json.load(file)
        except json.decoder.JSONDecodeError:
            self.erm_dict = {}

        try:
            with open(self.bad_channels_dict_path, 'r') as file:
                self.bad_channels_dict = json.load(file)
        except json.decoder.JSONDecodeError:
            self.bad_channels_dict = {}

        self.sel_files = self.mw.settings.value('sel_files', defaultValue=[])
        self.sel_mri_files = self.mw.settings.value('sel_mri_files', defaultValue=[])

    def load_py_lists(self):
        self.all_files = subs.read_files(join(self.pscripts_path, 'file_list.py'))
        self.all_mri_subjects = subs.read_files(join(self.pscripts_path, 'mri_sub_list.py'))
        self.erm_files = subs.read_files(join(self.pscripts_path, 'erm_list.py'))
        self.sub_dict = subs.read_sub_dict(join(self.pscripts_path, 'sub_dict.py'))
        self.erm_dict = subs.read_sub_dict(join(self.pscripts_path, 'erm_dict.py'))
        self.bad_channels_dict = subs.read_bad_channels_dict(join(self.pscripts_path, 'bad_channels_dict.py'))

    def save_sub_lists(self):
        self.mw.settings.setValue('home_path', self.home_path)
        self.mw.settings.setValue('project_name', self.project_name)
        self.mw.settings.setValue('projects', self.projects)
        self.mw.settings.setValue('sel_files', self.sel_files)
        self.mw.settings.setValue('sel_mri_files', self.sel_mri_files)
        with open(join(self.pscripts_path, 'file_list.json'), 'w') as file:
            json.dump(self.all_files, file, indent=4)
        with open(join(self.pscripts_path, 'erm_list.json'), 'w') as file:
            json.dump(self.erm_files, file, indent=4)
        with open(join(self.pscripts_path, 'mri_sub_list.json'), 'w') as file:
            json.dump(self.all_mri_subjects, file, indent=4)
        with open(join(self.pscripts_path, 'sub_dict.json'), 'w') as file:
            json.dump(self.sub_dict, file, indent=4)
        with open(join(self.pscripts_path, 'erm_dict.json'), 'w') as file:
            json.dump(self.erm_dict, file, indent=4)
        with open(join(self.pscripts_path, 'bad_channels_dict.json'), 'w') as file:
            json.dump(self.bad_channels_dict, file, indent=4)

    def load_parameters(self):
        try:
            with open(join(self.pscripts_path, f'parameters_{self.project_name}.json'), 'r') as read_file:
                self.parameters = json.load(read_file)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            string_params = dict(self.mw.pd_params['default'])
            for param in string_params:
                try:
                    self.parameters[param] = literal_eval(string_params[param])
                except (ValueError, SyntaxError):
                    # Allow parameters to be defined by functions by numpy, etc.
                    if self.mw.pd_params['gui_type'][param] == 'FuncGui':
                        self.parameters[param] = eval(string_params[param])
                    else:
                        self.parameters[param] = string_params[param]

    def save_parameters(self):
        with open(join(self.pscripts_path, f'parameters_{self.project_name}.json'), 'w') as write_file:
            json.dump(self.parameters, write_file, indent=4)

    def populate_directories(self):
        # create grand averages path with a statistics folder
        ga_folders = ['statistics', 'evoked', 'stc', 'tfr', 'connect']
        for subfolder in ga_folders:
            grand_average_path = join(self.data_path, 'grand_averages', subfolder)
            if not exists(grand_average_path):
                makedirs(grand_average_path)
                print(grand_average_path + ' has been created')

        # create erm(empty_room_measurements)paths
        erm_path = join(self.data_path, 'empty_room_data')
        if not exists(erm_path):
            makedirs(erm_path)
            print(erm_path + ' has been created')

        # create figures path
        folders = ['epochs', 'epochs_image', 'epochs_topo', 'evoked_image',
                   'power_spectra_raw', 'power_spectra_epochs',
                   'power_spectra_topo', 'evoked_butterfly', 'evoked_field',
                   'evoked_topo', 'evoked_topomap', 'evoked_joint', 'evoked_white', 'gfp',
                   'ica', 'ssp', 'stcs', 'vec_stcs', 'mxne', 'transformation', 'source_space',
                   'noise_covariance', 'events', 'label_time_course', 'ECD',
                   'stcs_movie', 'bem', 'snr', 'statistics', 'correlation_ntr',
                   'labels', 'tf_sensor_space/plot', 'tf_source_space/label_power',
                   'tf_sensor_space/topo', 'tf_sensor_space/joint',
                   'tf_sensor_space/oscs', 'tf_sensor_space/itc',
                   'tf_sensor_space/dynamics', 'tf_source_space/connectivity',
                   'epochs_drop_log', 'func_labels', 'evoked_h1h2', 'Various',
                   'sensitivity_maps', 'mxn_dipoles']

        for folder in folders:
            folder_path = join(self.figures_path, folder)
            if not exists(folder_path):
                makedirs(folder_path)
                print(folder_path + ' has been created')

        # create subfolders for for event_ids
        trialed_folders = ['epochs', 'power_spectra_epochs', 'power_spectra_topo',
                           'epochs_image', 'epochs_topo', 'evoked_butterfly',
                           'evoked_field', 'evoked_topomap', 'evoked_image',
                           'evoked_joint', 'evoked_white', 'gfp', 'label_time_course', 'ECD',
                           'stcs', 'vec_stcs', 'stcs_movie', 'snr',
                           'tf_sensor_space/plot', 'tf_sensor_space/topo',
                           'tf_sensor_space/joint', 'tf_sensor_space/oscs',
                           'tf_sensor_space/itc', 'evoked_h1h2', 'mxn_dipoles']

        for ev_id in self.parameters['event_id']:
            for tr in trialed_folders:
                subfolder = join(self.figures_path, tr, ev_id)
                if not exists(subfolder):
                    try:
                        makedirs(subfolder)
                        print(subfolder + ' has been created')
                    except OSError:
                        print(subfolder + ': this event-id-name can\'t be used due to OS-Folder-Naming-Conventions')

        # create grand average figures path
        grand_averages_figures_path = join(self.figures_path, 'grand_averages')
        figure_subfolders = ['sensor_space/evoked', 'sensor_space/tfr',
                             'source_space/statistics', 'source_space/stc',
                             'source_space/connectivity', 'source_space/stc_movie',
                             'source_space/tfr']

        for figure_subfolder in figure_subfolders:
            folder_path = join(grand_averages_figures_path, figure_subfolder)
            if not exists(folder_path):
                makedirs(folder_path)
                print(folder_path + ' has been created')
