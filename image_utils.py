from cStringIO import StringIO
try:
    from PIL import Image as im
    Image = im.open
    def resize(image, size):
        output = StringIO()
        back = im.new('RGBA', size, (0,0,0,0))
        image.thumbnail(size, im.ANTIALIAS)
        offset = [0,0]
        if image.size[0] >= image.size[1]:
            offset[1] = back.size[1]/2-image.size[1]/2
        else:
            offset[0] = back.size[0]/2-image.size[0]/2
        back.paste(image, tuple(offset))
        back.save(output, image.format)
        contents = output.getvalue()
        output.close()
        return contents
except ImportError:
    raise Exception('Python image library PIL/pillow is required.')

LARGEST_ICON_SIZE = 1024
SMALLEST_ICON_SIZE = 16
sizes = [LARGEST_ICON_SIZE,512,256,128,48,32,SMALLEST_ICON_SIZE]

def nearest_icon_size(width, height):
    maximum = max(width, height)

    if maximum >= LARGEST_ICON_SIZE:
        return LARGEST_ICON_SIZE
    if maximum <= SMALLEST_ICON_SIZE:
        return SMALLEST_ICON_SIZE

    for i in xrange(len(sizes)-1):
        current_size = sizes[i]
        next_size = sizes[i+1]
        if current_size > maximum >= next_size:
            return next_size
