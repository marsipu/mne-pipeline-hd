import sys

# specify the path to a general analysis folder according to your OS
if sys.platform == 'win32':
    home_path = 'Z:/Promotion'  # Windows-Path
elif sys.platform == 'linux':
    home_path = '/mnt/z/Promotion'  # Linux-Path
elif sys.platform == 'darwin':
    home_path = 'Users/'  # Mac-Path
else:
    home_path = 'Z:/Promotion'  # other OS

project_name = 'my_project'  # specify the name for your project as a folder
