import tkinter as tk
import h5py
from tkinter import ttk

from lightgbm import LGBMClassifier

from LogParser import LogParser
from preprocessing import ReCIVA_log_preprocessor
from LiveH5Reader import LiveH5Reader
from LivePlot import LivePlot
from LiveTextView import LiveTextView
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import filedialog
from datetime import datetime
import threading
from CustomNavigationToolbar import CustomNavigationToolbar
import pandas as pd


class DataWindow(tk.PanedWindow):
    def __init__(self, master, src: str, model: LGBMClassifier, colors_map: dict, *args, **kwargs):
        super().__init__(master=master, orient='vertical', *args, **kwargs)
        self.targets = []
        self.hidden_targets = ['Accumulated volume L', 'Pump L current']
        self.colors_map = colors_map

        self.master = master
        self.file = None
        self.reader = None
        self.canvas = None
        self.toolbar = None
        self.liveplot = None
        self.liveplot_canvas = None

        self.top_frame = tk.Frame(self)
        self.canvas_frame = tk.Frame(self)
        self.bottom_frame = tk.Frame(self)

        self.livetext = LiveTextView(self.bottom_frame)
        self.initial_time = None
        self.final_score = None

        self.log_parser = LogParser()

        self.src = src
        self.file_widget = FileWidget(self.top_frame, label='File', callback=self.open_file, font=32)
        self.file_widget.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW)
        self.select_file_from_src()

        self.reset_btn = tk.Button(self.top_frame, text='Reload File From Directory', font=32, command=self.reload_file)
        self.reset_btn.grid(row=0, column=2, sticky="nsw")


        self.create_controls()

        self.log_lock = threading.Lock()
        self.log_flag = False

        self.range_limit = False

        if self.src is not None:
            self.reload_file()
        else:
            self.livetext.add('Error: source_directory not found in config.json')

        self.model = model
        if model is None:
            self.livetext.add('Warning: no model found, check \'model_path\' in config.json')

        self.preprocessor = ReCIVA_log_preprocessor()

        self.livetext.grid(row=0, column=1, columnspan=2, sticky=tk.NSEW)

        self.top_frame.grid_rowconfigure(0, weight=1, minsize=32)
        self.bottom_frame.grid_rowconfigure(0, weight=1, minsize=32)

        self.top_frame.grid_columnconfigure((0, 1, 2), weight=1, minsize=16)
        self.bottom_frame.grid_columnconfigure(0, weight=1, minsize=16)
        self.bottom_frame.grid_columnconfigure(1, weight=14, minsize=32)

        self.add(self.top_frame, minsize=32, stretch='never')
        self.add(self.canvas_frame, minsize=250, stretch='middle')
        self.add(self.bottom_frame, minsize=100, stretch='middle')

    def create_controls(self):
        self.control_notebook = ttk.Notebook(self.bottom_frame)
        basic_frame = tk.Frame(self.control_notebook)
        advanced_frame = tk.Frame(self.control_notebook)

        flow_up_switch = ToggleButton(basic_frame, 'Flow rate L upstream', self.add_or_remove_target, active=True,
                                      inactive_color=self.cget('bg'),
                                      active_color=self.colors_map['Flow rate L upstream'])
        flow_down_switch = ToggleButton(basic_frame, 'Flow rate L downstream', self.add_or_remove_target,
                                        active=True, inactive_color=self.cget('bg'),
                                        active_color=self.colors_map['Flow rate L downstream'])

        scope_switch = ToggleButton(basic_frame, 'View Last 60 Seconds', self.toggle_range_limit, active=False,
                                    inactive_color=self.cget('bg'), active_color='grey')

        temperature_up_switch = ToggleButton(advanced_frame, 'Temperature L upstream', self.add_or_remove_target,
                                             inactive_color=self.cget('bg'),
                                             active_color=self.colors_map['Temperature L upstream'])
        temperature_down_switch = ToggleButton(advanced_frame, 'Temperature L downstream',
                                               self.add_or_remove_target, inactive_color=self.cget('bg'),
                                               active_color=self.colors_map['Temperature L downstream'])
        pressure_up_switch = ToggleButton(advanced_frame, 'Pressure L upstream', self.add_or_remove_target,
                                          inactive_color=self.cget('bg'),
                                          active_color=self.colors_map['Pressure L upstream'])
        pressure_down_switch = ToggleButton(advanced_frame, 'Pressure L downstream', self.add_or_remove_target,
                                            inactive_color=self.cget('bg'),
                                            active_color=self.colors_map['Pressure L downstream'])

        co2_stream_switch = ToggleButton(advanced_frame, 'CO2stream', self.add_or_remove_target,
                                         inactive_color=self.cget('bg'),
                                         active_color=self.colors_map['CO2stream'])
        mask_pressure_switch = ToggleButton(advanced_frame, 'Mask pressure', self.add_or_remove_target,
                                            inactive_color=self.cget('bg'),
                                            active_color=self.colors_map['Mask pressure'])

        flow_up_switch.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW)
        flow_down_switch.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)
        scope_switch.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW)

        temperature_up_switch.grid(row=0, column=0, sticky=tk.NSEW)
        temperature_down_switch.grid(row=1, column=0, sticky=tk.NSEW)
        pressure_up_switch.grid(row=2, column=0, sticky=tk.NSEW)
        pressure_down_switch.grid(row=3, column=0, sticky=tk.NSEW)
        co2_stream_switch.grid(row=4, column=0, sticky=tk.NSEW)
        mask_pressure_switch.grid(row=5, column=0, sticky=tk.NSEW)

        basic_frame.grid_rowconfigure((0, 1, 2, 3), weight=1, uniform='controls')
        basic_frame.grid_columnconfigure((0, 1), weight=1, uniform='controls')

        advanced_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1, uniform='controls')
        advanced_frame.grid_columnconfigure(0, weight=1, uniform='controls')

        self.control_notebook.add(basic_frame, text='Basic')
        self.control_notebook.add(advanced_frame, text='Advanced')

        self.control_notebook.grid(row=0, column=0, sticky=tk.NSEW)

        style = ttk.Style()
        current_theme = style.theme_use()
        style.theme_settings(current_theme, {'TNotebook.Tab': {'configure': {'padding': [15, 5], 'font': 32}}})



    def add_errors_from_logs(self, logs):
        warnings, errors = self.log_parser.get_warnings_and_errors(logs)
        self.liveplot.add_errors(warnings, errors)

    def reload_file(self):
        self.select_file_from_src()
        self.open_file()

    def draw_plot(self):
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.toolbar.destroy()
        if self.file is not None:
            self.create_plot_from_file(self.file)
            self.canvas = FigureCanvasTkAgg(master=self.canvas_frame, figure=self.liveplot.get_figure())
            self.toolbar = CustomNavigationToolbar(self.canvas, self.canvas_frame, self.liveplot)
            self.canvas.get_tk_widget().pack(expand=True, fill='both')
            self.toolbar.pack(fill=tk.X, side=tk.TOP)

    def create_plot_from_file(self, file):
        if self.reader is not None:
            with self.log_lock:
                self.reader.terminate()

        self.reader = LiveH5Reader(file, self.targets + self.hidden_targets)
        self.final_score = None

        logs = self.reader.read_all_logs()
        self.log_parser.set_initial_time(logs)
        self.livetext.clear()
        self.livetext.add_all_and_scroll_to_bottom(logs, self.log_parser)
        self.livetext.text.yview(tk.END)

        if self.liveplot is not None:
            self.liveplot.close()

        self.liveplot = LivePlot('Collection time', self.range_limit, self.targets, 'Accumulated volume L', 1,
                                 colors_map = self.colors_map, plot_params=self.master.get_plot_params())
        self.liveplot.initial_data(self.reader.read_all_data())
        self.liveplot.read(self.reader.read_data())
        with self.log_lock:
            self.reset_timer()

        self.add_errors_from_logs(logs)

        with self.log_lock:
            if not self.log_flag:
                self.log_flag = True
                self.livetext.after(0, self.poll_logs)

    def select_file_from_src(self):
        if os.path.isdir(self.src):
            files = [os.path.join(self.src, basename) for basename in os.listdir(self.src)]
            files = [file for file in files if file.endswith('.h5')]
            if len(files) > 0:
                files = sorted(files, key=os.path.getmtime, reverse=True)
                self.file_widget.set(files[0])
            else:
                self.file_widget.set("")
        elif os.path.isfile(self.src):
            self.file_widget.set(self.src)

    def open_file(self):
        file_path = self.file_widget.path()
        if file_path is not None and os.path.isfile(file_path):
            if self.file is not None:
                self.file.close()
            self.file = h5py.File(file_path, 'r', swmr=True, libver='latest', locking=False)
        self.draw_plot()

    def reset_timer(self):
        self.liveplot.reset_timer()

    def poll_logs(self):
        with self.log_lock:
            logs = self.reader.read_all_logs()
            self.log_parser.set_initial_time(logs)
            self.add_errors_from_logs(logs)
            self.livetext.add_all_and_scroll_to_bottom(logs)


        if self.reader.complete:
            self.terminate_file()
        else:
            self.livetext.after(1000, self.poll_logs)

    def terminate_file(self):
        with self.log_lock:
            self.liveplot.stop_timer()
            self.log_flag = False
            if self.model is not None:
                data = {}
                for attr in self.file['Data'].dtype.names:
                    data[attr] = self.file['Data'][attr]
                df = pd.DataFrame(data)
                if df.shape[0] > 0:
                    t = threading.Thread(target=lambda: self.compute_score(df))
                    t.start()
                    self.livetext.after(0, self.poll_score)
                else:
                    self.livetext.text.config(state='normal')
                    self.livetext.add('Error: no logs found')
                    self.livetext.text.config(state='disabled')
                    self.livetext.text.yview(tk.END)

            self.file.close()

    def compute_score(self, df):
        try:
            features = self.preprocessor.extract_features(df, extra=True)
            feature_df = pd.DataFrame(features, index=[0])
            self.final_score = self.model.predict_proba(feature_df)[0, 1]
        except:
            self.final_score = 1

    def poll_score(self):
        if self.final_score is not None:
            self.livetext.text.config(state='normal')
            if self.final_score > self.model.threshold_90:
                self.livetext.add('Warning: Model rejects sample at 90% significance level', self.log_parser)
            else:
                self.livetext.add('Success: Model accepts sample at 90% significance level', self.log_parser)
            self.livetext.text.config(state='disabled')
            self.livetext.text.yview(tk.END)
        else:
            self.livetext.after(1000, self.poll_score)


    def add_or_remove_target(self, y_target, activate):
        if activate:
            self.targets.append(y_target)
        elif y_target in self.targets:
            self.targets.remove(y_target)
        if self.file is not None:
            if self.file:
                self.draw_plot()
            else:
                self.open_file()

    def toggle_range_limit(self, identity, activate):
        self.range_limit = activate
        if self.file is not None:
            if self.file:
                self.draw_plot()
            else:
                self.open_file()

    def close(self):
        if self.file is not None:
            self.file.close()
        with self.log_lock:
            self.log_flag = False
            if self.reader is not None:
                self.reader.terminate()


