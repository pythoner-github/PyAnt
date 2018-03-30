import collections
import datetime
import glob
import os
import os.path
import random
import re
import shutil
import zipfile

from lxml import etree

from pyant import command, daemon, git, maven, password, smtp
from pyant.app import const
from pyant.app import build as app_build
from pyant.builtin import os as builtin_os

__all__ = (
    'auto',
    'stn_patch', 'umebn_patch', 'sdno_patch', 'bn_patch',
    'stn_installation', 'umebn_installation', 'sdno_installation', 'bn_installation'
)

def auto():
    status = True

    if os.path.isdir(const.PATCH_XML_HOME):
        with builtin_os.chdir(const.PATCH_XML_HOME) as chdir:
            print('===== 拷贝补丁申请单 =====')

            for dir in glob.iglob('*', recursive = True):
                if not os.path.isdir(dir):
                    try:
                        os.remove(dir)
                    except:
                        pass

                    continue

                m = re.search(r'^(stn|umebn|sdno|bn)_.*\((\d{8}.*)\)$', dir)

                if not m:
                    shutil.rmtree(dir, ignore_errors = True)

                    continue

                module = m.group(1)
                name = m.group(2)

                if module in ('bn',):
                    deploy_homes = [
                        os.path.join(const.PATCH_TEMPLATE_HOME, module, 'linux', name),
                        os.path.join(const.PATCH_TEMPLATE_HOME, module, 'solaris', name),
                        os.path.join(const.PATCH_TEMPLATE_HOME, module, 'windows', name),
                        os.path.join(const.PATCH_TEMPLATE_HOME, module, 'windows_x86', name)
                    ]
                else:
                    deploy_homes = [os.path.join(const.PATCH_TEMPLATE_HOME, module, 'none', name)]

                with builtin_os.chdir(dir) as _chdir:
                    for file in glob.iglob('**/*.xml', recursive = True):
                        try:
                            for deploy_home in deploy_homes:
                                os.makedirs(deploy_home, exist_ok = True)
                                shutil.copyfile(file, os.path.join(deploy_home, os.path.basename(file)))

                                if module in ('bn'):
                                    zipname = '%s.zip' % os.path.splitext(file)[0]

                                    if os.path.isfile(zipname):
                                        shutil.copyfile(zipname, os.path.join(deploy_home, os.path.basename(zipname)))
                        except Exception as e:
                            print(e)

                            status = False
                            continue

                shutil.rmtree(dir, ignore_errors = True)

    auto_info = []

    if os.path.isdir(const.PATCH_TEMPLATE_HOME):
        with builtin_os.chdir(const.PATCH_TEMPLATE_HOME) as chdir:
            print('===== 分发补丁申请单 =====')

            for dir in glob.iglob('*/*', recursive = True):
                if dir in const.PATCH_NODE_INFO:
                    ip, home = const.PATCH_NODE_INFO[dir]
                    proxy = daemon.PyroFileProxy(ip)

                    try:
                        proxy.proxy._pyroBind()
                    except:
                        continue

                    with builtin_os.chdir(dir) as _chdir:
                        for name in glob.iglob('*', recursive = True):
                            try:
                                if proxy.isdir(builtin_os.join(home, 'patch/build', 'dev', name)):
                                    build_home = builtin_os.join(home, 'patch/build', 'dev', name)
                                elif proxy.isdir(builtin_os.join(home, 'patch/build', 'release', name)):
                                    build_home = builtin_os.join(home, 'patch/build', 'release', name)
                                else:
                                    build_home = None

                                if build_home:
                                    for file in glob.iglob(os.path.join(name, '**/*.xml'), recursive = True):
                                        print('  %s' % os.path.normpath(os.path.abspath(file)))

                                        zipname = '%s.zip' % os.path.splitext(file)[0]

                                        try:
                                            tree = etree.parse(file)

                                            if not proxy.write(
                                                builtin_os.join(build_home, 'xml', os.path.basename(file)),
                                                etree.tostring(tree, encoding='utf-8', pretty_print=True, xml_declaration='utf-8')
                                            ):
                                                continue

                                            if os.path.isfile(zipname):
                                                if not proxy.copy_file(
                                                    zipname,
                                                    builtin_os.join(build_home, 'xml', os.path.basename(zipname))
                                                ):
                                                    continue

                                                os.remove(zipname)

                                            os.remove(file)
                                        except Exception as e:
                                            print(e)

                                            status = False
                                            continue

                                        if (dir, name) not in auto_info:
                                            auto_info.append((dir, name))

                                    if len(glob.glob(os.path.join(name, '**/*.xml'), recursive = True)) == 0:
                                        shutil.rmtree(name, ignore_errors = True)
                                else:
                                    shutil.rmtree(name, ignore_errors = True)
                            except Exception as e:
                                print(e)

                                status = False
                                continue

                    if len(glob.glob(os.path.join(dir, '**/*.xml'), recursive = True)) == 0:
                        shutil.rmtree(dir, ignore_errors = True)
                else:
                    shutil.rmtree(dir, ignore_errors = True)

            for dir in glob.iglob('*', recursive = True):
                if len(glob.glob(os.path.join(dir, '**/*.xml'), recursive = True)) == 0:
                    shutil.rmtree(dir, ignore_errors = True)

    if auto_info:
        print('===== 启动补丁制作 =====')

        for dir, name in auto_info:
            dir_paths = dir.split('/')

            if dir_paths[0] in ('bn',):
                jobname = '%s/patch/%s_patch_%s_%s' % (dir_paths[0], dir_paths[0], name, dir_paths[1])
            else:
                jobname = '%s/patch/%s_patch_%s' % (dir_paths[0], dir_paths[0], name)

            cmdline = 'java -jar "%s" -s %s build --username %s --password %s "%s"' % (
                const.JENKINS_CLI, const.JENKINS_URL, const.JENKINS_USERNAME, const.JENKINS_PASSWORD,
                jobname
            )

            display_cmd = 'java -jar "%s" -s %s build --username %s --password %s "%s"' % (
                const.JENKINS_CLI, const.JENKINS_URL, password.password(const.JENKINS_USERNAME), password.password(const.JENKINS_PASSWORD),
                jobname
            )

            cmd = command.command()

            for line in cmd.command(cmdline, display_cmd = display_cmd):
                print(line)

    return status

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
class patch():
    def __init__(self, path):
        self.path = builtin_os.abspath(path)

        m = re.search(r'\/build\/(dev|release)\/', self.path)

        if m:
            self.output = builtin_os.join(m.string[:m.start()], 'patch', m.group(1), m.string[m.end():])
        else:
            self.output = self.path

        self.name = 'none'
        self.type = 'none'
        self.notification = '<PATCH 通知>'
        self.modules = {}

    def init(self, branch):
        os.makedirs(self.path, exist_ok = True)
        os.makedirs(self.output, exist_ok = True)

        with builtin_os.chdir(self.path) as chdir:
            os.makedirs('code', exist_ok = True)
            os.makedirs('build', exist_ok = True)
            os.makedirs('xml', exist_ok = True)

            for file in glob.iglob('build/*/.git', recursive = True):
                shutil.rmtree(file, ignore_errors = True)

        with builtin_os.chdir(self.output) as chdir:
            os.makedirs('installation', exist_ok = True)
            os.makedirs('patch', exist_ok = True)

        status = True

        with builtin_os.chdir(os.path.join(self.path, 'code')) as chdir:
            for module in self.modules:
                if os.path.isdir(module):
                    if not git.pull(module, revert = True):
                        status = False
                else:
                    if not git.clone(self.modules[module], module, branch):
                        status = False

        return status

    def build(self):
        status = True

        message = []

        if os.path.isdir(self.path):
            with builtin_os.chdir(self.path) as chdir:
                for file in glob.iglob('xml/*.xml', recursive = True):
                    if not os.path.isfile(file):
                        continue

                    info_list = self.load_xml(file)

                    if info_list is None:
                        to_addrs, cc_addrs = self.get_addrs_from_file(file)

                        message.append((os.path.basename(file), '解析XML文件失败', False))
                        self.sendmail('%s 解析XML文件失败, 请尽快处理' % self.notification, to_addrs, cc_addrs, None, file)

                        os.remove(file)

                        zipfilename = self.get_xml_zipfile(file)

                        if zipfilename:
                            if os.path.isfile(zipfilename):
                                os.remove(zipfilename)

                        status = False
                        continue

                    if len(info_list) == 0:
                        message.append((os.path.basename(file), '未找到补丁信息', True))

                        os.remove(file)

                        zipfilename = self.get_xml_zipfile(file)

                        if zipfilename:
                            if os.path.isfile(zipfilename):
                                os.remove(zipfilename)

                        continue

                    tempdir = os.path.join(builtin_os.gettempdir(),
                        '%s%04d' % (datetime.datetime.now().strftime('%Y%m%d%H%M%S'), int(random.random() * 1000)))

                    index = -1
                    current = []

                    to_addrs, cc_addrs = self.get_addrs(info_list[0])

                    for info in info_list:
                        index += 1

                        if info.get('os'):
                            if builtin_os.osname() not in info['os']:
                                continue

                        current.append([os.path.basename(file), index, False])

                        if info.get('delete'):
                            if not self.build_delete(info['name'], info['delete']):
                                status = False

                                continue

                        if info.get('source'):
                            if not self.build_source(info['name'], info['source']):
                                status = False

                                continue

                        if info.get('compile'):
                            if not self.build_compile(info['name'], info['compile']):
                                status = False

                                continue

                        if info.get('deploy'):
                            if not self.build_deploy(info['name'], info['deploy'], os.path.join(tempdir, str(index))):
                                status = False

                                continue

                        if info.get('script'):
                            if not self.build_deploy_script(info['script'], info['zip'], os.path.join(tempdir, str(index))):
                                status = False

                                continue

                        current[-1][-1] = True

                    status_all = True

                    for filename, index, _status in current:
                        if not _status:
                            status_all = False

                            break

                    if status_all:
                        for filename, index, _status in current:
                            id = self.get_id()

                            output = os.path.join(self.output, 'patch', id)
                            cur_status = True

                            with builtin_os.chdir(os.path.join(tempdir, str(index)), True) as _chdir:
                                for filename in glob.iglob('**/*', recursive = True):
                                    if os.path.isfile(filename):
                                        try:
                                            dest_file = os.path.join(output, 'patch', filename)
                                            os.makedirs(os.path.dirname(dest_file), exist_ok = True)

                                            shutil.copyfile(filename, dest_file)
                                        except Exception as e:
                                            print(e)

                                            shutil.rmtree(output)

                                            status = False
                                            cur_status = False

                                            break

                            if cur_status:
                                if len(glob.glob(os.path.join(output, '*'), recursive = True)) == 0:
                                    message.append(('%s(%s)' % (filename, index), '补丁制作成功, 但没有输出文件(补丁号: %s)' % id, True))
                                    self.sendmail('%s 补丁制作成功, 但没有输出文件(补丁号: %s)'  % (self.notification, id), to_addrs, cc_addrs, None, file)
                                else:
                                    message.append(('%s(%s)' % (filename, index), '补丁制作成功(补丁号: %s)' % id, True))
                                    self.sendmail('%s 补丁制作成功, 请验证(补丁号: %s)' % (self.notification, id), to_addrs, cc_addrs, None, file)

                                self.to_xml(info_list[index], os.path.join(output, self.get_xml_filename(info_list[index])))
                            else:
                                message.append(('%s(%s)' % (filename, index), '补丁制作成功, 但输出补丁失败', True))
                                self.sendmail('%s 补丁制作成功, 但输出补丁失败' % self.notification, to_addrs, cc_addrs, None, file)
                    else:
                        for filename, index, _status in current:
                            if _status:
                                message.append(('%s(%s)' % (filename, index), '补丁制作成功, 但关联补丁制作失败', True))
                                self.sendmail('%s 补丁制作成功, 但关联补丁制作失败, 请尽快处理' % self.notification, to_addrs, cc_addrs, None, file)
                            else:
                                message.append(('%s(%s)' % (filename, index), '补丁制作失败', False))
                                self.sendmail('%s 补丁制作失败, 请尽快处理' % self.notification, to_addrs, cc_addrs, None, file)

                    os.remove(file)
                    shutil.rmtree(tempdir, ignore_errors = True)

                    zipfilename = self.get_xml_zipfile(file)

                    if zipfilename:
                        if os.path.isfile(zipfilename):
                            os.remove(zipfilename)

        return status

    def installation(self, version, type = None):
        return True

    # ------------------------------------------------------

    # info:
    #   name    : ''
    #   delete  : []
    #   source  : []
    #   info    : {}
    def load_xml(self, file):
        try:
            tree = etree.parse(file)
        except Exception as e:
            print(e)

            return None

        if tree.getroot().get('version', '').strip() != '2.0':
            print('补丁申请单格式错误, 请使用新补丁申请单模板(版本号2.0)')

            return None

        info_list = []

        status = True
        index = -1

        for e in tree.findall('patch'):
            index += 1

            info = {
                'name'      : e.get('name', '').strip(),
                'delete'    : [],
                'source'    : [],
                'info'      : {
                    '提交人员'  : None,
                    '变更版本'  : None,
                    '变更类型'  : None,
                    '变更描述'  : None,
                    '关联故障'  : None,
                    '影响分析'  : None,
                    '依赖变更'  : None,
                    '走查人员'  : None,
                    '走查结果'  : None,
                    '自测结果'  : None,
                    '变更来源'  : None,
                    '开发经理'  : None,
                    '抄送人员'  : None
                }
            }

            if info['name']:
                if info['name'] not in self.modules:
                    print('patch[%s]: patch节点的name属性不是合法的模块名称 - %s' % (index, info['name']))

                    status = False
            else:
                print('patch[%s]: patch节点的name属性不能为空' % index)

                status = False

            for e_delete in e.findall('delete/attr'):
                name = builtin_os.normpath(e_delete.get('name', '').strip())

                if name:
                    if name not in info['delete']:
                        info['delete'].append(name)
                else:
                    print('patch[%s]/delete/attr: delete下attr节点的name属性不能为空' % index)

                    status = False

            for e_source in e.findall('source/attr'):
                name = builtin_os.normpath(e_source.get('name', '').strip())

                if name:
                    if name not in info['source']:
                        info['source'].append(name)
                else:
                    print('patch[%s]/source/attr: source下attr节点的name属性不能为空' % index)

                    status = False

            for e_info in e.findall('info/attr'):
                name = e_info.get('name', '').strip()

                if e_info.text:
                    value = e_info.text.strip()
                else:
                    value = ''

                if name:
                    if name in ('提交人员', '走查人员', '开发经理', '抄送人员'):
                        value = value.replace('\\', '/')

                    info['info'][name] = value
                else:
                    print('patch[%s]/info/attr: info下attr节点的name属性不能为空' % index)

                    status = False

            for x in info['info']:
                if info['info'][x] is None:
                    print('patch[%s]/info: info节点缺少(%s)' % (index, x))

                    status = False
                    continue

                if x in ('变更类型'):
                    if info['info'][x] not in ('需求', '优化', '故障'):
                        print('patch[%s]/info: info节点的(%s)必须是需求, 优化 或 故障' % (index, x))

                        status = False

                    continue

                if x in ('变更描述'):
                    if len(info['info'][x]) < 10:
                        print('patch[%s]/info: info节点的(%s)必须最少10个字符, 当前字符数: %s' % (index, x, len(info['info'][x])))

                        status = False

                    continue

                if x in ('关联故障'):
                    if not re.search(r'^[\d,\s]+$', info['info'][x]):
                        print('patch[%s]/info: info节点的(%s)必须是数字' % (index, x))

                        status = False

                    continue

                if x in ('变更来源'):
                    if not info['info'][x]:
                        print('patch[%s]/info: info节点的(%s)不能为空' % (index, x))

                        status = False

                    continue

                if x in ('走查人员', '抄送人员'):
                    authors = []

                    for author in info['info'][x].split(','):
                        author = author.strip()

                        if author not in authors:
                            authors.append(author)

                    info['info'][x] = authors

                    continue

            if not self.load_xml_extend(info, e):
                status = False
                continue

            info_list.append(info)

        if status:
            return info_list
        else:
            return None

    def load_xml_extend(self, info, e):
        status = True

        info['compile'] = collections.OrderedDict()
        info['deploy'] = collections.OrderedDict()

        dirname = os.path.join(self.path, 'code', self.name)

        if os.path.isdir(dirname):
            with builtin_os.chdir(dirname) as chdir:
                if info.get('source'):
                    for dir in self.get_git_dirs(info['source']):
                        info['compile'][os.path.join(dir, 'build')] = True
                        info['deploy'][':'.join((os.path.join(dir, 'build/output'), ''))] = [self.type]
        else:
            print('no such directory: %s' % os.path.normpath(dirname))

            status = False

        return status

    def to_xml(self, info, file):
        tree = etree.ElementTree(etree.XML("<patches version='2.0'/>"))

        element = etree.Element('patch')
        element.set('name', info['name'])

        tree.getroot().append(element)

        if info.get('delete'):
            delete_element = etree.Element('delete')
            element.append(delete_element)

            for x in info['delete']:
                e = etree.Element('attr')
                e.set('name', x)

                delete_element.append(e)

        if info.get('source'):
            source_element = etree.Element('source')
            element.append(source_element)

            for x in info['source']:
                e = etree.Element('attr')
                e.set('name', x)

                source_element.append(e)

        if info.get('compile'):
            compile_element = etree.Element('compile')
            element.append(compile_element)

            for x in info['compile']:
                e = etree.Element('attr')
                e.set('name', x)
                e.set('clean', str(info['compile'][x]).lower())

                compile_element.append(e)

        if info.get('deploy') or info.get('deploy_delete'):
            deploy_element = etree.Element('deploy')
            element.append(deploy_element)

            if info.get('deploy'):
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

            if info.get('deploy_delete'):
                deploy_delete_element = etree.Element('delete')
                deploy_element.append(deploy_delete_element)

                for x in info['deploy_delete']:
                    e = etree.Element('attr')
                    e.set('name', x)

                    types = info['deploy_delete'][x]

                    if types != [self.type]:
                        e.set('type', ', '.join(types))

                    deploy_delete_element.append(e)

        if info.get('info'):
            info_element = etree.Element('info')
            element.append(info_element)

            for x in info['info']:
                e = etree.Element('attr')
                e.set('name', x)

                if isinstance(info['info'][x], str):
                    e.text = info['info'][x]
                else:
                    e.text = ', '.join(info['info'][x])

                info_element.append(e)

        if not self.to_xml_extend(info, element):
            return False

        os.makedirs(os.path.dirname(file), exist_ok = True)

        try:
            tree.write(file, encoding='utf-8', pretty_print=True, xml_declaration='utf-8')

            return True
        except Exception as e:
            print(e)

            return False

    def to_xml_extend(self, info, e):
        return True

    def build_delete(self, name, deletes):
        if not os.path.isdir(os.path.join('build', name)):
            return False

        with builtin_os.chdir(os.path.join('build', name)) as chdir:
            for file in deletes:
                if os.path.isfile(file):
                    os.remove(file)
                else:
                    shutil.rmtree(file, ignore_errors = True)

        return True

    def build_source(self, name, sources):
        if not os.path.isdir(os.path.join('code', name)):
            return False

        if not self.build_update_source(os.path.join('code', name), sources):
            return False

        with builtin_os.chdir('code') as chdir:
            for file in sources:
                if os.path.isfile(os.path.join(name, file)):
                    dest = os.path.join('../build', name, file)
                    os.makedirs(os.path.dirname(dest), exist_ok = True)

                    try:
                        shutil.copyfile(os.path.join(name, file), dest)
                    except Exception as e:
                        print(e)

                        return False
                elif os.path.isdir(os.path.join(name, file)):
                    for filename in glob.iglob(os.path.join(name, file, '**/*'), recursive = True):
                        if os.path.isfile(filename):
                            dest = os.path.join('../build', filename)
                            os.makedirs(os.path.dirname(dest), exist_ok = True)

                            try:
                                shutil.copyfile(filename, dest)
                            except Exception as e:
                                print(e)

                                return False
                else:
                    return False

        return True

    def build_update_source(self, path, sources):
        if not git.pull(path, revert = True):
            return False

        return True

    def build_compile(self, name, compile_info):
        if not os.path.isdir(os.path.join('build', name)):
            print('no such directory: %s' % os.path.normpath(os.path.join('build', name)))

            return False

        with builtin_os.chdir(os.path.join('build', name)) as chdir:
            for path, clean in compile_info.items():
                if os.path.isdir(path):
                    with builtin_os.chdir(path) as _chdir:
                        mvn = maven.maven()
                        mvn.notification = '%s 编译失败, 请尽快处理' % self.notification

                        if clean:
                            mvn.clean()

                        if re.search(r'code_c\/', path):
                            if not mvn.compile('mvn deploy -fn -U -Djobs=10', 'mvn deploy -fn -U', 'cpp'):
                                return False
                        else:
                            if not mvn.compile('mvn deploy -fn -U', 'mvn deploy -fn -U'):
                                return False
                else:
                    print('no such directory: %s' % os.path.normpath(path))

                    return False

        return True

    def build_deploy(self, name, deploy_info, tmpdir = None):
        if tmpdir:
            tmpdir = os.path.abspath(tmpdir)
        else:
            tmpdir = os.getcwd()

        if not os.path.isdir(os.path.join('build', name)):
            return False

        with builtin_os.chdir(os.path.join('build', name)) as chdir:
            for src_and_dest, types in deploy_info.items():
                src, dest = src_and_dest.split(':', 1)

                if os.path.isfile(src):
                    filename = self.expand_filename(src)

                    if filename:
                        for type in types:
                            if not self.build_deploy_file(filename, os.path.join(tmpdir, type, dest)):
                                return False
                elif os.path.isdir(src):
                    with builtin_os.chdir(src) as _chdir:
                        for filename in glob.iglob('**/*', recursive = True):
                            if os.path.isfile(filename):
                                filename = self.expand_filename(filename)

                                if filename:
                                    for type in types:
                                        if not self.build_deploy_file(filename, os.path.join(tmpdir, type, dest, filename)):
                                            return False
                else:
                    return False

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

    def build_deploy_script(self, types, zipfilename, tmpdir = None):
        return True

    def sendmail(self, notification, to_addrs, cc_addrs = None, lines = None, file = None):
        if lines is None:
            lines = []

        if os.environ.get('BUILD_URL'):
            console_url = builtin_os.join(os.environ['BUILD_URL'], 'console')

            lines.append('')
            lines.append('详细信息: <a href="%s">%s</a>' % (console_url, console_url))
            lines.append('')

        smtp.sendmail(notification, to_addrs, cc_addrs, '<br>\n'.join(lines))

    def get_git_dirs(self, paths):
        dirs = []

        for path in paths:
            dir = self.get_git_home(path)

            if dir:
                if not dir in dirs:
                    dirs.append(dir)

        return dirs

    def get_git_home(self, path):
        if os.path.abspath(path) == os.getcwd() or path == '/':
            return None

        if os.path.isfile(path):
            path = os.path.dirname(path)

        if os.path.isdir(os.path.join(path, '.git')):
            return path

        return self.get_git_home(os.path.dirname(path))

    def get_addrs(self, info):
        to_addrs = '%s@zte.com.cn' % info['info']['提交人员'].replace('\\', '/').split('/', 1)[-1]

        cc_addrs = ['%s@zte.com.cn' % x.replace('\\', '/').split('/', 1)[-1] for x in info['info']['走查人员'] + info['info']['抄送人员']]
        cc_addrs.append('%s@zte.com.cn' % info['info']['开发经理'].replace('\\', '/').split('/', 1)[-1])

        return (to_addrs, cc_addrs)

    def get_addrs_from_file(self, file):
        to_addrs = None
        cc_addrs = []

        for encoding in ('utf-8', 'cp936'):
            try:
                with open(file, encoding = encoding) as f:
                    for line in f.readlines():
                        line = line.strip()

                    m = re.search(r'^<\s*attr\s+name\s*=.*提交人员.*>(.*)<\s*/\s*attr\s*>$', line)

                    if m:
                        to_addrs = '%s@zte.com.cn' % m.group(1).replace('\\', '/').split('/', 1)[-1]

                        continue

                    m = re.search(r'^<\s*attr\s+name\s*=.*走查人员.*>(.*)<\s*/\s*attr\s*>$', line)

                    if m:
                        cc_addrs += ['%s@zte.com.cn' % x.strip().replace('\\', '/').split('/', 1)[-1] for x in m.group(1).split(',')]

                        continue

                    m = re.search(r'^<\s*attr\s+name\s*=.*开发经理.*>(.*)<\s*/\s*attr\s*>$', line)

                    if m:
                        cc_addrs.append('%s@zte.com.cn' % m.group(1).replace('\\', '/').split('/', 1)[-1])

                        continue

                    break
            except:
                pass

        return (to_addrs, cc_addrs)

    def expand_filename(self, file):
        pathname, extname = os.path.splitext(file)

        if builtin_os.osname() in ('windows', 'windows-x64'):
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

    def get_id(self):
        prefix = datetime.datetime.now().strftime('%Y%m%d')
        id = 0

        if os.path.isdir(os.path.join(self.output, 'patch')):
            with builtin_os.chdir(os.path.join(self.output, 'patch')) as chdir:
                for x in glob.iglob('%s_*' % prefix):
                    m = re.search(r'^\d{8}_(\d{4})$', x)

                    if m:
                        if id < int(m.group(1)):
                            id = int(m.group(1))

        return '%s_%04d' % (prefix, id + 1)

    def get_xml_filename(self, info):
        name, employee_id = info['info']['提交人员'].replace('\\', '/').split('/', 1)

        return '%s_%s_%s.xml' % (datetime.datetime.now().strftime('%Y%m%d'), employee_id, name)

    def get_xml_zipfile(self, file):
        return None

