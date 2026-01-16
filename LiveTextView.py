import tkinter as tk
from datetime import datetime

class LiveTextView(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master=master)
        self.text = tk.Text(self, font=12, wrap="none", state='disabled', width=24, height=8)
        self.text.tag_config('warning', background='orange')
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


    def add(self, line, log_parser = None):
        prefix = ''
        if log_parser is not None:
            time, msg = log_parser.extract_msg(line)
            time = log_parser.extract_time(time)
            prefix = log_parser.get_prefix(time)
        else:
            msg = line

        self.text.config(state='normal')
        tag = self.get_tag(msg)

        if len(prefix) > 0:
            self.text.insert('end', prefix, tag)
            self.text.tag_add('time', 'end-1c linestart', 'end-1c lineend')

        self.text.insert('end', f'{msg}\n', tag)
        self.text.config(state='disabled')

    def get_tag(self, msg):
        if msg.startswith('Warning'):
            return 'warning'
        if msg.startswith('Error'):
            return 'error'
        if msg.startswith('Success'):
            return 'success'
        return None

    def add_all(self, lines, log_parser):
        for line in lines:
            self.add(line, log_parser)

    def clear(self):
        self.text.config(state='normal')
        self.text.delete('1.0', 'end')
        self.text.config(state='disabled')

    def add_and_scroll_to_bottom(self, line, log_parser=None):
        y = self.y_scroll.get()
        self.add(line, log_parser)
        if len(y) == 2:
            _, y_end = y
            if float(y_end) > 0.95:
                self.text.yview(tk.END)

    def add_all_and_scroll_to_bottom(self, lines, log_parser=None):
        y = self.y_scroll.get()
        self.add_all(lines, log_parser)
        if len(y) == 2:
            _, y_end = y
            if float(y_end) > 0.95:
                self.text.yview(tk.END)
