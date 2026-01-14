# Video Organizer

Outil d'organisation automatisee de videotheque avec detection de metadonnees via les APIs TMDB et TVDB.

## Fonctionnalites

- Detection automatique des metadonnees video (titre, annee, genre)
- Extraction des specifications techniques (codec, resolution, langue) via MediaInfo
- Renommage standardise avec titres francais
- Creation de structures de symlinks organisees par genre/ordre alphabetique
- Gestion des doublons via suivi MD5 en base SQLite
- Support des films, series TV, animation et documentaires

## Modes de Fonctionnement

L'application propose **deux modes de fonctionnement** adaptes a differents usages :

### Mode Console (CLI)

Le mode console est ideal pour :
- Traitement automatise en lot
- Integration dans des scripts ou cron jobs
- Utilisateurs avances preferant la ligne de commande

#### Demarrage

```bash
# Mode standard (traitement des fichiers recents)
python -m organize

# Traitement de tous les fichiers
python -m organize --all

# Traitement des N derniers jours
python -m organize -d 7

# Mode simulation (aucune modification)
python -m organize --dry-run

# Mode force (ignore la verification des hash)
python -m organize --force

# Repertoires personnalises
python -m organize -i /source -o /temp -s /symlinks --storage /storage

# Mode debug
python -m organize --debug --tag "motif_fichier"

# Mode legacy (utilise organize.py directement)
python -m organize --legacy
```

#### Options disponibles

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

#### Comportement interactif

En mode console, le script demande confirmation pour :
- Correspondances API incertaines ou multiples
- Fichiers non detectes automatiquement
- Fichiers similaires (doublons potentiels)
- Series non identifiees

### Mode Interface Web (UI)

Le mode web est ideal pour :
- Gestion visuelle de la videotheque
- Traitement interactif avec confirmation par clic
- Consultation des statistiques et logs
- Utilisateurs preferant une interface graphique

#### Demarrage

```bash
cd web
python manage.py migrate  # Premiere utilisation uniquement
python manage.py init_settings  # Initialiser les parametres
python manage.py runserver 0.0.0.0:8000
```

Acceder a l'interface via `http://localhost:8000`

#### Fonctionnalites de l'interface web

**Tableau de bord** (`/`)
- Resume des videos traitees
- Confirmations en attente
- Jobs de traitement actifs
- Videos recentes

**Traitement** (`/processing/`)
- Creation de jobs de scan
- Suivi du progres en temps reel
- Gestion des confirmations avec interface modale
- Annulation et redemarrage des jobs

**Bibliotheque** (`/library/`)
- Navigation par categorie (films, series, animation, docs)
- Filtrage par genre, annee, recherche textuelle
- Affichage en grille avec posters
- Details des videos

**Statistiques** (`/dashboard/`)
- Statistiques par categorie et genre
- Activite recente
- Logs de traitement filtrable
- Informations de stockage

**Configuration** (`/settings/`)
- Gestion des repertoires
- Configuration des cles API
- Parametres de traitement
- Gestion de la base de hash

#### Technologies

- Django 4.x comme framework web
- HTMX pour les interactions dynamiques sans rechargement
- Huey pour les taches asynchrones en arriere-plan
- Interface responsive avec composants modulaires

## Configuration

### Prerequis

- Python 3.10+
- MediaInfo installe sur le systeme
- Cles API TMDB et TVDB

### Installation des dependances

```bash
# Avec uv (recommande)
uv sync

# Ou avec pip
pip install -r requirements.txt
```

### Variables d'environnement

Creer un fichier `.env` a la racine du projet :

```env
TMDB_API_KEY=votre_cle_tmdb
TVDB_API_KEY=votre_cle_tvdb
```

### Structure des repertoires

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

### Structure du projet

```
organize/
├── organize.py              # Application legacy monolithique
├── organize/                # Package modulaire
│   ├── __main__.py          # Point d'entree CLI
│   ├── config/              # Configuration et arguments
│   ├── models/              # Dataclass Video
│   ├── api/                 # Clients TMDB, TVDB, cache
│   ├── classification/      # Detection de type, genre, media info
│   ├── filesystem/          # Operations fichiers et symlinks
│   ├── ui/                  # Interface console et interactions
│   ├── pipeline/            # Traitement video principal
│   └── utils/               # Utilitaires (hash, database)
└── web/                     # Interface web Django
    ├── videomanager/        # Configuration Django
    ├── core/                # Modeles et services principaux
    ├── processing/          # Gestion des jobs de traitement
    ├── library/             # Navigation de la bibliotheque
    └── dashboard/           # Statistiques et logs
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

## Contribution

Les contributions sont bienvenues. Merci de :
1. Forker le projet
2. Creer une branche pour votre fonctionnalite
3. Ecrire des tests pour les nouvelles fonctionnalites
4. Soumettre une pull request

## Licence

Ce projet est sous licence MIT.
