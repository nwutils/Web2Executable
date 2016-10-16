"""A module to parse the contents of an ICNS file."""

import struct
import image_utils.image_utils as image_utils
import image_utils.png as png
from PIL import Image
import os
from io import BytesIO

#---------------------CONSTANTS-----------------------------------------------#

ICNS_TABLE_OF_CONTENTS = 0x544F4320  # "TOC "

ICNS_ICON_VERSION = 0x69636E56  # "icnV"

ICNS_1024x1024_32BIT_ARGB_DATA = 0x69633130  # "ic10"

ICNS_512x512_32BIT_ARGB_DATA = 0x69633039  # "ic09"
ICNS_256x256_32BIT_ARGB_DATA = 0x69633038  # "ic08"

ICNS_128x128_32BIT_DATA = 0x69743332  # "it32"
ICNS_128x128_8BIT_MASK = 0x74386D6B  # "t8mk"

ICNS_48x48_1BIT_DATA = 0x69636823  # "ich#"
ICNS_48x48_4BIT_DATA = 0x69636834  # "ich4"
ICNS_48x48_8BIT_DATA = 0x69636838  # "ich8"
ICNS_48x48_32BIT_DATA = 0x69683332  # "ih32"
ICNS_48x48_1BIT_MASK = 0x69636823  # "ich#"
ICNS_48x48_8BIT_MASK = 0x68386D6B  # "h8mk"

ICNS_32x32_1BIT_DATA = 0x49434E23  # "ICN#"
ICNS_32x32_4BIT_DATA = 0x69636C34  # "icl4"
ICNS_32x32_8BIT_DATA = 0x69636C38  # "icl8"
ICNS_32x32_32BIT_DATA = 0x696C3332  # "il32"
ICNS_32x32_1BIT_MASK = 0x49434E23  # "ICN#"
ICNS_32x32_8BIT_MASK = 0x6C386D6B  # "l8mk"

ICNS_16x16_1BIT_DATA = 0x69637323  # "ics#"
ICNS_16x16_4BIT_DATA = 0x69637334  # "ics4"
ICNS_16x16_8BIT_DATA = 0x69637338  # "ics8"
ICNS_16x16_32BIT_DATA = 0x69733332  # "is32"
ICNS_16x16_1BIT_MASK = 0x69637323  # "ics#"
ICNS_16x16_8BIT_MASK = 0x73386D6B  # "s8mk"

ICNS_16x12_1BIT_DATA = 0x69636D23  # "icm#"
ICNS_16x12_4BIT_DATA = 0x69636D34  # "icm4"
ICNS_16x12_1BIT_MASK = 0x69636D23  # "icm#"
ICNS_16x12_8BIT_DATA = 0x69636D38  # "icm8"

ICNS_32x32_1BIT_ICON = 0x49434F4E  # "ICON"

ICNS_TILE_VARIANT = 0x74696C65  # "tile"
ICNS_ROLLOVER_VARIANT = 0x6F766572  # "over"
ICNS_DROP_VARIANT = 0x64726F70  # "drop"
ICNS_OPEN_VARIANT = 0x6F70656E  # "open"
ICNS_OPEN_DROP_VARIANT = 0x6F647270  # "odrp"

ICNS_NULL_DATA = 0x00000000
ICNS_NULL_MASK = 0x00000000

# icns file / resource type constants

ICNS_FAMILY_TYPE = 0x69636E73  # "icns"

ICNS_MACBINARY_TYPE = 0x6D42494E  # "mBIN"

ICNS_NULL_TYPE = 0x00000000

ICNS_BYTE_BITS = 8

# icns error return values

ICNS_STATUS_OK = 0

ICNS_STATUS_NULL_PARAM = -1
ICNS_STATUS_NO_MEMORY = -2
ICNS_STATUS_INVALID_DATA = -3

ICNS_STATUS_IO_READ_ERR = 1
ICNS_STATUS_IO_WRITE_ERR = 2
ICNS_STATUS_DATA_NOT_FOUND = 3
ICNS_STATUS_UNSUPPORTED = 4

#---------------------------SYMBOL DICTS-------------------------------------#

struct_symbols = {1: 'B',  # byte
                  2: 'H',  # word
                  4: 'I',  # unsigned int/double word
                  8: 'Q'  # quad word
                  }

#used to easily get the icon type from dimensions
type_dict = {'mask': {128: {8: ICNS_128x128_8BIT_MASK},
             48: {1: ICNS_48x48_1BIT_MASK,
                  8: ICNS_48x48_8BIT_MASK},
             32: {1: ICNS_32x32_1BIT_MASK,
                  8: ICNS_32x32_8BIT_MASK},
             16: {1: ICNS_16x16_1BIT_MASK,
                  8: ICNS_16x16_8BIT_MASK},
             },
      'data': {1024: {32: ICNS_1024x1024_32BIT_ARGB_DATA},
               512: {32: ICNS_512x512_32BIT_ARGB_DATA},
               256: {32: ICNS_256x256_32BIT_ARGB_DATA},
               128: {32: ICNS_128x128_32BIT_DATA},
               48: {1: ICNS_48x48_1BIT_DATA,
                    4: ICNS_48x48_4BIT_DATA,
                    8: ICNS_48x48_8BIT_DATA,
                    32: ICNS_48x48_32BIT_DATA},
               32: {1: ICNS_32x32_1BIT_DATA,
                    4: ICNS_32x32_4BIT_DATA,
                    8: ICNS_32x32_8BIT_DATA,
                    32: ICNS_32x32_32BIT_DATA},
               16: {1: ICNS_16x16_1BIT_DATA,
                    4: ICNS_16x16_4BIT_DATA,
                    8: ICNS_16x16_8BIT_DATA,
                    32: ICNS_16x16_32BIT_DATA},
              }}


icns_colormap_4 = [
   [0xFF, 0xFF, 0xFF],
   [0xFC, 0xF3, 0x05],
   [0xFF, 0x64, 0x02],
   [0xDD, 0x08, 0x06],
   [0xF2, 0x08, 0x84],
   [0x46, 0x00, 0xA5],
   [0x00, 0x00, 0xD4],
   [0x02, 0xAB, 0xEA],
   [0x1F, 0xB7, 0x14],
   [0x00, 0x64, 0x11],
   [0x56, 0x2C, 0x05],
   [0x90, 0x71, 0x3A],
   [0xC0, 0xC0, 0xC0],
   [0x80, 0x80, 0x80],
   [0x40, 0x40, 0x40],
   [0x00, 0x00, 0x00]
]

