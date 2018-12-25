import numpy
import struct

###############################################################
##
##
###############################################################

class DataFormatError(Exception):
    pass

# B0 nnxx.xxxx  ->
# B1 xxxx.yyyy
# B2 yyyy.yyzz  ->  ssss.ssyy.yyyy.yyyy
# B3 zzzz.zzzz

# ssss.ssxx              B0 >> 4 + SE
#           xxxx.xxxx    B0 << 4 + B1 >> 4
# ssss.ssyy              B1 >> 2 + SE
#           yyyy.yyyy <- B0 << 4
# ssss.sszz
#           zzzz.zzzz <- B0 << 4

# Take raw byte data. 3x10 bit in each 4x8 value
# return numpy int16
def unpack10bit(data):
    # Unpack into 10bit values
    if len(data) % 4:
        raise DataFormatError()

    a = numpy.ndarray(len(data) // 4 * 3, dtype = numpy.int16)

    for i in range(len(data) // 4):
        # 32bit int
        val = struct.unpack(">I", data[i*4:(i+1)*4])[0]

        a[i*3]   = ((val >> 20) & 0x1FF) - (val >> 20 & 0x200)
        a[i*3+1] = ((val >> 10) & 0x1FF) - (val >> 10 & 0x200)
        a[i*3+2] = ((val      ) & 0x1FF) - (val       & 0x200)

    return a

#10  = 0x 0A =    0000.1010
#50  = 0x 32 =    0011.0010
#100 = 0x 64 =    0110.0100
#500 = 0x1F4 = 01.1111.0100
#-500          10.0000.1100


#50, 100, 500
# 0000.0011 0010.0001 1001.0001 1111.0100
#        03        21        91        f4

#50, 100, -500
# 0000.0011 0010.0001 1001.0010 0000.1100
#        03        21        92        0C


#unpack10bit(bytearray([0x03, 0x21, 0x91, 0xf4]))
#print(unpack10bit(bytearray([0x03, 0x21, 0x92, 0x0c])))

