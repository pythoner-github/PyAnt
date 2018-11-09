import collections
import json
import os
import os.path

from lxml import etree

from pyant import check, command, git, maven, password, smtp
from pyant.app import const
from pyant.builtin import __os__, __string__

from pyant.app import build

__all__ = ('dashboard',)

class dashboard:
    def __init__(self, name, repos):
        self.name = name
        self.repos = repos
        self.path = self.name

    def dashboard_monitor(self, branch = None):
        if not self.update(branch):
            return False

        if os.environ.get('JOB_NAME'):
            job_home = os.path.dirname(os.environ['JOB_NAME'])
        else:
            job_home = os.path.join(self.path, 'dashboard')

        for path, (authors, paths) in self.__dashboard_monitor__([self.path], self.expand_dashboard).items():
            self.dashboard_jenkins_cli(os.path.join(job_home, '%s_dashboard' % self.name), authors, paths)

        return True

    def dashboard(self, paths, branch = None):
        if os.path.isdir(self.path):
            if not git.reset(self.path, branch):
                return False

        if not self.update(branch):
            return False

        if os.path.isdir(self.path):
            with __os__.chdir(self.path) as chdir:
                return self.__dashboard__(paths)
        else:
            print('no such directory: %s' % os.path.normpath(self.path))

            return False

    def dashboard_gerrit(self, repos, revision, branch = None):
        if os.path.isdir(self.path):
            if not git.reset(self.path, branch):
                return False

        if not self.update(branch):
            return False

        status = True

        if os.path.isdir(self.path):
            try:
                with __os__.chdir(self.path) as chdir:
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
                        paths = collections.OrderedDict()

                        for log in logs:
                            if log['changes']:
                                for k, v in log['changes'].items():
                                    if k in ('delete',):
                                        continue

                                    for file in v:
                                        if os.path.splitext(file)[-1] in ('.java',):
                                            path = self.pom_path(file)

                                            if path:
                                                if path not in paths:
                                                    paths[path] = []

                                                paths[path].append(os.path.abspath(file))

                        for path in paths:
                            if os.path.isdir(path):
                                lang = None

                                if __os__.normpath(path).startswith('code_c/'):
                                    lang = 'cpp'

                                with __os__.chdir(path) as chdir:
                                    if path in ('code_c/build',):
                                        mvn = maven.maven()

                                        if not mvn.clean():
                                            if os.environ.get('GERRIT_EMAIL'):
                                                admin_addrs = None

                                                if os.environ.get('SENDMAIL.ADMIN'):
                                                    admin_addrs = __string__.split(os.environ.get('SENDMAIL.ADMIN'))

                                                line = ''

                                                if os.environ.get('BUILD_URL'):
                                                    console_url = __os__.join(os.environ['BUILD_URL'], 'console')
                                                    line = '详细信息: <a href="%s">%s</a>' % (console_url, console_url)

                                                smtp.sendmail(
                                                    '<%s_DASHBOARD_GERRIT_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper(),
                                                    os.environ['GERRIT_EMAIL'], admin_addrs, line
                                                )

                                            return False
                                        else:
                                            return True

                                    # mvn = maven.maven()
                                    # mvn.notification = '<%s_DASHBOARD_GERRIT_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper()
                                    #
                                    # mvn.clean()
                                    #
                                    # cmdline = 'mvn install -fn -U'
                                    #
                                    # if not mvn.compile(cmdline, 'mvn install -fn -U'):
                                    #     status = False
                                    #
                                    #     continue

                                    if not self.kw_check('.', lang, paths[path]):
                                        status = False

                                        continue
            finally:
                git.reset(self.path, branch)
                git.pull(self.path, revert = True)

        return status

    # ------------------------------------------------------

    # path:
    #   (authors, paths)
    def __dashboard_monitor__(self, paths, expand_dashboard = None):
        rev = {}

        if os.path.isfile('change.rev'):
            try:
                with open('change.rev', encoding = 'utf8') as f:
                    rev = json.load(f)
            except Exception as e:
                print(e)

        changes = collections.OrderedDict()
        changes_rev = collections.OrderedDict()

        for path in paths:
            if os.path.isdir(os.path.join(path, '.git')):
                with __os__.chdir(path) as chdir:
                    if path in rev.keys():
                        arg = '--stat=256 %s..HEAD' % rev[path][:6]

                        logs = git.log(None, arg)

                        if logs:
                            authors = []
                            tmp_paths = []

                            for log in logs:
                                if log['changes']:
                                    if log['author'] not in authors:
                                        authors.append(log['author'])

                                    for k, v in log['changes'].items():
                                        for file in v:
                                            if expand_dashboard:
                                                filenames = expand_dashboard(path, file)

                                                if filenames:
                                                    if isinstance(filenames, str):
                                                        filenames = (filenames,)
                                                else:
                                                    filenames = ()
                                            else:
                                                filenames = (file,)

                                            for filename in filenames:
                                                dir = self.pom_path(filename)

                                                if dir:
                                                    if dir not in tmp_paths:
                                                        tmp_paths.append(dir)

                            if tmp_paths:
                                changes[path] = (authors, tmp_paths)

                            changes_rev[path] = logs[-1]['revision']
                        else:
                            changes_rev[path] = rev[path]
                    else:
                        info = git.info()

                        if info:
                            changes_rev[path] = info['revision']

        try:
            with open('change.rev', 'w', encoding = 'utf8') as f:
                json.dump(changes_rev, f)
        except Exception as e:
            print(e)

        print()
        print('*' * 40)

        for path, (authors, paths) in changes.items():
            print(path, (authors, paths))

        print('*' * 40)
        print()

        return changes

    def __dashboard__(self, paths, ignores = None):
        filename = os.path.abspath(os.path.join('../errors', '%s.json' % os.path.basename(os.getcwd())))

        if os.path.isfile(filename):
            try:
                with open(filename, encoding = 'utf8') as f:
                    tmp = []

                    for path in json.load(f):
                        if path not in paths:
                            tmp.append(path)

                    paths = tmp + paths
            except Exception as e:
                print(e)

        errors = []
        authors = []

        # compile

        self.head('compile')

        for path in paths:
            if os.path.isdir(path):
                with __os__.chdir(path) as chdir:
                    mvn = maven.maven()
                    mvn.notification = '<%s_DASHBOARD_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper()

                    mvn.clean()

                    if 'code_c/' in __os__.normpath(path):
                        cmdline = 'mvn deploy -fn -U -Djobs=10'
                        lang = 'cpp'
                    else:
                        cmdline = 'mvn deploy -fn -U'
                        lang = None

                    if not mvn.compile(cmdline, 'mvn deploy -fn -U', lang):
                        if path not in errors:
                            errors.append(path)

                            if mvn.errors:
                                for file, info in mvn.errors.items():
                                    if info.get('author'):
                                        if info['author'] not in authors:
                                            authors.append(info['author'])

        # check

        self.head('check')

        for path in paths:
            if os.path.isdir(path):
                chk = check.check(path)
                chk.notification = '<%s_DASHBOARD_CHECK 通知> 文件检查失败, 请尽快处理' % self.name.upper()

                chk.check(ignores)

                if chk.errors:
                    if path not in errors:
                        errors.append(path)

                        for type, file_info in chk.errors.items():
                            for file, info in file_info.items():
                                if info:
                                    author, *_ = info

                                    if author not in authors:
                                        authors.append(author)

        if errors:
            os.makedirs(os.path.dirname(filename), exist_ok = True)

            try:
                with open(filename, 'w', encoding = 'utf8') as f:
                    json.dump(errors, f)
            except Exception as e:
                print(e)

            if os.environ.get('BUILD_WORKSPACE'):
                os.makedirs(os.environ['BUILD_WORKSPACE'], exist_ok = True)

                try:
                    with open(os.path.join(os.environ['BUILD_WORKSPACE'], 'authors.txt'), 'w', encoding = 'utf8') as f:
                        f.write(','.join(authors))
                except Exception as e:
                    print(e)

            return False
        else:
            if os.path.isfile(filename):
                os.remove(filename)

            return True

    def dashboard_jenkins_cli(self, jobname, authors, paths):
        cmdline = 'java -jar "%s" -s %s build --username %s --password %s "%s" -p authors="%s" -p paths="%s"' % (
            const.JENKINS_CLI, const.JENKINS_URL, const.JENKINS_USERNAME, const.JENKINS_PASSWORD,
            jobname, ','.join(authors), ','.join(paths))

        display_cmd = 'java -jar "%s" -s %s build --username %s --password %s "%s" -p authors="%s" -p paths="%s"' % (
            const.JENKINS_CLI, const.JENKINS_URL, password.password(const.JENKINS_USERNAME), password.password(const.JENKINS_PASSWORD),
            jobname, ','.join(authors), ','.join(paths))

        cmd = command.command()

        for line in cmd.command(cmdline, display_cmd = display_cmd):
            print(line)

    def update(self, branch = None):
        return build.build().update(branch)

    def kw_check(self, path = None, lang = None, filenames = None):
        if not path:
            path = '.'

        if os.path.isdir(path):
            with __os__.chdir(path) as chdir:
                kwinject = 'target/kwinject.out'

                mvn = maven.maven()
                mvn.notification = '<%s_DASHBOARD_GERRIT_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper()

                mvn.clean()

                if not os.path.isdir(os.path.dirname(kwinject)):
                    os.makedirs(os.path.dirname(kwinject), exist_ok = True)

                if lang == 'cpp':
                    cmdline = 'kwinject --output %s mvn install -U -fn -Djobs=10' % kwinject
                else:
                    cmdline = 'kwmaven --output %s install -U -fn' % kwinject

                if not mvn.compile(cmdline):
                    return False

                if os.path.isfile(kwinject):
                    defect = {}

                    with __os__.chdir(os.path.dirname(kwinject)) as _chdir:
                        kwreport = 'kwreport.xml'

                        cmd = command.command()

                        cmdlines = [
                            'kwcheck create kwcheck',
                            'kwcheck import %s' % os.path.basename(kwinject),
                            'kwcheck import %s' % const.KLOCWORK_PCONF_FILE,
                            'kwcheck run -F xml --report %s --license-host %s --license-port %s' % (kwreport, const.KLOCWORK_LICENSE_HOST, const.KLOCWORK_LICENSE_PORT)
                        ]

                        for cmdline in cmdlines:
                            for line in cmd.command(cmdline):
                                print(line)

                            if not cmd.result():
                                if cmdline.startswith('kwcheck run') and cmd.result(1):
                                    continue

                                return False

                        if os.path.isfile(kwreport):
                            try:
                                tree = etree.parse(kwreport)
                            except Exception as e:
                                print(e)

                                return False

                            namespace = tree.getroot().nsmap

                            for e in tree.findall('problem', namespace):
                                info = {}

                                for element in e.iter():
                                    tag = element.tag.replace('{%s}' % namespace[None], '')

                                    if tag in ('file', 'line', 'method', 'code', 'message', 'severity'):
                                        if tag == 'file':
                                            info[tag] = os.path.abspath(element.text)
                                        else:
                                            info[tag] = element.text

                                if info['severity'] not in defect:
                                    defect[info['severity']] = {}

                                if info['code'] not in defect[info['severity']]:
                                    defect[info['severity']][info['code']] = []

                                defect[info['severity']][info['code']].append(info)

                            defect = self.kw_check_fixed(defect, filenames)

                    if ('Critical' in defect) or ('Error' in defect):
                        lines = []

                        for severity in ('Critical', 'Error'):
                            if severity in defect:
                                lines.append('')
                                lines.append('=' * 60)
                                lines.append('KLOCWORK %s DEFECT:' % severity.upper())
                                lines.append('=' * 60)

                                for code in defect[severity]:
                                    lines.append('  %s:' % code)

                                    for info in defect[severity][code]:
                                        lines.append('    file     : %s' % info['file'])
                                        lines.append('    line     : %s' % info['line'])
                                        lines.append('    method   : %s' % info['method'])
                                        lines.append('    message  : %s' % info['message'])
                                        lines.append('')

                        for line in lines:
                            print(line)

                        if os.environ.get('GERRIT_EMAIL'):
                            admin_addrs = None

                            if os.environ.get('SENDMAIL.ADMIN'):
                                admin_addrs = __string__.split(os.environ.get('SENDMAIL.ADMIN'))

                            smtp.sendmail(
                                '<%s_DASHBOARD_GERRIT_BUILD 通知> KW检查失败, 请尽快处理' % self.name.upper(),
                                os.environ['GERRIT_EMAIL'], admin_addrs, '<br>\n'.join(lines)
                            )

                        return False

            return True
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False

    def kw_check_fixed(self, defect, filenames = None):
        return defect

    def expand_dashboard(self, path, file):
        return file

    def pom_path(self, path):
        if not path:
            return None

        if os.path.isdir(path):
            if os.path.isfile(os.path.join(path, 'pom.xml')):
                return path

        return self.pom_path(os.path.dirname(path))

    def head(self, string):
        print()
        print('*' * 60)

        if len(string) > 58:
            print('*' + string)
        else:
            size = (58 - len(string)) // 2

            print('*' + ' ' * size + string + ' ' * (58 - len(string) - size) + '*')

        print('*' * 60)
        print()
