"""
Copyright Joey Payne All Rights Reserved
"""

import os
import struct
from io import BytesIO

from PIL import Image


def resize(image, size, format=None):
    output = BytesIO()
    back = Image.new("RGBA", size, (0, 0, 0, 0))

    if image.size[0] < size[0] or image.size[1] < size[1]:
        if image.height > image.width:
            factor = size[0] / image.height
        else:
            factor = size[1] / image.width
        image = image.resize(
            (int(image.width * factor), int(image.height * factor)), Image.ANTIALIAS
        )
    else:
        image.thumbnail(size, Image.ANTIALIAS)

    offset = [0, 0]
    if image.size[0] > image.size[1]:
        offset[1] = int(back.size[1] / 2 - image.size[1] / 2)
    elif image.size[0] < image.size[1]:
        offset[0] = int(back.size[0] / 2 - image.size[0] / 2)
    else:
        offset[0] = int(back.size[0] / 2 - image.size[0] / 2)
        offset[1] = int(back.size[1] / 2 - image.size[1] / 2)

    back.paste(image, tuple(offset))
    format = format or image.format
    back.save(output, format, sizes=[size])
    contents = output.getvalue()
    output.close()
    return contents


struct_symbols = {
    1: "B",  # byte
    2: "H",  # word
    4: "L",  # long word
    8: "Q",  # double long word
}
endian_symbols = {"little": "<", "big": ">"}

name_dictionary = {
    "PEHeader_Machine": {
        0: "IMAGE_FILE_MACHINE_UNKNOWN",
        0x014C: "IMAGE_FILE_MACHINE_I386",
        0x0162: "IMAGE_FILE_MACHINE_R3000",
        0x0166: "IMAGE_FILE_MACHINE_R4000",
        0x0168: "IMAGE_FILE_MACHINE_R10000",
        0x0169: "IMAGE_FILE_MACHINE_WCEMIPSV2",
        0x0184: "IMAGE_FILE_MACHINE_ALPHA",
        0x01A2: "IMAGE_FILE_MACHINE_SH3",
        0x01A3: "IMAGE_FILE_MACHINE_SH3DSP",
        0x01A4: "IMAGE_FILE_MACHINE_SH3E",
        0x01A6: "IMAGE_FILE_MACHINE_SH4",
        0x01A8: "IMAGE_FILE_MACHINE_SH5",
        0x01C0: "IMAGE_FILE_MACHINE_ARM",
        0x01C2: "IMAGE_FILE_MACHINE_THUMB",
        0x01C4: "IMAGE_FILE_MACHINE_ARMNT",
        0x01D3: "IMAGE_FILE_MACHINE_AM33",
        0x01F0: "IMAGE_FILE_MACHINE_POWERPC",
        0x01F1: "IMAGE_FILE_MACHINE_POWERPCFP",
        0x0200: "IMAGE_FILE_MACHINE_IA64",
        0x0266: "IMAGE_FILE_MACHINE_MIPS16",
        0x0284: "IMAGE_FILE_MACHINE_ALPHA64",
        0x0284: "IMAGE_FILE_MACHINE_AXP64",  # same
        0x0366: "IMAGE_FILE_MACHINE_MIPSFPU",
        0x0466: "IMAGE_FILE_MACHINE_MIPSFPU16",
        0x0520: "IMAGE_FILE_MACHINE_TRICORE",
        0x0CEF: "IMAGE_FILE_MACHINE_CEF",
        0x0EBC: "IMAGE_FILE_MACHINE_EBC",
        0x8664: "IMAGE_FILE_MACHINE_AMD64",
        0x9041: "IMAGE_FILE_MACHINE_M32R",
        0xC0EE: "IMAGE_FILE_MACHINE_CEE",
    },
    "PEHeader_Characteristics": {
        0x0001: "IMAGE_FILE_RELOCS_STRIPPED",
        0x0002: "IMAGE_FILE_EXECUTABLE_IMAGE",
        0x0004: "IMAGE_FILE_LINE_NUMS_STRIPPED",
        0x0008: "IMAGE_FILE_LOCAL_SYMS_STRIPPED",
        0x0010: "IMAGE_FILE_AGGRESIVE_WS_TRIM",
        0x0020: "IMAGE_FILE_LARGE_ADDRESS_AWARE",
        0x0040: "IMAGE_FILE_16BIT_MACHINE",
        0x0080: "IMAGE_FILE_BYTES_REVERSED_LO",
        0x0100: "IMAGE_FILE_32BIT_MACHINE",
        0x0200: "IMAGE_FILE_DEBUG_STRIPPED",
        0x0400: "IMAGE_FILE_REMOVABLE_RUN_FROM_SWAP",
        0x0800: "IMAGE_FILE_NET_RUN_FROM_SWAP",
        0x1000: "IMAGE_FILE_SYSTEM",
        0x2000: "IMAGE_FILE_DLL",
        0x4000: "IMAGE_FILE_UP_SYSTEM_ONLY",
        0x8000: "IMAGE_FILE_BYTES_REVERSED_HI",
    },
    "OptionalHeader_Subsystem": {
        0: "IMAGE_SUBSYSTEM_UNKNOWN",
        1: "IMAGE_SUBSYSTEM_NATIVE",
        2: "IMAGE_SUBSYSTEM_WINDOWS_GUI",
        3: "IMAGE_SUBSYSTEM_WINDOWS_CUI",
        5: "IMAGE_SUBSYSTEM_OS2_CUI",
        7: "IMAGE_SUBSYSTEM_POSIX_CUI",
        8: "IMAGE_SUBSYSTEM_NATIVE_WINDOWS",
        9: "IMAGE_SUBSYSTEM_WINDOWS_CE_GUI",
        10: "IMAGE_SUBSYSTEM_EFI_APPLICATION",
        11: "IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER",
        12: "IMAGE_SUBSYSTEM_EFI_RUNTIME_DRIVER",
        13: "IMAGE_SUBSYSTEM_EFI_ROM",
        14: "IMAGE_SUBSYSTEM_XBOX",
        16: "IMAGE_SUBSYSTEM_WINDOWS_BOOT_APPLICATION",
    },
    "OptionalHeader_DLL_Characteristics": {
        0x0001: "IMAGE_LIBRARY_PROCESS_INIT",  # reserved
        0x0002: "IMAGE_LIBRARY_PROCESS_TERM",  # reserved
        0x0004: "IMAGE_LIBRARY_THREAD_INIT",  # reserved
        0x0008: "IMAGE_LIBRARY_THREAD_TERM",  # reserved
        0x0020: "IMAGE_DLLCHARACTERISTICS_HIGH_ENTROPY_VA",
        0x0040: "IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE",
        0x0080: "IMAGE_DLLCHARACTERISTICS_FORCE_INTEGRITY",
        0x0100: "IMAGE_DLLCHARACTERISTICS_NX_COMPAT",
        0x0200: "IMAGE_DLLCHARACTERISTICS_NO_ISOLATION",
        0x0400: "IMAGE_DLLCHARACTERISTICS_NO_SEH",
        0x0800: "IMAGE_DLLCHARACTERISTICS_NO_BIND",
        0x1000: "IMAGE_DLLCHARACTERISTICS_APPCONTAINER",
        0x2000: "IMAGE_DLLCHARACTERISTICS_WDM_DRIVER",
        0x4000: "IMAGE_DLLCHARACTERISTICS_GUARD_CF",
        0x8000: "IMAGE_DLLCHARACTERISTICS_TERMINAL_SERVER_AWARE",
    },
    "SectionHeader_Characteristics": {
        0x00000000: "IMAGE_SCN_TYPE_REG",  # reserved
        0x00000001: "IMAGE_SCN_TYPE_DSECT",  # reserved
        0x00000002: "IMAGE_SCN_TYPE_NOLOAD",  # reserved
        0x00000004: "IMAGE_SCN_TYPE_GROUP",  # reserved
        0x00000008: "IMAGE_SCN_TYPE_NO_PAD",  # reserved
        0x00000010: "IMAGE_SCN_TYPE_COPY",  # reserved
        0x00000020: "IMAGE_SCN_CNT_CODE",
        0x00000040: "IMAGE_SCN_CNT_INITIALIZED_DATA",
        0x00000080: "IMAGE_SCN_CNT_UNINITIALIZED_DATA",
        0x00000100: "IMAGE_SCN_LNK_OTHER",
        0x00000200: "IMAGE_SCN_LNK_INFO",
        0x00000400: "IMAGE_SCN_LNK_OVER",  # reserved
        0x00000800: "IMAGE_SCN_LNK_REMOVE",
        0x00001000: "IMAGE_SCN_LNK_COMDAT",
        0x00004000: "IMAGE_SCN_MEM_PROTECTED",  # obsolete
        0x00004000: "IMAGE_SCN_NO_DEFER_SPEC_EXC",
        0x00008000: "IMAGE_SCN_GPREL",
        0x00008000: "IMAGE_SCN_MEM_FARDATA",
        0x00010000: "IMAGE_SCN_MEM_SYSHEAP",  # obsolete
        0x00020000: "IMAGE_SCN_MEM_PURGEABLE",
        0x00020000: "IMAGE_SCN_MEM_16BIT",
        0x00040000: "IMAGE_SCN_MEM_LOCKED",
        0x00080000: "IMAGE_SCN_MEM_PRELOAD",
        0x00100000: "IMAGE_SCN_ALIGN_1BYTES",
        0x00200000: "IMAGE_SCN_ALIGN_2BYTES",
        0x00300000: "IMAGE_SCN_ALIGN_4BYTES",
        0x00400000: "IMAGE_SCN_ALIGN_8BYTES",
        0x00500000: "IMAGE_SCN_ALIGN_16BYTES",  # default alignment
        0x00600000: "IMAGE_SCN_ALIGN_32BYTES",
        0x00700000: "IMAGE_SCN_ALIGN_64BYTES",
        0x00800000: "IMAGE_SCN_ALIGN_128BYTES",
        0x00900000: "IMAGE_SCN_ALIGN_256BYTES",
        0x00A00000: "IMAGE_SCN_ALIGN_512BYTES",
        0x00B00000: "IMAGE_SCN_ALIGN_1024BYTES",
        0x00C00000: "IMAGE_SCN_ALIGN_2048BYTES",
        0x00D00000: "IMAGE_SCN_ALIGN_4096BYTES",
        0x00E00000: "IMAGE_SCN_ALIGN_8192BYTES",
        0x00F00000: "IMAGE_SCN_ALIGN_MASK",
        0x01000000: "IMAGE_SCN_LNK_NRELOC_OVFL",
        0x02000000: "IMAGE_SCN_MEM_DISCARDABLE",
        0x04000000: "IMAGE_SCN_MEM_NOT_CACHED",
        0x08000000: "IMAGE_SCN_MEM_NOT_PAGED",
        0x10000000: "IMAGE_SCN_MEM_SHARED",
        0x20000000: "IMAGE_SCN_MEM_EXECUTE",
        0x40000000: "IMAGE_SCN_MEM_READ",
        0x80000000: "IMAGE_SCN_MEM_WRITE",
    },
}

