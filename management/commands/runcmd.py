from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('script')
        parser.add_argument('arguments', nargs='*')

    def handle(self, *args, **options):
        script = options['script']
        arguments = options['arguments']
        mod = __import__(script, [], [], [' '])
        mod.run(*arguments)
