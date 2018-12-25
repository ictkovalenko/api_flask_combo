import numpy


OVER_CHUNK = 0
OVER_SAMPLES = 1


def get_xyz(sensor_data):
    data = sensor_data.samples()
    last_axis = len(data.shape) - 1
    x = data.take([0], axis=last_axis)
    y = data.take([1], axis=last_axis)
    z = data.take([2], axis=last_axis)
    try:
        valid = data.take([3], axis=last_axis)
    except:
        valid = numpy.ones(x.shape)
    valid_bool = (valid==False)
    x[valid_bool] = 0
    y[valid_bool] = 0
    z[valid_bool] = 0
    return x, y, z, valid
