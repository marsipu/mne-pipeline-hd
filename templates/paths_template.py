import sys

# specify the path to a general analysis folder according to your OS
if sys.platform == 'win32':
    home_path = 'Z:/MNE-Analyse'  # Windows-Path
elif sys.platform == 'linux':
    home_path = '/mnt/z/MNE-Analyse'  # Linux-Path
elif sys.platform == 'darwin':
    home_path = 'Users/MNE-Analyse'  # Mac-Path
else:
    home_path = 'Z:/Promotion'  # other OS

# specify the name of your project (will be a folder in home_path)
project_name = 'my_project'
