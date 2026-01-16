# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains **two separate applications**:

1. **CLI Application** (`organize/` package) - **FUNCTIONAL**
   - Command-line tool for batch video organization
   - Located in: `organize/` directory
   - Entry point: `organize-video` command or `python -m organize`

2. **Web Application** (`web/` directory) - **IN DEVELOPMENT**
   - Django web interface (not yet functional)
   - Located in: `web/` directory
   - See `web/README.md` for details

**These applications share no code and are completely independent.**

---

## CLI Application (organize/)

### Purpose

Organizes video files (movies and TV series) by:
- Detecting video metadata using TMDB and TVDB APIs
- Extracting technical specs (codec, resolution, language) via MediaInfo and guessit
- Renaming files with French titles and standardized format
- Creating organized symlink structures by genre/alphabetical order
- Managing duplicates via MD5 hash tracking in SQLite databases

### Usage

```bash
# Modern modular mode (default - uses organize/ package)
organize-video

# Process all files
organize-video --all

# Process files from last N days
organize-video -d 7

# Dry-run mode (simulation, no file changes)
organize-video --dry-run

# Force mode (ignore hash verification)
organize-video --force

# Custom directories
organize-video -i /source/path -o /temp/output -s /symlinks/path --storage /storage/path

# Debug mode
organize-video --debug --tag "specific_file_pattern"

# Legacy mode (delegates to organize.py directly)
organize-video --legacy

# Alternative (run package directly without installation)
python -m organize
```

### Dependencies

The project uses `uv` for dependency management. Key dependencies:

- `requests`, `tvdb_api` - API clients for TMDB/TVDB
- `guessit` - Filename parsing for video metadata
- `pymediainfo` - Technical video specs extraction
- `rapidfuzz` - Fuzzy string matching for duplicate detection
- `rich` - Terminal UI (panels, tables, progress bars)
- `loguru` - Logging
- `python-dotenv` - Environment variable management

### Architecture

```
organize/                    # CLI Package
├── __main__.py              # CLI entry point
├── config/                  # CLI arguments, settings, execution context
├── models/                  # Video dataclass
├── api/                     # TmdbClient, TvdbClient, CacheDB, validation
├── classification/          # text_processing, type_detector, genre_classifier, media_info
├── filesystem/              # discovery, symlinks, file_ops, paths
├── ui/                      # console, display, confirmations, interactive
├── pipeline/                # processor, series_handler, video_list, main_processor
└── utils/                   # hash, database

organize.py                  # Legacy monolithic script (~3400 lines) - DEPRECATED
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `organize/api/` | API clients (TMDB, TVDB), caching, validation |
| `organize/classification/` | Type detection, genre classification, media info extraction |
| `organize/filesystem/` | File operations, symlinks, path resolution |
| `organize/pipeline/` | Main processing: video_list, main_processor, series_handler |
| `organize/ui/` | Console display, interactive prompts |
| `organize/utils/` | Hash computation, database operations |

### Processing Pipeline

1. Parse arguments -> Validate API keys -> Test connectivity
2. Setup working directories (temp_dir, work_dir, original_dir)
3. Create video list with hash verification
4. For each video: extract info -> query APIs -> format filename -> create symlinks
5. Add episode titles for series -> Final copy and verification

### Directory Structure

```
/media/NAS64/temp/           # DEFAULT_SEARCH_DIR - Source videos
  ├── Series/
  ├── Films/
  ├── Animation/
  └── Docs/

/media/NAS64/                # DEFAULT_STORAGE_DIR - Final storage
/media/Serveur/test/         # DEFAULT_SYMLINKS_DIR - Symlink structure
/media/Serveur/LAF/liens_a_faire/  # DEFAULT_TEMP_SYMLINKS_DIR
```

### Database Files

- `cache.db` - SQLite cache for TMDB/TVDB API responses
- `symlink_video_Films.db`, `symlink_video_Series.db` - Hash tracking per category

### Configuration

API keys must be in `.env` file at project root:
```
TMDB_API_KEY=your_key
TVDB_API_KEY=your_key
```

### Important Constants

- `CATEGORIES` - Valid source directories: `{'Series', 'Films', 'Animation', 'Docs#1', 'Docs'}`
- `EXT_VIDEO` - Supported video extensions
- `GENRES` - TMDB genre ID to French genre name mapping
- `PRIORITY_GENRES` - Genres that take precedence in classification

### Interactive Behavior

The script prompts for user confirmation when:
- API returns multiple matches or uncertain results
- Files are not automatically detected
- Similar files (duplicates) are found
- Series cannot be identified

Options typically include: accept, manual entry, view file, skip, retry

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=organize

# Specific test file
pytest tests/unit/test_video_list.py
```

---

## Web Application (web/) - IN DEVELOPMENT

The web interface is a **separate project** located in the `web/` directory.

**Status:** Not yet functional. Development in progress.

See `web/README.md` for documentation.
