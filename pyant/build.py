import os
import os.path
import sys

from pyant.app import bn, stn, umebn, sdno
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
                    return build.compile(*arg)
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
