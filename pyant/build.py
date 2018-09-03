import datetime
import os
import os.path
import re
import shutil
import sys

from pyant import check, string
from pyant.app import const, patch
from pyant.app import build as app_build
from pyant.builtin import os as builtin_os

__build_name__ = ('bn', 'stn', 'umebn', 'sdno')
__all__ = ('build',)

usage = '''
Usage:
    name command home arg

    command:
        updateall                   arg: branch
        update                      arg: module branch
        compile_base                arg: cmd
        compile                     arg: module cmd clean retry_cmd dirname lang
        package                     arg: branch type
        update_package              arg: branch type
        check                       arg:
        kw_compile                  arg: output module cmd lang
        kw_build                    arg: module lang
        dashboard                   arg: module, paths, branch
        dashboard_gerrit            arg:
        dashboard_monitor           arg: branch
        patch_auto                  arg:
        patch                       arg: path
        patch_init                  arg: path, branch
        patch_install               arg: path, sp_next, type
'''

def build(argv = None):
    if not argv:
        argv = sys.argv[1:]

    if len(argv) >= 3:
        name = argv[0]
        command = argv[1]
        home = argv[2]

        if not name in __build_name__:
            print('name not found in (%s)' % ', '.join(__build_name__))

            return False

        arg = expand_arg(argv[3:], 10)

        os.makedirs(home, exist_ok = True)
        pwd = os.getcwd()

        with builtin_os.chdir(home) as chdir:
            version = None

            POM_VERSION = '%s_POM_VERSION' % name.upper()

            if os.environ.get('VERSION'):
                os.environ['VERSION'] = os.environ['VERSION'].strip()

                if os.environ['VERSION']:
                    if not os.environ.get(POM_VERSION):
                        os.environ[POM_VERSION] = os.environ['VERSION'].upper().replace('_${date}', '').replace(' ', '')

                        print('export %s=%s' % (POM_VERSION, os.environ[POM_VERSION]))

                    version = os.environ['VERSION'].replace('_${date}', datetime.datetime.now().strftime('%Y%m%d'))

            if name == 'bn':
                if os.environ.get(POM_VERSION):
                    os.environ['POM_VERSION'] = os.environ[POM_VERSION]

                    print('export POM_VERSION=%s' % os.environ['POM_VERSION'])

                build = app_build.bn_build()
                app_patch = patch.bn_patch
                app_installation = patch.bn_installation
            elif name == 'stn':
                build = app_build.stn_build()
                app_patch = patch.stn_patch
                app_installation = patch.stn_installation
            elif name == 'umebn':
                build = app_build.umebn_build()
                app_patch = patch.umebn_patch
                app_installation = patch.umebn_installation
            else:
                build = app_build.sdno_build()
                app_patch = patch.sdno_patch
                app_installation = patch.sdno_installation

            if command == 'updateall':
                branch = arg[0]

                if name in ('bn',):
                    return build.update(None, branch)
                else:
                    return build.update(branch)
            elif command == 'update':
                module, branch, *_ = arg

                if name in ('bn',):
                    return build.update(module, branch)
                else:
                    return build.update(branch)
            elif command == 'compile_base':
                cmd = arg[0]

                return build.compile_base(cmd)
            elif command == 'compile':
                module, cmd, clean, retry_cmd, dirname, lang, *_ = arg

                if clean in (True, ):
                    clean = True
                else:
                    clean = False

                id = build.metric_start(module)

                if name in ('bn',):
                    status = build.compile(module, cmd, clean, retry_cmd, dirname, lang)
                else:
                    status = build.compile(cmd, clean, retry_cmd, dirname)

                build.metric_end(id, status)

                return status
            elif command in ('package', 'update_package'):
                branch, type, *_ = arg

                if not version:
                    if not branch:
                        branch = 'master'

                    version = '%s_%s' % (branch, datetime.datetime.now().strftime('%Y%m%d'))

                if command == 'package':
                    return build.package(version, type)
                else:
                    return build.update_package(version, type)
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
            elif command == 'kw_compile':
                output, module, cmd, lang, *_ = arg

                with builtin_os.chdir(pwd) as _chdir:
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
            elif command == 'dashboard':
                module, paths, branch, *_ = arg

                if paths:
                    paths = string.split(paths)
                else:
                    paths = []

                id = build.metric_start(module, False)

                if name in ('bn',):
                    status = build.dashboard(module, paths, branch)
                else:
                    status = build.dashboard(paths, branch)

                build.metric_end(id, status)

                return status
            elif command == 'dashboard_gerrit':
                repos = builtin_os.join(const.SSH_GIT, os.environ.get('GERRIT_PROJECT'))
                revision = os.environ.get('GERRIT_PATCHSET_REVISION')
                branch = os.environ.get('GERRIT_BRANCH')

                if name in ('bn',):
                    return build.dashboard_gerrit(arg[0], repos, revision, branch)
                else:
                    return build.dashboard_gerrit(repos, revision, branch)
            elif command == 'dashboard_monitor':
                branch = arg[0]

                return build.dashboard_monitor(branch)
            elif command == 'patch_auto':
                return patch.auto()
            elif command == 'patch':
                path = arg[0]

                return app_patch(path).build()
            elif command == 'patch_init':
                path, branch, *_ = arg

                return app_patch(path).init(branch)
            elif command == 'patch_install':
                path, sp_next, type, *_ = arg

                if str(sp_next).lower() == 'true':
                    sp_next = True
                else:
                    sp_next = False

                display_version = None

                if os.environ.get('DISPLAY_VERSION'):
                    display_version = os.environ['DISPLAY_VERSION'].strip()

                return app_installation(path).install(version, display_version, sp_next, type)
            else:
                print(usage.strip())

                return False
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
