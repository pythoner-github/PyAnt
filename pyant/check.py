import collections
import glob
import os.path
import re

from lxml import etree

from pyant import git, smtp
from pyant.builtin import os as builtin_os

__all__ = ('check')

class check:
    def __init__(self, xpath = None):
        self.errors = None

        if xpath:
            self.xpath = xpath
        else:
            self.xpath = ''

        self.notification = '<CHECK 通知>文件检查失败, 请尽快处理'

    def check(self, ignores = None):
        self.errors = None

        self.encoding()
        self.xml(ignores)

        if self.errors:
            for type, file_info in self.errors.items():
                for file in file_info:
                    info = git.info(file)

                    if info:
                        file_info[file] = (
                            info['author'], info['email'], info['date'], info['url']
                        )
                    else:
                        file_info[file] = (
                            None, None, None, None
                        )

            self.puts_errors()
            self.sendmail()

            return False
        else:
            return True

    # ----------------------------------------------------------

    def encoding(self):
        for file in glob.iglob(os.path.join(self.xpath, '**/*.java'), recursive = True):
            found = False

            file = builtin_os.normpath(file)

            for name in ('target/', 'output/'):
                if name in file:
                    found = True

                    break

            if found:
                continue

            try:
                with open(file, encoding = 'utf8') as f:
                    for line in f.readlines():
                        pass
            except:
                if not self.errors:
                    self.errors = collections.OrderedDict()

                if 'encoding' not in self.errors:
                    self.errors['encoding'] = collections.OrderedDict()

                self.errors['encoding'][file] = None

    def xml(self, ignores = None):
        if ignores:
            if isinstance(ignores, str):
                ignores = (ignores,)

        for file in glob.iglob(os.path.join(self.xpath, '**/*.xml'), recursive = True):
            found = False

            file = builtin_os.normpath(file)

            for name in ('target/', 'output/'):
                if name in file:
                    found = True

                    break

            if found:
                continue

            if ignores:
                found = False

                for ignore in ignores:
                    if re.search(ignore, file):
                        found = True

                        break

                if found:
                    continue

            try:
                tree = etree.parse(file)
            except Exception as e:
                if not self.errors:
                    self.errors = collections.OrderedDict()

                if 'xml' not in self.errors:
                    self.errors['xml'] = collections.OrderedDict()

                self.errors['xml'][file] = str(e)

    def puts_errors(self):
        if self.errors:
            for type, file_info in self.errors.items():
                if type in ('encoding'):
                    print('encoding errors: %s(文件编码必须为utf-8)' % type)
                elif type in ('xml'):
                    print('xml errors: (XML解析错误)')
                else:
                    print('encoding errors: %s' % type)

                for file, info in file_info.items():
                    print('  %s' % os.path.abspath(file))

                print()

    def sendmail(self):
        if self.errors:
            errors = collections.OrderedDict()

            for type, file_info in self.errors.items():
                for file, info in file_info.items():
                    _, email, *_ = info

                    if email:
                        if email not in errors:
                            errors[email] = {}

                        if type not in errors[email]:
                            errors[email][type] = []

                        errors[email][type].append(file)

            for email, type_info in errors.items():
                message = []

                for type in sorted(type_info.keys()):
                    if type in ('encoding'):
                        message.append('<font color="red"><strong>encoding errors: %s(文件编码必须为utf-8)</strong></font>:' % type)
                    elif type in ('xml'):
                        message.append('<font color="red"><strong>xml errors: (XML解析错误)</strong></font>:')
                    else:
                        message.append('<font color="red"><strong>encoding errors: %s(文件编码必须为utf-8)</strong></font>:' % type)

                    for file in type_info[type]:
                        message.append('  %s' % os.path.abspath(file))

                    message.append('')

                if os.environ.get('BUILD_URL'):
                    console_url = builtin_os.join(os.environ['BUILD_URL'], 'console')

                    message.append('详细信息: <a href="%s">%s</a>' % (console_url, console_url))
                    message.append('')

                smtp.sendmail(self.notification, email, None, '<br>\n'.join(message))
