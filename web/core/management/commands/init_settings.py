"""Initialize default configuration settings."""

from django.core.management.base import BaseCommand
from django.conf import settings

from core.models import ConfigurationSetting


class Command(BaseCommand):
    help = 'Initialize default configuration settings'

    def handle(self, *args, **options):
        defaults = [
            {
                'key': 'search_dir',
                'value': str(getattr(settings, 'DEFAULT_SEARCH_DIR', '/media/NAS64/temp')),
                'value_type': 'path',
                'description': 'Repertoire de recherche des videos',
            },
            {
                'key': 'storage_dir',
                'value': str(getattr(settings, 'DEFAULT_STORAGE_DIR', '/media/NAS64')),
                'value_type': 'path',
                'description': 'Repertoire de stockage final',
            },
            {
                'key': 'symlinks_dir',
                'value': str(getattr(settings, 'DEFAULT_SYMLINKS_DIR', '/media/Serveur/test')),
                'value_type': 'path',
                'description': 'Repertoire des liens symboliques',
            },
            {
                'key': 'temp_symlinks_dir',
                'value': str(getattr(settings, 'DEFAULT_TEMP_SYMLINKS_DIR', '/media/Serveur/LAF/liens_a_faire')),
                'value_type': 'path',
                'description': 'Repertoire des liens temporaires',
            },
            {
                'key': 'default_days',
                'value': '7',
                'value_type': 'integer',
                'description': 'Nombre de jours par defaut pour le scan',
            },
            {
                'key': 'dry_run_default',
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Mode simulation par defaut',
            },
        ]

        created = 0
        updated = 0

        for item in defaults:
            setting, was_created = ConfigurationSetting.objects.get_or_create(
                key=item['key'],
                defaults={
                    'value': item['value'],
                    'value_type': item['value_type'],
                    'description': item['description'],
                }
            )
            if was_created:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created: {item['key']}")
                )
            else:
                # Update description if missing
                if not setting.description:
                    setting.description = item['description']
                    setting.save()
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nInitialization complete: {created} created, {updated} updated"
            )
        )
