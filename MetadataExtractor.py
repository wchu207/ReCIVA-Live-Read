import re
import h5py
import numpy as np

from LogParser import LogParser


class MetadataExtractor:
    def __init__(self):
        pass

    def extract(self, file: h5py.File):
        keys = [
            'Patient_ID', 'ReCIVA serial number', 'File_creation_time', 'Total collection time', 'Collection per tube L',
            'Flow rate upstream average ( >=5)', 'Flow rate downstream average ( >=5)', 'Cycle count',
            'Warning Left/Right sampling pump flowrate high', 'Warning Left/Right sampling pump flowrate low', 'Warning Sampling flow inconsistency downstream >> upstream R581',
            'Warning Sampling pump exceeding target flow rate flow high R575', 'Warning flow rate inconsistency downstream >> upstream'
        ]
        return {**self.extract_metadata(file), **self.extract_average_flows(file), 'Cycle count': self.extract_cycle_count(file), **self.extract_error_counts(file)}, keys

    def extract_metadata(self, file: h5py.File):
        res = {}
        if file:
            search_space = {
                'Collection_info': [
                    'Collection per tube L', 'Total collection time'
                ],
                'File_info': [
                    'Patient_ID', 'File_creation_time', 'ReCIVA serial number'
                ]
            }

            for group in search_space.keys():
                for attr in search_space[group]:
                    if group in file and attr in file[group].attrs:
                        s = file[group].attrs[attr]
                        res[attr] = s
        return res

    def extract_error_counts(self, file: h5py.File):
        res = {
            'Warning Left/Right sampling pump flowrate high': 0,
            'Warning Left/Right sampling pump flowrate low': 0,
            'Warning Sampling flow inconsistency downstream >> upstream R581': 0,
            'Warning Sampling pump exceeding target flow rate flow high R575': 0,
            'Warning flow rate inconsistency downstream >> upstream': 0,
            'Warning flow rate inconsistency upstream >> downstream': 0
        }
        parser = LogParser()
        if 'Status_log' in file:
            for line in file['Status_log']:
                time, msg = parser.extract_msg(line.decode('utf-8'))
                if msg in res.keys():
                    res[msg] += 1
        return res

    def extract_average_flows(self, file: h5py.File):
        average_up = None
        average_down = None
        if 'Data' in file and 'Flow rate L upstream' in file['Data'].dtype.names and 'Flow rate L downstream' in file['Data'].dtype.names:
            data = np.array([tuple(pair) for pair in file['Data'].fields(['Flow rate L upstream', 'Flow rate L downstream'])]).T

            if len(data.shape) > 1 and data.shape[1] > 0:
                average_up = np.mean(data[0, data[0, :] >= 5])
                average_down = np.mean(data[1, data[1, :] >= 5])
        return {'Flow rate upstream average ( >=5)': average_up, 'Flow rate downstream average ( >=5)': average_down}

    def extract_cycle_count(self, file: h5py.File):
        count = 0
        if 'Data' in file and 'Flow rate L upstream' in file['Data'].dtype.names and 'Flow rate L downstream' in file['Data'].dtype.names:
            n_measurements_active = 0
            for up, down in file['Data'].fields(['Flow rate L upstream', 'Flow rate L downstream']):
                flow = max(up, down)
                if flow < 20 and n_measurements_active >= 5:
                    count += 1
                    n_measurements_active = 0
                elif flow >= 100:
                    n_measurements_active += 1
        return count
