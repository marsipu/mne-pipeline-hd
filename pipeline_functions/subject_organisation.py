"""
subject_organisation by Martin Schulz
martin.schulz@stud.uni-heidelberg.de
"""
import os
import shutil
from os.path import join, isfile, exists
from . import io_functions as io
from . import operations_functions as op
from . import utilities as ut
import tkinter as t
import re


## Subjects
def add_subjects(sub_list_path, erm_list_path, motor_erm_list_path,
                 home_path, project_name, data_path, figures_path,
                 subjects_dir, orig_data_path, gui=False):
    
    subjects = read_subjects(sub_list_path)
    erm_files = read_subjects(erm_list_path)
    motor_erm_files = read_subjects(motor_erm_list_path)
    op.populate_data_directory_small(home_path, project_name, data_path, figures_path,
                           subjects_dir, subjects)
    
    all_files, paths = ut.getallfifFiles(orig_data_path)
    
    #Regular-Expressions Pattern
    pattern = r'pp[0-9][0-9]*[a-z]*_[0-9]{0,3}t?_[a,b]$'
    
    for f in all_files:
        fname = f[:-4]
        fdest = join(data_path, fname, fname + '-raw.fif')
        ermdest = join(data_path, 'empty_room_data', fname + '-raw.fif')
        
        match = re.match(pattern, fname)
        
        # Copy Empty-Room-Files to their directory
        if 'leer' in fname:
            if not isfile(ermdest):
                print('-'*60 + '\n' + fname)
                print(f'Copying ERM_File from {paths[f]}')
                shutil.copy2(paths[f], ermdest)
                print(f'Finished Copying to {ermdest}')
            # Organize Motor-ERMs
            if 'motor_leer' in fname:            
                if not fname in motor_erm_files:
                    if not isfile(motor_erm_list_path):
                        print('-'*60 + '\n' + fname)
                        if not exists(join(data_path, '_Subject_scripts')):
                            os.makedirs(join(data_path, '_Subject_scripts'))
                            print(join(data_path, '_Subject_scripts created'))
                            
                        with open(motor_erm_list_path, 'w') as el1:
                            el1.write(fname + '\n')
                        print('motor_erm_list.py created') 
                        print(f'{fname} was automatically added to motor_erm_list from {orig_data_path}')    
                    else:
                        print('-'*60 + '\n' + fname)
                        with open(motor_erm_list_path, 'a') as sl2:
                            sl2.write(fname + '\n')
                        print(f'{fname} was automatically added to motor_erm_list from {orig_data_path}')
            # Organize ERMs
            else:
                if not fname in erm_files:
                    if not isfile(erm_list_path):
                        print('-'*60 + '\n' + fname)
                        if not exists(join(data_path, '_Subject_scripts')):
                            os.makedirs(join(data_path, '_Subject_scripts'))
                            print(join(data_path, '_Subject_scripts created'))
                            
                        with open(erm_list_path, 'w') as el1:
                            el1.write(fname + '\n')
                        print('erm_list.py created') 
                        print(f'{fname} was automatically added to erm_list from {orig_data_path}')    
                    else:
                        print('-'*60 + '\n' + fname)
                        with open(erm_list_path, 'a') as sl2:
                            sl2.write(fname + '\n')
                        print(f'{fname} was automatically added to erm_list from {orig_data_path}')                    


        elif match:       
            # Organize sub_files
            if not fname in subjects:
                if not isfile(sub_list_path):
                    print('-'*60 + '\n' + fname)
                    if not exists(join(data_path, '_Subject_scripts')):
                        os.makedirs(join(data_path, '_Subject_scripts'))
                        print(join(data_path, '_Subject_scripts created'))
                        
                    with open(sub_list_path, 'w') as sl1:
                        sl1.write(fname + '\n')
                    print('sub_list.py created') 
                    print(f'{fname} was automatically added to sub_list from {orig_data_path}')
                    
                else:
                    print('-'*60 + '\n' + fname)
                    with open(sub_list_path, 'a') as sl2:
                        sl2.write(fname + '\n')
                print(f'{fname} was automatically added to sub_list from {orig_data_path}')
    
            # Copy sub_files to destination
            if not isfile(fdest):
                subjects = read_subjects(sub_list_path)
                op.populate_data_directory_small(home_path, project_name, data_path, figures_path,
                                                 subjects_dir, subjects)
                
                print(f'Copying File from {paths[f]}...')
                shutil.copy2(paths[f], fdest)
                print(f'Finished Copying to {fdest}')    
            
            
    if gui == True:
        def add_to_list():
            if not isfile(sub_list_path):
                if not exists(join(data_path, '_Subject_scripts')):
                    os.makedirs(join(data_path, '_Subject_scripts'))
                ilist = []
                ilist.append(e1.get())
                e1.delete(0,t.END)
                with open(sub_list_path, 'w') as sl:
                    for listitem in ilist:
                        sl.write('%s\n' % listitem)
                print('sub_list.py created')
    
            else:
                elist = []
                elist.append(e1.get())
                e1.delete(0,t.END)
                with open(sub_list_path, 'a') as sl:
                    for listitem in elist:
                        sl.write('%s\n' % listitem)
    
        def delete_last():
            with open(sub_list_path, 'r') as dl:
                dlist = (dl.readlines())
    
            with open(sub_list_path, 'w') as dl:
                for listitem in dlist[:-1]:
                    dl.write('%s' % listitem)
    
        def quittk():
            master.quit()
            master.destroy()
    
        def readl():
            try:
                with open(sub_list_path, 'r') as rl:
                    print(rl.read())
            except FileNotFoundError:
                print('sub_list.py not yet created, run add_subjects')
    
        def pop_dir():
    
            subjects = read_subjects(sub_list_path)
            op.populate_data_directory_small(home_path, project_name, data_path, figures_path,
                                       subjects_dir, subjects)
    
        master = t.Tk()
        t.Label(master, text='Subject(Filename without .fif)').grid(row=0, column=0)
    
        e1 = t.Entry(master)
        e1.grid(row=0, column=1)
    
        t.Button(master, text='read', command=readl).grid(row=1, column=0)
        t.Button(master, text='delete_last', command=delete_last).grid(row=1, column=1)
        t.Button(master, text='add', command=add_to_list).grid(row=1, column=2)
        t.Button(master, text='populate_dir', command=pop_dir).grid(row=1, column=3)
        t.Button(master, text='quit', command=quittk).grid(row=1, column=4)
    
        t.mainloop()