DEFAULT_ENDIAN = "little"


def read_data(file_data, offset, number_of_bytes, string_data=None):
    """Just reads the straight data with no endianness."""

    if number_of_bytes > 0:
        data = file_data[offset : offset + number_of_bytes]
        # if len(data) != number_of_bytes:
        # print 'data out of bounds:', 'offset', hex(offset), 'data', data, 'data_len', len(data), 'num_bytes', number_of_bytes, 'total', hex(len(file_data))
        return data
    else:
        return bytearray("")


def read_bytes(file_data, offset, number_of_bytes, endian=None, string_data=None):
    """Returns a tuple of the data value and string representation.
    Will read 1,2,4,8 bytes with little endian as the default
    (value, string)
    """

    if number_of_bytes > 0:
        endian = endian or DEFAULT_ENDIAN
        endian = endian_symbols[endian]

        data = bytes(file_data[offset : offset + number_of_bytes])
        if len(data) != number_of_bytes:
            return 0, ""

        return struct.unpack(endian + struct_symbols[number_of_bytes], data)[0], data
    else:
        return 0, ""


def value_to_byte_string(value, number_of_bytes, endian=None):
    endian = endian or DEFAULT_ENDIAN
    endian = endian_symbols[endian]

    return struct.pack(endian + struct_symbols[number_of_bytes], value)


class ResourceTypes(object):
    Cursor = 1
    Bitmap = 2
    Icon = 3
    Menu = 4
    Dialog = 5
    String = 6
    Font_Directory = 7
    Font = 8
    Accelerator = 9
    RC_Data = 10
    Message_Table = 11
    Group_Cursor = 12
    Group_Icon = 14
    Version_Info = 16
    DLG_Include = 17
    Plug_Play = 19
    VXD = 20
    Animated_Cursor = 21
    Animated_Icon = 22
    HTML = 23
    Manifest = 24