icns_colormap_8 =[
   [0xFF, 0xFF, 0xFF],
   [0xFF, 0xFF, 0xCC],
   [0xFF, 0xFF, 0x99],
   [0xFF, 0xFF, 0x66],
   [0xFF, 0xFF, 0x33],
   [0xFF, 0xFF, 0x00],
   [0xFF, 0xCC, 0xFF],
   [0xFF, 0xCC, 0xCC],
   [0xFF, 0xCC, 0x99],
   [0xFF, 0xCC, 0x66],
   [0xFF, 0xCC, 0x33],
   [0xFF, 0xCC, 0x00],
   [0xFF, 0x99, 0xFF],
   [0xFF, 0x99, 0xCC],
   [0xFF, 0x99, 0x99],
   [0xFF, 0x99, 0x66],
   [0xFF, 0x99, 0x33],
   [0xFF, 0x99, 0x00],
   [0xFF, 0x66, 0xFF],
   [0xFF, 0x66, 0xCC],
   [0xFF, 0x66, 0x99],
   [0xFF, 0x66, 0x66],
   [0xFF, 0x66, 0x33],
   [0xFF, 0x66, 0x00],
   [0xFF, 0x33, 0xFF],
   [0xFF, 0x33, 0xCC],
   [0xFF, 0x33, 0x99],
   [0xFF, 0x33, 0x66],
   [0xFF, 0x33, 0x33],
   [0xFF, 0x33, 0x00],
   [0xFF, 0x00, 0xFF],
   [0xFF, 0x00, 0xCC],
   [0xFF, 0x00, 0x99],
   [0xFF, 0x00, 0x66],
   [0xFF, 0x00, 0x33],
   [0xFF, 0x00, 0x00],
   [0xCC, 0xFF, 0xFF],
   [0xCC, 0xFF, 0xCC],
   [0xCC, 0xFF, 0x99],
   [0xCC, 0xFF, 0x66],
   [0xCC, 0xFF, 0x33],
   [0xCC, 0xFF, 0x00],
   [0xCC, 0xCC, 0xFF],
   [0xCC, 0xCC, 0xCC],
   [0xCC, 0xCC, 0x99],
   [0xCC, 0xCC, 0x66],
   [0xCC, 0xCC, 0x33],
   [0xCC, 0xCC, 0x00],
   [0xCC, 0x99, 0xFF],
   [0xCC, 0x99, 0xCC],
   [0xCC, 0x99, 0x99],
   [0xCC, 0x99, 0x66],
   [0xCC, 0x99, 0x33],
   [0xCC, 0x99, 0x00],
   [0xCC, 0x66, 0xFF],
   [0xCC, 0x66, 0xCC],
   [0xCC, 0x66, 0x99],
   [0xCC, 0x66, 0x66],
   [0xCC, 0x66, 0x33],
   [0xCC, 0x66, 0x00],
   [0xCC, 0x33, 0xFF],
   [0xCC, 0x33, 0xCC],
   [0xCC, 0x33, 0x99],
   [0xCC, 0x33, 0x66],
   [0xCC, 0x33, 0x33],
   [0xCC, 0x33, 0x00],
   [0xCC, 0x00, 0xFF],
   [0xCC, 0x00, 0xCC],
   [0xCC, 0x00, 0x99],
   [0xCC, 0x00, 0x66],
   [0xCC, 0x00, 0x33],
   [0xCC, 0x00, 0x00],
   [0x99, 0xFF, 0xFF],
   [0x99, 0xFF, 0xCC],
   [0x99, 0xFF, 0x99],
   [0x99, 0xFF, 0x66],
   [0x99, 0xFF, 0x33],
   [0x99, 0xFF, 0x00],
   [0x99, 0xCC, 0xFF],
   [0x99, 0xCC, 0xCC],
   [0x99, 0xCC, 0x99],
   [0x99, 0xCC, 0x66],
   [0x99, 0xCC, 0x33],
   [0x99, 0xCC, 0x00],
   [0x99, 0x99, 0xFF],
   [0x99, 0x99, 0xCC],
   [0x99, 0x99, 0x99],
   [0x99, 0x99, 0x66],
   [0x99, 0x99, 0x33],
   [0x99, 0x99, 0x00],
   [0x99, 0x66, 0xFF],
   [0x99, 0x66, 0xCC],
   [0x99, 0x66, 0x99],
   [0x99, 0x66, 0x66],
   [0x99, 0x66, 0x33],
   [0x99, 0x66, 0x00],
   [0x99, 0x33, 0xFF],
   [0x99, 0x33, 0xCC],
   [0x99, 0x33, 0x99],
   [0x99, 0x33, 0x66],
   [0x99, 0x33, 0x33],
   [0x99, 0x33, 0x00],
   [0x99, 0x00, 0xFF],
   [0x99, 0x00, 0xCC],
   [0x99, 0x00, 0x99],
   [0x99, 0x00, 0x66],
   [0x99, 0x00, 0x33],
   [0x99, 0x00, 0x00],
   [0x66, 0xFF, 0xFF],
   [0x66, 0xFF, 0xCC],
   [0x66, 0xFF, 0x99],
   [0x66, 0xFF, 0x66],
   [0x66, 0xFF, 0x33],
   [0x66, 0xFF, 0x00],
   [0x66, 0xCC, 0xFF],
   [0x66, 0xCC, 0xCC],
   [0x66, 0xCC, 0x99],
   [0x66, 0xCC, 0x66],
   [0x66, 0xCC, 0x33],
   [0x66, 0xCC, 0x00],
   [0x66, 0x99, 0xFF],
   [0x66, 0x99, 0xCC],
   [0x66, 0x99, 0x99],
   [0x66, 0x99, 0x66],
   [0x66, 0x99, 0x33],
   [0x66, 0x99, 0x00],
   [0x66, 0x66, 0xFF],
   [0x66, 0x66, 0xCC],
   [0x66, 0x66, 0x99],
   [0x66, 0x66, 0x66],
   [0x66, 0x66, 0x33],
   [0x66, 0x66, 0x00],
   [0x66, 0x33, 0xFF],
   [0x66, 0x33, 0xCC],
   [0x66, 0x33, 0x99],
   [0x66, 0x33, 0x66],
   [0x66, 0x33, 0x33],
   [0x66, 0x33, 0x00],
   [0x66, 0x00, 0xFF],
   [0x66, 0x00, 0xCC],
   [0x66, 0x00, 0x99],
   [0x66, 0x00, 0x66],
   [0x66, 0x00, 0x33],
   [0x66, 0x00, 0x00],
   [0x33, 0xFF, 0xFF],
   [0x33, 0xFF, 0xCC],
   [0x33, 0xFF, 0x99],
   [0x33, 0xFF, 0x66],
   [0x33, 0xFF, 0x33],
   [0x33, 0xFF, 0x00],
   [0x33, 0xCC, 0xFF],
   [0x33, 0xCC, 0xCC],
   [0x33, 0xCC, 0x99],
   [0x33, 0xCC, 0x66],
   [0x33, 0xCC, 0x33],
   [0x33, 0xCC, 0x00],
   [0x33, 0x99, 0xFF],
   [0x33, 0x99, 0xCC],
   [0x33, 0x99, 0x99],
   [0x33, 0x99, 0x66],
   [0x33, 0x99, 0x33],
   [0x33, 0x99, 0x00],
   [0x33, 0x66, 0xFF],
   [0x33, 0x66, 0xCC],
   [0x33, 0x66, 0x99],
   [0x33, 0x66, 0x66],
   [0x33, 0x66, 0x33],
   [0x33, 0x66, 0x00],
   [0x33, 0x33, 0xFF],
   [0x33, 0x33, 0xCC],
   [0x33, 0x33, 0x99],
   [0x33, 0x33, 0x66],
   [0x33, 0x33, 0x33],
   [0x33, 0x33, 0x00],
   [0x33, 0x00, 0xFF],
   [0x33, 0x00, 0xCC],
   [0x33, 0x00, 0x99],
   [0x33, 0x00, 0x66],
   [0x33, 0x00, 0x33],
   [0x33, 0x00, 0x00],
   [0x00, 0xFF, 0xFF],
   [0x00, 0xFF, 0xCC],
   [0x00, 0xFF, 0x99],
   [0x00, 0xFF, 0x66],
   [0x00, 0xFF, 0x33],
   [0x00, 0xFF, 0x00],
   [0x00, 0xCC, 0xFF],
   [0x00, 0xCC, 0xCC],
   [0x00, 0xCC, 0x99],
   [0x00, 0xCC, 0x66],
   [0x00, 0xCC, 0x33],
   [0x00, 0xCC, 0x00],
   [0x00, 0x99, 0xFF],
   [0x00, 0x99, 0xCC],
   [0x00, 0x99, 0x99],
   [0x00, 0x99, 0x66],
   [0x00, 0x99, 0x33],
   [0x00, 0x99, 0x00],
   [0x00, 0x66, 0xFF],
   [0x00, 0x66, 0xCC],
   [0x00, 0x66, 0x99],
   [0x00, 0x66, 0x66],
   [0x00, 0x66, 0x33],
   [0x00, 0x66, 0x00],
   [0x00, 0x33, 0xFF],
   [0x00, 0x33, 0xCC],
   [0x00, 0x33, 0x99],
   [0x00, 0x33, 0x66],
   [0x00, 0x33, 0x33],
   [0x00, 0x33, 0x00],
   [0x00, 0x00, 0xFF],
   [0x00, 0x00, 0xCC],
   [0x00, 0x00, 0x99],
   [0x00, 0x00, 0x66],
   [0x00, 0x00, 0x33],
   [0xEE, 0x00, 0x00],
   [0xDD, 0x00, 0x00],
   [0xBB, 0x00, 0x00],
   [0xAA, 0x00, 0x00],
   [0x88, 0x00, 0x00],
   [0x77, 0x00, 0x00],
   [0x55, 0x00, 0x00],
   [0x44, 0x00, 0x00],
   [0x22, 0x00, 0x00],
   [0x11, 0x00, 0x00],
   [0x00, 0xEE, 0x00],
   [0x00, 0xDD, 0x00],
   [0x00, 0xBB, 0x00],
   [0x00, 0xAA, 0x00],
   [0x00, 0x88, 0x00],
   [0x00, 0x77, 0x00],
   [0x00, 0x55, 0x00],
   [0x00, 0x44, 0x00],
   [0x00, 0x22, 0x00],
   [0x00, 0x11, 0x00],
   [0x00, 0x00, 0xEE],
   [0x00, 0x00, 0xDD],
   [0x00, 0x00, 0xBB],
   [0x00, 0x00, 0xAA],
   [0x00, 0x00, 0x88],
   [0x00, 0x00, 0x77],
   [0x00, 0x00, 0x55],
   [0x00, 0x00, 0x44],
   [0x00, 0x00, 0x22],
   [0x00, 0x00, 0x11],
   [0xEE, 0xEE, 0xEE],
   [0xDD, 0xDD, 0xDD],
   [0xBB, 0xBB, 0xBB],
   [0xAA, 0xAA, 0xAA],
   [0x88, 0x88, 0x88],
   [0x77, 0x77, 0x77],
   [0x55, 0x55, 0x55],
   [0x44, 0x44, 0x44],
   [0x22, 0x22, 0x22],
   [0x11, 0x11, 0x11],
   [0x00, 0x00, 0x00]
]


