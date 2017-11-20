import collections
import os.path

from pyant import git, maven
from pyant.app import const
from pyant.builtin import os as builtin_os

__all__ = ['update', 'compile']

REPOS = collections.OrderedDict([
  ('u3_interface'     , os.path.join(const.SSH_GIT, 'U31R22_INTERFACE')),
  ('sdn_interface'    , os.path.join(const.SSH_GIT, 'stn/sdn_interface')),
  ('sdn_framework'    , os.path.join(const.SSH_GIT, 'stn/sdn_framework')),
  ('sdn_application'  , os.path.join(const.SSH_GIT, 'stn/sdn_application')),
  ('sdn_tunnel'       , os.path.join(const.SSH_GIT, 'stn/sdn_tunnel')),
  ('sdn_installation' , os.path.join(const.SSH_GIT, 'stn/sdn_installation')),
  ('CTR-ICT'          , os.path.join(const.SSH_GIT, 'stn/CTR-ICT')),
  ('SPTN-E2E'         , os.path.join(const.SSH_GIT, 'stn/SPTN-E2E'))
])

def update(name = None, branch = None, *arg):
    if name in REPOS.keys():
        if name == 'u3_interface':
            path = name
        else:
            path = os.path.basename(REPOS[name])

        if os.path.isdir(path):
            return git.pull(path, revert = True)
        else:
            return git.clone(REPOS[name], path, branch)
    else:
        print('module name not found in %s' % tuple(REPOS.keys()))

        return False

def compile_base(cmd = None):
    path = os.path.basename(REPOS['sdn_interface'])

    if os.path.isdir(path):
        with builtin_os.chdir(path) as dir:
            for home in ('pom/version', 'pom/testframework', 'pom'):
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
    if name in REPOS.keys():
        if not dirname:
            if name == 'u3_interface':
                dirname = 'sdn/build'
            else:
                dirname = 'code/build'

        if name == 'u3_interface':
            path = os.path.join('u3_interface', dirname)
        else:
            path = os.path.join(os.path.basename(REPOS[name]), dirname)

        if os.path.isdir(path):
            with builtin_os.chdir(path) as dir:
                mvn = maven.maven()

                if clean:
                    mvn.clean()

                return mvn.compile(cmd, retry_cmd)
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False
    else:
        print('module name not found in %s' % tuple(REPOS.keys()))

        return False
