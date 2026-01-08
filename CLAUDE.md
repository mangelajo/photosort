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
```

### Distribution
```bash
make distribute
# Builds package and uploads to PyPI using twine
```

### Running PhotoSort CLI
```bash
# Using uv
uv run photosort --config my_photosort.yaml sync
uv run photosort --config my_photosort.yaml rebuilddb
uv run photosort --config my_photosort.yaml monitor

# Or install and run directly
pip3 install photosort
photosort --config /path/to/config.yml sync
```

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

1. **Sync/Monitor**: `PhotoSort._sync_source()` → `WalkForMedia.find_media()` → yields files
2. **For each file**: Create `MediaFile` → extract datetime via `exif` → compute hash
3. **Duplicate check**: `PhotoDB.is_duplicate()` compares hash against database
4. **If duplicate**: Move to `duplicates_dir`
5. **If new**: `MediaFile.move_to_directory_with_date()` → moves to date-organized path
6. **Update DB**: `PhotoDB.add_to_db()` → `PhotoDB.write()` persists to CSV

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

Test data files are included in the package via `pyproject.toml` build system.

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

## Important Notes

- The database is CSV-based for manual editing capability (future: migrate to SQLite)
- Files without EXIF datetime are skipped (logged as errors)
- Duplicate detection uses MD5 + EXIF datetime to prevent hash collisions
- File permissions are set via `chmod` config parameter (octal format: `0o774`)
- Monitor mode syncs every 10 seconds
- Tagged directory support: directories matching date pattern with suffix are reused