resource_types = {
    1: "Cursor",
    2: "Bitmap",
    3: "Icon",
    4: "Menu",
    5: "Dialog",
    6: "String",
    7: "Font Directory",
    8: "Font",
    9: "Accelerator",
    10: "RC Data",
    11: "Message Table",
    12: "Group Cursor",
    14: "Group Icon",
    16: "Version Info",
    17: "DLG Include",
    19: "Plug and Play",
    20: "VXD",
    21: "Animated Cursor",
    22: "Animated Icon",
    23: "HTML",
    24: "Manifest",
}

_32BIT_PLUS_MAGIC = 0x20B
_32BIT_MAGIC = 0x10B
_ROM_MAGIC = 0x107


def read_from_name_dict(obj, field_name):
    dict_field = "{}_{}".format(obj.__class__.__name__, field_name)
    return name_dictionary.get(dict_field, {})


def test_bit(value, index):
    mask = 1 << index
    return value & mask


def set_bit(value, index):
    mask = 1 << index
    return value | mask


def clear_bit(value, index):
    mask = ~(1 << index)
    return value & mask


def toggle_bit(value, index):
    mask = 1 << index
    return value ^ mask


class PEFormatError(Exception):
    pass


class Printable(object):
    def _attrs(self):
        a = []
        for attr in dir(self):
            if not attr.startswith("_") and not callable(getattr(self, attr)):
                a.append(attr)
        return a

    def _dict_items(self):
        for a in reversed(self._attrs()):
            yield a, getattr(self, a)

    def _dict_string(self):
        vals = []
        for key, val in self._dict_items():
            try:
                vals.append("{}={}".format(key, val))
            except UnicodeDecodeError:
                vals.append("{}=<not printable>".format(key))
        return ", ".join(vals)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{} [{}]".format(self.__class__.__name__, self._dict_string())


class Structure(Printable):
    _fields = {}

    def __init__(
        self,
        size=0,
        value=None,
        data=None,
        absolute_offset=0,
        name="",
        friendly_name="",
        *args,
        **kwargs
    ):
        self._value = value
        self.size = size
        self.data = data
        self.name = name
        self.friendly_name = friendly_name
        self._absolute_offset = absolute_offset
        self._file_data = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def absolute_offset(self):
        return self._absolute_offset

    @absolute_offset.setter
    def absolute_offset(self, abs_offset):
        self._absolute_offset = abs_offset
        for k, v in self._fields.items():
            field = getattr(self, k)
            field.absolute_offset = self.absolute_offset + field.offset

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self._file_data is not None:
            self.data = value_to_byte_string(value, self.size)
            self._file_data[
                self.absolute_offset : self.absolute_offset + self.size
            ] = bytearray(self.data)
        self._value = value

    def process_field(self, file_data, field_name, field_info):
        if hasattr(self, "process_" + field_name) and callable(
            getattr(self, "process_" + field_name)
        ):
            getattr(self, "process_" + field_name)(file_data, field_name, field_info)
        else:
            absolute_offset = field_info["offset"] + self.absolute_offset
            size = field_info["size"]
            self.size += size
            int_value, data = read_bytes(file_data, absolute_offset, size)
            field_name_dict = read_from_name_dict(self, field_name)
            name = field_name_dict.get(int_value, "")
            friendly_name = name.replace("_", " ").capitalize()

            setattr(
                self,
                field_name,
                Structure(
                    offset=field_info["offset"],
                    size=size,
                    value=int_value,
                    data=data,
                    absolute_offset=absolute_offset,
                    name=name,
                    friendly_name=friendly_name,
                ),
            )
            getattr(self, field_name)._file_data = file_data

    def process_Characteristics(self, file_data, field_name, field_info):
        absolute_offset = field_info["offset"] + self.absolute_offset
        size = field_info["size"]
        self.size += size
        int_value, data = read_bytes(file_data, absolute_offset, size)
        field_name_dict = read_from_name_dict(self, field_name)

        bit_length = len(bin(int_value)) - 2

        characteristics = {}
        for i in range(bit_length):
            set_bit = test_bit(int_value, i)
            char_name = field_name_dict.get(set_bit, "")
            if set_bit != 0 and char_name:
                characteristics[char_name] = set_bit

        setattr(
            self,
            field_name,
            Structure(
                offset=field_info["offset"],
                size=size,
                value=int_value,
                data=data,
                absolute_offset=absolute_offset,
                values=characteristics,
            ),
        )
        getattr(self, field_name)._file_data = file_data

    @classmethod
    def parse_from_data(cls, file_data, **cls_args):
        """Parses the Structure from the file data."""
        self = cls(**cls_args)
        self._file_data = file_data
        for field_name, field_info in self._fields.items():
            self.process_field(file_data, field_name, field_info)
        return self


class DOSHeader(Structure):
    """The dos header of the PE file"""

    _fields = {
        "Signature": {"offset": 0, "size": 2},
        "PEHeaderOffset": {"offset": 0x3C, "size": 4},
    }


class PEHeader(Structure):
    """PE signature plus the COFF header"""

    _fields = {
        "Signature": {"offset": 0, "size": 4},
        "Machine": {"offset": 4, "size": 2},
        "NumberOfSections": {"offset": 6, "size": 2},
        "TimeDateStamp": {"offset": 8, "size": 4},
        "PointerToSymbolTable": {"offset": 12, "size": 4},
        "NumberOfSymbols": {"offset": 16, "size": 4},
        "SizeOfOptionalHeader": {"offset": 20, "size": 2},
        "Characteristics": {"offset": 22, "size": 2},
    }