def read_subjects(sub_list_path):

    sub_list = []

    try:
        with open(sub_list_path, 'r') as sl:
            for line in sl:
                currentPlace = line[:-1]
                sub_list.append(currentPlace)

    except FileNotFoundError:
        print(f'{sub_list_path} not yet created, add subject')

    return sub_list

##MRI-Subjects
def add_mri_subjects(mri_sub_list_path, data_path):

    def add_to_list():
        if not isfile(mri_sub_list_path):
            if not exists(join(data_path, '_Subject_scripts')):
                os.makedirs(join(data_path, '_Subject_scripts'))
            ilist = []
            ilist.append(e1.get())
            e1.delete(0,t.END)
            with open(mri_sub_list_path, 'w') as sl:
                for listitem in ilist:
                    sl.write('%s\n' % listitem)

            print('mri_sub_list.py created')

        else:
            elist = []
            elist.append(e1.get())
            e1.delete(0,t.END)
            with open(mri_sub_list_path, 'a') as sl:
                for listitem in elist:
                    sl.write('%s\n' % listitem)

    def delete_last():
        with open(mri_sub_list_path, 'r') as dl:
            dlist = (dl.readlines())

        with open(mri_sub_list_path, 'w') as dl:
            for listitem in dlist[:-1]:
                dl.write('%s' % listitem)

    def quittk():
        master.quit()
        master.destroy()

    def readl():
        try:
            with open(mri_sub_list_path, 'r') as rl:
                print(rl.read())
        except FileNotFoundError:
            print('mri_sub_list.py not yet created, run add_mri_subjects')

    master = t.Tk()
    t.Label(master, text='MRI-Subject(Foldername in SUBJECTS_DIR)').grid(row=0, column=0)

    e1 = t.Entry(master)
    e1.grid(row=0, column=1)

    t.Button(master, text='read', command=readl).grid(row=1, column=0)
    t.Button(master, text='delete_last', command=delete_last).grid(row=1, column=1)
    t.Button(master, text='add', command=add_to_list).grid(row=1, column=2)
    t.Button(master, text='quit', command=quittk).grid(row=1, column=3)

    t.mainloop()




