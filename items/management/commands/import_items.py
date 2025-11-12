from django.core.management.base import BaseCommand, CommandError

from items.services import import_items


class Command(BaseCommand):
    help = 'Import items from the configured source.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-url',
            dest='source_url',
            help='Optional URL to override the configured IMPORT_SOURCE_URL setting.',
        )

    def handle(self, *args, **options):
        source_url = options.get('source_url')
        try:
            report = import_items(source_url=source_url)
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed: {report.created} created, {report.updated} updated '
                f'(rows processed: {report.total_rows})'
            )
        )

