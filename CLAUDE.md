# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool for organizing video files (movies and TV series) by:
- Detecting video metadata using TMDB and TVDB APIs
- Extracting technical specs (codec, resolution, language) via MediaInfo and guessit
- Renaming files with French titles and standardized format
- Creating organized symlink structures by genre/alphabetical order
- Managing duplicates via MD5 hash tracking in SQLite databases

## Commands

### Running the Application
```bash
# Process recent files (default behavior)
python organize.py

# Process all files
python organize.py --all

# Process files from last N days
python organize.py -d 7

# Dry-run mode (simulation, no file changes)
python organize.py --dry-run

# Force mode (ignore hash verification)
python organize.py --force

# Custom directories
python organize.py -i /source/path -o /temp/output -s /symlinks/path --storage /storage/path

# Debug mode
python organize.py --debug --tag "specific_file_pattern"
```

### Dependencies
The project uses `uv` for dependency management. Key dependencies include:
- `requests`, `tvdb_api` - API clients for TMDB/TVDB
- `guessit` - Filename parsing for video metadata
- `pymediainfo` - Technical video specs extraction
- `rapidfuzz` - Fuzzy string matching for duplicate detection
- `rich` - Terminal UI (panels, tables, progress bars)
- `loguru` - Logging
- `python-dotenv` - Environment variable management

## Architecture

### Main Components

**`organize.py`** - Single-file application (~3400 lines) containing:

1. **Data Classes**
   - `Video` - Core dataclass holding all video metadata and paths
   - `SubfolderCache`, `CacheDB` - Caching mechanisms for performance

2. **API Clients**
   - `Tmdb` class - TMDB API wrapper for movie/series lookup
   - TVDB integration via `tvdb_api` for episode titles

3. **Processing Pipeline** (in `main()`)
   - Parse arguments → Validate API keys → Test connectivity
   - Setup working directories (temp_dir, work_dir, original_dir)
   - Create video list with hash verification
   - For each video: extract info → query APIs → format filename → create symlinks
   - Add episode titles for series → Final copy and verification

4. **Key Functions**
   - `extract_file_infos()` - Uses guessit to parse filename metadata
   - `media_info()` - Extracts codec/resolution/language via MediaInfo
   - `query_movie_database()` - Interactive API lookup with user confirmation
   - `set_fr_title_and_category()` - Main processing for title/genre assignment
   - `find_directory_for_video()` - Alphabetical subfolder placement logic
   - `create_symlink()`, `move_file_new_nas()` - File operations

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

## Interactive Behavior

The script prompts for user confirmation when:
- API returns multiple matches or uncertain results
- Files are not automatically detected
- Similar files (duplicates) are found
- Series cannot be identified

Options typically include: accept, manual entry, view file, skip, retry