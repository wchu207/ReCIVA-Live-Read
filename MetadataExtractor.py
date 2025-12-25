import h5py

class MetadataExtractor:
    def __init__(self):
        pass

    def extract(self, file: h5py.File):
        return {**self.extract_metadata(file), 'Cycle count': self.extract_cycle_count(file)}

    def extract_metadata(self, file: h5py.File):
        res = {}
        if file:
            search_space = {
                'Collection_info': [
                    'Collection per tube L', 'Total collection time'
                ],
                'File_info': [
                    'File_creation_time', 'ReCIVA serial number'
                ]
            }

            for group in search_space.keys():
                for attr in search_space[group]:
                    if group in file and attr in file[group].attrs:
                        res[attr] = file[group].attrs[attr]
        return res

    def extract_error_counts(self, file: h5py.File):
        pass

    def extract_cycle_count(self, file: h5py.File):
        count = 0
        if 'Data' in file and 'Flow rate L upstream' in file['Data'].dtype.names and 'Flow rate L downstream' in file['Data'].dtype.names :
            n_measurements_active = 0
            for up, down in file['Data'].fields(['Flow rate L upstream', 'Flow rate L downstream']):
                flow = max(up, down)
                if flow < 20 and n_measurements_active >= 5:
                    count += 1
                    n_measurements_active = 0
                elif flow >= 100:
                    n_measurements_active += 1
        return count
