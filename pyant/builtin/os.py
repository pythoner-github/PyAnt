import os
import shutil

__all__ = ['chdir']

class chdir:
    def __init__(self, path):
        self.path = path
        self.cwd = os.getcwd()

        os.chdir(self.path)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        os.chdir(self.cwd)

class tmpdir:
    def __init__(self, path):
        self.path = path
        self.cwd = os.getcwd()

        os.makedirs(self.path, exist_ok = True)
        os.chdir(self.path)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        os.chdir(self.cwd)
        shutil.rmtree(self.path, ignore_errors = True)