class FileWidget(tk.Frame):
    def __init__(self, master=None, label=None, path="", callback = None, filetypes=[('.h5', '*.h5')], font=32):
        tk.Frame.__init__(self, master=master)
        self.label = tk.Label(self, text=label, font=font)
        self.file_text = tk.Entry(self, width=80, font=font, disabledforeground='black')
        self.file_text.insert(0, path)

        self.file_path = ''
        self.but = tk.Button(self, text='Select', command=self.open_file_dialog, font=font)
        self.filetypes = filetypes
        self.callback = callback

        self.label.grid(row=0, column=0, sticky=tk.NSEW)
        self.file_text.grid(row=0, column=1, sticky=tk.NSEW)
        self.but.grid(row=0, column=2, sticky=tk.NSEW)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=8)
        self.grid_columnconfigure((0, 2), weight=1)

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(title="Select a File", filetypes=self.filetypes)

        self.file_path = file_path
        filename = os.path.basename(file_path)

        self.file_text.config(state='normal')
        self.file_text.delete(0, tk.END)
        self.file_text.insert(0, filename)
        if os.path.isfile(file_path) and self.callback is not None:
            self.file_text.config(state='disabled')
            self.callback()

    def set(self, file_path):
        self.file_path = file_path
        filename = os.path.basename(file_path)

        self.file_text.delete(0, tk.END)
        self.file_text.insert(0, filename)

    def path(self):
        return self.file_path

class ToggleButton(tk.Frame):
    but = None
    active = False
    identity = None
    parent_command = None

    def __init__(self, master, identity, parent_command, active=False, inactive_color='#F0F0F0', active_color='#F0F0F0', **kwargs):
        super().__init__(master)
        self.but = tk.Button(self, text=identity, font=('utopia', 14), width=20, command=self.command)
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

