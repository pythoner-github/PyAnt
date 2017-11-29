import os.path

from pyant import git, maven
from pyant.app import const
from pyant.builtin import os as builtin_os

__all__ = ['update', 'compile', 'package']

REPOS = os.path.join(const.SSH_GIT, 'sdno')

def update(name = None, branch = None, *arg):
    if name:
        path = name
    else:
        path = os.path.basename(REPOS)

    if os.path.isdir(path):
        return git.pull(path, revert = True)
    else:
        return git.clone(REPOS, path, branch)

def compile_base(name = None, cmd = None):
    if name:
        path = name
    else:
        path = os.path.basename(REPOS)

    if os.path.isdir(path):
        with builtin_os.chdir(path) as dir:
            for home in ('devops/parent/version', 'devops/parent/build'):
                if os.path.isdir(home):
                    with builtin_os.chdir(home) as dir:
                        mvn = maven.maven()

                        if not mvn.compile(cmd):
                            return False
                else:
                    print('no such directory: %s' % os.path.normpath(home))

                    return False

        return True
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def compile(name = None, cmd = None, clean = False, retry_cmd = None, dirname = None, *arg):
    if isinstance(clean, str):
        if clean.lower().strip() == 'true':
            clean = True

    if not dirname:
        dirname = 'build'

    if name:
        path = os.path.join(name, dirname)
    else:
        path = os.path.join(os.path.basename(REPOS), dirname)

    if os.path.isdir(path):
        with builtin_os.chdir(path) as dir:
            mvn = maven.maven()

            if clean:
                mvn.clean()

            return mvn.compile(cmd, retry_cmd)
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def package(version = None, *arg):
    return True
