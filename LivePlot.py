import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from matplotlib import patches
import matplotlib.backends.backend_tkagg
from matplotlib.backends.backend_pdf import PdfPages

from MetadataExtractor import MetadataExtractor

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
    'Pressure': (160, '×1000'),
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

    max_interval = 150

    n_frames_per_shift = 20

    x_axis = None

    max_x = None

    transform_map = {
        'Accumulated volume L': lambda x: x / 1000,
        'Mask pressure': lambda x: x / 1000,
        'Pressure L upstream': lambda x: x / 1000,
        'Pressure L downstream': lambda x: x / 1000
    }

    def __init__(self, x_label, x_range_limit, y_labels, progress_label, max_progress, colors_map, plot_params=None):
        self.x_label = x_label
        self.progress_label = progress_label
        self.max_progress = max_progress
        self.y_labels = y_labels.copy()

        self.x_range_limit = x_range_limit

        self.x_vals = []
        self.y_axes = {}
        self.y_vals = {}
        self.frame_num = 0

        self.colors_map = colors_map
        self.warnings = []
        self.errors = []

        plt.switch_backend('tkagg')
        matplotlib.rcParams.update({'font.size': 14})
        self.fig = plt.figure(figsize=(24,16))
        if plot_params is not None and 'right_adjust_per_axis' in plot_params:
            plot_params['right'] = 1 - plot_params['right_adjust_per_axis'] * self.count_axes()
            del plot_params['right_adjust_per_axis']
            self.fig.subplots_adjust(**plot_params)
        else:
            self.fig.subplots_adjust(right=1 - 0.06 * self.count_axes(), top=1, left=0.025, bottom=0.075)

        self.grid = self.fig.add_gridspec(3, 1, height_ratios=[0.05, 0.05, 0.90], hspace=0.025)

        self.progress = self.fig.add_subplot(self.grid[0, 0], xticks=[], yticks=[], frame_on=False, clip_on=False)
        self.progress.set_xlim(0, 1)
        self.progress.set_ylim(0, 1)
        self.progress.add_patch(patches.Rectangle((0, 0), 1, 1, edgecolor='black', facecolor='lightgrey', clip_on=False))
        self.progress_text = self.progress.text(.5, 0.5, '0%', zorder=10, ha='center', va='center')

        self.pump_indicator = patches.Rectangle((1, 0), 0.035, 1, edgecolor='black', facecolor='red', clip_on=False)
        self.progress.add_patch(self.pump_indicator)
        self.pump_text = self.progress.text(1 + 0.035/2, 0.5, 'Pump\nInactive', ha='center', va='center', fontsize=11, clip_on=False)
        self.is_pump_on = False

        self.error_plot = self.fig.add_subplot(self.grid[1, 0], xticks=[], yticks=[], frame_on=False, clip_on=False)
        self.error_plot.set_xlim(0, 1)
        self.error_plot.set_ylim(0, 1)
        self.error_plot.add_patch(patches.Rectangle((0, 0), 1, 1, edgecolor='black', facecolor='none', clip_on=False))
        self.events = []

        self.timer = None
        self.timer_text = self.error_plot.text(1 + 0.035/2, 0.5, '00:00', ha='center', va='center', fontsize=14, clip_on=False)
        self.error_plot.add_patch(patches.Rectangle((1, 0), 0.035, 1, edgecolor='black', facecolor='none', clip_on=False))

        self.x_axis = self.fig.add_subplot(self.grid[2, 0])
        self.x_axis.set_yticks([])


        i = 0
        for y_label in y_labels:
            self.y_vals[y_label] = []
            if y_map[y_label] not in self.y_axes.keys():
                self.add_axis(y_label, 1 + i * 0.075)
                i = i + 1


    def initial_data(self, data_list):
        self.x_vals = [data[self.x_label] / 60 for data in data_list]

        self.y_vals[self.progress_label] = [self.transform(self.progress_label, data[self.progress_label]) for data in data_list]
        for y_label in self.y_labels:
            self.y_vals[y_label] = [self.transform(y_label, data[y_label]) for data in data_list]

    def initial_frame(self):
        x_end = 0
        if len(self.x_vals) > 0:
            x_end = self.x_vals[-1]

        axes_done = []
        i = 0
        self.max_x = x_end + self.n_frames_per_shift * self.max_interval / (60*1000)
        for y_label in self.y_labels:
            axis_name, y_axis = self.get_axis(y_label)
            if axis_name not in axes_done:
                axes_done.append(axis_name)
                y_axis.clear()
                y_axis.set_xlabel('Time (min)')
                x_start = 0
                if self.x_range_limit:
                    x_start = max(0, x_end - 1)
                y_axis.set_xlim([x_start, self.max_x])
                y_label = y_map[y_label]
                y_axis.set_ylim([0, axis_map[y_label][0]])
                if len(axis_map[y_label][1]) > 0:
                    y_label = f'{y_label} ({axis_map[y_label][1]})'
                y_axis.set_ylabel(y_label)
                y_axis.yaxis.set_label_position('right')
                y_axis.yaxis.set_ticks_position('right')
                y_axis.spines['right'].set_position(('axes', 1 + i * 0.075))
                i = i + 1

        lines = self.draw_lines() + self.draw_progress() + self.draw_errors() + [self.timer_text]

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
            try:
                lines.extend(
                    axis.plot(self.x_vals, self.y_vals[y_label], label=y_label, color=self.colors_map[y_label]))
            except ValueError:
                print(f'Failed with {y_label}, x size {len(self.x_vals)}, y size {(len(self.y_vals[y_label]))}')
        return lines

    def animate(self, data):
        lines = []
        if data is not None and len(data) > 0:
            for point in data:
                self.x_vals.append(point[self.x_label] / 60)
                self.y_vals[self.progress_label].append(self.transform(self.progress_label, point[self.progress_label]))
                for y_label in self.y_labels:
                    self.y_vals[y_label].append(self.transform(y_label, point[y_label]))

            if 'Pump L current' in data[-1]:
                indicator = self.set_pump_indicator(data[-1]['Pump L current'])
                if indicator is not None:
                    lines += indicator

            self.frame_num = self.frame_num + 1

        if self.frame_num == 1 or self.frame_num % self.n_frames_per_shift == 0:
            lines = self.initial_frame()
        else:
            lines = self.draw_lines() + self.draw_progress() + self.draw_errors() + [self.timer_text]

        return lines

    def draw_progress(self):
        if self.progress_label in self.y_vals and len(self.y_vals[self.progress_label]) > 0:
            percent = max(self.y_vals[self.progress_label]) / self.max_progress
            rect = patches.Rectangle((0, 0), percent, 1, facecolor='lime', edgecolor='black', zorder=5)
            self.progress.add_patch(rect)
            self.progress_text.set(text=f'{int(percent * 100)}%')
            self.progress_text.set(zorder=10)
            return [rect] + [self.progress_text]
        return []

    def add_errors(self, warnings, errors):
        self.warnings.extend(warnings)
        self.errors.extend(errors)

    def draw_errors(self):
        warnings = []
        errors = []
        if self.x_range_limit:
            x_start = self.max_x - 1
            warnings += [(time - x_start) / (self.max_x - x_start) for time in self.warnings if time > x_start]
            errors += [(time - x_start) / (self.max_x - x_start) for time in self.errors if time > x_start]
        else:
            warnings += [time / self.max_x for time in self.warnings]
            errors += [time / self.max_x for time in self.errors]


        for event in self.events:
            event.remove()
        self.events = self.error_plot.eventplot(warnings, colors='orange', linelength=1, lineoffset=0.5, zorder=5)
        self.events += self.error_plot.eventplot(errors , colors='red', linelength=1, lineoffset=0.5, clip_on=False, zorder=5)
        return self.events

    def read(self, generator):
        self.ani=animation.FuncAnimation(self.fig, self.animate, frames=generator, interval=self.max_interval, repeat=False, init_func=self.initial_frame, cache_frame_data=False)

    def get_figure(self):
        return self.fig

    def add_axis(self, name, offset):
        x_end = 0
        if len(self.x_vals) > 0:
            x_end = self.x_vals[-1]
        self.x_axis.set_xlabel('Time (min)')
        axis = self.x_axis.twinx()
        x_start = 0
        if self.x_range_limit:
            x_start = max(0, x_end - 1)
        axis.set_xlim([x_start, x_end + self.n_frames_per_shift * self.max_interval])
        y_label = y_map[name]
        axis.set_ylim([0, axis_map[y_label][0]])
        if len(axis_map[y_label][1]) > 0:
            y_label = f'{y_label} ({axis_map[y_label][1]})'
        axis.set_ylabel(y_label)
        axis.yaxis.set_label_position('right')
        axis.yaxis.set_ticks_position('right')
        axis.spines['right'].set_position(('axes', offset))
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

    def set_pump_indicator(self, current):
        if (current >= 40 and not self.is_pump_on) or (current < 40 and self.is_pump_on):
            self.is_pump_on = not self.is_pump_on
            if self.is_pump_on:
                self.pump_indicator.set(facecolor='lime')
                self.pump_text.set(text='Pump\nActive')
            else:
                self.pump_indicator.set(facecolor='red')
                self.pump_text.set(text='Pump\nInactive')
            return [self.pump_indicator, self.pump_text]
        return None

    def stop_timer(self):
        if self.timer is not None:
            self.timer.stop()

    def reset_timer(self):
        if self.timer is not None:
            self.timer.stop()
        self.timer_text.set(text='00:00')
        self.timer = self.fig.canvas.new_timer(interval=1000, callbacks=[(self.increment_timer, [], {})])
        self.timer.start()
        self.increment_timer()

    def increment_timer(self):
        if len(self.x_vals) > 0:
            time = int(self.x_vals[-1] * 60)
            self.timer_text.set(text=f'{str(time // 60).zfill(2)}:{str(time % 60).zfill(2)}')

    def get_configs(self):
        config = self.fig.subplotpars.__dict__
        config['right_adjust_per_axis'] = (1 - config['right']) / self.count_axes()
        del config['right']
        return config

    def close(self):
        self.stop_timer()
        plt.close(self.fig)

    def save(self, path, file):
        with PdfPages(path) as pdf:
            self.ani.to_html5_video()
            legend = self.fig.legend(loc=(0.05, 0.85 - 0.025 * self.count_axes()))
            plot_mat = self.fig_to_mat(self.fig)
            legend.remove()

            metadata_extractor = MetadataExtractor()
            metadata, keys = metadata_extractor.extract(file)

            summary_fig = self.get_summary_fig(metadata, keys)
            summary_mat = self.fig_to_mat(summary_fig)
            plt.close(summary_fig)

            fig = plt.figure(num=12, figsize=(24, 16), frameon=False)
            ax = fig.subplots()
            ax.xaxis.set_visible(False)
            ax.yaxis.set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.spines['right'].set_visible(False)

            ax.imshow(np.vstack((summary_mat, plot_mat)))
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

            return metadata

    def fig_to_mat(self, fig):
        fig.canvas.draw()
        buf = fig.canvas.tostring_rgb()
        ncols, nrows = fig.canvas.get_width_height()
        return np.fromstring(buf, dtype=np.uint8).reshape(nrows, ncols, 3)

    def get_summary_fig(self, metadata, keys):
        table = []
        for key in keys:
            if key in metadata:
                try:
                    table.append([key, '%.2f' % metadata[key]])
                except:
                    table.append([key, metadata[key]])
            else:
                table.append([key, ""])
        fig = plt.figure(num=11, figsize=(24, 6), frameon=False)
        ax = fig.subplots()
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.table(table, bbox=(0, 0.0675, 1, 1))
        return fig