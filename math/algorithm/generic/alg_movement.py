from math.algorithm.algorithms import Algorithm

import numpy

from math.algorithm.utils import get_xyz, OVER_SAMPLES


class ActivityMovement(Algorithm):
    __algname__ = "activity_movement"
    __type__ = 'categorizer'
    __vers__ = '1.nov.2018'

    __place__ = ['any']
    __input__ = ['acc/3ax/4g']
    __output__ = ['general/data/time', 'peakl/count']

    @classmethod
    def analyse_data_chunks(cls, sensor_data, parameters):
        assert(len(sensor_data.data.shape) == 3) # required for 'chunk' type
        x, y, z, _ = get_xyz(sensor_data)
        # todo: force chunk
        l = x*x + y*y + z*z
        lsum = numpy.zeros((sensor_data.chunk_count(),1))
        for part in numpy.array_split(l, 3, axis=OVER_SAMPLES):
            OVER_PARTS = 1 # part is a dimension smaller than chunk, so this is last axis
            mx = numpy.amax(part, axis=OVER_PARTS)
            mn = numpy.amin(part, axis=OVER_PARTS)
            df = mx - mn
            lsum += df
        peakl = (lsum/3.0) * 10
        return numpy.hstack([numpy.ones([len(peakl), 1], dtype=numpy.int32), peakl.astype(numpy.int32)])
