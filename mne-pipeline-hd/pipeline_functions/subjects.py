"""
subject_organisation by Martin Schulz
martin.schulz@stud.uni-heidelberg.de
"""
import os
import re
import shutil
from functools import partial
from os.path import isdir, isfile, join
from pathlib import Path

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor

from qtpy.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QLabel, \
    QProgressBar, QMessageBox, QGridLayout, QCheckBox

# Todo: GUI erstellen(FolderDialog, Input for RegExp)
from basic_functions import io
from pipeline_functions import utilities as ut


def file_selection(which_file, all_files):
    if which_file == '':
        raise RuntimeError('No file assigned, rerun and assign one')
    # Turn string input into according sub_list-Index
    try:
        if 'all' in which_file:
            if ',' in which_file:
                splits = which_file.split(',')
                rm = []
                run = []
                for sp in splits:
                    if '!' in sp and '-' in sp:
                        x, y = sp.split('-')
                        x = x[1:]
                        for n in range(int(x) - 1, int(y)):
                            rm.append(n)
                    elif '!' in sp:
                        rm.append(int(sp[1:]) - 1)
                    elif 'all' in sp:
                        for i in range(0, len(all_files)):
                            run.append(i)
                for r in rm:
                    if r in run:
                        run.remove(r)
            else:
                run = range(0, len(all_files))

        elif ',' in which_file and '-' in which_file:
            z = which_file.split(',')
            run = []
            rm = []
            for i in z:
                if '-' in i and '!' not in i:
                    x, y = i.split('-')
                    for n in range(int(x) - 1, int(y)):
                        run.append(n)
                elif '!' not in i:
                    run.append(int(i) - 1)
                elif '!' in i and '-' in i:
                    x, y = i.split('-')
                    x = x[1:]
                    for n in range(int(x) - 1, int(y)):
                        rm.append(n)
                elif '!' in i:
                    rm.append(int(i[1:]) - 1)

            for r in rm:
                if r in run:
                    run.remove(r)

        elif '-' in which_file and ',' not in which_file:
            x, y = which_file.split('-')
            run = range(int(x) - 1, int(y))

        elif ',' in which_file and '-' not in which_file:
            splits = which_file.split(',')
            rm = []
            run = []
            for sp in splits:
                if '!' in sp:
                    rm.append(int(sp) - 1)
                else:
                    run.append(int(sp) - 1)
            if len(rm) > 0:
                for r in rm:
                    run.remove(r)

        else:
            run = [int(which_file) - 1]

        files = [x for (i, x) in enumerate(all_files) if i in run]

        return files

    except TypeError:
        raise TypeError(f'{which_file} is not a string(enclosed by quotes)')

    except ValueError:
        raise ValueError(f'{which_file} makes a problem')


def move_file(forig, fdest):
    parent_dir = Path(fdest).parent
    # Copy sub_files to destination
    if not isfile(fdest):
        os.makedirs(parent_dir, exist_ok=True)
        print(f'Copying File from {forig}...')
        shutil.copy2(forig, fdest)
        print(f'Finished Copying to {fdest}')
    else:
        print(f'{fdest} already exists')
        pass


def write_file_list(fname, file_list_path):
    if not isfile(file_list_path):
        with open(file_list_path, 'w') as el1:
            el1.write(fname + '\n')
        print(f'{fname} was automatically added')
    else:
        with open(file_list_path, 'a') as sl2:
            sl2.write(fname + '\n')
        print(f'{fname} was automatically added')


def read_files(file_list_path):
    file_list = []
    file_name = Path(file_list_path).name
    try:
        with open(file_list_path, 'r') as sl:
            for line in sl:
                current_place = line[:-1]
                file_list.append(current_place)

    except FileNotFoundError:
        print(f'{file_name} not yet created')
        pass

    return file_list