class OptionalHeader(Structure):
    _fields_32_plus = {
        "Magic": {"offset": 0, "size": 2},
        "MajorLinkerVersion": {"offset": 2, "size": 1},
        "MinorLinkerVersion": {"offset": 3, "size": 1},
        "SizeOfCode": {"offset": 4, "size": 4},
        "SizeOfInitializedData": {"offset": 8, "size": 4},
        "SizeOfUninitializedData": {"offset": 12, "size": 4},
        "AddressOfEntryPoint": {"offset": 16, "size": 4},
        "BaseOfCode": {"offset": 20, "size": 4},
        "ImageBase": {"offset": 24, "size": 8},
        "SectionAlignment": {"offset": 32, "size": 4},
        "FileAlignment": {"offset": 36, "size": 4},
        "MajorOperatingSystemVersion": {"offset": 40, "size": 2},
        "MinorOperatingSystemVersion": {"offset": 42, "size": 2},
        "MajorImageVersion": {"offset": 44, "size": 2},
        "MinorImageVersion": {"offset": 46, "size": 2},
        "MajorSubsystemVersion": {"offset": 48, "size": 2},
        "MinorSubsystemVersion": {"offset": 50, "size": 2},
        "Reserved": {"offset": 52, "size": 4},
        "SizeOfImage": {"offset": 56, "size": 4},
        "SizeOfHeaders": {"offset": 60, "size": 4},
        "SizeOfHeaders": {"offset": 60, "size": 4},
        "CheckSum": {"offset": 64, "size": 4},
        "Subsystem": {"offset": 68, "size": 2},
        "DLL_Characteristics": {"offset": 70, "size": 2},
        "SizeOfStackReserve": {"offset": 72, "size": 8},
        "SizeOfStackCommit": {"offset": 80, "size": 8},
        "SizeOfHeapReserve": {"offset": 88, "size": 8},
        "SizeOfHeapCommit": {"offset": 96, "size": 8},
        "LoaderFlags": {"offset": 104, "size": 4},
        "NumberOfRvaAndSizes": {"offset": 108, "size": 4},
        "ExportTableAddress": {"offset": 112, "size": 4},
        "ExportTableSize": {"offset": 116, "size": 4},
        "ImportTableAddress": {"offset": 120, "size": 4},
        "ImportTableSize": {"offset": 124, "size": 4},
        "ResourceTableAddress": {"offset": 128, "size": 4},
        "ResourceTableSize": {"offset": 132, "size": 4},
        "ExceptionTableAddress": {"offset": 136, "size": 4},
        "ExceptionTableSize": {"offset": 140, "size": 4},
        "CertificateTableAddress": {"offset": 144, "size": 4},
        "CertificateTableSize": {"offset": 148, "size": 4},
        "BaseRelocationTableAddress": {"offset": 152, "size": 4},
        "BaseRelocationTableSize": {"offset": 156, "size": 4},
        "DebugAddress": {"offset": 160, "size": 4},
        "DebugSize": {"offset": 164, "size": 4},
        "ArchitectureAddress": {"offset": 168, "size": 4},
        "ArchitectureSize": {"offset": 172, "size": 4},
        "GlobalPtrAddress": {"offset": 176, "size": 8},
        "GlobalPtrSize": {"offset": 184, "size": 0},
        "ThreadLocalStorageTableAddress": {"offset": 184, "size": 4},
        "ThreadLocalStorageTableSize": {"offset": 188, "size": 4},
        "LoadConfigTableAddress": {"offset": 192, "size": 4},
        "LoadConfigTableSize": {"offset": 196, "size": 4},
        "BoundImportAddress": {"offset": 200, "size": 4},
        "BoundImportSize": {"offset": 204, "size": 4},
        "ImportAddressTableAddress": {"offset": 208, "size": 4},
        "ImportAddressTableSize": {"offset": 212, "size": 4},
        "DelayImportDescriptorAddress": {"offset": 216, "size": 4},
        "DelayImportDescriptorSize": {"offset": 220, "size": 4},
        "COMRuntimeHeaderAddress": {"offset": 224, "size": 4},
        "COMRuntimeHeaderSize": {"offset": 228, "size": 4},
        "Reserved2": {"offset": 232, "size": 8},
    }

    _fields_32 = {
        "Magic": {"offset": 0, "size": 2},
        "MajorLinkerVersion": {"offset": 2, "size": 1},
        "MinorLinkerVersion": {"offset": 3, "size": 1},
        "SizeOfCode": {"offset": 4, "size": 4},
        "SizeOfInitializedData": {"offset": 8, "size": 4},  #
        "SizeOfUninitializedData": {"offset": 12, "size": 4},
        "AddressOfEntryPoint": {"offset": 16, "size": 4},
        "BaseOfCode": {"offset": 20, "size": 4},
        "BaseOfData": {"offset": 24, "size": 4},
        "ImageBase": {"offset": 28, "size": 4},
        "SectionAlignment": {"offset": 32, "size": 4},
        "FileAlignment": {"offset": 36, "size": 4},
        "MajorOperatingSystemVersion": {"offset": 40, "size": 2},
        "MinorOperatingSystemVersion": {"offset": 42, "size": 2},
        "MajorImageVersion": {"offset": 44, "size": 2},
        "MinorImageVersion": {"offset": 46, "size": 2},
        "MajorSubsystemVersion": {"offset": 48, "size": 2},
        "MinorSubsystemVersion": {"offset": 50, "size": 2},
        "Reserved": {"offset": 52, "size": 4},
        "SizeOfImage": {"offset": 56, "size": 4},  #
        "SizeOfHeaders": {"offset": 60, "size": 4},
        "CheckSum": {"offset": 64, "size": 4},
        "Subsystem": {"offset": 68, "size": 2},
        "DLL_Characteristics": {"offset": 70, "size": 2},
        "SizeOfStackReserve": {"offset": 72, "size": 4},
        "SizeOfStackCommit": {"offset": 76, "size": 4},
        "SizeOfHeapReserve": {"offset": 80, "size": 4},
        "SizeOfHeapCommit": {"offset": 84, "size": 4},
        "LoaderFlags": {"offset": 88, "size": 4},
        "NumberOfRvaAndSizes": {"offset": 92, "size": 4},
        "ExportTableAddress": {"offset": 96, "size": 4},
        "ExportTableSize": {"offset": 100, "size": 4},
        "ImportTableAddress": {"offset": 104, "size": 4},
        "ImportTableSize": {"offset": 108, "size": 4},
        "ResourceTableAddress": {"offset": 112, "size": 4},
        "ResourceTableSize": {"offset": 116, "size": 4},  #
        "ExceptionTableAddress": {"offset": 120, "size": 4},
        "ExceptionTableSize": {"offset": 124, "size": 4},
        "CertificateTableAddress": {"offset": 128, "size": 4},
        "CertificateTableSize": {"offset": 132, "size": 4},
        "BaseRelocationTableAddress": {"offset": 136, "size": 4},  #
        "BaseRelocationTableSize": {"offset": 140, "size": 4},
        "DebugAddress": {"offset": 144, "size": 4},
        "DebugSize": {"offset": 148, "size": 4},
        "ArchitectureAddress": {"offset": 152, "size": 4},
        "ArchitectureSize": {"offset": 156, "size": 4},
        "GlobalPtrAddress": {"offset": 160, "size": 8},
        "GlobalPtrSize": {"offset": 168, "size": 0},
        "ThreadLocalStorageTableAddress": {"offset": 168, "size": 4},
        "ThreadLocalStorageTableSize": {"offset": 172, "size": 4},
        "LoadConfigTableAddress": {"offset": 176, "size": 4},
        "LoadConfigTableSize": {"offset": 180, "size": 4},
        "BoundImportAddress": {"offset": 184, "size": 4},
        "BoundImportSize": {"offset": 188, "size": 4},
        "ImportAddressTableAddress": {"offset": 192, "size": 4},
        "ImportAddressTableSize": {"offset": 196, "size": 4},
        "DelayImportDescriptorAddress": {"offset": 200, "size": 4},
        "DelayImportDescriptorSize": {"offset": 204, "size": 4},
        "COMRuntimeHeaderAddress": {"offset": 208, "size": 4},
        "COMRuntimeHeaderSize": {"offset": 212, "size": 4},
        "Reserved2": {"offset": 216, "size": 8},
    }

    def process_DLL_Characteristics(self, file_data, field_name, field_info):
        self.process_Characteristics(file_data, field_name, field_info)

    def process_field(self, file_data, field_name, field_info):
        if hasattr(self, "process_" + field_name) and callable(
            getattr(self, "process_" + field_name)
        ):
            getattr(self, "process_" + field_name)(file_data, field_name, field_info)
        else:
            absolute_offset = field_info["offset"] + self.absolute_offset
            size = field_info["size"]
            self.size += size
            int_value, data = read_bytes(file_data, absolute_offset, size)
            field_name_dict = read_from_name_dict(self, field_name)
            name = field_name_dict.get(int_value, "")
            friendly_name = name.replace("_", " ").capitalize()

            setattr(
                self,
                field_name,
                Structure(
                    offset=field_info["offset"],
                    size=size,
                    value=int_value,
                    data=data,
                    absolute_offset=absolute_offset,
                    name=name,
                    friendly_name=friendly_name,
                ),
            )
            getattr(self, field_name)._file_data = file_data

    @classmethod
    def parse_from_data(cls, file_data, **cls_args):
        """Parses the Structure from the file data."""
        self = cls(**cls_args)
        self._file_data = file_data
        magic, x = read_bytes(file_data, self.absolute_offset, 2)

        if magic == _32BIT_MAGIC:
            self._fields = self._fields_32
        elif magic == _32BIT_PLUS_MAGIC:
            self._fields = self._fields_32_plus
        else:
            print(magic, _32BIT_MAGIC, _32BIT_PLUS_MAGIC)
            raise PEFormatError("Magic for Optional Header is invalid.")

        for field_name, field_info in self._fields.items():
            self.process_field(file_data, field_name, field_info)

        return self