#---------------------------UTILITY FUNCTIONS---------------------------------#

def encode_rle24(data):
    dataRun = bytearray(130)
    dataInChanSize = int(len(data)/4)
    dataTempCount = 0

    dataTemp = bytearray(int(len(data) + dataInChanSize))

    if len(data) >= 65536:
        dataTempCount = 4

    for colorOffset in range(3):
        runCount = 0
        runLength = 1
        runType = 0
        dataRun[0] = data[colorOffset]

        for dataInCount in range(1, dataInChanSize):
            dataByte = data[colorOffset+(dataInCount*4)]
            if runLength < 2:
                dataRun[runLength] = dataByte
                runLength += 1
            elif runLength == 2:
                if dataByte == dataRun[runLength-1] and dataByte == dataRun[runLength-2]:
                    runType = 1
                else:
                    runType = 0
                dataRun[runLength] = dataByte
                runLength += 1
            else:
                if runType == 0 and runLength < 128:
                    if dataByte == dataRun[runLength-1] and dataByte == dataRun[runLength -2]:
                        dataTemp[dataTempCount] = runLength - 3
                        dataTempCount += 1
                        dataTemp[dataTempCount:dataTempCount+runLength-2] = dataRun[:runLength-2]
                        dataTempCount += runLength - 2
                        runCount += 1

                        dataRun[0] = dataRun[runLength - 2]
                        dataRun[1] = dataRun[runLength - 1]
                        dataRun[2] = dataByte
                        runLength = 3
                        runType = 1
                    else:
                        dataRun[runLength] = dataByte
                        runLength += 1
                elif runType == 1 and runLength < 130:
                    if dataByte == dataRun[runLength - 1] and dataByte == dataRun[runLength - 2]:
                        dataRun[runLength] = dataByte
                        runLength += 1
                    else:
                        dataTemp[dataTempCount] = runLength + 125
                        dataTempCount += 1

                        dataTemp[dataTempCount] = dataRun[0]
                        dataTempCount += 1
                        runCount += 1

                        dataRun[0] = dataByte
                        runLength = 1
                        runType = 0
                else:
                    if runType == 0:
                        dataTemp[dataTempCount] = runLength - 1
                        dataTempCount += 1

                        dataTemp[dataTempCount:dataTempCount+runLength] = dataRun[:runLength]
                        dataTempCount = dataTempCount + runLength
                    elif runType == 1:
                        dataTemp[dataTempCount] = runLength + 125
                        dataTempCount += 1

                        dataTemp[dataTempCount] = dataRun[0]
                        dataTempCount += 1
                    runCount += 1

                    dataRun[0] = dataByte
                    runLength = 1
                    runType = 0
        if runLength > 0:
            if runType == 0:
                dataTemp[dataTempCount] = runLength - 1
                dataTempCount += 1

                dataTemp[dataTempCount:dataTempCount+runLength] = dataRun[:runLength]
                dataTempCount = dataTempCount + runLength
            elif runType == 1:
                dataTemp[dataTempCount] = runLength + 125
                dataTempCount += 1

                dataTemp[dataTempCount] = dataRun[0]
                dataTempCount += 1
            runCount += 1

    return dataTemp[:dataTempCount]

