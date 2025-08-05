from matplotlib import pyplot as plt
from matplotlib import animation
import matplotlib.backends.backend_tkagg

transform_map = {
    'Pressure': lambda x: x / 1000,
    'Volume': lambda x: x / 1000,
    'CO2': lambda x: x / 1000
}
y_map = {
    'CO2stream': 'CO2',
    'Mask pressure': 'Pressure',
    'Pump L current': 'Current',
    'Flow rate L upstream': 'Flow rate',
    'Flow rate L downstream': 'Flow rate',
    'Temperature L upstream': 'Temperature',
    'Temperature L downstream': 'Temperature',
    'Pressure L upstream': 'Pressure',
    'Pressure L downstream': 'Pressure',
    'Accumulated volume L': 'Volume'
}

axis_map = {
    'CO2': (30, '×1000'),
    'Pressure': (160, 'x1000'),
    'Current': (400, ''),
    'Flow rate': (600, ''),
    'Temperature': (40, '°C'),
    'Volume': (1, 'L')
}


class LivePlot(object):

    fig = None

    x_vals = []
    y_vals = {}

    x_label = None
    y_labels = []
    y_axes = {}

    frame_num = 0

    max_interval = 0.10

    n_frames_per_shift = 20


    x_axis = None

    transform_map = {
        'Accumulated volume L': lambda x: x / 1000,
        'Mask pressure': lambda x: x / 1000,
        'Pressure L upstream': lambda x: x / 1000,
        'Pressure L downstream': lambda x: x / 1000
    }

    def __init__(self, x_label, y_labels, colors_map):
        self.x_label = x_label
        self.y_labels = y_labels.copy()

        self.x_vals = []
        self.y_axes = {}
        self.frame_num = 0

        self.colors_map = colors_map

        plt.switch_backend('tkagg')
        matplotlib.rcParams.update({'font.size': 14})
        self.fig = plt.figure(figsize=(8,12))
        self.fig.subplots_adjust(right=1 - 0.06 * self.count_axes(), top=0.95, left=0.05)
        self.x_axis = self.fig.add_subplot(1, 1, 1)
        self.x_axis.set_yticks([])

        i = 0
        for y_label in y_labels:
            self.y_vals[y_label] = []
            if y_map[y_label] not in self.y_axes.keys():
                self.add_axis(y_label, 1 + i * 0.075)
                i = i + 1


    def initial_data(self, data_list):
        self.x_vals = [data[self.x_label] for data in data_list]

        for y_label in self.y_labels:
            self.y_vals[y_label] = [self.transform(y_label, data[y_label]) for data in data_list]

    def initial_frame(self):
        x_end = 0
        if len(self.x_vals) > 0:
            x_end = self.x_vals[-1]

        axes_done = []
        i = 0
        for y_label in self.y_labels:
            axis_name, y_axis = self.get_axis(y_label)
            if axis_name not in axes_done:
                axes_done.append(axis_name)
                y_axis.clear()
                y_axis.set_xlabel('Time (s)')
                y_axis.set_xlim([0, x_end + self.n_frames_per_shift * self.max_interval])
                y_label = y_map[y_label]
                y_axis.set_ylim([0, axis_map[y_label][0]])
                if len(axis_map[y_label][1]) > 0:
                    y_label = f'{y_label} ({axis_map[y_label][1]})'
                y_axis.set_ylabel(y_label)
                y_axis.yaxis.set_label_position('right')
                y_axis.yaxis.set_ticks_position('right')
                y_axis.spines['right'].set_position(('axes', 1 + i * 0.075))
                i = i + 1

        lines = self.draw_lines()

        self.fig.canvas.draw()
        return lines

    def transform(self, y_label, val):
        if y_map[y_label] in transform_map.keys():
            return transform_map[y_map[y_label]](val)
        else:
            return val

    def draw_lines(self):
        lines = []
        for i, y_label in enumerate(self.y_labels):
            name, axis = self.get_axis(y_label)
            lines.extend(
                axis.plot(self.x_vals, self.y_vals[y_label], label=y_label, color=self.colors_map[y_label]))

        return lines

    def animate(self, data):
        lines = []
        if data is not None and len(data) > 0:
            self.x_vals.append(data[self.x_label])
            for y_label in self.y_labels:
                self.y_vals[y_label].append(self.transform(y_label, data[y_label]))

            self.frame_num = self.frame_num + 1

        if self.frame_num == 1 or self.frame_num % self.n_frames_per_shift == 0:
            lines = self.initial_frame()
        else:
            lines = self.draw_lines()

        return lines


    def read(self, generator):
        self.ani=animation.FuncAnimation(self.fig, self.animate, frames=generator, interval=self.max_interval * 1000, repeat=False, blit=True, init_func=self.initial_frame, cache_frame_data=False)

    def get_figure(self):
        return self.fig

    def add_axis(self, name, offset):
        x_end = 0
        if len(self.x_vals) > 0:
            x_end = self.x_vals[-1]
        axis = self.x_axis.twinx()
        axis.set_xlabel('Time (s)')
        axis.set_xlim([0, x_end + self.n_frames_per_shift * self.max_interval])
        y_label = y_map[name]
        axis.set_ylim([0, axis_map[y_label][0]])
        if len(axis_map[y_label][1]) > 0:
            y_label = f'{y_label} ({axis_map[y_label][1]})'
        axis.set_ylabel(y_label)
        axis.yaxis.set_label_position('left')
        axis.yaxis.set_ticks_position('left')
        axis.spines['left'].set_position(('axes', offset))
        self.y_axes[y_map[name]] = axis

    def get_axis(self, name):
        if y_map[name] in self.y_axes:
            return y_map[name], self.y_axes[y_map[name]]
        return None

    def count_axes(self):
        axes = []
        for y_label in self.y_labels:
            if y_map[y_label] not in axes:
                axes.append(y_map[y_label])
        return len(axes)