def read_mri_subjects(mri_sub_list_path):

    mri_sub_list = []

    try:
        with open(mri_sub_list_path, 'r') as sl:
            for line in sl:
                currentPlace = line[:-1]
                mri_sub_list.append(currentPlace)

    except FileNotFoundError:
        print('mri_sub_list.py not yet created, add mri_subject')

    return mri_sub_list

##Subject-Dict
def add_sub_dict(sub_dict_path, sub_list_path, data_path):

    def assign_sub():
        choice=listbox.get(listbox.curselection())
        if not isfile(sub_dict_path):
            if not exists(join(data_path, '_Subject_scripts')):
                os.makedirs(join(data_path, '_Subject_scripts'))
            idict = {}
            idict.update({choice:e2.get()})
            e2.delete(0,t.END)
            with open(sub_dict_path, 'w') as sd:
                for key, value in idict.items():
                    sd.write('%s:%s\n' % (key, value))

            print('sub_dict.py created')

        else:
            edict = {}
            edict.update({choice:e2.get()})
            e2.delete(0,t.END)
            with open(sub_dict_path, 'a') as sd:
                for key, value in edict.items():
                    sd.write('%s:%s\n' % (key, value))

    def delete_last():
        with open(sub_dict_path, 'r') as dd:
            dlist = (dd.readlines())

        with open(sub_dict_path, 'w') as dd:
            for listitem in dlist[:-1]:
                dd.write('%s' % listitem)

    def quittk():
        master.quit()
        master.destroy()

    def readd():
        try:
            with open(sub_dict_path, 'r') as rd:
                print(rd.read())
        except FileNotFoundError:
            print('sub_dict.py not yet created, run add_sub_dict')

    master = t.Tk()
    t.Label(master, text='Assign Subject to MRI-Subject').pack(side=t.TOP)

    e2 = t.Entry(master, width=100)
    e2.pack(side=t.TOP, expand=True)

    scrollbar = t.Scrollbar(master)
    scrollbar.pack(side=t.LEFT, fill = t.Y)

    listbox = t.Listbox(master, height=20, selectmode = 'SINGLE', yscrollcommand = scrollbar.set)
    listbox.pack(side=t.LEFT, expand=True)

    scrollbar.config(command=listbox.yview)


    with open(sub_list_path, 'r') as sl:
        for line in sl:
            currentPlace = line[:-1]
            listbox.insert(t.END, currentPlace)

    t.Button(master, text='read', command=readd).pack()
    t.Button(master, text='delete_last', command=delete_last).pack()
    t.Button(master, text='assign', command=assign_sub).pack()
    t.Button(master, text='quit', command=quittk).pack()


    t.mainloop()
def read_sub_dict(sub_dict_path):
    sub_dict = {}

    try:
        with open(sub_dict_path, 'r') as sd:
            for item in sd:
                if ':' in item:
                    key,value = item.split(':', 1)
                    value = value[:-1]
                    sub_dict[key]=value

    except FileNotFoundError:
        print('sub_dict.py not yet created, run add_sub_dict')

    return sub_dict

## empty_room_data