def decode_rle24(data, pixel_count):
    color_value = 0
    run_length = 0
    data_offset = 0
    pixel_offset = 0
    i = 0
    dest_icon_data = bytearray(int(pixel_count*4))

    if from_bytes(data[:4]) == 0:
        data_offset = 4
    color_offset = 0
    while color_offset < 3:
        pixel_offset = 0
        while (pixel_offset < pixel_count) and (data_offset < len(data)):
            if ((data[data_offset] & 0x80) == 0):
                run_length = (0xFF & data[data_offset]) + 1
                data_offset += 1
                i = 0
                while (i < run_length) and (pixel_offset < pixel_count) and (data_offset < len(data)):
                    dest_icon_data[(pixel_offset*4)+color_offset] = data[data_offset]
                    pixel_offset += 1
                    data_offset += 1
                    i += 1
            else:
                run_length = (0xFF & data[data_offset]) - 125
                data_offset += 1
                color_value = data[data_offset]
                data_offset += 1
                i = 0
                while (i < run_length) and (pixel_offset < pixel_count):
                    dest_icon_data[(pixel_offset*4)+color_offset] = color_value
                    pixel_offset += 1
                    i += 1
        color_offset += 1

    return dest_icon_data


def get_mask_type_for_icon_type(icon_type):
    if icon_type == ICNS_TABLE_OF_CONTENTS or\
       icon_type == ICNS_ICON_VERSION or\
       icon_type == ICNS_1024x1024_32BIT_ARGB_DATA or\
       icon_type == ICNS_512x512_32BIT_ARGB_DATA or\
       icon_type == ICNS_256x256_32BIT_ARGB_DATA:
        return ICNS_NULL_MASK

    if icon_type == ICNS_128x128_32BIT_DATA:
        return ICNS_128x128_8BIT_MASK
    if icon_type == ICNS_48x48_32BIT_DATA:
        return ICNS_48x48_8BIT_MASK
    if icon_type == ICNS_32x32_32BIT_DATA:
        return ICNS_32x32_8BIT_MASK
    if icon_type == ICNS_16x16_32BIT_DATA:
        return ICNS_16x16_8BIT_MASK

    # 8-bit image types - 1-bit mask types
    if icon_type == ICNS_48x48_8BIT_DATA:
        return ICNS_48x48_1BIT_MASK
    if icon_type == ICNS_32x32_8BIT_DATA:
        return ICNS_32x32_1BIT_MASK
    if icon_type == ICNS_16x16_8BIT_DATA:
        return ICNS_16x16_1BIT_MASK
    if icon_type == ICNS_16x12_8BIT_DATA:
        return ICNS_16x12_1BIT_MASK

    # 4 bit image types - 1-bit mask types
    if icon_type == ICNS_48x48_4BIT_DATA:
        return ICNS_48x48_1BIT_MASK
    if icon_type == ICNS_32x32_4BIT_DATA:
        return ICNS_32x32_1BIT_MASK
    if icon_type == ICNS_16x16_4BIT_DATA:
        return ICNS_16x16_1BIT_MASK
    if icon_type == ICNS_16x12_4BIT_DATA:
        return ICNS_16x12_1BIT_MASK

    # 1 bit image types - 1-bit mask types
    if icon_type == ICNS_48x48_1BIT_DATA:
        return ICNS_48x48_1BIT_MASK
    if icon_type == ICNS_32x32_1BIT_DATA:
        return ICNS_32x32_1BIT_MASK
    if icon_type == ICNS_16x16_1BIT_DATA:
        return ICNS_16x16_1BIT_MASK
    if icon_type == ICNS_16x12_1BIT_DATA:
        return ICNS_16x12_1BIT_MASK

    return ICNS_NULL_MASK


def to_bytes(n, length, endianess='big'):
    h = '%x' % n
    s = bytes.fromhex(('0'*(len(h) % 2) + h).zfill(length*2))
    return s if endianess == 'big' else s[::-1]


def from_bytes(byte_str):
    bits = (len(byte_str)-1)*8
    result = 0
    for i in range(len(byte_str)):
        result = (byte_str[i] << bits) + result
        bits -= 8
    return result


def type_to_str(type):
    s = bytearray()
    s.append(type >> 24 & 0xff)
    s.append(type >> 16 & 0xff)
    s.append(type >> 8 & 0xff)
    s.append(type & 0xff)
    s.append(0)
    return bytes(s)

class Printable(object):
    def _attrs(self):
        a = []
        for attr in dir(self):
            if not attr.startswith('_') and not callable(getattr(self, attr)):
                a.append(attr)
        return a

    def _dict_items(self):
        for a in reversed(self._attrs()):
            yield a, getattr(self,a)

    def _dict_string(self):
        vals = []
        for key, val in self._dict_items():
            try:
                vals.append('{}={}'.format(key, val))
            except UnicodeDecodeError:
                vals.append('{}=<not printable>'.format(key))
        return ', '.join(vals)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '{} [{}]'.format(self.__class__.__name__, self._dict_string())


#---------------------------CLASSES-------------------------------------------#

