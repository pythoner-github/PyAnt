import collections
import datetime
import glob
import os
import re
import subprocess

from pyant import command
from pyant.builtin import os as builtin_os

__all__ = ('clone', 'pull', 'log', 'info', 'config')

def clone(url, path = None, branch = None, arg = None):
    cmdline = 'git clone'

    if branch:
        cmdline += ' -b %s' % branch

    if arg:
        cmdline += ' %s -- %s' % (arg, url)
    else:
        cmdline += ' %s' % url

    if path:
        cmdline += ' %s' % os.path.normpath(path)

    cmd = command.command()

    for line in cmd.command(cmdline):
        print(line)

    if cmd.result():
        if not path:
            path = os.path.basename(url)

        if is_submodule(path):
            if not branch:
                branch = 'master'

            with builtin_os.chdir(path) as chdir:
                cmds = (
                    'git submodule init',
                    'git submodule update',
                    'git submodule foreach git checkout %s' % branch,
                    'git submodule foreach git pull'
                )

                for cmdline in cmds:
                    for line in cmd.command(cmdline):
                        print(line)

                    if not cmd.result():
                        return False

        return True
    else:
        return False

def pull(path = None, arg = None, revert = False):
    if not path:
        path = '.'

    if os.path.isdir(path):
        cmdline = 'git pull'

        if arg:
            cmdline += ' %s' % arg

        with builtin_os.chdir(path) as chdir:
            if revert:
                cmd = command.command()

                for line in cmd.command('git checkout -- .'):
                    print(line)

            cmd = command.command()

            for line in cmd.command(cmdline):
                print(line)

            if cmd.result():
                if is_submodule():
                    branch = 'master'

                    for key in config().keys():
                        m = re.search(r'^branch\.(.*)\.remote$', key)

                        if m:
                            branch = m.group(1)

                            break

                    if revert:
                        for line in cmd.command('git submodule foreach git checkout -- .'):
                            print(line)

                    cmds = (
                        'git submodule update',
                        'git submodule foreach git checkout %s' % branch,
                        'git submodule foreach git pull'
                    )

                    for cmdline in cmds:
                        for line in cmd.command(cmdline):
                            print(line)

                        if not cmd.result():
                            return False

                return True
            else:
                return False
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def log(path = None, arg = None, display = False):
    if not path:
        path = '.'

    if os.path.exists(path):
        if os.path.isdir(path):
            name = '.'
        else:
            name = os.path.basename(path)
            path = os.path.dirname(path)

        cmdline = 'git log'

        if arg:
            cmdline += ' %s' % arg
        else:
            cmdline += ' -1 --stat=256'

        cmdline += ' -- %s' % subprocess.list2cmdline([name]).strip()

        with builtin_os.chdir(path) as chdir:
            lines = []

            cmd = command.command()

            for line in cmd.command(cmdline):
                lines.append(line)

                if display:
                    print(line)

                # if re.search(r'^\$\s+', line.strip()) or re.search(r'^in\s+\(.*\)$', line.strip()):
                #     print(line)

            if cmd.result():
                logs = []

                info = None
                comment = False

                git_home = home()

                if not git_home:
                    git_home = os.getcwd()

                for line in lines:
                    line = line.rstrip()

                    m = re.search(r'^commit\s+([0-9a-fA-F]+)$', line.strip())

                    if m:
                        if info:
                            logs.append(info)

                        info = {
                          'revision': m.group(1),
                          'author'  : None,
                          'email'   : None,
                          'date'    : None,
                          'comment' : None,
                          'changes' : None
                        }

                        comment = False

                        continue

                    m = re.search(r'^Author\s*:\s*(.*?)\s*<(.*?)>$', line.strip())

                    if m:
                        info['author'] = m.group(1)
                        info['email'] = m.group(2)

                        continue

                    m = re.search(r'^Date\s*:\s*', line.strip())

                    if m:
                        try:
                            info['date'] = datetime.datetime.strptime(m.string[m.end():], "%a %b %d %H:%M:%S %Y %z")
                        except:
                            pass

                        comment = True

                        continue

                    m = re.search(r'\|\s+(\d+\s+([+-]*)|Bin\s+(\d+)\s+->\s+(\d+)\s+bytes)$', line.strip())

                    if m:
                        name = m.string[:m.start()].strip()

                        tmp_m = re.search(r'^\.{3}\/', name)

                        if tmp_m:
                            with builtin_os.chdir(git_home) as chdir:
                                for file in glob.iglob(os.path.join('**', tmp_m.string[tmp_m.end():]), recursive = True):
                                    name = file

                        if m.group(2):
                            if '+' in m.group(2) and '-' in m.group(2):
                                if not info['changes']:
                                    info['changes'] = {}

                                if 'update' not in info['changes']:
                                    info['changes']['update'] = []

                                info['changes']['update'].append(name)
                            else:
                                if '+' in m.group(2):
                                    if not info['changes']:
                                        info['changes'] = {}

                                    if 'add' not in info['changes']:
                                        info['changes']['add'] = []

                                    info['changes']['add'].append(name)
                                else:
                                    if not info['changes']:
                                        info['changes'] = {}

                                    if 'delete' not in info['changes']:
                                        info['changes']['delete'] = []

                                    info['changes']['delete'].append(name)
                        else:
                            if m.group(3) == '0':
                                if not info['changes']:
                                    info['changes'] = {}

                                if 'add' not in info['changes']:
                                    info['changes']['add'] = []

                                info['changes']['add'].append(name)
                            else:
                                if m.group(4) == '0':
                                    if not info['changes']:
                                        info['changes'] = {}

                                    if 'delete' not in info['changes']:
                                        info['changes']['delete'] = []

                                    info['changes']['delete'].append(name)
                                else:
                                    if not info['changes']:
                                        info['changes'] = {}

                                    if 'update' not in info['changes']:
                                        info['changes']['update'] = []

                                    info['changes']['update'].append(name)

                        comment = False

                        continue

                    if comment:
                        if line:
                            if not info.get('comment'):
                                info['comment'] = []

                            info['comment'].append(line)
                        else:
                            if info.get('comment'):
                                if info['comment'][-1]:
                                    info['comment'].append(line)

                        continue

                if info:
                    logs.append(info)

                logs.reverse()

                return logs
            else:
                return None
    else:
        print('no such file or directory: %s' % os.path.normpath(path))

        return None

