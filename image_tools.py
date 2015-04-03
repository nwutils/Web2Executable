from pepy.pe import PEFile
from pycns import save_icns
import sys

if __name__ == '__main__':
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print ('image_tools <command> <args>\n'
               '  commands: save_icns input_file output_file\n'
               '            replace_icon input_exe icon_path [output_path]')
        sys.exit()

    command = sys.argv[1]
    file1, file2 = sys.argv[2:4]

    output_path = file1
    if len(sys.argv) == 5:
        output_path = sys.argv[4]

    if command == 'save_icns':
        save_icns(file1, file2)
    elif command == 'replace_icon':
        p = PEFile(file1)
        p.replace_icon(file2)
        p.write(output_path)
