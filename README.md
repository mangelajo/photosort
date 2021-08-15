# PhotoSort Project

![Unit/Functional testing](https://github.com/mangelajo/photosort/workflows/Unit/Functional%20testing/badge.svg)

## What is PhotoSort?

PhotoSort simplifies your photo inbox, it watches for a set of photo
input directories, to catalog and move into a predefined storage,
it can delete the input or keep it.

It does take care of duplicate files, if there is a duplicate in a
it will be moved to the duplicates directory

## Easy install

```bash
pip3 install photosort
```

PhotoSort depends on `exiftool`, please install exiftool in your system.

## Alternate install method

```
git clone https://github.com/mangelajo/photosort
cd photosort
sudo python3 setup.py install
```

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

photosort depends on `exiftool` to identify the original creation
time of videos or pictures.

## Configuration

Configuration is stored in YAML format

Don't create the field 'file_prefix' if no change is desired in the filename 
of the media items.

This is an example file:

```
sources:
  dropbox:
    dir: '/Users/ajo/Dropbox/Camera Uploads'
  nasinbox:
    dir: '/mnt/nas/Pictures/inbox'


output:
  dir: '/mnt/nas/Pictures'
  dir_pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
  file_prefix: "%(year)d%(month)02d%(day)02d%(hour)02d%(minute)02d%(second)02d_"
  duplicates_dir: 'duplicates'
  chmod: 0o774
  log_file: 'photosort.log'
  db_file: 'photosort.db'
```

## Release Notes

### 2021.1.4
 * PIL image library has been replaced for exiftool so datetime from videos can
   be obtained too.
 * Files with no creation datetime EXIF or tags are ignored for now.