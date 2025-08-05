import tkinter as tk
from datetime import datetime

class LiveTextView(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master=master)
        self.text = tk.Text(self, font=18, wrap="none", state='disabled', width=24, height=12)
        self.text.tag_config('warning', background='yellow')
        self.text.tag_config('error', background='red')
        self.text.tag_config('time', foreground='blue')
        self.text.tag_config('success', background='lime')
        self.text.grid(row=0, column=0, sticky=tk.NSEW)

        self.y_scroll = tk.Scrollbar(self, orient='vertical', command=self.text.yview)
        self.x_scroll = tk.Scrollbar(self, orient='horizontal', command=self.text.xview)
        self.y_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.x_scroll.grid(row=1, column=0, sticky=tk.EW)

        self.text.config(xscrollcommand = self.x_scroll.set)
        self.text.config(yscrollcommand = self.y_scroll.set)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.initial_time = None

    def add(self, line):
        time, msg = self.extract_time(line)
        time = self.parse_time(time)

        self.text.config(state='normal')

        if self.initial_time is None:
            if 'Training Pumps' in msg:
                self.initial_time = time

        prefix = ''
        if self.initial_time is not None and time is not None:
            time_diff = (time - self.initial_time).total_seconds()
            minutes = int(time_diff // 60)
            seconds = int(time_diff % 60)
            prefix = '[{:02d}:{:02d}] '.format(minutes, seconds)

        tag = self.get_tag(msg)

        if len(prefix) > 0:
            self.text.insert('end', prefix, tag)
            self.text.tag_add('time', 'end-1c linestart', 'end-1c lineend')

        self.text.insert('end', f'{msg}\n', tag)
        self.text.config(state='disabled')

    def extract_time(self, line):
        parts = line.split(', ')
        if len(parts) > 1:
            return parts[0], parts[1]
        return '', line

    def parse_time(self, time):
        parts = time.split("+")
        if len(parts) > 1:
            time = parts[0]
            return datetime.strptime(time, '%Y-%m-%dT%H:%M:%S')
        return None

    def get_tag(self, msg):
        if msg.startswith('Warning'):
            return 'warning'
        if msg.startswith('Error'):
            return 'error'
        if msg.startswith('Success'):
            return 'success'
        return None

    def add_all(self, lines):
        for line in lines:
            self.add(line)

    def clear(self):
        self.text.config(state='normal')
        self.text.delete('1.0', 'end')
        self.text.config(state='disabled')
        self.initial_time = None