class SectionHeader(Structure):
    """Section Header. Each section header is a row in the section table"""

    _fields = {
        "Name": {"offset": 0, "size": 8},
        "VirtualSize": {"offset": 8, "size": 4},  # .rsrc
        "VirtualAddress": {"offset": 12, "size": 4},  # .reloc
        "SizeOfRawData": {"offset": 16, "size": 4},  # .rsrc
        "PointerToRawData": {"offset": 20, "size": 4},  # .reloc
        "PointerToRelocations": {"offset": 24, "size": 4},
        "PointerToLineNumbers": {"offset": 28, "size": 4},
        "NumberOfRelocations": {"offset": 32, "size": 2},
        "NumberOfLineNumbers": {"offset": 34, "size": 2},
        "Characteristics": {"offset": 36, "size": 4},
    }


class ResourceDirectoryTable(Structure):
    _fields = {
        "Characteristics": {"offset": 0, "size": 4},
        "TimeDateStamp": {"offset": 4, "size": 4},
        "MajorVersion": {"offset": 8, "size": 2},
        "MinorVersion": {"offset": 10, "size": 2},
        "NumberOfNameEntries": {"offset": 12, "size": 2},
        "NumberOfIDEntries": {"offset": 14, "size": 2},
    }

    def __init__(self, *args, **kwargs):
        self.name_entries = []
        self.id_entries = []
        self.subdirectory_tables = []
        self.data_entries = []

        super(ResourceDirectoryTable, self).__init__(*args, **kwargs)


class ResourceDirectoryEntryName(Structure):
    _fields = {
        "NameRVA": {"offset": 0, "size": 4},
        "DataOrSubdirectoryEntryRVA": {
            "offset": 4,  # high bit 1 for subdir RVA
            "size": 4,
        },
    }

    directory_string = None

    def is_data_entry(self):
        return test_bit(self.DataOrSubdirectoryEntryRVA.value, 31) == 0

    def data_rva_empty(self):
        return self.get_data_or_subdirectory_rva() == 0

    def get_data_or_subdirectory_rva(self, virtual_to_physical=0):
        return clear_bit(
            self.DataOrSubdirectoryEntryRVA.value - virtual_to_physical, 31
        )

    def get_data_or_subdirectory_absolute_offset(self):
        return (
            self.get_data_or_subdirectory_rva()
            + self._section_header.PointerToRawData.value
        )

    def get_name_absolute_offset(self):
        return (
            clear_bit(self.NameRVA.value, 31)
            + self._section_header.PointerToRawData.value
        )


class ResourceDirectoryEntryID(Structure):
    _fields = {
        "IntegerID": {"offset": 0, "size": 4},
        "DataOrSubdirectoryEntryRVA": {
            "offset": 4,  # high bit 1 for Subdir RVA
            "size": 4,
        },
    }

    def is_data_entry(self):
        return test_bit(self.DataOrSubdirectoryEntryRVA.value, 31) == 0

    def data_rva_empty(self):
        return self.get_data_or_subdirectory_rva() == 0

    def get_data_or_subdirectory_rva(self, virtual_to_physical=0):
        return clear_bit(
            self.DataOrSubdirectoryEntryRVA.value - virtual_to_physical, 31
        )

    def get_data_or_subdirectory_absolute_offset(self, vtp=0):
        return (
            self.get_data_or_subdirectory_rva(vtp)
            + self._section_header.PointerToRawData.value
        )


