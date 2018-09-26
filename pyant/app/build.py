import collections
import datetime
import glob
import json
import os
import os.path
import re
import shutil
import tarfile
import tempfile
import time
import zipfile

from lxml import etree

from pyant import check, command, git, maven, password, smtp
from pyant.app import const
from pyant.builtin import __os__, __string__

__all__ = ('umebn_build', 'bn_build')

class build():
    def __init__(self, name, repos, artifact_repos):
        self.name = name
        self.repos = repos
        self.artifact_repos = artifact_repos

        self.path = self.name
        self.type = 'none'

    def update(self, branch = None):
        if os.path.isdir(self.path):
            if os.path.isfile(os.path.join(self.path, '.git/index.lock')):
                time.sleep(30)

                return True
            else:
                return git.pull(self.path, revert = True)
        else:
            return git.clone(self.repos, self.path, branch)

    def compile_base(self, cmd = None, file = None):
        if not file:
            file = os.path.join(self.path, 'pom/pom.xml')

        if os.path.isfile(file):
            with __os__.chdir(os.path.dirname(file)) as chdir:
                mvn = maven.maven()

                return mvn.compile(cmd)
        else:
            print('no such file: %s' % os.path.normpath(file))

            return False

    def compile(self, cmd = None, clean = False, retry_cmd = None, dirname = None):
        if not dirname:
            dirname = 'build'

        path = os.path.join(self.path, dirname)

        if os.path.isdir(path):
            with __os__.chdir(path) as chdir:
                mvn = maven.maven()
                mvn.notification = '<%s_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper()

                if clean:
                    mvn.clean()

                return mvn.compile(cmd, retry_cmd)
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False

    def package(self, version, type = None):
        if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
            artifact = self.artifact_repos['snapshot']
        else:
            artifact = self.artifact_repos['alpha']

        return True

    def update_package(self, version, type = None):
        if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
            artifact = self.artifact_repos['snapshot']
        else:
            artifact = self.artifact_repos['alpha']

        return True

    def dashboard(self, paths, branch = None):
        if os.path.isdir(self.path):
            if not git.reset(self.path, branch):
                return False

        if not self.update(branch):
            return False

        if os.path.isdir(self.path):
            with __os__.chdir(self.path) as chdir:
                return self.inner_dashboard(paths)
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
                    paths = []

                    for log in logs:
                        if log['changes']:
                            for k, v in log['changes'].items():
                                for file in v:
                                    filenames = (file,)

                                    for filename in filenames:
                                        dir = self.pom_path(filename)

                                        if dir:
                                            if dir not in paths:
                                                paths.append(dir)

                    for path in paths:
                        if os.path.isdir(path):
                            lang = None

                            if __os__.normpath(path).startswith('code_c/'):
                                lang = 'cpp'

                            with __os__.chdir(path) as chdir:
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

                                if not self.kw_check('.', lang):
                                    status = False

                                    continue

        return status

    def dashboard_monitor(self, branch = None):
        if not self.update(branch):
            return False

        if os.environ.get('JOB_NAME'):
            job_home = os.path.dirname(os.environ['JOB_NAME'])
        else:
            job_home = os.path.join(self.path, 'dashboard')

        for path, (authors, paths) in self.inner_dashboard_monitor([self.path], self.expand_dashboard).items():
            self.dashboard_jenkins_cli(os.path.join(job_home, '%s_dashboard' % self.name), authors, paths)

        return True

    def kw_build(self, path = None):
        if not path:
            path = '.'

        if os.path.isdir(path):
            with __os__.chdir(path) as chdir:
                if os.path.isfile('kwinject/kwinject.out'):
                    basename = os.path.basename(os.getcwd())

                    if self.name == basename:
                        project_name = self.name
                    else:
                        project_name = '%s_%s' % (self.name, basename)

                    cmd = command.command()

                    found = False
                    cmdline = 'kwadmin --url %s list-projects' % const.KLOCWORK_HTTP

                    for line in cmd.command(cmdline):
                        print(line)

                        if project_name == line.strip():
                            found = True

                    if not cmd.result():
                        return False

                    if not found:
                        cmdline = 'kwadmin --url %s create-project %s' % (const.KLOCWORK_HTTP, project_name)

                        for line in cmd.command(cmdline):
                            print(line)

                        if not cmd.result():
                            return False

                        if '_cpp' in project_name:
                            lang = 'c,cxx'
                        else:
                            lang = 'java'

                        for property in ('auto_delete_threshold 3', 'language %s' % lang):
                            cmdline = 'kwadmin --url %s set-project-property %s %s' % (const.KLOCWORK_HTTP, project_name, property)

                            for line in cmd.command(cmdline):
                                print(line)

                            if not cmd.result():
                                return False

                    cmdline = 'kwbuildproject --url %s/%s --tables-directory kwbuild --jobs-num auto kwinject/kwinject.out' % (const.KLOCWORK_HTTP, project_name)

                    for line in cmd.command(cmdline):
                        print(line)

                    if not cmd.result():
                        return False

                    cmdline = 'kwadmin --url %s load %s kwbuild' % (const.KLOCWORK_HTTP, project_name)

                    for line in cmd.command(cmdline):
                        print(line)

                    if not cmd.result():
                        return False

            return True
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False

    def kw_check(self, path = None, lang = None):
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
                    cmdline = 'kwinject --output %s mvn install -U -fn' % kwinject
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
                                return False

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

                    defect = self.kw_check_fixed(defect)

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

                        #return False

            return True
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False

    def kw_check_fixed(self, defect):
        return defect

    def metric_start(self, module = None, night = True):
        if os.environ.get('METRIC_IGNORE'):
            return None

        cmdline = None

        if not module:
            module = ''

        if os.environ.get('METRIC'):
            id = self.metric_id(module)

            if id:
                if night:
                    hour = datetime.datetime.now().hour

                    if 0 <= hour <= 8 or hour >= 22:
                        cmdline = 'curl --data "action=buildstart&project=%s&buildtype=night&item=%s" %s' % (id, module, const.METRIC_HTTP)
                else:
                    cmdline = 'curl --data "action=buildstart&project=%s&buildtype=CI&item=%s" %s' % (id, module, const.METRIC_HTTP)

        if cmdline:
            lines = []

            for line in ('$ ' + cmdline, '  in (' + os.getcwd() + ')'):
                print(line)

            try:
                return os.popen(cmdline).read().strip()
            except:
                return None
        else:
            return None

    def metric_end(self, id, status):
        if id:
            if status:
                success = 'success'
            else:
                success = 'failed'

            cmdline = 'curl --data "action=buildend&buildid=%s&buildresult=%s" %s' % (id, success, const.METRIC_HTTP)

            cmd = command.command()

            for line in cmd.command(cmdline):
                print(line)

    # ------------------------------------------------------

    def inner_dashboard(self, paths, ignores = None):
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
                        cmdline = 'mvn deploy -fn -U -Djobs=5'
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

    # path:
    #   (authors, paths)
    def inner_dashboard_monitor(self, paths, expand_dashboard = None):
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

    def inner_artifactory(self, path, artifact_path, artifact_filenames = None, suffix = None, targz = True):
        if isinstance(artifact_filenames, str):
            artifact_filenames = [artifact_filenames]

        if os.path.isdir(path):
            with __os__.tmpdir(tempfile.mkdtemp(), False) as tmpdir:
                if artifact_filenames:
                    # download

                    for file in artifact_filenames:
                        filename = __os__.join(const.ARTIFACT_HTTP, file)

                        cmdline = 'curl -k -H "X-JFrog-Art-Api: %s" -O "%s"' % (const.ARTIFACT_APIKEY, filename)
                        display_cmd = 'curl -k -H "X-JFrog-Art-Api: %s" -O "%s"' % (password.password(const.ARTIFACT_APIKEY), filename)

                        cmd = command.command()

                        for line in cmd.command(cmdline, display_cmd = display_cmd):
                            print(line)

                        if not cmd.result():
                            return False

                        try:
                            with tarfile.open(os.path.basename(file)) as tar:
                                tar.extractall('installation')
                        except Exception as e:
                            print(e)

                            return False

                dst = os.path.join(os.getcwd(), 'installation')

                with __os__.chdir(path) as chdir:
                    try:
                        for file in glob.iglob('**/*', recursive = True):
                            filename = os.path.join(dst, file)

                            if os.path.isfile(file):
                                if not os.path.isdir(os.path.dirname(filename)):
                                    os.makedirs(os.path.dirname(filename), exist_ok = True)

                                shutil.copyfile(file, filename)
                    except Exception as e:
                        print(e)

                        return False

                if targz:
                    if suffix:
                        zipname = '%s%s.tar.gz' % (os.path.basename(path), suffix)
                    else:
                        zipname = '%s.tar.gz' % os.path.basename(path)

                    try:
                        with tarfile.open(zipname, 'w:gz') as tar:
                            tar.add('installation')
                    except Exception as e:
                        print(e)

                        return False
                else:
                    if suffix:
                        zipname = '%s%s.zip' % (os.path.basename(path), suffix)
                    else:
                        zipname = '%s.zip' % os.path.basename(path)

                    try:
                        with zipfile.ZipFile(zipname, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
                            for file in glob.iglob('installation/**/*', recursive = True):
                                zip.write(file)
                    except Exception as e:
                        print(e)

                        return False

                # upload

                file = __os__.join(const.ARTIFACT_HTTP, artifact_path, zipname)

                cmdline = 'curl -k -H "X-JFrog-Art-Api: %s" -T "%s" "%s"' % (const.ARTIFACT_APIKEY, zipname, file)
                display_cmd = 'curl -k -H "X-JFrog-Art-Api: %s" -T "%s" "%s"' % (password.password(const.ARTIFACT_APIKEY), zipname, file)

                cmd = command.command()

                for line in cmd.command(cmdline, display_cmd = display_cmd):
                    print(line)

                if not cmd.result():
                    return False

                return True
        else:
            return False

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

    def package_home(self, version, type):
        return os.path.normpath(os.path.abspath(os.path.join('../zipfile', type, version.replace(' ', ''))))

    def expand_dashboard(self, path, file):
        return file

    def metric_id(self, module_name = None):
        return None

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

    def pom_path(self, path):
        if not path:
            return None

        if os.path.isdir(path):
            if os.path.isfile(os.path.join(path, 'pom.xml')):
                return path

        return self.pom_path(os.path.dirname(path))

class umebn_build(build):
    def __init__(self):
        artifact_repos = {
            'snapshot'  : 'umebn-snapshot-generic',
            'alpha'     : 'umebn-alpha-generic',
            'release'   : 'umebn-release-generic'
        }

        super().__init__(
            'umebn',
            __os__.join(const.SSH_GIT, 'umebn'),
            artifact_repos
        )

        self.type = 'umebn'

    def compile_base(self, cmd = None):
        return super().compile_base(cmd, 'devops/parent/build/pom.xml')

    # ------------------------------------------------------

    def metric_id(self, module_name = None):
        return const.METRIC_ID_UMEBN

class bn_build(build):
    def __init__(self):
        artifact_repos = {
            'snapshot'  : 'U31R22-snapshot-generic',
            'alpha'     : 'U31R22-alpha-generic',
            'release'   : 'U31R22-release-generic'
        }

        repos = collections.OrderedDict([
            ('interface', __os__.join(const.SSH_GIT, 'U31R22_INTERFACE')),
            ('platform' , __os__.join(const.SSH_GIT, 'U31R22_PLATFORM')),
            ('necommon' , __os__.join(const.SSH_GIT, 'U31R22_NECOMMON')),
            ('e2e'      , __os__.join(const.SSH_GIT, 'U31R22_E2E')),
            ('uca'      , __os__.join(const.SSH_GIT, 'U31R22_UCA')),
            ('xmlfile'  , __os__.join(const.SSH_GIT, 'U31R22_NBI_XMLFILE')),
            ('nbi'      , __os__.join(const.SSH_GIT, 'U31R22_NBI')),
            ('sdh'      , __os__.join(const.SSH_GIT, 'U31R22_SDH')),
            ('wdm'      , __os__.join(const.SSH_GIT, 'U31R22_WDM')),
            ('ptn'      , __os__.join(const.SSH_GIT, 'U31R22_PTN')),
            ('ptn2'     , __os__.join(const.SSH_GIT, 'U31R22_PTN2')),
            ('ip'       , __os__.join(const.SSH_GIT, 'U31R22_IP')),
            ('inventory', __os__.join(const.SSH_GIT, 'U31R22_Inventory'))
        ])

        super().__init__(
            'bn',
            repos,
            artifact_repos
        )

        self.type = 'ems'

        self.repos_devtools = const.SSH_GIT

    def update(self, module, branch = None):
        if module:
            if module in self.repos:
                path = os.path.basename(self.repos[module])

                if os.path.isdir(path):
                    if os.path.isfile(os.path.join(path, '.git/index.lock')):
                        time.sleep(30)

                        return True
                    else:
                        return git.pull(path, revert = True)
                else:
                    return git.clone(self.repos[module], path, branch)
            elif module in ('devtools', ):
                return self.update_devtools(branch)
            else:
                print('module name not found in %s' % str(tuple(self.repos.keys())))

                return False
        else:
            status = True

            for module in self.repos:
                if not self.update(module, branch):
                    status = False

            if not self.update_devtools(branch):
                status = False

            return status

    def compile_base(self, cmd = None):
        return super().compile_base(cmd, 'U31R22_PLATFORM/pom/pom.xml')

    def compile(self, module, cmd = None, clean = False, retry_cmd = None, dirname = None, lang = None):
        if module:
            if module in list(self.repos.keys()) + ['wdm1', 'wdm2', 'wdm3']:
                self.environ(lang)

                if lang in ('cpp', ):
                    if not dirname:
                        dirname = 'code_c/build'
                else:
                    if not dirname:
                        dirname = 'code/build'

                if module in ('wdm1', 'wdm2', 'wdm3'):
                    self.path = os.path.basename(self.repos['wdm'])
                else:
                    self.path = os.path.basename(self.repos[module])

                return super().compile(cmd, clean, retry_cmd, dirname)
            else:
                print('module name not found in %s' % str(tuple(self.repos.keys())))

                return False
        else:
            status = True

            for module in self.repos:
                if not self.compile(module, cmd, clean, retry_cmd, dirname, lang):
                    status = False

            return status

    def package(self, version, type = None):
        if not type:
            type = 'ems'

        type = type.strip().lower()

        if self.inner_package(version, None, type, self.expand_filename, False):
            if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
                artifact = self.artifact_repos['snapshot']
            else:
                artifact = self.artifact_repos['alpha']

            suffix = '-%s' % __os__.osname()

            if type not in ('ems',):
                suffix += '_%s' % type

            if type in ('lct',):
                filenames = (
                    os.path.join(self.artifact_repos['release'], 'bn/LCT/current_en.tar.gz'),
                    os.path.join(self.artifact_repos['release'], 'bn/LCT/current_zh.tar.gz')
                )
            else:
                filenames = ((
                    os.path.join(self.artifact_repos['release'], 'bn/%s/current.tar.gz' % type.upper()),
                    os.path.join(self.artifact_repos['release'], 'bn/%s/extend.tar.gz' % type.upper())
                ),)

            for filename in filenames:
                if not self.inner_artifactory(
                    self.package_home(version, type),
                    os.path.join(artifact, version.replace(' ', '')),
                    filename,
                    suffix
                ):
                    return False

            return True

        return False

    def update_package(self, version, type = None):
        if not type:
            type = 'ems'

        type = type.strip().lower()

        if self.inner_package(version, '*/installdisk/updatedisk.xml', type, self.expand_filename, False):
            if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
                artifact = self.artifact_repos['snapshot']
            else:
                artifact = self.artifact_repos['alpha']

            suffix = '-update-%s' % __os__.osname()

            if type not in ('ems',):
                suffix += '_%s' % type

            if not self.inner_artifactory(
                self.package_home(version, type),
                os.path.join(artifact, version.replace(' ', '')),
                None,
                suffix
            ):
                return False

            return True

        return False

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
                return self.inner_dashboard(paths)
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

        return status

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

        for path, (authors, paths) in self.inner_dashboard_monitor(path_info.keys(), self.expand_dashboard).items():
            self.dashboard_jenkins_cli(os.path.join(job_home, '%s_dashboard_%s' % (self.name, path_info[path])), authors, paths)

        return True

    # ------------------------------------------------------

    # installdisk.xml
    #
    #    <install>
    #      <type>
    #        <packages>
    #          <package name = '...' dirname = '...' dest = '...'>
    #            <file name='...'/>
    #            <ignore name='...'/>
    #          </package>
    #
    #          <package name = '...' dirname = '...' dest = '...'>
    #            <file name='...'/>
    #            <ignore name='...'/>
    #          </package>
    #        </packages>
    #
    #        <copies>
    #          <copy name = '...' dirname = '...' dest = '...'>
    #            <file name='...'/>
    #            <ignore name='...'/>
    #          </copy>
    #
    #          <copy name = '...' dirname = '...' dest = '...'>
    #            <file name='...'/>
    #            <ignore name='...'/>
    #          </copy>
    #        </copies>
    #      </type>
    #    </install>
    def inner_package(self, version, xpath = None, type = None, expand_filename = None, cross_platform = True):
        if not xpath:
            xpath = '*/installdisk/installdisk.xml'

        if not type:
            type = self.type

        zipfile_home = self.package_home(version, type)
        tmpdir = tempfile.mkdtemp()

        shutil.rmtree(zipfile_home, ignore_errors = True)
        os.makedirs(zipfile_home, exist_ok = True)

        packages = {}
        copies = {}
        vars = {}

        for file in glob.iglob(xpath, recursive = True):
            try:
                tree = etree.parse(file, etree.XMLParser(strip_cdata=False))
            except:
                print('error: parse xml file fail: %s' % os.path.abspath(file))

                return False

            vars[file] = {
                'os': __os__.osname()
            }

            for e in tree.findall('%s/opts/attr' % type):
                name = e.get('name', '').strip()
                value = ''

                for element in e.findall('value'):
                    value = element.text.strip()

                    if '<![CDATA[' in etree.tostring(element, encoding='utf-8').decode('utf-8'):
                        value = '<![CDATA[%s]]' % value

                    break

                filenames = []

                for element in e.findall('files/file'):
                    filename = element.get('name', '').strip()

                    if filename == '.':
                        filenames.append(file)
                    else:
                        for _filename in glob.iglob(os.path.join(os.path.dirname(file), filename), recursive = True):
                            filenames.append(os.path.normpath(_filename))

                if not filenames:
                    filenames.append(file)

                for filename in filenames:
                    if not vars.get(filename):
                        vars[filename] = {}

                    vars[filename][name] = value

            for hash, _xpath in ((packages, 'packages/package'), (copies, 'copies/copy')):
                for e in tree.findall(__os__.join(type, _xpath)):
                    name = e.get('name')
                    dirname = e.get('dirname')
                    dest = e.get('dest', '')
                    ver = e.get('version', version)

                    if dest in ('', '.'):
                        dest = ''

                    if name and dirname:
                        _vars = vars.get(file)

                        name = __os__.normpath(__string__.vars_expand(name.strip(), _vars))
                        dirname = __os__.normpath(os.path.join(os.path.dirname(file), __string__.vars_expand(dirname.strip(), _vars)))
                        dest = __os__.normpath(__string__.vars_expand(dest.strip(), _vars))
                        ver = __os__.normpath(__string__.vars_expand(ver.strip(), _vars))

                        if _xpath == 'packages/package':
                            name = '%s_%s' % (name, ver.replace(' ', ''))

                        if os.path.isdir(dirname):
                            if name not in hash:
                                hash[name] = collections.OrderedDict()

                            with __os__.chdir(dirname) as chdir:
                                for element in e.findall('file'):
                                    element_name = element.get('name')
                                    element_dest = element.get('dest', '')

                                    if element_name:
                                        element_name = os.path.normpath(__string__.vars_expand(element_name.strip(), _vars))
                                        element_dest = os.path.normpath(__string__.vars_expand(element_dest.strip(), _vars))

                                        if element_dest in ('', '.'):
                                            element_dest = element_name

                                        if dirname not in hash[name]:
                                            hash[name][dirname] = collections.OrderedDict()

                                        if dest not in hash[name][dirname]:
                                            hash[name][dirname][dest] = {}

                                        found = False

                                        if os.path.isfile(element_name):
                                            found = True

                                            hash[name][dirname][dest][element_dest] = element_name
                                        elif os.path.isdir(element_name):
                                            found = True

                                            with __os__.chdir(element_name) as _chdir:
                                                for filename in glob.iglob('**/*', recursive = True):
                                                    if os.path.isfile(filename):
                                                        hash[name][dirname][dest][os.path.join(element_dest, filename)] = os.path.join(element_name, filename)
                                        else:
                                            for path in glob.iglob(element_name, recursive = True):
                                                found = True

                                                if os.path.isfile(path):
                                                    hash[name][dirname][dest][path] = path
                                                elif os.path.isdir(path):
                                                    with __os__.chdir(path) as _chdir:
                                                        for filename in glob.iglob('**/*', recursive = True):
                                                            if os.path.isfile(filename):
                                                                hash[name][dirname][dest][os.path.join(path, filename)] = os.path.join(path, filename)
                                                else:
                                                    pass

                                        if not found:
                                            print('no such file or directory: %s' % os.path.abspath(element_name))

                                for element in e.findall('ignore'):
                                    element_name = element.get('name')

                                    if element_name:
                                        element_name = os.path.normpath(element_name.strip())

                                        if dirname in hash[name]:
                                            if dest in hash[name][dirname]:
                                                found = False

                                                for path in glob.iglob(element_name, recursive = True):
                                                    found = True

                                                    if os.path.isfile(path):
                                                        if path in hash[name][dirname][dest]:
                                                            del hash[name][dirname][dest][path]
                                                    elif os.path.isdir(path):
                                                        for filename in glob.iglob(os.path.join(path, '**/*'), recursive = True):
                                                            if os.path.isfile(filename):
                                                                if filename in hash[name][dirname][dest]:
                                                                    del hash[name][dirname][dest][filename]
                                                    else:
                                                        pass

                                                if not found:
                                                    print('no such file or directory: %s' % os.path.abspath(element_name))
                        else:
                            print('no such directory: %s' % dirname)

        for name, dirname_info in packages.items():
            zipinfo = collections.OrderedDict()

            for dirname, dest_info in dirname_info.items():
                for dest, filename_info in dest_info.items():
                    for destname, filename in filename_info.items():
                        if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib', '.manifest'):
                            continue

                        if not cross_platform:
                            if __os__.osname() in ('windows', 'windows-x64'):
                                if os.path.splitext(filename)[-1] in ('.so', '.sh'):
                                    if os.path.splitext(filename)[-1] in ('.so', ):
                                        if 'ruby/' not in __os__.normpath(filename):
                                            continue
                                    else:
                                        continue
                            else:
                                if os.path.splitext(filename)[-1] in ('.exe', '.dll', '.bat'):
                                    continue

                        if os.path.isfile(os.path.join(dirname, filename)):
                            arcname = destname

                            if expand_filename:
                                filename, arcname = expand_filename(version, dirname, filename, destname, type, tmpdir, vars.get(os.path.normpath(os.path.join(dirname, filename))))

                            srcname = os.path.join(dirname, filename)

                            if type in ('upgrade', ):
                                srcname = self.upgrade_expand_filename(srcname, tmpdir)

                            zipinfo[__os__.normpath(os.path.join(dest, arcname))] = srcname

            try:
                zipname = os.path.join(zipfile_home, '%s.zip' % name)

                if not os.path.isdir(os.path.dirname(zipname)):
                    os.makedirs(os.path.dirname(zipname), exist_ok = True)

                with zipfile.ZipFile(zipname, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
                    for line in ('$ zipfile: %s' % zip.filename, '  in (' + os.getcwd() + ')'):
                        print(line)

                    for arcname, filename in zipinfo.items():
                        zip.write(filename, arcname)

            except Exception as e:
                print(e)

                shutil.rmtree(tmpdir, ignore_errors = True)

                return False

        for name, dirname_info in copies.items():
            try:
                for line in ('$ copy: %s' % name, '  in (' + os.getcwd() + ')'):
                    print(line)

                for dirname, dest_info in dirname_info.items():
                    for dest, filename_info in dest_info.items():
                        for destname, filename in filename_info.items():
                            if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib'):
                                continue

                            if not cross_platform:
                                if __os__.osname() in ('windows', 'windows-x64'):
                                    if os.path.splitext(filename)[-1] in ('.so', '.sh'):
                                        if os.path.splitext(filename)[-1] in ('.so',):
                                            if 'ruby/' not in __os__.normpath(filename):
                                                continue
                                        else:
                                            continue
                                else:
                                    if os.path.splitext(filename)[-1] in ('.dll', '.bat'):
                                        continue

                            if os.path.isfile(os.path.join(dirname, filename)):
                                dst = destname

                                if expand_filename:
                                    filename, dst = expand_filename(version, dirname, filename, destname, type, tmpdir, vars.get(os.path.normpath(os.path.join(dirname, filename))))

                                dst = os.path.join(zipfile_home, name, dest, dst)

                                if not os.path.isdir(os.path.dirname(dst)):
                                    os.makedirs(os.path.dirname(dst), exist_ok = True)

                                shutil.copyfile(os.path.join(dirname, filename), dst)
            except Exception as e:
                print(e)

                shutil.rmtree(tmpdir, ignore_errors = True)

                return False

        shutil.rmtree(tmpdir, ignore_errors = True)

        return True

    def inner_artifactory(self, path, artifact_path, artifact_filenames = None, suffix = None):
        return super().inner_artifactory(path, artifact_path, artifact_filenames, suffix, False)

    def metric_id(self, module_name = None):
        if module_name in ('interface', 'platform', 'necommon', 'uca', 'sdh', 'ptn'):
            return const.METRIC_ID_BN_ITN
        elif module_name in ('ptn2', 'ip'):
            return const.METRIC_ID_BN_IPN
        elif module_name in ('e2e',):
            return const.METRIC_ID_BN_E2E
        elif module_name in ('xmlfile', 'nbi', 'inventory'):
            return const.METRIC_ID_BN_NBI
        elif module_name in ('wdm',):
            return const.METRIC_ID_BN_OTN
        else:
            return None

    def update_devtools(self, branch = None):
        if __os__.osname() == 'linux':
            url = __os__.join(self.repos_devtools, 'U31R22_DEVTOOLS_LINUX')
        elif __os__.osname() == 'solaris':
            url = __os__.join(self.repos_devtools, 'U31R22_DEVTOOLS_SOLARIS')
        elif __os__.osname() == 'windows-x64':
            url = __os__.join(self.repos_devtools, 'U31R22_DEVTOOLS_WINDOWS-x64')
        else:
            url = __os__.join(self.repos_devtools, 'U31R22_DEVTOOLS_WINDOWS')

        path = 'DEVTOOLS'

        if os.path.isdir(path):
            if os.path.isfile(os.path.join(path, '.git/index.lock')):
                time.sleep(30)

                return True
            else:
                return git.pull(path, revert = True)
        else:
            return git.clone(url, path, branch)

    def environ(self, lang = None):
        if os.environ.get('UEP_VERSION'):
            if not os.environ.get('POM_UEP_VERSION'):
                os.environ['POM_UEP_VERSION'] = os.environ['UEP_VERSION'].upper()

                print('export POM_UEP_VERSION=%s' % os.environ['POM_UEP_VERSION'])

        if not os.environ.get('DEVTOOLS_ROOT'):
            if os.path.isdir('DEVTOOLS'):
                os.environ['DEVTOOLS_ROOT'] = __os__.abspath('DEVTOOLS')

        if lang == 'cpp':
            if os.environ.get('DEVTOOLS_ROOT'):
                if os.path.isdir(os.path.join(os.environ['DEVTOOLS_ROOT'], 'vc/bin')):
                    os.environ['PATH'] = ';'.join((__os__.join(os.environ['DEVTOOLS_ROOT'], 'vc/bin'), os.environ['PATH']))

            if not os.environ.get('INTERFACE_OUTPUT_HOME'):
                path = os.path.basename(self.repos['interface'])

                if os.path.isdir(path):
                    os.environ['INTERFACE_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('PLATFORM_OUTPUT_HOME'):
                path = os.path.basename(self.repos['platform'])

                if os.path.isdir(path):
                    os.environ['PLATFORM_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('NECOMMON_OUTPUT_HOME'):
                path = os.path.basename(self.repos['necommon'])

                if os.path.isdir(path):
                    os.environ['NECOMMON_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('E2E_OUTPUT_HOME'):
                path = os.path.basename(self.repos['e2e'])

                if os.path.isdir(path):
                    os.environ['E2E_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('UCA_OUTPUT_HOME'):
                path = os.path.basename(self.repos['uca'])

                if os.path.isdir(path):
                    os.environ['UCA_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('NAF_OUTPUT_HOME'):
                path = os.path.basename(self.repos['nbi'])

                if os.path.isdir(path):
                    os.environ['NAF_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('SDH_OUTPUT_HOME'):
                path = os.path.basename(self.repos['sdh'])

                if os.path.isdir(path):
                    os.environ['SDH_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('WDM_OUTPUT_HOME'):
                path = os.path.basename(self.repos['wdm'])

                if os.path.isdir(path):
                    os.environ['WDM_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

    def expand_filename(self, version, dirname, filename, destname, type, tmpdir, vars = None):
        dst = destname
        name = os.path.join(dirname, filename)

        if vars:
            lines = []

            with open(name, encoding = 'utf-8') as f:
                for line in f.readlines():
                    lines.append(__string__.vars_expand(line.rstrip(), vars))

            name = os.path.join(tmpdir, __os__.tmpfilename())

            with open(name, 'w', encoding = 'utf-8') as f:
                f.write('\n'.join(lines))

        dst = dst.replace('ums-nms', 'ums-client').replace('ums-lct', 'ums-client')

        if os.path.basename(name) in ('ppuinfo.xml', 'pmuinfo.xml', 'u3backup.xml', 'u3backupme.xml', 'dbtool-config.xml', 'package-update-info.xml'):
            try:
                tree = etree.parse(name)

                if os.path.basename(name) in ('ppuinfo.xml', 'pmuinfo.xml'):
                    if version:
                        for e in tree.findall('info'):
                            e.set('version', version)
                            e.set('display-version', version)
                elif os.path.basename(name) in ('u3backup.xml', 'u3backupme.xml'):
                    if version:
                        for e in tree.findall('version'):
                            e.text = version
                elif os.path.basename(name) in ('dbtool-config.xml',):
                    for e in tree.findall('ems_type'):
                        e.text = type
                elif os.path.basename(name) in ('package-update-info.xml',):
                    tree.getroot().set('package-name', tree.getroot().get('package-name').replace(' -B', '-B').replace(' ', '_'))
                else:
                    pass

                tree.write(name, encoding='utf-8', pretty_print=True, xml_declaration=True)
            except:
                pass

        return (filename, dst)

    def upgrade_expand_filename(self, name, tmpdir):
        if re.search(r'ums-server\/procs\/ppus\/bn\.ppu\/bn-ptn\.pmu\/.*\/ican-adaptercmdcode-config.*\.xml$', name):
            try:
                tree = etree.parse(name)

                for e in tree.findall('commandCode'):
                    cmdcode = e.get('cmdCode')

                    if cmdcode == '88224':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ican.emf.subnet.process.TDoNothingProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    elif cmdcode == '80724':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('needMutex')
                        element.text = 'false'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ican.emf.subnet.process.TCreateMEProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    elif cmdcode == '84205':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')
                        e.append(element)
                    elif cmdcode == '81300':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('cmdType')
                        element.set('overTime', '30')
                        element.text = 'S'
                        e.append(element)

                        element = etree.Element('needMutex')
                        element.text = 'false'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')
                        e.append(element)
                    elif cmdcode == '80702':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('needMutex')
                        element.text = 'false'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ums.bn.mecopy.emf.process.BeginCopyMEDataProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ums.bn.mecopy.emf.process.EndCopyMEDataProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    elif cmdcode == '80703':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('needMutex')
                        element.text = 'true'
                        e.append(element)

                        element = etree.Element('supportOffline')
                        element.text = 'true'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ums.bn.ne.emf.uploadDownload.ptn9000.process.TMESetPreCheckProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ican.emf.subnet.process.TModifyMEProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ican.emf.subnet.process.TPublishModifyMEProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    else:
                        pass

                name = os.path.join(tmpdir, __os__.tmpfilename())
                tree.write(name, encoding='utf-8', pretty_print=True, xml_declaration=True)
            except:
                pass
        elif re.search(r'ums-server\/procs\/ppus\/bn\.ppu\/(bn-mstp|bn-wdm)\.pmu\/.*\/ican-adaptercmdcode-config.*\.xml$', name):
            try:
                tree = etree.parse(name)

                for e in tree.findall('commandCode'):
                    cmdcode = e.get('cmdCode')

                    if cmdcode == '80724':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('needMutex')
                        element.text = 'true'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'CCreateMEProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    else:
                        pass

                name = os.path.join(tmpdir, __os__.tmpfilename())
                tree.write(name, encoding='utf-8', pretty_print=True, xml_declaration=True)
            except:
                pass
        else:
            pass

        return name

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
