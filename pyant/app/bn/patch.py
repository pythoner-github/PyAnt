import collections
import datetime
import glob
import os
import os.path
import re
import shutil
import zipfile

from lxml import etree

from pyant import git, maven
from pyant.app import const, __patch__, __installation__
from pyant.app.bn import build
from pyant.builtin import __os__, __string__

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
#                   code
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

        self.name = 'bn'
        self.type = 'ems'
        self.notification = '<BN_PATCH 通知>'

        for name, url in const.BN_REPOS.items():
            self.modules[os.path.basename(url)] = url

    def init(self, branch = None):
        if not super().init(branch):
            return False

        status = True

        with __os__.chdir(self.path) as chdir:
            os.makedirs('code', exist_ok = True)

            with __os__.chdir('code') as _chdir:
                for module in self.modules:
                    if os.path.isdir(module):
                        if not git.pull(module, revert = True):
                            status = False
                    else:
                        if not git.clone(self.modules[module], module, branch):
                            status = False

            for file in glob.iglob('build/*/.git', recursive = True):
                try:
                    shutil.rmtree(file)
                except:
                    pass

        return status

    # ------------------------------------------------------

    def build_permit(self, info):
        if info.get('os'):
            if __os__.osname() not in info['os']:
                return False

        return True

    def build_delete(self, info):
        path = os.path.join('build', info['name'])

        if info['delete']:
            if os.path.isdir(path):
                with __os__.chdir(path) as chdir:
                    for file in info['delete']:
                        try:
                            if os.path.isfile(file):
                                os.remove(file)
                            else:
                                shutil.rmtree(file)
                        except:
                            pass

        return True

    def build_source(self, info):
        path = os.path.join('code', info['name'])

        if info['source']:
            if not os.path.isdir(path):
                print('no such directory: %s' % os.path.normpath(path))

                return False

            if not git.pull(path, revert = True):
                return False

            with __os__.chdir(path) as chdir:
                for file in info['source']:
                    if os.path.isfile(file):
                        dest = os.path.join('../../build', info['name'], file)
                        os.makedirs(os.path.dirname(dest), exist_ok = True)

                        try:
                            shutil.copyfile(file, dest)
                        except Exception as e:
                            print(e)

                            return False
                    elif os.path.isdir(file):
                        for filename in glob.iglob(os.path.join(file, '**/*'), recursive = True):
                            if os.path.isfile(filename):
                                dest = os.path.join('../../build', info['name'], filename)
                                os.makedirs(os.path.dirname(dest), exist_ok = True)

                                try:
                                    shutil.copyfile(filename, dest)
                                except Exception as e:
                                    print(e)

                                    return False
                    else:
                        return False

        return True

    def build_compile(self, info):
        path = os.path.join('build', info['name'])

        if info['compile']:
            if not os.path.isdir(path):
                print('no such directory: %s' % os.path.normpath(path))

                return False

            with __os__.chdir('build') as chdir:
                build.build().environ('cpp')

            with __os__.chdir(path) as chdir:
                for build_path, clean in info['compile'].items():
                    if os.path.isdir(build_path):
                        with __os__.chdir(build_path) as _chdir:
                            mvn = maven.maven()
                            mvn.notification = '%s 编译失败, 请尽快处理' % self.notification

                            if clean:
                                mvn.clean()

                            if re.search(r'code_c\/', build_path):
                                if not mvn.compile('mvn deploy -fn -U -Djobs=10', 'mvn deploy -fn -U', 'cpp'):
                                    return False
                            else:
                                if not mvn.compile('mvn deploy -fn -U', 'mvn deploy -fn -U'):
                                    return False
                    else:
                        print('no such directory: %s' % os.path.normpath(build_path))

                        return False

        return True

    def build_deploy(self, info, path):
        build_path = os.path.join('build', info['name'])

        if info['deploy']:
            if not os.path.isdir(build_path):
                print('no such directory: %s' % os.path.normpath(build_path))

                return False

            with __os__.chdir(build_path) as chdir:
                for src_and_dest, types in info['deploy'].items():
                    src, dest = src_and_dest.split(':', 1)

                    if os.path.isfile(src):
                        filename = self.expand_filename(src)

                        if filename:
                            for type in types:
                                if not self.build_deploy_file(filename, os.path.join(path, type, dest)):
                                    return False
                    elif os.path.isdir(src):
                        with __os__.chdir(src) as _chdir:
                            for filename in glob.iglob('**/*', recursive = True):
                                if os.path.isfile(filename):
                                    filename = self.expand_filename(filename)

                                    if filename:
                                        for type in types:
                                            if not self.build_deploy_file(filename, os.path.join(path, type, dest, filename)):
                                                return False
                    else:
                        print('no such file or directory: %s' % os.path.normpath(src))

                        return False

        if info.get('script'):
            if not self.build_deploy_script(info['script'], info['zip'], path):
                status = False

        if info['deploy_delete']:
            for k, v in info['deploy_delete'].items:
                for type in v:
                    try:
                        os.makedirs(os.path.join(path, type), exist_ok = True)
                    except:
                        pass

        return True

    def build_deploy_file(self, src_file, dest_file):
        try:
            os.makedirs(os.path.dirname(dest_file), exist_ok = True)

            shutil.copyfile(src_file, dest_file)

            pathname, extname = os.path.splitext(src_file)

            if extname.lower() in ('.dll'):
                if os.path.isfile('%s.pdb' % pathname):
                    shutil.copyfile('%s.pdb' % pathname, '%s.pdb' % os.path.splitext(dest_file)[0])
            elif extname.lower() in ('.so'):
                if os.path.isfile('%s.debuginfo' % pathname):
                    shutil.copyfile('%s.debuginfo' % pathname, '%s.debuginfo' % os.path.splitext(dest_file)[0])
            else:
                pass

            return True
        except Exception as e:
            print(e)

            return False

    def build_deploy_script(self, types, zipfilename, path):
        if zipfilename:
            zipfilename = os.path.abspath(zipfilename)

            if not os.path.isfile(zipfilename):
                print('找不到增量补丁包对应的zip文件: %s' % os.path.normpath(zipfilename))

                return False

            with __os__.tmpdir(os.path.join(path, '../zip', os.path.basename(path))) as tmpdir:
                try:
                    with zipfile.ZipFile(zipfilename) as zip:
                        zip.extractall()
                except Exception as e:
                    print(e)

                    return False

                install = None

                for file in glob.iglob('**/install/dbscript-patch/ums-db-update-info.xml'):
                    install = os.path.dirname(os.path.dirname(file))

                    break

                if not install:
                    print('增量补丁包中找不到install/dbscript-patch/ums-db-update-info.xml')

                    return False

                prefix = 'install'

                m = re.search(r'\/(pmu|ppu)\/', install)

                if m:
                    prefix = os.path.join(m.group(1), m.string[m.end():])

                with __os__.chdir(install) as chdir:
                    for file in glob.iglob('dbscript-patch/**/*', recursive = True):
                        if os.path.isfile(file):
                            for type in types:
                                try:
                                    shutil.copyfile(file, os.path.join(path, type, prefix, file))
                                except Exception as e:
                                    print(e)

                                    return False

        return True

    def expand_filename(self, file):
        pathname, extname = os.path.splitext(file)

        if __os__.osname() in ('windows', 'windows-x64'):
            if extname.lower() in ('.sh'):
                return '%s.bat' % pathname
            elif extname.lower() in ('.so'):
                m = re.search(r'^lib(.*)$', os.path.basename(pathname))

                if m:
                    return os.path.join(os.path.dirname(pathname), '%s.dll' % m.group(1))
                else:
                    return '%s.dll' % pathname
            else:
                return file
        else:
            if extname.lower() in ('.bat'):
                return '%s.sh' % pathname
            elif extname.lower() in ('.dll', '.lib'):
                return os.path.join(os.path.dirname(pathname), 'lib%s.so' % os.path.basename(pathname))
            elif extname.lower() in ('.exe'):
                return pathname
            else:
                return file

    # info:
    #   name            : ''
    #   delete          : []
    #   source          : []
    #   compile         : {}
    #   deploy          : {}
    #   deploy_delete   : {}
    #   info            : {}
    #
    #   options
    #       os          : []
    #       script      : []
    #       zip         : ''
    def __load_xml__(self, info, element, file):
        status = True

        osname = element.get('os', '').strip()

        if osname:
            info['os'] = __string__.split(osname)

            if not set(info['os']) - set(('windows', 'linux', 'solaris')):
                print('patch[%s]: patch节点的os属性值错误, 只能包含windows, linux, solaris' % index)

                status = False

        script = element.get('script', '').strip()

        if script:
            zipfilename = self.get_xml_zipfile(file)

            if zipfilename:
                info['script'] = self.types(script)
                info['zip'] = zipfilename

                if not os.path.isfile(info['zip']):
                    print('patch[%s]: 找不到增量脚本对应的zip文件 - %s' % (index, info['zip']))

                    status = False

        info['delete'] = []
        info['compile'] = collections.OrderedDict()
        info['deploy'] = collections.OrderedDict()
        info['deploy_delete'] = collections.OrderedDict()

        for e_delete in element.findall('delete/attr'):
            name = __os__.normpath(e_delete.get('name', '').strip())

            if name:
                if name not in info['delete']:
                    info['delete'].append(name)
            else:
                print('patch[%s]/delete/attr: delete下attr节点的name属性不能为空' % index)

                status = False

        for e_compile in element.findall('compile/attr'):
            name = __os__.normpath(e_compile.get('name', '').strip())
            clean = e_compile.get('clean', '').strip().lower()

            if name:
                if clean:
                    if clean == 'true':
                        clean = True
                    else:
                        clean = False
                else:
                    if re.search(r'^code\/', name):
                        clean = True
                    else:
                        clean = False

                info['compile'][name] = clean
            else:
                print('patch[%s]/compile/attr: compile下attr节点的name属性不能为空' % index)

                status = False

        for e_deploy in element.findall('deploy/deploy/attr'):
            name = __os__.normpath(e_deploy.get('name', '').strip())
            dest = e_deploy.text
            type = e_deploy.get('type', '').strip()

            if dest is not None:
                dest = __os__.normpath(dest.strip())

            types = self.types(type)

            if name:
                m = re.search(r'^(code|code_c)\/build\/output\/', name)

                if m:
                    if not dest:
                        dest = m.string[m.end():]

                    m = re.search(r'^ums-(\w+)', dest)

                    if m:
                        if m.group(1) in ('nms', 'lct'):
                            types = [m.group(1)]

                            dest = dest.replace(m.string[m.start():m.end()], 'ums-client')

                    info['deploy'][':'.join((name, dest))] = types
                elif re.search(r'^installdisk\/', name):
                    if dest:
                        info['deploy'][':'.join((name, dest))] = types
                    else:
                        print('patch[%s]/deploy/deploy/attr: installdisk目录下的文件, 必须提供输出路径' % index)

                        status = False
                else:
                    print('patch[%s]/deploy/deploy/attr: 源文件必须以code/build/output, code_c/build/output或installdisk开始' % index)

                    status = False
            else:
                print('patch[%s]/deploy/deploy/attr: deploy/deploy下attr节点的name属性不能为空' % index)

                status = False

        for e_deploy_delete in element.findall('deploy/delete/attr'):
            name = __os__.normpath(e_deploy_delete.get('name', '').strip())
            type = e_deploy_delete.get('type', '').strip()

            types = self.types(type)

            if name:
                m = re.search(r'^ums-(\w+)', name)

                if m:
                    if not m.group(1) in ('client', 'server'):
                        print('patch[%s]/deploy/delete/attr: deploy/delete下attr节点的name属性错误, 根目录应该为ums-client或ums-server' % index)

                        status = False

                info['deploy_delete'][name] = types
            else:
                print('patch[%s]/deploy/delete/attr: deploy/delete下attr节点的name属性不能为空' % index)

                status = False

        return status

    def __to_xml__(self, info, element):

        if info.get('os'):
            element.set('os', ', '.join(info['os']))

        if info.get('script'):
            element.set('script', ', '.join(info['script']))

        if info['delete']:
            delete_element = etree.Element('delete')
            element.append(delete_element)

            for x in info['delete']:
                e = etree.Element('attr')
                e.set('name', x)

                delete_element.append(e)

        if info['source']:
            source_element = etree.Element('source')
            element.append(source_element)

            for x in info['source']:
                e = etree.Element('attr')
                e.set('name', x)

                source_element.append(e)

        if info['compile']:
            compile_element = etree.Element('compile')
            element.append(compile_element)

            for x in info['compile']:
                e = etree.Element('attr')
                e.set('name', x)
                e.set('clean', str(info['compile'][x]).lower())

                compile_element.append(e)

        if info['deploy'] or info['deploy_delete']:
            deploy_element = etree.Element('deploy')
            element.append(deploy_element)

            if info['deploy']:
                deploy_deploy_element = etree.Element('deploy')
                deploy_element.append(deploy_deploy_element)

                for x in info['deploy']:
                    name, *dest = x.split(':', 1)

                    e = etree.Element('attr')
                    e.set('name', name)
                    e.text = ''.join(dest)

                    types = info['deploy'][x]

                    if types != [self.type]:
                        e.set('type', ', '.join(types))

                    deploy_deploy_element.append(e)

            if info['deploy_delete']:
                deploy_delete_element = etree.Element('delete')
                deploy_element.append(deploy_delete_element)

                for x in info['deploy_delete']:
                    e = etree.Element('attr')
                    e.set('name', x)

                    types = info['deploy_delete'][x]

                    if types != [self.type]:
                        e.set('type', ', '.join(types))

                    deploy_delete_element.append(e)

        return True

    def get_xml_zipfile(self, file):
        return '%s.zip' % file[0:-4]

    def types(self, type):
        types = []

        if not type:
            type = self.type

        for x in __string__.split(type):
            if x in ('ems', 'nms', 'upgrade', 'lct', 'su31', 'su31nm', 'su31-e2e', 'su31-nme2e', 'service'):
                if x not in types:
                    types.append(x)
            else:
                return None

        if 'service' in types:
            if 'ems' not in types:
                types.append('ems')

        return types

