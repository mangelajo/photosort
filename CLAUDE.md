# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PhotoSort is a Python CLI tool that simplifies photo inbox management. It watches input directories, catalogs media files by EXIF datetime, moves them to organized storage with date-based directory structures, and handles duplicates through MD5 hashing.

**External dependency**: Requires `exiftool` to be installed on the system (not a Python package).

## Development Commands

### Environment Setup
```bash
# Install uv package manager (if not installed)
make install-uv

# Sync dependencies
make sync
# or directly: uv sync
```

### Testing
```bash
# Run tests across all supported Python versions (3.9-3.12)
make test

# Run tests for a specific Python version
uv run -p 3.9 pytest
uv run -p 3.10 pytest
uv run -p 3.11 pytest
uv run -p 3.12 pytest

# Run pytest directly (uses current environment)
uv run pytest

# Run a specific test file
uv run pytest src/photosort/test/testcases/test_001_walk_for_media.py

# Run a specific test function
uv run pytest src/photosort/test/testcases/test_001_walk_for_media.py::TestWalkForMedia::test_directory_inspection

# Run tests with higher verbosity
uv run pytest -v
```

**Note**: Tests require `exiftool` to be installed on the system. On Ubuntu/Debian: `sudo apt-get install exiftool`, on macOS: `brew install exiftool`.

### Distribution
```bash
make distribute
# Builds package and uploads to PyPI using twine
```

### Running PhotoSort CLI
```bash
# Using uv (for development)
uv run photosort --config my_photosort.yaml sync
uv run photosort --config my_photosort.yaml rebuilddb
uv run photosort --config my_photosort.yaml monitor
uv run photosort --config my_photosort.yaml version

# Enable debug logging
uv run photosort --config my_photosort.yaml --debug sync

# Or install and run directly
pip3 install photosort
photosort --config /path/to/config.yml sync
```

**Config file reference**: See `etc/photosort.yml` or `my_photosort.yaml` for example configurations.

## Architecture

### Core Components

**photosort.py** - Main entry point with `PhotoSort` class orchestrating the workflow:
- Initializes config, logging, and database
- Provides three main operations: `sync`, `rebuilddb`, `monitor`
- Coordinates between walker, media files, and database

**config.py** - YAML configuration parser (`Config` class):
- Reads from `/etc/photosort.yml` by default
- Handles sources, output directories, patterns, file modes, logging
- Supports relative or absolute paths for output-related files

**photodb.py** - CSV-based file database (`PhotoDB` class):
- Stores file hashes (MD5 + EXIF datetime) to detect duplicates
- CSV format: directory, filename, type, hash
- Creates `.bak` backup before writing
- Tracks all processed media to prevent re-processing

**media.py** - Media file handling (`MediaFile` class):
- Detects file type by extension (photo/movie/unknown)
- Extracts EXIF datetime from multiple possible tags (photos and videos)
- Computes MD5 hash combined with EXIF datetime for duplicate detection
- Moves files to date-organized directories with optional file prefixes
- Supports tagged directories (e.g., "2024_01_15_Birthday Party")

**walk.py** - Directory traversal (`WalkForMedia` class):
- Recursively walks directories to find media files
- Implements safety checks: file locking, growth detection, modification time
- Waits 30 seconds after last modification before processing
- Handles filesystem time skew for remote/NAS directories
- Ignores hidden files and specified directories

**exif.py** - EXIF metadata extraction wrapper:
- Uses `pyexiftool` library which wraps the external `exiftool` binary
- Maintains a background batch process for performance (`ExifToolHelper`)
- Must call `exif.start()` before use (done in `main()`)

### Data Flow

**Initial Setup (rebuilddb operation)**:
1. Walk the output directory (excluding source directories)
2. For each existing media file, compute hash and add to database
3. Write database to CSV (creates baseline for duplicate detection)

**Sync Operation**:
1. `PhotoSort._sync_source()` → `WalkForMedia.find_media()` → yields files
2. **For each file**: Create `MediaFile` → extract datetime via `exif` → compute hash
3. **Duplicate check**: `PhotoDB.is_duplicate()` compares hash against database
4. **If duplicate**: Move to `duplicates_dir`
5. **If new**: `MediaFile.move_to_directory_with_date()` → moves to date-organized path
6. **Update DB**: `PhotoDB.add_to_db()` → `PhotoDB.write()` persists to CSV