def add_erm_dict(erm_dict_path, sub_list_path, data_path):

    def assign_erm():
        choice=listbox.get(listbox.curselection())
        if not isfile(erm_dict_path):
            if not exists(join(data_path, '_Subject_scripts')):
                os.makedirs(join(data_path, '_Subject_scripts'))
            idict = {}
            idict.update({choice:e2.get()})
            e2.delete(0,t.END)
            with open(erm_dict_path, 'w') as sd:
                for key, value in idict.items():
                    sd.write('%s:%s\n' % (key, value))

            print('erm_dict.py created')

        else:
            edict = {}
            edict.update({choice:e2.get()})
            e2.delete(0,t.END)
            with open(erm_dict_path, 'a') as sd:
                for key, value in edict.items():
                    sd.write('%s:%s\n' % (key, value))

    def delete_last():
        with open(erm_dict_path, 'r') as dd:
            dlist = (dd.readlines())

        with open(erm_dict_path, 'w') as dd:
            for listitem in dlist[:-1]:
                dd.write('%s' % listitem)

    def quittk():
        master.quit()
        master.destroy()

    def readd():
        try:
            with open(erm_dict_path, 'r') as rd:
                print(rd.read())
        except FileNotFoundError:
            print('erm_dict.py not yet created, run add_erm_dict')

    master = t.Tk()
    t.Label(master, text='Assign ERM to Subject').pack(side=t.TOP)

    e2 = t.Entry(master, width=100)
    e2.pack(side=t.TOP, expand=True)

    scrollbar = t.Scrollbar(master)
    scrollbar.pack(side=t.LEFT, fill = t.Y)

    listbox = t.Listbox(master, height=20, selectmode = 'SINGLE', yscrollcommand = scrollbar.set)
    listbox.pack(side=t.LEFT, expand=True)

    scrollbar.config(command=listbox.yview)


    with open(sub_list_path, 'r') as sl:
        for line in sl:
            currentPlace = line[:-1]
            listbox.insert(t.END, currentPlace)

    t.Button(master, text='read', command=readd).pack()
    t.Button(master, text='delete_last', command=delete_last).pack()
    t.Button(master, text='assign', command=assign_erm).pack()
    t.Button(master, text='quit', command=quittk).pack()


    t.mainloop()

def read_erm_dict(erm_dict_path):
    erm_dict = {}

    try:
        with open(erm_dict_path, 'r') as sd:
            for item in sd:
                if ':' in item:
                    key,value = item.split(':', 1)
                    value = value[:-1]
                    erm_dict[key]=value

    except FileNotFoundError:
        print('erm_dict.py not yet created, run add_erm_dict')

    return erm_dict


## bad_channels_dict

