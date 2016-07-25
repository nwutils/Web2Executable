from io import BytesIO
try:
    from PIL import Image as im
    IMAGE_UTILS_AVAILABLE = True
    Image = im.open
    def resize(image, size):
        output = BytesIO()
        back = im.new('RGBA', size, (0,0,0,0))
        image.thumbnail(size, im.ANTIALIAS)
        offset = [0,0]
        if image.size[0] >= image.size[1]:
            offset[1] = int(back.size[1]/2-image.size[1]/2)
        else:
            offset[0] = int(back.size[0]/2-image.size[0]/2)
        back.paste(image, tuple(offset))
        back.save(output, image.format)
        contents = output.getvalue()
        output.close()
        return contents
except ImportError:
    IMAGE_UTILS_AVAILABLE = False

LARGEST_ICON_SIZE = 1024
SMALLEST_ICON_SIZE = 16
sizes = [LARGEST_ICON_SIZE,512,256,128,48,32,SMALLEST_ICON_SIZE]

def nearest_icon_size(width, height):
    maximum = max(width, height)

    if maximum >= LARGEST_ICON_SIZE:
        return LARGEST_ICON_SIZE
    if maximum <= SMALLEST_ICON_SIZE:
        return SMALLEST_ICON_SIZE

    for i in range(len(sizes)-1):
        current_size = sizes[i]
        next_size = sizes[i+1]
        if current_size > maximum >= next_size:
            return next_size
