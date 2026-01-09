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

# Sync dependencies (core + dev dependencies)
make sync
# or directly: uv sync

# Sync dependencies including YOLO (for development)
make sync-yolo
# This installs core, dev, and YOLO dependencies (ultralytics, torch, opencv-python)
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

### Coverage Reporting
```bash
# Run tests with coverage report
uv run pytest --cov

# Run tests with detailed coverage showing missing lines
uv run pytest --cov --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov --cov-report=html
# Open htmlcov/index.html in browser to view

# Generate XML coverage report (for CI/CD)
uv run pytest --cov --cov-report=xml
```

**Coverage configuration:**
- Source code coverage tracked in `src/photosort/`
- Test files excluded from coverage
- Branch coverage enabled
- HTML reports generated in `htmlcov/` directory
- Current coverage: ~77% (as of test suite expansion)

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

# Add YOLO object detection tags to existing photos
uv run photosort --config my_photosort.yaml add-yolo-tags

# YOLO tagging with options
uv run photosort --config my_photosort.yaml add-yolo-tags --dry-run      # Preview without writing
uv run photosort --config my_photosort.yaml add-yolo-tags --interactive  # Show visualization

# Enable debug logging
uv run photosort --config my_photosort.yaml --debug sync

# Or install and run directly
pip3 install photosort
photosort --config /path/to/config.yml sync

# Install with YOLO support
pip3 install photosort[yolo]
photosort --config /path/to/config.yml add-yolo-tags
```

**Config file reference**: See `etc/photosort.yml` or `my_photosort.yaml` for example configurations.

## Architecture

### Core Components

**photosort.py** - Main entry point with `PhotoSort` class orchestrating the workflow:
- Initializes config, logging, and database
- Provides main operations: `sync`, `rebuilddb`, `monitor`, `add-yolo-tags`
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

**yolo_tagger.py** - YOLO11 object detection and tagging (optional):
- Detects objects in photos using YOLO11 models
- Stores ONLY object class names (e.g., 'cat', 'dog', 'person') in EXIF Keywords
- Does NOT store bounding boxes or coordinate data
- Supports interactive visualization with cv2.imshow
- Device auto-detection (MPS/CUDA/CPU) handled by ultralytics
- Requires optional dependencies: `pip install photosort[yolo]`

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

**Add YOLO Tags Operation**:
1. `PhotoSort.add_yolo_tags()` → `WalkForMedia.find_media()` → yields photo files
2. **For each photo**: Load image → run YOLO inference → extract object class names
3. **Write tags**: Store class names (e.g., 'cat', 'dog') as EXIF Keywords using exiftool
4. **Optional visualization**: Display annotated image with cv2.imshow if `--interactive` flag set
5. **Report summary**: Total processed, tagged, and any errors

### Configuration Structure

YAML config with two main sections:
- `sources`: Dictionary of input directories to watch
- `output`: Target directory, patterns, duplicates handling, permissions, logging

**Source section options (per source):**
- `dir`: Input directory path to watch for media files
- `fallback_to_file_date`: Use file modification time when EXIF datetime is unavailable (default: `false`, optional)

**Output section options:**
- `dir`: Output directory for organized photos
- `dir_pattern`: Directory organization pattern (e.g., `%(year)d/%(year)04d_%(month)02d_%(day)02d`)
- `file_prefix`: Optional filename prefix (e.g., `%(year)d%(month)02d%(day)02d_`)
- `duplicates_dir`: Directory for duplicate files
- `chmod`: File permissions in octal format (e.g., `0o774`)
- `chmod_dirs`: Directory permissions in octal format (optional, defaults to `chmod | 0o111`)
- `log_file`: Path to log file (optional)
- `log_to_stderr`: Log to console/stderr in addition to file (default: `true`, optional)
- `db_file`: Path to CSV database file

Pattern variables: `%(year)d`, `%(month)02d`, `%(day)02d`, `%(hour)02d`, `%(minute)02d`, `%(second)02d`

**Permission handling:**
- Files use `chmod` permissions (e.g., `0o774` = rwxrwxr--)
- Directories use `chmod_dirs` if specified, otherwise `chmod | 0o111` (adds execute for all)
- Execute permission (0o111) is required for directories to be traversable
- Example: `chmod: 0o664` files → `chmod_dirs: 0o775` directories (auto-default)

**Logging behavior:**
- If `log_to_stderr` is `true` (default): logs to both console and file
- If `log_to_stderr` is `false`: logs only to file (or console if no log file)
- In `--debug` mode: always logs to console regardless of config
- Useful for Docker deployments where you want logs in `docker logs` output

**YOLO section options (optional):**
- `model`: YOLO model to use (default: `yolo11x.pt`) - auto-downloads if not found
- `confidence`: Detection confidence threshold 0.0-1.0 (default: `0.25`)
- `imgsz`: Image size for inference (default: `640`)
- `interactive`: Show cv2 visualization window (default: `false`)

Example YOLO configuration:
```yaml
yolo:
  model: 'yolo11x.pt'    # or yolo11n.pt, yolo11s.pt, yolo11m.pt, yolo11l.pt
  confidence: 0.25       # higher = fewer but more confident detections
  imgsz: 640            # larger = more accurate but slower
  interactive: false     # true = show detection visualization
