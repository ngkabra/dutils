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
# call compass_ with dir=<compass dir>
# rscript task for scripts directory
# specific tasks

# Scripts from dutils that it expects to find
dumpdb
dutils.replacedb

NOTE/WARNING: replacedb this will not work unless dutils is in the
<djangoproject> directory. i.e. dirname(dirname(__filename__)) should
contain manage.py

# Other Local setup expected
in <LOCAL>/fabfile.py:
  from fabric.api import env
  env.virtualenv = '~/.v/p27' # without trailing slash
  env.backups_dir = '~/Backups/websites' # without trailing slash
  env.new_migrations = True # for django1.7 or above

# Things that just work, if right things are installed
tags,
findmigs (== schemamigration <appname> --auto)
compass compile, celeryd, nosetests
shell_plus, runscript
'''

from collections import defaultdict
import inspect
from datetime import datetime
from functools import wraps
from itertools import chain
from os.path import expanduser, lexists, join, dirname
from shutil import move
from os import symlink, remove
from os import getcwd
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


class LocalApp(App):
    def __init__(self, name='localhost', dir=getcwd(), projdir=getcwd()):
        venv = env.virtualenv
        prefix = 'source {}/bin/activate'.format(venv) if venv else ''
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

    def __init__(self, name, host,
                 proj_subdir='myproject',
                 python='python2.7'):
        dir = '{home}/webapps/{name}'.format(home=self.home,
                                             name=name)
        projdir = '{dir}/{subdir}'.format(dir=dir,
                                          subdir=proj_subdir)
        super(WFApp, self).__init__(name=name,
                                    dir=dir,
                                    projdir=projdir,
                                    python=python)
        self.host = 'navin@{h}.webfaction.com'.format(h=host)


APPMAP = dict(
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
    return run(env.app.managepy + cmd)


@cmd_category('Pre-defined App Groups')
def all():
    '''All apps: rsdemo, rs, rsph'''
    apps('all')


@cmd_category('Local only')
def tags():
    '''Re-build tags table for emacs'''
    local('find . -path "*migrations" -prune -o -name \*.html '
          '-print -o -name \*.py -print -o -name \*.sass -print | etags -')


@localtask
def findmigs(appname=''):
    '''schemamigration --auto for given {appname}'''
    if env.new_migrations:
        managepy('makemigrations {}'.format(appname))
    else:
        managepy('schemamigration {0} --auto'.format(appname))


def compass_(dir='base/static'):
    '''Run compass compile'''
    local('cd {} && compass compile'.format(dir))


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
        managepy('dumpdb --output={}'.format(dest_file))
    else:
        managepy('dumpdb')


@projtask
def dumpdb(dest_file=None):
    '''dumpdb'''
    _dumpdb(dest_file)


def _dumpmedia(dest_file=None):
    '''Not used anymore: we use rsync now'''
    if dest_file:
        managepy('dumpmedia --output {}'.format(dest_file))
    else:
        managepy('dumpmedia')


@projtask
def dumpmedia(dest_file=None):
    '''dump site_media into project-media.gz

    Not used anymore: we use rsync now'''
    _dumpmedia(dest_file)


def app_to_dbfilename(app):
    return '~/u/{}.sql.gz'.format(app.name)


def app_to_mediafilename(app):
    '''Not used anymore: we use rsync now'''
    return '~/u/{}-media.gz'.format(app.name)


def move_and_link(src, dest):
    move(src, dest)
    symlink(dest, src)


@projtask
def getdbonly(db_dest_file=None):
    '''Get db (no media) from projects and place them in env.backups_dir & ~'''
    db_dest_file = db_dest_file or app_to_dbfilename(env.app)
    _dumpdb(db_dest_file)
    local_db_dest_file = expanduser(db_dest_file)
    if lexists(local_db_dest_file):
        remove(local_db_dest_file)
        # otherwise get tries to overwrite the linked file!
    get(db_dest_file, local_db_dest_file)
    move_and_link(local_db_dest_file,
                  expanduser(
                      '{}/{}/db{}.sql.gz'.format(
                          env.backups_dir,
                          env.app.name,
                          datetime.now().strftime('%d%b%Y'))))


@projtask
def getmediaonly(db_dest_file=None, media_dest_file=None):
    '''Get media (no db) from projects and place them env.backups_dir & ~'''
    backup_dir = '{env.backups_dir}/{env.app.name}'.format(env=env)

    media_dir = managepy('mediadir')
    media_src = '{env.app.host}:{media_dir}'.format(
        env=env,
        media_dir=media_dir)
    media_dest = backup_dir + '/media/'
    media_zip = '{backup_dir}/media{timestamp}.tgz'.format(
        backup_dir=backup_dir,
        timestamp=datetime.now().strftime('%d%b%Y'))

    local("rsync -avz -e ssh {media_src} {media_dest}".format(
            media_src=media_src,
            media_dest=media_dest))

    local("tar -cvzf {media_zip} --directory {media_dest} .".format(
            media_zip=media_zip,
            media_dest=media_dest))
    local("rm -rf site_media")
    local("ln -s {}site_media/ site_media".format(media_dest))
    local("ln -f -s {media_zip} {home_zip}".format(
            media_zip=media_zip,
            home_zip=expanduser('~/u/{}-media.tgz'.format(
                    env.app.name))))


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
    apps('localhost')
    if not mediaonly:
        replacedb(db=db_filename, demo=False)
    # no replacemedia since we use rsync


@cmd_category('Local only')
def getreplacedbonly():
    '''Get db (no media) and replace'''
    getreplacedb(dbonly=True)


@cmd_category('Local only')
def getreplacedball():
    '''Get db and media and replace'''
    getreplacedb(dbonly=True)


@projtask
def replacedb(db, demo=None, nosync=None, verbose=None):
    'Replace db with {db}. {demo}=True will fix_demo. Does not replacemedia'
    if 'local' not in env.app.name and 'demo' not in env.app.name:
        abort('WTF?! Trying to replace production? [{}]'.format(env.app.name))
    replacedb_path = join(dirname(__file__), 'replacedb.py')
    args = ''
    if env.project_path:
        args += ' -p ' + ' '.join(env.project_path)
    if env.django_settings_module:
        args += ' -s ' + env.django_settings_module
    if demo:
        args += ' -D'
    if nosync:
        args += ' -n'
    args += ' -- ' + db
    run('{python} {replacedb} {args}'.format(python=env.app.python,
                                             replacedb=replacedb_path,
                                             args=args))


@projtask
def replacemedia(mediafile):
    '''Not used anymore - we use rsync

    Replace site_media with {mediafile}.'''
    if 'local' not in env.app.name and 'demo' not in env.app.name:
        abort('WTF?! Trying to replace production? [{}]'.format(env.app.name))
    run('tar -xvzf {}'.format(mediafile))


def runscript_(script):
    managepy('runcmd {0}'.format(script))


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


@projtask
def fakeinit_migs():
    'Re-initialize migrations after resetmigs'
    execute(_pull)
    execute(_submodule_update)
    managepy('runcmd scripts.resetmigs fakeinit_migs')


def _migrate(apps=''):
    '''Here, apps are django apps, not fab apps'''
    managepy('migrate -v 0 {}'.format(apps))


def _syncdb():
    '''Don't run syncdb if we are on django1.7 or above'''
    if not env.new_migrations:
        managepy('syncdb')


@projtask
def syncdb():
    '''syncdb'''
    _syncdb()


def _media():
    '''upgrade the media - do collectstatic'''
    cmd = 'collectstatic --noinput'
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
def media():
    '''manage.py collectstatic.'''
    _media()


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
