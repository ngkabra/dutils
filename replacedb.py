
#!/usr/bin/python
'''Replace the database with a dump

Get the database and user name by loading settings.
Load settings is fake, because we do not load django.
We do not load django because the database might not be uptodate.

Drop the database and recreate it so db is clean.
from being sent.
'''
import argparse
from datetime import datetime
import os
from os.path import exists, expanduser
import sys
import subprocess
import MySQLdb as mysql
from logging.config import fileConfig
import django
from django.conf import settings
from django.core.management import ManagementUtility

import logging
logger = logging.getLogger(__name__)


def replace_db(dbfile):
    if not exists(expanduser(dbfile)):
        for f in (expanduser(dbfile) + '.sql.gz',
                  expanduser('~/u/' + dbfile + '.sql.gz')):
            if exists(f):
                dbfile = f
                break
        else:
            raise Exception('{} not found'.format(dbfile))
    logger.debug('Replacing db from {}'.format(dbfile))

    db = settings.DATABASES['default']

    # sanity check
    if db['NAME'] in ('navin_rs', 'navin_rsph'):
        raise Exception('WTF? Are you trying to replace production?')

    # drop and recreate database
    logger.debug('mysql connect {}'.format(db['NAME']))
    rootdb = mysql.connect(user=db['NAME'],
                           passwd=db['PASSWORD'])
    c = rootdb.cursor()
    try:
        c.execute('drop database %s' % db['NAME'])
        logger.debug('Dropped database {}'.format(db['NAME']))
    except:
        pass                              # ignore drop database errors
    c.execute('create database {} character set utf8 collate utf8_general_ci'.format(db['NAME']))
    logger.debug('Created database {}'.format(db['NAME']))
    c.close()
    rootdb.close()

    logger.info('replacedb started at {0:%H:%M:%S}'.format(datetime.now()))
    # now load the data. For that first gunzip it,
    # then run mysql in a subprocess
    unzipproc = subprocess.Popen(['gunzip', '--stdout', dbfile],
                                 stdout=subprocess.PIPE)
    mysqlproc = subprocess.Popen(
        ['mysql', '-u', db['USER'],
         '--password={}'.format(db['PASSWORD'],),
         db['NAME']],
        stdin=unzipproc.stdout, stdout=subprocess.PIPE)
    unzipproc.stdout.close()
    logger.debug('Waiting for gunzip|mysql process')
    mysqlproc.wait()

    # notifications_TODO: truncate the notifications
    # mydb = mysql.connect(user=db['USER'],
    #                     passwd=db['PASSWORD'],
    #                     db=db['NAME'])
    # mydb.cursor().execute('truncate table wcomments_enotify')

parser = argparse.ArgumentParser()
parser.add_argument('-D', '--demo', action='store_true',
                    help='Prep db for demo after loading')
parser.add_argument('-d', '--debug', action='store_true',
                    help='log debug messages to stderr')
parser.add_argument('-p', '--project-path', nargs='*',
                    help='directories to add to project path')
parser.add_argument('-s', '--settings-module',
                    default='settings',
                    help='settings for DJANGO_SETTINGS_MODULE')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='log messages to console')
parser.add_argument('-f', '--fixdemoscript',
                    default='scripts.pyfixtures.fix_demo',
                    help='dotted path for fix_demo script')
parser.add_argument('-n', '--no-syncdb',
                    action='store_true',
                    help='dont do syncdb or migrate')
parser.add_argument('file', help='Dump of database')

args = parser.parse_args()
handlers = 'console,file' if args.verbose else 'file'
fileConfig(expanduser('~/.pylog.cfg'),
           defaults=dict(
               logfile=expanduser('~/logs/replacedb.log'),
               root_handlers=handlers,
           ),
           disable_existing_loggers=False)

if args.debug:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


for path_el in args.project_path[::-1]:
    sys.path.insert(0, path_el)  # insert in reverse order to get correct order
if args.settings_module:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', args.settings_module)

replace_db(args.file)

if args.no_syncdb:
    cmds = []
elif django.VERSION[0] > 1 or django.VERSION[1] >= 9:
    # no syncdb in django 1.9 or above
    cmds = [['migrate']]
else:
    cmds = [['syncdb'], ['migrate']]

if args.demo:
    cmds.append(['runcmd', args.fixdemoscript])
for cmd in cmds:
    utility = ManagementUtility([sys.argv[0]] + cmd)
    utility.execute()
