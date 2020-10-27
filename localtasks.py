from invoke import Collection, task
from invoke.context import Context
from shutil import move
from os import symlink
from os.path import join, dirname

from . import djtasks

@task
def autoconfig(c, force=False):
    if force or not c.config.get('project'):
        c['project'] = 'rs'
    if force or not c.config.get('venv'):
        c['venv'] = c.project

    if force:
        c['host'] = None
        c['original_host'] = None

    c['home'] = '/home/navin'
    c['wfdir'] = None
    c['projdir'] = '{home}/{project}'.format(home=c.home, project=c.project)
    c['python'] = '{home}/.v/{venv}/bin/python'.format(home=c.home, venv=c.venv)


def local_context(c):
    local_ctx = Context(c.config)
    autoconfig(local_ctx, force=True)
    return local_ctx
    

@task
def forcelocal(c):
    autoconfig(c)
    try:
        if c.host:
            raise Exception('Local command attempted on remote')
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
def managepy(c, command):
    forcelocal(c)
    djtasks.managepy(c, command)


@task
def findmigs(c, appname=''):
    '''find migrations'''
    forcelocal(c)
    djtasks.managepy(c, 'schemamigration {appname}'.format(appname=appname))


@task
def compass(c):
    forcelocal(c)
    compass_directory = 'base/static'
    c.run('cd {} && compass compile'.format(compass_directory))


@task
def regevals(c, company=None):
    '''register evaluators for company (or all companies if None)'''
    forcelocal(c)
    company_arg = company or "reliscore"
    managepy("register_evaluators -f -c {}".format(company_arg))


@task
def replacedb(c, dbfile, nomigs=False, verbose=False):
    '''Replace db

    nomigs: don't run migrations
    '''
    forcelocal(c)
    replacedb_path = join(dirname(__file__), 'replacedb.py')
    args = ''
    if c.config.get('project_path'):
        args += ' -p ' + ' '.join(c.project_path)
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
        python=c.python, replacedb=replacedb_path, args=args)
    c.run(cmd, echo=True)
