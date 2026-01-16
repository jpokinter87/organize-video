"""Hash utilities for file deduplication."""

import hashlib
from pathlib import Path
from typing import Optional

from loguru import logger


# Size threshold for full file hashing (650 KB)
SMALL_FILE_THRESHOLD = 650000

# Chunk size for partial hashing (512 KB)
PARTIAL_HASH_CHUNK_SIZE = 524288


def checksum_md5(filename: Path) -> Optional[str]:
    """
    Calculate MD5 hash of a file.

    For small files (< 650KB), the entire file is hashed.
    For larger files, only a 512KB chunk from 1/8 into the file is hashed.
    This provides a good balance between accuracy and performance for
    deduplication purposes.

    Args:
        filename: Path to the file to hash.

    Returns:
        MD5 hex digest string, or None if file doesn't exist
        or an error occurs.
    """
    if not filename.exists():
        return None

    # usedforsecurity=False for FIPS compliance (MD5 used for dedup, not crypto)
    md5 = hashlib.md5(usedforsecurity=False)
    try:
        with open(filename, 'rb') as f:
            size = filename.stat().st_size
            if size < SMALL_FILE_THRESHOLD:
                md5.update(f.read())
            else:
                # For large files, hash from 1/8 into the file
                f.seek(size // 8)
                md5.update(f.read(PARTIAL_HASH_CHUNK_SIZE))
        return md5.hexdigest()
    except (OSError, IOError) as e:
        logger.debug(f'Erreur I/O lors du calcul MD5 de {filename}: {e}')
        return None
