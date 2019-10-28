import sys

# specify the path to a general analysis folder according to your OS
if sys.platform == 'win32':
    # home_path = 'Z:/Promotion'  # Windows-Path
    home_path = 'D:/Rächner/Desktop/Pinprick-Offline'
elif sys.platform == 'linux':
    home_path = '/mnt/z/Promotion'  # Linux-Path
elif sys.platform == 'darwin':
    home_path = 'Users/'  # Mac-Path
else:
    home_path = 'Z:/Promotion'  # some other path

project_name = 'Pin-Prick-Projekt'  # specify the name for your project as a folder