class Field(object):
    """This is a field object that will describe a field on the
    class it is a part of.
    """
    name = ''
    size = 0
    default_value = None

    def __init__(self, name='', size=0, default_value=None):
        self.name = name
        self.size = size
        self.default_value = default_value


class Structure(Printable):
    """A structure is composed of fields denoted by the _fields attribute."""
    _fields = None

    def __init__(self, *args, **kwargs):
        for field in self._fields:
            setattr(self, field.name, field.default_value)
        for k,v in kwargs:
            setattr(self, k, v)

    @property
    def size(self):
        sum_ = 0
        for f in self._fields:
            sum_ += f.size
        return sum_

    def dump(self):
        s = '>'
        values = []
        for field in self._fields:
            val = getattr(self, field.name)
            if not isinstance(val, (str, bytes)):
                values.append(val)
                s += struct_symbols[field.size]
            else:
                s += 'B'*len(val)
                values.extend(struct.unpack('>'+'B'*len(val), bytearray(val, encoding='utf-8')))


        return struct.pack(s, *values)


class Size(Printable):
    def __init__(self, width=0, height=0):
        self.width = width
        self.height = height


class ICNSInfo(Printable):
    def __init__(self):
        self.iconType = None
        self.isImage = False
        self.isMask = False
        self.iconSize = Size()
        self.iconChannels = 0
        self.iconPixelDepth = 0
        self.iconBitDepth = 0
        self.iconRawDataSize = 0

    data = None

    def get_image_type(self):
        if not self.isImage and not self.isMask:
            return ICNS_NULL_TYPE
        if self.iconSize.width == 0 or self.iconSize.height == 0:
            if self.iconRawDataSize == 24:
                if self.isImage and self.isMask:
                    return ICNS_NULL_TYPE
                if self.isImage:
                    return ICNS_16x12_1BIT_DATA
                if self.isMask:
                    return ICNS_16x12_1BIT_MASK
            if self.iconRawDataSize == 32:
                if self.isImage and self.isMask:
                    return ICNS_NULL_TYPE
                if self.isImage:
                    return ICNS_16x16_1BIT_DATA
                if self.isMask:
                    return ICNS_16x16_1BIT_MASK
            return ICNS_NULL_TYPE

        if self.iconBitDepth == 0 and (self.iconSize.width < 128 or self.iconSize.height < 128):
            if self.iconPixelDepth == 0 or self.iconChannels == 0:
                return ICNS_NULL_TYPE
            else:
                self.iconBitDepth = self.iconPixelDepth * self.iconChannels

        if self.iconSize.width == 16 and self.iconSize.height == 12:
            if self.iconBitDepth == 1:
                if self.isImage:
                    return ICNS_16x12_1BIT_DATA
                if self.isMask:
                    return ICNS_16x12_1BIT_MASK
            if self.iconBitDepth == 4:
                return ICNS_16x12_4BIT_DATA
            if self.iconBitDepth == 8:
                return ICNS_16x12_8BIT_DATA

            return ICNS_NULL_TYPE

        if self.iconSize.width != self.iconSize.height:
            return ICNS_NULL_TYPE

        data_type = ''
        if self.isImage:
            data_type = 'data'
        elif self.isMask:
            data_type = 'mask'

        try:
            return type_dict[data_type][self.iconSize.width][self.iconBitDepth]
        except KeyError:
            return ICNS_NULL_TYPE

    @classmethod
    def from_type(cls, type):
        icon_info = cls()

        icon_info.iconType = type

        if type == ICNS_TABLE_OF_CONTENTS or type == ICNS_ICON_VERSION:
            return icon_info

        if type == ICNS_1024x1024_32BIT_ARGB_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 1024
            icon_info.iconSize.height = 1024
            icon_info.iconChannels = 4
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 32
        elif type == ICNS_512x512_32BIT_ARGB_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 512
            icon_info.iconSize.height = 512
            icon_info.iconChannels = 4
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 32
        elif type == ICNS_256x256_32BIT_ARGB_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 256
            icon_info.iconSize.height = 256
            icon_info.iconChannels = 4
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 32
        elif type == ICNS_128x128_32BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 128
            icon_info.iconSize.height = 128
            icon_info.iconChannels = 4
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 32
        elif type == ICNS_48x48_32BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 48
            icon_info.iconSize.height = 48
            icon_info.iconChannels = 4
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 32
        elif type == ICNS_32x32_32BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 32
            icon_info.iconSize.height = 32
            icon_info.iconChannels = 4
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 32
        elif type == ICNS_16x16_32BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 16
            icon_info.iconSize.height = 16
            icon_info.iconChannels = 4
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 32

        elif type == ICNS_48x48_8BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 48
            icon_info.iconSize.height = 48
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 8
        elif type == ICNS_32x32_8BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 32
            icon_info.iconSize.height = 32
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 8
        elif type == ICNS_16x16_8BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 16
            icon_info.iconSize.height = 16
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 8
        elif type == ICNS_16x12_8BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 16
            icon_info.iconSize.height = 12
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 8

        elif type == ICNS_128x128_8BIT_MASK:
            icon_info.isImage = False
            icon_info.isMask = True
            icon_info.iconSize.width = 128
            icon_info.iconSize.height = 128
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 8
        elif type == ICNS_48x48_8BIT_MASK:
            icon_info.isImage = False
            icon_info.isMask = True
            icon_info.iconSize.width = 48
            icon_info.iconSize.height = 48
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 8
        elif type == ICNS_32x32_8BIT_MASK:
            icon_info.isImage = False
            icon_info.isMask = True
            icon_info.iconSize.width = 32
            icon_info.iconSize.height = 32
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 8
        elif type == ICNS_16x16_8BIT_MASK:
            icon_info.isImage = False
            icon_info.isMask = True
            icon_info.iconSize.width = 16
            icon_info.iconSize.height = 16
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 8
            icon_info.iconBitDepth = 8

        elif type == ICNS_48x48_4BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 48
            icon_info.iconSize.height = 48
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 4
            icon_info.iconBitDepth = 4
        elif type == ICNS_32x32_4BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 32
            icon_info.iconSize.height = 32
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 4
            icon_info.iconBitDepth = 4
        elif type == ICNS_16x16_4BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 16
            icon_info.iconSize.height = 16
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 4
            icon_info.iconBitDepth = 4
        elif type == ICNS_16x12_4BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = False
            icon_info.iconSize.width = 16
            icon_info.iconSize.height = 12
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 4
            icon_info.iconBitDepth = 4

        elif type == ICNS_48x48_1BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = True
            icon_info.iconSize.width = 48
            icon_info.iconSize.height = 48
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 1
            icon_info.iconBitDepth = 1
        elif type == ICNS_32x32_1BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = True
            icon_info.iconSize.width = 32
            icon_info.iconSize.height = 32
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 1
            icon_info.iconBitDepth = 1
        elif type == ICNS_16x16_1BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = True
            icon_info.iconSize.width = 16
            icon_info.iconSize.height = 16
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 1
            icon_info.iconBitDepth = 1
        elif type == ICNS_16x12_1BIT_DATA:
            icon_info.isImage = True
            icon_info.isMask = True
            icon_info.iconSize.width = 16
            icon_info.iconSize.height = 12
            icon_info.iconChannels = 1
            icon_info.iconPixelDepth = 1
            icon_info.iconBitDepth = 1
        else:
            print('Unable to parse icon type {}'.format(type_to_str(type)))
            icon_info.iconType = ICNS_NULL_TYPE

        icon_info.iconRawDataSize = int(icon_info.iconSize.height * icon_info.iconSize.width * icon_info.iconBitDepth/ICNS_BYTE_BITS)
        icon_info.data = bytearray(int(icon_info.iconRawDataSize))

        return icon_info


