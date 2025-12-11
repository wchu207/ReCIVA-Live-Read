import json
import os

from Application import Application
import tkinter as tk


def main():
    config = None
    with open('config.json', 'r') as f:
        config = json.load(f)

    root = tk.Tk()
    root.title('Breath Collection View')
    root.geometry('1600x1200')
    root.minsize(400, 600)
    root.state('zoomed')
    model_path = None
    if 'model_path' in config:
        model_path = config['model_path']

    data_source = None
    if 'data_source' in config:
        data_source = config['data_source']

    app = Application(root, src=data_source, model_path=model_path)
    root.mainloop()

if __name__ == '__main__':
    main()