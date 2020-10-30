from datetime import datetime
from invoke import Collection, task
from os import symlink, remove
from os.path import expanduser, join, dirname, lexists
import shutil


class LocalConfig():
    def __init__(self, c):
        self.lproject = c.lproject or 'rs'
        self.lhome = getattr(c, 'lhome', expanduser('~'))
        self.lvenv = getattr(c, 'lvenv', self.lproject)
        self.backups_dir = expanduser(
            getattr(c, 'backups_dir', '~/Backups/websites'))
        self.project_path = c.project_path
        self.lpython = join(self.lhome, '.v', self.lvenv, 'bin', 'python')

    @property
    def lappdir(self):
        '''The directory for git commands'''
        return join(self.lhome, self.lproject)

    @property
    def lprojdir(self):
        '''The directory for git commands'''
        return self.lappdir

    def proj_backup_path(self, rproj, relpath):
        return join(self.backups_dir, rproj, relpath)

    def timestamped_backup_filename(self, rproj, prefix, ext):
        timestamp = datetime.now().strftime('%d%b%Y')
        return self.proj_backup_path(rproj, prefix + timestamp + ext)

    def media_backup_dir(self, rproj):
        self.proj_backup_path(rproj, 'media')


class RemoteConfig():
    def __init__(self, hostmap):
        self.rproject = hostmap['rproject']
        self.rhome = hostmap.get('rhome', '/home/navin')
        self.rvenv = hostmap.get('rvenv', self.rproject)
        
    @property
    def rappdir(self):
        raise Exception('rappdir not set')

    @property
    def rpython(self):
        raise Exception('rpython not set')

    @property
    def rprojdir(self):
        '''The directory for git commands'''
        return join(self.rappdir, 'myproject')

    @property
    def managepydir(self):
        '''The directory that has manage.py

        Usually same as rprojdir, except for twit6
        '''
        return self.rprojdir

    @property
    def dumpdb_relfile(self):
        return join('u', self.rproject + '.sql.gz')

    @property
    def mediagz_relfile(self):
        return join('u', self.rproject + '-media.tgz')
        

class WFConfig(RemoteConfig):
    @property
    def rappdir(self):
        return join(self.rhome, 'webapps', self.rproject)

    @property
    def rpython(self):
        return join(self.rhome, '.v', self.rvenv, 'bin', 'python')

    @property
    def restart_commands(self):
        return [join(self.rappdir, 'apache2', 'bin', 'restart')]


class OpalConfig(RemoteConfig):
    @property
    def rappdir(self):
        return join(self.rhome, 'apps', self.rproject)
    
    @property
    def envdir(self):
        return join(self.rappdir, 'env')

    @property
    def rpython(self):
        return join(self.envdir, 'bin', 'python')

    @property
    def restart_commands(self):
        return [join(self.envdir, 'stop'), join(self.envdir, 'start')]


class LocalRConfig(RemoteConfig):
    def __init__(self, lconfig, *args, **kwargs):
        self.orig_lconfig = lconfig
        super(LocalRConfig, self).__init__(
            dict(rproject=lconfig.lproject,
                 rhome=lconfig.lhome,
                 rvenv=lconfig.lvenv),
            *args, **kwargs)

    @property
    def rappdir(self):
        return self.orig_lconfig.lappdir

    @property
    def rpython(self):
        return join(self.rhome, '.v', self.rvenv, 'bin', 'python')

    @property
    def rprojdir(self):
        return self.rappdir

    @property
    def restart_commands(self):
        raise Exception('local restart not implemented')
    


@task
def autoconfig(c):
    c.lconfig = LocalConfig(c)
    try:
        hoststr = c.host
    except AttributeError:
        hoststr = 'localhost'

    if 'webfaction' in hoststr:
        c.rconfig = WFConfig(c.hostmap[c.original_host])
    elif 'opalstack' in hoststr:
        c.rconfig = OpalConfig(c.hostmap[c.original_host])
    elif 'localhost' in hoststr:
        c.rconfig = LocalRConfig(lconfig=c.lconfig)
    else:
        raise Exception('Unknown host: {}'.format(c.host))


@task
def test(c, dir=None):
    autoconfig(c)
    print('rappdir is', c.rappdir)
    c.run('hostname')
    c.run('pwd')


@task
def restart(c):
    autoconfig(c)
    for cmd in c.rconfig.restart_commands:
        c.run(cmd, echo=True)


@task
def managepy(c, command):
    autoconfig(c)
    with c.cd(c.rconfig.managepydir):
        result = c.run("{rpython} manage.py {command}".format(
            rpython=c.rconfig.rpython, command=command), echo=True)
        return result.stdout