**Monitor Operation**: Runs sync in infinite loop with 10-second sleep between iterations

### Configuration Structure

YAML config with two main sections:
- `sources`: Dictionary of input directories to watch
- `output`: Target directory, patterns, duplicates handling, permissions, logging

Pattern variables: `%(year)d`, `%(month)02d`, `%(day)02d`, `%(hour)02d`, `%(minute)02d`, `%(second)02d`

### Test Organization

Tests located in `src/photosort/test/testcases/`:
- `test_001_walk_for_media.py` - Directory traversal tests
- `test_002_exif_media.py` - EXIF extraction and media handling tests
- `test_003_noexif_media.py` - Files without EXIF data handling

**Test infrastructure**:
- Base test class: `photosort.test.TestCase` (extends `unittest.TestCase`)
- Test data: Located in `src/photosort/test/data/` with `media1/` and `media2/` subdirectories
- Helper method: `self.get_data_path('media1')` returns path to test data
- Temp directories: Auto-created via `self._temp_dir` in `setUp()`
- Uses `mock` library to patch file readiness checks in CI environments

## Project Management

This project uses **bd** (beads) for issue tracking. Key commands:
- `bd ready` - Find available work
- `bd show <id>` - View issue details
- `bd update <id> --status in_progress` - Claim work
- `bd close <id>` - Complete work
- `bd sync` - Sync with git

**Session completion requirements** (from AGENTS.md): When ending work, you must:
1. File issues for remaining work
2. Run tests if code changed
3. Update issue status
4. Push to remote (`git pull --rebase && bd sync && git push`)
5. Verify `git status` shows "up to date with origin"

## Important Implementation Details

### Duplicate Detection Strategy
Combines MD5 hash with EXIF datetime string: `hash = md5_hash + " - " + str(exif_datetime)`

This prevents MD5 collisions and provides better uniqueness. If a collision is detected, it's logged as `CRITICAL`.

### File Safety Mechanisms
The `WalkForMedia` class implements multiple safety checks before processing:
1. **Lock check**: Uses `fcntl.flock()` to verify file isn't being written
2. **Modification time**: Waits 30 seconds after last modification
3. **Empty file check**: Skips zero-byte files
4. **Filesystem time skew**: Calculates offset for remote/NAS directories by creating `.timesync` test file

### EXIF Datetime Extraction Priority
Tries tags in order until one is found (media.py:81-91):
1. `EXIF:DateTimeOriginal`
2. `EXIF:DateTimeDigitized`
3. `EXIF:CreateDate`
4. `XMP-exif:DateTimeDigitized`
5. `QuickTime:ContentCreateDate` (for videos)
6. `QuickTime:CreationDate`
7. `QuickTime:CreateDate`
8. `MediaCreateDate`
9. `TrackCreateDate`
10. `CreateDate`

Files with datetime `'0000:00:00 00:00:00'` are treated as having no datetime.

### Tagged Directory Support
When organizing files, `locate_output_directory()` (media.py:230) checks if a directory matching the date pattern exists with a user-added suffix (e.g., `2024_01_15_Birthday Party` matches pattern `2024_01_15`). This allows users to tag directories without breaking the organization.

### Database Format
CSV with columns: `directory, filename, type, md5`
- Directory paths are stored relative to output_dir (strips `output_dir + '/'` prefix)
- Creates `.bak` backup before each write
- Loads entire database into memory as `_hashes` dict

### Supported Media Extensions
- **Photos**: `heic`, `jpeg`, `jpg`, `cr2`, `raw`, `png`, `arw`, `thm`, `orf`
- **Movies**: `m4v`, `mpeg`, `mpg`, `mov`, `mp4`, `avi`

### Logging Behavior
- Defaults to stderr if no `log_file` specified in config
- Uses Python's standard logging module with INFO level (DEBUG with `--debug` flag)
- Critical operations log to `CRITICAL` level
