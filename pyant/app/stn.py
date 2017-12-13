import collections
import datetime
import os.path
import re
import xml.etree.ElementTree

from pyant import git, maven
from pyant.app import build, const
from pyant.builtin import os as builtin_os

__all__ = ['update', 'compile', 'package']

REPOS = collections.OrderedDict([
    ('u3_interface'     , builtin_os.join(const.SSH_GIT, 'U31R22_INTERFACE')),
    ('sdn_interface'    , builtin_os.join(const.SSH_GIT, 'stn/sdn_interface')),
    ('sdn_framework'    , builtin_os.join(const.SSH_GIT, 'stn/sdn_framework')),
    ('sdn_application'  , builtin_os.join(const.SSH_GIT, 'stn/sdn_application')),
    ('sdn_tunnel'       , builtin_os.join(const.SSH_GIT, 'stn/sdn_tunnel')),
    ('SPTN-E2E'         , builtin_os.join(const.SSH_GIT, 'stn/SPTN-E2E')),
    ('CTR-ICT'          , builtin_os.join(const.SSH_GIT, 'stn/CTR-ICT'))
])

ARTIFACT_REPOS = {
    'snapshot'  : 'stn_contoller-snapshot-generic',
    'alpha'     : 'stn_contoller-alpha-generic',
    'release'   : 'stn_contoller-release-generic'
}

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
        with builtin_os.chdir(path) as chdir:
            for home in ('pom/version', 'pom/testframework', 'pom'):
                if os.path.isdir(home):
                    with builtin_os.chdir(home) as chdir:
                        mvn = maven.maven()

                        if not mvn.compile(cmd):
                            return False
                else:
                    print('no such directory: %s' % builtin_os.join(home))

                    return False

        return True
    else:
        print('no such directory: %s' % builtin_os.join(path))

        return False

def compile(name = None, cmd = None, clean = False, retry_cmd = None, dirname = None, *arg):
    if isinstance(clean, str):
        if clean.lower().strip() == 'true':
            clean = True

    if name in REPOS.keys():
        if not dirname:
            if name == 'u3_interface':
                dirname = 'sdn/build'
            else:
                dirname = 'code/build'

        if name == 'u3_interface':
            path = builtin_os.join('u3_interface', dirname)
        else:
            path = builtin_os.join(os.path.basename(REPOS[name]), dirname)

        if os.path.isdir(path):
            with builtin_os.chdir(path) as chdir:
                mvn = maven.maven()

                if clean:
                    mvn.clean()

                return mvn.compile(cmd, retry_cmd)
        else:
            print('no such directory: %s' % builtin_os.join(path))

            return False
    else:
        print('module name not found in %s' % tuple(REPOS.keys()))

        return False

def package(version, *arg):
    if build.package(version, None, 'stn', expand_filename):
        if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
            generic_path = ARTIFACT_REPOS['snapshot']
        else:
            generic_path = ARTIFACT_REPOS['alpha']

        return build.artifactory(build.package_home(version), generic_path,
            builtin_os.join(ARTIFACT_REPOS['release'], 'OSCP/current.tar.gz'))
    else:
        return False

# ----------------------------------------------------------

def expand_filename(version, dirname, filename, type):
    dst = filename
    name = builtin_os.join(dirname, filename)

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
                tree = xml.etree.ElementTree.parse(name)

                for e in tree.findall('info'):
                    e.set('version', version)
                    e.set('display-version', version)

                tree.write(name, encoding = 'utf-8', xml_declaration = True)
            except:
                pass
    else:
        pass

    return (filename, dst)
