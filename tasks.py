from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

from datetime import datetime
from invoke import task
from os import symlink, remove
from os.path import expanduser, join, dirname, lexists


class BaseConfig():
    def __init__(self, context, *args, **kwargs):
        self.context = context

    def get_key(self):
        return getattr(self.context, 'original_host', 'localhost')

    @property
    def mapper(self):
        return self.context.mapper.get(self.get_key(), {})

    @property
    def lmapper(self):
        '''mapper for localhost: special case of above'''
        return self.context.mapper.get('localhost', {})

    @property
    def home(self):
        return self.mapper.get('home', '/home/navin')

    @property
    def lhome(self):
        return self.lmapper.get('home', '/home/navin')

    @property
    def project(self):
        '''Defaults to original_host'''
        return self.mapper.get('project', self.get_key())

    @property
    def lproject(self):
        '''Defaults to project'''
        return self.lmapper.get('project', self.project)

    @property
    def venv(self):
        '''defaults to project'''
        return self.mapper.get('venv', self.project)

    @property
    def lvenv(self):
        '''defaults to lproject'''
        return self.lmapper.get('venv', self.lproject)

    @property
    def managepy_subdir(self):
        return getattr(self.context, 'managepy_subdir', '')

    @property
    def backups_dir(self):
        return getattr(self.context, 'backups_dir',
                       expanduser('~/Backups/websites'))


class DjangoConfig(BaseConfig):
    @property
    def projdir(self):
        '''Directory for git commands'''
        raise NotImplementedError

    @property
    def python(self):
        raise NotImplementedError

    @property
    def managepydir(self):
        if self.managepy_subdir:
            return join(self.projdir, self.managepy_subdir)
        else:
            return self.projdir

    @property
    def proj_backup_dir(self):
        return join(self.backups_dir, self.project)


    def backup_file(self, relpath):
        return join(self.proj_backup_dir, relpath)

    def timestamped_backup_file(self, prefix, ext):
        timestamp = datetime.now().strftime('%d%b%Y')
        return self.backup_file(prefix + timestamp + ext)

    @property
    def media_backup_dir(self):
        return self.backup_file('media')

    @property
    def dumpdb_relfile(self):
        return join('u', self.project + '.sql.gz')

    @property
    def mediagz_file(self):
        return join(self.lhome, 'u', self.project + '-media.tgz')

    @property
    def mediagz_tsfile(self):
        return self.timestamped_backup_file('media', '.tgz')

    @property
    def project_path(self):
        '''Used currently for replacedb

        Except for twit6, others have only one element in this list
        '''
        return list(set([self.projdir, self.managepydir]))

    @property
    def restart_commands(self):
        raise NotImplementedError


class WFConfig(DjangoConfig):
    @property
    def projdir(self):
        return join(self.home, 'webapps', self.project, 'myproject')

    @property
    def python(self):
        return join(self.home, '.v', self.venv, 'bin', 'python')

    @property
    def restart_commands(self):
        return [join(self.home, 'webapps', self.project,
                     'apache2', 'bin', 'restart')]


class OpalConfig(DjangoConfig):
    @property
    def projdir(self):
        return join(self.home, 'apps', self.project, 'myproject')

    @property
    def python(self):
        return join(self.home, 'apps', self.project, 'env', 'bin', 'python')
    
    @property
    def restart_commands(self):
        return [join(self.home, 'apps', self.project, 'stop'),
                join(self.home, 'apps', self.project, 'start')]


class LocalConfig(DjangoConfig):
    @property
    def projdir(self):
        return join(self.lhome, self.lproject)

    @property
    def python(self):
        return join(self.lhome, '.v', self.lvenv, 'bin', 'python')

    def lrun(self, cmd, *args, **kwargs):
        try:
            return self.context.local(cmd, *args, **kwargs)
        except AttributeError:
            if getattr(self.context, 'host', 'localhost') != 'localhost':
                raise Exception('This is a local-only command')
            return self.context.run(cmd, *args, **kwargs)


