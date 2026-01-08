# PhotoSort Container Image

This document describes how to build and run PhotoSort in a container.

## Pre-built Images

Multi-architecture container images are automatically built and published to Quay.io:

**Image:** `quay.io/mangelajo/photosort:latest`

**Supported architectures:**
- `linux/amd64` (x86_64)
- `linux/arm64` (aarch64)

### Using Pre-built Images

Pull and run the latest image:

```bash
podman pull quay.io/mangelajo/photosort:latest
podman run --rm quay.io/mangelajo/photosort:latest --help
```

Or with Docker:

```bash
docker pull quay.io/mangelajo/photosort:latest
docker run --rm quay.io/mangelajo/photosort:latest --help
```

## Building the Container Locally

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
  quay.io/mangelajo/photosort:latest sync
```

### Example: Sync Operation

```bash
podman run --rm \
  -v $PWD/my_photosort.yaml:/etc/photosort.yml:ro \
  -v /media/photos/inbox:/inbox \
  -v /media/photos/sorted:/sorted \
  quay.io/mangelajo/photosort:latest --config /etc/photosort.yml sync
```

### Example: Monitor Mode

Run in monitor mode (continuously watches for new files):

```bash
podman run -d \
  --name photosort-monitor \
  -v $PWD/my_photosort.yaml:/etc/photosort.yml:ro \
  -v /media/photos/inbox:/inbox \
  -v /media/photos/sorted:/sorted \
  quay.io/mangelajo/photosort:latest --config /etc/photosort.yml monitor
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
  quay.io/mangelajo/photosort:latest --config /etc/photosort.yml rebuilddb
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

## Automated Builds

Multi-architecture container images are automatically built and pushed to Quay.io via GitHub Actions on every push to the master branch.

**Workflow:** `.github/workflows/container-build.yml`

**Triggers:**
- Push to `master` branch
- Git tags matching `v*` pattern
- Manual workflow dispatch

**Built platforms:**
- `linux/amd64` (Intel/AMD x86_64)
- `linux/arm64` (ARM 64-bit, Apple Silicon, Raspberry Pi 4+)

**Tags generated:**
- `latest` - Latest build from master branch
- `v1.2.3` - Semantic version tags
- `1.2` - Major.minor tags
- `1` - Major version tags

### Setting up Secrets

To enable automated pushes to Quay.io, configure these GitHub secrets in your repository settings:

- `QUAY_USERNAME` - Your Quay.io username
- `QUAY_PASSWORD` - Your Quay.io password or robot token (recommended)

**Creating a Quay.io Robot Account (recommended):**
1. Go to https://quay.io/organization/mangelajo?tab=robots
2. Create a new robot account with write permissions
3. Use the robot credentials for GitHub secrets
