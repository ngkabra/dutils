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
from os.path import dirname
import sys
import subprocess
import MySQLdb as mysql

# first set path appropriately so settings can be loaded
topdir = dirname(dirname(__file__))
sys.path.insert(0, topdir)

import settings

def replace_db(dbfile):
    db = settings.DATABASES['default']

    # sanity check
    if db['NAME'] in ('navin_rs', 'navin_rsph'):
        raise Exception('WTF? Are you trying to replace production?')


    # drop and recreate database
    rootdb = mysql.connect(user=db['NAME'],
                           passwd=db['PASSWORD'])
    c = rootdb.cursor()
    c.execute('drop database %s' % db['NAME'])
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
args = parser.parse_args()

replace_db(args.file)

if args.demo:
  from django.core.management import setup_environ, ManagementUtility
  setup_environ(settings)
  for cmd in [['syncdb'],
               ['migrate'],
               ['runscript', 'scripts.pyfixtures.fix_demo']]:
      utility = ManagementUtility([sys.argv[0]] + cmd)
      utility.execute()
