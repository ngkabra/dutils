from django.core.management.base import BaseCommand

class Command(BaseCommand):
    '''Run a script with django initialized

    Import a standalone script and call `run` on it
    This is not to run a managepy django command
    Django will be initialized

    Expects arguments as a0 a1 kw1=kwarg1 kw2=kwarg2
    '''
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