# ******************************************************** #
#                    PATCH INSTALLATION                    #
# ******************************************************** #

class installation(__installation__):
    def __init__(self, path):
        super().__init__(path)

        if not os.path.isdir(self.output):
            if os.path.isdir(os.path.join(self.path, 'build/patch')):
                self.output = os.path.join(self.path, 'build/patch')

        self.name = 'bn'
        self.type = 'ems'

    # ------------------------------------------------------

    def process(self, version, display_version, id_info, sp_next, type):
        suffix = self.patchname(version, sorted(id_info.keys())[-1], sp_next, type)
        patchsets = self.patchset_names(version, type)

        # pmu

        if os.path.isdir('pmu'):
            for dirname in glob.iglob('pmu/*'):
                with __os__.chdir(dirname) as chdir:
                    self.name = os.path.basename(dirname)
                    ppuname = self.name.split('-')[0]
                    pmuname = self.name

                    tmp_id_info = {}

                    for id, value in id_info.items():
                        if os.path.isdir(os.path.join(value, 'pmu', self.name)):
                            tmp_id_info[id] = os.path.join(value, 'pmu', self.name)

                    if not self.__process__(suffix, patchsets, version, display_version, tmp_id_info, sp_next, type, ppuname, pmuname):
                        return False
            try:
                shutil.rmtree('pmu')
            except:
                pass

        # bn

        if not self.ppuinfo(version, display_version):
            return False

        self.name = 'bn'
        ppuname = 'bn'

        tmp_id_info = {}

        for id, value in id_info.items():
            if os.path.isdir(os.path.join(value, 'pmu')):
                if len(glob.glob(os.path.join(value, '*'))) > 1:
                    tmp_id_info[id] = value
            else:
                tmp_id_info[id] = value

        if not self.__process__(suffix, patchsets, version, display_version, tmp_id_info, sp_next, type, ppuname):
            return False

        return True

    def installation(self, version, type):
        osname = __os__.osname()

        if type not in ('ems'):
            osname += "(%s)" % type

        return os.path.join(self.output, 'installation', version, osname, 'patch')

    def expand_filename(self, filename):
        extname = os.path.splitext(filename)[1].lower()

        if extname in ['.pdb', '.exp', '.lib', '.debuginfo']:
            return None

        return filename

    def get_patch_dirname(self, dirname, type = None):
        if not type:
            type = self.type

        path = os.path.join(dirname, 'patch', type)

        if not os.path.isdir(path):
            for _dir in glob.iglob(os.path.join(dirname, 'patch/*', type), recursive = True):
                path = _dir

        return path

    def patchname(self, version, id, sp_next, type):
        prefix = '-%s-SP' % version
        last_sp = 0
        last_index = 0

        installation = self.installation(version, type)

        if os.path.isdir(installation):
            with __os__.chdir(installation) as chdir:
                for filename in glob.iglob('*%s*.zip' % prefix):
                    m = re.search(r'-SP(\d+)\(001-(\d+)\)', filename)

                    if m:
                        last_sp = max(last_sp, int(m.group(1)))
                        last_index = max(last_index, int(m.group(2)))
                    else:
                        m = re.search(r'-SP(\d+)\((\d+)\)', filename)

                        if m:
                            last_sp = max(last_sp, int(m.group(1)))
                            last_index = max(last_index, int(m.group(2)))

        if sp_next or last_sp == 0:
            last_sp += 1

        return '%s%03d(%03d)-%s' % (prefix, last_sp, last_index + 1, id)

    def patchset_names(self, version, type):
        prefix = '-%s-SP' % version
        last_index = 0

        installation = self.installation(version, type)

        if os.path.isdir(installation):
            with __os__.chdir(installation) as chdir:
                for filename in glob.iglob('*%s*.zip' % prefix):
                    m = re.search(r'-SP(\d+)\(001-(\d+)\)', filename)

                    if m:
                        last_index = max(last_index, int(m.group(2)))
                    else:
                        m = re.search(r'-SP(\d+)\((\d+)\)', filename)

                        if m:
                            last_index = max(last_index, int(m.group(2)))

        last_index += 1

        names = []

        for i in range(last_index):
            names.append('%s-%s-%03d' % (self.name, version, i + 1))

        return names

    def ppuinfo(self, version, display_version):
        # ums-client/procs/ppus/bn.ppu/ppuinfo.xml
        # ums-server/procs/ppus/bn.ppu/ppuinfo.xml

        tree = etree.ElementTree(etree.XML("<ppu/>"))

        display_element = etree.Element('display-name')
        display_element.set('en_US', 'BN-xTN')
        display_element.set('zh_CN', 'BN-xTN')

        tree.getroot().append(display_element)

        info_element = etree.Element('info')
        info_element.set('version', version)
        info_element.set('display-version', display_version)
        info_element.set('en_US', 'Bearer Network Transport Common Module')
        info_element.set('zh_CN', '承载传输公用组件')

        tree.getroot().append(info_element)

        for filename in ('ums-client/procs/ppus/bn.ppu/ppuinfo.xml', 'ums-server/procs/ppus/bn.ppu/ppuinfo.xml'):
            os.makedirs(os.path.dirname(filename), exist_ok = True)

            try:
                tree.write(filename, encoding='gb2312', pretty_print=True, xml_declaration=True)
            except Exception as e:
                print(e)

                return False

        # ums-client/procs/ppus/e2e.ppu/ppuinfo.xml
        # ums-server/procs/ppus/e2e.ppu/ppuinfo.xml

        display_element.set('en_US', 'E2E')
        display_element.set('zh_CN', 'E2E')

        info_element.set('en_US', 'End-To-End Module')
        info_element.set('zh_CN', '端到端组件')

        for filename in ('ums-client/procs/ppus/e2e.ppu/ppuinfo.xml', 'ums-server/procs/ppus/e2e.ppu/ppuinfo.xml'):
            os.makedirs(os.path.dirname(filename), exist_ok = True)

            try:
                tree.write(filename, encoding='gb2312', pretty_print=True, xml_declaration=True)
            except Exception as e:
                print(e)

                return False

        return True

    def __process__(self, suffix, patchsets, version, display_version, id_info, sp_next, type, ppuname, pmuname = None):
        zipname = '%s%s' % (self.name, suffix)
        installation = self.installation(version, type)

        if not self.process_extend(zipname, type):
            return False

        if not self.dbscript_patch(sorted(id_info.values()), patchsets, version, type):
            return False

        if not self.update_patchinfo(sorted(id_info.keys()), type):
            return False

        if not self.patchset_update_info(zipname, patchsets, sorted(id_info.keys()), version, display_version, type, ppuname, pmuname):
            return False

        if __os__.osname() in ('linux', 'solaris'):
            for filename in glob.iglob('**/*.dll', recursive = True):
                os.remove(filename)

        zip_filename = os.path.join(installation, '%s%s.zip' % zipname)

        try:
            if not os.path.isdir(os.path.dirname(zip_filename)):
                os.makedirs(os.path.dirname(zip_filename), exist_ok = True)

            with zipfile.ZipFile(zip_filename, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
                for line in ('$ zipfile: %s' % zip.filename, '  in (' + os.getcwd() + ')'):
                    print(line)

                for filename in glob.iglob('**/*', recursive = True):
                    if os.path.isfile(filename):
                        zip.write(filename)
        except Exception as e:
            print(e)

            return False

        if not self.__change_info__(id_info, installation, zipname):
            return False

        print('installation:', zip_filename)

        return True

    def process_extend(self, zipname, type):
        path = os.path.join(self.path, 'build')

        if os.path.isdir(os.path.join(path, 'code')):
            path = os.path.join(path, 'code')

        cwd = os.getcwd()
        vars = {
            'zipname': zipname
        }

        with __os__.chdir(path) as chdir:
            for file in glob.iglob('*/installdisk/extends.xml'):
                try:
                    tree = etree.parse(file)
                except Exception as e:
                    print(e)

                    return False

                for e in tree.findall(os.path.join(type, 'patch')):
                    dirname = e.get('dirname')

                    if dirname:
                        dirname = __os__.normpath(os.path.join(os.path.dirname(file), dirname.strip()))

                        if os.path.isdir(dirname):
                            with __os__.chdir(dirname) as _chdir:
                                copies = collections.OrderedDict()

                                for element in e.findall('file'):
                                    name = element.get('name')
                                    dest = element.get('dest')

                                    if name and dest:
                                        name = __os__.normpath(__string__.vars_expand(name.strip(), vars))
                                        dest = __os__.normpath(__string__.vars_expand(dest.strip(), vars))

                                        if os.path.isfile(name):
                                            copies[dest] = name
                                        elif os.path.isdir(name):
                                            with __os__.chdir(name) as tmp_chdir:
                                                for filename in glob.iglob('**/*', recursive = True):
                                                    if os.path.isfile(filename):
                                                        copies[os.path.join(dest, filename)] = os.path.join(name, filename)
                                        else:
                                            print('no such file or directory: %s' % os.path.abspath(name))

                                for element in e.findall('ignore'):
                                    name = element.get('name')

                                    if name:
                                        name = __os__.normpath(__string__.vars_expand(name.strip(), vars))

                                        if os.path.isfile(name):
                                            if name in copies:
                                                del copies[name]
                                        elif os.path.isdir(name):
                                            for filename in glob.iglob(os.path.join(name, '**/*'), recursive = True):
                                                if os.path.isfile(filename):
                                                    if filename in copies:
                                                        del copies[filename]
                                        else:
                                            print('no such file or directory: %s' % os.path.abspath(name))

                                for dest, name in copies.items():
                                    try:
                                        dst = os.path.join(cwd, dest)

                                        if not os.path.isdir(os.path.dirname(dst)):
                                            os.makedirs(os.path.dirname(dst), exist_ok = True)

                                        shutil.copyfile(name, dst)
                                    except Exception as e:
                                        print(e)

                                        return False
                        else:
                            print('no such directory: %s' % dirname)

        return True

    def dbscript_patch(self, paths, patchsets, version, type):
        dirname = os.path.join('scripts', patchsets[-1])

        if os.path.isdir('install/dbscript-patch'):
            filenames = []

            for dir in glob.iglob('install/dbscript-patch/*'):
                if os.path.isdir(dir):
                    with __os__.chdir(dir) as chdir:
                        for file in glob.iglob('**/*', recursive = True):
                            if os.path.isfile(file):
                                filenames.append(os.path.join(os.path.basename(dir), file))

            if filenames:
                for file in filenames:
                    os.makedirs(os.path.dirname(os.path.join(dirname, file)), exist_ok = True)

                    try:
                        shutil.copyfile(os.path.join('install/dbscript-patch', file), os.path.join(dirname, file))
                    except Exception as e:
                        print(e)

                        return False

            try:
                shutil.rmtree('install/dbscript-patch')
            except:
                pass

        dbs = {}
        name = 'install/dbscript-patch/ums-db-update-info.xml'

        for path in paths:
            file = os.path.join(path, name)

            if os.path.isfile(file):
                try:
                    tree = etree.parse(file)
                except Exception as e:
                    print(e)

                    return False

                for e in tree.findall('data-source'):
                    data_source = e.get('key', '').strip()

                    if data_source:
                        if data_source not in dbs:
                            dbs[data_source] = {}

                        for element in e.findall('*//item'):
                            xpath = '/'.join(re.sub(r'[\[\]\d]+', '', tree.getelementpath(element)).split('/')[1:-1])

                            filename = __os__.normpath(element.get('filename', '').strip())
                            rollback = __os__.normpath(element.get('rollback', '').strip())

                            if not filename or not rollback:
                                print('%s: filename or rollback is empty' % file)

                                return False

                            if xpath not in dbs[data_source]:
                                dbs[data_source][xpath] = {}

                            dbs[data_source][xpath][filename] = element.items()

        tree = etree.ElementTree(etree.XML("<install-db/>"))

        for data_source in dbs:
            element = etree.Element('data-source')
            element.set('key', data_source)

            for xpath in dbs[data_source]:
                lang, dbname, normal, *_ = xpath.split('/')

                lang_element = etree.Element(lang)
                element.append(lang_element)

                dbname_element = etree.Element(dbname)
                lang_element.append(dbname_element)

                normal_element = etree.Element(normal)
                dbname_element.append(normal_element)

                for filename in sorted(dbs[data_source][xpath]):
                    item_element = etree.Element('item')
                    normal_element.append(item_element)

                    rollback = ''
                    attrs = []

                    for key, value in sorted(dbs[data_source][xpath][filename]):
                        if key == 'filename':
                            pass
                        elif key == 'rollback':
                            rollback = value
                        else:
                            attrs.append((key, value))

                    item_element.set('filename', filename)
                    item_element.set('rollback', rollback)

                    for key, value in attrs:
                        item_element.set(key, value)

            tree.getroot().append(element)

        os.makedirs(dirname, exist_ok = True)

        try:
            tree.write(os.path.join(dirname, 'ums-db-update-info.xml'), encoding='utf-8', pretty_print=True, xml_declaration=True)
        except Exception as e:
            print(e)

            return False

        return True

    def update_patchinfo(self, ids, type):
        tree = etree.ElementTree(etree.XML("<update/>"))
        tree_defect = etree.ElementTree(etree.XML("<update/>"))

        with __os__.chdir(self.output) as chdir:
            for id in ids:
                if os.path.isdir(os.path.join('patch', id, 'ids')):
                    for file in glob.iglob(os.path.join('patch', id, 'ids/*.xml')):
                        info = self.get_patch_info(file)

                        if info:
                            element = etree.Element('info')
                            element.set('name', id)

                            attr_element = etree.Element('attr')
                            attr_element.set('name', '提交人员')
                            attr_element.text = info['info']['提交人员']
                            element.append(attr_element)

                            attr_element = etree.Element('attr')
                            attr_element.set('name', '开发经理')
                            attr_element.text = info['info']['开发经理']
                            element.append(attr_element)

                            attr_element = etree.Element('attr')
                            attr_element.set('name', '变更描述')
                            attr_element.text = info['info']['变更描述']
                            element.append(attr_element)

                            if info['info']['变更类型'] in ('故障', ):
                                tree_defect.getroot().append(element)
                            else:
                                tree.getroot().append(element)
                else:
                    for file in glob.iglob(os.path.join('patch', id, '*.xml')):
                        info = self.get_patch_info(file)

                        if info:
                            element = etree.Element('info')
                            element.set('name', id)

                            attr_element = etree.Element('attr')
                            attr_element.set('name', '提交人员')
                            attr_element.text = info['info']['提交人员']
                            element.append(attr_element)

                            attr_element = etree.Element('attr')
                            attr_element.set('name', '开发经理')
                            attr_element.text = info['info']['开发经理']
                            element.append(attr_element)

                            attr_element = etree.Element('attr')
                            attr_element.set('name', '变更描述')
                            attr_element.text = info['info']['变更描述']
                            element.append(attr_element)

                            if info['info']['变更类型'] in ('故障', ):
                                tree_defect.getroot().append(element)
                            else:
                                tree.getroot().append(element)

                        break

        dirname = os.path.join('update/patchinfo', datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        os.makedirs(dirname, exist_ok = True)

        try:
            tree.write(os.path.join(dirname, 'update.xml'), encoding='utf-8', pretty_print=True, xml_declaration=True)
            tree_defect.write(os.path.join(dirname, 'update_defect.xml'), encoding='utf-8', pretty_print=True, xml_declaration=True)
        except Exception as e:
            print(e)

            return False

        return True

    def patchset_update_info(self, zipname, patchsets, ids, version, display_version, type, ppuname, pmuname):
        tree = etree.ElementTree(etree.XML("<update-info/>"))

        if ppuname == 'bn-ip':
            ppuname = 'bn'
            pmuname = 'bn-ip'
        elif ppuname == 'bn':
            if type == 'ems':
                ppuname = 'e2e'
        else:
            pass

        tree.getroot().set('ppuname', ppuname)

        if pmuname:
            tree.getroot().set('pmuname', pmuname)

        if type == 'service':
            tree.getroot().set('ppuname', 'bn')
            tree.getroot().set('pmuname', 'bn-servicetools')
            tree.getroot().set('hotpatch', 'true')

        element = etree.Element('description')

        e = etree.Element('zh_cn')
        e.text = 'NetNumen U31统一网管系统%s' % display_version
        element.append(e)

        e = etree.Element('en_us')
        e.text = 'NetNumen U31 Unified Network Management System %s' % display_version
        element.append(e)

        tree.getroot().append(element)

        if type == 'service':
            element = etree.Element('hotpatch')
            element.set('restart-client', 'true')
            element.set('run-operation', 'true')
            tree.getroot().append(element)

            element = etree.Element('pmus')
            e = etree.Element('pmu')
            e.set('name', 'bn-servicetools')
            element.append(e)
            tree.getroot().append(element)

        element = etree.Element('src-version')
        e = etree.Element('version')
        e.set('main', version)
        element.append(e)
        tree.getroot().append(element)

        element = etree.Element('patchs')

        for name in patchsets:
            e = etree.Element('patch')
            e.text = name
            element.append(e)

        tree.getroot().append(element)

        delete_files = []

        with __os__.chdir(self.output) as chdir:
            for id in ids:
                if os.path.isdir(os.path.join('patch', id, 'ids')):
                    for file in glob.iglob(os.path.join('patch', id, 'ids/*.xml')):
                        deletes = self.get_patch_deletes(file, type)

                        for delete_file in deletes:
                            if delete_file not in delete_files:
                                delete_files.append(delete_file)
                else:
                    for file in glob.iglob(os.path.join('patch', id, '*.xml')):
                        deletes = self.get_patch_deletes(file, type)

                        for delete_file in deletes:
                            if delete_file not in delete_files:
                                delete_files.append(delete_file)

                        break

        if delete_files:
            element = etree.Element('delete-file-list')

            for file in delete_files:
                e = etree.Element('file-item')
                e.set('delfile', file)
                element.append(e)

            tree.getroot().append(element)

        dirname = os.path.join('update-info', zipname)
        os.makedirs(dirname, exist_ok = True)

        try:
            tree.write(os.path.join(dirname, 'patchset-update-info.xml'), encoding='utf-8', pretty_print=True, xml_declaration=True)
        except Exception as e:
            print(e)

            return False

        return True

    def get_patch_deletes(self, file, type):
        try:
            tree = etree.parse(file)
        except Exception as e:
            print(e)

            return []

        deletes = []

        for e in tree.findall('patch/deploy/delete/attr'):
            name = __os__.normpath(e.get('name', '').strip())
            cur_type = e.get('type', '').strip()

            if not cur_type:
                cur_type = self.type

            types = []

            for x in cur_type.split(','):
                types.append(x.strip())

            if 'service' in types:
                types.append('ems')

            if type in types:
                deletes.append(name)

        return deletes
