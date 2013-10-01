# PhotoSort Project

## What is PhotoSort?

PhotoSort simplifies your photo inbox, it watches for a set of photo
input directories, to catalog and move into a predefined storage,
it can delete the input or keep it.

It does take care of duplicate files, if there is a duplicate in a
"deletable" source, it will be moved to the duplicates directory
for inspection. If it does found a duplicate in a non deletable source
it will just log it and ignore it.

## Why deletable or not deletable sources?

### Non deletables:

My use case is dropbox, mobile phone uploads pictures to dropbox,
the script picks them and packs them, you can decide if they must
be removed from your dropbox account.

### Deletables:

An SD card, or a NAS input directory for pictures, you just drag
and drop, and the daemon will discover the new files, process them,
delete them.

## The database

Well, it's a plain textfile for now, I want to be able to remove or edit
entries by hand if needed, at least on early stages of the project.

In the future this could be an sqlite file.

## Configuration

Configuration is stored in YAML format, this is an example file:

'''
sources:
  dropbox:
    dir: '/Users/ajo/Dropbox/mobilephotos'
    delete: False
  nasinbox:
    dir: '/Volumes/casa/Fotos/inbox'
    delete: True


output_dir: '/Volumes/casa/Fotos'
duplicates_dir: 'duplicates'
log_file: 'photosort.log'
db_file: 'photosort.db'

dir_pattern: "%(year)s/%(year)s_%(month)s_%(day)s"
'''