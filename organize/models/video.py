"""Video data model for the organize package."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from organize.config.settings import FILMANIM, FILMSERIE, NOT_DOC
from organize.classification.text_processing import normalize, remove_article


@dataclass
class Video:
    """
    Data class representing a video file with its metadata.

    This class holds all information about a video file including:
    - File paths (original, destination, symlinks)
    - Metadata (title, year, genre, season/episode)
    - Technical specs (codec, resolution, language)
    """

    # Path information
    complete_path_original: Path = field(default_factory=Path)
    complete_path_temp_links: Path = field(default_factory=Path)
    complete_dir_symlinks: Path = field(default_factory=Path)
    destination_file: Path = field(default_factory=Path)
    extended_sub: Path = field(default_factory=Path)
    sub_directory: Path = field(default_factory=Path)

    # Title information
    title: str = ''
    title_fr: str = ''
    name_without_article: str = ''

    # Date and episode information
    date_film: int = 0
    sequence: str = ''
    season: int = 0
    episode: int = 0

    # Classification
    genre: str = ''
    list_genres: List[str] = field(default_factory=list)
    type_file: str = ''

    # Technical specs
    spec: str = ''
    formatted_filename: str = ''
    hash: str = ''

    def format_name(self, title: str) -> str:
        """
        Format the filename for this video.

        Args:
            title: The title to use in the filename.

        Returns:
            Formatted filename with title, year, specs, and extension.
        """
        # Gérer les fichiers non détectés
        if not title or title.strip() == '' or not self.title_fr:
            return self._format_undetected_filename()

        if self.is_serie():
            result = f'{title} ({self.date_film}) {self.sequence} {self.spec}'
        else:
            result = f'{title} ({self.date_film}) {self.spec}'

        result = normalize(result)
        file_ext = self.complete_path_original.suffix
        if file_ext == '.ts':
            file_ext = '.mp4'
        result += file_ext
        return result

    def _format_undetected_filename(self) -> str:
        """
        Format filename for videos that couldn't be identified.

        This is a simplified version - the full implementation is in
        the classification module.
        """
        import re

        original_name = self.complete_path_original.stem

        # Nettoyage de base
        cleaned_title = original_name
        tech_patterns = [
            r'\b\d{4}\b',
            r'\b(MULTI|MULTi|VF|VOSTFR|FR|VO|FRENCH)\b',
            r'\b(x264|x265|HEVC|H264|H265|AV1)\b',
            r'\b(1080p|720p|480p|2160p)\b',
            r'\b(WEB|BluRay|BDRip|DVDRip|WEBRip)\b',
        ]

        for pattern in tech_patterns:
            cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE)

        cleaned_title = re.sub(r'[._-]+', ' ', cleaned_title)
        cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
        cleaned_title = cleaned_title.title() if cleaned_title else "Fichier non identifié"

        # Extraire l'année
        year_match = re.search(r'\b(19|20)\d{2}\b', original_name)
        year = year_match.group() if year_match else "Année inconnue"

        # Construire les specs
        specs = self.spec if self.spec else "Specs inconnues"
        formatted_name = f"{cleaned_title} ({year}) {specs}"
        formatted_name = normalize(formatted_name)

        file_ext = self.complete_path_original.suffix
        if file_ext == '.ts':
            file_ext = '.mp4'

        return formatted_name + file_ext

    def find_initial(self) -> str:
        """
        Get the initial letter for alphabetical sorting.

        Returns:
            Lowercase title without leading article, for sorting.
        """
        return remove_article(self.title_fr).lower()

    def is_film(self) -> bool:
        """Check if this video is a film."""
        return self.type_file == 'Films'

    def is_serie(self) -> bool:
        """Check if this video is a TV series."""
        return self.type_file == 'Séries'

    def is_animation(self) -> bool:
        """Check if this video is animation."""
        return self.type_file == 'Animation'

    def is_film_serie(self) -> bool:
        """Check if this video is a film or series."""
        return self.type_file in FILMSERIE

    def is_film_anim(self) -> bool:
        """Check if this video is a film or animation."""
        return self.type_file in FILMANIM

    def is_not_doc(self) -> bool:
        """Check if this video is not a documentary."""
        return self.type_file in NOT_DOC
