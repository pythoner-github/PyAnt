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

from pyant import check, command, git, maven, password
from pyant.app import const
from pyant.builtin import os as builtin_os

class build():
    def __init__(self, name, repos, artifact_repos):
        self.name = name
        self.repos = repos
        self.artifact_repos = artifact_repos

        self.path = self.name

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
            with builtin_os.chdir(os.path.dirname(file)) as chdir:
                mvn = maven.maven()

                return mvn.compile(cmd)
        else:
            print('no such file: %s' % os.path.normpath(file))

            return False

    def compile(self, cmd = None, clean = False, retry_cmd = None, dirname = None):
        if isinstance(clean, str):
            if clean.lower().strip() == 'true':
                clean = True

        if not dirname:
            dirname = 'build'

        path = os.path.join(self.path, dirname)

        if os.path.isdir(path):
            with builtin_os.chdir(path) as chdir:
                mvn = maven.maven()
                mvn.notification = '<%s_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper()

                if clean:
                    mvn.clean()

                return mvn.compile(cmd, retry_cmd)
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False

    def package(self, version, type = None):
        if self.inner_package(version, None, type, self.expand_filename):
            if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
                artifact = self.artifact_repos['snapshot']
            else:
                artifact = self.artifact_repos['alpha']

            return self.artifactory(
                self.package_home(version),
                artifact,
                os.path.join(self.artifact_repos['release'], self.name, 'current.tar.gz')
            )

        return False

    def dashboard(self, paths, branch = None):
        if not self.update(branch):
            return False

        if os.path.isdir(self.path):
            with builtin_os.chdir(self.path) as chdir:
                return self.inner_dashboard(paths)
        else:
            print('no such directory: %s' % os.path.normpath(self.path))

            return False

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

    def kw_build(self, name, path):
        if os.path.isdir(path):
            with builtin_os.chdir(path) as chdir:
                if os.path.isfile('kwinject/kwinject.out'):
                    project_name = '%s_%s' % (name, os.path.basename(os.getcwd()))

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

    def metric_start(self, module_name = None, night = True):
        cmdline = None

        if not module_name:
            module_name = ''

        if os.environ.get('METRIC'):
            id = metric_id(module_name)

            if id:
                if night:
                    hour = datetime.datetime.now().hour

                    if 0 <= hour <= 8 or hour >= 22:
                        cmdline = 'curl --data "action=buildstart&project=%s&buildtype=night&item=%s" %s' % (id, module_name, const.METRIC_HTTP)
                else:
                    cmdline = 'curl --data "action=buildstart&project=%s&buildtype=CI&item=%s" %s' % (id, module_name, const.METRIC_HTTP)

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
            type = 'none'

        zipfile_home = self.package_home(version)

        shutil.rmtree(zipfile_home, ignore_errors = True)
        os.makedirs(zipfile_home, exist_ok = True)

        packages = {}
        copies = {}

        for file in glob.iglob(xpath, recursive = True):
            try:
                tree = etree.parse(file)
            except:
                print('error: parse xml file fail: %s' % os.path.abspath(file))

                return False

            for hash, _xpath in ((packages, 'packages/package'), (copies, 'copies/copy')):
                for e in tree.findall(builtin_os.join(type, _xpath)):
                    name = e.get('name')
                    dirname = e.get('dirname')
                    dest = e.get('dest')

                    if dest in (None, '.'):
                        dest = ''

                    if name and dirname:
                        name = builtin_os.normpath(name.strip())
                        dirname = builtin_os.normpath(os.path.join(os.path.dirname(file), dirname.strip()))
                        dest = builtin_os.normpath(dest.strip())

                        if os.path.isdir(dirname):
                            if name not in hash:
                                hash[name] = collections.OrderedDict()

                            with builtin_os.chdir(dirname) as chdir:
                                for element in e.findall('file'):
                                    element_name = element.get('name')

                                    if element_name:
                                        element_name = element_name.strip()

                                        if dirname not in hash[name]:
                                            hash[name][dirname] = collections.OrderedDict()

                                        if dest not in hash[name][dirname]:
                                            hash[name][dirname][dest] = []

                                        found = False

                                        for path in glob.iglob(element_name, recursive = True):
                                            found = True

                                            if os.path.isfile(path):
                                                hash[name][dirname][dest].append(path)
                                            elif os.path.isdir(path):
                                                for filename in glob.iglob(os.path.join(path, '**/*'), recursive = True):
                                                    if os.path.isfile(filename):
                                                        if filename not in hash[name][dirname][dest]:
                                                            hash[name][dirname][dest].append(filename)
                                            else:
                                                pass

                                        if not found:
                                            print('no such file or directory: %s' % os.path.abspath(element_name))

                                for element in e.findall('ignore'):
                                    element_name = element.get('name')

                                    if element_name:
                                        element_name = element_name.strip()

                                        if dirname in hash[name]:
                                            if dest in hash[name][dirname]:
                                                found = False

                                                for path in glob.iglob(element_name, recursive = True):
                                                    found = True

                                                    if os.path.isfile(path):
                                                        if path in hash[name][dirname][dest]:
                                                            hash[name][dirname][dest].remove(path)
                                                    elif os.path.isdir(path):
                                                        for filename in glob.iglob(os.path.join(path, '**/*'), recursive = True):
                                                            if os.path.isfile(filename):
                                                                if filename in hash[name][dirname][dest]:
                                                                    hash[name][dirname][dest].remove(filename)
                                                    else:
                                                        pass

                                                if not found:
                                                    print('no such file or directory: %s' % os.path.abspath(element_name))
                        else:
                            print('no such directory: %s' % dirname)

        for name, dirname_info in packages.items():
            try:
                zipname = os.path.join(zipfile_home, '%s_%s.zip' % (name, version.replace(' ', '')))

                if not os.path.isdir(os.path.dirname(zipname)):
                    os.makedirs(os.path.dirname(zipname), exist_ok = True)

                with zipfile.ZipFile(zipname, 'w') as zip:
                    for line in ('$ zipfile: %s' % zip.filename, '  in (' + os.getcwd() + ')'):
                        print(line)

                    for dirname, dest_info in dirname_info.items():
                        for dest, filename_list in dest_info.items():
                            for filename in filename_list:
                                if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib', '.manifest'):
                                    continue

                                if not cross_platform:
                                    if builtin_os.osname() in ('windows', 'windows-x64'):
                                        if os.path.splitext(filename)[-1] in ('.so', '.sh'):
                                            if os.path.splitext(filename)[-1] in ('.so'):
                                                if 'ruby/' not in builtin_os.normpath(filename):
                                                    continue
                                            else:
                                                continue
                                    else:
                                        if os.path.splitext(filename)[-1] in ('.exe', '.dll', '.bat'):
                                            continue

                                if os.path.isfile(os.path.join(dirname, filename)):
                                    arcname = None

                                    if expand_filename:
                                        filename, arcname = expand_filename(version, dirname, filename, type)

                                    zip.write(os.path.join(dirname, filename), builtin_os.normpath(os.path.join(dest, arcname)))
            except Exception as e:
                print(e)

                return False

        for name, dirname_info in copies.items():
            try:
                for line in ('$ copy: %s' % name, '  in (' + os.getcwd() + ')'):
                    print(line)

                for dirname, dest_info in dirname_info.items():
                    for dest, filename_list in dest_info.items():
                        for filename in filename_list:
                            if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib'):
                                continue

                            if not cross_platform:
                                if builtin_os.osname() in ('windows', 'windows-x64'):
                                    if os.path.splitext(filename)[-1] in ('.so', '.sh'):
                                        if os.path.splitext(filename)[-1] in ('.so'):
                                            if 'ruby/' not in builtin_os.normpath(filename):
                                                continue
                                        else:
                                            continue
                                else:
                                    if os.path.splitext(filename)[-1] in ('.dll', '.bat'):
                                        continue

                            if os.path.isfile(os.path.join(dirname, filename)):
                                dst = filename

                                if expand_filename:
                                    filename, dst = expand_filename(version, dirname, filename, type)

                                dst = os.path.join(zipfile_home, name, dest, dst)

                                if not os.path.isdir(os.path.dirname(dst)):
                                    os.makedirs(os.path.dirname(dst), exist_ok = True)

                                shutil.copyfile(os.path.join(dirname, filename), dst)
            except Exception as e:
                print(e)

                return False

        return True

    def inner_dashboard(self, paths, ignores = None):
        if isinstance(paths, str):
            paths = tuple(path.strip() for path in paths.split(','))
        else:
            paths = tuple(paths)

        filename = os.path.abspath(os.path.join('../errors', '%s.json' % os.path.basename(os.getcwd())))

        if os.path.isfile(filename):
            try:
                with open(filename, encoding = 'utf8') as f:
                    tmp_paths = []

                    for path in json.load(f):
                        if path not in paths:
                            tmp_paths.append(path)

                    paths = tuple(tmp_paths) + paths
            except Exception as e:
                print(e)

        errors = []
        authors = []

        # compile

        self.head('compile')

        for path in paths:
            if os.path.isdir(path):
                with builtin_os.chdir(path) as chdir:
                    mvn = maven.maven()
                    mvn.notification = '<%s_DASHBOARD_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper()

                    mvn.clean()

                    if 'code_c/' in builtin_os.normpath(path):
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
                with builtin_os.chdir(path) as chdir:
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

    def artifactory(self, path, artifact_path, artifact_base_list = None, suffix = None):
        if os.path.isdir(path):
            with builtin_os.tmpdir(tempfile.mkdtemp(), False) as tmpdir:
                if artifact_base_list:
                    # download

                    if isinstance(artifact_base_list, str):
                        artifact_base_list = (artifact_base_list,)

                    for file in artifact_base_list:
                        artifact_file = builtin_os.join(const.ARTIFACT_HTTP, file)

                        cmdline = 'curl -k -H "X-JFrog-Art-Api: %s" -O "%s"' % (const.ARTIFACT_APIKEY, artifact_file)
                        display_cmd = 'curl -k -H "X-JFrog-Art-Api: %s" -O "%s"' % (password.password(const.ARTIFACT_APIKEY), artifact_file)

                        cmd = command.command()

                        for line in cmd.command(cmdline, display_cmd = display_cmd):
                            print(line)

                        if not cmd.result():
                            return False

                        try:
                            with tarfile.open(os.path.basename(artifact_file)) as tar:
                                tar.extractall('installation')
                        except Exception as e:
                            print(e)

                            return False

                dst = os.path.join(os.getcwd(), 'installation')

                with builtin_os.chdir(path) as chdir:
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

                if suffix:
                    tarname = '%s%s.tar.gz' % (os.path.basename(path), suffix)
                else:
                    tarname = '%s.tar.gz' % os.path.basename(path)

                try:
                    with tarfile.open(tarname, 'w:gz') as tar:
                        tar.add('installation')
                except Exception as e:
                    print(e)

                    return False

                # upload

                artifact_file = builtin_os.join(const.ARTIFACT_HTTP, artifact_path, tarname)

                cmdline = 'curl -k -H "X-JFrog-Art-Api: %s" -T "%s" "%s"' % (const.ARTIFACT_APIKEY, tarname, artifact_file)
                display_cmd = 'curl -k -H "X-JFrog-Art-Api: %s" -T "%s" "%s"' % (password.password(const.ARTIFACT_APIKEY), tarname, artifact_file)

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

    def package_home(self, version):
        return os.path.normpath(os.path.abspath(os.path.join('../zipfile', version.replace(' ', ''))))

    def expand_filename(self, version, dirname, filename, type):
        dst = filename
        name = os.path.join(dirname, filename)

        if os.path.basename(name) in ('ppuinfo.xml', 'pmuinfo.xml'):
            if version:
                try:
                    tree = etree.parse(name)

                    for e in tree.findall('info'):
                        e.set('version', version)
                        e.set('display-version', version)

                    tree.write(name, encoding='utf-8', pretty_print=True, xml_declaration='utf-8')
                except:
                    pass

        return (filename, dst)

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

