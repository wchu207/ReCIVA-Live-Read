import os
import multiprocessing
import threading
import tkinter as tk
from tkinter import filedialog

import h5py
import pandas as pd
from lightgbm import LGBMClassifier
from tqdm import tqdm

from LiveH5Reader import LiveH5Reader
from LivePlot import LivePlot
from LogParser import LogParser
from preprocessing import ReCIVA_log_preprocessor
from pdfrw import PdfWriter, PdfReader


class FileWindow(tk.Frame):
    def __init__(self, master, model: LGBMClassifier, out_dir, colors_map, *args, logging_callback=None,  **kwargs):
        super().__init__(*args, **kwargs)
        self.master = master
        self.model = model
        self.out_dir = out_dir
        self.file_listbox = tk.Listbox(self)
        self.file_listbox.grid(row=0, column=0, sticky=tk.NSEW)

        self.colors_map = colors_map

        self.create_controls()
        self.log = logging_callback

        self.widget_lock = WidgetLock([self.select_files_btn, self.check_files_btn, self.clear_files_btn, self.plot_files_btn])
        self.log_parser = LogParser()

        self.scores = []

        self.grid_rowconfigure(0, weight=7)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)


    def create_controls(self):
        self.control_frame = tk.Frame(self)
        self.select_files_btn = tk.Button(self.control_frame, text='Add Files', command=self.select_files)
        self.clear_files_btn = tk.Button(self.control_frame, text='Clear', command=self.clear_files)
        self.check_files_btn = tk.Button(self.control_frame, text='Check Files', command=self.check_files)
        self.plot_files_btn = tk.Button(self.control_frame, text='Plot', command=self.plot_files)

        self.select_files_btn.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW)
        self.clear_files_btn.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)
        self.check_files_btn.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW)
        self.plot_files_btn.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW)
        self.control_frame.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.control_frame.grid_columnconfigure((0, 1), weight=1)

        self.control_frame.grid(row=1, column=0, sticky=tk.NSEW)


    def select_files(self):
        with self.widget_lock:
            filenames = filedialog.askopenfilenames(filetypes=[('.h5', '*.h5')])
            old_files = []
            if self.file_listbox.size() > 0:
                old_files += list(self.file_listbox.get(0, self.file_listbox.size()))

            new_files = [file for file in filenames if file not in old_files]
            for file in new_files:
                self.file_listbox.insert(tk.END, file)

    def clear_files(self):
        self.file_listbox.delete(0, tk.END)
        self.scores = []

    def check_files(self):
        with self.widget_lock:
            self.update_scores()


    def load_as_df(self, file):
        file = h5py.File(file, 'r', libver='latest', locking=False)
        data = {}
        for attr in file['Data'].dtype.names:
            data[attr] = file['Data'][attr]
        return pd.DataFrame(data)

    def compute_score(self, df):
        score = 1
        try:
            preprocessor = ReCIVA_log_preprocessor()
            features = preprocessor.extract_features(df, extra=True)
            feature_df = pd.DataFrame(features, index=[0])
            score = self.model.predict_proba(feature_df)[0, 1]
        except:
            pass
        return score

    def update_scores(self):
        if len(self.scores) < self.file_listbox.size():
            files = list(self.file_listbox.get(len(self.scores), self.file_listbox.size()))
            for i, file in enumerate(files):
                score = 1
                df = self.load_as_df(file)
                if df is not None and df.shape[0] > 0:
                    score = self.compute_score(df)
                self.scores.append(score)
        for i, score in enumerate(self.scores):
            if score > self.model.threshold_90:
                self.file_listbox.itemconfig(i, bg='red')
            else:
                self.file_listbox.itemconfig(i, bg='lime')

    def plot_files(self):
        threading.Thread(target=self._plot_files).start()

    def _plot_files(self):
        with self.widget_lock:
            plot_params = self.master.get_plot_params()
            targets = self.master.get_targets()

            if self.file_listbox.size() > 0:
                args_list = []
                for path in self.file_listbox.get(0, self.file_listbox.size()):
                    filename, _ = os.path.splitext(os.path.basename(path))
                    args_list.append((path, targets, plot_params, self.colors_map, self.log_parser, self.out_dir))
                if self.log is not None:
                    self.log(f'Processing selected files and saving to {self.out_dir}...')
                p = multiprocessing.Pool(16, maxtasksperchild=1)
                results = p.starmap(plot_file, args_list)
                results = [r for r in results if not type(r) == str]


                summary_df = pd.DataFrame(results)
                summary_df.set_index('File').to_excel(os.path.join(self.out_dir, 'summary.xlsx'))

                p = multiprocessing.Pool(16)
                files = summary_df['File'].copy()
                files = [os.path.join(self.out_dir, file + '.pdf') for file in files]
                merger = PdfWriter()

                for file in files:
                    if os.path.isfile(file):
                        merger.addpages(PdfReader(file).pages)
                merger.write(os.path.join(self.out_dir, 'summary.pdf'))

                if self.log is not None:
                    self.log(f'Finished processing files')
                    self.log(f'Success Saved summary.xlsx and summary.pdf to {self.out_dir}...')


def plot_file(path, targets, plot_params, colors_map, log_parser, out_dir):
    filename, _ = os.path.splitext(os.path.basename(path))
    try:
        file = h5py.File(path, 'r', libver='latest', locking=False)
        reader = LiveH5Reader(file, targets + ['Accumulated volume L', 'Pump L current'])

        liveplot = LivePlot('Collection time', False, targets, 'Accumulated volume L', 1,
                                     colors_map=colors_map, plot_params=plot_params)
        liveplot.initial_data(reader.read_all_data())

        logs = reader.read_all_logs()
        log_parser.set_initial_time(logs)
        warnings, errors = log_parser.get_warnings_and_errors(logs)
        liveplot.add_errors(warnings, errors)

        liveplot.read(reader.read_data())
        liveplot.increment_timer()




        os.makedirs(out_dir, exist_ok=True)
        metadata = liveplot.save(os.path.join(out_dir, filename + '.pdf'), file)
        metadata['File'] = filename
        liveplot.close()
        return metadata
    except Exception as e:
        raise f'Error Failed to process {filename} due to {repr(e)}'

class WidgetLock:
    def __init__(self, widgets):
        self.widgets = widgets

    def __enter__(self):
        for widget in self.widgets:
            widget.config(state='disabled')

    def __exit__(self, type, value, traceback):
        for widget in self.widgets:
            widget.config(state='normal')
