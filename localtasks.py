from invoke import task

from . import wftasks 

def autoconfig(c):
    if not c.config.get('project'):
        c['project'] = 'rs'
    if not c.config.get('venv'):
        c['venv'] = c.project
    

@task
def forcelocal(c):
    try:
        if c.host:
            raise Exception('Local command attempted on remote')
    except AttributeError:
        pass

@task(forcelocal)
def tags(c):
    '''Re-build tags table for emacs'''
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



@task(forcelocal)
def managepy(c, command):
    autoconfig(c)
    c.run('{python} manage.py {command}'.format(
        python=c.python, command=command))


@task(forcelocal)
def findmigs(c, appname=''):
    '''find migrations'''
    managepy(c, 'schemamigration {appname}'.format(appname=appname))

