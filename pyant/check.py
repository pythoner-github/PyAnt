import collections
import glob
import os.path
import platform
import re
import xml.etree.ElementTree

from pyant import git
from pyant.builtin import os as builtin_os

__all__ = ('check', 'xml_etree_with_encoding')

def xml_etree_with_encoding(file, encoding = 'gb2312'):
    tree = None

    try:
        string = None

        with open(file, encoding = encoding) as f:
            string = f.read()

        if string:
            string = string.strip()

            m = re.search(r'encoding\s*=\s*(\'|")([\w-]+)(\'|")', string.splitlines()[0])

            if encoding == m.group(2).strip().lower():
                tree = xml.etree.ElementTree.ElementTree(xml.etree.ElementTree.fromstring(string))
    except:
        pass

    return tree

class check:
    def __init__(self, xpath = None):
        self.errors = None

        if xpath:
            self.xpath = xpath
        else:
            self.xpath = ''

    def check(self, ignores = None, gb2312 = False):
        self.errors = None

        self.encoding()
        self.xml(ignores, gb2312)

        if self.errors:
            for type, file_info in self.errors.items():
                for file in file_info:
                    info = git.info(file)

                    if info:
                        file_info[file] = (
                            info['author'], info['email'], info['date'], info['url']
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

    def xml(self, ignores = None, gb2312 = False):
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
                xml.etree.ElementTree.parse(file)
            except:
                if gb2312:
                    if xml_etree_with_encoding(file, 'gb2312') is not None:
                        continue

                if not self.errors:
                    self.errors = collections.OrderedDict()

                if 'xml' not in self.errors:
                    self.errors['xml'] = collections.OrderedDict()

                self.errors['xml'][file] = None

    def puts_errors(self):
        if self.errors:
            for type, file_info in self.errors.items():
                print('encoding errors: %s' % type)

                for file, info in file_info.items():
                    print('  %s' % file)

                print()

    def sendmail(self):
        if self.errors:
            osname = platform.system().lower()

            if os.environ.get('WIN64') == '1':
                osname += '-X64'

            subject = '<CHECK 通知>文件检查失败, 请尽快处理(%s)' % osname

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
                    message.append('<font color="red"><strong>encoding errors: %s</strong></font>:' % type)

                    for file in type_info[type]:
                        message.append('  %s' % file)

                    message.append('')

                smtp.sendmail(subject, email, None, '<br>\n'.join(message))
