import collections
import datetime
import os.path
import re
import time

from lxml import etree

from pyant import git, maven
from pyant.app import build, const
from pyant.builtin import os as builtin_os

__all__ = ('update', 'compile_base', 'compile', 'package', 'dashboard', 'dashboard_monitor')

REPOS = builtin_os.join(const.SSH_GIT, 'stn/sdn_tunnel')

ARTIFACT_REPOS = {
    'snapshot'  : 'stn_contoller-snapshot-generic',
    'alpha'     : 'stn_contoller-alpha-generic',
    'release'   : 'stn_contoller-release-generic'
}

def update(name, branch = None, *arg):
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
            for home in ('pom/version', 'pom/bundle', 'pom'):
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

def compile(name, cmd = None, clean = False, retry_cmd = None, dirname = None, *arg):
    if isinstance(clean, str):
        if clean.lower().strip() == 'true':
            clean = True

    if not dirname:
        dirname = 'build'

    path = os.path.join(os.path.basename(REPOS), dirname)

    if os.path.isdir(path):
        with builtin_os.chdir(path) as chdir:
            mvn = maven.maven()
            mvn.notification = '<STN_BUILD 通知>编译失败, 请尽快处理'

            if clean:
                mvn.clean()

            return mvn.compile(cmd, retry_cmd)
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def package(version, *arg):
    if build.package(version, None, 'stn', expand_filename):
        if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
            generic_path = ARTIFACT_REPOS['snapshot']
        else:
            generic_path = ARTIFACT_REPOS['alpha']

        return build.artifactory(build.package_home(version), generic_path,
            os.path.join(ARTIFACT_REPOS['release'], 'OSCP/current.tar.gz'))
    else:
        return False

def dashboard(paths, branch = None, *arg):
    if not update(None, branch):
        return False

    path = os.path.basename(REPOS)

    if os.path.isdir(path):
        with builtin_os.chdir(path) as chdir:
            return build.dashboard(paths)
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def dashboard_monitor(branch = None):
    if not update(None, branch):
        return False

    path_info = collections.OrderedDict()
    path_info[os.path.basename(REPOS)] = 'stn'

    if os.environ.get('JOB_NAME'):
        job_home = os.path.dirname(os.environ['JOB_NAME'])
    else:
        job_home = 'stn/dashboard'

    for path, (authors, paths) in build.dashboard_monitor(path_info.keys(), expand_dashboard).items():
        build.dashboard_jenkins_cli(os.path.join(job_home, 'stn_dashboard'), authors, paths)

    return True

# ----------------------------------------------------------

def expand_filename(version, dirname, filename, type):
    dst = filename
    name = os.path.join(dirname, filename)

    if os.path.basename(name) == 'sptnconf.properties':
        if os.path.basename(dirname).endswith('_anode'):
            nodetype = '1'
        elif os.path.basename(dirname).endswith('_cnode'):
            nodetype = '2'
        else:
            nodetype = '3'

        for encoding in ('utf8', 'cp936'):
            try:
                lines = []

                with open(name, encoding = encoding) as f:
                    for line in f.readlines():
                        line = line.rstrip()

                        if re.search(r'^sptn\.nodetype\s*=', line):
                            line = 'sptn.nodetype=%s' % nodetype

                        lines.append(line)

                with open(name, 'w', encoding = encoding) as f:
                    f.write('\n'.join(lines).strip())

                break
            except:
                pass
    elif os.path.basename(name) in ('ppuinfo.xml', 'pmuinfo.xml'):
        if version:
            try:
                tree = etree.parse(name)

                for e in tree.findall('info'):
                    e.set('version', version)
                    e.set('display-version', version)

                tree.write(name, encoding='utf-8', pretty_print=True, xml_declaration='utf-8')
            except:
                pass
    else:
        pass

    return (filename, dst)

def expand_dashboard(path, file):
    file = builtin_os.normpath(file)

    if path in ('U31R22_INTERFACE'):
        if file.startswith('code/asn/'):
            return 'sdn/build'
        else:
            if file.startswith('sdn/'):
                return file
            else:
                return None
    else:
        return file
