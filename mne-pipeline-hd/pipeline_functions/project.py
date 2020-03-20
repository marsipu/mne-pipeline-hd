from os import listdir, makedirs
from os.path import exists, isdir, isfile, join

import mne
from PyQt5.QtWidgets import QFileDialog, QInputDialog

from pipeline_functions import subjects as subs


class MyProject:
    def __init__(self, mainwin):
        self.win = mainwin

        # Initiate some project-variables
        self.sel_files = []
        self.sel_mri_files = []

        self.get_paths()
        self.make_paths()
        self.update_sub_lists()

    def get_paths(self):
        # Get home_path
        self.home_path = self.win.settings.value('home_path')
        if self.home_path is None:
            hp = QFileDialog.getExistingDirectory(self.win, 'Select a folder to store your Pipeline-Projects')
            if hp == '':
                self.win.close()
                raise RuntimeError('You canceled an important step, start over')
            else:
                self.home_path = str(hp)
                self.win.settings.setValue('home_path', self.home_path)
        else:
            if not isdir(self.home_path):
                hp = QFileDialog.getExistingDirectory(self.win, f'{self.home_path} not found! '
                                                                f'Select the folder where '
                                                                f'you store your Pipeline-Projects')
                if hp == '':
                    self.win.close()
                    raise RuntimeError('You canceled an important step, start over')
                else:
                    self.home_path = str(hp)
                    self.win.settings.setValue('home_path', self.home_path)
            else:
                pass

        # Get project_name
        self.project_name = self.win.settings.value('project_name')
        self.projects = [p for p in listdir(self.home_path) if isdir(join(self.home_path, p, 'data'))]
        if len(self.projects) == 0:
            self.project_name, ok = QInputDialog.getText(self.win, 'Project-Selection',
                                                         f'No projects in {self.home_path} found\n'
                                                         'Enter a project-name for your first project')
            if ok:
                self.projects.append(self.project_name)
                self.win.settings.setValue('project_name', self.project_name)
                self.make_paths()
            else:
                # Problem in Python Console, QInputDialog somehow stays in memory
                self.win.close()
                raise RuntimeError('You canceled an important step, start over')
        elif self.project_name is None or self.project_name not in self.projects:
            self.project_name = self.projects[0]
            self.win.settings.setValue('project_name', self.project_name)

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
        self.file_list_path = join(self.pscripts_path, 'file_list.py')
        self.erm_list_path = join(self.pscripts_path, 'erm_list.py')
        self.motor_erm_list_path = join(self.pscripts_path, 'motor_erm_list.py')
        self.mri_sub_list_path = join(self.pscripts_path, 'mri_sub_list.py')
        self.sub_dict_path = join(self.pscripts_path, 'sub_dict.py')
        self.erm_dict_path = join(self.pscripts_path, 'erm_dict.py')
        self.bad_channels_dict_path = join(self.pscripts_path, 'bad_channels_dict.py')
        self.quality_dict_path = join(self.pscripts_path, 'quality.py')

        path_lists = [self.subjects_dir, self.data_path, self.erm_data_path, self.pscripts_path]
        file_lists = [self.file_list_path, self.erm_list_path, self.motor_erm_list_path, self.mri_sub_list_path,
                      self.sub_dict_path, self.erm_dict_path, self.bad_channels_dict_path, self.quality_dict_path]

        for path in path_lists:
            if not exists(path):
                makedirs(path)
                print(f'{path} created')

        for file in file_lists:
            if not isfile(file):
                with open(file, 'w') as fl:
                    fl.write('')
                print(f'{file} created')

    def update_sub_lists(self):
        self.projects = [p for p in listdir(self.home_path) if isdir(join(self.home_path, p, 'data'))]
        self.all_files = subs.read_files(self.file_list_path)
        self.all_mri_subjects = subs.read_files(self.mri_sub_list_path)
        self.erm_files = subs.read_files(self.erm_list_path)
        self.motor_erm_files = subs.read_files(self.motor_erm_list_path)
        self.sub_dict = subs.read_sub_dict(self.sub_dict_path)
        self.erm_dict = subs.read_sub_dict(self.erm_dict_path)
        self.bad_channels_dict = subs.read_bad_channels_dict(self.bad_channels_dict_path)
