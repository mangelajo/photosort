# PhotoSort Project

## What is PhotoSort?

PhotoSort simplifies your photo inbox, it watches for a set of photo
input directories, to catalog and move into a predefined storage,
it can delete the input or keep it.

It does take care of duplicate files, if there is a duplicate in a
it will be moved to the duplicates directory

## The database

It's a plain textfile for now, I want to be able to remove or edit
entries by hand if needed, at least on early stages of the project.

In the future this must be an sqlite file.

## Configuration

Configuration is stored in YAML format, this is an example file:

```
sources:
  dropbox:
    dir: '/Users/ajo/Dropbox/Camera Uploads'
  nasinbox:
    dir: '/Volumes/casa/Fotos/inbox'


output_dir: '/mnt/nas/Pictures'
duplicates_dir: 'duplicates'
log_file: 'photosort.log'
db_file: 'photosort.db'

dir_pattern: "%(year)s/%(year)s_%(month)s_%(day)s"
```
