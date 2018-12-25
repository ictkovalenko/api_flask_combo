from .sensor_data import SensorData2


class SensorDataBundle(object):

    IS_BUNDLE = True

    def __init__(self, start_time, end_time, stream_type):
        self.start_time = start_time
        self.end_time = end_time
        self.stream_type = stream_type
        self.data = []

    def add(self, sensor_data):
        if self.start_time is None or self.start_time > sensor_data.start_time:
            self.start_time = sensor_data.start_time
        if self.end_time is None or self.end_time < sensor_data.end_time:
            self.end_time = sensor_data.end_time
        if sensor_data.has_data():
            self.data.append(sensor_data)

    def has_data(self):
        return len(self.data) != 0

    def data_parts(self):
        return len(self.data)

    def get_data(self, i =- 1):
        if not self.has_data():
            return SensorData2.empty(self.stream_type)
        if len(self.data) != 1:
            print("Sensor Len", len(self.data))
        #assert(len(self.data) == 1)
        return self.data[i]

    def __getitem__(self, idx):
        # Support direct indexing
        return self.get_data(idx)

    def __setitem__(self, idx, value):
        # Support setting via index
        self.data[idx] = value

    def __iter__(self):
        # Support iteration with e.g. for loops
        return iter(self.data)
