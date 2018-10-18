import collections
import os
import os.path
import re

from pyant import command, git, maven
from pyant.app import const, __dashboard__
from pyant.builtin import __os__

from pyant.app.bn import build

__all__ = ('dashboard',)

class dashboard(__dashboard__):
    def __init__(self):
        super().__init__('bn', build.build().repos)

    def dashboard_monitor(self, branch = None):
        if not self.update(None, branch):
            return False

        path_info = collections.OrderedDict()

        for module in self.repos:
            path_info[os.path.basename(self.repos[module])] = module

        if os.environ.get('JOB_NAME'):
            job_home = os.path.dirname(os.environ['JOB_NAME'])
        else:
            job_home = os.path.join(self.path, 'dashboard')

        for path, (authors, paths) in self.__dashboard_monitor__(path_info.keys(), self.expand_dashboard).items():
            self.dashboard_jenkins_cli(os.path.join(job_home, '%s_dashboard_%s' % (self.name, path_info[path])), authors, paths)

        return True

    def dashboard(self, module, paths, branch = None):
        modules = []

        if module in ('ptn', 'ptn2'):
            modules = ['ptn', 'ptn2']
        else:
            modules = [module]

        for _module in modules:
            module_path = os.path.basename(self.repos[_module])

            if os.path.isdir(module_path):
                if not git.reset(module_path, branch):
                    return False

            if not self.update(_module, branch):
                return False

        if not os.environ.get('NOT_DASHBOARD_DEVTOOLS'):
            if not self.update('devtools', branch):
                return False

        self.environ('cpp')

        self.path = os.path.basename(self.repos[module])

        if os.path.isdir(self.path):
            with __os__.chdir(self.path) as chdir:
                return self.__dashboard__(paths)
        else:
            print('no such directory: %s' % os.path.normpath(self.path))

            return False

    def dashboard_gerrit(self, module, repos, revision, branch = None):
        modules = []

        if module in ('ptn', 'ptn2'):
            modules = ['ptn', 'ptn2']
        else:
            modules = [module]

        for _module in modules:
            module_path = os.path.basename(self.repos[_module])

            if os.path.isdir(module_path):
                if not git.reset(module_path, branch):
                    return False

            if not self.update(_module, branch):
                return False

        if not os.environ.get('NOT_DASHBOARD_DEVTOOLS'):
            if not self.update('devtools', branch):
                return False

        self.environ('cpp')

        status = True

        module_path = os.path.basename(self.repos[module])

        if os.path.isdir(module_path):
            try:
                with __os__.chdir(module_path) as chdir:
                    cmd = command.command()

                    for line in cmd.command('git fetch %s +refs/changes/*:refs/changes/*' % repos):
                        print(line)

                    if not cmd.result():
                        return False

                    for line in cmd.command('git checkout -f %s' % revision):
                        print(line)

                    if not cmd.result():
                        return False

                    status = True

                    logs = git.log(None, '-1 --stat=256 %s' % revision, True)

                    if logs:
                        paths = []

                        for log in logs:
                            if log['changes']:
                                for k, v in log['changes'].items():
                                    for file in v:
                                        filenames = (file,)

                                        for filename in filenames:
                                            dir = self.pom_path(filename)

                                            if dir:
                                                if re.search(r'^code_c\/database\/.*\/xml\/.*\.xml$', filename):
                                                    if os.path.isfile('code_c/database/dbscript/pom.xml'):
                                                        if os.path.isfile(os.path.join(os.path.dirname(filename), '../pom.xml')):
                                                            if 'code_c/database/dbscript' not in paths:
                                                                paths.append('code_c/database/dbscript')

                                                if dir not in paths:
                                                    paths.append(dir)
                                            else:
                                                if module in ('interface',):
                                                    if filename.startswith('code/asn/'):
                                                        if 'code/finterface' not in paths:
                                                            paths.append('code/finterface')

                                                        if 'code_c/finterface' not in paths:
                                                            paths.append('code_c/finterface')
                                                    else:
                                                        if filename.startswith('code_c/asn/sdh-wdm/qx-interface/asn/'):
                                                            dir = 'code_c/qxinterface/qxinterface'
                                                        elif filename.startswith('code_c/asn/sdh-wdm/qx-interface/asn5800/'):
                                                            dir = 'code_c/qxinterface/qx5800'
                                                        elif filename.startswith('code_c/asn/sdh-wdm/qx-interface/asnwdm721/'):
                                                            dir = 'code_c/qxinterface/qxwdm721'
                                                        elif filename.startswith('code_c/asn/otntlvqx/'):
                                                            dir = 'code_c/qxinterface/qxotntlv'
                                                        else:
                                                            pass

                                                        if dir:
                                                            if dir not in paths:
                                                                paths.append(dir)

                        paths = self.expand_dashboard_gerrit(module, paths)

                        for path in paths:
                            if os.path.isdir(path):
                                lang = None

                                if __os__.normpath(path).startswith('code_c/'):
                                    lang = 'cpp'

                                with __os__.chdir(path) as chdir:
                                    if module in ('interface',):
                                        mvn = maven.maven()
                                        mvn.notification = '<%s_DASHBOARD_GERRIT_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper()

                                        mvn.clean()

                                        cmdline = 'mvn install -fn -U'

                                        if not mvn.compile(cmdline, None, lang):
                                            status = False

                                            continue
                                    else:
                                        if not self.kw_check('.', lang):
                                            status = False

                                            continue
            finally:
                git.reset(module_path, branch)
                git.pull(module_path, revert = True)

        return status

    # ------------------------------------------------------

    def update(self, module, branch = None):
        return build.build().update(module, branch)

    def environ(self, lang = None):
        return build.build().environ(lang)

    def expand_dashboard(self, path, file):
        file = __os__.normpath(file)

        if path in ('U31R22_INTERFACE',):
            if file.startswith('code/asn/'):
                return ('code/finterface', 'code_c/finterface')
            elif file.startswith('code_c/asn/sdh-wdm/qx-interface/asn/'):
                return 'code_c/qxinterface/qxinterface'
            elif file.startswith('code_c/asn/sdh-wdm/qx-interface/asn5800/'):
                return 'code_c/qxinterface/qx5800'
            elif file.startswith('code_c/asn/sdh-wdm/qx-interface/asnwdm721/'):
                return 'code_c/qxinterface/qxwdm721'
            elif file.startswith('code_c/asn/otntlvqx/'):
                return 'code_c/qxinterface/qxotntlv'
            else:
                return file
        elif path in ('U31R22_NBI',):
            if file.startswith('code_c/adapters/xtncorba/corbaidl/'):
                return ('code_c/adapters/xtncorba/corbaidl/corbaidl_common', 'code_c/adapters/xtncorba/corbaidl/corbaidl')
            elif file.startswith('code_c/adapters/xtntmfcorba/corbaidl/'):
                return ('code_c/adapters/xtntmfcorba/corbaidl/corbaidl_common', 'code_c/adapters/xtntmfcorba/corbaidl/corbaidl')
            else:
                return file
        else:
            if re.search(r'^code_c\/database\/.*\/xml\/.*\.xml$', file):
                if os.path.isfile('code_c/database/dbscript/pom.xml'):
                    if os.path.isfile(os.path.join(os.path.dirname(file), '../pom.xml')):
                        return ('code_c/database/dbscript', file)

            return file

    def expand_dashboard_gerrit(self, module, paths):
        _paths = []

        for path in paths:
            _path = path

            if module in ('U31R22_INTERFACE',):
                if path.startswith('code/finterface'):
                    _path = 'code/finterface'
                elif path.startswith('code/netconf'):
                    _path = 'code/netconf'
                elif path.startswith('code/otn/wdmqx'):
                    _path = 'code/otn/wdmqx'
                elif path.startswith('code/ptn/qx'):
                    _path = 'code/ptn/qx'
                elif path.startswith('code/ptn/netconf_sptn'):
                    _path = 'code/ptn/netconf_sptn'
                elif path.startswith('code_c/finterface'):
                    _path = 'code_c/finterface'
                elif path.startswith('code_c/qxinterface/qxinterface'):
                    _path = 'code_c/qxinterface/qxinterface'
                elif path.startswith('code_c/qxinterface/qx5800'):
                    _path = 'code_c/qxinterface/qx5800'
                elif path.startswith('code_c/qxinterface/qxwdm721'):
                    _path = 'code_c/qxinterface/qxwdm721'
                elif path.startswith('code_c/qxinterface/qxotntlv'):
                    _path = 'code_c/qxinterface/qxotntlv'
                else:
                    _path = path
            elif module in ('U31R22_NBI',):
                if path.startswith('code_c/adapters/xtncorba/corbaidl'):
                    if 'code_c/adapters/xtncorba/corbaidl/corbaidl_common' not in _paths:
                        _paths.append('code_c/adapters/xtncorba/corbaidl/corbaidl_common')

                    path = 'code_c/adapters/xtncorba/corbaidl/corbaidl'
                elif path.startswith('code_c/adapters/xtntmfcorba/corbaidl'):
                    if 'code_c/adapters/xtntmfcorba/corbaidl/corbaidl_common' not in _paths:
                        _paths.append('code_c/adapters/xtntmfcorba/corbaidl/corbaidl_common')

                    path = 'code_c/adapters/xtntmfcorba/corbaidl/corbaidl'
                else:
                    _path = path
            else:
                _path = path

            if _path not in _paths:
                _paths.append(_path)

        return _paths

    def kw_check_fixed(self, defect):
        branch = 'master'

        git_home = git.home()

        for k in git.config():
            m = re.search(r'^branch\.(.*)\.remote$', k)

            if m:
                branch = m.group(1)

        lines = []

        cmd = command.command()

        for line in cmd.command('git rev-list -n 1 --before="%s" %s' % (const.KLOCWORK_DATE, branch)):
            lines.append(line)

        if not cmd.result():
            return defect

        commit = lines[-1]

        lines = []

        for line in cmd.command('git diff %s' % commit):
            lines.append(line)

        fixed_defect = {}

        diff_info = self.diff(lines, git_home)

        for severity in defect:
            for code in defect[severity]:
                for info in defect[severity][code]:
                    if info['file'] not in diff_info:
                        continue

                    if int(info['line']) in diff_info[info['file']]:
                        if severity not in fixed_defect:
                            fixed_defect[severity] = {}

                        if code not in fixed_defect[severity]:
                            fixed_defect[severity][code] = []

                        fixed_defect[severity][code].append(info)

        return fixed_defect

    def diff(self, lines, git_home = None):
        info = {}

        tmp_lines = []

        for line in lines:
            line = line.strip()

            m = re.search(r'^diff\s+--git\s+a\/(.*)\s+b/.*$', line)

            if m:
                if tmp_lines:
                    filename, diff_info = self.diff_lines(tmp_lines, git_home)

                    if not info.get(filename):
                        info[filename] = []

                    info[filename] += diff_info

                tmp_lines = []

            tmp_lines.append(line)

        if tmp_lines:
            filename, diff_info = self.diff_lines(tmp_lines, git_home)

            if not info.get(filename):
                info[filename] = []

            info[filename] += diff_info

        return info

    def diff_lines(self, lines, git_home = None):
        if git_home is None:
            git_home = '.'

        filename = None
        diff_info = []

        lineno = -1

        for line in lines:
            m = re.search(r'^diff\s+--git\s+a\/(.*)\s+b/.*$', line)

            if m:
                with __os__.chdir(git_home) as chdir:
                    filename = os.path.abspath(m.group(1))

                continue

            m = re.search(r'^\++\s+\/dev\/null$', line)

            if m:
                filename = None
                break

            m = re.search(r'^@@\s+-(\d+),(\d+)\s+\+(\d+),(\d+)\s+@@.*$', line)

            if m:
                lineno = int(m.group(3))
                continue

            if lineno > -1:
                m = re.search(r'^-.*$', line)

                if m:
                    continue

                m = re.search(r'^\+.*$', line)

                if m:
                    diff_info.append(lineno)

                lineno += 1

        return (filename, diff_info)
