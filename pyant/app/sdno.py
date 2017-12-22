import datetime
import os.path
import time

from pyant import git, maven
from pyant.app import const
from pyant.builtin import os as builtin_os

__all__ = ('update', 'compile_base', 'compile', 'package', 'dashboard', 'dashboard_monitor')

REPOS = builtin_os.join(const.SSH_GIT, 'sdno')

ARTIFACT_REPOS = {
    'snapshot'  : 'sdno-snapshot-generic',
    'alpha'     : 'sdno-alpha-generic',
    'release'   : 'sdno-release-generic'
}

def update(name = None, branch = None, *arg):
    path = os.path.basename(REPOS)

    if os.path.isdir(path):
        if os.path.isfile(os.path.join(path, '.git/index.lock')):
            time.sleep(30)

            return True
        else:
            return git.pull(path, revert = True)
    else:
        return git.clone(REPOS, path, branch)

def compile_base(cmd = None):
    path = os.path.basename(REPOS)

    if os.path.isdir(path):
        with builtin_os.chdir(path) as chdir:
            for home in ('devops/parent/version', 'devops/parent/build'):
                if os.path.isdir(home):
                    with builtin_os.chdir(home) as chdir:
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

    path = os.path.join(os.path.basename(REPOS), dirname)

    if os.path.isdir(path):
        with builtin_os.chdir(path) as chdir:
            mvn = maven.maven()
            mvn.notification = '<SDNO_BUILD 通知>编译失败, 请尽快处理'

            if clean:
                mvn.clean()

            return mvn.compile(cmd, retry_cmd)
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def package(version, *arg):
    return True

def dashboard(name, paths, branch = None, *arg):
    pass

def dashboard_monitor(branch = None):
    return True
