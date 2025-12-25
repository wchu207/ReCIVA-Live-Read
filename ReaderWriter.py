import h5py
import threading
import time
from tqdm import tqdm

class ReaderWriter(object):
    def __init__(self, src, dst):
        self.src_path = src
        self.dst_path = dst

        self.src_file = h5py.File(self.src_path, 'r', libver='latest')
        self.dst_file = h5py.File(self.dst_path, 'w', libver='latest', locking=False)
        self.dst_file.create_dataset('Data', shape=(0,), maxshape=(None,), dtype=self.src_file['Data'].dtype)
        self.dst_file.create_dataset('Status_log', shape=(0,), maxshape=(None,), dtype=self.src_file['Status_log'].dtype)
        self.dst_file.swmr_mode=True

        self.thread = None

    def convert(self):
        self.thread = threading.Thread(target=self.convert_impl)
        self.thread.start()

    def convert_impl(self):
        dataset = self.src_file['Data']
        logs = self.src_file['Status_log']

        for i in tqdm(range(logs.shape[0])):
            self.dst_file['Status_log'].resize((i + 1, ))
            self.dst_file['Status_log'][i] = logs[i]
            self.dst_file['Status_log'].flush()
            time.sleep(0.15)


        for i in tqdm(range(dataset.shape[0])):
            entry = dataset[i]
            self.dst_file['Data'].resize((i + 1,))
            self.dst_file['Data'][i] = entry
            self.dst_file['Data'].flush()
            time.sleep(0.05)



    def close(self):
        if self.thread is not None:
            self.thread.join()
            self.src_file.close()
            self.dst_file.close()
