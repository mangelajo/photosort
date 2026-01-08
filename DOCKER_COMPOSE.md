# PhotoSort Docker Compose Deployment Guide

This guide explains how to deploy PhotoSort using Docker Compose with different configuration approaches.

## Quick Start (Recommended)

The simplest approach with embedded configuration:

```bash
# Use the production-ready configuration
docker-compose -f docker-compose.prod.yaml up -d

# Check logs
docker-compose -f docker-compose.prod.yaml logs -f

# Stop the service
docker-compose -f docker-compose.prod.yaml down
```

## Configuration Approaches

### 1. Embedded Config (Recommended)

**File**: `docker-compose.prod.yaml`

This approach embeds the configuration directly in the docker-compose file using Docker's `configs` feature. No external files needed!

**Pros**:
- Everything in one file
- Easy to version control
- No risk of missing config files
- Works with Docker Compose 3.3+

**Usage**:
```bash
docker-compose -f docker-compose.prod.yaml up -d
```

**To customize**: Edit the `configs.photosort_config.content` section in the YAML file.

### 2. External Config File

**File**: `docker-compose.yaml` (first service)

This approach uses an external YAML file (like `my_photosort.yaml`).

**Pros**:
- Easier to edit configuration (separate file)
- Can reuse existing config files
- Can have multiple config files for different scenarios

**Usage**:
```bash
# Create or copy your config file
cp my_photosort.yaml photosort-config.yaml

# Update paths in photosort-config.yaml to use container paths (/photos/...)

# Start the service
docker-compose up photosort
```

### 3. Multiple Configuration Examples

**File**: `docker-compose-examples.yaml`

Contains 6 different deployment scenarios:
- Simple deployment with external config
- Inline config (embedded)
- Multi-source (multiple input directories)
- One-time sync (not monitor mode)
- Debug mode with verbose logging
- Production deployment with healthcheck

**Usage**:
```bash
# Run a specific example
docker-compose -f docker-compose-examples.yaml up photosort-inline
```

## Configuration Details

### Volume Mapping

The key is mapping your host directories to container paths:

```yaml
volumes:
  - /Volumes/Fotos:/photos
  #   ↑               ↑
  #   Host path      Container path
```

Then reference the container path in your config:

```yaml
configs:
  photosort_config:
    content: |
      sources:
        nasinbox:
          dir: '/photos/inbox'  # Container path
      output:
        dir: '/photos'          # Container path
```

### Path Translation Example

If your photos are at `/Volumes/Fotos/inbox` on the host:

1. Mount the parent: `/Volumes/Fotos:/photos`
2. Reference in config: `/photos/inbox`

### Commands

PhotoSort supports three commands:

```yaml
# Continuous monitoring (checks every 10 seconds)
command: ["photosort", "--config", "/etc/photosort.yml", "monitor"]

# One-time sync
command: ["photosort", "--config", "/etc/photosort.yml", "sync"]

# Rebuild database from existing sorted photos
command: ["photosort", "--config", "/etc/photosort.yml", "rebuilddb"]

# Debug mode (verbose logging)
command: ["photosort", "--config", "/etc/photosort.yml", "--debug", "monitor"]
```

## Common Scenarios

### Scenario 1: NAS with Inbox Folder

You have photos in `/mnt/nas/photos/inbox` and want them sorted into `/mnt/nas/photos`:

```yaml
services:
  photosort:
    image: quay.io/mangelajo/photosort:latest
    volumes:
      - /mnt/nas/photos:/photos
    configs:
      - source: photosort_config
        target: /etc/photosort.yml
    command: ["photosort", "--config", "/etc/photosort.yml", "monitor"]

configs:
  photosort_config:
    content: |
      sources:
        inbox:
          dir: '/photos/inbox'
      output:
        dir: '/photos'
        dir_pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
        file_prefix: "%(year)d%(month)02d%(day)02d%(hour)02d%(minute)02d%(second)02d_"
        duplicates_dir: 'duplicates'
        chmod: '0o774'
        log_file: 'photosort.log'
        db_file: 'photosort.db'
```

### Scenario 2: Multiple Input Sources

You want to monitor multiple directories (camera uploads, phone sync, etc.):

```yaml
volumes:
  - /mnt/camera:/photos/camera:ro      # Read-only
  - /mnt/phone:/photos/phone:ro        # Read-only
  - /mnt/sorted:/photos/sorted         # Read-write

configs:
  photosort_config:
    content: |
      sources:
        camera:
          dir: '/photos/camera'
        phone:
          dir: '/photos/phone'
      output:
        dir: '/photos/sorted'
        # ... rest of config
```

### Scenario 3: One-Time Sync (Cron Job)

For scheduled syncs instead of continuous monitoring:

```yaml
services:
  photosort-sync:
    image: quay.io/mangelajo/photosort:latest
    volumes:
      - /path/to/photos:/photos
    command: ["photosort", "--config", "/etc/photosort.yml", "sync"]
    restart: "no"  # Don't restart - run once and exit
    # ... configs section
```

Then run with: `docker-compose run --rm photosort-sync`

## Configuration Options Explained

### Directory Pattern (`dir_pattern`)

Controls how subdirectories are organized:

```yaml
# Year/YYYY_MM_DD format
dir_pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
# Result: 2024/2024_01_15/

# Year/Month format
dir_pattern: "%(year)d/%(month)02d"
# Result: 2024/01/

# Flat year-based
dir_pattern: "%(year)04d"
# Result: 2024/
```

### File Prefix (`file_prefix`)

Adds timestamp prefix to filenames:

```yaml
# Full datetime prefix
file_prefix: "%(year)d%(month)02d%(day)02d%(hour)02d%(minute)02d%(second)02d_"
# Result: 20240115143052_IMG_1234.jpg

# Date only
file_prefix: "%(year)04d%(month)02d%(day)02d_"
# Result: 20240115_IMG_1234.jpg

# No prefix
file_prefix: ""
# Result: IMG_1234.jpg
```

### File Permissions (`chmod`)

```yaml
# Owner: rwx, Group: rwx, Other: r
chmod: '0o774'

# Owner: rwx, Group: rx, Other: none
chmod: '0o750'

# Owner: rwx, Group: rw, Other: r
chmod: '0o764'
```

## Troubleshooting

### Check Container Status

```bash
docker-compose -f docker-compose.prod.yaml ps
```

### View Logs

```bash
# Follow logs in real-time
docker-compose -f docker-compose.prod.yaml logs -f

# View last 100 lines
docker-compose -f docker-compose.prod.yaml logs --tail=100

# View logs for specific service
docker-compose -f docker-compose.prod.yaml logs photosort
```

### Exec Into Container

```bash
docker-compose -f docker-compose.prod.yaml exec photosort sh

# Check if exiftool is available
exiftool -ver

# Check config file
cat /etc/photosort.yml

# List photos directory
ls -la /photos
```

### Permission Issues

If you get permission errors, ensure the container has access to your directories:

```bash
# Check directory permissions on host
ls -la /Volumes/Fotos

# If needed, adjust permissions
chmod -R 775 /Volumes/Fotos
```

### Test Configuration

Run a one-time sync to test without monitor mode:

```bash
# Modify docker-compose.prod.yaml temporarily
# Change: command: ["photosort", "--config", "/etc/photosort.yml", "sync"]

docker-compose -f docker-compose.prod.yaml up
```

## Advanced Configuration

### Resource Limits

Prevent photosort from using too many resources:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'      # Max 1 CPU core
      memory: 512M     # Max 512MB RAM
    reservations:
      cpus: '0.25'     # Reserve 0.25 CPU core
      memory: 128M     # Reserve 128MB RAM
```

### Health Checks

Monitor container health:

```yaml
healthcheck:
  test: ["CMD", "pgrep", "-f", "photosort"]
  interval: 60s       # Check every 60 seconds
  timeout: 10s        # Timeout after 10 seconds
  retries: 3          # Retry 3 times before marking unhealthy
  start_period: 10s   # Wait 10s before starting checks
```

Check health status:
```bash
docker-compose -f docker-compose.prod.yaml ps
# Look for "healthy" in the status column
```

### Log Rotation

Prevent logs from filling up disk:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"   # Max 10MB per log file
    max-file: "3"     # Keep 3 log files (30MB total)
```

## Production Checklist

Before deploying to production:

- [ ] Update volume paths to point to actual photo directories
- [ ] Verify exiftool is installed in the Docker image
- [ ] Test with `sync` command first, then switch to `monitor`
- [ ] Set appropriate `chmod` permissions (e.g., `0o774`)
- [ ] Configure log rotation to prevent disk fill
- [ ] Set resource limits appropriate for your system
- [ ] Configure timezone (`TZ` environment variable)
- [ ] Test duplicate detection is working
- [ ] Verify database and log files are being created
- [ ] Set up monitoring/alerting for container health

## Files Reference

- `docker-compose.yaml` - Default file with external config approach
- `docker-compose.prod.yaml` - Production-ready with embedded config (recommended)
- `docker-compose-examples.yaml` - Multiple example scenarios
- `my_photosort.yaml` - Your original configuration (for reference)
- `photosort-config.yaml` - External config file (if using external approach)

## Additional Resources

- PhotoSort GitHub: https://github.com/mangelajo/photosort
- Docker Compose Documentation: https://docs.docker.com/compose/
- Docker Configs Reference: https://docs.docker.com/compose/compose-file/compose-file-v3/#configs
