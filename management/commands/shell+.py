# Code adapted from shell.py management command in Django-1.4.3
# Don't want django-extensions just for shell_plus
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = "Runs a Python interactive interpreter. Tries to use IPython, if it's available."
    def ipython(self, imported_objects):
        from IPython import embed
        embed(user_ns=imported_objects)

    def handle_noargs(self, **options):
        imported_objects = {}
        from django.db.models.loading import get_models
        for m in get_models():
            imported_objects[m.__name__] = m

        try:
            self.ipython(imported_objects)
        except ImportError:
            import code
            imported_objects = {}
            try: # Try activating rlcompleter, because it's handy.
                import readline
            except ImportError:
                pass
            else:
                # We don't have to wrap the following import in a 'try', because
                # we already know 'readline' was imported successfully.
                import rlcompleter
                readline.set_completer(rlcompleter.Completer(imported_objects).complete)
                readline.parse_and_bind("tab:complete")
            code.interact(local=imported_objects)
