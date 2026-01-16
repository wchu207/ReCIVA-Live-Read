from datetime import datetime
import re


class LogParser:
    def __init__(self):
        self.initial_time = None

    def extract_msg(self, s):
        if s is not None:
            parts = s.split(', ')
            if len(parts) > 1:
                msg = ", ".join(parts[1:])
                msg = self.parse_msg(msg)
                return parts[0], msg
            elif len(parts) == 1:
                msg = self.parse_msg(parts[0])
                return None, msg
        return None, None

    def parse_msg(self, msg):
        msg = re.sub('[\\[\\]()]', '', msg)
        msg = re.sub('-', ' ', msg)
        return msg

    def extract_time(self, s):
        if s is not None:
            parts = s.split("+")
            if len(parts) > 1:
                time = datetime.strptime(parts[0], '%Y-%m-%dT%H:%M:%S')
                return time
        return None

    def get_warnings_and_errors(self, logs):
        warnings = []
        errors = []
        if self.initial_time is not None:
            for log in logs:
                time, msg = self.extract_msg(log)
                if time is not None and msg is not None:
                    if msg.startswith('Warning'):
                        time = (self.extract_time(time) - self.initial_time).total_seconds()
                        if time >= 0:
                            warnings.append(time / 60)
                    elif msg.startswith('Error'):
                        time = (self.extract_time(time) - self.initial_time).total_seconds()
                        if time >= 0:
                            errors.append(time / 60)
        return warnings, errors

    def set_initial_time(self, logs):
        for log in logs:
            time, msg = self.extract_msg(log)
            if 'Wait in progress' in log:
                self.initial_time = self.extract_time(time)

    def get_prefix(self, time):
        prefix = ''
        if self.initial_time is not None and time is not None:
            time_diff = (time - self.initial_time).total_seconds()
            if time_diff >= 0:
                minutes = int(time_diff // 60)
                seconds = int(time_diff % 60)
                prefix = '[{:02d}:{:02d}] '.format(minutes, seconds)
        return prefix
