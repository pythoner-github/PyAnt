import datetime
import glob
import os
import os.path
import re
import shutil
import tarfile

from lxml import etree

from pyant import git, maven
from pyant.app import const, __patch__, __installation__
from pyant.app.umebn import build
from pyant.builtin import __os__

__all__ = ('patch', 'installation')

# ******************************************************** #
#                          PATCH                           #
# ******************************************************** #

# 目录结构
#   patch
#       build
#           dev
#           release
#               20171203
#                   build
#                   xml
#       patch
#           dev
#           release
#               20171203
#                   installation
#                   patch
class patch(__patch__):
    def __init__(self, path, version = None):
        super().__init__(path, version)

        self.name = 'umebn'
        self.notification = '<UMEBN_PATCH 通知>'
        self.modules = {
            'umebn' : const.UMEBN_REPOS
        }

    def init(self, branch = None):
        if not super().init(branch):
            return False

        with __os__.chdir(self.path) as chdir:
            dir = os.path.join('build', self.name)

            if os.path.isdir(dir):
                if not git.pull(dir, revert = True):
                    return False
            else:
                if not git.clone(self.modules['umebn'], dir, branch):
                    return False

        return True

    # ------------------------------------------------------

    def build_source(self, info):
        path = os.path.join('build', info['name'])

        if info['source']:
            if not os.path.isdir(path):
                print('no such directory: %s' % os.path.normpath(path))

                return False

            with __os__.chdir(path) as chdir:
                for dir in info['source']:
                    if not git.pull(dir, revert = True):
                        return False

        return True

    def build_compile(self, info):
        path = os.path.join('build', info['name'])

        if info['source']:
            if not os.path.isdir(path):
                print('no such directory: %s' % os.path.normpath(path))

                return False

            with __os__.chdir(path) as chdir:
                for dir in info['source']:
                    build_path = os.path.join(dir, 'build')

                    if not os.path.isdir(build_path):
                        build_path = dir

                    if os.path.isdir(build_path):
                        with __os__.chdir(build_path) as _chdir:
                            mvn = maven.maven()
                            mvn.notification = '%s 编译失败, 请尽快处理' % self.notification

                            mvn.clean()

                            if not mvn.compile('mvn deploy -fn -U', 'mvn deploy -fn -U', None, True):
                                return False

                        if not self.oki(build_path, os.environ.get('VERSION')):
                            return False
                    else:
                        print('no such directory: %s' % os.path.normpath(build_path))

                        return False

        return True

    def build_deploy(self, info, path):
        build_path = os.path.join('build', info['name'])

        if info['source']:
            if not os.path.isdir(build_path):
                print('no such directory: %s' % os.path.normpath(build_path))

                return False

            with __os__.chdir(build_path) as chdir:
                for dir in info['source']:
                    deploy_path = os.path.join(dir, 'build/output')

                    if os.path.isdir(deploy_path):
                        with __os__.chdir(deploy_path) as _chdir:
                            for filename in glob.iglob('app/**/*', recursive = True):
                                if os.path.isfile(filename):
                                    filename = self.expand_filename(filename)

                                    if filename:
                                        dest = os.path.join(path, filename)

                                        try:
                                            os.makedirs(os.path.dirname(dest), exist_ok = True)
                                            shutil.copyfile(filename, dest)
                                        except Exception as e:
                                            print(e)

                                            return False
                    else:
                        print('no such directory: %s' % os.path.normpath(deploy_path))

        return True

    def build_check(self, path):
        if not super().build_check(path):
            return False

        if os.path.isdir(path):
            with __os__.chdir(path) as chdir:
                for dir in glob.iglob('app/*'):
                    if os.path.isdir(dir):
                        with __os__.chdir(dir) as _chdir:
                            appname = os.path.basename(dir)

                            # commonservice-instance-config.xml
                            # *.spd
                            # *.tar.gz

                            if not os.path.isfile('commonservice-instance-config.xml'):
                                print('no such file: %s' % os.path.abspath('commonservice-instance-config.xml'))

                                return False

                            if not os.path.isfile('%s.spd' % appname):
                                print('no such file: %s' % os.path.abspath('%s.spd' % appname))

                                return False

                            for tarname in glob.iglob('%s*.tar.gz' % appname):
                                with tarfile.open(tarname) as tar:
                                    try:
                                        tar.getmember(os.path.join(appname, 'install.sh'))
                                    except Exception as e:
                                        print('no such file: %s(%s)' % (os.path.join(appname, 'install.sh'), os.path.abspath(tarname)))

                                        return False

        return True

    def expand_filename(self, filename):
        return filename

    def __load_xml__(self, info, element, file):
        return True

    def __to_xml__(self, info, element):
        if info['source']:
            source_element = etree.Element('source')
            element.append(source_element)

            for x in info['source']:
                e = etree.Element('attr')
                e.set('name', x)

                source_element.append(e)

        return True

    def oki(self, path, version):
        return build.build().oki(path, version)

# ******************************************************** #
#                    PATCH INSTALLATION                    #
# ******************************************************** #

class installation(__installation__):
    def __init__(self, path):
        super().__init__(path)

        self.name = 'umebn'

    # ------------------------------------------------------

    def process(self, version, display_version, id_info, sp_next, type):
        installation = self.installation(version, type)

        try:
            if not os.path.isdir(installation):
                os.makedirs(installation, exist_ok = True)

            for file in glob.iglob('**/*', recursive = True):
                if os.path.isfile(file):
                    os.makedirs(os.path.dirname(os.path.join(installation, file)), exist_ok = True)

                    shutil.copyfile(file, os.path.join(installation, file))
        except Exception as e:
            print(e)

            return False

        if not self.__change_info__(id_info, installation, os.path.basename(installation)):
            return False

        print('installation:', installation)

        return True

    def installation(self, version, type):
        installation = os.path.join(self.output, 'installation', version)

        id= 0
        prefix = datetime.datetime.now().strftime('%Y%m%d')

        if os.path.isdir(installation):
            with __os__.chdir(installation) as chdir:
                for x in glob.iglob('%s_*' % prefix):
                    m = re.search(r'^\d{8}_(\d{4})$', x)

                    if m:
                        if id < int(m.group(1)):
                            id = int(m.group(1))

        return os.path.join(installation, '%s_%04d' % (prefix, id + 1))