class AddFiles(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QVBoxLayout()

        self.files = list()
        self.paths = dict()
        self.file_types = dict()

        self.init_ui()
        self.setLayout(self.layout)
        self.open()

    def init_ui(self):
        # Input Buttons
        files_bt = QPushButton('File-Import', self)
        files_bt.clicked.connect(self.get_files_path)
        folder_bt = QPushButton('Folder-Import', self)
        folder_bt.clicked.connect(self.get_folder_path)
        input_bt_layout = QHBoxLayout()
        input_bt_layout.addWidget(files_bt)
        input_bt_layout.addWidget(folder_bt)
        self.layout.addLayout(input_bt_layout)

        list_label = QLabel('These .fif-Files can be imported \n'
                            '(the empty-room-measurements should appear here too \n'
                            ' and will be sorted, if name contains e.g. "empty", "leer", ...)', self)
        self.layout.addWidget(list_label)
        self.list_widget = QListWidget(self)
        self.list_widget.itemChanged.connect(self.double_click_rename)
        self.layout.addWidget(self.list_widget)
        self.pgbar = QProgressBar(self)
        self.pgbar.setMinimum(0)
        self.layout.addWidget(self.pgbar)

        main_bt_layout = QHBoxLayout()
        import_bt = QPushButton('Import', self)
        import_bt.clicked.connect(self.add_files)
        main_bt_layout.addWidget(import_bt)
        rename_bt = QPushButton('Rename File', self)
        rename_bt.clicked.connect(self.rename_item)
        main_bt_layout.addWidget(rename_bt)
        delete_bt = QPushButton('Delete File', self)
        delete_bt.clicked.connect(self.delete_item)
        main_bt_layout.addWidget(delete_bt)
        ok_bt = QPushButton('OK', self)
        ok_bt.clicked.connect(self.close)
        main_bt_layout.addWidget(ok_bt)
        self.layout.addLayout(main_bt_layout)

    def populate_list_widget(self):
        # List with checkable names
        self.list_widget.clear()
        self.list_widget.addItems(self.files)

        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)

    def delete_item(self):
        i = self.list_widget.currentRow()
        if i >= 0:  # Assert that an item is selected
            name = self.list_widget.item(i).text()
            self.list_widget.takeItem(i)
            self.files.remove(name)

    # Todo: Double-Clicking renaming not working
    def rename_item(self):
        r = self.list_widget.currentRow()
        item = self.list_widget.currentItem()
        if r >= 0:
            old_name = self.list_widget.item(r).text()
            self.list_widget.editItem(item)
            new_name = self.list_widget.item(r).text()
            repl_ind = self.files.index(old_name)
            self.files[repl_ind] = new_name
            self.paths[new_name] = self.paths[old_name]
            self.file_types[new_name] = self.paths[old_name]

    def get_files_path(self):
        files_list = QFileDialog.getOpenFileNames(self, 'Choose raw-file/s to import', filter='fif-Files(*.fif)')[0]
        if len(files_list) > 0:
            for file_path in files_list:
                p = Path(file_path)
                file = p.stem
                if file not in self.files:
                    self.files.append(file)
                if file not in self.paths:
                    self.paths.update({file: file_path})
                if file not in self.file_types:
                    self.file_types.update({file: p.suffix})
            self.populate_list_widget()
        else:
            pass

    def get_folder_path(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'Choose a folder to import your raw-Files from (including '
                                                             'subfolders)')
        if folder_path != '':
            # create a list of file and sub directories
            # names in the given directory
            list_of_file = os.walk(folder_path)
            # Iterate over all the entries
            for dirpath, dirnames, filenames in list_of_file:
                for full_file in filenames:
                    match = re.search(r'.fif', full_file)
                    if match:
                        file = full_file[:-len(match.group())]
                        if not any(x in full_file for x in ['-eve.', '-epo.', '-ica.', '-ave.', '-tfr.', '-fwd.',
                                                            '-cov.', '-inv.', '-src.', '-trans.', '-bem-sol.']):
                            if file not in self.files:
                                self.files.append(file)
                            if file not in self.paths:
                                self.paths.update({file: join(dirpath, full_file)})
                            if file not in self.file_types:
                                self.file_types.update({file: match.group()})
            self.populate_list_widget()
        else:
            pass

    def add_files(self):
        existing_files = read_files(self.mw.pr.file_list_path)
        existing_erm_files = read_files(self.mw.pr.erm_list_path)
        self.pgbar.setMaximum(len(self.files))
        step = 0
        for fname in self.files:
            forig = self.paths[fname]
            # Make sure every raw-file got it's -raw appendix
            if fname[-4:] == '-raw':
                fdest = join(self.mw.pr.data_path, fname[:-4], fname + self.file_types[fname])
                ermdest = join(self.mw.pr.data_path, 'empty_room_data', fname[:-4], fname + self.file_types[fname])
                fname = fname[:-4]
            else:
                fdest = join(self.mw.pr.data_path, fname, fname + '-raw' + self.file_types[fname])
                ermdest = join(self.mw.pr.data_path, 'empty_room_data', fname, fname + '-raw' + self.file_types[fname])

            # Copy Empty-Room-Files to their directory
            if any(x in fname for x in ['leer', 'Leer', 'erm', 'ERM', 'empty', 'Empty', 'room', 'Room']):
                # Organize ERMs
                if fname not in existing_erm_files:
                    write_file_list(fname, self.mw.pr.erm_list_path)
                # Copy empty-room-files to destination
                move_file(forig, ermdest)
            else:
                # Organize sub_files
                if fname not in existing_files:
                    write_file_list(fname, self.mw.pr.file_list_path)
                # Copy sub_files to destination
                move_file(forig, fdest)
            step += 1
            self.pgbar.setValue(step)
        self.list_widget.clear()
        self.files = list()
        self.paths = dict()
        self.file_types = dict()


