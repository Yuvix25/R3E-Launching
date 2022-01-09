from distutils.core import setup
import py2exe, sys


sys.argv.append('py2exe')

setup(
    options = {'py2exe': {'bundle_files': 1, 'compressed': True}},
    windows = [{
        'script': 'R3E_Launching.py',
        'icon_resources': [(1, 'timer.ico')],
        'dest_base' : 'test',
        }],
    zipfile = None,
)