```

**YOLO model size tradeoffs:**
- `yolo11n.pt` (nano): Fastest, smallest, least accurate (~6MB)
- `yolo11s.pt` (small): Good balance (~19MB)
- `yolo11m.pt` (medium): Better accuracy (~40MB)
- `yolo11l.pt` (large): High accuracy (~51MB)
- `yolo11x.pt` (extra large): Best accuracy, slowest (~115MB) - **default**

### Test Organization

Tests located in `src/photosort/test/testcases/`:
- `test_001_walk_for_media.py` - Directory traversal and file discovery (19 tests)
- `test_002_exif_media.py` - EXIF extraction and media handling (10 tests)
- `test_003_noexif_media.py` - Files without EXIF data handling (2 tests)
- `test_004_config.py` - YAML configuration parsing (20 tests)
- `test_005_photodb.py` - CSV database operations (20 tests)
- `test_006_photosort_integration.py` - End-to-end workflow tests (15 tests)
- `test_007_yolo_tagger.py` - YOLO object detection tests (requires YOLO dependencies)
- `test_008_yolo_integration.py` - YOLO tagging integration tests (requires YOLO dependencies)
- `test_005_photodb.py` - CSV database operations (20 tests)
- `test_006_photosort_integration.py` - End-to-end workflow tests (15 tests)

**Test infrastructure**:
- Base test class: `photosort.test.TestCase` (extends `unittest.TestCase`)
- Test data: Located in `src/photosort/test/data/` with `media1/` and `media2/` subdirectories
- Helper method: `self.get_data_path('media1')` returns path to test data
- Temp directories: Auto-created via `self._temp_dir` in `setUp()`
- Uses `mock` library to patch time-sensitive checks in CI environments

### Testing Philosophy and Best Practices

**Behavior Testing vs Implementation Testing:**
- Focus on testing behavior and outcomes, not implementation details
- Test what the code does, not how it does it
- Example: Test that a file is moved to the correct destination, not the internal steps of the move operation

**Mocking Strategy:**
- Mock external dependencies: file system time checks, remote services, system clocks
- Don't mock internal application logic
- Use `mock.patch()` for time-sensitive operations (`_file_is_ready` 30-second check)
- Integration tests use real file operations with mocked time checks for speed

**Test Data Management:**
- Use real media files in `src/photosort/test/data/` for authentic EXIF testing
- Create temporary files in `self._temp_dir` for isolation
- Set file modification times explicitly to bypass time-based safety checks
- Clean up is automatic via `unittest.TestCase` cleanup handlers

**Coverage Interpretation:**
- Target: >75% coverage for core modules (config, photodb, media, walk)
- Lower coverage acceptable for: CLI entry points, error handling paths
- Branch coverage enabled to catch untested conditional paths
- Missing lines often indicate edge cases or error paths worth testing

**Test Naming:**
- Use descriptive names: `test_duplicate_detection_and_movement` not `test_dup`
- Include docstrings explaining what behavior is being tested
- Group related tests in the same file

**Avoiding Common Pitfalls:**
- Don't test library internals (e.g., testing that `yaml.safe_load` works)
- Don't over-mock: only mock what's necessary for test isolation
- Avoid testing implementation details that may change
- Don't create brittle tests tied to exact log messages or internal state

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

### Datetime Fallback Strategy
When `fallback_to_file_date: true` is set for a source:
- If EXIF datetime is not available or is `'0000:00:00 00:00:00'`, use file modification time
- Uses `min(mtime, ctime)` to get earliest timestamp (handles platform differences)
- Logs when fallback is used: `"using file modification time for <path>: <datetime>"`
- If `fallback_to_file_date: false` (default), files without EXIF are skipped with error log

This is useful for sources containing:
- Screenshots or screen recordings without EXIF data
- Edited images that lost their metadata
- Files from apps that don't embed EXIF timestamps

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

## YOLO Object Detection Feature

PhotoSort can automatically tag photos with detected objects using YOLO11 (You Only Look Once) object detection models.

### Installation

YOLO dependencies are optional. Install with:
```bash
pip install photosort[yolo]
# or
pip install ultralytics torch opencv-python
```

For development:
```bash
uv sync  # installs all dependencies including YOLO
```

### Usage

Tag all photos in your output directory:
```bash
photosort --config config.yml add-yolo-tags
```

Preview tags without writing to EXIF:
```bash
photosort --config config.yml add-yolo-tags --dry-run
```

Show visualization window for each detection (requires display):
```bash
photosort --config config.yml add-yolo-tags --interactive
```

### What Gets Stored

**IMPORTANT**: PhotoSort stores ONLY object class names (e.g., 'cat', 'dog', 'person', 'car') in the EXIF Keywords field. It does NOT store:
- Bounding box coordinates
- Object locations or positions
- Confidence scores
- Any other detection metadata

This keeps EXIF data clean and focused on searchability. Tags are written to the `IPTC:Keywords` field using exiftool.

### Configuration

Add a `yolo` section to your config file:
```yaml
yolo:
  model: 'yolo11x.pt'    # Model to use (see options below)
  confidence: 0.25       # Detection threshold (0.0-1.0)
  imgsz: 640            # Inference image size
  interactive: false     # Show cv2 visualization window
