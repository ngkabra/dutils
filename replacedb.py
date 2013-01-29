#!/usr/bin/python
'''Replace the database with a dump

Get the database and user name by loading settings.
Load settings is fake, because we do not load django.
We do not load django because the database might not be uptodate.

Drop the database and recreate it so db is clean.
After loading, truncate the enotify table to prevent notifications
from being sent.
'''

import argparse
from os.path import dirname, exists, expanduser
import sys
import subprocess
import MySQLdb as mysql

# first set path appropriately so settings can be loaded
topdir = dirname(dirname(__file__))
sys.path.insert(0, topdir)

import settings

def replace_db(dbfile):
    if not exists(expanduser(dbfile)):
        for f in (expanduser(dbfile) + '.sql.gz',
                  expanduser('~/' + dbfile + '.sql.gz')):
            if exists(f):
                dbfile = f
                break
        else:
            raise Exception('{} not found'.format(dbfile))

    db = settings.DATABASES['default']

    # sanity check
    if db['NAME'] in ('navin_rs', 'navin_rsph'):
        raise Exception('WTF? Are you trying to replace production?')


    # drop and recreate database
    rootdb = mysql.connect(user=db['NAME'],
                           passwd=db['PASSWORD'])
    c = rootdb.cursor()
    try:
        c.execute('drop database %s' % db['NAME'])
    except:
        pass                              # ignore drop database errors
    c.execute('create database %s character set utf8 collate utf8_general_ci' % db['NAME'])
    c.close()
    rootdb.close()


    # now load the data. For that first gunzip it,
    # then run mysql in a subprocess
    unzipproc = subprocess.Popen(['gunzip', '--stdout', dbfile],
                                 stdout=subprocess.PIPE)
    mysqlproc = subprocess.Popen(['mysql', '-u', db['USER'],
                                  '--password=%s' % (db['PASSWORD'],),
                                  db['NAME']],
                                 stdin=unzipproc.stdout, stdout=subprocess.PIPE)
    unzipproc.stdout.close()
    mysqlproc.wait()


    # truncate the notifications
    # mydb = mysql.connect(user=db['USER'],
    #                     passwd=db['PASSWORD'],
    #                     db=db['NAME'])
    # mydb.cursor().execute('truncate table wcomments_enotify')

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--demo', action='store_true',
                    help='Prep db for demo after loading')
parser.add_argument('file', help='Dump of database')
parser.add_argument('-f', '--fixdemoscript',
                    default='scripts.pyfixtures.fix_demo',
                    help='dotted path for fix_demo script')
parser.add_argument('-n', '--no-syncdb',
                    action='store_true',
                    help='dont do syncdb or migrate')
args = parser.parse_args()

replace_db(args.file)

from django.core.management import setup_environ, ManagementUtility
setup_environ(settings)

if args.no_syncdb:
    cmds = []
else:
    cmds = [['syncdb'], ['migrate']]

if args.demo:
    cmds.append(['runcmd', args.fixdemoscript])
for cmd in cmds:
    utility = ManagementUtility([sys.argv[0]] + cmd)
    utility.execute()
