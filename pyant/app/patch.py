import collections
import glob
import os.path
import re
import xml.etree.ElementTree

from pyant import git, smtp
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
    def __init__(self, path, modules):
        self.path = builtin_os.abspath(path)
        self.modules = modules

        m = re.search(r'\/build\/(dev|release)\/', self.path)

        if m:
            self.output = builtin_os.join(m.string[:m.start()], 'patch', m.group(1), m.string[m.end():])
        else:
            self.output = self.path

        self.notification = '<PATCH 通知>补丁编译失败, 请尽快处理'

    def build(self):
        status = True

        if os.path.isdir(self.path):
            with builtin_os.chdir(self.path) as chdir:
                for file in glob.iglob('xml/**/*.xml', recursive = True):
                    info_list = self.load_xml(file)

        return status

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

                    if name:
                        m = re.search(r'^(code|code_c|sdn)\/build\/output\/', name)

                        if m:
                            dest = m.string[m.end():]
                            type = str(e_deploy.get('type')).strip()

                            if not type:
                                type = self.default_type

                            m = re.search(r'^ums-(\w+)', dest)

                            if m:
                                if m.group(0) in ('nms', 'lct'):
                                    type = m.group(0)

                                    dest = dest.repace(m.string[m.start():m.end()], 'ums-client')

                            types = []

                            for x in type.split(','):
                                x = x.strip()

                                if x in self.types:
                                    if x not in types:
                                        types.append(x)
                                else:
                                    print('patch[%s]/deploy/deploy/attr: type值非法 - %s' % (index, type))

                                    status = False

                            if 'service' in types:
                                if 'ems' not in types:
                                    types.append('ems')

                            map['deploy'][name] = types
                        elif re.search(r'^installdisk\/', name):
                            dest = builtin_os.normpath(str(e_deploy.text).strip())

                            if dest:
                                type = str(e_deploy.get('type')).strip()

                                if not type:
                                    type = self.default_type

                                types = []

                                for x in type.split(','):
                                    x = x.strip()

                                    if x in self.types:
                                        if x not in types:
                                            types.append(x)
                                    else:
                                        print('patch[%s]/deploy/deploy/attr: type值非法 - %s' % (index, type))

                                        status = False

                                if 'service' in types:
                                    if 'ems' not in types:
                                        types.append('ems')

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
                    pass

            return info_list
        except Exception as e:
            print(e)

            return None

    def to_xml(self, info, file):
        pass

    def sendmail(self, notification = None):
        smtp.sendmail(self.notification, email, None, '<br>\n'.join(lines), attaches)