@task
def dumpdb(c, dest_file):
    autoconfig(c)
    managepy(c, 'dumpdb --output={}'.format(dest_file))


@task
def dumpmedia(c, dest_file=None):
    autoconfig(c)
    mediadir = managepy(c, 'mediadir').strip()
    mediasrc = '{host}:{mediadir}'.format(host=c.host, mediadir=mediadir)
    mediadest = c.lconfig.media_backup_dir(c.rconfig.rproject)
    mediazip = c.lconfig.timestamped_backup_filename(
        c.rconfig.rproject, 'media', '.tgz')
    
    c.local("rsync -avz -e ssh {mediasrc} {mediadest}".format(
        mediasrc=mediasrc,
        mediadest=mediadest), echo=True)
    # tar.gz the media for backup purposes
    # do this in the background because it takes a long time
    c.local("tar -czf {mediazip} --directory {mediadest} .".format(
        mediazip=mediazip,
        mediadest=mediadest), disown=True, echo=True)
    if lexists('site_media'):
        remove('site_media')
    symlink('{mediadest}/site_media'.format(mediadest=mediadest),
            'site_media')
    local_mediagz = join(c.lconfig.lhome, c.rconfig.mediagz_relfile)
    if lexists(local_mediagz):
        remove(local_mediagz)
    symlink(mediazip, local_mediagz)


@task
def getdbonly(c):
    autoconfig(c)
    dumpdb_relfile = c.rconfig.dumpdb_relfile
    rdumpdb_file = join(c.rconfig.rhome, dumpdb_relfile)
    dumpdb(c, rdumpdb_file)
    ldumpdb_ts = c.lconfig.timestamped_backup_filename(
        c.rconfig.rproject, 'db', '.sql.gz')

    # soft link appropriately
    ldumpdb_file = join(c.lconfig.lhome, dumpdb_relfile)
    if lexists(ldumpdb_file):
        remove(ldumpdb_file)
    print('Getting {}'.format(dumpdb_relfile))
    c.get(rdumpdb_file, ldumpdb_ts)
    symlink(ldumpdb_ts, ldumpdb_file)
    return ldumpdb_file


@task
def runscript(c, script, *args, **kwargs):
    autoconfig(c)
    managepy(c, command='runcmd {} {} {}'.format(
        script, ' '.join(args),
        ' '.join('{}={}'.format(k, v) for k, v in kwargs.items())))


@task
def upgrade(c):
    autoconfig(c)
    with c.cd(c.rconfig.rprojdir):
        c.run('git pull')
        c.run('git submodule update')

    managepy(c, 'migrate -v 0')
    managepy(c, 'collectstatic --noinput')
    restart(c)
    

@task
def getdb(c):
    # getdbonly will do autoconfig
    dbfile = getdbonly(c)
    dumpmedia(c)
    replacedb(c, dbfile)


def forcelocal(c):
    autoconfig(c)
    try:
        if 'localhost' not in c.host:
            raise Exception('This is a local-only task')
    except AttributeError:
        pass


@task
def tags(c):
    '''Re-build tags table for emacs'''
    forcelocal(c)
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
    managepy(c, 'schemamigration {appname}'.format(appname=appname))


@task
def compass(c):
    forcelocal(c)
    compass_directory = 'base/static'
    c.run('cd {} && compass compile'.format(compass_directory))


@task
def regevals(c, company=None):
    '''register evaluators for company (or all companies if None)'''
    autoconfig(c)
    forcelocal(c)
    company_arg = company or "reliscore"
    managepy(c, "register_evaluators -f -c {}".format(company_arg))


@task
def replacedb(c, dbfile, nomigs=False, verbose=False):
    '''Replace db

    nomigs: don't run migrations
    TODO: dbfile shouldn't be a required parameter; guess from c
    '''
    autoconfig(c)
    replacedb_path = join(dirname(__file__), 'replacedb.py')
    args = ''
    args += ' -p ' + ' '.join(c.lconfig.project_path)
    if c.config.get('django_settings_module'):
        '''Unused?'''
        args += ' -s ' + c.django_settings_module
    if nomigs:
        args += ' -n'
    if verbose:
        args += ' -d'
    args += ' -v'
    args += ' -- ' + dbfile
    cmd = '{python} {replacedb} {args}'.format(
        python=c.lconfig.lpython, replacedb=replacedb_path, args=args)

    with c.cd(c.lconfig.lprojdir):
        try:
            c.local(cmd, echo=True)
        except AttributeError:
            forcelocal(c)
            c.run(cmd, echo=True)
