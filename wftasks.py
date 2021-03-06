from invoke import Collection, task
from os.path import join

from dutils import djtasks, localtasks




@task
def autoconfig(c):
    '''Autoconfig for webfaction tasks'''
    if not c.config.get('project'):
        c['project'] = c.original_host # default for now ('rsh')
    if not c.config.get('venv'):
        c.config['venv'] = c.project

    c['wfhome'] = '/home/navin'
    c['wfdir'] = '{wfhome}/webapps/{project}'.format(wfhome=c.wfhome,
                                                     project=c.project)
    c['python'] = '{wfhome}/.v/{venv}/bin/python'.format(
        wfhome=c.wfhome, venv=c.venv)

    # projdir is for git commands, managepydir is for manage.py
    c['projdir'] = '{wfdir}/myproject'.format(wfdir=c.wfdir)
    c['managepydir'] = c.projdir
    if c.config.get('managepy_subdir'):
        c.managepydir = join(c.projdir, c.managepy_subdir)


@task
def restart(c):
    autoconfig(c)
    c.run('{wfdir}/apache2/bin/restart'.format(wfdir=c.wfdir))


@task
def managepy(c, command):
    autoconfig(c)
    djtasks.managepy(c, command)


@task
def getdb(c):
    autoconfig(c)
    dbfile = djtasks.getdbonly(c)
    djtasks.dumpmedia(c)
    local_ctx = localtasks.local_context(c)
    localtasks.replacedb(local_ctx, dbfile)


@task
def runscript(c, script, *args, **kwargs):
    autoconfig(c)
    djtasks.runscript(script, *args, **kwargs)


@task
def upgrade(c):
    autoconfig(c)
    djtasks.upgrade(c)
    restart(c)


@task
def dumpmedia(c):
    autoconfig(c)
    djtasks.dumpmedia(c)