```

All fields are optional with sensible defaults.

### Model Selection

Choose based on accuracy vs speed tradeoffs:

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| yolo11n.pt | 6MB | Fastest | Good | Quick tagging of large collections |
| yolo11s.pt | 19MB | Fast | Better | Balanced performance |
| yolo11m.pt | 40MB | Medium | High | More accurate tagging |
| yolo11l.pt | 51MB | Slow | Very High | When accuracy matters |
| yolo11x.pt | 115MB | Slowest | Best | Maximum accuracy (default) |

Models auto-download on first use.

### Device Support

YOLO automatically detects and uses available hardware:
- **Apple Silicon Macs**: Uses MPS (Metal Performance Shaders) for GPU acceleration
- **NVIDIA GPUs**: Uses CUDA if available
- **CPU**: Fallback for all systems

No manual device configuration needed.

### Detectable Objects

YOLO11 is trained on the COCO dataset and can detect 80 object classes including:
- People and animals: person, cat, dog, horse, bird, etc.
- Vehicles: car, truck, bus, bicycle, motorcycle, boat, airplane
- Indoor: chair, table, couch, bed, tv, laptop, keyboard, cell phone
- Outdoor: traffic light, fire hydrant, stop sign, bench
- Sports: sports ball, baseball bat, tennis racket, skateboard
- Food: pizza, donut, cake, apple, banana, sandwich
- And many more...

### Workflow Example

1. Organize your photos with sync:
   ```bash
   photosort --config config.yml sync
   ```

2. Add AI tags to organized photos:
   ```bash
   photosort --config config.yml add-yolo-tags
   ```

3. Search photos by tags using any photo management software that reads EXIF keywords (Lightroom, Apple Photos, etc.)

### Performance Tips

- Use smaller models (yolo11n.pt or yolo11s.pt) for faster processing of large collections
- Lower confidence threshold (0.1-0.2) to detect more objects, higher (0.4-0.5) for only confident detections
- Run on machines with GPU (Apple Silicon MPS or NVIDIA CUDA) for significant speedup
- Process in batches - YOLO is more efficient with multiple images

### Troubleshooting

**"YOLO dependencies not installed"**
- Run: `pip install photosort[yolo]`

**"Could not display window (headless?)"**
- You're using `--interactive` on a system without display. Remove the flag or run on a system with GUI.

**Model download fails**
- Check internet connection
- Models are downloaded from Ultralytics servers on first use
- Downloaded models are cached in `~/.cache/torch/hub/`

**Slow performance**
- Try a smaller model (yolo11n.pt or yolo11s.pt)
- Reduce imgsz to 320 or 416 for faster inference
- Ensure GPU acceleration is working (check logs for device info)

**No tags written**
- Check that exiftool is installed and accessible
- Verify file permissions allow writing EXIF data
- Use `--dry-run` to see what would be tagged
- Check logs with `--debug` flag for errors
