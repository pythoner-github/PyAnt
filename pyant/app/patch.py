import collections
import glob
import os
import os.path
import re
import shutil
import xml.etree.ElementTree

from pyant import git, smtp
from pyant.app import bn, stn
from pyant.builtin import os as builtin_os

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

        if os.path.isdir(self.path):
            with builtin_os.chdir(self.path) as chdir:
                for file in glob.iglob('xml/**/*.xml', recursive = True):
                    info_list = self.load_xml(file)

        return status

    def installation(self):
        pass

    # ------------------------------------------------------

    def load_xml(self, file):
        try:
            tree = xml.etree.ElementTree.parse(file)

            if str(tree.getroot().get('version')).strip() != '2.0':
                print('补丁申请单格式错误, 请使用新补丁申请单模板(版本号2.0)')

                return None

            info_list = []

            status = True
            index = -1

            for e in tree.findall('patch'):
                index += 1

                map = {
                    'name'          : str(e.get('name')).strip(),
                    'os'            : None,
                    'script'        : None,
                    'zip'           : '%.zip' % file[0:-4],
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

                osname = str(e.get('os')).strip()

                if not osname:
                    map['os'] = tuple(x.strip() for x in osname.split(','))

                    if not set(map['os']) - set(('windows', 'linux', 'solaris')):
                        print('patch[%s]: patch节点的os属性值错误, 只能包含windows, linux, solaris' % index)

                        status = False

                script = str(e.get('script')).strip()

                if not script:
                    map['script'] = tuple(x.strip() for x in script.split(','))

                    if not os.path.isfile(map['zip']):
                        print('patch[%s]: 找不到增量脚本对应的zip文件 - %s' % (index, map['zip']))

                        status = False

                for e_delete in e.findall('delete/attr'):
                    name = builtin_os.normpath(str(e_delete.get('name')).strip())

                    if name:
                        if name not in map['delete']:
                            map['delete'].append(name)
                    else:
                        print('patch[%s]/delete/attr: delete下attr节点的name属性不能为空' % index)

                        status = False

                for e_source in e.findall('source/attr'):
                    name = builtin_os.normpath(str(e_source.get('name')).strip())

                    if name:
                        if name not in map['source']:
                            map['source'].append(name)
                    else:
                        print('patch[%s]/source/attr: source下attr节点的name属性不能为空' % index)

                        status = False

                for e_compile in e.findall('compile/attr'):
                    name = builtin_os.normpath(str(e_compile.get('name')).strip())
                    clean = str(e_compile.get('clean')).strip().lower()

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
                    name = builtin_os.normpath(str(e_deploy.get('name')).strip())
                    type = str(e_deploy.get('type')).strip()

                    types = self.types(type)

                    if not types:
                        print('patch[%s]/deploy/deploy/attr: type值非法 - %s' % (index, type))

                        status = False

                    if name:
                        m = re.search(r'^(code|code_c|sdn)\/build\/output\/', name)

                        if m:
                            dest = m.string[m.end():]

                            m = re.search(r'^ums-(\w+)', dest)

                            if m:
                                if m.group(0) in ('nms', 'lct'):
                                    types = [m.group(0)]

                                    dest = dest.repace(m.string[m.start():m.end()], 'ums-client')

                            map['deploy'][':'.join(name, dest)] = types
                        elif re.search(r'^installdisk\/', name):
                            dest = builtin_os.normpath(str(e_deploy.text).strip())

                            if dest:
                                map['deploy'][':'.join(name, dest)] = types
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
                    name = builtin_os.normpath(str(e_deploy_delete.get('name')).strip())
                    type = str(e_deploy_delete.get('type')).strip()

                    types = self.types(type)

                    if not types:
                        print('patch[%s]/deploy/delete/attr: type值非法 - %s' % (index, type))

                        status = False

                    if name:
                        m = re.search(r'^ums-(\w+)', name)

                        if m:
                            if not m.group(0) in ('client', 'server'):
                                print('patch[%s]/deploy/delete/attr: deploy/delete下attr节点的name属性错误, 根目录应该为ums-client或ums-server' % index)

                                status = False

                        map['deploy_delete'][name] = types
                    else:
                        print('patch[%s]/deploy/delete/attr: deploy/delete下attr节点的name属性不能为空' % index)

                        status = False

                for e_info in e.findall('info/attr'):
                    name = str(e_info.get('name')).strip()
                    value = str(e_info.text).strip()

                    if name:
                        if name in ('提交人员', '走查人员', '开发经理', '抄送人员'):
                            value = value.replace('\\', '/')

                        map['info'][name] = value
                    else:
                        print('patch[%s]/info/attr: info下attr节点的name属性不能为空' % index)

                        status = False

                for x in ('提交人员', '变更版本', '变更类型', '变更描述', '关联故障', '影响分析', '依赖变更', '自测结果', '变更来源', '开发经理', '抄送人员'):
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
        except Exception as e:
            print(e)

            return None

    def to_xml(self, info, file):
        pass

    def sendmail(self, notification):
        smtp.sendmail(notification, email, None, '<br>\n'.join(lines))

    def types(self, type):
        return []

class bnpatch(patch):
    def __init__(self, path):
        super.__init__(path)

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

class stnpatch(patch):
    def __init__(self, path):
        super.__init__(path)

        for name, url in stn.REPOS.items():
            self.modules[os.path.basename(url)] = url
