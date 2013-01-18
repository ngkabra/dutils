from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, script, *args, **kwargs):
        mod = __import__(script, [], [], [' '])
        mod.run(*args, **kwargs)
