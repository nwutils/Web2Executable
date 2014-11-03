import struct
from image_utils import Image, nearest_icon_size, resize
import png


#---------------------CONSTANTS-----------------------------------------------#

ICNS_TABLE_OF_CONTENTS = 0x544F4320 # "TOC "

ICNS_ICON_VERSION = 0x69636E56 # "icnV"

ICNS_1024x1024_32BIT_ARGB_DATA = 0x69633130 # "ic10"

ICNS_512x512_32BIT_ARGB_DATA = 0x69633039 # "ic09"
ICNS_256x256_32BIT_ARGB_DATA = 0x69633038 # "ic08"

ICNS_128x128_32BIT_DATA = 0x69743332 # "it32"
ICNS_128x128_8BIT_MASK = 0x74386D6B # "t8mk"

ICNS_48x48_1BIT_DATA = 0x69636823 # "ich#"
ICNS_48x48_4BIT_DATA = 0x69636834 # "ich4"
ICNS_48x48_8BIT_DATA = 0x69636838 # "ich8"
ICNS_48x48_32BIT_DATA = 0x69683332 # "ih32"
ICNS_48x48_1BIT_MASK = 0x69636823 # "ich#"
ICNS_48x48_8BIT_MASK = 0x68386D6B # "h8mk"

ICNS_32x32_1BIT_DATA = 0x49434E23 # "ICN#"
ICNS_32x32_4BIT_DATA = 0x69636C34 # "icl4"
ICNS_32x32_8BIT_DATA = 0x69636C38 # "icl8"
ICNS_32x32_32BIT_DATA = 0x696C3332 # "il32"
ICNS_32x32_1BIT_MASK = 0x49434E23 # "ICN#"
ICNS_32x32_8BIT_MASK = 0x6C386D6B # "l8mk"

ICNS_16x16_1BIT_DATA = 0x69637323 # "ics#"
ICNS_16x16_4BIT_DATA = 0x69637334 # "ics4"
ICNS_16x16_8BIT_DATA = 0x69637338 # "ics8"
ICNS_16x16_32BIT_DATA = 0x69733332 # "is32"
ICNS_16x16_1BIT_MASK = 0x69637323 # "ics#"
ICNS_16x16_8BIT_MASK = 0x73386D6B # "s8mk"

ICNS_16x12_1BIT_DATA = 0x69636D23 # "icm#"
ICNS_16x12_4BIT_DATA = 0x69636D34 # "icm4"
ICNS_16x12_1BIT_MASK = 0x69636D23 # "icm#"
ICNS_16x12_8BIT_DATA = 0x69636D38 # "icm8"

ICNS_32x32_1BIT_ICON = 0x49434F4E # "ICON"

ICNS_TILE_VARIANT = 0x74696C65 # "tile"
ICNS_ROLLOVER_VARIANT = 0x6F766572 # "over"
ICNS_DROP_VARIANT = 0x64726F70 # "drop"
ICNS_OPEN_VARIANT = 0x6F70656E # "open"
ICNS_OPEN_DROP_VARIANT = 0x6F647270 # "odrp"

ICNS_NULL_DATA = 0x00000000
ICNS_NULL_MASK = 0x00000000

# icns file / resource type constants

ICNS_FAMILY_TYPE = 0x69636E73 # "icns"

ICNS_MACBINARY_TYPE = 0x6D42494E # "mBIN"

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

struct_symbols = {1:'B',#byte
                  2:'H',#word
                  4:'I',#unsigned int/double word
                  8:'Q' #quad word
                }

