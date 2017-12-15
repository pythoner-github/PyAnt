import os
import os.path
import shutil

__all__ = ('abspath', 'join', 'normpath', 'chdir')

def abspath(path):
    return os.path.abspath(path).replace('\\', '/')

def join(path, *paths):
    return os.path.join(path, *paths).replace('\\', '/')

def normpath(path):
    return os.path.normpath(path).replace('\\', '/')

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
