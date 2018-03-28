import datetime
import os
import os.path
import re
import shutil
import sys

from pyant import check
from pyant.app import patch, const
from pyant.app import build as app_build
from pyant.builtin import os as builtin_os

__all__ = ('build',)

__build_name__ = ('bn', 'stn', 'umebn', 'sdno')
__build_command__ = (
    'updateall', 'update', 'compile_base', 'compile', 'package', 'check',
    'dashboard', 'dashboard_monitor',
    'patch_auto', 'patch', 'patch_init', 'patch_install',
    'kw_compile', 'kw_build'
)

def build(argv = None):
    if not argv:
        argv = sys.argv[1:]

    if len(argv) >= 3:
        name = argv[0]
        command = argv[1]
        home = argv[2]

        arg = []

        for x in argv[3:]:
            if x.startswith('mvn_'):
                arg.append(x.replace('_', ' '))
            elif x == '_':
                arg.append('')
            else:
                arg.append(x)

        if not name in __build_name__:
            print('name not found in (%s)' % ', '.join(__build_name__))

            return False

        if not command in __build_command__:
            print('command not found in (%s)' % ', '.join(__build_command__))

            return False

        os.makedirs(home, exist_ok = True)
        pwd = os.getcwd()

        if os.path.isdir(home):
            version = None

            if os.environ.get('VERSION'):
                os.environ['VERSION'] = os.environ['VERSION'].strip()

                if os.environ.get('VERSION'):
                    if not os.environ.get('POM_VERSION'):
                        os.environ['POM_VERSION'] = os.environ['VERSION'].upper().replace('_${date}', '').replace(' ', '')

                        print('export POM_VERSION=%s' % os.environ['POM_VERSION'])

                    version = os.environ['VERSION'].replace('_${date}', datetime.datetime.now().strftime('%Y%m%d'))

            with builtin_os.chdir(home) as chdir:
                if name == 'bn':
                    build = app_build.bn_build()
                elif name == 'stn':
                    build = app_build.stn_build()
                elif name == 'umebn':
                    build = app_build.umebn_build()
                else:
                    build = app_build.sdno_build()

                if command == 'updateall':
                    branch = None

                    if arg:
                        branch = arg[0]

                    if name in ('bn',):
                        return build.update(None, branch)
                    else:
                        return build.update(branch)
                elif command == 'update':
                    module, branch, *_ = expand_arg(arg, 2)

                    if name in ('bn',):
                        return build.update(module, branch)
                    else:
                        return build.update(branch)
                elif command == 'compile_base':
                    cmd = None

                    if arg:
                        cmd = arg[0]

                    return build.compile_base(cmd)
                elif command == 'compile':
                    module, cmd, clean, retry_cmd, dirname, lang, *_ = expand_arg(arg, 6)

                    id = build.metric_start(module)

                    if name in ('bn',):
                        status = build.compile(module, cmd, clean, retry_cmd, dirname, lang)
                    else:
                        status = build.compile(cmd, clean, retry_cmd, dirname)

                    build.metric_end(id, status)

                    return status
                elif command == 'package':
                    branch, type, *_ = expand_arg(arg, 2)

                    if not version:
                        if not branch:
                            branch = 'master'

                        version = '%s_%s' % (branch, datetime.datetime.now().strftime('%Y%m%d'))

                    return build.package(version, type)
                elif command == 'check':
                    if name in ('bn',):
                        status = True

                        for _name in bn.REPOS.keys():
                            if _name in ('ptn2'):
                                ignores = r'error_conf\.xml'
                            else:
                                ignores = None

                            chk = check.check(os.path.basename(bn.REPOS[_name]))
                            chk.notification = '<%s_CHECK 通知> 文件检查失败, 请尽快处理' % name.upper()

                            if not chk.check(ignores):
                                status = False

                        return status
                    else:
                        chk = check.check()
                        chk.notification = '<%s_CHECK 通知> 文件检查失败, 请尽快处理' % name.upper()

                        return chk.check()
                elif command == 'dashboard':
                    module, paths, branch, *_ = expand_arg(arg, 3)

                    id = build.metric_start(module, False)

                    if build.dashboard(module, paths, branch):
                        build.metric_end(id, True)

                        return True
                    else:
                        build.metric_end(id, False)

                        return False
                elif command == 'dashboard_monitor':
                    branch = None

                    if arg:
                        branch = arg[0]

                    return build.dashboard_monitor(branch)
                elif command == 'patch_auto':
                    return patch.auto()
                elif command == 'patch':
                    return patch.build(name, arg[0])
                elif command == 'patch_init':
                    if len(arg) > 1:
                        branch = arg[1]
                    else:
                        branch = 'master'

                    return patch.init(name, arg[0], branch)
                elif command == 'patch_install':
                    return patch.install(name, arg[0], version)
                elif command == 'kw_compile':
                    output = arg[0]
                    module = arg[1]

                    if len(arg) > 2:
                        cmd = arg[2]
                    else:
                        cmd = None

                    if len(arg) > 3:
                        lang = arg[3]
                    else:
                        lang = None

                    with builtin_os.chdir(pwd) as _chdir:
                        output = os.path.abspath(output)

                    path = os.path.join(output, name, module)

                    if name == 'bn':
                        if lang == 'cpp':
                            path += '_cpp'

                    kw_option = '--output "%s"' % os.path.join(path, 'kwinject/kwinject.out')

                    if cmd:
                        m = re.search(r'^(kwmaven|kwinject)\s+', cmd)

                        if m:
                            cmd = '%s %s %s' % (m.group(1), kw_option, m.string[m.end():])
                    else:
                        if name == 'bn':
                            if lang == 'cpp':
                                cmd = 'kwinject %s mvn install -U -fn' % kw_option
                            else:
                                cmd = 'kwmaven %s install -U -fn' % kw_option
                        else:
                            cmd = 'kwmaven %s install -U -fn' % kw_option

                    if name in ('bn', 'stn'):
                        if module in build.REPOS.keys() or module in ('wdm1', 'wdm2', 'wdm3'):
                            shutil.rmtree(os.path.join(path, 'kwinject'), ignore_errors = True)
                            os.makedirs(os.path.join(path, 'kwinject'), exist_ok = True)
                    else:
                        shutil.rmtree(os.path.join(path, 'kwinject'), ignore_errors = True)
                        os.makedirs(os.path.join(path, 'kwinject'), exist_ok = True)

                    if name == 'bn':
                        if module in ('wdm1', 'wdm2', 'wdm3'):
                            return build.compile(module, cmd, True, dirname = os.path.join('code_c/build/kw', module), lang = lang)
                        else:
                            return build.compile(module, cmd, True, lang = lang)
                    else:
                        return build.compile(module, cmd, True)
                elif command == 'kw_build':
                    module = arg[0]

                    if len(arg) > 1:
                        lang = arg[1]
                    else:
                        lang = None

                    path = os.path.join(name, module)

                    if name == 'bn':
                        if lang == 'cpp':
                            path += '_cpp'

                    if name in ('bn', 'stn'):
                        if module in build.REPOS.keys():
                            shutil.rmtree(os.path.join(path, 'kwbuild'), ignore_errors = True)
                            os.makedirs(os.path.join(path, 'kwbuild'), exist_ok = True)
                    else:
                        shutil.rmtree(os.path.join(path, 'kwbuild'), ignore_errors = True)
                        os.makedirs(os.path.join(path, 'kwbuild'), exist_ok = True)

                    return app_build.kw_build(name, path)
                else:
                    return True
        else:
            print('no such directory: %s' % os.path.normpath(home))

            return False
    else:
        usage = '''
Usage:
    name command home arg

    command:
        updateall           arg: branch
        update              arg: module branch
        compile_base        arg: cmd
        compile             arg: module cmd clean retry_cmd dirname lang
        package             arg: branch type
        check               arg:
        dashboard           arg: module, paths, branch
        dashboard_monitor   arg: branch
        patch_auto          arg:
        patch               arg: path
        patch_init          arg: path, branch
        patch_install       arg: path
        kw_compile          arg: output module cmd lang
        kw_build            arg: module lang
        '''

        print(usage.strip())

        return False

# ----------------------------------------------------------

def expand_arg(arg, size):
    dup = arg[:]

    if len(arg) < size:
        for i in range(size - len(arg)):
            dup.append(None)

    return dup
