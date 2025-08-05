import numpy as np
from scipy.signal import find_peaks


# Data loading and transformation
class ReCIVA_log_preprocessor:
    def __init__(self):
        return

    def extract_features(self, df, extra=False):
        features = {}
        if extra:
            # Time of last log
            features['Total time'] = df['Collection time'].max()
            # For time between logs
            timediff_array = self.diff(df['Collection time'])
            features = {**features, **self.extract_summary("Interval", timediff_array)}

            # Time before collection starts
            features['Time before collection'] = df.iloc[(df.loc[:, 'Accumulated volume L'] > 0.01).argmax(), :]['Collection time']


            # Number of peaks in CO2 stream
            features = {**features, **self.extract_summary("CO2stream", df['CO2stream'])}
            features = {**features, **self.extract_cycles("CO2stream", df['Collection time'], df['CO2stream'])}

            # Volume at end
            features = {**features, 'Accumulated volume L': df['Accumulated volume L'].max()}
            # A flow: discover by the transition from zero flow to positive flow, then positive to zero
            #   must find flow boundaries
            #   interval starts at first positive after zero, end at first zero
            flow_intervals = self.extract_flow_intervals(df['Flow rate L upstream'].to_numpy(),
                                                         df['Collection time'].to_numpy())
            features['Flow upstream length count'] = len(flow_intervals)
            features = {**features, **self.extract_summary("Flow upstream length", flow_intervals)}

            flow_intervals = self.extract_flow_intervals(df['Flow rate L downstream'].to_numpy(),
                                                         df['Collection time'].to_numpy())
            features['Flow downstream length count'] = len(flow_intervals)
            features = {**features, **self.extract_summary("Flow downstream length", flow_intervals)}

            features = {**features, **self.extract_summary("Pump current", df['Pump L current'])}
            features = {**features, **self.extract_summary("Mask pressure", df['Mask pressure'])}
            features = {**features, **self.extract_summary("Pressure upstream", df['Pressure L upstream'])}
            features = {**features, **self.extract_summary("Pressure downstream", df['Pressure L downstream'])}
            features = {**features, **self.extract_summary("Voltage", df['Voltage L'])}
            features = {**features, **self.extract_summary("Training current", df['Pump L training current'])}
            features = {**features, **self.extract_summary("Live voltage", df['Pump L live voltage'])}


        # Flow magnitudes
        features = {**features, **self.extract_flow_summary('Flow rate upstream', df['Flow rate L upstream'])}
        features = {**features, **self.extract_flow_summary('Flow rate downstream', df['Flow rate L downstream'])}

        # Average of upstream-downstream difference
        flow_difference_values = (df['Flow rate L upstream'] - df['Flow rate L downstream'])
        features = {**features, **self.extract_flow_summary("Upstream-downstream flow rate difference", flow_difference_values, only_nonzero=False)}

        #features = {**features, **self.extract_summary("Mask pressure", df['Mask pressure'])}

        return features

    def diff(self, col):
        return np.diff(col)

    def extract_summary(self, name, col):
        results = {}
        results[f'{name} mean'] = col.mean()
        results[f'{name} min'] = col.min()
        results[f'{name} max'] = col.max()
        results[f'{name} s.dev'] = col.std()
        return results

    def extract_flow_summary(self, name, col, only_nonzero=True):
        flows = col
        if only_nonzero:
            flows = col[col > 0]
        return {**self.extract_summary(name, flows), f'{name} sum': col.sum()}

    def extract_flow_intervals(self, flow_array, time_array):
        # A flow: discover by the transition from zero flow to positive flow, then positive to zero
        #   must find flow boundaries
        #   interval starts at first positive after zero, end at first zero
        flow_exists_array = flow_array > 0.01
        flow_not_exists_array = np.logical_not(flow_exists_array)
        flows = []
        index = 0
        while index < len(flow_array):
            starts = np.argwhere(flow_exists_array[index:])
            if len(starts) > 0:
                start = starts[0][0] + index
                ends = np.argwhere(flow_not_exists_array[start:])
                if len(ends) > 0:
                    end = ends[0][0] + start
                    flows.append((start, end))
                    index = end
                else:
                    break
            else:
                break
        return np.array([time_array[flow[1]] - time_array[flow[0]] for flow in flows])

    def extract_cycles(self, name, t, y):
        first_index = np.argmax(y > 0)
        t = t[first_index:].to_numpy()
        y = y[first_index:].to_numpy()


        peak_indices, _ = find_peaks(y, height=np.mean(y), width=7)
        peak_times = t[peak_indices]
        periods = self.diff(peak_times)

        out = {f'{name} cycle count': max(0, len(peak_indices) - 1)}
        if len(periods) > 0:
            out = {**out, **self.extract_summary(f'{name} cycle period', periods)}

        return out