def move_folder(src, dst):
    if not isdir(dst):
        print(f'Copying Folder from {src}...')
        shutil.copytree(src, dst)
        print(f'Finished Copying to {dst}')
    else:
        print(f'{dst} already exists')


def get_existing_mri_subjects(subjects_dir):
    existing_mri_subs = list()
    for mri_sub in os.listdir(subjects_dir):
        if 'surf' in os.listdir(join(subjects_dir, mri_sub)):
            existing_mri_subs.append(mri_sub)

    return existing_mri_subs

class AddMRIFiles(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.mw = main_win
        self.layout = QVBoxLayout()

        self.folders = list()
        self.paths = dict()
        self.file_types = dict()

        self.init_ui()
        self.setLayout(self.layout)
        self.open()

    def init_ui(self):
        bt_layout = QHBoxLayout()
        folder_bt = QPushButton('Import 1 FS-Segmentation', self)
        folder_bt.clicked.connect(self.import_mri_subject)
        bt_layout.addWidget(folder_bt)
        folders_bt = QPushButton('Import >1 FS-Segmentations', self)
        folders_bt.clicked.connect(self.import_mri_subjects)
        bt_layout.addWidget(folders_bt)
        self.layout.addLayout(bt_layout)

        list_label = QLabel('These Freesurfer-Segmentations can be imported:', self)
        self.layout.addWidget(list_label)
        self.list_widget = QListWidget(self)
        self.list_widget.itemChanged.connect(self.double_click_rename)
        self.layout.addWidget(self.list_widget)
        self.pgbar = QProgressBar(self)
        self.pgbar.setMinimum(0)
        self.layout.addWidget(self.pgbar)

        main_bt_layout = QHBoxLayout()
        import_bt = QPushButton('Import', self)
        import_bt.clicked.connect(self.add_mri_subjects)
        main_bt_layout.addWidget(import_bt)
        rename_bt = QPushButton('Rename File', self)
        rename_bt.clicked.connect(self.rename_item)
        main_bt_layout.addWidget(rename_bt)
        delete_bt = QPushButton('Delete File', self)
        delete_bt.clicked.connect(self.delete_item)
        main_bt_layout.addWidget(delete_bt)
        ok_bt = QPushButton('OK', self)
        ok_bt.clicked.connect(self.close)
        main_bt_layout.addWidget(ok_bt)
        self.layout.addLayout(main_bt_layout)

    def populate_list_widget(self):
        # List with checkable names
        self.list_widget.clear()
        self.list_widget.addItems(self.folders)

        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)

    def delete_item(self):
        i = self.list_widget.currentRow()
        if i >= 0:
            name = self.list_widget.item(i).text()
            self.list_widget.takeItem(i)
            self.folders.remove(name)

    def rename_item(self):
        i = self.list_widget.currentRow()
        if i >= 0:
            old_name = self.list_widget.item(i).text()
            self.list_widget.edit(i)
            new_name = self.list_widget.item(i).text()
            repl_ind = self.files.index(old_name)
            self.folders[repl_ind] = new_name
            self.paths[new_name] = self.paths[old_name]

    def import_mri_subject(self):
        mri_subjects = get_existing_mri_subjects(self.mw.pr.subjects_dir)
        folder_path = QFileDialog.getExistingDirectory(self, 'Choose a folder with a subject\'s Freesurfe-Segmentation')

        if folder_path != '':
            if 'surf' in os.listdir(folder_path):
                mri_sub = Path(folder_path).name
                if mri_sub not in mri_subjects and mri_sub not in self.folders:
                    self.folders.append(mri_sub)
                    self.paths.update({mri_sub: folder_path})
                    self.populate_list_widget()
                else:
                    print(f'{mri_sub} already existing in <home_path>/Freesurfer')
            else:
                print('Selected Folder doesn\'t seem to be a Freesurfer-Segmentation')

    def import_mri_subjects(self):
        mri_subjects = get_existing_mri_subjects(self.mw.pr.subjects_dir)
        parent_folder = QFileDialog.getExistingDirectory(self, 'Choose a folder containting several '
                                                               'Freesurfer-Segmentations')
        folder_list = os.listdir(parent_folder)

        for mri_sub in folder_list:
            folder_path = join(parent_folder, mri_sub)
            if 'surf' in os.listdir(folder_path):
                if mri_sub not in mri_subjects and mri_sub not in self.folders:
                    self.folders.append(mri_sub)
                    self.paths.update({mri_sub: folder_path})
                else:
                    print(f'{mri_sub} already existing in <home_path>/Freesurfer')
            else:
                print('Selected Folder doesn\'t seem to be a Freesurfer-Segmentation')
        self.populate_list_widget()

    def add_mri_subjects(self):
        self.pgbar.setMaximum(len(self.folders))
        step = 0
        for mri_sub in self.folders:
            src = self.paths[mri_sub]
            dst = join(self.mw.pr.subjects_dir, mri_sub)
            write_file_list(mri_sub, self.mw.pr.mri_sub_list_path)
            move_folder(src, dst)
            step += 1
            self.pgbar.setValue(step)
        self.list_widget.clear()
        self.folders = list()
        self.paths = dict()