class ResourceDirectoryString(Structure):
    _fields = {
        "Length": {"offset": 0, "size": 2},
        # String : offset=2, len=Length
    }

    @classmethod
    def parse_from_data(cls, file_data, **cls_args):
        """Parses the Structure from the file data."""
        self = cls(**cls_args)
        self._file_data = file_data
        str_len, _ = read_bytes(file_data, self.absolute_offset, 2)

        self._fields["String"] = {"offset": 2, "size": str_len}

        for field_name, field_info in self._fields.items():
            self.process_field(file_data, field_name, field_info)

        return self

    def process_String(self, file_data, field_name, field_info):
        absolute_offset = field_info["offset"] + self.absolute_offset
        size = field_info["size"]
        self.size += size
        data = ""
        for i in range(size):
            val, dat = read_bytes(file_data, absolute_offset + i * 2, 2)
            data += str(dat, "utf-8")

        setattr(
            self,
            field_name,
            Structure(
                offset=field_info["offset"],
                size=size,
                data=data,
                absolute_offset=absolute_offset,
            ),
        )


class ResourceDataEntry(Structure):
    _fields = {
        "DataRVA": {"offset": 0, "size": 4},
        "Size": {"offset": 4, "size": 4},
        "Codepage": {"offset": 8, "size": 4},
        "Reserved": {"offset": 12, "size": 4},
    }

    def get_data_absolute_offset(self):
        return (
            self._section_header.PointerToRawData.value
            - self._section_header.VirtualAddress.value
            + self.DataRVA.value
        )

    def process_field(self, file_data, field_name, field_info):
        if hasattr(self, "process_" + field_name) and callable(
            getattr(self, "process_" + field_name)
        ):
            getattr(self, "process_" + field_name)(file_data, field_name, field_info)
        else:
            absolute_offset = field_info["offset"] + self.absolute_offset
            size = field_info["size"]
            self.size += size
            int_value, data = read_bytes(file_data, absolute_offset, size)
            field_name_dict = read_from_name_dict(self, field_name)
            name = field_name_dict.get(int_value, "")
            friendly_name = name.replace("_", " ").capitalize()

            setattr(
                self,
                field_name,
                Structure(
                    offset=field_info["offset"],
                    size=size,
                    value=int_value,
                    data=data,
                    absolute_offset=absolute_offset,
                    name=name,
                    friendly_name=friendly_name,
                ),
            )
            getattr(self, field_name)._file_data = file_data

    @classmethod
    def parse_from_data(cls, file_data, **cls_args):
        """Parses the Structure from the file data."""
        self = cls(**cls_args)
        self._file_data = file_data
        for field_name, field_info in self._fields.items():
            self.process_field(file_data, field_name, field_info)

        self.data = read_data(
            file_data, self.get_data_absolute_offset(), self.Size.value
        )

        return self


class ResourceHeader(Structure):
    _fields = {
        "DataSize": {"offset": 0, "size": 4},
        "HeaderSize": {"offset": 4, "size": 4},
        "Type": {"offset": 8, "size": 4},
        "Name": {"offset": 12, "size": 4},
        "DataVersion": {"offset": 16, "size": 4},
        "MemoryFlags": {"offset": 20, "size": 2},
        "LanguageID": {"offset": 22, "size": 2},
        "Version": {"offset": 24, "size": 4},
        "Characteristics": {"offset": 28, "size": 4},
    }

    def get_name(self):
        return resource_types[self.Type.value]

    def set_name(self, value):
        for k, v in resource_types.items():
            if v == value:
                self.Type.value = k
                return


class IconHeader(Structure):
    _fields = {
        "Reserved": {"offset": 0, "size": 2},
        "ImageType": {"offset": 2, "size": 2},  # 1 for ICO, 2 for CUR, others invalid
        "ImageCount": {"offset": 4, "size": 2},
    }

    def copy_from(self, group_header):
        self.Reserved.value = group_header.Reserved.value
        self.ImageType.value = group_header.ResourceType.value
        self.ImageCount.value = group_header.ResourceCount.value

        self.entries = []
        entry_offset = 0
        self.total_size = self.size
        for group_entry in group_header.entries:
            icon_entry = IconEntry.parse_from_data(
                bytearray(""),
                absolute_offset=self.absolute_offset + self.size + entry_offset,
                offset=entry_offset,
            )
            icon_entry._file_data = self._file_data
            icon_entry.copy_from(group_entry)
            icon_entry.number = group_entry.number
            self.entries.append(icon_entry)
            entry_offset += icon_entry.size
            self.total_size += icon_entry.size

    @classmethod
    def parse_from_data(cls, file_data, **cls_args):
        """Parses the Structure from the file data."""
        self = cls(**cls_args)
        self._file_data = file_data

        for field_name, field_info in self._fields.items():
            self.process_field(file_data, field_name, field_info)

        self.entries = []
        entry_offset = 0
        self.total_size = self.size
        for i in range(self.ImageCount.value):
            entry = IconEntry.parse_from_data(
                file_data,
                absolute_offset=self.absolute_offset + self.size + entry_offset,
                offset=entry_offset,
            )
            entry.number = i + 1
            self.entries.append(entry)
            entry_offset += entry.size
            self.total_size += entry.size

        return self


class GroupHeader(Structure):
    _fields = {
        "Reserved": {"offset": 0, "size": 2},
        "ResourceType": {
            "offset": 2,  # 1 for ICO, 2 for CUR, others invalid
            "size": 2,
        },
        "ResourceCount": {"offset": 4, "size": 2},
    }

    def copy_from(self, icon_header):
        self.Reserved._file_data = self._file_data
        self.ResourceType._file_data = self._file_data
        self.ResourceCount._file_data = self._file_data

        self.Reserved.value = icon_header.Reserved.value
        self.ResourceType.value = icon_header.ImageType.value
        self.ResourceCount.value = icon_header.ImageCount.value

        self.entries = []
        entry_offset = 0
        self.total_size = self.size
        for icon_entry in icon_header.entries:
            group_entry = GroupEntry.parse_from_data(
                bytearray(b""),
                absolute_offset=self.absolute_offset + self.size + entry_offset,
                offset=entry_offset,
            )
            group_entry._file_data = self._file_data
            group_entry.copy_from(icon_entry)
            group_entry.number = icon_entry.number
            self.entries.append(group_entry)
            entry_offset += group_entry.size
            self.total_size += group_entry.size

    @classmethod
    def parse_from_data(cls, file_data, **cls_args):
        """Parses the Structure from the file data."""
        self = cls(**cls_args)
        self._file_data = file_data

        for field_name, field_info in self._fields.items():
            self.process_field(file_data, field_name, field_info)

        self.entries = []
        entry_offset = 0
        self.total_size = self.size
        for i in range(self.ResourceCount.value):
            entry = GroupEntry.parse_from_data(
                file_data,
                absolute_offset=self.absolute_offset + self.size + entry_offset,
                offset=entry_offset,
            )
            entry.number = i + 1
            self.entries.append(entry)
            entry_offset += entry.size
            self.total_size += entry.size

        return self


