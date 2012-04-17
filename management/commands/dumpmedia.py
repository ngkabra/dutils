from optparse import make_option
from os.path import expanduser, dirname, basename, abspath

from django.core.management.base import BaseCommand
from django.conf import settings

import subprocess


class Command(BaseCommand):
    project_root = abspath(dirname(dirname(dirname(dirname(__file__)))))
    project_name = basename(project_root)
    option_list = BaseCommand.option_list + (
        make_option('--output',
                    default='~/{}-media.gz'.format(project_name),
                    help='output file'),)
    def handle(self, **options):
        outfile = expanduser(options['output'])
        mediadir = basename(settings.MEDIA_ROOT)
        subprocess.call(['tar',
                         '--directory', Command.project_root,
                         '-czf', outfile,
                         mediadir])
