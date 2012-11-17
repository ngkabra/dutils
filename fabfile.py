'''Useful utilities for a fabfile.py

Specifically, includes webfaction apps.
Command categories (for automatic help generation).

To use, from dutils.fabfile import *
and then do the following:

from fabric.api import env
APPMAP.update(dict containing WFApps and a definition for "all")
env.apps = something, usually list(appmap("localhost"))
@cmd_category("Pre-defined App Groups")
def some_app_name():
    "Name of app"
    apps("app_name")
# more app_names
# call _compass with dir=<compass dir>
# call _jsgen with has_dajax=True|False, and dir=<js dir>
# rscript task for scripts directory
# specific tasks


# Scripts from dutils that it expects to find
dumpdb
dutils.jscombine (for jsgen)
dutils.replacedb

NOTE/WARNING: replacedb this will not work unless dutils is in the
<djangoproject> directory. i.e. dirname(dirname(__filename__)) should
contain manage.py

# Other Local setup expected
in <LOCAL>/fabfile.py:
  from fabric.api import env
  env.virtualenv = '~/.v/p27' # without trailing slash
  env.backups_dir = '~/Backups/websites' # without trailing slash

# Things that just work, if right things are installed
tags, jsgen, generate_static_dajaxice,
findmigs (== schemamigration <appname> --auto)
compass watch, celeryd, nosetests
shell_plus, runscript
'''

from collections import defaultdict
import inspect
from datetime import datetime
from functools import wraps
from itertools import chain
from os.path import expanduser
from shutil import move
from os import symlink
import re
import sys


from fabric.api import *

# see below for default value of env.apps

class App(object):
    def __init__(self, name, dir, projdir, python='python', prefix=None):
        self.name = name
        self.dir = dir
        self.projdir = projdir
        self.host = None
        self.python = python
        self.managepy = self.python + ' manage.py '
        self.prefix = prefix

    def __unicode__(self):
        return '{name}::{host}/{dir}'.format(name=self.name,
                                             host=self.host,
                                             dir=self.dir)


from os import getcwd
class LocalApp(App):
    def __init__(self, name='localhost', dir=getcwd(), projdir=getcwd()):
        virtualenv = env.virtualenv
        prefix = 'source {}/bin/activate'.format(virtualenv)
        super(LocalApp, self).__init__(name=name,
                                       dir=dir,
                                       projdir=projdir,
                                       prefix=prefix,
                                       )
        self.host = 'localhost'


class WFApp(App):
    @property
    def home(self):
        return '/home/{0}'.format(env.user)

    def __init__(self, name, host):
        dir = '{home}/webapps/{name}'.format(home=self.home,
                                             name=name)
        projdir = '{dir}/myproject'.format(dir=dir)
        super(WFApp, self).__init__(name=name,
                                    dir=dir,
                                    projdir=projdir,
                                    python='python2.7')
        self.host = 'navin@{h}.webfaction.com'.format(h=host)


APPMAP=dict(
    localhost=[LocalApp()],
    ALL=['localhost', 'remote'],
    local=['localhost'],
    # users should extend this by defining a bunch of
    # WFApps, and also 'all'
)


def appmap(app):
    if isinstance(app, App):
        return [app]
    return chain.from_iterable(appmap(a) for a in APPMAP[app])


def apps(*apps):
    env.apps = list(chain.from_iterable(appmap(a) for a in apps))


