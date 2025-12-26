"""
Core Django models for the video organization web interface.

This module defines the main data models used throughout the application:
- Video: Processed video files with metadata from TMDB/TVDB
- ProcessingJob: Scan/processing sessions
- PendingConfirmation: Videos awaiting user decision
- ConfigurationSetting: Application settings stored in database
- FileHash: Hash tracking for duplicate detection
- ProcessingLog: Processing history and logs
"""

import json
from django.db import models
from django.utils import timezone
from pathlib import Path


class ConfigurationSetting(models.Model):
    """Application configuration stored in database."""

    class ValueType(models.TextChoices):
        STRING = 'string', 'Texte'
        PATH = 'path', 'Chemin'
        INTEGER = 'integer', 'Entier'
        BOOLEAN = 'boolean', 'Booleen'
        JSON = 'json', 'JSON'

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField()
    value_type = models.CharField(max_length=20, choices=ValueType.choices, default=ValueType.STRING)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuration_settings'
        verbose_name = 'Parametre'
        verbose_name_plural = 'Parametres'
        ordering = ['key']

    def __str__(self):
        return f"{self.key}: {self.value[:50]}"

    def get_typed_value(self):
        """Return value with proper Python type."""
        if self.value_type == self.ValueType.INTEGER:
            return int(self.value)
        elif self.value_type == self.ValueType.BOOLEAN:
            return self.value.lower() in ('true', '1', 'yes', 'oui')
        elif self.value_type == self.ValueType.JSON:
            return json.loads(self.value)
        elif self.value_type == self.ValueType.PATH:
            return Path(self.value)
        return self.value

    @classmethod
    def get_value(cls, key: str, default=None):
        """Get a setting value by key."""
        try:
            setting = cls.objects.get(key=key)
            return setting.get_typed_value()
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(cls, key: str, value, value_type: str = 'string', description: str = ''):
        """Set a setting value."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
            value_type = 'json'
        elif isinstance(value, bool):
            value = str(value).lower()
            value_type = 'boolean'
        elif isinstance(value, int):
            value = str(value)
            value_type = 'integer'
        elif isinstance(value, Path):
            value = str(value)
            value_type = 'path'
        else:
            value = str(value)

        obj, created = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'value_type': value_type,
                'description': description,
            }
        )
        return obj


class ProcessingJob(models.Model):
    """Scan/processing session."""

    class Status(models.TextChoices):
        QUEUED = 'queued', 'En file d\'attente'
        SCANNING = 'scanning', 'Analyse en cours'
        AWAITING_CONFIRMATION = 'awaiting', 'En attente de confirmation'
        PROCESSING = 'processing', 'Traitement en cours'
        COMPLETED = 'completed', 'Termine'
        FAILED = 'failed', 'Echec'
        CANCELLED = 'cancelled', 'Annule'

    # Job configuration
    source_directory = models.CharField(max_length=1000)
    categories = models.JSONField(default=list, help_text="Categories a traiter: Films, Series, Animation, Docs")
    process_all = models.BooleanField(default=False, help_text="Traiter tous les fichiers")
    days_back = models.IntegerField(default=0, help_text="Nombre de jours a remonter (0 = recent)")
    force_mode = models.BooleanField(default=False, help_text="Ignorer verification des hash")
    dry_run = models.BooleanField(default=False, help_text="Mode simulation")

    # Status tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)

    # Progress tracking
    total_files = models.IntegerField(default=0)
    scanned_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    confirmed_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)
    skipped_files = models.IntegerField(default=0)
    current_file = models.CharField(max_length=500, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # User who launched the job
    launched_by = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'processing_jobs'
        ordering = ['-created_at']
        verbose_name = 'Job de traitement'
        verbose_name_plural = 'Jobs de traitement'

    def __str__(self):
        return f"Job #{self.id} - {self.get_status_display()}"

    @property
    def progress_percent(self) -> int:
        """Calculate progress percentage."""
        if self.total_files == 0:
            return 0
        return int((self.processed_files / self.total_files) * 100)

    @property
    def pending_confirmations_count(self) -> int:
        """Count pending confirmations for this job."""
        return self.pending_confirmations.filter(is_resolved=False).count()

    @property
    def duration(self):
        """Calculate job duration."""
        if not self.started_at:
            return None
        end_time = self.completed_at or timezone.now()
        return end_time - self.started_at


class Video(models.Model):
    """Processed video file with metadata."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        SCANNING = 'scanning', 'Analyse'
        AWAITING_CONFIRMATION = 'awaiting', 'Confirmation requise'
        CONFIRMED = 'confirmed', 'Confirme'
        PROCESSING = 'processing', 'En traitement'
        COMPLETED = 'completed', 'Termine'
        FAILED = 'failed', 'Echec'
        SKIPPED = 'skipped', 'Ignore'

    class Category(models.TextChoices):
        FILMS = 'Films', 'Films'
        SERIES = 'Series', 'Series'
        ANIMATION = 'Animation', 'Animation'
        DOCS = 'Docs', 'Documentaires'
        DOCS1 = 'Docs#1', 'Documentaires #1'

    # File information
    original_path = models.CharField(max_length=1000, db_index=True)
    original_filename = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0)
    file_hash = models.CharField(max_length=64, db_index=True, blank=True)

    # Extracted metadata (from guessit)
    detected_title = models.CharField(max_length=500, blank=True)
    detected_year = models.IntegerField(null=True, blank=True)
    detected_season = models.IntegerField(null=True, blank=True)
    detected_episode = models.IntegerField(null=True, blank=True)

    # Technical specs
    video_codec = models.CharField(max_length=50, blank=True)
    resolution = models.CharField(max_length=20, blank=True)
    language = models.CharField(max_length=50, blank=True)
    spec_string = models.CharField(max_length=100, blank=True, help_text="Ex: FR x264 1080p")

    # TMDB/TVDB metadata
    tmdb_id = models.IntegerField(null=True, blank=True, db_index=True)
    tvdb_id = models.IntegerField(null=True, blank=True, db_index=True)
    title_fr = models.CharField(max_length=500, blank=True, verbose_name="Titre francais")
    title_original = models.CharField(max_length=500, blank=True, verbose_name="Titre original")
    release_date = models.DateField(null=True, blank=True)
    overview = models.TextField(blank=True, verbose_name="Synopsis")
    vote_average = models.FloatField(null=True, blank=True, verbose_name="Note")
    vote_count = models.IntegerField(null=True, blank=True)
    popularity = models.FloatField(null=True, blank=True)
    poster_path = models.CharField(max_length=200, blank=True, help_text="TMDB poster path")
    poster_local = models.CharField(max_length=500, blank=True, help_text="Cached local poster path")

    # Classification
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    genre = models.CharField(max_length=100, blank=True)
    genres_list = models.JSONField(default=list)

    # Directors/Cast (for display)
    directors = models.JSONField(default=list, help_text="Liste des realisateurs")
    cast = models.JSONField(default=list, help_text="Liste des acteurs principaux")

    # Processing status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    # Output paths
    formatted_filename = models.CharField(max_length=500, blank=True)
    destination_path = models.CharField(max_length=1000, blank=True)
    symlink_path = models.CharField(max_length=1000, blank=True)

    # Relationships
    processing_job = models.ForeignKey(
        ProcessingJob,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='videos'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'videos'
        ordering = ['-created_at']
        verbose_name = 'Video'
        verbose_name_plural = 'Videos'
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['tmdb_id']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['title_fr']),
        ]

    def __str__(self):
        return self.title_fr or self.detected_title or self.original_filename

    @property
    def display_title(self) -> str:
        """Get the best available title for display."""
        return self.title_fr or self.detected_title or self.original_filename

    @property
    def year(self) -> int | None:
        """Get year from release date or detected year."""
        if self.release_date:
            return self.release_date.year
        return self.detected_year

    @property
    def poster_url(self) -> str:
        """Get full poster URL."""
        if self.poster_local:
            return f"/static/{self.poster_local}"
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w342{self.poster_path}"
        return ""

    @property
    def poster_url_large(self) -> str:
        """Get large poster URL."""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return ""

    @property
    def is_series(self) -> bool:
        """Check if video is a series."""
        return self.category == self.Category.SERIES

    @property
    def is_film(self) -> bool:
        """Check if video is a film."""
        return self.category == self.Category.FILMS

    @property
    def episode_info(self) -> str:
        """Format episode info for series."""
        if self.detected_season and self.detected_episode:
            return f"S{self.detected_season:02d}E{self.detected_episode:02d}"
        return ""


