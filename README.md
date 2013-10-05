# PhotoSort Project

## What is PhotoSort?

PhotoSort simplifies your photo inbox, it watches for a set of photo
input directories, to catalog and move into a predefined storage,
it can delete the input or keep it.

It does take care of duplicate files, if there is a duplicate in a
it will be moved to the duplicates directory

## Easy install

pip install photosort

## How to use it

Create a config file in /etc/photosort.yml or anywhere else and use
the --config parameter.

Then run:

photosort rebuilddb  # only for the first time

photosort sync # to sync new files in

or

photosort monitor # to keep it running and watching for new files


## The database

It's a plain textfile for now, I want to be able to remove or edit
entries by hand if needed, at least on early stages of the project.

In the future this must be an sqlite file.

## Dependencies

photosort depends on PIL and piyaml

## Configuration

Configuration is stored in YAML format, this is an example file:

```
sources:
  dropbox:
    dir: '/Users/ajo/Dropbox/Camera Uploads'
  nasinbox:
    dir: '/mnt/nas/Pictures/inbox'


output:
  dir: '/mnt/nas/Pictures'
  pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
  duplicates_dir: 'duplicates'
  chmod: 0o774
  log_file: 'photosort.log'
  db_file: 'photosort.db'


```
