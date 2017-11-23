import locale
import os
import time
import subprocess

__all__ = ['command']

class command:
    def __init__(self):
        self.pipe = None
        self.async = False

    def command(self, args, timeout = None, cwd = None, async = False):
        self.pipe = None
        self.async = async

        try:
            self.pipe = subprocess.Popen(args, stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT, stdin = subprocess.PIPE, cwd = cwd
            )
        except:
            self.pipe = subprocess.Popen(args, stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT, stdin = subprocess.PIPE, cwd = cwd,
                shell = True
            )

        if isinstance(args, str):
            cmd = args.strip()
        else:
            cmd = subprocess.list2cmdline([arg.strip() for arg in args])

        for line in ('$ ' + cmd, '  (' + os.getcwd() + ')'):
            yield line

        t = time.time()

        while True:
            if self.async:
                break

            if timeout:
                if (time.time() - t) > timeout:
                    self.pipe.kill()

                    timeout = None

            line = self.pipe.stdout.readline()

            if line:
                yield line.decode(locale.getpreferredencoding(False)).rstrip()
            else:
                break

        self.pipe.wait()

    def peek_line(self, size = 200):
        line = ''

        if self.pipe:
            if not self.pipe.stdout.closed:
                data = self.pipe.stdout.peek(size)

                if data:
                    line = data.splitlines()[0].decode(locale.getpreferredencoding(False)).rstrip()

        line

    def input(self, string):
        if self.pipe:
            if not self.pipe.stdin.closed:
                self.pipe.stdin.write(string.encode(locale.getpreferredencoding(False)))
                self.pipe.stdin.flush()

    def result(self, returncode = 0):
        if not isinstance(returncode, list):
            returncode = [returncode]

        if self.pipe:
            if self.pipe.returncode in returncode:
                return True
            else:
                return False
        else:
            return None