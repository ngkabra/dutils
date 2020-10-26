from invoke import Collection, task


def autoconfig(c):
    name = c.original_host
    host = name             # host defaults to name for now ('rsh')
    if not c.config.get('venv'):
        c.config['venv'] = name

    c['home'] = '/home/navin'
    c['wfdir'] = '{home}/webapps/{name}'.format(home=c.home, name=name)
    c['projdir'] = '{wfdir}/myproject'.format(wfdir=c.wfdir)
    c['python'] = '{home}/.v/{venv}/bin/python'.format(home=c.home, venv=c.venv)


@task
def managepy(c, command):
    autoconfig(c)
    with c.cd(c.projdir):
        c.run("{python} manage.py {command}".format(
            python=c.python, command=command))


@task
def ls(c, directory=None):
    if not directory:
        c.run('ls')
    else:
        with c.cd(directory):
            c.run('ls')


@task
def host(c):
    try:
        print('original_host', c.original_host)
    except AttributeError:
        print('No original_host')

    try:
        print('host', c.host)
    except AttributeError:
        print('No host')