def add_bad_channels_dict(bad_channels_dict_path, sub_list_path,
                          erm_list_path, motor_erm_list_path,
                          data_path, predefined_bads):

    def check():
        
        for x in var_dict:
            n = var_dict[x].get()
            if n == 1:
                print(x)
    
    def assign_bad_channels():
        
        name = listbox.get(listbox.curselection())
        listbox.itemconfig(listbox.curselection(), {'bg':'green', 'fg':'white'})
        b_list = []
        for x in var_dict:
            n = var_dict[x].get()
            if n == 1:
                b_list.append(x)
        
        if not isfile(bad_channels_dict_path):
            if not exists(join(data_path, '_Subject_scripts')):
                os.makedirs(join(data_path, '_Subject_scripts'))

            with open(bad_channels_dict_path, 'w') as bd:
                bd.write(f'{name}:{b_list}\n')

            print('bad_channels_dict.py created')

        else:
            b_dict = {}
            with open(bad_channels_dict_path) as bd:
                for i in bd:
                    key,value = i.split(':',1)
                    value = value[:-1]
                    value = eval(value)
                    b_dict.update({key:value})
                
            if name in b_dict:
                if b_dict[name] == b_list:
                    print(f'Same Bad-Channels as before, nothing changed for {name}')
                else:
                    b_dict[name] = b_list
                    print(f'Bad-Channels changed for {name}')
                    
                    with open(bad_channels_dict_path, 'w') as bd:
                        for k in b_dict:
                            bd.write(f'{k}:{b_dict[k]}\n')
        
            else:
                with open(bad_channels_dict_path, 'a') as bd:
                    bd.write(f'{name}:{b_list}\n')
                    print(f'Bad-Channels added for {name}')


    def delete_last():
        with open(bad_channels_dict_path, 'r') as dd:
            dlist = (dd.readlines())

        with open(bad_channels_dict_path, 'w') as dd:
            for listitem in dlist[:-1]:
                dd.write('%s' % listitem)

    def quittk():
        master.quit()
        master.destroy()

    def readd():
        try:
            with open(bad_channels_dict_path, 'r') as rd:
                print(rd.read())
        except FileNotFoundError:
            print('bad_channels_dict.py not yet created, press assign')

    def plot_raw_tk():
        name = listbox.get(listbox.curselection())
        
        if 'leer' in name or 'ruhe' in name:
            save_dir = join(data_path, 'empty_room_data')
        else:
            save_dir = join(data_path, name)
        
        raw = io.read_raw(name, save_dir)
        try:
            bad_channels_dict = read_bad_channels_dict(bad_channels_dict_path)
            bad_channels = bad_channels_dict[name]
            raw.info['bads'] = bad_channels

            try:
                raw.plot(title=name, bad_color='red',
                         scalings=dict(mag=1e-12, grad =4e-11, eeg='auto', stim=1),
                         n_channels=32)
            except ValueError: #No EEG-Channel
                raw.plot(title=name, bad_color='red',
                         scalings=dict(mag=1e-12, grad =4e-11, stim=1),
                         n_channels=32)
        except (FileNotFoundError, KeyError):
            predef_bads = []
            for i in predefined_bads:
                predef_bads.append('MEG %03d' % i)
            raw.info['bads'] = predef_bads
            print('Plot predefined_bads')
            try:
                raw.plot(title=name, bad_color='red',
                         scalings=dict(mag=1e-12, grad =4e-11, eeg='auto', stim=1),
                         n_channels=32)
            except ValueError: #No EEG-Channel
                raw.plot(title=name, bad_color='red',
                         scalings=dict(mag=1e-12, grad =4e-11, stim=1),
                         n_channels=32)

    def listselect(evt):
        w = evt.widget
        index = int(w.curselection()[0])
        name = w.get(index)

        #Clear all entries
        for x in var_dict:
            var_dict[x].set(0)

        bad_channels_dict = read_bad_channels_dict(bad_channels_dict_path)        
        try:
            bad_channels = bad_channels_dict[name]
            
            #Check existing bad_channels
            for bc in bad_channels:
                number = int(bc[-3:])
                var_dict[number].set(1)
                
        except KeyError:
            # Set predefined_bads for new
            for number in predefined_bads:
                var_dict[number].set(1)
            print('Set predefinded bads, nothing assigned')
        


               
    # Create TkinterWidget
    master = t.Tk()

    master.title('Assign bad_channels')

    scrollbar = t.Scrollbar(master)
    scrollbar.grid(row=0, column=0, rowspan=14, sticky=t.NS)

    listbox = t.Listbox(master, height=20, selectmode = 'SINGLE', yscrollcommand = scrollbar.set)
    listbox.grid(row=0, column=1, rowspan=14)
    
    listbox.bind('<<ListboxSelect>>', listselect)
    
    scrollbar.config(command=listbox.yview)

    bad_channels_dict = read_bad_channels_dict(bad_channels_dict_path)     
    # Add entries for subjects and erm_files
    with open(sub_list_path, 'r') as sl:
        for line in sl:
            currentPlace = line[:-1]
            listbox.insert(t.END, currentPlace)
            if currentPlace in bad_channels_dict:
                listbox.itemconfig(listbox.size()-1, {'bg':'green', 'fg':'white'})
            else:
                listbox.itemconfig(listbox.size()-1, {'bg':'red', 'fg':'white'})
                
    with open(erm_list_path, 'r') as el:
        for line in el:
            currentPlace = line[:-1]
            listbox.insert(t.END, currentPlace)
            if currentPlace in bad_channels_dict:
                listbox.itemconfig(listbox.size()-1, {'bg':'green', 'fg':'white'})
            else:
                listbox.itemconfig(listbox.size()-1, {'bg':'red', 'fg':'white'})
                
    with open(motor_erm_list_path, 'r') as el:
        for line in el:
            currentPlace = line[:-1]
            listbox.insert(t.END, currentPlace)
            if currentPlace in bad_channels_dict:
                listbox.itemconfig(listbox.size()-1, {'bg':'green', 'fg':'white'})
            else:
                listbox.itemconfig(listbox.size()-1, {'bg':'red', 'fg':'white'})
                
    # Add Checkbuttons for each channel
    var_dict = {} 
    for x in range(1,123):      
        var = t.IntVar()
        var_dict.update({x:var})
        chk = t.Checkbutton(master, text=x, variable=var)
        r = 1 + (x-1)//10
        c = 2 + (x-1)%10
        chk.grid(row=r, column=c)


    t.Button(master, text='read', command=readd).grid(row=0, column=2, columnspan=2)
    t.Button(master, text='delete_last', command=delete_last).grid(row=0, column=4, columnspan=2)
    t.Button(master, text='plot_raw', command=plot_raw_tk).grid(row=0, column=6, columnspan=2)
    t.Button(master, text='assign', command=assign_bad_channels).grid(row=0, column=8, columnspan=2)
    t.Button(master, text='quit', command=quittk).grid(row=0, column=10, columnspan=2)


    t.mainloop()