def info(path = None):
    map = None

    logs = log(path)

    if logs:
        map = logs[-1]

        conf = config(path)

        if conf:
            url = conf.get('remote.origin.url')

            if url:
                m = re.search(r':\/\/(.*?)@', url)

                if m:
                    url = '%s://%s' % (m.string[:m.start()], m.string[m.end():])

                if path:
                    git_home = home(path)

                    if git_home:
                        map['url'] = builtin_os.join(url, os.path.relpath(path, git_home))
                else:
                    map['url'] = url

    return map

def reset(path = None, branch = None):
    if not path:
        path = '.'

    if not branch:
        branch = 'master'

    if os.path.isdir(path):
        with builtin_os.chdir(path) as chdir:
            cmd = command.command()

            for line in cmd.command('git checkout -f -B %s' % branch):
                print(line)

            if not cmd.result():
                return False

            for line in cmd.command('git reset --hard origin/%s' % branch):
                print(line)

            if not cmd.result():
                return False

            return True
    else:
        print('no such directory: %s' % os.path.normpath(path))

        return False

def config(path = None, arg = None):
    if not path:
        path = '.'

    if os.path.isfile(path):
        path = os.path.dirname(path)

    conf = {}

    if os.path.isdir(path):
        cmdline = 'git config'

        if arg:
            cmdline += ' %s' % arg

        cmdline += ' --list'

        with builtin_os.chdir(path) as chdir:
            lines = []

            cmd = command.command()

            for line in cmd.command(cmdline):
                lines.append(line)

            if cmd.result():
                for line in lines:
                    m = re.search(r'=', line)

                    if m:
                        conf[m.string[:m.start()]] = m.string[m.end():]
    else:
        print('no such directory: %s' % os.path.normpath(path))

    return conf

# ----------------------------------------------------------

def home(path = None):
    if not path:
        path = '.'

    path = os.path.abspath(path)

    if os.path.isfile(path):
        path = os.path.dirname(path)

    if os.path.isdir(path):
        if os.path.isdir(os.path.join(path, '.git')):
            return path
        else:
            if os.path.dirname(path) == path:
                return None
            else:
                return home(os.path.dirname(path))
    else:
        return None

def is_submodule(path = None):
    if not path:
        path = '.'

    return os.path.isfile(os.path.join(path, '.gitmodules'))
