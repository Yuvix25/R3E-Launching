from distutils.core import setup
import py2exe, sys, shutil


sys.argv.append('py2exe')
NAME = 'R3E_Launching'


setup(
    options = {'py2exe': {
        'bundle_files': 1,
        'compressed': True,
        'dist_dir' : NAME
    }},
    windows = [{
        'script': 'R3E_Launching.py',
        'icon_resources': [(1, 'timer.ico')],
        'dest_base' : NAME,
        }],
    zipfile = None,
)

shutil.copyfile('timer.ico', NAME + '/timer.ico')