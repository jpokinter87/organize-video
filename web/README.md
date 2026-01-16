# Video Organizer - Interface Web

Interface web Django pour l'organisation de videotheque.

> **STATUT : EN DEVELOPPEMENT**
> Cette application n'est pas encore fonctionnelle. Le developpement est en cours.

## Prerequis

- Python 3.13+
- MediaInfo installe sur le systeme
- Cles API TMDB et TVDB (dans `.env` a la racine du projet parent)

## Installation

```bash
cd web

# Installer les dependances
pip install -r requirements.txt

# Ou avec uv
uv pip install -r requirements.txt

# Initialiser la base de donnees
python manage.py migrate

# Initialiser les parametres par defaut
python manage.py init_settings

# Lancer le serveur de developpement
python manage.py runserver 0.0.0.0:8000
```

Acceder a l'interface via `http://localhost:8000`

## Configuration

Les cles API doivent etre definies dans le fichier `.env` du projet parent :

```env
TMDB_API_KEY=votre_cle_tmdb
TVDB_API_KEY=votre_cle_tvdb

# Optionnel : configuration Django
DJANGO_SECRET_KEY=votre_cle_secrete
DJANGO_DEBUG=True
```

Les repertoires peuvent etre configures via l'interface web (`/settings/`) ou via variables d'environnement.

## Structure

```
web/
├── videomanager/        # Configuration Django
│   ├── settings.py      # Parametres Django
│   ├── urls.py          # Routes principales
│   └── wsgi.py          # Point d'entree WSGI
├── core/                # Logique metier principale
│   ├── models.py        # Modeles Django ORM
│   ├── services/        # Services (TMDB, traitement video)
│   ├── tasks.py         # Taches asynchrones Huey
│   └── management/      # Commandes Django personnalisees
├── processing/          # Gestion des jobs de traitement
├── library/             # Navigation de la bibliotheque
├── dashboard/           # Statistiques et logs
├── templates/           # Templates HTML
└── static/              # Fichiers statiques (CSS, JS)
```

## Fonctionnalites (prevues)

- **Tableau de bord** (`/`) : Resume, confirmations en attente, jobs actifs
- **Traitement** (`/processing/`) : Creation et suivi des jobs de scan
- **Bibliotheque** (`/library/`) : Navigation par categorie, filtres, posters
- **Statistiques** (`/dashboard/`) : Stats, logs, infos stockage
- **Configuration** (`/settings/`) : Repertoires, cles API, parametres

## Technologies

- Django 5.x
- HTMX pour les interactions dynamiques
- Huey pour les taches en arriere-plan
- SQLite pour la base de donnees

## Relation avec l'application CLI

Cette interface web est un projet **separe et independant** de l'application CLI `organize-video`.

- Les deux applications ne partagent **aucun code**
- Chacune a sa propre base de donnees
- Elles peuvent etre deployees independamment

Pour l'application CLI (fonctionnelle), voir le README a la racine du projet.

## Developpement

```bash
# Lancer les tests
pytest

# Lancer le serveur avec rechargement automatique
python manage.py runserver

# Lancer le worker Huey (taches en arriere-plan)
python manage.py run_huey
```

## Licence

MIT
