import exiftool

et = None


def start():
    """Starts a background batch exiftool process for quickly processing files
    """
    global et
    et = exiftool.ExifTool()
    et.start()


def get_metadata(filename):
    global et
    if et is None:
        start()
    return et.get_metadata(filename)
