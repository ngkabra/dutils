from optparse import make_option
from os.path import expanduser, dirname, basename

from django.core.management.base import BaseCommand
from django.conf import settings

import subprocess


class Command(BaseCommand):
     project_name = basename(dirname(dirname(dirname(dirname(__file__)))))
     option_list = BaseCommand.option_list + (
          make_option('--output',
                      default='~/{}.sql'.format(project_name),
                      help='output file'),)
     def handle(self, **options):
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
