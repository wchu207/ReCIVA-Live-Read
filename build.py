import PyInstaller.__main__
import os, shutil

if os.path.isdir('dist/BreathCollectionLiveView'):
    shutil.rmtree('dist/BreathCollectionLiveView')

PyInstaller.__main__.run([
    'main.py',
    '--windowed',
    '--hidden-import=\'PIL._tkinter._finder\'',
    '--exclude-module=PyQt5',
    '--name=BreathCollectionLiveView'
])

shutil.copyfile('config.json', 'dist/BreathCollectionLiveView/config.json')
shutil.copyfile('model.pkl', 'dist/BreathCollectionLiveView/model.pkl')
