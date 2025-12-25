import json
import tkinter as tk
from tkinter import ttk

from DataWindow import DataWindow
from FileWindow import FileWindow
import _pickle as pickle

class Application(ttk.PanedWindow):
    def __init__(self, master=None, src=None, model_path=None):
        ttk.Style().configure('Sash', sashthickness=6)
        super().__init__(master=master, orient='horizontal')

        self.model = None
        if model_path is not None:
            with open(model_path, "rb") as file:
                try:
                    self.model = pickle.load(file)
                except:
                    pass

        self.colors_map = {
            'Flow rate L upstream': '#ff7f0e',
            'Flow rate L downstream': '#2ca02c',
            'Temperature L upstream': '#d62728',
            'Temperature L downstream': '#9467bd',
            'Pressure L upstream': '#8c564b',
            'Pressure L downstream': '#e377c2',
            'CO2stream': '#7f7f7f',
            'Mask pressure': '#bcbd22'
        }

        self.root = master
        self.grid(row=0, column=0, sticky=tk.NSEW)

        if master is not None:
            master.grid_rowconfigure(0, weight=1)
            master.grid_columnconfigure(0, weight=1)

        self.left_panes = DataWindow(self, src, self.model, self.colors_map)
        self.right_panes = FileWindow(self, self.model, self.colors_map)

        self.add(self.left_panes, weight=3)
        self.add(self.right_panes, weight=1)

        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def get_plot_params(self):
        plot_params = None
        with open('config.json', 'r') as f:
            p = json.load(f)
            if 'plot_params' in p:
                plot_params = p['plot_params']
        return plot_params

    def get_targets(self):
        return self.left_panes.targets

    def close(self):
        self.left_panes.close()
        self.root.quit()
        self.root.destroy()


    def run(self):
        self.root.mainloop()
