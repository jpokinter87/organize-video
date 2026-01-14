# Refactoring Plan: organize.py Full Modularization

## Current State Analysis

### organize.py (~3400 lines)
- Monolithic file containing all application logic
- 50+ functions covering:
  - API clients and caching
  - File metadata extraction
  - Interactive user prompts
  - File operations (symlinks, moves, renames)
  - Video processing pipeline

### organize/ package (partial modularization)
- `config/`: CLI arguments, settings, execution context
- `models/`: Video dataclass
- `api/`: TmdbClient, CacheDB, TvdbClient
- `classification/`: text_processing, type_detector, genre_classifier
- `filesystem/`: discovery, symlinks, file_ops, paths
- `ui/`: console, display, confirmations
- `pipeline/`: processor, series_handler
- `utils/`: hash

### GAP Functions in __main__.py
Functions that still delegate to organize.py:
1. `validate_api_keys` - API validation
2. `test_api_connectivity` - API connectivity test
3. `media_info` - MediaInfo extraction
4. `set_fr_title_and_category` - Main video processing
5. `aplatir_repertoire_series` - Series directory flattening
6. `create_video_list` - Video list creation with filtering
7. `process_video` - Single video duplicate handling
8. `rename_video` - Video file renaming
9. `find_symlink_and_sub_dir` - Symlink path resolution
10. `find_directory_for_video` - Alphabetical directory finder
11. `add_episodes_titles` - TVDB episode title lookup
12. `move_file_new_nas` - Final file transfer
13. `cleanup_directories` - Directory cleanup
14. `format_undetected_filename` - Undetected file naming
15. `cleanup_work_directory` - Work directory cleanup

---

## Migration Plan

### Phase 1: API and Validation (organize/api/)
**Files to modify:** `organize/api/__init__.py`, create `organize/api/validation.py`

Functions to migrate:
- `validate_api_keys()` → `organize/api/validation.py`
- `test_api_connectivity()` → `organize/api/validation.py`

### Phase 2: Media Processing (organize/classification/)
**Files to modify:** `organize/classification/__init__.py`, create `organize/classification/media_info.py`

Functions to migrate:
- `media_info()` → `organize/classification/media_info.py`
- `format_undetected_filename()` → already in models/video.py (verify completeness)

### Phase 3: Interactive UI (organize/ui/)
**Files to modify:** `organize/ui/__init__.py`, create `organize/ui/interactive.py`

Functions to migrate:
- `query_movie_database()` → `organize/ui/interactive.py`
- `user_confirms_match()` → `organize/ui/interactive.py`
- `wait_for_user_after_viewing()` → `organize/ui/interactive.py`
- `choose_genre_manually()` → `organize/ui/interactive.py`
- `launch_video_player()` → `organize/ui/interactive.py`
- `extract_title_from_filename()` → `organize/classification/text_processing.py`
- `handle_unsupported_genres()` → `organize/classification/genre_classifier.py`

### Phase 4: File Operations (organize/filesystem/)
**Files to modify:** `organize/filesystem/__init__.py`, `organize/filesystem/file_ops.py`

Functions to migrate:
- `aplatir_repertoire_series()` → `organize/filesystem/file_ops.py`
- `rename_video()` → `organize/filesystem/file_ops.py`
- `move_file_new_nas()` → `organize/filesystem/file_ops.py`
- `cleanup_directories()` → `organize/filesystem/file_ops.py`
- `cleanup_work_directory()` → `organize/filesystem/file_ops.py`
- `cleanup_recursive_symlinks()` → `organize/filesystem/symlinks.py`

### Phase 5: Video Processing Pipeline (organize/pipeline/)
**Files to modify:** `organize/pipeline/__init__.py`, `organize/pipeline/processor.py`

Functions to migrate:
- `create_video_list()` → `organize/pipeline/processor.py`
- `process_single_video()` → `organize/pipeline/processor.py`
- `process_video()` → `organize/pipeline/processor.py`
- `create_paths()` → `organize/pipeline/processor.py`

### Phase 6: Path Resolution (organize/filesystem/)
**Files to modify:** `organize/filesystem/paths.py`

Functions to migrate:
- `find_directory_for_video()` → `organize/filesystem/paths.py`
- `find_symlink_and_sub_dir()` → `organize/filesystem/paths.py`
- `find_similar_file()` → `organize/filesystem/paths.py`
- `find_similar_file_in_folder()` → `organize/filesystem/paths.py`
- `handle_similar_file()` → `organize/filesystem/file_ops.py`

### Phase 7: Series Handler (organize/pipeline/)
**Files to modify:** `organize/pipeline/series_handler.py`

Functions to migrate:
- `add_episodes_titles()` → `organize/pipeline/series_handler.py`

### Phase 8: Main Processing Function (organize/pipeline/)
**Files to modify:** Create `organize/pipeline/main_processor.py`

Functions to migrate:
- `set_fr_title_and_category()` → `organize/pipeline/main_processor.py`
- `classify_movie()` → already in classification/genre_classifier.py
- `classify_animation()` → already in classification/genre_classifier.py

### Phase 9: Final Integration
- Update `organize/__main__.py` to use only modular imports
- Remove all GAP function wrappers
- Keep `organize.py` as legacy fallback (optional --legacy flag)

---

## Implementation Order

1. **Phase 1** - API validation (low dependency)
2. **Phase 2** - Media info extraction (independent)
3. **Phase 6** - Path resolution (needed by others)
4. **Phase 4** - File operations (uses path resolution)
5. **Phase 3** - Interactive UI (complex, needs testing)
6. **Phase 5** - Video processing pipeline
7. **Phase 7** - Series handler
8. **Phase 8** - Main processing function
9. **Phase 9** - Final integration

---

## Testing Strategy

For each phase:
1. Write tests BEFORE migrating (if not existing)
2. Migrate function with identical signature
3. Run existing tests to verify behavior
4. Update __main__.py to use new module
5. Run integration test
6. Commit if all tests pass

---

## Success Criteria

- [ ] All 324+ existing tests pass
- [ ] organize.py can be removed or kept as legacy-only
- [ ] __main__.py has no GAP function imports
- [ ] Each module is independently testable
- [ ] No circular imports