class PendingConfirmation(models.Model):
    """Videos awaiting user decision."""

    class ConfirmationType(models.TextChoices):
        TITLE_MATCH = 'title_match', 'Confirmation de titre'
        GENRE_SELECT = 'genre_select', 'Selection de genre'
        DUPLICATE = 'duplicate', 'Doublon detecte'
        MANUAL_ENTRY = 'manual_entry', 'Saisie manuelle requise'
        NOT_FOUND = 'not_found', 'Non trouve dans TMDB'

    class Resolution(models.TextChoices):
        PENDING = 'pending', 'En attente'
        ACCEPTED = 'accepted', 'Accepte'
        REJECTED = 'rejected', 'Rejete'
        MANUAL = 'manual', 'Saisie manuelle'
        SKIPPED = 'skipped', 'Ignore'

    video = models.OneToOneField(
        Video,
        on_delete=models.CASCADE,
        related_name='pending_confirmation'
    )
    job = models.ForeignKey(
        ProcessingJob,
        on_delete=models.CASCADE,
        related_name='pending_confirmations'
    )

    confirmation_type = models.CharField(max_length=20, choices=ConfirmationType.choices)

    # TMDB search results for selection
    tmdb_candidates = models.JSONField(
        default=list,
        help_text="Liste des candidats TMDB avec poster, synopsis, etc."
    )

    # User response
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolution = models.CharField(
        max_length=20,
        choices=Resolution.choices,
        default=Resolution.PENDING
    )
    selected_tmdb_id = models.IntegerField(null=True, blank=True)
    manual_title = models.CharField(max_length=500, blank=True)
    manual_year = models.IntegerField(null=True, blank=True)
    selected_genre = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pending_confirmations'
        ordering = ['created_at']
        verbose_name = 'Confirmation en attente'
        verbose_name_plural = 'Confirmations en attente'

    def __str__(self):
        return f"Confirmation pour {self.video.original_filename}"

    def resolve(self, resolution: str, **kwargs):
        """Mark confirmation as resolved."""
        self.is_resolved = True
        self.resolution = resolution
        self.resolved_at = timezone.now()

        if 'tmdb_id' in kwargs:
            self.selected_tmdb_id = kwargs['tmdb_id']
        if 'title' in kwargs:
            self.manual_title = kwargs['title']
        if 'year' in kwargs:
            self.manual_year = kwargs['year']
        if 'genre' in kwargs:
            self.selected_genre = kwargs['genre']

        self.save()


