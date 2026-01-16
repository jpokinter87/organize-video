# Video Organizer (CLI)

Outil en ligne de commande pour l'organisation automatisee de videotheque avec detection de metadonnees via les APIs TMDB et TVDB.

## Fonctionnalites

- Detection automatique des metadonnees video (titre, annee, genre)
- Extraction des specifications techniques (codec, resolution, langue) via MediaInfo
- Renommage standardise avec titres francais
- Creation de structures de symlinks organisees par genre/ordre alphabetique
- Gestion des doublons via suivi MD5 en base SQLite
- Support des films, series TV, animation et documentaires

## Installation

### Prerequis

- Python 3.13+
- MediaInfo installe sur le systeme
- Cles API TMDB et TVDB

### Installation avec uv (recommande)

```bash
uv sync
```

### Installation avec pip

```bash
pip install -e .
```

## Configuration

Creer un fichier `.env` a la racine du projet :

```env
TMDB_API_KEY=votre_cle_tmdb
TVDB_API_KEY=votre_cle_tvdb
```

## Utilisation

```bash
# Mode standard (traitement des fichiers recents)
organize-video

# Traitement de tous les fichiers
organize-video --all

# Traitement des N derniers jours
organize-video -d 7

# Mode simulation (aucune modification)
organize-video --dry-run

# Mode force (ignore la verification des hash)
organize-video --force

# Repertoires personnalises
organize-video -i /source -o /temp -s /symlinks --storage /storage

# Mode debug
organize-video --debug --tag "motif_fichier"

# Mode legacy (utilise organize.py directement)
organize-video --legacy

# Alternative sans installation (execution directe du package)
python -m organize
```

### Options disponibles

| Option | Description |
|--------|-------------|
| `-i, --input` | Repertoire source des videos |
| `-o, --output` | Repertoire de sortie temporaire |
| `-s, --symlinks` | Repertoire des symlinks |
| `--storage` | Repertoire de stockage final |
| `-d, --days` | Nombre de jours a traiter |
| `--all` | Traiter tous les fichiers |
| `--force` | Ignorer la verification des hash |
| `--dry-run` | Mode simulation |
| `--debug` | Activer les logs debug |
| `--tag` | Filtrer par motif de nom de fichier |
| `--legacy` | Utiliser le mode legacy (organize.py) |

### Comportement interactif

Le script demande confirmation pour :
- Correspondances API incertaines ou multiples
- Fichiers non detectes automatiquement
- Fichiers similaires (doublons potentiels)
- Series non identifiees

## Structure des repertoires

```
/media/NAS64/temp/           # Repertoire source (DEFAULT_SEARCH_DIR)
  ├── Series/
  ├── Films/
  ├── Animation/
  └── Docs/

/media/NAS64/                # Stockage final (DEFAULT_STORAGE_DIR)
/media/Serveur/test/         # Structure symlinks (DEFAULT_SYMLINKS_DIR)
/media/Serveur/LAF/liens_a_faire/  # Symlinks temporaires
```

## Architecture

```
organize-video/
├── organize/                # Package principal
│   ├── __main__.py          # Point d'entree CLI
│   ├── config/              # Configuration et arguments
│   ├── models/              # Dataclass Video
│   ├── api/                 # Clients TMDB, TVDB, cache
│   ├── classification/      # Detection de type, genre, media info
│   ├── filesystem/          # Operations fichiers et symlinks
│   ├── ui/                  # Interface console et interactions
│   ├── pipeline/            # Traitement video principal
│   └── utils/               # Utilitaires (hash, database)
├── organize.py              # Script legacy (deprecated)
├── tests/                   # Tests unitaires
└── web/                     # Interface web (projet separe)
```

### Bases de donnees

- `cache.db` : Cache des reponses API TMDB/TVDB
- `symlink_video_Films.db` : Suivi des hash pour les films
- `symlink_video_Series.db` : Suivi des hash pour les series

## Tests

```bash
# Executer tous les tests
pytest

# Tests avec couverture
pytest --cov=organize

# Tests specifiques
pytest tests/unit/test_video_list.py
```

## Interface Web (projet separe)

Une interface web Django est en cours de developpement dans le repertoire `web/`.
**Cette interface n'est pas encore fonctionnelle.**

Pour plus d'informations, voir [web/README.md](web/README.md).

## Licence

MIT
