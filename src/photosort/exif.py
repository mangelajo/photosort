import exiftool
from exiftool.exceptions import ExifToolExecuteError

et = None


def start():
    """Starts a background batch exiftool process for quickly processing files
    """
    global et
    et = exiftool.ExifToolHelper()


def get_metadata(filename):
    global et
    if et is None:
        start()
    # exiftool.get_metadata returns a list of maps with the
    # exif metadata, because now it supports a list of files as input
    try:
        return et.get_metadata(filename)[0]
    except ExifToolExecuteError as e:
        print("ExifToolExecutError: %s" % e)
        print("args: %s" % e.args)
        print("stderr: %s" % e.stderr)
        print("stdout: %s" % e.stdout)
        raise e
