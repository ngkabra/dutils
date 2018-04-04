from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('script')
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        mod = __import__(options['script'], [], [], [' '])
        mod.run(*options.get('args', []))
