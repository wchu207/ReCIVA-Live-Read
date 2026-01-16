import json
import os

from Application import Application
import tkinter as tk

from multiprocessing import freeze_support



def main():
    config = None
    freeze_support()
    with open('config.json', 'r') as f:
        config = json.load(f)

    root = tk.Tk()
    root.title('Breath Collection View')
    root.geometry('1600x1200')
    root.minsize(400, 600)
    model_path = None
    if 'model_path' in config:
        model_path = config['model_path']

    data_source = None
    if 'data_source' in config:
        data_source = config['data_source']

    out_dir = 'Output'
    if 'output_directory' in config:
        out_dir = config['output_directory']

    app = Application(root, src=data_source, model_path=model_path, output_directory = out_dir)
    root.mainloop()

if __name__ == '__main__':
    main()