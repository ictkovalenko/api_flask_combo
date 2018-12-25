import numpy
import struct

CNT11 = 0
CNT10 = 0
CNT7 = 0
CNT5 = 0
CNT2 = 0

IDLE_MIN_LEN = 12
IDLE_WINDOW = 8

# pack an x-width value into an integer
def packval(val, offset, width):
    # Max is width
    limit = 2**(width-1)
    #print("Max", limit)
    assert((val < limit) and (val >= -limit))
    signbits = 0x01 << (width-1)
    valbits = signbits-1
    #print("%02X, %02X" % (signbits, valbits))
    if (val < 0):
        val = limit*2 + val
    return (val << offset)


# pack an unsigned x-width value into an integer
def packuval(val, offset, width):
    # Max is width
    limit = 2**(width)
    #print("Max", limit)
    assert((val < limt) and (val >= 0))
    #print("%02X, %02X" % (signbits, valbits))
    return (val << offset)


# Extract an x-width signed value from a byte array
def unpackval(data, offset, width):
    while len(data) < 4:
        data = bytearray([0]) + data
    val = struct.unpack(">I", data)[0]
    signbits = 0x01 << (width-1)
    valbits = signbits-1
    v = ((val >> offset) & valbits) - ((val >> offset) & signbits)
    return v


# Extract an unsigned x-width signed value from a byte array
def unpackuval(data, offset, width):
    while len(data) < 4:
        data = bytearray([0]) + data
    val = struct.unpack(">I", data)[0]
    signbits = 0x01 << (width)
    valbits = signbits-1
    v = ((val >> offset) & valbits)
    return v


def unpackvals(data, width):
    while len(data) < 8:
        data = bytearray([0]) + data
    val = struct.unpack(">Q", data)[0]
    signbits = 0x01 << (width-1)
    valbits = signbits-1
    offset = width*2
    vx = ((val >> offset) & valbits) - ((val >> offset) & signbits)
    offset = width
    vy = ((val >> offset) & valbits) - ((val >> offset) & signbits)
    offset = 0
    vz = ((val >> offset) & valbits) - ((val >> offset) & signbits)
    return numpy.array([vx, vy, vz])


# Packs a xyz value into integer
def packvals(xyz, width):
    return packval(xyz[0], width*2, width) | packval(xyz[1], width, width) | packval(xyz[2], 0, width)


# Splits an integer into with_bytes seperate bytes
def tobytes(val, width_bytes):
    d = bytearray([])
    while width_bytes != 0:
        d = bytearray([chr(val & 0xFF)]) + d
        val = val >> 8
        width_bytes -= 1
    assert(val == 0)
    return d


def frame_11(xyz):
    return tobytes(packvals(xyz, 11) | 0xFC00000000, 5)


def frame_10(xyz):
    return tobytes(packvals(xyz, 10) | 0x80000000, 4)


def frame_5(xyz):
    return tobytes(packvals(xyz, 5), 2)


def frame_7(xyz):
    return tobytes(packvals(xyz, 7) | 0xC00000, 3)


def frame_idle(l):
    return tobytes(0xF000 | l-1, 2)


def within(val, valn, width):
    limit = 2**(width-1)
    return (val < limit) and (val >= -limit) and (valn < limit) and (valn >= -limit)


def compress(in_data, max_samples = 4000, max_packetsize = 1024):
    #  Frames
    #  0.X.X.X-X.X.Y.Y  Y.Y.Y.Z-Z.Z.Z.Z                                   (2 bytes, each sample 5 bits)
    #  1.0.X.X-X.X.X.X  X.X.X.X-Y.Y.Y.Y  Y.Y.Y.Y-Y.Y.Z.Z  Z.Z.Z.Z-Z.Z.Z.Z (4 bytes, each sample 10 bits)
    #  1.1.0.X-X.X.X.X  X.X.Y.Y-Y.Y.Y.Y  Y.Z.Z.Z-Z.Z.Z.Z                  (3 bytes, each sample 7 bits)
    #  1.1.1.0-I.I.I.I                                                    (NOT USED, 1 byte, 0-15 samples within window)
    #  1.1.1.1-0.I.I.I  I.I.I.I-I.I.I.I                                   (2 bytes, 2048 samples within window)
    #  1.1.1.1-1.0.?.?                                                    (Free)
    #  1.1.1.1-1.1.0.X  X.X.X.X-X.X.X.X  X.X.Y.Y-Y.Y.Y.Y  Y.Y.Y.Y-Y.Z.Z.Z  Z.Z.Z.Z-Z.Z.Z.Z (5 b, each 11 bits, abs)
    #  1.1.1.1-1.1.1.0  L.L.L.L-L.L.L.L                                   (Ignore L bytes)
    #  1.1.1.1-1.1.1.1                                                    (Free, BOUNDARY FILL)
    #
    # Now:
    # 11 bit = +-8G --> 2048
    #            8G --> 1024
    #            4G --> 512
    #            2G --> 256
    #            1G --> 128
    #
    # Before:
    # 10 bit = 4G --> 512
    #          2G --> 256
    #          1G --> 128
    data = bytearray([])
    prev = numpy.array([0,0,0])
    i = 0
    i_returned = 0
    while i < len(in_data):
        cur = in_data[i]
        x = cur[0]
        y = cur[1]
        z = cur[2]
        did_idle = False
        if len(data) == 0:
            data += frame_11(cur)
            #print(i, "B11")
        else:
            diff = cur - prev
            diffmin = min(diff)
            diffmax = max(diff)
            # lookahead
            l = 0
            while True:
                if (i + l) >= len(in_data) or (i - i_returned + l) >= max_samples or len(data) >= max_packetsize-6:
                    break;
                diff2 = in_data[i+l] - prev
                diff2abs = max(-min(diff2), max(diff2))
                if l == 2048:
                    break
                elif diff2abs > IDLE_WINDOW:
                    break
                l += 1
            l += -0
            if l >= IDLE_MIN_LEN:
                #print(i, "Idle", l)
                data += frame_idle(l)
                i += l - 1
                did_idle = True
            elif within(diffmax, diffmin, 5):
                #print(i, "B5")
                data += frame_5(diff)
            elif within(diffmax, diffmin, 7):
                #print(i, "B7")
                data += frame_7(diff)
            elif within(diffmax, diffmin, 10):
                #print(i, "B10")
                data += frame_10(diff)
            else:
                data += frame_11(cur)
        if not did_idle:
            prev = in_data[i]
        i += 1
        if (i - i_returned) >= max_samples or len(data) >= max_packetsize - 4:
            #print("YIELD", len(data), i, i_returned)
            yield data
            data = bytearray([])
            i_returned = i
    #print(len(data), len(in_data)*4)
    #print("YIELD", len(data), i, i_returned)
    yield data


