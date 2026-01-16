# Améliorations à effectuer - Code Review CLI

> Généré le 2026-01-16 - Session de review approfondie

## Critiques (4)

### 1. Gestion d'erreurs API incomplète
- **Fichier**: `organize/pipeline/main_processor.py:75-130`
- **Problème**: `query_movie_database()` lève `RuntimeError` et `ConnectionError` mais les appelants utilisent `except (OSError, IOError, ValueError)` qui ne les capture pas
- **Impact**: Les erreurs API échouent silencieusement

### 2. String split sans vérification de longueur
- **Fichier**: `organize/filesystem/file_ops.py:226,238,274`
- **Problème**: Code comme `str(video.complete_path_original).split(video.type_file, 1)` suppose que split produit toujours 2 éléments
- **Impact**: Potentiel `IndexError` si le chemin ne contient pas le séparateur attendu

### 3. Connexions DB non fermées explicitement
- **Fichier**: `organize/api/cache_db.py:97`
- **Problème**: Dans `get_tmdb()` et méthodes similaires, cursor/connexion non fermés explicitement
- **Impact**: Potentiels problèmes de verrouillage avec accès concurrent
- **Solution**: Utiliser des context managers

### 4. Input utilisateur non validé
- **Fichier**: `organize/filesystem/file_ops.py:416-420`
- **Problème**: `handle_similar_file()` utilise `input()` sans sanitisation
- **Impact**: Potentiel comportement inattendu

---

## Haute priorité (5)

### 5. Logique de hash dupliquée
- **Fichiers**: `organize/pipeline/video_list.py:50-59` ET `organize/pipeline/processor.py:63-97`
- **Problème**: La logique de vérification de duplicats par hash existe en deux endroits avec des implémentations légèrement différentes
- **Solution**: Extraire vers une fonction utilitaire partagée

### 6. Context manager non utilisé partout
- **Fichier**: `organize/config/context.py:52-116`
- **Problème**: Le context manager thread-safe existe mais n'est pas utilisé dans tout le code
- **Impact**: Setup/teardown du contexte incohérent

### 7. Conditions imbriquées complexes
- **Fichier**: `organize/pipeline/orchestrator.py:171-216`
- **Problème**: `_process_new_video()` a des blocs if/else profondément imbriqués
- **Solution**: Extraire la gestion des fichiers non détectés

### 8. Vérifications null/empty incohérentes
- **Fichiers**: `organize/models/video.py:62`, `organize/classification/main_processor.py:153-160`
- **Problème**: Patterns multiples pour vérifier les chaînes vides mais incohérents

### 9. Gestion d'erreurs fichiers incohérente
- **Fichier**: `organize/filesystem/file_ops.py`
- **Problème**: `move_file()` capture `OSError` et `shutil.Error`, `copy_tree()` pareil, mais `aplatir_repertoire_series()` capture seulement `OSError` à un endroit
- **Solution**: Créer un pattern de gestion d'erreurs cohérent

---

## Moyenne priorité (8)

### 10. Magic numbers non centralisés
- **Exemples**:
  - `organize/pipeline/video_list.py:110`: `100000000.0` pour le seuil "tous les fichiers"
  - `organize/pipeline/video_list.py:141`: `> 10` seuil multiprocessing hardcodé
- **Solution**: Déplacer vers `settings.py`

### 11. Type hints manquants
- **Fichiers**:
  - `organize/pipeline/orchestrator.py:114-125`
  - `organize/classification/main_processor.py:41-49`
  - `organize/filesystem/file_ops.py:196`: fonction imbriquée `reps_pattern()`

### 12. Docstrings incomplètes
- **Fichiers**:
  - `organize/filesystem/file_ops.py:149`: pas de docstring pour `aplatir_repertoire_series()`
  - `organize/pipeline/orchestrator.py:114-125`: docstring `_process_single_video()` incomplète

### 13. Niveaux de log incohérents
- Certaines fonctions utilisent `logger.debug()` pour des infos opérationnelles importantes
- D'autres utilisent `logger.info()` pour des détails verbeux

