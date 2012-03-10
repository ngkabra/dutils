from django.core.management.base import BaseCommand
from django.conf import settings

import subprocess


class Command(BaseCommand):
     def handle(self,**options):
         db = settings.DATABASES['default']
         subprocess.call(['mysqldump',
                          '-r',
                          'rs.sql',
                          '-u',
                          db['USER'],
                          '--password=%s' % (db['PASSWORD'],),
                          db['NAME']])
         subprocess.call(['rm', '-f', 'rs.sql.gz'])
         subprocess.call(['gzip', 'rs.sql'])
