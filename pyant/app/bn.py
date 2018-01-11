import collections
import datetime
import os
import os.path
import re
import time
import xml.etree.ElementTree

from pyant import check, git, maven
from pyant.app import build, const
from pyant.builtin import os as builtin_os

__all__ = ('update', 'compile_base', 'compile', 'package', 'dashboard', 'dashboard_monitor', 'environ')

REPOS = collections.OrderedDict([
    ('interface', builtin_os.join(const.SSH_GIT, 'U31R22_INTERFACE')),
    ('platform' , builtin_os.join(const.SSH_GIT, 'U31R22_PLATFORM')),
    ('necommon' , builtin_os.join(const.SSH_GIT, 'U31R22_NECOMMON')),
    ('e2e'      , builtin_os.join(const.SSH_GIT, 'U31R22_E2E')),
    ('uca'      , builtin_os.join(const.SSH_GIT, 'U31R22_UCA')),
    ('xmlfile'  , builtin_os.join(const.SSH_GIT, 'U31R22_NBI_XMLFILE')),
    ('nbi'      , builtin_os.join(const.SSH_GIT, 'U31R22_NBI')),
    ('sdh'      , builtin_os.join(const.SSH_GIT, 'U31R22_SDH')),
    ('wdm'      , builtin_os.join(const.SSH_GIT, 'U31R22_WDM')),
    ('ptn'      , builtin_os.join(const.SSH_GIT, 'U31R22_PTN')),
    ('ptn2'     , builtin_os.join(const.SSH_GIT, 'U31R22_PTN2')),
    ('ip'       , builtin_os.join(const.SSH_GIT, 'U31R22_IP'))
])

REPOS_DEVTOOLS = const.SSH_GIT

ARTIFACT_REPOS = {
    'snapshot'  : 'U31R22-snapshot-generic',
    'alpha'     : 'U31R22-alpha-generic',
    'release'   : 'U31R22-release-generic'
}

def update(name = None, branch = None, *arg):
    if name in REPOS.keys():
        path = os.path.basename(REPOS[name])

        if os.path.isdir(path):
            if os.path.isfile(os.path.join(path, '.git/index.lock')):
                time.sleep(30)

                return True
            else:
                return git.pull(path, revert = True)
        else:
            return git.clone(REPOS[name], path, branch)
    else:
        if name == 'devtools':
            return update_devtools(branch)
        else:
            print('module name not found in %s' % tuple(REPOS.keys()))

            return False

def compile_base(cmd = None):
    path = os.path.basename(REPOS['platform'])

    if os.path.isdir(path):
        with builtin_os.chdir(path) as chdir:
            for home in ('pom/version', 'pom/testframework', 'pom'):
                if os.path.isdir(home):
                    with builtin_os.chdir(home) as chdir:
                        mvn = maven.maven()

                        if not mvn.compile(cmd):
                            return False
                else:
                    print('no such directory: %s' % os.path.normpath(home))

                    return False

        for http in REPOS.values():
            path = os.path.join(os.path.basename(http), 'code/build/thirdparty')

            if os.path.isdir(path):
                with builtin_os.chdir(path) as chdir:
                    mvn = maven.maven()

                    if not mvn.compile(cmd):
                        return False

        return True
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def compile(name = None, cmd = None, clean = False, retry_cmd = None, dirname = None, lang = None, *arg):
    if isinstance(clean, str):
        if clean.lower().strip() == 'true':
            clean = True

    if name in REPOS.keys():
        environ(lang)

        notification = '<BN_BUILD 通知>编译失败, 请尽快处理(%s)' % builtin_os.osname().upper()

        if not dirname:
            if lang == 'cpp':
                dirname = 'code_c/build'
            else:
                dirname = 'code/build'

        path = os.path.join(os.path.basename(REPOS[name]), dirname)

        if os.path.isdir(path):
            with builtin_os.chdir(path) as chdir:
                mvn = maven.maven()
                mvn.notification = notification

                if clean:
                    mvn.clean()

                return mvn.compile(cmd, retry_cmd, lang)
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False
    else:
        print('module name not found in %s' % tuple(REPOS.keys()))

        return False

