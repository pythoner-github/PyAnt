import datetime
import os
import os.path
import sys
import xml.etree.ElementTree

from pyant.app import bn, stn, umebn, sdno, const
from pyant.app import build as app_build
from pyant.builtin import os as builtin_os

__all__ = ['build']

__build_name__ = ('bn', 'stn', 'umebn', 'sdno')
__build_command__ = ('updateall', 'update', 'compile_base', 'compile', 'package', 'check')

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

                    id = app_build.metric_start(name, module_name)

                    if build.compile(*arg):
                        app_build.metric_end(id, True)

                        return True
                    else:
                        app_build.metric_end(id, False)

                        return False
                elif command == 'package':
                    if os.environ.get('VERSION'):
                        version = os.environ['VERSION']
                    else:
                        if arg:
                            branch = arg[0]
                        else:
                            branch = 'master'

                        version = '%s_%s' % (datetime.datetime.now().strftime('%Y%m%d'), branch)

                    return build.package(version, *arg)
                elif command == 'check':
                    if name == 'bn':
                        return app_build.check('U31R22_*', r'error_conf\.xml')
                    else:
                        return app_build.check()
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
        package         arg: branch
        check           arg:
        '''

        print(usage.strip())

        return False
