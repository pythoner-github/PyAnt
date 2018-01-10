import os
import os.path
import platform
import shutil

__all__ = ('abspath', 'join', 'normpath', 'osname', 'chdir', 'tmpdir')

def abspath(path):
    return os.path.abspath(path).replace('\\', '/')

def join(path, *paths):
    return os.path.join(path, *paths).replace('\\', '/')

def normpath(path):
    return os.path.normpath(path).replace('\\', '/')

def osname():
    if platform.system().lower() == 'linux':
        return 'linux'
    elif platform.system().lower() == 'sunos':
        return 'solaris'
    elif platform.system().lower() == 'windows':
        if os.environ.get('WIN64') == '1':
            return 'windows-x64'
        else:
            return 'windows'
    else:
        return None

class chdir:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.cwd = os.getcwd()

        os.chdir(self.path)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        os.chdir(self.cwd)

class tmpdir:
    def __init__(self, path, create = True):
        self.path = os.path.abspath(path)
        self.cwd = os.getcwd()

        if create:
            os.makedirs(self.path, exist_ok = True)

        os.chdir(self.path)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        os.chdir(self.cwd)
        shutil.rmtree(self.path, ignore_errors = True)
