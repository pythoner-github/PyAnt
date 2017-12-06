import collections
import os
import os.path
import sys

from pyant import git, maven
from pyant.app import build, const
from pyant.builtin import os as builtin_os

__all__ = ['update', 'compile', 'package']

REPOS = collections.OrderedDict([
  ('interface', os.path.join(const.SSH_GIT, 'U31R22_INTERFACE')),
  ('platform' , os.path.join(const.SSH_GIT, 'U31R22_PLATFORM')),
  ('necommon' , os.path.join(const.SSH_GIT, 'U31R22_NECOMMON')),
  ('e2e'      , os.path.join(const.SSH_GIT, 'U31R22_E2E')),
  ('uca'      , os.path.join(const.SSH_GIT, 'U31R22_UCA')),
  ('xmlfile'  , os.path.join(const.SSH_GIT, 'U31R22_NBI_XMLFILE')),
  ('nbi'      , os.path.join(const.SSH_GIT, 'U31R22_NBI')),
  ('sdh'      , os.path.join(const.SSH_GIT, 'U31R22_SDH')),
  ('wdm'      , os.path.join(const.SSH_GIT, 'U31R22_WDM')),
  ('ptn'      , os.path.join(const.SSH_GIT, 'U31R22_PTN')),
  ('ptn2'     , os.path.join(const.SSH_GIT, 'U31R22_PTN2')),
  ('ip'       , os.path.join(const.SSH_GIT, 'U31R22_IP'))
])

REPOS_DEVTOOLS = const.SSH_GIT

def update(name = None, branch = None, *arg):
    if name in REPOS.keys():
        path = os.path.basename(REPOS[name])

        if os.path.isdir(path):
            return git.pull(path, revert = True)
        else:
            return git.clone(REPOS[name], path, branch)
    else:
        if name == 'devtools':
            return update_devtools(branch)
        else:
            print('module name not found in %s' % tuple(REPOS.keys()))

            return False

def compile_base(name = None, cmd = None):
    path = os.path.basename(REPOS['platform'])

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

        for http in REPOS.values():
            path = os.path.join(os.path.basename(http), 'code/build/thirdparty')

            if os.path.isdir(path):
                with builtin_os.chdir(path) as dir:
                    mvn = maven.maven()

                    if not mvn.compile(cmd):
                        return False

        return True
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def compile(name = None, cmd = None, clean = False, retry_cmd = None, lang = None, dirname = None, *arg):
    if isinstance(clean, str):
        if clean.lower().strip() == 'true':
            clean = True

    if name in REPOS.keys():
        environ(lang)

        if not dirname:
            if lang == 'cpp':
                dirname = 'code_c/build'
            else:
                dirname = 'code/build'

        path = os.path.join(os.path.basename(REPOS[name]), dirname)

        if os.path.isdir(path):
            with builtin_os.chdir(path) as dir:
                mvn = maven.maven()

                if clean:
                    mvn.clean()

                return mvn.compile(cmd, retry_cmd, lang)
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False
    else:
        print('module name not found in %s' % tuple(REPOS.keys()))

        return False

def package(version = None, type = None, *arg):
    if not type:
        type = 'ems'

    return build.package(None, version, type, expand_filename)

# ----------------------------------------------------------

def update_devtools(branch = None):
    if sys.platform == 'linux':
        url = os.path.join(REPOS_DEVTOOLS, 'U31R22_DEVTOOLS_LINUX')
    elif sys.platform == 'sunos':
        url = os.path.join(REPOS_DEVTOOLS, 'U31R22_DEVTOOLS_SOLARIS')
    else:
        if os.environ.get('X64') == '1':
            url = os.path.join(REPOS_DEVTOOLS, 'U31R22_DEVTOOLS_WINDOWS-x64')
        else:
            url = os.path.join(REPOS_DEVTOOLS, 'U31R22_DEVTOOLS_WINDOWS')

    path = 'DEVTOOLS'

    if os.path.isdir(path):
        return git.pull(path, revert = True)
    else:
        return git.clone(url, path, branch)

def environ(lang = None):
    if not os.environ.get('DEVTOOLS_ROOT'):
        if os.path.isdir('DEVTOOLS'):
            os.environ['DEVTOOLS_ROOT'] = os.path.abspath('DEVTOOLS')

    if lang == 'cpp':
        if not os.environ.get('INTERFACE_OUTPUT_HOME'):
            path = os.path.basename(REPOS['interface'])

            if os.path.isdir(path):
                os.environ['INTERFACE_OUTPUT_HOME'] = os.path.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('PLATFORM_OUTPUT_HOME'):
            path = os.path.basename(REPOS['platform'])

            if os.path.isdir(path):
                os.environ['PLATFORM_OUTPUT_HOME'] = os.path.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('NECOMMON_OUTPUT_HOME'):
            path = os.path.basename(REPOS['necommon'])

            if os.path.isdir(path):
                os.environ['NECOMMON_OUTPUT_HOME'] = os.path.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('E2E_OUTPUT_HOME'):
            path = os.path.basename(REPOS['e2e'])

            if os.path.isdir(path):
                os.environ['E2E_OUTPUT_HOME'] = os.path.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('UCA_OUTPUT_HOME'):
            path = os.path.basename(REPOS['uca'])

            if os.path.isdir(path):
                os.environ['UCA_OUTPUT_HOME'] = os.path.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('NAF_OUTPUT_HOME'):
            path = os.path.basename(REPOS['nbi'])

            if os.path.isdir(path):
                os.environ['NAF_OUTPUT_HOME'] = os.path.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('SDH_OUTPUT_HOME'):
            path = os.path.basename(REPOS['sdh'])

            if os.path.isdir(path):
                os.environ['SDH_OUTPUT_HOME'] = os.path.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('WDM_OUTPUT_HOME'):
            path = os.path.basename(REPOS['wdm'])

            if os.path.isdir(path):
                os.environ['WDM_OUTPUT_HOME'] = os.path.join(os.path.abspath(path), 'code_c/build/output')

def expand_filename(dirname, filename):
    dst = filename.replace('ums-nms', 'ums-client').replace('ums-lct', 'ums-client')

    return (filename, dst)