def package(version, *arg):
    if arg:
        type = arg[0].strip().lower()
    else:
        type = None

    if not type:
        type = 'ems'

    if build.package(version, None, type, expand_filename, False):
        if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
            generic_path = ARTIFACT_REPOS['snapshot']
        else:
            generic_path = ARTIFACT_REPOS['alpha']

        suffix = '-%s' % builtin_os.osname()

        if type not in ('ems'):
            suffix += '(%s)' % type

        if type in ('lct'):
            bases = (
                os.path.join(ARTIFACT_REPOS['release'], 'UEP/LCT/current_en.tar.gz'),
                os.path.join(ARTIFACT_REPOS['release'], 'UEP/LCT/current_zh.tar.gz')
            )
        else:
            bases = ((
                os.path.join(ARTIFACT_REPOS['release'], 'UEP/current.tar.gz'),
                os.path.join(ARTIFACT_REPOS['release'], 'UEP/TYPES/%s.tar.gz' % type)
            ),)

        for base_list in bases:
            if not build.artifactory(build.package_home(version),
                os.path.join(generic_path, version.replace(' ', '')), base_list, suffix):
                return False

        return True
    else:
        return False

def dashboard(name, paths, branch = None, *arg):
    if not os.environ.get('NOT_DASHBOARD_DEVTOOLS'):
        if not update('devtools', branch):
            return False

    if not update(name, branch):
        return False

    path = os.path.basename(REPOS[name])

    if os.path.isdir(path):
        environ('cpp')

        with builtin_os.chdir(path) as chdir:
            return build.dashboard(paths, r'error_conf\.xml', True)
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def dashboard_monitor(branch = None):
    status = True

    for module in REPOS.keys():
        if not update(module, branch):
            status = False

    if not status:
        return False

    path_info = collections.OrderedDict()

    for module, url in REPOS.items():
        path_info[os.path.basename(REPOS[module])] = module

    if os.environ.get('JOB_NAME'):
        job_home = os.path.dirname(os.environ['JOB_NAME'])
    else:
        job_home = 'bn/dashboard'

    for path, (authors, paths) in build.dashboard_monitor(path_info.keys(), expand_dashboard).items():
        build.dashboard_jenkins_cli(os.path.join(job_home, 'bn_dashboard_%s' % path_info[path]), authors, paths)

    return True

# ----------------------------------------------------------

def update_devtools(branch = None):
    if builtin_os.osname() == 'linux':
        url = builtin_os.join(REPOS_DEVTOOLS, 'U31R22_DEVTOOLS_LINUX')
    elif builtin_os.osname() == 'solaris':
        url = builtin_os.join(REPOS_DEVTOOLS, 'U31R22_DEVTOOLS_SOLARIS')
    elif builtin_os.osname() == 'windows-x64':
        url = builtin_os.join(REPOS_DEVTOOLS, 'U31R22_DEVTOOLS_WINDOWS-x64')
    else:
        url = builtin_os.join(REPOS_DEVTOOLS, 'U31R22_DEVTOOLS_WINDOWS')

    path = 'DEVTOOLS'

    if os.path.isdir(path):
        if os.path.isfile(os.path.join(path, '.git/index.lock')):
            time.sleep(30)

            return True
        else:
            return git.pull(path, revert = True)
    else:
        return git.clone(url, path, branch)

