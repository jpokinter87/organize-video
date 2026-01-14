# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python video organization tool with two operating modes:
- **Console (CLI)**: Command-line interface for batch processing
- **Web UI**: Django web interface for interactive management

The tool organizes video files (movies and TV series) by:
- Detecting video metadata using TMDB and TVDB APIs
- Extracting technical specs (codec, resolution, language) via MediaInfo and guessit
- Renaming files with French titles and standardized format
- Creating organized symlink structures by genre/alphabetical order
- Managing duplicates via MD5 hash tracking in SQLite databases

## Operating Modes

### Mode 1: Console (CLI)

The primary way to run batch processing via command line.

```bash
# Modern modular mode (default - uses organize/ package)
python -m organize

# Process all files
python -m organize --all

# Process files from last N days
python -m organize -d 7

# Dry-run mode (simulation, no file changes)
python -m organize --dry-run

# Force mode (ignore hash verification)
python -m organize --force

# Custom directories
python -m organize -i /source/path -o /temp/output -s /symlinks/path --storage /storage/path

# Debug mode
python -m organize --debug --tag "specific_file_pattern"

# Legacy mode (delegates to organize.py directly)
python -m organize --legacy
```

### Mode 2: Web UI (Django)

Interactive web interface for visual management.

```bash
cd web
python manage.py migrate          # First time setup
python manage.py init_settings    # Initialize configuration
python manage.py runserver 0.0.0.0:8000
```

Access at `http://localhost:8000`

**Web UI Features:**
- `/` - Dashboard with summary statistics
- `/processing/` - Create and manage processing jobs
- `/processing/confirmations/` - Resolve pending confirmations via modal UI
- `/library/` - Browse organized videos with filters
- `/dashboard/` - Statistics, logs, storage info
- `/settings/` - Configure directories, API keys, processing options

### Dependencies

The project uses `uv` for dependency management. Key dependencies:

**Core:**
- `requests`, `tvdb_api` - API clients for TMDB/TVDB
- `guessit` - Filename parsing for video metadata
- `pymediainfo` - Technical video specs extraction
- `rapidfuzz` - Fuzzy string matching for duplicate detection
- `rich` - Terminal UI (panels, tables, progress bars)
- `loguru` - Logging
- `python-dotenv` - Environment variable management

**Web UI:**
- `django` - Web framework
- `htmx` - Dynamic interactions without full page reload
- `huey` - Background task queue

## Architecture

### Project Structure

```
organize/
├── organize.py              # Legacy monolithic script (~3400 lines)
├── organize/                # Modular package (recommended)
│   ├── __main__.py          # CLI entry point
│   ├── config/              # CLI arguments, settings, execution context
│   ├── models/              # Video dataclass
│   ├── api/                 # TmdbClient, TvdbClient, CacheDB, validation
│   ├── classification/      # text_processing, type_detector, genre_classifier, media_info
│   ├── filesystem/          # discovery, symlinks, file_ops, paths
│   ├── ui/                  # console, display, confirmations, interactive
│   ├── pipeline/            # processor, series_handler, video_list, main_processor
│   └── utils/               # hash, database
└── web/                     # Django web interface
    ├── videomanager/        # Django project settings
    ├── core/                # Models, services, tasks
    ├── processing/          # Job management views
    ├── library/             # Video browsing views
    └── dashboard/           # Statistics and logs views
```

### Key Modules (organize/ package)

| Module | Purpose |
|--------|---------|
| `organize/api/` | API clients (TMDB, TVDB), caching, validation |
| `organize/classification/` | Type detection, genre classification, media info extraction |
| `organize/filesystem/` | File operations, symlinks, path resolution |
| `organize/pipeline/` | Main processing: video_list, main_processor, series_handler |
| `organize/ui/` | Console display, interactive prompts |
| `organize/utils/` | Hash computation, database operations |

### Processing Pipeline

1. Parse arguments → Validate API keys → Test connectivity
2. Setup working directories (temp_dir, work_dir, original_dir)
3. Create video list with hash verification
4. For each video: extract info → query APIs → format filename → create symlinks
5. Add episode titles for series → Final copy and verification

### Directory Structure

```
/media/NAS64/temp/           # DEFAULT_SEARCH_DIR - Source videos
  ├── Séries/
  ├── Films/
  ├── Animation/
  └── Docs/

/media/NAS64/                # DEFAULT_STORAGE_DIR - Final storage
/media/Serveur/test/         # DEFAULT_SYMLINKS_DIR - Symlink structure
/media/Serveur/LAF/liens_à_faire/  # DEFAULT_TEMP_SYMLINKS_DIR
```

### Database Files

- `cache.db` - SQLite cache for TMDB/TVDB API responses
- `symlink_video_Films.db`, `symlink_video_Séries.db` - Hash tracking per category

## Configuration

API keys must be in `.env` file at project root:
```
TMDB_API_KEY=your_key
TVDB_API_KEY=your_key
```

## Important Constants

- `CATEGORIES` - Valid source directories: `{'Séries', 'Films', 'Animation', 'Docs#1', 'Docs'}`
- `EXT_VIDEO` - Supported video extensions
- `GENRES` - TMDB genre ID to French genre name mapping
- `PRIORITY_GENRES` - Genres that take precedence in classification

## Interactive Behavior (CLI Mode)

The script prompts for user confirmation when:
- API returns multiple matches or uncertain results
- Files are not automatically detected
- Similar files (duplicates) are found
- Series cannot be identified

Options typically include: accept, manual entry, view file, skip, retry

## Testing

```bash
# Run all tests (417 tests)
pytest

# With coverage
pytest --cov=organize

# Specific test file
pytest tests/unit/test_video_list.py
```
