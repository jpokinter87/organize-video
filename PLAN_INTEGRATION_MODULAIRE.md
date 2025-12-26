# Plan d'integration modulaire pour organize/__main__.py

## Objectif
Remplacer la delegation simple vers `organize.py` par une integration utilisant les modules existants, tout en conservant un mode legacy pour la securite.

## Etat actuel

Le refactoring a cree une structure modulaire (~2900 lignes) dans `organize/` avec :
- `api/` : tmdb_client, tvdb_client, cache_db
- `classification/` : genre_classifier, type_detector, text_processing
- `config/` : settings, cli, context
- `filesystem/` : discovery, file_ops, symlinks, paths
- `models/` : video, cache
- `pipeline/` : processor, series_handler
- `ui/` : display, console, confirmations
- `utils/` : hash

**Probleme** : `organize/__main__.py` delegue actuellement vers l'ancien `organize.py` au lieu d'utiliser ces modules.

## Fichiers a modifier

### 1. `organize/config/cli.py`
Ajouter le flag `--legacy` au parser d'arguments :
```python
parser.add_argument(
    '--legacy',
    action='store_true',
    help="utiliser le mode legacy (delegation complete vers organize.py)"
)
```

### 2. `organize/__main__.py` (reecriture complete ~350 lignes)

**Structure du nouveau fichier :**

```
1. Imports modulaires (composants disponibles)
   - organize.config: CLIArgs, parse_arguments, args_to_cli_args, CATEGORIES
   - organize.models: Video
   - organize.api: TmdbClient, CacheDB
   - organize.filesystem: get_available_categories, count_videos, copy_tree, verify_symlinks, setup_working_directories
   - organize.ui: ConsoleUI, display_statistics, display_summary
   - organize.utils: checksum_md5

2. Chargement lazy de organize.py pour les fonctions manquantes
   - _load_organize_module() - charge organize.py dynamiquement
   - Wrappers pour chaque fonction gap avec marqueur [GAP]

3. Fonctions gap (temporaires - a migrer vers modules)
   - validate_api_keys()
   - test_api_connectivity()
   - media_info()
   - set_fr_title_and_category()
   - query_movie_database()
   - find_similar_file()
   - aplatir_repertoire_series()
   - select_db(), hash_exists_in_db(), add_hash_to_db()
   - create_video_list()
   - process_video()
   - rename_video()
   - find_symlink_and_sub_dir()
   - find_directory_for_video()
   - add_episodes_titles()
   - move_file_new_nas()
   - cleanup_directories()

4. Fonctions helpers
   - setup_logging(debug: bool) - configure loguru
   - display_configuration(cli_args, console) - affiche panneau config
   - display_simulation_banner(console) - banniere mode simulation
   - check_legacy_flag() - detecte --legacy dans sys.argv
   - run_legacy_mode() - delegue entierement a organize.py

5. Fonction main()
   - Verifie --legacy en premier -> run_legacy_mode()
   - Parse arguments avec parse_arguments() modulaire
   - Setup logging
   - Validation repertoire source
   - Creation ExecutionContext
   - Affichage config et banniere simulation
   - Validation API (gap)
   - Setup directories (modulaire)
   - Detection categories (modulaire)
   - Comptage videos (modulaire)
   - Aplatissement series (gap)
   - Creation liste videos (gap)
   - Boucle de traitement principale (gap functions)
   - Ajout titres episodes (gap)
   - Copie finale (modulaire)
   - Verification symlinks (modulaire)
   - Statistiques (modulaire)
```

## Flux d'execution

```
organize-video [--legacy]
       |
       +-- --legacy present ?
       |   +-- OUI -> run_legacy_mode() -> organize.py:main()
       |
       +-- NON -> main() modulaire
           +-- Composants modulaires (organize/*)
           +-- Fonctions gap (organize.py via import dynamique)
```

## Sequence d'implementation

1. **Modifier `cli.py`** : Ajouter argument `--legacy`
2. **Reecrire `__main__.py`** :
   - Imports modulaires
   - Lazy loading organize.py
   - Wrappers gap functions avec marqueur [GAP]
   - Helpers (setup_logging, display_configuration)
   - run_legacy_mode()
   - main() avec logique complete
3. **Tests** : Verifier que les 324 tests passent
4. **Test fonctionnel** : Tester `organize-video --dry-run` et `organize-video --legacy --dry-run`

## Avantages de cette approche

1. **Securite** : `--legacy` permet de revenir au code eprouve
2. **Progressivite** : Les marqueurs [GAP] identifient clairement ce qui reste a migrer
3. **Compatibilite** : Les tests existants continuent de passer
4. **Tracabilite** : Chaque fonction gap documente sa source

## Migration future

Pour chaque fonction gap :
1. Creer le module correspondant (ex: `classification/media_info.py`)
2. Ecrire les tests unitaires
3. Remplacer l'import gap par l'import modulaire
4. Supprimer le wrapper gap

Modules prioritaires a creer :
- `classification/media_info.py` - extraction pymediainfo
- `api/hash_db.py` - gestion bases de hash (symlink_video_*.db)
- `pipeline/interactive.py` - query_movie_database avec UI
- `classification/similarity.py` - detection doublons rapidfuzz

## Pour lancer l'implementation

Demander a Claude : "Implemente le plan d'integration modulaire selon PLAN_INTEGRATION_MODULAIRE.md"