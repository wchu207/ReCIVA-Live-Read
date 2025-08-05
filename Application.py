import tkinter as tk

import h5py
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import filedialog
from datetime import datetime
import lightgbm

from LiveH5Reader import LiveH5Reader
from LivePlot import LivePlot
from LiveTextView import LiveTextView
import os
import _pickle as pickle

from preprocessing import ReCIVA_log_preprocessor


class Application(tk.Frame):
    def __init__(self, master=None, dir=None, model_path=None):
        super().__init__(master=master)
        self.root = master
        self.grid(row=0, column=0, sticky=tk.NSEW)

        if master is not None:
            master.grid_rowconfigure(0, weight=1)
            master.grid_columnconfigure(0, weight=1)

        self.targets = []

        self.file_path = None
        self.file = None
        self.reader = None
        self.canvas = None
        self.toolbar = None
        self.liveplot = None
        self.liveplot_canvas = None
        self.pump_active_flag = None
        self.pump_active_prev_val = None

        self.livetext = LiveTextView(self)

        self.colors_map = {
            'Accumulated volume L': '#1f77b4',
            'Flow rate L upstream': '#ff7f0e',
            'Flow rate L downstream': '#2ca02c',
            'Temperature L upstream': '#d62728',
            'Temperature L downstream': '#9467bd',
            'Pressure L upstream': '#8c564b',
            'Pressure L downstream': '#e377c2',
            'CO2stream': '#7f7f7f',
            'Mask pressure': '#bcbd22',
            'Pump L current': '#17becf'
        }

        self.dir = dir
        self.create_controls()
        self.canvas_frame = tk.Frame(self)
        self.canvas_frame.grid(row=0, column=0, columnspan=3, sticky=tk.NSEW)
        self.pump_active_flag = tk.BooleanVar(self, value=False)
        if self.dir is not None:
            self.select_and_open_file()
            self.draw_plot()
        else:
            self.livetext.add('Error source_directory not found in config.json')

        self.model = None
        if model_path is not None:
            with open(model_path, "rb") as file:
                self.model = pickle.load(file)
        else:
            self.livetext.add('Warning model_path not found in config.json')

        self.preprocessor = ReCIVA_log_preprocessor()

        self.livetext.grid(row=1, column=2, sticky=tk.NSEW)

        self.pump_active_flag.trace('w', self.pump_changed)
        self.pump_active_prev_val = False

        self.pump_active_text = tk.Text(self, font=('utopia', 18), bg='red', height=4, width=10)
        self.pump_active_text.tag_configure('center', justify='center')
        self.pump_active_text.insert('1.0', '\n\nPump Inactive', 'center')
        self.pump_active_text.grid(row=1, column=0, sticky=tk.NSEW)

        self.grid_rowconfigure(0, weight=8)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=4)
        self.root.after(100, self.poll_logs)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def draw_plot(self):
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.toolbar.destroy()
        if self.file_path is not None:
            self.liveplot = self.create_plot_from_file(self.file)
            self.canvas = FigureCanvasTkAgg(master=self.canvas_frame, figure=self.liveplot.get_figure())
            self.canvas.get_tk_widget().pack(expand=True, fill='both')
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.canvas_frame)

    def create_plot_from_file(self, file):
        if self.reader is not None:
            self.reader.terminate()
        self.reader = LiveH5Reader(file, self.targets, current_flag=self.pump_active_flag)
        self.livetext.clear()
        self.livetext.add_all(self.reader.read_all_logs())
        self.livetext.text.yview(tk.END)
        lp = LivePlot('Collection time', self.targets, self.colors_map)
        lp.initial_data(self.reader.read_all_data())
        lp.read(self.reader.read_data())
        return lp

    def select_and_open_file(self):
        files = [os.path.join(self.dir, basename) for basename in os.listdir(self.dir)]
        files = [file for file in files if file.endswith('.h5')]
        if len(files) > 0:
            files = sorted(files, key=os.path.getmtime, reverse=True)
            self.file_path = files[0]
        else:
            self.file_path = None

        if self.file_path is not None:
            if self.file is not None:
                self.file.close()
            self.file = h5py.File(self.file_path, 'r', swmr=True, libver='latest', locking=False)

    def run(self):
        self.root.mainloop()

    def close(self):
        if self.file is not None:
            self.file.close()
        self.reader.terminate()
        self.root.quit()
        self.root.destroy()

    def poll_logs(self):
        y = self.livetext.y_scroll.get()
        if len(y) == 2:
            _, y_end = y
            self.livetext.add_all(self.reader.read_all_logs())
            if float(y_end) > 0.95:
                self.livetext.text.yview(tk.END)
        if self.reader.complete and self.model is not None:
            data = {}
            for attr in self.file['Data'].dtype.names:
                data[attr] = self.file['Data'][attr]
            df = pd.DataFrame(data)
            if df.shape[0] > 0:
                features = self.preprocessor.extract_features(df, extra=True)
                feature_df = pd.DataFrame(features, index=[0])
                score = self.model.predict_proba(feature_df)[0,1]
                self.livetext.text.config(state='normal')
                if score > self.model.threshold_90:
                    self.livetext.add('Warning: Model rejects sample at 90% significance level')
                else:
                    self.livetext.add('Success: Model accepts sample at 90% significance level')
                self.livetext.text.config(state='disabled')
                self.livetext.text.yview(tk.END)
        else:
            self.root.after(500, self.poll_logs)

    def pump_changed(self, flag, d, mode):
        flag = self.pump_active_flag.get()
        if flag != self.pump_active_prev_val:
            self.pump_active_prev_val = flag
            self.pump_active_text.delete('1.0', tk.END)
            if flag:
                self.pump_active_text.insert('1.0', '\n\nPump Active', 'center')
                self.pump_active_text.configure(bg='green')
            else:
                self.pump_active_text.insert('1.0', '\n\nPump Inactive', 'center')
                self.pump_active_text.configure(bg='red')

    def add_or_remove_target(self, y_target, activate):
        if self.reader is not None:
            self.reader.terminate()
        if activate:
            self.targets.append(y_target)
        elif y_target in self.targets:
            self.targets.remove(y_target)
        if self.file is not None:
            self.draw_plot()

    def create_controls(self):
        self.control_frame = tk.Frame(self)

        volume_switch = ToggleButton(self.control_frame, 'Accumulated volume L', self.add_or_remove_target, active=True, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Accumulated volume L'])
        current_switch = ToggleButton(self.control_frame, 'Pump L current', self.add_or_remove_target, active=True, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Pump L current'])
        flow_up_switch = ToggleButton(self.control_frame, 'Flow rate L upstream', self.add_or_remove_target, active=True, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Flow rate L upstream'])
        flow_down_switch = ToggleButton(self.control_frame, 'Flow rate L downstream', self.add_or_remove_target, active=True, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Flow rate L downstream'])

        temperature_up_switch = ToggleButton(self.control_frame, 'Temperature L upstream', self.add_or_remove_target, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Temperature L upstream'])
        temperature_down_switch = ToggleButton(self.control_frame, 'Temperature L downstream', self.add_or_remove_target, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Temperature L downstream'])
        pressure_up_switch = ToggleButton(self.control_frame, 'Pressure L upstream', self.add_or_remove_target, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Pressure L upstream'])
        pressure_down_switch = ToggleButton(self.control_frame, 'Pressure L downstream', self.add_or_remove_target, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Pressure L downstream'])

        co2_stream_switch = ToggleButton(self.control_frame, 'CO2stream', self.add_or_remove_target, inactive_color=self.root.cget('bg'), active_color=self.colors_map['CO2stream'])
        mask_pressure_switch = ToggleButton(self.control_frame, 'Mask pressure', self.add_or_remove_target, inactive_color=self.root.cget('bg'), active_color=self.colors_map['Mask pressure'])

        reset_btn = tk.Button(self.control_frame, text='Reload File', font=('utopia', 18), command=lambda: self.draw_plot())

        volume_switch.grid(row=0, column=0, sticky=tk.NSEW)
        current_switch.grid(row=0, column=1, sticky=tk.NSEW)
        flow_up_switch.grid(row=1, column=0, sticky=tk.NSEW)
        flow_down_switch.grid(row=1, column=1, sticky=tk.NSEW)
        temperature_up_switch.grid(row=2, column=0, sticky=tk.NSEW)
        temperature_down_switch.grid(row=2, column=1, sticky=tk.NSEW)
        pressure_up_switch.grid(row=3, column=0, sticky=tk.NSEW)
        pressure_down_switch.grid(row=3, column=1, sticky=tk.NSEW)
        co2_stream_switch.grid(row=4, column=0, sticky=tk.NSEW)
        mask_pressure_switch.grid(row=4, column=1, sticky=tk.NSEW)
        reset_btn.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW)

        self.control_frame.grid(row=1, column=1, sticky=tk.NSEW)

        self.control_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)
        self.control_frame.grid_columnconfigure((0, 1), weight=1)



class FileWidget(tk.Frame):
    def __init__(self, master=None, label=None, path="", filetypes=[('.h5', '*.h5')]):
        tk.Frame.__init__(self, master=master)
        self.label = tk.Label(self, text=label)
        self.file_text = tk.Entry(self, width=80)
        self.file_text.insert(0, path)
        self.but = tk.Button(self, text='Select', command=self.open_file_dialog)
        self.filetypes = filetypes

        self.label.grid(row=0, column=0, sticky=tk.W)
        self.file_text.grid(row=0, column=1, sticky=tk.W)
        self.but.grid(row=0, column=2, sticky=tk.W)

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(title="Select a File", filetypes=self.filetypes)
        self.file_text.delete(0, tk.END)
        self.file_text.insert(0, file_path)

    def path(self):
        return self.file_text.get()

class ToggleButton(tk.Frame):
    but = None
    active = False
    identity = None
    parent_command = None

    def __init__(self, master, identity, parent_command, active=False, inactive_color='#F0F0F0', active_color='#F0F0F0', **kwargs):
        super().__init__(master)
        self.but = tk.Button(self, text=identity, font=('utopia', 18), command=self.command)
        self.but.grid(row=0, column=0, sticky=tk.NSEW)
        self.identity = identity
        self.parent_command = parent_command
        self.active = not active

        self.active_color = active_color
        self.inactive_color = inactive_color

        self.light = tk.Button(self, relief='ridge', bd=2, command=self.command)
        self.light.grid(row=0, column=1, sticky=tk.NSEW)

        self.grid_rowconfigure(0, weight=1, uniform='controls')
        self.grid_columnconfigure(0, weight=8, uniform='controls')
        self.grid_columnconfigure(1, weight=1, uniform='controls')

        self.command()

    def command(self):
        if self.active:
            self.but.config(relief="ridge")
            self.light.config(background=self.inactive_color)
            self.parent_command(self.identity, not self.active)
        else:
            self.but.config(relief="sunken")
            self.light.config(background=self.active_color)
            self.parent_command(self.identity, not self.active)
        self.active = not self.active
