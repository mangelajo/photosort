# PhotoSort Container Image

This document describes how to build and run PhotoSort in a container.

## Building the Container

The container is based on Red Hat Universal Base Image 9 (UBI9) and includes:
- Python 3.11
- ExifTool (from EPEL)
- PhotoSort and all its dependencies

To build the container image:

```bash
make container-build
```

Or directly with podman/docker:

```bash
podman build -t photosort:latest -f Containerfile .
```

## Running PhotoSort in a Container

PhotoSort requires a configuration file to operate. You need to mount your config file and directories into the container.

### Basic Usage

1. Create a configuration file (e.g., `photosort-config.yml`)
2. Run the container with volume mounts:

```bash
podman run --rm \
  -v /path/to/photosort-config.yml:/etc/photosort.yml:ro \
  -v /path/to/source:/source \
  -v /path/to/output:/output \
  photosort:latest sync
```

### Example: Sync Operation

```bash
podman run --rm \
  -v $PWD/my_photosort.yaml:/etc/photosort.yml:ro \
  -v /media/photos/inbox:/inbox \
  -v /media/photos/sorted:/sorted \
  photosort:latest --config /etc/photosort.yml sync
```

### Example: Monitor Mode

Run in monitor mode (continuously watches for new files):

```bash
podman run -d \
  --name photosort-monitor \
  -v $PWD/my_photosort.yaml:/etc/photosort.yml:ro \
  -v /media/photos/inbox:/inbox \
  -v /media/photos/sorted:/sorted \
  photosort:latest --config /etc/photosort.yml monitor
```

Stop the monitor:

```bash
podman stop photosort-monitor
podman rm photosort-monitor
```

### Example: Rebuild Database

```bash
podman run --rm \
  -v $PWD/my_photosort.yaml:/etc/photosort.yml:ro \
  -v /media/photos/sorted:/sorted \
  photosort:latest --config /etc/photosort.yml rebuilddb
```

## Configuration File Notes

Your configuration file should use paths that match the container's mounted volumes. For example:

```yaml
output:
  dir: /sorted
  chmod: '0o755'
  db_file: photos.csv
  duplicates_dir: duplicates
  dir_pattern: '%(year)04d/%(year)04d_%(month)02d_%(day)02d'

sources:
  inbox:
    dir: /inbox
```

## Quick Test

To test the container build:

```bash
make container-run
```

This runs the container with `--help` to verify it's working.

## Building with Docker

If you're using Docker instead of Podman, simply replace `podman` with `docker` in all commands, or update the Makefile:

```bash
docker build -t photosort:latest -f Containerfile .
docker run --rm photosort:latest --help
```