class IconEntry(Structure):
    _fields = {
        "Width": {"offset": 0, "size": 1},
        "Height": {"offset": 1, "size": 1},
        "ColorCount": {"offset": 2, "size": 1},
        "Reserved": {"offset": 3, "size": 1},
        "ColorPlanes": {"offset": 4, "size": 2},
        "BitCount": {"offset": 6, "size": 2},  # bits per pixel
        "DataSize": {"offset": 8, "size": 4},
        "OffsetToData": {"offset": 12, "size": 4},  # from start of file
    }

    def copy_from(self, group_entry, entries):
        self.Width.value = group_entry.Width.value
        self.Height.value = group_entry.Height.value
        self.ColorCount.value = group_entry.ColorCount.value
        self.Reserved.value = group_entry.Reserved.value
        self.ColorPlanes.value = group_entry.ColorPlanes.value
        self.BitCount.value = group_entry.BitCount.value
        self.DataSize.value = group_entry.DataSize.value
        self.OffsetToData.value = self._get_entry_offset(group_entry, entries)

    def _get_entry_offset(self, group_entry, group_entries):
        offset = 6  # Default icon header size
        offset += self.size * len(group_entries)

        for i in range(group_entry.number - 1):
            offset += group_entries[i].DataSize.value

        return offset

    @classmethod
    def parse_from_data(cls, file_data, **cls_args):
        """Parses the Structure from the file data."""
        self = cls(**cls_args)
        self._file_data = file_data
        for field_name, field_info in self._fields.items():
            self.process_field(file_data, field_name, field_info)

        self.data = read_data(file_data, self.OffsetToData.value, self.DataSize.value)

        return self


class GroupEntry(Structure):
    _fields = {
        "Width": {"offset": 0, "size": 1},
        "Height": {"offset": 1, "size": 1},
        "ColorCount": {"offset": 2, "size": 1},
        "Reserved": {"offset": 3, "size": 1},
        "ColorPlanes": {"offset": 4, "size": 2},
        "BitCount": {"offset": 6, "size": 2},
        "DataSize": {"offset": 8, "size": 4},
        "IconCursorId": {"offset": 12, "size": 2},
    }

    def copy_from(self, icon_entry):
        self.Width._file_data = self._file_data
        self.Height._file_data = self._file_data
        self.ColorCount._file_data = self._file_data
        self.Reserved._file_data = self._file_data
        self.ColorPlanes._file_data = self._file_data
        self.BitCount._file_data = self._file_data
        self.DataSize._file_data = self._file_data
        self.IconCursorId._file_data = self._file_data

        self.Width.value = icon_entry.Width.value
        self.Height.value = icon_entry.Height.value
        self.ColorCount.value = icon_entry.ColorCount.value
        self.Reserved.value = icon_entry.Reserved.value
        self.ColorPlanes.value = icon_entry.ColorPlanes.value
        self.BitCount.value = icon_entry.BitCount.value
        self.DataSize.value = icon_entry.DataSize.value
        self.IconCursorId.value = icon_entry.number