def analyze_compressed(data):
    i = 0
    i_ = 0
    j = 0
    ret = []
    tx = 0
    while i < len(data):
        d = data[i]
        # Check frame
        if True:
            value = None
            if ((0x80 & d) == 0): # B5 frame
                i += 2
                j += 1
            elif (0x40 & d) == 0: #B10
                i += 4
                j += 1
            elif (0x20 & d) == 0: #B7
                i += 3
                j += 1
            elif (0x10 & d) == 0: #BI1
                value = unpackuval(data[i:i+1], 0, 4) + 6
                i += 1
                j += value
            elif (0x08 & d) == 0: #BI2
                value = unpackuval(data[i:i+2], 0, 11) + 1
                i += 2
                j += value
            elif (0x02 & d) == 0: #B11
                i += 5
                j += 1
            elif (0x01 & d) == 0: #Ignore
                #print("Ignoring ", data[i+1], j)
                if tx != 0:
                    ret += [(tx, j, i - i_)]
                    j = 0
                    i_ = i
                tx = data[i+2] * 0x1000000 + data[i+3] * 0x10000 + data[i+4] * 0x100 + data[i+5]
                i += 2 + data[i+1]
            elif d == 0xFF:
                i += 1
                #print("FF ", j)
            else:
                assert "Unexpected %02X" % d
            pass
    ret += [(tx, j, i - i_)]
    return ret




def decompress(data):
    i = 0
    j = 0
    ref = numpy.array([0,0,0], dtype=numpy.int16)
    res = numpy.zeros([1000000,3], dtype=numpy.int16)
    while i < len(data):
        d = data[i]
        # Check frame
        if True:
            value = None
            if ((0x80 & d) == 0): # B5 frame
                value = unpackvals(data[i:i+2], 5)
                i += 2
                ref += value
                res[j] = ref
                j += 1
                #print("B5 ", ref/500.0*4.0, value/500.0*4.0, j)
            elif (0x40 & d) == 0: #B10
                value = unpackvals(data[i:i+4], 10)
                i += 4
                ref += value
                res[j] = ref
                j += 1
                #print("B10", ref/500.0*4.0, value/500.0*4.0, j, i)
            elif (0x20 & d) == 0: #B7
                value = unpackvals(data[i:i+3], 7)
                i += 3
                ref += value
                res[j] = ref
                j += 1
                #print("B7 ", ref/500.0*4.0, value/500.0*4.0, j)
            elif (0x10 & d) == 0: #BI1
                #assert(False)
                value = unpackuval(data[i:i+1], 0, 4) + 6
                i += 1
                res[j:j+value] = ref
                j += value
                #print("B.1", ref/500.0*4.0, j, value)
            elif (0x08 & d) == 0: #BI2
                value = unpackuval(data[i:i+2], 0, 11) + 1
                i += 2
                res[j:j+value] = ref
                j += value
                #print("B.2", ref/500.0*4.0, j, value)
            elif (0x02 & d) == 0: #B11
                value = unpackvals(data[i:i+5], 11)
                i += 5
                ref = value
                res[j] = ref
                j += 1
                #print("B11", value/500.0*4.0, j, i)
            elif (0x01 & d) == 0: #Ignore
                #print("Ignoring ", data[i+1])
                i += 2 + data[i+1]
            elif d == 0xFF:
                i += 1
                #print("FF ", j)
            else:
                assert "Unexpected %02X" % d
            pass
    return res[:j, :]