def environ(lang = None):
    if os.environ.get('UEP_VERSION'):
        if not os.environ.get('POM_UEP_VERSION'):
            os.environ['POM_UEP_VERSION'] = os.environ['UEP_VERSION'].upper()

            print('export POM_UEP_VERSION=%s' % os.environ['POM_UEP_VERSION'])

    if not os.environ.get('DEVTOOLS_ROOT'):
        if os.path.isdir('DEVTOOLS'):
            os.environ['DEVTOOLS_ROOT'] = builtin_os.abspath('DEVTOOLS')

    if lang == 'cpp':
        if os.path.isdir(os.path.join(os.environ['DEVTOOLS_ROOT'], 'vc/bin')):
            os.environ['PATH'] = ';'.join((builtin_os.join(os.environ['DEVTOOLS_ROOT'], 'vc/bin'), os.environ['PATH']))

        if not os.environ.get('INTERFACE_OUTPUT_HOME'):
            path = os.path.basename(REPOS['interface'])

            if os.path.isdir(path):
                os.environ['INTERFACE_OUTPUT_HOME'] = builtin_os.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('PLATFORM_OUTPUT_HOME'):
            path = os.path.basename(REPOS['platform'])

            if os.path.isdir(path):
                os.environ['PLATFORM_OUTPUT_HOME'] = builtin_os.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('NECOMMON_OUTPUT_HOME'):
            path = os.path.basename(REPOS['necommon'])

            if os.path.isdir(path):
                os.environ['NECOMMON_OUTPUT_HOME'] = builtin_os.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('E2E_OUTPUT_HOME'):
            path = os.path.basename(REPOS['e2e'])

            if os.path.isdir(path):
                os.environ['E2E_OUTPUT_HOME'] = builtin_os.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('UCA_OUTPUT_HOME'):
            path = os.path.basename(REPOS['uca'])

            if os.path.isdir(path):
                os.environ['UCA_OUTPUT_HOME'] = builtin_os.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('NAF_OUTPUT_HOME'):
            path = os.path.basename(REPOS['nbi'])

            if os.path.isdir(path):
                os.environ['NAF_OUTPUT_HOME'] = builtin_os.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('SDH_OUTPUT_HOME'):
            path = os.path.basename(REPOS['sdh'])

            if os.path.isdir(path):
                os.environ['SDH_OUTPUT_HOME'] = builtin_os.join(os.path.abspath(path), 'code_c/build/output')

        if not os.environ.get('WDM_OUTPUT_HOME'):
            path = os.path.basename(REPOS['wdm'])

            if os.path.isdir(path):
                os.environ['WDM_OUTPUT_HOME'] = builtin_os.join(os.path.abspath(path), 'code_c/build/output')

def expand_filename(version, dirname, filename, type):
    dst = filename
    name = os.path.join(dirname, filename)

    dst = dst.replace('ums-nms', 'ums-client').replace('ums-lct', 'ums-client')

    if os.path.basename(name) in ('ppuinfo.xml', 'pmuinfo.xml', 'u3backup.xml', 'u3backupme.xml', 'dbtool-config.xml'):
        try:
            tree = xml.etree.ElementTree.parse(name)
        except:
            tree = check.xml_etree_with_encoding(name, 'gb2312')

        if tree is not None:
            if os.path.basename(name) in ('ppuinfo.xml', 'pmuinfo.xml'):
                if version:
                    for e in tree.findall('info'):
                        e.set('version', version)
                        e.set('display-version', version)
            elif os.path.basename(name) in ('u3backup.xml', 'u3backupme.xml'):
                if version:
                    for e in tree.findall('version'):
                        e.text = version
            elif os.path.basename(name) in ('dbtool-config.xml'):
                for e in tree.findall('ems_type'):
                    e.text = type
            else:
                pass

            tree.write(name, encoding = 'utf-8', xml_declaration = True)

    return (filename, dst)

def expand_dashboard(path, file):
    file = builtin_os.normpath(file)

    if path in ('U31R22_INTERFACE'):
        if file.startswith('code/asn/'):
            return ('code/finterface', 'code_c/finterface')
        elif file.startswith('code_c/asn/sdh-wdm/qx-interface/asn/'):
            return 'code_c/qxinterface/qxinterface'
        elif file.startswith('code_c/asn/sdh-wdm/qx-interface/asn5800/'):
            return 'code_c/qxinterface/qx5800'
        elif file.startswith('code_c/asn/sdh-wdm/qx-interface/asnwdm721/'):
            return 'code_c/qxinterface/qxwdm721'
        elif file.startswith('code_c/asn/otntlvqx/'):
            return 'code_c/qxinterface/qxotntlv'
        else:
            return file
    elif path in ('U31R22_NBI'):
        if file.startswith('code_c/adapters/xtncorba/corbaidl/'):
            return ('code_c/adapters/xtncorba/corbaidl/corbaidl', 'code_c/adapters/xtncorba/corbaidl/corbaidl2')
        elif file.startswith('code_c/adapters/xtntmfcorba/corbaidl/'):
            return ('adapters/xtntmfcorba/corbaidl/corbaidl', 'code_c/adapters/xtntmfcorba/corbaidl/corbaidl2')
        else:
            return file
    else:
        if re.search(r'^code_c\/database\/.*\/xml\/.*\.xml$', file):
            if os.path.isfile('code_c/database/dbscript/pom.xml'):
                if os.path.isfile(os.path.join(os.path.dirname(file), '../pom.xml')):
                    return ('code_c/database/dbscript', file)

        return file