class ICNSHeader(Structure):
    _fields = [Field('TypeID', 4, 'icns'),
               Field('Size', 4)]

    elements = None

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.elements = []

    def parse_image(self, image):
        if not image_utils.IMAGE_UTILS_AVAILABLE:
            return None

        icon_size = image_utils.nearest_icon_size(image.size[0], image.size[1])

        icon_sizes = [icon_size]

        self.Size = self.size

        f_data = bytearray()

        for icon_s in icon_sizes:
            icns_element = ICNSElement()

            im_data = image_utils.resize(image, (int(icon_s), int(icon_s)))

            png_file = png.Reader(bytes=im_data)

            width, height, data, stats_dict = png_file.read_flat()

            if icon_size >= 256:
                encoded_data = im_data
            else:
                encoded_data = encode_rle24(data)

            bpp = stats_dict['bitdepth'] * 4

            icns_info = ICNSInfo()
            icns_info.isImage = 1
            icns_info.iconSize.width = int(icon_size)
            icns_info.iconSize.height = int(icon_size)
            icns_info.iconBitDepth = bpp
            icns_info.iconChannels = 4 if bpp == 32 else 1
            icns_info.iconPixelDepth = int(bpp / icns_info.iconChannels)
            icns_info.iconRawDataSize = int(width * height * 4)
            icns_info.data = bytearray(list(data))

            icon_type = icns_info.get_image_type()
            mask_type = get_mask_type_for_icon_type(icon_type)

            if mask_type != ICNS_NULL_MASK:
                icns_mask = ICNSInfo.from_type(mask_type)

                iconDataOffset = 0
                maskDataOffset = 0

                while iconDataOffset < icns_info.iconRawDataSize and maskDataOffset < icns_mask.iconRawDataSize:
                    icns_mask.data[maskDataOffset] = icns_info.data[iconDataOffset+3]
                    iconDataOffset += 4
                    maskDataOffset += 1
                mask_element = ICNSElement()

                mask_element.TypeID = mask_type
                mask_element.Size = len(icns_mask.data) + mask_element.size
                mask_element.icns_image = icns_mask

                icns_element.TypeID = icon_type
                icns_element.Size = len(encoded_data) + icns_element.size
                icns_element.icns_image = icns_info

                self.Size += icns_element.Size + mask_element.Size

                f_data += icns_element.dump()+encoded_data+mask_element.dump()+icns_mask.data
                self.elements.append(icns_element)
                self.elements.append(mask_element)

            else:  # just use the png data
                icns_element.TypeID = icon_type
                icns_element.Size = len(encoded_data) + icns_element.size
                icns_element.icns_image = icns_info

                self.Size += icns_element.Size

                f_data += icns_element.dump()+encoded_data

                self.elements.append(icns_element)

            return self.dump()+f_data