def autoconfig(c):
    c.lconfig = LocalConfig(c)
    hoststr = getattr(c, 'host', 'localhost')

    if 'webfaction' in hoststr:
        c.rconfig = WFConfig(c)
    elif 'opalstack' in hoststr:
        c.rconfig = OpalConfig(c)
    elif 'localhost' in hoststr:
        c.rconfig = c.lconfig
    else:
        raise Exception('Unknown host: {}'.format(c.host))


@task
def test(c, dir=None):
    autoconfig(c)
    print('projdir is', c.rconfig.projdir)
    print('hostname is ', end='')
    c.run('hostname')
    print('pwd is ', end='')
    c.run('pwd')
    print('home is', c.rconfig.home)
    print('project is', c.rconfig.project)


@task
def restart(c):
    autoconfig(c)
    for cmd in c.rconfig.restart_commands:
        c.run(cmd, echo=True)


@task
def managepy(c, command, local=False):
    '''Run managepy. Remote by default, but locally if local=True'''
    autoconfig(c)
    cfg = c.lconfig if local else c.rconfig
    runner = cfg.lrun if local else c.run
    with c.cd(cfg.managepydir):
        result = runner("{python} manage.py {command}".format(
            python=cfg.python, command=command), echo=True)
        return result.stdout


@task
def dumpdb(c, dest_file):
    autoconfig(c)
    managepy(c, 'dumpdb --output={}'.format(dest_file))


@task
def dumpmedia(c, dest_file=None):
    autoconfig(c)
    media_rdir = managepy(c, 'mediadir').strip()
    rsync_src = '{host}:{media_rdir}'.format(host=c.host, media_rdir=media_rdir)
    rsync_dest = c.rconfig.media_backup_dir
    mediagz_tsfile = c.rconfig.mediagz_tsfile
    
    c.local("rsync -avz -e ssh {rsync_src} {rsync_dest}".format(
        rsync_src=rsync_src,
        rsync_dest=rsync_dest), echo=True)

    # tar.gz the media for backup purposes
    # do this in the background because it takes a long time
    c.local("tar -czf {mediagz_tsfile} --directory {rsync_dest} .".format(
        mediagz_tsfile=mediagz_tsfile,
        rsync_dest=rsync_dest), disown=True, echo=True)
    site_media_symlink = join(c.lconfig.managepydir, 'site_media')
    if lexists(site_media_symlink):
        remove(site_media_symlink)
    symlink('{rsync_dest}/site_media'.format(rsync_dest=rsync_dest),
            site_media_symlink)
    local_mediagz = c.rconfig.mediagz_file
    if lexists(local_mediagz):
        remove(local_mediagz)
    symlink(mediagz_tsfile, local_mediagz)


@task
def getdbonly(c):
    autoconfig(c)
    dumpdb_relfile = c.rconfig.dumpdb_relfile
    rdumpdb_file = join(c.rconfig.home, dumpdb_relfile)
    dumpdb(c, rdumpdb_file)
    ldumpdb_tsfile = c.rconfig.timestamped_backup_file('db', '.sql.gz')
    
    # soft link appropriately
    ldumpdb_file = join(c.rconfig.lhome, dumpdb_relfile)
    if lexists(ldumpdb_file):
        remove(ldumpdb_file)
    print('Getting {}'.format(dumpdb_relfile))
    c.get(rdumpdb_file, ldumpdb_tsfile)
    symlink(ldumpdb_tsfile, ldumpdb_file)
    return ldumpdb_file


@task
def runcmd(c, script, args=''):
    '''
    Call managepy::runcmd with args as a comma-separated arg list

    remember: managepy::runcmd runs a standalone script with django initialized
    This is not to run a managepy django command
    managepy::runcmd expects arguments of the form a0 a1 kw1=kwarg1 etc

    This runcmd takes same arguments but comma separated
    fab -H rsh runcmd scripts.needs_attention a1,a2,kw1=kwarg1,kw2=kwarg2
    '''
    autoconfig(c)
    managepy(c, command='runcmd {} {}'.format(script,
                                              ' '.join(args.split(','))))


@task
def gitpull(c):
    autoconfig(c)
    with c.cd(c.rconfig.projdir):
        c.run('git pull')


