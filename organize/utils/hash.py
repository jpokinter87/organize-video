"""Utilitaires de hachage pour la déduplication de fichiers."""

import hashlib
from pathlib import Path
from typing import Optional

from loguru import logger

from organize.config import (
    SMALL_FILE_THRESHOLD,
    PARTIAL_HASH_CHUNK_SIZE,
    HASH_FILE_POSITION_DIVISOR,
)


def checksum_md5(filename: Path) -> Optional[str]:
    """
    Calcule le hash MD5 d'un fichier.

    Pour les petits fichiers (< 650 Ko), le fichier entier est haché.
    Pour les fichiers plus gros, seul un chunk de 512 Ko à partir de 1/8
    du fichier est haché. Cela offre un bon équilibre entre précision
    et performance pour la déduplication.

    Arguments :
        filename: Chemin vers le fichier à hacher.

    Retourne :
        Chaîne hexadécimale MD5, ou None si le fichier n'existe pas
        ou si une erreur survient.
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
                # Pour les gros fichiers, hacher depuis 1/N du fichier
                f.seek(size // HASH_FILE_POSITION_DIVISOR)
                md5.update(f.read(PARTIAL_HASH_CHUNK_SIZE))
        return md5.hexdigest()
    except (OSError, IOError) as e:
        logger.debug(f'Erreur I/O lors du calcul MD5 de {filename}: {e}')
        return None