class ICNSElement(Structure):
    _fields = [Field('TypeID', 4),
               Field('Size', 4)]

    icns_image = None
    data = None

    @classmethod
    def from_family(cls, icns_data, icon_type):
        resource_size = len(icns_data)
        offset = 8
        found_data = False
        icon_element = cls()

        while not found_data and offset < resource_size:
            icon_element.TypeID = from_bytes(icns_data[offset:offset+4])
            icon_element.Size = from_bytes(icns_data[offset+4:offset+8])
            size = from_bytes(icns_data[offset+4:offset+8])
            icon_element.data = icns_data[offset+8:offset+size]

            if icon_element.TypeID == icon_type:
                found_data = True
            else:
                offset += icon_element.Size

        return icon_element

    def get_image(self):
        icon_type = self.TypeID
        raw_data_size = self.Size - 8
        data = self.data

        icns_info = ICNSInfo()
        icns_info.isImage = 1

        if icon_type in [ICNS_256x256_32BIT_ARGB_DATA,
                         ICNS_512x512_32BIT_ARGB_DATA,
                         ICNS_1024x1024_32BIT_ARGB_DATA]:
            magic_png = bytearray([0x89, 0x50, 0x4E, 0x47,
                                   0x0D, 0x0A, 0x1A, 0x0A])
            magic_read = data[:8]

            if magic_png == magic_read:
                png_file = png.Reader(bytes=data)

                width, height, png_data, stats_dict = png_file.read_flat()

                im = Image.frombytes('RGBA', [width, height], bytes(png_data))
                output = BytesIO()
                im.save(output, format='PNG')

                bpp = stats_dict['bitdepth'] * 4

                icns_info = ICNSInfo()
                icns_info.isImage = 1
                icns_info.iconSize.width = int(width)
                icns_info.iconSize.height = int(height)
                icns_info.iconBitDepth = bpp
                icns_info.iconChannels = 4 if bpp == 32 else 1
                icns_info.iconPixelDepth = int(bpp / icns_info.iconChannels)
                icns_info.iconRawDataSize = int(width * height * 4)
                icns_info.data = bytes(output.getvalue())
            else:
                image = Image.open(BytesIO(data))
                mode_to_bpp = {'1':1, 'L':8, 'P':8, 'RGB':24, 'RGBA':32, 'CMYK':32, 'YCbCr':24, 'I':32, 'F':32}
                output = BytesIO()
                image.save(output, format='PNG')
                bpp = mode_to_bpp[image.mode]
                png_data = bytes(output.getvalue())

                icns_info = ICNSInfo()
                icns_info.isImage = 1
                icns_info.iconSize.width = int(image.size[0])
                icns_info.iconSize.height = int(image.size[1])
                icns_info.iconBitDepth = bpp
                icns_info.iconChannels = 4 if bpp == 32 else 1
                icns_info.iconPixelDepth = int(bpp / icns_info.iconChannels)
                icns_info.iconRawDataSize = int(image.size[0] * image.size[1] * 4)
                icns_info.data = png_data

        else:
            icns_info = ICNSInfo.from_type(icon_type)

            if icon_type in [ICNS_128x128_32BIT_DATA,
                             ICNS_48x48_32BIT_DATA,
                             ICNS_32x32_32BIT_DATA,
                             ICNS_16x16_32BIT_DATA]:
                icon_bit_depth = icns_info.iconPixelDepth * icns_info.iconChannels
                icon_data_row_size = icns_info.iconSize.width * icon_bit_depth*ICNS_BYTE_BITS

                if raw_data_size < icns_info.iconRawDataSize:
                    pixel_count = icns_info.iconSize.width*icns_info.iconSize.height
                    decoded_data = decode_rle24(data, pixel_count)
                    icns_info.data = decoded_data
                else:
                    data_count = 0
                    pixel_count = 0
                    while data_count < icns_info.iconSize.width:
                        data_pos = data_count * icon_data_row_size
                        icns_info.data[data_pos:data_pos+icon_data_row_size] = data[data_pos:data_pos+icon_data_row_size]
                        data_count += 1
                    pixel_count = icns_info.iconSize.width*icns_info.iconSize.height
                    data_count = 0
                    while data_count < pixel_count:
                        argb = icns_info.data[data_count*4:data_count*4+4]
                        rgba = [argb[1], argb[2], argb[3], argb[0]]
                        icns_info.data[data_count*4:data_count*4+4] = rgba
                        data_count += 1
            elif icon_type in [ICNS_48x48_8BIT_DATA,
                               ICNS_32x32_8BIT_DATA,
                               ICNS_16x16_8BIT_DATA,
                               ICNS_16x12_8BIT_DATA,
                               ICNS_48x48_4BIT_DATA,
                               ICNS_32x32_4BIT_DATA,
                               ICNS_16x16_4BIT_DATA,
                               ICNS_16x12_4BIT_DATA,
                               ICNS_48x48_1BIT_DATA,
                               ICNS_32x32_1BIT_DATA,
                               ICNS_16x16_1BIT_DATA,
                               ICNS_16x12_1BIT_DATA]:
                icon_bit_depth = icns_info.iconPixelDepth * icns_info.iconChannels
                icon_data_row_size = icns_info.iconSize.width * icon_bit_depth*ICNS_BYTE_BITS
                data_count = 0
                while data_count < icns_info.iconSize.width:
                    data_pos = data_count * icon_data_row_size
                    icns_info.data[data_pos:data_pos+icon_data_row_size] = data[data_pos:data_pos+icon_data_row_size]
                    data_count += 1

        return icns_info

    def get_mask(self):
        element_type = self.TypeID
        element_size = self.Size
        mask_type = element_type
        raw_data_size = element_size - 8
        data = self.data
        icns_info = ICNSInfo.from_type(mask_type)
        mask_bit_depth = icns_info.iconSize.width * icns_info.iconSize.height
        mask_data_size = icns_info.iconRawDataSize
        mask_data_row_size = int(icns_info.iconSize.width * mask_bit_depth / ICNS_BYTE_BITS)

        if mask_type in [ICNS_128x128_8BIT_MASK,
                         ICNS_48x48_8BIT_MASK,
                         ICNS_32x32_8BIT_MASK,
                         ICNS_16x16_8BIT_MASK]:
            data_count = 0
            while data_count < icns_info.iconSize.height:
                data_pos = int(data_count * mask_data_row_size)
                icns_info.data[data_pos:data_pos+mask_data_row_size] = data[data_pos:data_pos+mask_data_row_size]
                data_count += 1

        elif mask_type in [ICNS_48x48_1BIT_MASK,
                           ICNS_32x32_1BIT_MASK,
                           ICNS_16x16_1BIT_MASK,
                           ICNS_16x12_1BIT_MASK]:
            if raw_data_size == mask_data_size*2:
                data_count = 0
                while data_count < icns_info.iconSize.height:
                    data_pos = data_count * mask_data_row_size
                    icns_info.data[data_pos:data_pos+mask_data_row_size] = data[data_pos+mask_data_size:data_pos+mask_data_row_size+mask_data_size]
                    data_count += 1

            else:
                data_count = 0
                while data_count < icns_info.iconSize.height:
                    data_pos = data_count * mask_data_row_size
                    icns_info.data[data_pos:data_pos+mask_data_row_size] = data[data_pos:data_pos+mask_data_row_size]
                data_count += 1
        return icns_info


def icns_read_be(icns_data, size):
    icns_bytes = icns_data[:size]

    if size == 1:
        return icns_bytes[0]
    elif size == 2:
        return icns_bytes[1] | icns_bytes[0] << 8
    elif size == 3:
        return (icns_bytes[2] & 0xffff | icns_bytes[1] & 0xffff << 8| icns_bytes[0] & 0xffff << 16) & 0x00FFFFFF
    elif size == 4:
        return icns_bytes[3] | icns_bytes[2] << 8 | icns_bytes[1] << 16 | icns_bytes[0] << 24
    elif size == 8:
        b = icns_bytes
        return b[7] | b[6] << 8 | b[5] << 16 | b[4] << 24 | b[3] << 32 | b[2] << 40 | b[1] << 48 | b[0] << 56


def icns_header_check(icns_data):
    resource_type = icns_read_be(icns_data, 4)
    resource_size = icns_read_be(icns_data[4:], 4)

    if resource_type != ICNS_FAMILY_TYPE:
        raise Exception('File is not an ICNS file.')
    if resource_size != len(icns_data):
        raise Exception('Expected size {}, but got {}'.format(len(icns_data)))


def icns_parse_family_data(icns_data):
    resource_type = icns_read_be(icns_data, 4)
    resource_size = icns_read_be(icns_data[4:], 4)

    if resource_type == ICNS_FAMILY_TYPE:
        if len(icns_data) == resource_size:
            icns_data[:4] = to_bytes(resource_type, 4)
            icns_data[4:8] = to_bytes(resource_size, 4)

            offset = 8
            while (offset+8) < resource_size:
                element_type = icns_read_be(icns_data[offset:], 4)
                element_size = icns_read_be(icns_data[offset+4:], 4)
                icns_data[offset:offset+4] = to_bytes(element_type, 4)
                icns_data[offset+4:offset+8] = to_bytes(element_size, 4)
                offset += element_size
    return icns_data

