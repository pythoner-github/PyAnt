import datetime
import os
import os.path
import re
import shutil
import sys

from pyant import check
from pyant.app import const, patch, utils
from pyant.builtin import __os__, __string__

from pyant.app.bn import bn_build, bn_dashboard, bn_patch, bn_installation
from pyant.app.umebn import umebn_build, umebn_dashboard, umebn_patch, umebn_installation

__build_name__ = ('bn', 'umebn')
__all__ = ('build',)

usage = '''
Usage:
    name command home arg

    command:
        update                      arg: module branch
        updateall                   arg: branch
        compile_pom                 arg: cmd
        compile                     arg: module cmd clean retry_cmd dirname lang
        package                     arg: branch type
        update_package              arg: branch type
        check                       arg:
        kw_compile                  arg: output module cmd lang
        kw_build                    arg: module lang
        dashboard_monitor           arg: branch
        dashboard                   arg: module, paths, branch
        dashboard_gerrit            arg:
        patch_auto                  arg:
        patch                       arg: path
        patch_init                  arg: path, branch
        patch_install               arg: path, sp_next, type
'''

def build(argv = None):
    if not argv:
        argv = sys.argv[1:]

    if len(argv) < 3:
        print(usage.strip())

        return False

    name = argv[0]
    command = argv[1]
    home = argv[2]

    if not name in __build_name__:
        print('name not found in (%s)' % ', '.join(__build_name__))

        return False

    arg = expand_arg(argv[3:], 10)

    os.makedirs(home, exist_ok = True)
    pwd = os.getcwd()

    with __os__.chdir(home) as chdir:
        version = None

        POM_VERSION = '%s_POM_VERSION' % name.upper()

        if os.environ.get('VERSION'):
            os.environ['VERSION'] = os.environ['VERSION'].strip()

            if os.environ['VERSION']:
                if not os.environ.get(POM_VERSION):
                    os.environ[POM_VERSION] = os.environ['VERSION'].upper().replace('_${date}', '').replace(' ', '')

                    print('export %s=%s' % (POM_VERSION, os.environ[POM_VERSION]))

                version = os.environ['VERSION'].replace('_${date}', datetime.datetime.now().strftime('%Y%m%d'))

        if name in ('bn',):
            if os.environ.get(POM_VERSION):
                os.environ['POM_VERSION'] = os.environ[POM_VERSION]

                print('export POM_VERSION=%s' % os.environ['POM_VERSION'])

        if command in (
            'update', 'updateall', 'compile_pom', 'compile', 'check',
            'package', 'update_package', 'kw_compile', 'kw_build'
        ):
            # build

            if name == 'bn':
                build = bn_build()
            else:
                build = umebn_build()

            if command == 'update':
                module, branch, *_ = arg

                if name in ('bn',):
                    return build.update(module, branch)
                else:
                    return build.update(branch)
            elif command == 'updateall':
                branch = arg[0]

                if name in ('bn',):
                    return build.update(None, branch)
                else:
                    return build.update(branch)
            elif command == 'compile_pom':
                cmd = arg[0]

                return build.compile_pom(cmd)
            elif command == 'compile':
                module, cmd, clean, retry_cmd, dirname, lang, *_ = arg

                if clean in (True, ):
                    clean = True
                else:
                    clean = False

                id = utils.metric_start(build.metric_id(module), module)

                if name in ('bn',):
                    status = build.compile(module, cmd, clean, retry_cmd, dirname, lang)
                else:
                    status = build.compile(cmd, clean, retry_cmd, dirname)

                utils.metric_end(id, status)

                return status
            elif command == 'check':
                if name in ('bn',):
                    status = True

                    for key in build.repos.keys():
                        if key in ('ptn2'):
                            ignores = r'error_conf\.xml'
                        else:
                            ignores = None

                        chk = check.check(os.path.basename(build.repos[key]))
                        chk.notification = '<%s_CHECK 通知> 文件检查失败, 请尽快处理' % name.upper()

                        if not chk.check(ignores):
                            status = False

                    return status
                else:
                    chk = check.check()
                    chk.notification = '<%s_CHECK 通知> 文件检查失败, 请尽快处理' % name.upper()

                    return chk.check()
            elif command in ('package', 'update_package'):
                branch, type, *_ = arg

                if not version:
                    if not branch:
                        branch = 'master'

                    version = '%s_%s' % (branch, datetime.datetime.now().strftime('%Y%m%d'))

                if command == 'package':
                    return build.package(version, type)
                else:
                    if name == 'bn':
                        return build.update_package(version, type)
                    else:
                        return True
            elif command == 'kw_compile':
                output, module, cmd, lang, *_ = arg

                with __os__.chdir(pwd) as _chdir:
                    output = os.path.abspath(output)

                if name in ('bn',):
                    path = os.path.join(output, name, module)

                    if lang == 'cpp':
                        path += '_cpp'
                else:
                    path = os.path.join(output, name)

                kw_option = '--output "%s"' % os.path.join(path, 'kwinject/kwinject.out')

                if cmd:
                    m = re.search(r'^(kwmaven|kwinject)\s+', cmd)

                    if m:
                        cmd = '%s %s %s' % (m.group(1), kw_option, m.string[m.end():])
                else:
                    if name in ('bn',):
                        if lang == 'cpp':
                            cmd = 'kwinject %s mvn install -U -fn' % kw_option
                        else:
                            cmd = 'kwmaven %s install -U -fn' % kw_option
                    else:
                        cmd = 'kwmaven %s install -U -fn' % kw_option

                if name in ('bn',):
                    if module in list(build.repos.keys()) + ['wdm1', 'wdm2', 'wdm3']:
                        shutil.rmtree(os.path.join(path, 'kwinject'), ignore_errors = True)
                        os.makedirs(os.path.join(path, 'kwinject'), exist_ok = True)

                    if module in ('wdm1', 'wdm2', 'wdm3'):
                        return build.compile(module, cmd, True, dirname = os.path.join('code_c/build/kw', module), lang = lang)
                    else:
                        return build.compile(module, cmd, True, lang = lang)
                else:
                    shutil.rmtree(os.path.join(path, 'kwinject'), ignore_errors = True)
                    os.makedirs(os.path.join(path, 'kwinject'), exist_ok = True)

                    return build.compile(cmd, True)
            elif command == 'kw_build':
                module, lang, *_ = arg

                if name in ('bn',):
                    path = os.path.join(name, module)

                    if lang == 'cpp':
                        path += '_cpp'
                else:
                    path = name

                if name in ('bn',):
                    if module in list(build.repos.keys()) + ['wdm1', 'wdm2', 'wdm3']:
                        shutil.rmtree(os.path.join(path, 'kwbuild'), ignore_errors = True)
                        os.makedirs(os.path.join(path, 'kwbuild'), exist_ok = True)
                else:
                    shutil.rmtree(os.path.join(path, 'kwbuild'), ignore_errors = True)
                    os.makedirs(os.path.join(path, 'kwbuild'), exist_ok = True)

                return build.kw_build(path)
            else:
                pass

            return True
        elif command in ('dashboard_monitor', 'dashboard', 'dashboard_gerrit'):
            # dashboard

            if name == 'bn':
                build = bn_build()
                dashboard = bn_dashboard()
            else:
                build = umebn_build()
                dashboard = umebn_dashboard()

            if command == 'dashboard_monitor':
                branch = arg[0]

                return dashboard.dashboard_monitor(branch)
            elif command == 'dashboard':
                module, paths, branch, *_ = arg

                if paths:
                    paths = __string__.split(paths)
                else:
                    paths = []

                id = utils.metric_start(build.metric_id(module), module, False)

                if name in ('bn',):
                    status = dashboard.dashboard(module, paths, branch)
                else:
                    status = dashboard.dashboard(paths, branch)

                utils.metric_end(id, status)

                return status
            elif command == 'dashboard_gerrit':
                repos = __os__.join(const.SSH_GIT, os.environ.get('GERRIT_PROJECT'))
                revision = os.environ.get('GERRIT_PATCHSET_REVISION')
                branch = os.environ.get('GERRIT_BRANCH')

                if name in ('bn',):
                    return dashboard.dashboard_gerrit(arg[0], repos, revision, branch)
                else:
                    return dashboard.dashboard_gerrit(repos, revision, branch)
            else:
                pass

            return True
        elif command in ('patch_auto',):
            # patch auto
            return patch.auto()
        elif command in ('patch', 'patch_init', ):
            # patch

            if name == 'bn':
                patch = bn_patch
            else:
                patch = umebn_patch

            if command == 'patch':
                path = arg[0]

                return patch(path, version).build()
            elif command == 'patch_init':
                path, branch, *_ = arg

                return patch(path, version).init(branch)
            else:
                pass
        elif command in ('patch_install', ):
            # patch installation

            if name == 'bn':
                installation = bn_installation
            else:
                installation = umebn_installation

            path, sp_next, type, *_ = arg

            if str(sp_next).lower() == 'true':
                sp_next = True
            else:
                sp_next = False

            display_version = None

            if os.environ.get('DISPLAY_VERSION'):
                display_version = os.environ['DISPLAY_VERSION'].strip()

            return installation(path).build(version, display_version, sp_next, type)
        else:
            print(usage.strip())

            return False

# ----------------------------------------------------------

def expand_arg(arg, size):
    dup = []

    for a in arg:
        x = a.strip().lower()

        if x in ('', '_', 'none'):
            dup.append(None)
        elif x in ('true'):
            dup.append(True)
        elif x in ('false'):
            dup.append(False)
        else:
            if x.startswith('mvn_'):
                dup.append(x.replace('_', ' '))
            else:
                dup.append(a)

    if len(arg) < size:
        for i in range(size - len(arg)):
            dup.append(None)

    return dup
