from invoke import Collection, task


@task
def managepy(c, command):
    c.run("{} {}".format(c['managepy'], command))


@task
def ls(c, dir=None):
    c.run('ls {}'.format(dir or ''))

