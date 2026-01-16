

class LiveH5Reader(object):
    file = None
    filename = None
    next_data_index = None
    next_log_index = None
    target_labels = []
    time_label = 'Collection time'

    def __init__(self, file, target_labels):
        self.file = file
        self.target_labels = target_labels
        self.next_data_index = 0
        self.next_log_index = 0
        self.tol = 10
        self.complete = False



    def read_data(self):
        n_times_failed = 0
        while not self.complete:
            self.file['Data'].id.refresh()
            new_entries = self.read_all_data()

            if len(new_entries) == 0:
                if n_times_failed >= self.tol:
                    self.complete = True
                n_times_failed = n_times_failed + 1
                yield None
            else:
                n_times_failed = 0
                yield new_entries

        return None

    def read_all_data(self):
        dataset = self.file['Data']
        current_len = max(dataset.shape[0], 0)
        columns = [self.time_label] + self.target_labels
        new_entries = dataset.fields(columns)[self.next_data_index: max(0, current_len)]
        new_entries = [dict(zip(columns, entry)) for entry in new_entries]
        self.next_data_index = current_len
        return [entry for entry in new_entries if entry[self.time_label] != 0]


    def read_all_logs(self):
        log_list = []
        if not self.complete and self.file and 'Status_log' in self.file:
            self.file['Status_log'].id.refresh()
            current_len = max(self.file['Status_log'].shape[0], 0)
            log_list.extend(self.file['Status_log'][self.next_log_index:current_len])
            self.next_log_index = current_len
        log_list = [log.decode('utf-8') for log in log_list]
        return log_list



    def terminate(self):
        self.complete=True

