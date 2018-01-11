import collections
import glob
import os
import os.path
import re
import shutil
import xml.etree.ElementTree
import xml.dom.minidom

from pyant import git, maven, smtp
from pyant.app import bn, stn
from pyant.builtin import os as builtin_os

__all__ = ('build', 'build_init', 'build_install')

def build(name, path):
    if name == 'bn':
        return bnpatch(path).build()
    elif name == 'stn':
        return stnpatch(path).build()
    else:
        return True

def build_init(name, path, branch):
    if name == 'bn':
        return bnpatch(path).init(branch)
    elif name == 'stn':
        return stnpatch(path).init(branch)
    else:
        return True

def build_install(name, path, version):
    if name == 'bn':
        return bnpatch(path).installation(version)
    elif name == 'stn':
        return stnpatch(path).installation(version)
    else:
        return True

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
                for file in glob.iglob('xml/**/*.xml', recursive = True):
                    info_list = self.load_xml(file)

                    if info_list is None:
                        to_addrs, cc_addrs = self.get_addrs_from_file(file)

                        message.append((os.path.basename(file), '解析XML文件失败', False))
                        self.sendmail('<PATCH 通知>解析XML文件失败, 请尽快处理', to_addrs, cc_addrs, None, file)

                        shutil.rmtree(file, ignore_errors = True)

                        status = False
                        continue

                    shutil.rmtree(file, ignore_errors = True)

                    if info_list.empty():
                        message.append((os.path.basename(file), '未找到补丁信息', True))

                        continue

                    for info in info_list:
                        if info['os']:
                            if builtin_os.osname() not in info['os']:
                                continue

                        if not self.build_delete(info['name'], info['delete']):
                            status = False
                            continue

                        if not self.build_source(info['name'], info['source']):
                            status = False
                            continue

                        if not self.build_compile(info['name'], info['compile']):
                            status = False
                            continue

                        if not self.build_deploy(info['name'], info['deploy']):
                            status = False
                            continue

        return status

    def installation(self, version):
        pass

    # ------------------------------------------------------

    def load_xml(self, file):
        try:
            tree = xml.etree.ElementTree.parse(file)
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

            map = {
                'name'          : e.get('name', '').strip(),
                'os'            : None,
                'script'        : None,
                'zip'           : None,
                'delete'        : [],
                'source'        : [],
                'compile'       : collections.OrderedDict(),
                'deploy'        : collections.OrderedDict(),
                'deploy_delete' : collections.OrderedDict(),
                'info'          : {
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

            if map['name']:
                if map['name'] not in self.modules:
                    print('patch[%s]: patch节点的name属性不是合法的模块名称 - %s' % (index, map['name']))

                    status = False
            else:
                print('patch[%s]: patch节点的name属性不能为空' % index)

                status = False

            osname = e.get('os', '').strip()

            if osname:
                map['os'] = tuple(x.strip() for x in osname.split(','))

                if not set(map['os']) - set(('windows', 'linux', 'solaris')):
                    print('patch[%s]: patch节点的os属性值错误, 只能包含windows, linux, solaris' % index)

                    status = False

            script = e.get('script', '').strip()

            if script:
                map['script'] = tuple(x.strip() for x in script.split(','))
                map['zip'] = '%s.zip' % file[0:-4]

                if not os.path.isfile(map['zip']):
                    print('patch[%s]: 找不到增量脚本对应的zip文件 - %s' % (index, map['zip']))

                    status = False

            for e_delete in e.findall('delete/attr'):
                name = builtin_os.normpath(e_delete.get('name', '').strip())

                if name:
                    if name not in map['delete']:
                        map['delete'].append(name)
                else:
                    print('patch[%s]/delete/attr: delete下attr节点的name属性不能为空' % index)

                    status = False

            for e_source in e.findall('source/attr'):
                name = builtin_os.normpath(e_source.get('name', '').strip())

                if name:
                    if name not in map['source']:
                        map['source'].append(name)
                else:
                    print('patch[%s]/source/attr: source下attr节点的name属性不能为空' % index)

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

                    map['compile'][name] = clean
                else:
                    print('patch[%s]/compile/attr: compile下attr节点的name属性不能为空' % index)

                    status = False

            for e_deploy in e.findall('deploy/deploy/attr'):
                name = builtin_os.normpath(e_deploy.get('name', '').strip())
                type = e_deploy.get('type', '').strip()

                types = self.types(type)

                if types is None:
                    print('patch[%s]/deploy/deploy/attr: type值非法 - %s' % (index, type))

                    status = False

                if name:
                    m = re.search(r'^(code|code_c|sdn)\/build\/output\/', name)

                    if m:
                        dest = m.string[m.end():]

                        m = re.search(r'^ums-(\w+)', dest)

                        if m:
                            if m.group(1) in ('nms', 'lct'):
                                types = [m.group(1)]

                                dest = dest.replace(m.string[m.start():m.end()], 'ums-client')

                        map['deploy'][':'.join((name, dest))] = types
                    elif re.search(r'^installdisk\/', name):
                        dest = e_deploy.text

                        if dest is not None:
                            dest = dest.strip()

                        if dest:
                            dest = builtin_os.normpath(dest)

                            map['deploy'][':'.join((name, dest))] = types
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

                if types is None:
                    print('patch[%s]/deploy/delete/attr: type值非法 - %s' % (index, type))

                    status = False

                if name:
                    m = re.search(r'^ums-(\w+)', name)

                    if m:
                        if not m.group(1) in ('client', 'server'):
                            print('patch[%s]/deploy/delete/attr: deploy/delete下attr节点的name属性错误, 根目录应该为ums-client或ums-server' % index)

                            status = False

                    map['deploy_delete'][name] = types
                else:
                    print('patch[%s]/deploy/delete/attr: deploy/delete下attr节点的name属性不能为空' % index)

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

                    map['info'][name] = value
                else:
                    print('patch[%s]/info/attr: info下attr节点的name属性不能为空' % index)

                    status = False

            for x in map['info']:
                if map['info'][x] is None:
                    print('patch[%s]/info: info节点缺少(%s)' % (index, x))

                    status = False
                    continue

                if x in ('变更类型'):
                    if map['info'][x] not in ('需求', '优化', '故障'):
                        print('patch[%s]/info: info节点的(%s)必须是需求, 优化 或 故障' % (index, x))

                        status = False

                    continue

                if x in ('变更描述'):
                    if len(map['info'][x]) < 10:
                        print('patch[%s]/info: info节点的(%s)必须最少10个字符, 当前字符数: %s' % (index, x, len(map['info'][x])))

                        status = False

                    continue

                if x in ('关联故障'):
                    if not re.search(r'^[\d,\s]+$', map['info'][x]):
                        print('patch[%s]/info: info节点的(%s)必须是数字' % (index, x))

                        status = False

                    continue

                if x in ('变更来源'):
                    if not map['info'][x]:
                        print('patch[%s]/info: info节点的(%s)不能为空' % (index, x))

                        status = False

                    continue

                if x in ('走查人员', '抄送人员'):
                    authors = []

                    for author in map['info'][x].split(','):
                        author = author.strip()

                        if author not in authors:
                            authors.append(author)

                    map['info'][x] = authors

                    continue

            info_list.append(map)

        if status:
            return info_list
        else:
            return None

    def to_xml(self, info, file):
        tree = xml.etree.ElementTree.ElementTree(xml.etree.ElementTree.fromstring("<patches version='2.0'/>"))

        element = xml.etree.ElementTree.Element('patch')
        element.set('name', info['name'])

        if info['os']:
            element.set('os', ', '.join(info['os']))

        if info['script']:
            element.set('script', ', '.join(info['script']))

        tree.getroot().append(element)

        if info['delete']:
            delete_element = xml.etree.ElementTree.Element('delete')
            element.append(delete_element)

            for x in info['delete']:
                e = xml.etree.ElementTree.Element('attr')
                e.set('name', x)

                delete_element.append(e)

        if info['source']:
            source_element = xml.etree.ElementTree.Element('source')
            element.append(source_element)

            for x in info['source']:
                e = xml.etree.ElementTree.Element('attr')
                e.set('name', x)

                source_element.append(e)

        if info['compile']:
            compile_element = xml.etree.ElementTree.Element('compile')
            element.append(compile_element)

            for x in info['compile']:
                e = xml.etree.ElementTree.Element('attr')
                e.set('name', x)
                e.set('clean', str(info['compile'][x]).lower())

                compile_element.append(e)

        if info['deploy'] or info['deploy_delete']:
            deploy_element = xml.etree.ElementTree.Element('deploy')
            element.append(deploy_element)

            if info['deploy']:
                deploy_deploy_element = xml.etree.ElementTree.Element('deploy')
                deploy_element.append(deploy_deploy_element)

                for x in info['deploy']:
                    name, *dest = x.split(':', 1)

                    e = xml.etree.ElementTree.Element('attr')
                    e.set('name', name)

                    if info['deploy'][x]:
                        e.set('type', ', '.join(info['deploy'][x]))

                    if not re.search(r'^(code|code_c|sdn)\/build\/output\/', name):
                        e.text = ''.join(dest)

                    deploy_deploy_element.append(e)

            if info['deploy_delete']:
                deploy_delete_element = xml.etree.ElementTree.Element('delete')
                deploy_element.append(deploy_delete_element)

                for x in info['deploy_delete']:
                    e = xml.etree.ElementTree.Element('attr')
                    e.set('name', x)

                    if info['deploy_delete'][x]:
                        e.set('type', ', '.join(info['deploy_delete'][x]))

                    deploy_delete_element.append(e)

        if info['info']:
            info_element = xml.etree.ElementTree.Element('info')
            element.append(info_element)

            for x in info['info']:
                e = xml.etree.ElementTree.Element('attr')
                e.set('name', x)

                if isinstance(info['info'][x], str):
                    e.text = info['info'][x]
                else:
                    e.text = ', '.join(info['info'][x])

                info_element.append(e)

        os.makedirs(os.path.dirname(file), exist_ok = True)

        try:
            with open(file, 'w', encoding = 'utf-8') as f:
                f.write(xml.dom.minidom.parseString(xml.etree.ElementTree.tostring(tree.getroot())).toprettyxml(indent = '  '))

            return True
        except Exception as e:
            print(e)

            return False

    def get_addrs(self, info):
        to_addrs = '%s@zte.com.cn' % info['提交人员'].replace('\\', '/').split('/')[-1]
        cc_addrs = ['%s@zte.com.cn' % x.replace('\\', '/').split('/')[-1] for x in info['走查人员'] + info['抄送人员']]

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
                        to_addrs = '%s@zte.com.cn' % m.group(1).replace('\\', '/').split('/')[-1]

                        continue

                    m = re.search(r'^<\s*attr\s+name\s*=.*走查人员.*>(.*)<\s*/\s*attr\s*>$', line)

                    if m:
                        cc_addrs = ['%s@zte.com.cn' % x.strip().replace('\\', '/').split('/')[-1] for x in m.group(1).split(',')]

                        continue

                    break
            except:
                pass

        return (to_addrs, cc_addrs)

    def sendmail(self, notification, to_addrs, cc_addrs = None, lines = None, file = None):
        if os.environ.get('BUILD_URL'):
            lines = []

            console_url = builtin_os.join(os.environ['BUILD_URL'], 'console')

            lines.append('')
            lines.append('详细信息: <a href="%s">%s</a>' % (console_url, console_url))
            lines.append('')

        smtp.sendmail(notification, to_addrs, cc_addrs, '<br>\n'.join(lines))

    def types(self, type):
        return []

    def build_delete(self, name, deletes):
        if not os.path.isdir(os.path.join('build', name)):
            return False

        with builtin_os.chdir(os.path.join('build', name)) as chdir:
            for file in deletes:
                shutil.rmtree(file, ignore_errors = True)

        return True

    def build_source(self, name, sources):
        if not os.path.isdir(os.path.join('code', name)):
            return False

        if not git.pull(os.path.join('code', name), revert = True):
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
                    for filename in glob.iglob(os.path.join(name, file, '**/*', recursive = True)):
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

    def build_compile(self, name, compile_info):
        if not os.path.isdir(os.path.join('build', name)):
            return False

        with builtin_os.chdir(os.path.join('build', name)) as chdir:
            for path, clean in compile_info.items():
                if not os.path.isdir(path):
                    return False

                mvn = maven.maven()
                mvn.notification = '<PATCH 通知>编译失败, 请尽快处理'

                if clean:
                    mvn.clean()

                if re.search(r'code_c\/', path):
                    if not mvn.compile('mvn deploy -fn -U -Djobs=10', 'mvn deploy -fn -U', 'cpp'):
                        return False
                else:
                    if not mvn.compile('mvn deploy -fn -U', 'mvn deploy -fn -U'):
                        return False

        return True

    def build_deploy(self, name, deploy_info):
        if not os.path.isdir(os.path.join('build', name)):
            return False

        return True

class bnpatch(patch):
    def __init__(self, path):
        super().__init__(path)

        for name, url in bn.REPOS.items():
            self.modules[os.path.basename(url)] = url

    def types(self, type):
        types = []

        if not type:
            type = 'ems'

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

    def build_compile(self, name, compile_info):
        if os.path.isdir('build'):
            with builtin_os.chdir('build') as chdir:
                bn.environ('cpp')

        return super().build_compile(name, compile_info)

class stnpatch(patch):
    def __init__(self, path):
        super().__init__(path)

        for name, url in stn.REPOS.items():
            self.modules[os.path.basename(url)] = url