def read_sub_dict(sub_dict_path):
    sub_dict = {}
    file_name = Path(sub_dict_path).name
    try:
        with open(sub_dict_path, 'r') as sd:
            for item in sd:
                if ':' in item:
                    key, value = item.split(':', 1)
                    value = value[:-1]
                    sub_dict[key] = value

    except FileNotFoundError:
        print(f'{file_name} not yet created, run add_sub_dict')

    return sub_dict



class SubDictDialog(QDialog):
    def __init__(self, main_win, mode):
        super().__init__(main_win)
        self.main_win = main_win
        self.layout = QGridLayout()
        self.mode = mode
        if mode == 'mri':
            self.setWindowTitle('Assign files to their MRI-Subject')
            self.path2 = main_win.pr.mri_sub_list_path
            self.dict_path = main_win.pr.sub_dict_path
            self.label2 = 'Choose a mri-subject'
        elif mode == 'erm':
            self.setWindowTitle('Assign files to their ERM-File')
            self.path2 = main_win.pr.erm_list_path
            self.dict_path = main_win.pr.erm_dict_path
            self.label2 = 'Choose a erm-file'

        self.init_ui()
        self.open()

    def init_ui(self):
        file_label = QLabel('Choose a file', self)
        second_label = QLabel(self.label2, self)

        self.layout.addWidget(file_label, 0, 0)
        self.layout.addWidget(second_label, 0, 1)
        # ListWidgets
        list_widget1 = QListWidget(self)
        list_widget2 = QListWidget(self)
        with open(self.main_win.pr.file_list_path, 'r') as sl:
            for idx, line in enumerate(sl):
                list_widget1.insertItem(idx, line[:-1])
        with open(self.path2, 'r') as msl:
            for idx, line in enumerate(msl):
                list_widget2.insertItem(idx, line[:-1])

        # Response to Clicking
        list_widget1.itemClicked.connect(partial(sub_dict_selected, list_widget1, list_widget2, self.dict_path))

        self.layout.addWidget(list_widget1, 1, 0)
        self.layout.addWidget(list_widget2, 1, 1)
        # Add buttons
        bt_layout = QVBoxLayout()
        assign_bt = QPushButton('Assign', self)
        assign_bt.clicked.connect(partial(sub_dict_assign, self.dict_path, list_widget1, list_widget2))
        bt_layout.addWidget(assign_bt)

        none_bt = QPushButton('Assign None', self)
        none_bt.clicked.connect(partial(sub_dict_assign_none, self.dict_path, list_widget1))
        bt_layout.addWidget(none_bt)

        all_none_bt = QPushButton('Assign None to all')
        all_none_bt.clicked.connect(partial(sub_dict_assign_all_none, self, self.dict_path, list_widget1))
        bt_layout.addWidget(all_none_bt)

        all_bt = QPushButton('Assign Selected to all')
        all_bt.clicked.connect(partial(sub_dict_assign_to_all, self, self.dict_path, list_widget1, list_widget2))
        bt_layout.addWidget(all_bt)

        read_bt = QPushButton('Read', self)
        read_bt.clicked.connect(partial(read, self.dict_path))
        bt_layout.addWidget(read_bt)

        delete_bt = QPushButton('Delete Last', self)
        delete_bt.clicked.connect(partial(delete_last, self.dict_path))
        bt_layout.addWidget(delete_bt)

        ok_bt = QPushButton('OK', self)
        ok_bt.clicked.connect(self.close)
        bt_layout.addWidget(ok_bt)

        self.layout.addLayout(bt_layout, 0, 2, 2, 1)
        self.setLayout(self.layout)