class stn_patch(patch):
    def __init__(self, path):
        super().__init__(path)

        self.name = 'stn'
        self.type = 'stn'
        self.notification = '<STN_PATCH 通知>'
        self.modules = {
            'stn' : app_build.stn_build().repos
        }

class umebn_patch(patch):
    def __init__(self, path):
        super().__init__(path)

        self.name = 'umebn'
        self.type = 'umebn'
        self.notification = '<UMEBN_PATCH 通知>'
        self.modules = {
            'umebn' : app_build.umebn_build().repos
        }

    # ------------------------------------------------------

    def build_update_source(self, path, sources):
        status = True

        with builtin_os.chdir(path) as chdir:
            for dir in self.get_git_dirs(sources):
                if not git.pull(dir, revert = True):
                    status = False

        return status

class sdno_patch(umebn_patch):
    def __init__(self, path):
        super().__init__(path)

        self.name = 'sdno'
        self.type = 'sdno'
        self.notification = '<SDNO_PATCH 通知>'
        self.modules = {
            'sdno' : app_build.sdno_build().repos
        }

class bn_patch(patch):
    def __init__(self, path):
        super().__init__(path)

        self.name = 'bn'
        self.type = 'ems'
        self.notification = '<BN_PATCH 通知>'

        for name, url in app_build.bn_build().repos.items():
            self.modules[os.path.basename(url)] = url

    # ------------------------------------------------------

    # info:
    #   name            : ''
    #   delete          : []
    #   source          : []
    #   compile         : {}
    #   deploy          : {}
    #   deploy_delete   : {}
    #   info            : {}
    def load_xml_extend(self, info, e):
        status = True

        info['compile'] = collections.OrderedDict()
        info['deploy'] = collections.OrderedDict()
        info['deploy_delete'] = collections.OrderedDict()

        osname = e.get('os', '').strip()

        if osname:
            info['os'] = tuple(x.strip() for x in osname.split(','))

            if not set(info['os']) - set(('windows', 'linux', 'solaris')):
                print('patch[%s]: patch节点的os属性值错误, 只能包含windows, linux, solaris' % index)

                status = False

        script = e.get('script', '').strip()

        if script:
            zipfilename = self.get_xml_zipfile(file)

            if zipfilename:
                info['script'] = self.types(script)
                info['zip'] = zipfilename

                if not os.path.isfile(info['zip']):
                    print('patch[%s]: 找不到增量脚本对应的zip文件 - %s' % (index, info['zip']))

                    status = False

        for e_compile in e.findall('compile/attr'):
                name = builtin_os.normpath(e_compile.get('name', '').strip())
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

        for e_deploy in e.findall('deploy/deploy/attr'):
            name = builtin_os.normpath(e_deploy.get('name', '').strip())
            dest = e_deploy.text
            type = e_deploy.get('type', '').strip()

            if dest is not None:
                dest = builtin_os.normpath(dest.strip())

            types = self.types(type)

            if name:
                m = re.search(r'^(code|code_c|sdn)\/build\/output\/', name)

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
                    print('patch[%s]/deploy/deploy/attr: 源文件必须以code/build/output, code_c/build/output, sdn/build/output或installdisk开始' % index)

                    status = False
            else:
                print('patch[%s]/deploy/deploy/attr: deploy/deploy下attr节点的name属性不能为空' % index)

                status = False

        for e_deploy_delete in e.findall('deploy/delete/attr'):
            name = builtin_os.normpath(e_deploy_delete.get('name', '').strip())
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

    def to_xml_extend(self, info, e):
        if info.get('os'):
            e.set('os', ', '.join(info['os']))

        if info.get('script'):
            e.set('script', ', '.join(info['script']))

        return True

    def build_compile(self, name, compile_info):
        if os.path.isdir('build'):
            with builtin_os.chdir('build') as chdir:
                bn.environ('cpp')

        return super().build_compile(name, compile_info)

    def build_deploy_script(self, types, zipfilename, tmpdir = None):
        if zipfilename:
            zipfilename = os.path.abspath(zipfilename)

            if not os.path.isfile(zipfilename):
                print('找不到增量补丁包对应的zip文件: %s' % os.path.normpath(zipfilename))

                return False

            if tmpdir:
                tmpdir = os.path.abspath(tmpdir)
            else:
                tmpdir = os.getcwd()

            with builtin_os.tmpdir(os.path.join(tmpdir, '../zip', os.path.basename(tmpdir))) as _tmpdir:
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

                with builtin_os.chdir(install) as chdir:
                    for file in glob.iglob('dbscript-patch/**/*', recursive = True):
                        if os.path.isfile(file):
                            for type in types:
                                try:
                                    shutil.copyfile(file, os.path.join(tmpdir, type, prefix, file))
                                except Exception as e:
                                    print(e)

                                    return False

        return True

    def get_xml_zipfile(self, file):
        return '%s.zip' % file[0:-4]

    def types(self, type):
        types = []

        if not type:
            type = self.type

        for x in type.split(','):
            x = x.strip()

            if x in ('ems', 'nms', 'lct', 'update', 'upgrade', 'service'):
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

