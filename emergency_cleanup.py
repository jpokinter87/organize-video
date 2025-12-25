def emergency_cleanup(target_dir: Path):
    """Nettoyage d'urgence des structures récursives."""
    console.print(f"[red]🚨 NETTOYAGE D'URGENCE de {target_dir}[/red]")

    def find_and_remove_recursive_dirs(path: Path, depth: int = 0) -> int:
        if depth > 20:  # Protection contre récursivité infinie
            return 0

        removed_count = 0

        try:
            for item in list(path.iterdir()):
                if item.is_dir():
                    # Détection de répétition de nom dans le chemin
                    path_parts = item.parts
                    if len(path_parts) > 3:
                        last_parts = path_parts[-3:]
                        if len(set(last_parts)) < len(last_parts):  # Répétition détectée
                            console.print(f"[red]Suppression récursive: {item}[/red]")
                            shutil.rmtree(item, ignore_errors=True)
                            removed_count += 1
                            continue

                    # Récursion
                    removed_count += find_and_remove_recursive_dirs(item, depth + 1)
        except (PermissionError, FileNotFoundError):
            pass

        return removed_count

    total_removed = find_and_remove_recursive_dirs(target_dir)
    console.print(f"[green]✅ {total_removed} dossiers récursifs supprimés[/green]")

# Pour utiliser en cas d'urgence :
# emergency_cleanup(Path("/media/Serveur/LAF/liens_à_faire"))