#used to easily get the icon type from dimensions
type_dict = {'mask':{128:{8:ICNS_128x128_8BIT_MASK},
             48:{1:ICNS_48x48_1BIT_MASK,
                 8:ICNS_48x48_8BIT_MASK},
             32:{1:ICNS_32x32_1BIT_MASK,
                 8:ICNS_32x32_8BIT_MASK},
             16:{1:ICNS_16x16_1BIT_MASK,
                 8:ICNS_16x16_8BIT_MASK},
             },
      'data':{1024:{32:ICNS_1024x1024_32BIT_ARGB_DATA},
              512:{32:ICNS_512x512_32BIT_ARGB_DATA},
              256:{32:ICNS_256x256_32BIT_ARGB_DATA},
              128:{32:ICNS_128x128_32BIT_DATA},
              48:{1:ICNS_48x48_1BIT_DATA,
                  4:ICNS_48x48_4BIT_DATA,
                  8:ICNS_48x48_8BIT_DATA,
                  32:ICNS_48x48_32BIT_DATA},
              32:{1:ICNS_32x32_1BIT_DATA,
                  4:ICNS_32x32_4BIT_DATA,
                  8:ICNS_32x32_8BIT_DATA,
                  32:ICNS_32x32_32BIT_DATA},
              16:{1:ICNS_16x16_1BIT_DATA,
                  4:ICNS_16x16_4BIT_DATA,
                  8:ICNS_16x16_8BIT_DATA,
                  32:ICNS_16x16_32BIT_DATA},
              }}

#---------------------------UTILITY FUNCTIONS---------------------------------#

def encode_rle24(data):
    encoded_data = bytearray()
    dataRun = bytearray(130)
    dataInChanSize = len(data)/4
    dataTempCount = 0

    dataTemp = bytearray(len(data) + len(data)/4)

    if len(data) >= 65536:
        dataTempCount = 4

    for colorOffset in xrange(3):
        runCount = 0
        runLength = 1
        runType = 0
        dataRun[0] = data[colorOffset]

        for dataInCount in xrange(1, dataInChanSize):
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

def type_to_str(type):
    s = bytearray()
    s.append(type >> 24 & 0xff)
    s.append(type >> 16 & 0xff)
    s.append(type >> 8 & 0xff)
    s.append(type & 0xff)
    s.append(0)
    return str(s)

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
                vals.append(u'{}={}'.format(key, val))
            except UnicodeDecodeError:
                vals.append(u'{}=<not printable>'.format(key))
        return u', '.join(vals)

    def __repr__(self):
        return unicode(self)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'{} [{}]'.format(self.__class__.__name__, self._dict_string())


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
            if not isinstance(val, basestring):
                values.append(val)
                s += struct_symbols[field.size]
            else:
                s += 'B'*len(val)
                values.extend(struct.unpack('>'+'B'*len(val), val))


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
            print 'Unable to parse icon type {}'.format(type_to_str(type))
            icon_info.iconType = ICNS_NULL_TYPE

        icon_info.iconRawDataSize = icon_info.iconSize.height * icon_info.iconSize.width * icon_info.iconBitDepth/ICNS_BYTE_BITS
        icon_info.data = bytearray(icon_info.iconRawDataSize)

        return icon_info


class ICNSHeader(Structure):
    _fields = [Field('TypeID', 4, 'icns'),
               Field('Size', 4)]

    elements = None

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.elements = []

    def parse_image(self, image):
        icon_size = nearest_icon_size(image.size[0], image.size[1])

        icon_sizes = [icon_size]

        self.Size = self.size

        f_data = bytearray()

        for icon_s in icon_sizes:
            icns_element = ICNSElement()

            im_data = resize(image, (icon_s, icon_s))

            png_file = png.Reader(bytes=im_data)

            width, height, data, stats_dict = png_file.read_flat()

            if icon_size >= 256:
                encoded_data = im_data
            else:
                encoded_data = encode_rle24(data)

            bpp = stats_dict['bitdepth'] * 4

            icns_info = ICNSInfo()
            icns_info.isImage = 1
            icns_info.iconSize.width = icon_size
            icns_info.iconSize.height = icon_size
            icns_info.iconBitDepth = bpp
            icns_info.iconChannels = 4 if bpp == 32 else 1
            icns_info.iconPixelDepth = bpp / icns_info.iconChannels
            icns_info.iconRawDataSize = width * height * 4
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

            else:#just use the png data
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