class installation():
    def __init__(self, path):
        self.path = builtin_os.abspath(path)

        m = re.search(r'\/build\/(dev|release)\/', self.path)

        if m:
            self.output = builtin_os.join(m.string[:m.start()], 'patch', m.group(1), m.string[m.end():])
        else:
            self.output = self.path

        self.type = 'none'

    def install(self, version, type = None):
        if not os.path.isdir(self.output):
            print('no such directory: %s' % os.path.normpath(self.output))

            return False

        if type is None:
            type = self.type

        with builtin_os.chdir(self.output) as chdir:
            id_info = {}

            for dir in glob.iglob('patch/*', recursive = True):
                id = os.path.basename(dir)

                if not re.search(r'^\d{8}_\d{4}$', id):
                    continue

                path = os.path.join(dir, 'patch', type)

                if not os.path.isdir(path):
                    for _dir in glob.iglob(os.path.join(dir, 'patch/*', type), recursive = True):
                        path = _dir

                if os.path.isdir(path):
                    id_info[id] = os.path.abspath(path)

            info = {}

            for id in sorted(id_info.keys()):
                with builtin_os.chdir(id_info[id]) as _chdir:
                    for file in glob.iglob('**/*', recursive = True):
                        if os.path.isfile(file):
                            info[file] = os.path.abspath(file)

            with builtin_os.tmpdir(tempfile.mkdtemp(dir=os.getcwd()), False) as _tmpdir:
                for file in info:
                    if os.path.splitext(file)[1] in ['.pdb', '.exp', '.lib', '.debuginfo']:
                        continue

                    os.makedirs(os.path.dirname(file), exist_ok = True)

                    try:
                        shutil.copyfile(info[file], file)
                    except Exception as e:
                        print(e)

                        return False

                if not self.install_extend(version, type):
                    return False

        return True

    # ------------------------------------------------------

    def install_extend(self, version, type = None):
        return True

