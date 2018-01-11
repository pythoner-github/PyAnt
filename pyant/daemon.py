import glob
import os
import os.path
import shutil

import Pyro4

from pyant import command, smtp
from pyant.builtin import os as builtin_os

__all__ = ('PyroCommandProxy', 'PyroFileProxy', 'daemon')

@Pyro4.expose
class PyroCommand():
    def __init__(self):
        self.cmd = None

    def command(self, cmdline, timeout = None, cwd = None, async = False, display_cmd = None):
        self.cmd = command.command()

        for line in self.cmd.command(cmdline, timeout, cwd, async, display_cmd):
            yield line

    def result(self, returncode = 0):
        if self.cmd:
            return self.cmd.result(returncode)
        else:
            return None

@Pyro4.expose
class PyroFile():
    def __init__(self):
        self.cache = {}

    def copy_file(self, name, data = None):
        name = os.path.abspath(name)

        if data:
            if name not in self.cache:
                if not os.path.isdir(os.path.dirname(name)):
                    os.makedirs(os.path.dirname(name), exist_ok = True)

                self.cache[name] = {
                    'file': open(name, 'wb'),
                    'addr': Pyro4.current_context.client_sock_addr
                }

            if Pyro4.current_context.client_sock_addr != self.cache[name]['addr']:
                return False

            self.cache[name]['file'].write(data)

            return True
        else:
            if name in self.cache:
                try:
                    self.cache[name]['file'].close()
                finally:
                    del self.cache[name]

            return True

    def delete_file(self, name):
        name = os.path.abspath(name)
        shutil.rmtree(name, ignore_errors = True)

        return True

    def mkdir(self, name):
        name = os.path.abspath(name)
        os.makedirs(name, exist_ok = True)

        return True

    def close(self):
        for name in self.cache:
            try:
                self.cache[name]['file'].close()
            except:
                pass

        self.cache = {}

        return True

    def glob(self, xpath):
        return glob.glob(xpath, recursive = True)

    def exists(self, path):
        return os.path.exists(path)

    def isfile(self, path):
        return os.path.isfile(path)

    def isdir(self, path):
        return os.path.isdir(path)

@Pyro4.expose
class PyroMail():
    def __init__(self):
        pass

    def sendmail(self, from_addr, to_addrs, string):
        return smtp.smtp_sendmail(from_addr, to_addrs, string)

class PyroCommandProxy():
    def __init__(self, ip):
        self.proxy = Pyro4.Proxy('PYRO:daemon.command@%s:9000' % ip)

    def command(self, cmdline, timeout = None, cwd = None, async = False, display_cmd = None):
        try:
            for line in self.proxy.command(cmdline, timeout, cwd, async, display_cmd):
                print(line)

            if self.proxy.result():
                return True
            else:
                return False
        except Exception as e:
            print(e)

            return False

class PyroFileProxy():
    def __init__(self, ip):
        self.proxy = Pyro4.Proxy('PYRO:daemon.file@%s:9000' % ip)

    def copy_file(self, file, name):
        if os.path.isfile(file):
            try:
                status = True

                with open(file, 'rb') as f:
                    while True:
                        data = f.read(64 * 1024)

                        if not data:
                            break

                        if not self.proxy.copy_file(name, data):
                            status = False

                            break

                self.proxy.copy_file(name)

                return status
            except Exception as e:
                print(e)

                return False
        else:
            print('no such file: %s' % os.path.normpath(file))

            return False

    def copy(self, path, name):
        if os.path.exists(path):
            if os.path.isfile(path):
                return self.copy_file(path, name)
            elif os.path.isdir(path):
                with builtin_os.chdir(path) as chdir:
                    for file in glob.iglob('**/*', recursive = True):
                        if os.path.isfile(file):
                            if not self.copy_file(file, os.path.join(name, file)):
                                return False
                        elif os.path.isdir(file):
                            if not self.mkdir(os.path.join(name, file)):
                                return False
                        else:
                            pass

                return True
            else:
                pass
        else:
            print('no such file or directory: %s' % os.path.normpath(path))

            return False

    def delete_file(self, name):
        try:
            return self.proxy.delete_file(name)
        except Exception as e:
            print(e)

            return False

    def mkdir(self, name):
        try:
            return self.proxy.mkdir(name)
        except Exception as e:
            print(e)

            return False

    def close(self):
        try:
            return self.proxy.close()
        except Exception as e:
            print(e)

            return False

    def glob(self, xpath):
        try:
            return self.proxy.glob(xpath)
        except Exception as e:
            print(e)

            return None

    def exists(self, path):
        try:
            return self.proxy.exists(path)
        except Exception as e:
            print(e)

            return None

    def isfile(self, path):
        try:
            return self.proxy.isfile(path)
        except Exception as e:
            print(e)

            return None

    def isdir(self, path):
        try:
            return self.proxy.isdir(path)
        except Exception as e:
            print(e)

            return None

def daemon():
    with Pyro4.Daemon(host = '0.0.0.0', port = 9000) as daemon:
        print(daemon.register(PyroCommand, 'daemon.command'))
        print(daemon.register(PyroFile, 'daemon.file'))
        print(daemon.register(PyroMail, 'daemon.mail'))

        daemon.requestLoop()