### 14. Manipulation de chemins mixte (str vs Path)
- **Fichier**: `organize/filesystem/file_ops.py:226,238,274,426-430`
- **Problème**: Mélange de `str(path).split()` avec `Path.rglob()` et autres méthodes pathlib

### 15. Instances Console multiples
- **Fichiers**: 5 fichiers créent leur propre instance `Console()`
- **Solution**: Utiliser l'instance centralisée de `organize/ui/console.py`

### 16. Exceptions avalées en multiprocessing
- **Fichier**: `organize/pipeline/video_list.py:75-77`
- **Problème**: `process_single_video()` capture toutes les `Exception` et retourne None
- **Solution**: Logger au niveau WARNING et tracer les fichiers échoués

### 17. Imports conditionnels
- **Fichier**: `organize/classification/main_processor.py:65-73`
- **Problème**: Imports dans le corps de fonction pour éviter les imports circulaires

---

## Basse priorité (7)

### 18. Patterns regex non compilés
- **Fichiers**: `organize/models/video.py:90-96`, `organize/filesystem/file_ops.py:360,362`
- **Solution**: Pré-compiler les patterns regex au niveau module

### 19. Pas de validation des extensions de fichiers
- **Fichier**: `organize/filesystem/discovery.py:52`

### 20. Résolution incohérente des chemins de base de données
- **Fichiers**: `organize/api/cache_db.py:26`, `organize/utils/database.py`
- **Problème**: Chemins de DB relatifs, pourraient échouer selon le répertoire de travail

### 21. Pas de validation des paramètres de répertoire
- **Fichier**: `organize/config/cli.py:227-246`
- **Problème**: `_resolve_path()` résout les chemins mais ne valide pas qu'ils sont raisonnables

### 22. Capture d'exceptions trop large
- **Fichier**: `organize/__main__.py:420-424`
- **Problème**: Ne capture que `OSError`, manque `ValueError`, `AttributeError`

### 23. Types de retour incohérents
- `organize/filesystem/file_ops.py:95` vs `organize/filesystem/file_ops.py:390`

### 24. Vérifications d'existence de fichier redondantes
- **Fichier**: `organize/filesystem/symlinks.py:27-28`
- **Problème**: `.exists()` ET `.is_symlink()` appelés sur le même chemin

---

## Sécurité (3)

### 25. Pas de détection d'échappement symlink
- **Fichier**: `organize/filesystem/symlinks.py:30`
- **Problème**: Lors de la création de symlinks, pas de validation que la cible ne s'échappe pas des répertoires autorisés

### 26. Erreurs API TVDB ignorées silencieusement
- **Fichier**: `organize/api/validation.py:96-113`
- **Problème**: Les erreurs de connexion TVDB sont loggées en warning mais l'exécution continue

### 27. Chemin vidéo non validé dans subprocess
- **Fichier**: `organize/ui/interactive.py:67-73`
- **Risque mineur**: Pas de validation que `video_path` est sûr

---

## Résumé

| Sévérité | Nombre |
|----------|--------|
| Critique | 4 |
| Haute | 5 |
| Moyenne | 8 |
| Basse | 7 |
| Sécurité | 3 |
| **Total** | **27** |

## Actions recommandées (par ordre de priorité)

1. Corriger la gestion d'erreurs pour les échecs API (Critique #1)
2. Ajouter des vérifications de bornes pour les opérations sur chaînes (Critique #2)
3. Implémenter des context managers pour les connexions DB (Critique #3)
4. Valider et sanitiser les inputs utilisateur (Critique #4)
5. Extraire la logique dupliquée de vérification de hash (Haute #5)
6. Uniformiser la gestion d'erreurs dans les opérations fichiers (Haute #9)
7. Déplacer les magic numbers vers settings.py (Moyenne #10)
8. Ajouter les type hints manquants (Moyenne #11)
9. Consolider les instances Console (Moyenne #15)