@task
def collectstatic(c):
    autoconfig(c)
    managepy(c, 'collectstatic --noinput')


@task
def upgrade_no_restart(c):
    autoconfig(c)
    with c.cd(c.rconfig.projdir):
        c.run('git pull')
        c.run('git submodule update')

    managepy(c, 'migrate -v 0')
    managepy(c, 'collectstatic --noinput')


@task
def upgrade(c):
    autoconfig(c)
    upgrade_no_restart(c)
    restart(c)
    

@task
def getdb(c, nomigs=False):
    # getdbonly will do autoconfig
    dbfile = getdbonly(c)
    dumpmedia(c)
    replacedb(c, dbfile, nomigs=nomigs)


def forcelocal(c):
    autoconfig(c)
    if 'localhost' not in c.host:
        raise Exception('This is a local-only task')


@task
def tags(c):
    '''Re-build tags table for emacs'''
    forcelocal(c)
    with(c.cd(c.lconfig.projdir)):
        c.run('find . -path "*migrations" -prune '
              '-o -name \*.html -print '
              '-o -name \*.py -print '
              '-o -name \*.js -print '
              '-o -name \*.sass -print '
              '| etags -')
        c.run('find . -path ./autoevals -prune -path "*migrations" -prune '
              '-o -name \*.html -print '
              '-o -name \*.py -print '
              '-o -name \*.js -print '
              '-o -name \*.sass -print '
              '| etags -o TAGS_NOEVALS -')
        c.run('find . -path "*migrations" -prune '
              '-o -name \*.py -print '
              '-o -name \*.sass -print '
              '| etags -o TAGS_NOHTMLNOJS -')
        c.run('find . -path ./autoevals -prune -path "*migrations" -prune '
              '-o -name \*.js -print '
              '-o -name \*.sass -print '
              '-o -name \*.html -print '
              '| etags -o TAGS_ONLYJSHTML -')
        c.run('find . -path ./autoevals -prune -path "*migrations" -prune '
              '-o -name \*.py -print '
              '-o -name \*.sass -print '
              '| etags -o TAGS_ONLYPY -')
        c.run('find . -path ./autoevals -prune -path "*migrations" -prune '
              '-o -name \*.py -print '
              '-o -name \*.html -print '
              '-o -name \*.sass -print '
              '| etags -o TAGS_ONLYPYHTML -')


@task
def findmigs(c, appname=''):
    '''find migrations'''
    forcelocal(c)
    managepy(c, 'makemigrations {appname}'.format(appname=appname))


@task
def migrate(c, appname=''):
    '''apply migrations'''
    forcelocal(c)
    managepy(c, 'migrate -v 0 {appname}'.format(appname=appname))


@task
def compass(c, compass_directory='base/static'):
    forcelocal(c)
    c.run('cd {} && compass compile'.format(compass_directory))


@task
def regevals(c, company=None):
    '''register evaluators for company (or all companies if None)'''
    forcelocal(c)
    company_arg = company or "reliscore"
    managepy(c, "register_evaluators -f -c {}".format(company_arg))


@task
def force_copysearch(c):
    managepy(c, 'index_solutions')
    managepy(c, 'copy_search')


@task
def precompute_attention(c):
    managepy(c, 'precompute_attention')


@task
def replacedb(c, dbfile=None, nomigs=False, verbose=False):
    '''Replace db

    nomigs: don't run migrations
    '''
    autoconfig(c)
    dbfile = dbfile or c.rconfig.project
    replacedb_path = join(dirname(__file__), 'replacedb.py')
    args = ''
    args += ' -p ' + ' '.join(c.lconfig.project_path)
    if getattr(c, 'django_settings_module', None):
        '''Unused?'''
        args += ' -s ' + c.django_settings_module
    if nomigs:
        args += ' -n'
    if verbose:
        args += ' -d'
    args += ' -v'
    args += ' -- ' + dbfile
    cmd = '{python} {replacedb} {args}'.format(
        python=c.lconfig.python, replacedb=replacedb_path, args=args)

    with c.cd(c.lconfig.projdir):
        c.lconfig.lrun(cmd, echo=True)