def ftask(projdir=False, apps=None, cmd_category=None):
    def dec(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for app in appmap(apps) if apps else env.apps:
                with settings(host_string=app.host,
                              app=app):
                    with cd(app.projdir if projdir else app.dir):
                        if app.prefix:
                            with prefix(app.prefix):
                                f(*args, **kwargs)
                        else:
                            f(*args, **kwargs)
        wrapper.cmd_category = cmd_category
        return wrapper
    return dec

def cmd_category(cat):
    def dec(f):
        f.cmd_category = cat
        return f
    return dec

wftask = ftask(cmd_category='Server commands')
projtask = ftask(projdir=True, cmd_category='Project commands')
localtask = ftask(projdir=True, apps='localhost', cmd_category='Local only')

def managepy(cmd):
    run(env.app.managepy + cmd)


@cmd_category('Pre-defined App Groups')
def all():
    '''All apps: rsdemo, rs, rsph'''
    apps('all')


@cmd_category('Local only')
def tags():
    '''Re-build tags table for emacs'''
    local('find . -name \*.html -o -name \*.py -o -name \*.sass | etags -')


@localtask
def findmigs(appname):
    '''schemamigration --auto for given {appname}'''
    managepy('schemamigration {0} --auto'.format(appname))


@localtask
def jsgen_(has_dajax=True, dir='base/static/js'):
    '''Generate and combine javascript files'''
    if has_dajax:
        managepy('generate_static_dajaxice > {}/dajaxice.js'.format(dir))
    run('python dutils/jscombine.py -d {}'.format(dir))


def compass_(dir='base/static'):
    '''Run compass watch'''
    local('cd {} && compass watch'.format(dir))


@localtask
def celery():
    '''Run celery'''
    managepy('celeryd -l info')


@wftask
def ls():
    '''Run ls'''
    run('ls')


@wftask
def pwd():
    '''Run pwd'''
    run('pwd')


@projtask
def serve():
    '''Run manage.py runserver'''
    managepy('runserver_plus')


def nose_opts():
    try:
        import pinocchio
    except ImportError:
        return []
    return ['--with-stopwatch']

def test_cmd():
    '''Test command'''
    return 'test ' + ' '.join(nose_opts())

@projtask
def testfailed(options=''):
    '''test with --failed {options}'''
    managepy('{} --failed {}'.format(test_cmd(), options))


@projtask
def test(options=''):
    '''run managepy test with {options}'''
    managepy('{} {}'.format(test_cmd(), options))

@projtask
def quicktest(seconds=5):
    '''run only tests faster than seconds seconds'''
    managepy('{cmd} --faster-than{seconds} {opts}'.format(cmd=test_cmd(),
                                                          seconds=seconds))

@projtask
def shell():
    '''Shell plus'''
    managepy('shell_plus')


@projtask
def dbshell():
    '''dbshell'''
    managepy('dbshell')


def _dumpdb(dest_file=None):
    if dest_file:
        managepy('dumpdb --output {}'.format(dest_file))
    else:
        managepy('dumpdb')


@projtask
def dumpdb(dest_file=None):
    '''dumpdb'''
    _dumpdb(dest_file)


def _dumpmedia(dest_file=None):
    if dest_file:
        managepy('dumpmedia --output {}'.format(dest_file))
    else:
        managepy('dumpmedia')


@projtask
def dumpmedia(dest_file=None):
    '''dump site_media into project-media.gz'''
    _dumpmedia(dest_file)


def app_to_dbfilename(app):
    return '~/{}.sql.gz'.format(app.name)

def app_to_mediafilename(app):
    return '~/{}-media.gz'.format(app.name)

def move_and_link(src, dest):
    move(src, dest)
    symlink(dest, src)


@projtask
def getdbonly(db_dest_file=None):
    '''Get db (no media) from projects and place them in env.backups_dir & ~'''
    db_dest_file = db_dest_file or app_to_dbfilename(env.app)
    _dumpdb(db_dest_file)
    get(db_dest_file, db_dest_file)
    move_and_link(expanduser(db_dest_file),
                  expanduser(
                      '{}/{}/db{}.sql.gz'.format(
                          env.backups_dir,
                          env.app.name,
                          datetime.now().strftime('%d%b%Y'))))

@projtask
def getmediaonly(db_dest_file=None, media_dest_file=None):
    '''Get media (no db) from projects and place them env.backups_dir & ~'''
    media_dest_file = media_dest_file or app_to_mediafilename(env.app)
    _dumpmedia(media_dest_file)
    get(media_dest_file, media_dest_file)
    move_and_link(expanduser(media_dest_file), expanduser(
        '{}/{}/media{}.gz'.format(
            env.backups_dir,
            env.app.name,
            datetime.now().strftime('%d%b%Y'))))


@cmd_category('Local only')
def getreplacedb(dbonly=None, mediaonly=None):
    '''Get db from remote replace local db. Dont fix demo'''
    if dbonly and mediaonly:
        abort('Cant specify both flags')

    if len(env.apps) != 1:
        abort('What is wrong with you?')
    if not mediaonly:
        getdbonly()

    if not dbonly:
        getmediaonly()

    db_filename = app_to_dbfilename(env.apps[0])
    media_filename = app_to_mediafilename(env.apps[0])
    apps('localhost')

    if not mediaonly:
        replacedb(db=db_filename, demo=False)
    if not dbonly:
        replacemedia(mediafile=media_filename)

@cmd_category('Local only')
def getreplacedbonly():
    '''Get db (no media) and replace'''
    getreplacedb(dbonly=True)

@cmd_category('Local only')
def getreplacedball():
    '''Get db and media and replace'''
    getreplacedb(dbonly=True)



@projtask
def replacedb(db, demo=None):
    'Replace db with {db}. {demo}=True will fix_demo. Does not replacemedia'
    if not 'local' in env.app.name and not 'demo' in env.app.name:
        abort('WTF?! Trying to replace production? [{}]'.format(env.app.name))
    run(env.app.python + ' dutils/replacedb.py {demo} {db}'.format(
        demo='-d' if demo else '',
        db=db))

@projtask
def replacemedia(mediafile):
    '''Replace site_media with {mediafile}.'''
    if not 'local' in env.app.name and not 'demo' in env.app.name:
        abort('WTF?! Trying to replace production? [{}]'.format(env.app.name))
    run('tar -xvzf {}'.format(mediafile))

def runscript_(script):
    managepy('runscript {0}'.format(script))

@projtask
def runscript(script):
    '''manage.py runscript {script}'''
    runscript_(script)

@projtask
def push():
    '''git push. Is this really needed?'''
    run('git push')


def _pull():
    run('git pull')

def _submodule_update():
    run('git submodule update')

def _migrate(apps=''):
    '''Here, apps are django apps, not fab apps'''
    managepy('migrate -v 0 {}'.format(apps))

def _syncdb():
    managepy('syncdb')

@projtask
def syncdb():
    '''syncdb'''
    _syncdb()


def _media(link=None):
    '''upgrade the media - do collectstatic'''
    cmd = 'collectstatic --noinput'
    if link is None:
        link = env.app.host == 'localhost'
    if link:
        cmd += ' --link'
    managepy(cmd)


def _restart():
    with cd(env.app.dir):
        run('./apache2/bin/restart')


@projtask
def pull():
    '''git pull'''
    _pull()


@projtask
def migrate(apps=''):
    '''migrate {apps}'''
    _migrate(apps)


@projtask
def media(link=None):
    '''collectstatic. Automatically determines --links. Or use {link}'''
    _media(link)


@projtask
def restart():
    '''restart apache'''
    _restart()


@projtask
def upgrade():
    '''pull, syncdb, migrate, media, restart.'''
    execute(_pull)
    execute(_submodule_update)
    execute(_syncdb)
    execute(_migrate)
    execute(_media)
    execute(_restart)

@projtask
def cmd(c):
    '''Run command {c} in project directory'''
    run(c)


@wftask
def rcmd(c):
    '''Run command {c} in server home directory'''
    run(c)


@projtask
def mcmd(c):
    '''manage.py {c} - at remote'''
    managepy(c)


@wftask
def wfinstall(package):
    'Install package on webfaction machine'
    run('easy_install-2.7 {}'.format(package))


def help(func=None, cat=None):
    '''Print a nice list of fab commands'''
    flist = defaultdict(list)
    for n, f in inspect.getmembers(sys.modules[__name__],
                                   inspect.isfunction):
        cmd_category = getattr(f, 'cmd_category', None)
        if cmd_category:
            if cat and not re.search(cat, cmd_category, re.I):
                continue
            if func and not (re.search(func, n, re.I) or
                             re.search(func, f.__doc__, re.I)):
                continue
            flist[cmd_category].append(f)

    for c, funcs in flist.iteritems():
        print '{}:'.format(c)
        for f in funcs:
            if f.__doc__:
                doc = f.__doc__.replace('\n', '    \n')
            else:
                doc = 'Lazy bum. No __doc__ for {f.__name__}'.format(f=f)
            print '    {f.__name__}: {doc}'.format(f=f, doc=doc)
