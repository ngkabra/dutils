from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('script')
        parser.add_argument('arguments', nargs='*')

    def handle(self, *args, **options):
        script = options['script']
        args = []
        kwargs = {}
        for argument in options['arguments']:
            if '=' in argument:
                key, value = argument.split('=', 1)
                kwargs[key] = value
            else:
                args.append(argument)
        mod = __import__(script, [], [], [' '])
        mod.run(*args, **kwargs)
