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

__all__ = ('build',)

class build():
    def __init__(self, name, repos, artifact_repos):
        self.name = name
        self.repos = repos
        self.artifact_repos = artifact_repos

        self.path = self.name
        self.type = 'none'

        self.load_env()

    def update(self, module = None, branch = None):
        return True

    def compile_pom(self, cmd = None, file = None):
        if not file:
            file = os.path.join(self.path, 'pom/pom.xml')

        if os.path.isfile(file):
            with __os__.chdir(os.path.dirname(file)) as chdir:
                mvn = maven.maven()

                return mvn.compile(cmd)
        else:
            print('no such file: %s' % os.path.normpath(file))

            return False

    def compile(self, cmd = None, clean = False, retry_cmd = None, dirname = None, lang = None, all = False):
        if not dirname:
            dirname = 'build'

        path = os.path.join(self.path, dirname)

        if os.path.isdir(path):
            with __os__.chdir(path) as chdir:
                mvn = maven.maven()
                mvn.notification = '<%s_BUILD 通知> 编译失败, 请尽快处理' % self.name.upper()

                if clean:
                    mvn.clean()

                return mvn.compile(cmd, retry_cmd, lang, all)
        else:
            print('no such directory: %s' % os.path.normpath(path))

            return False

    def package(self, version, type = None):
        path = os.path.dirname(self.package_home(version, type))

        if len(glob.glob(os.path.join(path, '*'))) > 5:
            try:
                shutil.rmtree(path)
            except:
                pass

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

    def metric_id(self, module_name = None):
        return None

    # ------------------------------------------------------

    def load_env(self):
        file = const.ENV_FILE

        if os.path.isfile(file):
            envs = collections.OrderedDict()

            with open(file) as f:
                for line in f:
                    m = re.search(r'\s*=\s*', line.strip())

                    if m and m.string[:m.start()]:
                        envs[m.string[:m.start()]] = m.string[m.end():]

            print()
            print('=' * 17, 'LOAD ENVIRONMENT VARIABLE', '=' * 16)

            for name in envs:
                os.environ[name] = envs[name]
                print('export %s=%s' % (name, os.environ[name]))

            print('=' * 60)
            print()

    def package_home(self, version, type):
        return os.path.normpath(os.path.abspath(os.path.join('../zipfile', type, version.replace(' ', ''))))

    def __artifactory__(self, path, artifact_path, artifact_filenames = None, suffix = None, targz = True, tarpath = None):
        if isinstance(artifact_filenames, str):
            artifact_filenames = [artifact_filenames]

        if not tarpath:
            tarpath = 'installation'

        if os.path.isdir(path):
            with __os__.tmpdir(tempfile.mkdtemp(), False) as tmpdir:
                # download

                if artifact_filenames:
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
                                def is_within_directory(directory, target):
                                    
                                    abs_directory = os.path.abspath(directory)
                                    abs_target = os.path.abspath(target)
                                
                                    prefix = os.path.commonprefix([abs_directory, abs_target])
                                    
                                    return prefix == abs_directory
                                
                                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                                
                                    for member in tar.getmembers():
                                        member_path = os.path.join(path, member.name)
                                        if not is_within_directory(path, member_path):
                                            raise Exception("Attempted Path Traversal in Tar File")
                                
                                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                                    
                                
                                safe_extract(tar, tarpath)
                        except Exception as e:
                            print(e)

                            return False

                # zip

                dst = os.path.join(os.getcwd(), tarpath.split('/')[0])

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
                            tar.add(tarpath.split('/')[0])
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
                            for file in glob.iglob(os.path.join(tarpath.split('/')[0], '**/*'), recursive = True):
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
