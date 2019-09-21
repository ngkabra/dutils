from os.path import abspath
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    def handle(self, **options):
        print(abspath(settings.MEDIA_ROOT))