def read_bad_channels_dict(bad_channels_dict_path):
    bad_channels_dict = {}

    try:
        with open(bad_channels_dict_path, 'r') as bd:
            for item in bd:
                if ':' in item:
                    key,value = item.split(':', 1)
                    value = value[:-1]
                    value = eval(value)
                    for i in value:
                        value[value.index(i)] = 'MEG %03d' % i
                    bad_channels_dict[key]=value

    except FileNotFoundError:
        print('bad_channels_dict.py not yet created, run add_bad_channels_dict')

    return bad_channels_dict


## bad_channels_dict

def add_sub_cond_dict(bad_channels_dict_path, sub_list_path, data_path):


    def assign_condition():
        choice=listbox.get(listbox.curselection())
        if not isfile(bad_channels_dict_path):
            if not exists(join(data_path, '_Subject_scripts')):
                os.makedirs(join(data_path, '_Subject_scripts'))
            idict = {}
            idict.update({choice:e2.get()})
            e2.delete(0,t.END)
            with open(bad_channels_dict_path, 'w') as sd:
                for key, value in idict.items():
                    sd.write('%s:%s\n' % (key, value))

            print('bad_channels_dict.py created')

        else:
            edict = {}
            edict.update({choice:e2.get()})
            e2.delete(0,t.END)
            with open(bad_channels_dict_path, 'a') as sd:
                for key, value in edict.items():
                    sd.write('%s:%s\n' % (key, value))

    def delete_last():
        with open(bad_channels_dict_path, 'r') as dd:
            dlist = (dd.readlines())

        with open(bad_channels_dict_path, 'w') as dd:
            for listitem in dlist[:-1]:
                dd.write('%s' % listitem)

    def quittk():
        master.quit()
        master.destroy()

    def readd():
        try:
            with open(bad_channels_dict_path, 'r') as rd:
                print(rd.read())
        except FileNotFoundError:
            print('bad_channels_dict.py not yet created, press assign')

    def plot_raw_tk():
        choice=listbox.get(listbox.curselection())
        name = choice
        save_dir = join(data_path, choice)
        raw = io.read_raw(name, save_dir)
        raw.plot(title=name, bad_color='red', scalings=dict(mag=1e-12, grad=4e-11, eeg=20e-5, stim=1), block=True, n_channels=30)


    master = t.Tk()

    t.Label(master, text='Assign bad channels to Subject').pack(side=t.TOP)


    e2 = t.Entry(master, width=100)
    e2.pack(side=t.TOP, expand=True)

    scrollbar = t.Scrollbar(master)
    scrollbar.pack(side=t.LEFT, fill = t.Y)

    listbox = t.Listbox(master, height=20, selectmode = 'SINGLE', yscrollcommand = scrollbar.set)
    listbox.pack(side=t.LEFT, expand=True)

    scrollbar.config(command=listbox.yview)


    with open(sub_list_path, 'r') as sl:
        for line in sl:
            currentPlace = line[:-1]
            listbox.insert(t.END, currentPlace)


    t.Button(master, text='read', command=readd).pack()
    t.Button(master, text='delete_last', command=delete_last).pack()
    t.Button(master, text='plot_raw', command=plot_raw_tk).pack()
    t.Button(master, text='assign', command=assign_condition).pack()
    t.Button(master, text='quit', command=quittk).pack()


    t.mainloop()

