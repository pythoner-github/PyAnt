import datetime
import os
import os.path
import sys

from pyant import command
from pyant.app import bn, stn, umebn, sdno, const
from pyant.builtin import os as builtin_os

__all__ = ['build']

__build_name__ = ('bn', 'stn', 'umebn', 'sdno')
__build_command__ = ('updateall', 'update', 'compile_base', 'compile', 'package')

def build(argv = None):
    if not argv:
        argv = sys.argv[1:]

    if len(argv) >= 3:
        name = argv[0]
        command = argv[1]
        home = argv[2]
        arg = argv[3:]

        if not name in __build_name__:
            print('name not found in (%s)' % ', '.join(__build_name__))

            return False

        if not command in __build_command__:
            print('command not found in (%s)' % ', '.join(__build_command__))

            return False

        os.makedirs(home, exist_ok = True)

        if os.path.isdir(home):
            if os.environ.get('VERSION'):
                if not os.environ.get('POM_VERSION'):
                    os.environ['POM_VERSION'] = os.environ['VERSION'].upper().replace(' ', '')

                    print('export POM_VERSION=%s' % os.environ['POM_VERSION'])

            with builtin_os.chdir(home) as dir:
                if name == 'bn':
                    build = bn
                elif name == 'stn':
                    build = stn
                elif name == 'umebn':
                    build = umebn
                else:
                    build = sdno

                if command == 'updateall':
                    if arg:
                        branch = arg[0]
                    else:
                        branch = None

                    if name in ['bn', 'stn']:
                        status = True

                        for module in build.REPOS.keys():
                            if not build.update(module, branch):
                                status = False

                        return status
                    else:
                        return build.update(None, branch);
                elif command == 'update':
                    return build.update(*arg)
                elif command == 'compile_base':
                    return build.compile_base(*arg)
                elif command == 'compile':
                    if arg:
                        module_name = arg[0]
                    else:
                        module_name = None

                    id = metric_start(metric_id(name, module_name), module_name)

                    if build.compile(*arg):
                        metric_end(id, True)

                        return True
                    else:
                        metric_end(id, False)

                        return False
                elif command == 'package':
                    return build.package(*arg)
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
        updateall       arg: branch
        update          arg: module branch
        compile_base    arg: module cmd
        compile         arg: module cmd clean retry_cmd dirname lang
        package         arg:
        '''

        print(usage.strip())

        return False

def metric_id(name, module_name = None):
    if name == 'bn':
        if module_name in ('interface', 'platform', 'necommon', 'uca', 'sdh', 'ptn'):
            return const.METRIC_ID_BN_IPTN
        elif module_name in ('ptn2', 'ip'):
            return const.METRIC_ID_BN_IPTN_NJ
        elif module_name in ('e2e'):
            return const.METRIC_ID_BN_E2E
        elif module_name in ('xmlfile', 'nbi'):
            return const.METRIC_ID_BN_NBI
        elif module_name in ('wdm'):
            return const.METRIC_ID_BN_OTN
        else:
            return None
    elif name == 'stn':
        return const.METRIC_ID_STN
    elif name == 'umebn':
        return const.METRIC_ID_UMEBN
    elif name == 'sdno':
        return const.METRIC_ID_SDNO
    else:
        return None

def metric_start(id, module_name = None, night = True):
    cmdline = None

    if not module_name:
        module_name = ''

    if os.environ.get('METRIC'):
        if id:
            if night:
                hour = datetime.datetime.now().hour

                if 0 <= hour <=8 or hour >= 22:
                    cmdline = 'curl --data "action=buildstart&project=%s&buildtype=night&item=%s" %s' % (id, module_name, const.HTTP_METRIC)
            else:
                cmdline = 'curl --data "action=buildstart&project=%s&buildtype=CI&item=%s" %s' % (id, module_name, const.HTTP_METRIC)

    if cmdline:
        lines = []

        cmd = command.command()

        for line in cmd.command(cmdline):
            lines.append(line)

            print(line)

        if cmd.result():
            return ''.join(lines[2:]).strip()
        else:
            return None
    else:
        return None

def metric_end(id, status):
    if id:
        if status:
            success = 'success'
        else:
            success = 'failed'

        cmdline = 'curl --data "action=buildend&buildid=%s&buildresult=%s" %s' % (id, success, const.HTTP_METRIC)

        cmd = command.command()

        for line in cmd.command(cmdline):
            print(line)
