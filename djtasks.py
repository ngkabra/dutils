from datetime import datetime
from invoke import Collection, task
from os.path import expanduser, lexists, join
from os import symlink, remove
import shutil
import subprocess


@task
def autoconfig(c):
    '''Autoconfig for django tasks

    Expects the following to already be autoconfiged
    python, project, projdir, managepydir, backups_dir'''

    c['dumpdb_filename'] = 'u/{project}.sql.gz'.format(project=c.project)
    c['mediagz_filename'] = 'u/{project}-media.tgz'.format(project=c.project)
    c['proj_backup_dir'] = '{backups_dir}/{project}'.format(
        backups_dir=c.backups_dir, project=c.project)
    c['media_backup_dir'] = c.proj_backup_dir + '/media/'


def backup_filename(c, prefix, ext):
    return '{proj_backup_dir}/{prefix}{timestamp}{ext}'.format(
        proj_backup_dir=c.proj_backup_dir,
        prefix=prefix,
        timestamp=datetime.now().strftime('%d%b%Y'),
        ext=ext)


@task
def managepy(c, command):
    autoconfig(c)
    with c.cd(c.managepydir):
        result = c.run("{python} manage.py {command}".format(
            python=c.python, command=command), echo=True)
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
    mediadest = c.media_backup_dir
    mediazip = backup_filename(c, 'media', '.tgz')
    
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
    local_mediagz = join(c.localhome, c.mediagz_filename)
    if lexists(local_mediagz):
        remove(local_mediagz)
    symlink(mediazip, local_mediagz)


@task
def getdbonly(c):
    autoconfig(c)
    dumpdb_file = join(c.wfhome, c.dumpdb_filename)
    dumpdb(c, dumpdb_file)
    local_destination = backup_filename(c, 'db', '.sql.gz')

    # soft link appropriately
    local_dumpdb_file = join(c.localhome, dumpdb_file)
    if lexists(local_dumpdb_file):
        remove(local_dumpdb_file)
    print('Getting {}'.format(c.dumpdb_filename))
    c.get(dumpdb_file, local_destination)
    symlink(local_destination, local_dumpdb_file)
    return local_dumpdb_file


@task
def runscript(c, script, *args, **kwargs):
    autoconfig(c)
    managepy(c, command='runcmd {} {} {}'.format(
        script, ' '.join(args),
        ' '.join('{}={}'.format(k, v) for k, v in kwargs.items())))


@task
def upgrade(c):
    autoconfig(c)
    with c.cd(c.projdir):
        c.run('git pull')
        c.run('git submodule update')

    managepy(c, 'migrate -v 0')
    managepy(c, 'collectstatic --noinput')