def read_sub_cond_dict(bad_channels_dict_path):
    bad_channels_dict = {}

    try:
        with open(bad_channels_dict_path, 'r') as sd:
            for item in sd:
                if ':' in item:
                    key,value = item.split(':', 1)
                    value = value[:-1]
                    value = value.split(',')
                    if '' in value and len(value)==1:
                        bad_channels_dict[key]=[]
                        print('for {} no bad_channels assigned'.format(key))
                    elif '' in value and len(value)!=1:
                        raise ValueError('There is a mistake in the bad_channels_dict value')
                    else:
                        bad_channels_dict[key]=value

    except FileNotFoundError:
        print('sub_cond_dict.py not yet created, run add_sub_cond_dict')

    return bad_channels_dict


def file_selection(which_file, all_subjects):
    # Turn string input into according sub_list-Index
    try:
        if which_file == 'all':
            run = range(0,len(all_subjects))
        
        elif ',' in which_file and '-' in which_file:
            z = which_file.split(',')
            run = []
            for i in z:
                if '-' in i:
                    x,y = i.split('-')
                    for n in range(int(x)-1,int(y)):
                        run.append(n)
                else:
                    run.append(int(i)-1)              
        
        elif '-' in which_file and ',' not in which_file:
            x,y = which_file.split('-')
            run = range(int(x)-1,int(y))
            
        elif ',' in which_file and '-' not in which_file:
            run = which_file.split(',')
            for i in run:
                run[run.index(i)] = int(i)-1
            
        else:
            run = [int(which_file)-1]
        
        subjects = [x for (i,x) in enumerate(all_subjects) if i in run]
        
        return subjects
    
    except TypeError:
        raise TypeError('{} is not a string(enclosed by quotes)'.format(which_file))
    
    except ValueError:
        raise ValueError('{} is not a whole number'.format(which_file))

def mri_subject_selection(which_mri_subject, all_mri_subjects):
    # Turn string input into according mri_sub_list-Index
    try:
        if which_mri_subject == 'all':
            run = range(0,len(all_mri_subjects))
        
        elif ',' in which_mri_subject and '-' in which_mri_subject:
            z = which_mri_subject.split(',')
            run = []
            for i in z:
                if '-' in i:
                    x,y = i.split('-')
                    for n in range(int(x)-1,int(y)):
                        run.append(n)
                else:
                    run.append(int(i)-1)
                    
        elif '-' in which_mri_subject and ',' not in which_mri_subject:
            x,y = which_mri_subject.split('-')
            run = range(int(x)-1,int(y))
            
        elif ',' in which_mri_subject and '-' not in which_mri_subject:
            run = which_mri_subject.split(',')
            for i in run:
                run[run.index(i)] = int(i)-1
            
        else:
            run = [int(which_mri_subject)-1]
            
        mri_subjects = [x for (i,x) in enumerate(all_mri_subjects) if i in run]
    
        return mri_subjects
  
    except TypeError:
        raise TypeError('{} is not a string(enclosed by quotes)'.format(which_mri_subject))
    
    except ValueError:
        raise ValueError('{} is not a whole number'.format(which_mri_subject))