def sub_dict_selected(inst1, inst2, dict_path):
    choice = inst1.currentItem().text()
    existing_dict = read_sub_dict(dict_path)
    if choice in existing_dict:
        if existing_dict[choice] == 'None':
            # Kind of bulky, improvable
            enable_none_insert = True
            for i in range(inst2.count()):
                if inst2.item(i).text() == 'None':
                    enable_none_insert = False
            if enable_none_insert:
                inst2.addItem('None')
        try:
            it2 = inst2.findItems(existing_dict[choice], Qt.MatchExactly)[0]
            inst2.setCurrentItem(it2)
        except IndexError:
            pass


def sub_dict_assign(dict_path, list_widget1, list_widget2):
    choice1 = list_widget1.currentItem().text()
    choice2 = list_widget2.currentItem().text()
    if not isfile(dict_path):
        with open(dict_path, 'w') as sd:
            sd.write(f'{choice1}:{choice2}\n')
        print(f'{dict_path} created')

    else:
        existing_dict = read_sub_dict(dict_path)
        if choice1 in existing_dict:
            existing_dict[choice1] = choice2
        else:
            existing_dict.update({choice1: choice2})
        with open(dict_path, 'w') as sd:
            for key, value in existing_dict.items():
                sd.write(f'{key}:{value}\n')


def sub_dict_assign_none(dict_path, list_widget1):
    choice = list_widget1.currentItem().text()
    if not isfile(dict_path):
        with open(dict_path, 'w') as sd:
            sd.write(f'{choice}:None\n')
        print(f'{dict_path} created')

    else:
        existing_dict = read_sub_dict(dict_path)
        if choice in existing_dict:
            existing_dict[choice] = None
        else:
            existing_dict.update({choice: None})
        with open(dict_path, 'w') as sd:
            for key, value in existing_dict.items():
                sd.write(f'{key}:{value}\n')


