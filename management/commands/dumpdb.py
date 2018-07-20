from os.path import expanduser, dirname, basename

from django.core.management.base import BaseCommand
from django.conf import settings

import subprocess


class Command(BaseCommand):
     project_name = basename(dirname(dirname(dirname(dirname(__file__)))))
     def add_arguments(self, parser):
          parser.add_argument(
               '--output',
               default='~/{}.sql'.format(Command.project_name),
               help='output file')

     def handle(self, *args, **options):
          db = settings.DATABASES['default']
          outfile = expanduser(options['output'])
          if outfile.endswith('.gz'):
               outfile = outfile[:-3]
          outfile_gz = outfile + '.gz'
          subprocess.call(['mysqldump',
                           '-r',
                           outfile,
                           '-u',
                           db['USER'],
                           '--password=%s' % (db['PASSWORD'],),
                           db['NAME']])
          subprocess.call(['rm', '-f', outfile_gz])
          subprocess.call(['gzip', outfile])