class FileHash(models.Model):
    """Hash tracking for duplicate detection (mirrors existing SQLite DBs)."""

    hash_value = models.CharField(max_length=64, primary_key=True)
    filepath = models.CharField(max_length=1000)
    filename = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0)
    category = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'file_hashes'
        verbose_name = 'Hash de fichier'
        verbose_name_plural = 'Hash de fichiers'

    def __str__(self):
        return f"{self.filename} ({self.hash_value[:16]}...)"


class ProcessingLog(models.Model):
    """Processing history and logs."""

    class Level(models.TextChoices):
        DEBUG = 'DEBUG', 'Debug'
        INFO = 'INFO', 'Info'
        WARNING = 'WARNING', 'Avertissement'
        ERROR = 'ERROR', 'Erreur'
        SUCCESS = 'SUCCESS', 'Succes'

    job = models.ForeignKey(
        ProcessingJob,
        on_delete=models.CASCADE,
        related_name='logs',
        null=True, blank=True
    )
    video = models.ForeignKey(
        Video,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='logs'
    )

    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'processing_logs'
        ordering = ['-created_at']
        verbose_name = 'Log de traitement'
        verbose_name_plural = 'Logs de traitement'
        indexes = [
            models.Index(fields=['job', 'level']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.level}] {self.message[:50]}"

    @classmethod
    def log(cls, level: str, message: str, job=None, video=None, **details):
        """Create a log entry."""
        return cls.objects.create(
            level=level,
            message=message,
            job=job,
            video=video,
            details=details
        )

    @classmethod
    def info(cls, message: str, **kwargs):
        return cls.log('INFO', message, **kwargs)

    @classmethod
    def warning(cls, message: str, **kwargs):
        return cls.log('WARNING', message, **kwargs)

    @classmethod
    def error(cls, message: str, **kwargs):
        return cls.log('ERROR', message, **kwargs)

    @classmethod
    def success(cls, message: str, **kwargs):
        return cls.log('SUCCESS', message, **kwargs)