def sub_dict_assign_to_all(inst, dict_path, list_widget1, list_widget2):
    reply = QMessageBox.question(inst, f'Assign None to All?', 'Do you really want to assign none to all?',
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        all_items = dict()
        selected = list_widget2.currentItem().text()
        for i in range(list_widget1.count()):
            all_items.update({list_widget1.item(i).text(): selected})
        with open(dict_path, 'w') as sd:
            for key, value in all_items.items():
                sd.write(f'{key}:{value}\n')


def sub_dict_assign_all_none(inst, dict_path, list_widget1):
    reply = QMessageBox.question(inst, 'Assign None to All?', 'Do you really want to assign none to all?',
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        all_items = dict()
        for i in range(list_widget1.count()):
            all_items.update({list_widget1.item(i).text(): None})
        with open(dict_path, 'w') as sd:
            for key, value in all_items.items():
                sd.write(f'{key}:{value}\n')


def delete_last(dict_path):
    with open(dict_path, 'r') as dl:
        dlist = (dl.readlines())

    with open(dict_path, 'w') as dl:
        for listitem in dlist[:-1]:
            dl.write(str(listitem))


def read(dict_path):
    try:
        with open(dict_path, 'r') as rl:
            print(rl.read())
    except FileNotFoundError:
        print('file not yet created, assign some files')


def read_bad_channels_dict(bad_channels_dict_path):
    bad_channels_dict = {}

    try:
        with open(bad_channels_dict_path, 'r') as bd:
            for item in bd:
                if ':' in item:
                    key, value = item.split(':', 1)
                    value = value[:-1]
                    value = eval(value)
                    for i in value:
                        value[value.index(i)] = 'MEG %03d' % i
                    bad_channels_dict[key] = value

    except FileNotFoundError:
        print('bad_channels_dict.py not yet created, run add_bad_channels_dict')

    return bad_channels_dict


class BadChannelsSelect(QDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.main_win = main_win
        self.setWindowTitle('Assign bad_channels for your files')
        self.file_list_path = self.main_win.pr.file_list_path
        self.bad_dict = read_bad_channels_dict(self.main_win.pr.bad_channels_dict_path)
        self.layout = QGridLayout()
        self.channel_count = 122
        self.bad_chkbts = {}

        self.initui()
        self.open()

    def initui(self):
        listwidget = QListWidget(self)
        self.layout.addWidget(listwidget, 0, 0, self.channel_count // 10, 1)
        with open(self.file_list_path, 'r') as sl:
            for idx, line in enumerate(sl):
                listwidget.insertItem(idx, line[:-1])
                if line[:-1] in self.bad_dict:
                    listwidget.item(idx).setBackground(QColor('green'))
                    listwidget.item(idx).setForeground(QColor('white'))
                else:
                    listwidget.item(idx).setBackground(QColor('red'))
                    listwidget.item(idx).setForeground(QColor('white'))

        # Make Checkboxes for channels
        for x in range(1, self.channel_count + 1):
            ch_name = f'MEG {x:03}'
            chkbt = QCheckBox(ch_name, self)
            self.bad_chkbts.update({ch_name: chkbt})
            r = 0 + (x - 1) // 10
            c = 1 + (x - 1) % 10
            self.layout.addWidget(chkbt, r, c)

        # Response to Clicking
        listwidget.itemClicked.connect(partial(self.bad_dict_selected, listwidget))

        # Add Buttons
        bt_layout = QVBoxLayout()
        assign_bt = QPushButton('Assign', self)
        assign_bt.clicked.connect(partial(self.bad_dict_assign, listwidget))
        bt_layout.addWidget(assign_bt)

        plot_bt = QPushButton('Plot Raw')
        plot_bt.clicked.connect(partial(self.plot_raw_bad, listwidget))
        bt_layout.addWidget(plot_bt)

        ok_bt = QPushButton('OK', self)
        ok_bt.clicked.connect(self.close)
        bt_layout.addWidget(ok_bt)

        self.layout.addLayout(bt_layout, 0, 11, self.channel_count // 10, 1)
        self.setLayout(self.layout)

    def bad_dict_selected(self, listwidget):
        # First clear all entries
        for bt in self.bad_chkbts:
            self.bad_chkbts[bt].setChecked(False)
        # Then load existing bads for choice
        name = listwidget.currentItem().text()
        if name in self.bad_dict:
            for bad in self.bad_dict[name]:
                self.bad_chkbts[bad].setChecked(True)

    def bad_dict_assign(self, listwidget):
        name = listwidget.currentItem().text()
        listwidget.currentItem().setBackground(QColor('green'))
        listwidget.currentItem().setForeground(QColor('white'))
        bad_channels = []
        second_list = []
        for ch in self.bad_chkbts:
            if self.bad_chkbts[ch].isChecked():
                bad_channels.append(ch)
                second_list.append(int(ch[-3:]))
        self.bad_dict.update({name: bad_channels})
        ut.dict_filehandler(name, 'bad_channels_dict', self.main_win.pr.pscripts_path, values=second_list)

    def plot_raw_bad(self, listwidget):
        name = listwidget.currentItem().text()
        raw = io.read_raw(name, join(self.main_win.pr.data_path, name))
        print(f'first: {raw.info["bads"]}')
        # Todo: Make online bad-channel-selection work (mnelab-solution?)
        raw.plot(n_channels=30, bad_color='red',
                 scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1), title=name)
        print(f'second: {raw.info["bads"]}')
        self.bad_dict.update({name: raw.info['bads']})
        for ch in self.bad_dict[name]:
            self.bad_chkbts[ch].setChecked(True)
