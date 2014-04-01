import os, zipfile, io
import sys

def zip_files(zip_file_name, *args, **kwargs):
    zip_file = zipfile.ZipFile(zip_file_name, 'w')
    verbose = kwargs.pop('verbose', False)
    exclude_paths = kwargs.pop('exclude_paths', [])
    old_path = os.getcwd()

    for arg in args:
        if os.path.exists(arg):
            if os.path.isdir(arg):
                directory = os.path.abspath(arg)
                os.chdir(directory)

                for root, dirs, files in os.walk(directory):
                    excluded = False
                    for exclude_path in exclude_paths:
                        if exclude_path in os.path.join(directory,root):
                            excluded = True
                    if not excluded:
                        for file in files:
                            file_loc = os.path.relpath(os.path.join(root, file), directory)
                            if verbose:
                                print file_loc
                            zip_file.write(file_loc)
                        for direc in dirs:
                            dir_loc = os.path.relpath(os.path.join(root, direc), directory)
                            if verbose:
                                print dir_loc
                            zip_file.write(dir_loc)

            else:
                file = os.path.abspath(arg)
                directory = os.path.abspath(os.path.join(file,'..'))
                os.chdir(directory)
                file_loc = os.path.relpath(arg, directory)
                if verbose:
                    print file_loc
                zip_file.write(file_loc)

    os.chdir(old_path)

    zip_file.close()

def join_files(destination, *args, **kwargs):
    with io.open(destination, 'wb') as dest_file:
        for arg in args:
            if os.path.exists(arg):
                with io.open(arg, 'rb') as file:
                    while True:
                        bytes = file.read(4096)
                        if len(bytes) == 0:
                            break
                        dest_file.write(bytes)

#def convert_icns_to_png(inputname, outputname, size=0, out_type='png'):
#    try:
#        # new_from_file_at_size() does not work, requires incremental loader
#        pixbuf = GdkPixbuf.Pixbuf.new_from_file(inputname)
#        if size:
#            width, height = pixbuf.get_width(), pixbuf.get_height()
#            if width > height:
#                if width > size:
#                    height = height * size / width
#                    width  = size
#            else:
#                if height > size:
#                    width  = width * size / height
#                    height = size
#
#            scaled = GdkPixbuf.Pixbuf.scale_simple(pixbuf, width, height,
#                                                   GdkPixbuf.InterpType.BILINEAR)
#        else:
#            scaled = pixbuf
#
#        scaled.savev(outputname, out_type, [], [])
#
#    except GLib.GError as e:
#        sys.stderr.write("%s:%d: %s\n" % (e.domain, e.code, e))
#        return e.code