def get_image_with_mask(icns_data, element_type):
    element = ICNSElement.from_family(icns_data, element_type)
    icns_image = element.get_image()
    if element_type in [ICNS_256x256_32BIT_ARGB_DATA,
                        ICNS_512x512_32BIT_ARGB_DATA,
                        ICNS_1024x1024_32BIT_ARGB_DATA]:
        return icns_image
    mask_type = get_mask_type_for_icon_type(element_type)
    mask_element = ICNSElement.from_family(icns_data, mask_type)
    mask_image = mask_element.get_mask()

    old_bit_depth = icns_image.iconPixelDepth * icns_image.iconChannels
    if old_bit_depth < 32:
        old_bit_depth = icns_image.iconPixelDepth * icns_image.iconChannels
        pixel_count = icns_image.iconSize.width * icns_image.iconSize.height
        new_block_size = icns_image.iconSize.width * 32
        new_data_size = new_block_size * icns_image.iconSize.height

        old_data = icns_image.data
        new_data = bytearray(int(new_data_size))

        data_count = 0

        if element_type in [ICNS_48x48_8BIT_DATA,
                            ICNS_32x32_8BIT_DATA,
                            ICNS_16x16_8BIT_DATA,
                            ICNS_16x12_8BIT_DATA]:
            for pixel_id in range(pixel_count):
                color_index = old_data[data_count]
                color_rgb = icns_colormap_8[color_index]
                new_data[pixel_id*4+0] = color_rgb[0]
                new_data[pixel_id*4+1] = color_rgb[1]
                new_data[pixel_id*4+2] = color_rgb[2]
                new_data[pixel_id*4+3] = 0xFF
                data_count += 1
        elif element_type in [ICNS_48x48_4BIT_DATA,
                              ICNS_32x32_4BIT_DATA,
                              ICNS_16x16_4BIT_DATA,
                              ICNS_16x12_4BIT_DATA]:
            data_value = 0
            for pixel_id in range(pixel_count):
                if (pixel_id % 2) == 0:
                    data_value = old_data[data_count]
                    data_count += 1
                color_index = (data_value & 0xF0) >> 4
                color_rgb = icns_colormap_4[color_index]
                new_data[pixel_id*4+0] = color_rgb[0]
                new_data[pixel_id*4+1] = color_rgb[1]
                new_data[pixel_id*4+2] = color_rgb[2]
                new_data[pixel_id*4+3] = 0xFF
        elif element_type in [ICNS_48x48_1BIT_DATA,
                              ICNS_32x32_1BIT_DATA,
                              ICNS_16x16_1BIT_DATA,
                              ICNS_16x12_1BIT_DATA]:
            data_value = 0
            for pixel_id in range(pixel_count):
                if (pixel_id % 8) == 0:
                    data_value = old_data[data_count]
                    data_count += 1
                color_index = 0x00 if (data_value & 0x80) else 0xFF
                data_value = data_value << 1
                new_data[pixel_id*4+0] = color_index
                new_data[pixel_id*4+1] = color_index
                new_data[pixel_id*4+2] = color_index
                new_data[pixel_id*4+3] = 0xFF

        icns_image.iconPixelDepth = 8
        icns_image.iconChannels = 4
        icns_image.iconRawDataSize = int(new_data_size)
        icns_image.data = new_data

    if mask_type in [ICNS_128x128_8BIT_MASK,
                     ICNS_48x48_8BIT_MASK,
                     ICNS_32x32_8BIT_MASK,
                     ICNS_16x16_8BIT_MASK]:
        pixel_count = mask_image.iconSize.width * mask_image.iconSize.height
        data_count = 0
        for pixel_id in range(pixel_count):
            icns_image.data[pixel_id*4+3] = mask_image.data[data_count]
            data_count += 1

    elif mask_type in [ICNS_48x48_1BIT_MASK,
                       ICNS_32x32_1BIT_MASK,
                       ICNS_16x16_1BIT_MASK,
                       ICNS_16x12_1BIT_MASK]:
        pixel_count = mask_image.iconSize.width * mask_image.iconSize.height
        data_count = 0
        data_value = 0
        for pixel_id in range(pixel_count):
            if (pixel_id % 8) == 0:
                data_value = mask_image.data[data_count]
                data_count += 1
            color_index = 0xFF if (data_value & 0x80) else 0x00
            data_value = data_value << 1
            icns_image.data[pixel_id*4+3] = color_index
    im = Image.frombytes('RGBA', [icns_image.iconSize.width,icns_image.iconSize.height], bytes(icns_image.data))
    #print(icns_image.data)
    output = BytesIO()
    im.save(output, format='PNG')
    icns_image.data = bytes(output.getvalue())

    return icns_image


def extract_icons(all_icns_data):
    image_count = 0
    stack = [all_icns_data]
    data = []

    while stack:

        offset = 8
        icns_data = stack.pop()

        while ((offset+8) < len(icns_data)):
            element = ICNSElement()
            element.TypeID = from_bytes(icns_data[offset:offset+4])
            element.Size = from_bytes(icns_data[offset+4:offset+8])

            if element.TypeID == ICNS_TABLE_OF_CONTENTS:
                pass
            elif element.TypeID in [ICNS_TILE_VARIANT,
                                    ICNS_ROLLOVER_VARIANT,
                                    ICNS_DROP_VARIANT,
                                    ICNS_OPEN_VARIANT,
                                    ICNS_OPEN_DROP_VARIANT]:
                variant_data = icns_data[offset:offset+element.Size]
                variant_data[:4] = 'icns'
                variant_data[4:8] = to_bytes(element.Size, 4)
                variant_data = icns_parse_family_data(variant_data)
                stack.append(variant_data)

            else:
                icon_info = ICNSInfo.from_type(element.TypeID)
                if icon_info.isImage:
                    image_count += 1

                    image_data = get_image_with_mask(icns_data, element.TypeID)
                    image_data.data = bytes(image_data.data)
                    data.append(image_data)

            offset += element.Size

    return data


def icns_to_png(icns_file, out_file=None):
    """Convert an icns file to a list of png file data"""

    if not os.path.exists(icns_file):
        return

    icns_fp = open(icns_file, 'rb')
    icns_data = bytearray(icns_fp.read())
    icns_fp.close()

    icns_header_check(icns_data)
    new_data = icns_parse_family_data(icns_data)

    icons = extract_icons(new_data)
    return icons