class stn_build(build):
    def __init__(self):
        artifact_repos = {
            'snapshot'  : 'stn_contoller-snapshot-generic',
            'alpha'     : 'stn_contoller-alpha-generic',
            'release'   : 'stn_contoller-release-generic'
        }

        super().__init__(
            'stn',
            builtin_os.join(const.SSH_GIT, 'stn/sdn_tunnel'),
            artifact_repos
        )

    # ------------------------------------------------------

    def metric_id(self, module_name = None):
        return const.METRIC_ID_STN

class umebn_build(build):
    def __init__(self):
        artifact_repos = {
            'snapshot'  : 'umebn-snapshot-generic',
            'alpha'     : 'umebn-alpha-generic',
            'release'   : 'umebn-release-generic'
        }

        super().__init__(
            'umebn',
            builtin_os.join(const.SSH_GIT, 'umebn'),
            artifact_repos
        )

    def compile_base(self, cmd = None):
        return super().compile_base(cmd, 'devops/parent/build/pom.xml')

    # ------------------------------------------------------

    def metric_id(self, module_name = None):
        return const.METRIC_ID_UMEBN

class sdno_build(build):
    def __init__(self):
        artifact_repos = {
            'snapshot'  : 'sdno-snapshot-generic',
            'alpha'     : 'sdno-alpha-generic',
            'release'   : 'sdno-release-generic'
        }

        super().__init__(
            'sdno',
            builtin_os.join(const.SSH_GIT, 'sdno'),
            artifact_repos
        )

    def compile_base(self, cmd = None):
        return True

    # ------------------------------------------------------

    def metric_id(self, module_name = None):
        return const.METRIC_ID_SDNO

class bn_build(build):
    def __init__(self):
        artifact_repos = {
            'snapshot'  : 'U31R22-snapshot-generic',
            'alpha'     : 'U31R22-alpha-generic',
            'release'   : 'U31R22-release-generic'
        }

        super().__init__(
            'bn',
            None,
            artifact_repos
        )

    def update(self, module, branch = None):
        pass

    def compile(self, module, cmd = None, clean = False, retry_cmd = None, dirname = None, lang = None):
        pass

    # ------------------------------------------------------

    def metric_id(self, module_name = None):
        if module_name in ('interface', 'platform', 'necommon', 'uca', 'sdh', 'ptn'):
            return const.METRIC_ID_BN_ITN
        elif module_name in ('ptn2', 'ip'):
            return const.METRIC_ID_BN_IPN
        elif module_name in ('e2e'):
            return const.METRIC_ID_BN_E2E
        elif module_name in ('xmlfile', 'nbi'):
            return const.METRIC_ID_BN_NBI
        elif module_name in ('wdm'):
            return const.METRIC_ID_BN_OTN
        else:
            return None