class PEFile(Printable):
    """Reads a portable exe file in either big or little endian.
    Right now this only reads the .rsrc section.
    """

    signature = b"MZ"
    dos_header = None

    def __init__(self, file_path, endian="little"):
        self.file_path = os.path.abspath(os.path.expanduser(file_path))

        self.endian = endian
        if not self.is_PEFile():
            raise PEFormatError(
                "File is not a proper portable executable formatted file!"
            )

        self.pe_file_data = bytearray(open(self.file_path, "rb").read())

        self.dos_header = DOSHeader.parse_from_data(self.pe_file_data)
        self.pe_header = PEHeader.parse_from_data(
            self.pe_file_data, absolute_offset=self.dos_header.PEHeaderOffset.value
        )
        self.optional_header = OptionalHeader.parse_from_data(
            self.pe_file_data,
            absolute_offset=self.pe_header.size + self.pe_header.absolute_offset,
        )

        number_of_sections = self.pe_header.NumberOfSections.value
        section_size = 40
        section_offset = (
            self.pe_header.size
            + self.pe_header.absolute_offset
            + self.pe_header.SizeOfOptionalHeader.value
        )
        self.sections = {}

        for section_number in range(number_of_sections):
            section_header = SectionHeader.parse_from_data(
                self.pe_file_data, absolute_offset=section_offset
            )
            section_offset += section_size
            header_name = str(section_header.Name.data, "utf-8").strip("\x00")
            self.sections[header_name] = section_header

            if section_header.PointerToLineNumbers.value != 0:
                print(
                    "{} section contains line number COFF table, which is not implemented yet.".format(
                        section_header.Name
                    )
                )

            if section_header.PointerToRelocations.value != 0:
                print(
                    "{} section contains relocation table, which is not implemented yet.".format(
                        section_header.Name
                    )
                )

            if section_header.Name.data == b".rsrc\x00\x00\x00":
                current_table_pointer = section_header.PointerToRawData.value
                current_resource_directory_table = (
                    ResourceDirectoryTable.parse_from_data(
                        self.pe_file_data,
                        absolute_offset=current_table_pointer,
                        _section_header=section_header,
                        type=None,
                    )
                )
                self.resource_directory_table = current_resource_directory_table
                cur_level = 0
                stack = [(current_resource_directory_table, cur_level)]

                delta = (
                    section_header.VirtualAddress.value
                    - section_header.PointerToRawData.value
                )

                while stack:
                    resource_directory_table, level = stack.pop()
                    num_name_entries = (
                        resource_directory_table.NumberOfNameEntries.value
                    )
                    num_id_entries = resource_directory_table.NumberOfIDEntries.value
                    current_offset = (
                        resource_directory_table.absolute_offset
                        + resource_directory_table.size
                    )

                    for i in range(num_name_entries):
                        name_entry = ResourceDirectoryEntryName.parse_from_data(
                            self.pe_file_data,
                            absolute_offset=current_offset,
                            _section_header=section_header,
                        )
                        current_offset += name_entry.size

                        string_offset = name_entry.get_name_absolute_offset()
                        name_entry.directory_string = (
                            ResourceDirectoryString.parse_from_data(
                                self.pe_file_data,
                                absolute_offset=string_offset,
                                _section_header=section_header,
                            )
                        )

                        offset = name_entry.get_data_or_subdirectory_absolute_offset()

                        if not name_entry.data_rva_empty():
                            if name_entry.is_data_entry():
                                rd = ResourceDataEntry.parse_from_data(
                                    self.pe_file_data,
                                    absolute_offset=offset,
                                    _section_header=section_header,
                                )
                                resource_directory_table.data_entries.append(rd)
                            else:
                                rd = ResourceDirectoryTable.parse_from_data(
                                    self.pe_file_data,
                                    absolute_offset=offset,
                                    _section_header=section_header,
                                    type=None,
                                )
                                resource_directory_table.subdirectory_tables.append(rd)

                                stack.append((rd, level + 1))

                        resource_directory_table.name_entries.append(name_entry)

                    for i in range(num_id_entries):
                        id_entry = ResourceDirectoryEntryID.parse_from_data(
                            self.pe_file_data,
                            absolute_offset=current_offset,
                            _section_header=section_header,
                        )
                        current_offset += id_entry.size

                        offset = id_entry.get_data_or_subdirectory_absolute_offset()

                        if id_entry.is_data_entry():
                            rd = ResourceDataEntry.parse_from_data(
                                self.pe_file_data,
                                absolute_offset=offset,
                                _section_header=section_header,
                            )
                            resource_directory_table.data_entries.append(rd)
                        else:
                            id_entry.name = str(id_entry.IntegerID.value)
                            if level + 1 == 1:
                                id_entry.name = resource_types[id_entry.IntegerID.value]
                            rd = ResourceDirectoryTable.parse_from_data(
                                self.pe_file_data,
                                absolute_offset=offset,
                                _section_header=section_header,
                                type=id_entry.IntegerID.value,
                            )
                            resource_directory_table.subdirectory_tables.append(rd)
                            stack.append((rd, level + 1))
                        resource_directory_table.id_entries.append(id_entry)

    def replace_icon(self, icon_path):
        """Replaces an icon in the pe file with the one specified.
        This only replaces the largest icon and resizes the input
        image to match so that the data is undisturbed. I tried to
        update the pointers automatically by moving the data to the end
        of the file, but that did not work. Comments were left as history
        to what I attempted.
        """
        icon_path = os.path.expanduser(
            icon_path
        )  # this needs to be a string and not unicode

        if not os.path.exists(icon_path):
            raise Exception("Icon {} does not exist".format(icon_path))

        resource_section = self.sections[".rsrc"]

        g_icon_dir = self.get_directory_by_type(ResourceTypes.Group_Icon)
        g_icon_data_entry = g_icon_dir.subdirectory_tables[0].data_entries[0]
        icon_dir = self.get_directory_by_type(ResourceTypes.Icon)
        icon_data_entry = icon_dir.subdirectory_tables[0].data_entries[0]

        group_header = GroupHeader.parse_from_data(
            self.pe_file_data,
            absolute_offset=g_icon_data_entry.get_data_absolute_offset(),
        )
        g_entry = group_header.entries[0]

        icon = Image.open(icon_path)
        width = g_entry.Width.value
        height = g_entry.Height.value

        if width == 0:
            width = 256
        if height == 0:
            height = 256

        i_data = resize(icon, (width, height), format="ico")

        new_icon_size = len(i_data)
        icon_file_size = g_entry.DataSize.value + group_header.size + g_entry.size + 2

        # 9662 is the exact length of the icon in nw.exe
        extra_size = icon_file_size - new_icon_size

        if extra_size < 0:
            extra_size = 0
        icon_data = bytearray(i_data) + bytearray(extra_size)

        icon_header = IconHeader.parse_from_data(icon_data, absolute_offset=0)

        # group_header.absolute_offset = len(self.pe_file_data)
        # g_icon_data_entry.DataRVA.value = len(self.pe_file_data) - resource_section.PointerToRawData.value + resource_section.VirtualAddress.value
        # padding = 6+14*len(icon_header.entries)
        # g_icon_data_entry.Size.value = padding

        # self.pe_file_data += bytearray(padding)
        group_header._file_data = self.pe_file_data
        group_header.copy_from(icon_header)

        # icon_data_entry.DataRVA.value = len(self.pe_file_data) - resource_section.PointerToRawData.value + resource_section.VirtualAddress.value
        # print hex(icon_data_entry.DataRVA.value), hex(len(self.pe_file_data)), hex(icon_data_entry.get_data_absolute_offset())

        # print hex(read_bytes(self.pe_file_data[icon_data_entry.DataRVA.absolute_offset:icon_data_entry.DataRVA.absolute_offset+icon_data_entry.DataRVA.size],0, icon_data_entry.DataRVA.size)[0])

        # data = bytearray()
        # for entry in icon_header.entries:
        # data += entry.data
        # self.pe_file_data += entry.data

        # icon_data_entry.Size.value = len(data)

        # self.optional_header.SizeOfImage.value = self.optional_header.SizeOfImage.value + len(data) + padding
        # self.optional_header.ResourceTableSize.value = self.optional_header.ResourceTableSize.value + len(data) + padding
        # self.optional_header.SizeOfInitializedData.value = self.optional_header.SizeOfInitializedData.value + len(data) + padding
        # resource_section.SizeOfRawData.value = resource_section.SizeOfRawData.value + len(data) + padding
        # resource_section.VirtualSize.value = resource_section.VirtualSize.value + len(data) + padding
        # print icon_header.total_size
        data_address = icon_data_entry.get_data_absolute_offset()
        data_size = icon_data_entry.Size.value
        self.pe_file_data = (
            self.pe_file_data[:data_address]
            + icon_data[icon_header.total_size :]
            + self.pe_file_data[data_address + data_size :]
        )

    def write(self, file_name):
        with open(file_name, "wb+") as f:
            f.write(self.pe_file_data)

    def get_directory_by_type(self, type):
        """Gets the directory by resource type."""
        for d in self.resource_directory_table.subdirectory_tables:
            if d.type == type:
                return d

    def is_PEFile(self):
        """Checks if the file is a proper PE file"""
        signature = None
        try:
            with open(self.file_path, "rb") as f:
                signature = f.read(2)
        except IOError as e:
            raise e
        finally:
            return signature == self.signature
