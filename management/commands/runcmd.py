from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('script')
        parser.add_argument('arguments', nargs='*')

    def handle(self, *args, **options):
        script = args[0]
        arguments = args[1:]
        mod = __import__(script, [], [], [' '])
        mod.run(*arguments)