class stn_installation(installation):
    def __init__(self, path):
        super().__init__(path)

        self.type = 'stn'

class umebn_installation(installation):
    def __init__(self, path):
        super().__init__(path)

        self.type = 'umebn'

class sdno_installation(installation):
    def __init__(self, path):
        super().__init__(path)

        self.type = 'sdno'

class bn_installation(installation):
    def __init__(self, path):
        super().__init__(path)

        self.type = 'ems'

    # ------------------------------------------------------

    def install_extend(self, version, type = None):
        return True

    def ums_db_update_info(self, paths, filename = 'install/dbscript-patch/ums-db-update-info.xml'):
        dbs = {}

        for path in paths:
            file = os.path.join(path, filename)

            if os.path.isfile(file):
                try:
                    tree = etree.parse(file)
                except Exception as e:
                    print(e)

                    return None

                for e in tree.findall('/install-db/data-source'):
                    data_source = e.get('key', '').strip()

                    if data_source not in dbs:
                        dbs[data_source] = {}

                    for element in e.findall('//item'):
                        filename = element.get('filename', '').strip().replace('\\', '/')
                        rollback = element.get('rollback', '').strip().replace('\\', '/')

                        if not filename or not rollback:
                            print('%s: filename or rollback is empty' % file)

                            return None

                        dbname = filename.split('/')[1]

                        if dbname not in dbs[data_source]:
                            dbs[data_source][dbname] = {}

                        dbs[data_source][dbname][filename] = element.attrib

        lines = []
        lines.append('<install-db>')

        for data_source in dbs:
            lines.append('  <data-source key="%s">' % data_source)

            for lang in ('zh', 'en'):
                lines.append('      <%s>' % lang)

                for dbname in dbs[data_source]:
                    lines.append('          <%s>' % dbname)
                    lines.append('              <normal>')

                    for filename in sorted(dbs[data_source][dbname].keys()):
                        attrs = ['k="%s"' % v for k, v in dbs[data_source][dbname][filename].items()]
                        lines.append('                  <item %s/>' % ' '.join(sorted(attrs)))

                    lines.append('          </%s>' % dbname)
                    lines.append('              </normal>')

                lines.append('      </%s>' % lang)

            lines.append('  </data-source>')

        lines.append('</install-db>')

        return '\n'.join(lines)
