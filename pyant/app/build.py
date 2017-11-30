import collections
import datetime
import glob
import os
import os.path
import shutil
import xml.etree.ElementTree
import zipfile

from pyant import command
from pyant.app import const
from pyant.builtin import os as builtin_os

__all__ = ['check', 'package', 'metric_start', 'metric_end']

def check(xpath = None, ignores = None):
    if not xpath:
        xpath = '*'

    if ignores:
        if not isinstance(ignores, list):
            ignores = [ignores]

    map = collections.OrderedDict()

    for file in glob.iglob(os.path.join(xpath, '**/*.java'), recursive = True):
        try:
            with open(file, encoding = 'utf8') as f:
                for line in f.readlines():
                    pass
        except:
            if 'java' not in map:
                map['java'] = []

            map['java'].append(file)

    for file in glob.iglob(os.path.join(xpath, '**/*.xml'), recursive = True):
        found = False

        unix_file = file.replace('\\', '/')

        for name in ('/target/', '/output/'):
            if name in unix_file:
                found = True

                break

        if found:
            continue

        try:
            xml.etree.ElementTree.parse(file)
        except:
            if ignores:
                found = False

                for ignore in ignores:
                    if re.search(ignore, file):
                        found = True

                        break

                if found:
                    continue

            if 'xml' not in map:
                map['xml'] = []

            map['xml'].append(file)

    if map:
        for k, v in map.items():
            print('encoding errors: %s' % k)

            for file in v:
                print('  %s' % file)

            print()

        return False
    else:
        return True

# installdisk.xml
#
#    <install>
#      <type>
#        <packages>
#          <package name = '...' dirname = '...'>
#            <file name='...'/>
#            <ignore name='...'/>
#          </package>
#
#          <package name = '...' dirname = '...'>
#            <file name='...'/>
#            <ignore name='...'/>
#          </package>
#        </packages>
#
#        <copies>
#          <copy name = '...' dirname = '...'>
#            <file name='...'/>
#            <ignore name='...'/>
#          </copy>
#
#          <copy name = '...' dirname = '...'>
#            <file name='...'/>
#            <ignore name='...'/>
#          </copy>
#        </copies>
#      </type>
#    </install>
def package(xpath = None, version = None, type = None, expand_filename = None):
    if not xpath:
        xpath = '*/installdisk/installdisk.xml'

    if not type:
        type = '*'

    zipfile_home = os.path.abspath('../zipfile')

    shutil.rmtree(zipfile_home, ignore_errors = True)
    os.makedirs(zipfile_home, exist_ok = True)

    packages = {}
    copies = {}

    for file in glob.iglob(xpath, recursive = True):
        try:
            tree = xml.etree.ElementTree.parse(file)
        except:
            print('error: parse xml file fail: %s' % os.path.abspath(file))

            return False

        for e in tree.findall('/'.join((type, 'packages/package'))):
            name = e.get('name')
            dirname = e.get('dirname')

            if name and dirname:
                dirname = os.path.normpath(os.path.dirname(file), dirname)

                if os.path.isdir(dirname):
                    if name not in packages:
                        packages[name] = collections.OrderedDict()

                    with builtin_os.chdir(dirname) as home_dir:
                        for element in e.findall('file'):
                            element_name = element.get('name')

                            if element_name:
                                if home_dir not in packages[name]:
                                    packages[name][home_dir] = []

                                if os.path.isfile(element_name):
                                    packages[name][home_dir].append(element_name)
                                else:
                                    for filename in glob.iglob(os.path.join(element_name, '**/*'), recursive = True):
                                        packages[name][home_dir].append(filename)

                        for element in e.findall('ignore'):
                            element_name = element.get('name')

                            if element_name:
                                if home_dir in packages[name]:
                                    if os.path.isfile(element_name):
                                        if element_name in packages[name][home_dir]:
                                            packages[name][home_dir].remove(element_name)
                                    else:
                                        for filename in glob.iglob(os.path.join(element_name, '**/*'), recursive = True):
                                            if filename in packages[name][home_dir]:
                                                packages[name][home_dir].remove(filename)

        for e in tree.findall('/'.join((type, 'copies/copy'))):
            name = e.get('name')
            dirname = e.get('dirname')

            if name and dirname:
                dirname = os.path.normpath(os.path.dirname(file), dirname)

                if os.path.isdir(dirname):
                    if name not in copies:
                        copies[name] = collections.OrderedDict()

                    with builtin_os.chdir(dirname) as home_dir:
                        for element in e.findall('file'):
                            element_name = element.get('name')

                            if element_name:
                                if home_dir not in copies[name]:
                                    copies[name][home_dir] = []

                                if os.path.isfile(element_name):
                                    copies[name][home_dir].append(element_name)
                                else:
                                    for filename in glob.iglob(os.path.join(element_name, '**/*'), recursive = True):
                                        copies[name][home_dir].append(filename)

                        for element in e.findall('ignore'):
                            element_name = element.get('name')

                            if element_name:
                                if home_dir in copies[name]:
                                    if os.path.isfile(element_name):
                                        if element_name in copies[name][home_dir]:
                                            copies[name][home_dir].remove(element_name)
                                    else:
                                        for filename in glob.iglob(os.path.join(element_name, '**/*'), recursive = True):
                                            if filename in copies[name][home_dir]:
                                                copies[name][home_dir].remove(filename)

    for name, dirname_list in packages.items():
        try:
            with zipfile.ZipFile(os.path.join(zipfile_home, '%s_%s.zip' % (name, version)), 'w') as zip:
                print('$ zipfile: %s' % zip.filename)
                print('  (' + os.getcwd() + ')')

                for dirname, filename_list in dirname_list.items():
                    for filename in filename_list:
                        arcname = None

                        if expand_filename:
                            filename, arcname = expand_filename(dirname, filename)

                        zip.write(os.path.join(dirname, filename), arcname)
        except Exception as e:
            print(e)

            return False

    for name, filename_list in copies.items():
        try:
            print('$ copy: %s' % name)
            print('  (' + os.getcwd() + ')')

            for dirname, filename_list in dirname_list.items():
                for filename in filename_list:
                    if os.path.isfile(os.path.join(dirname, filename)):
                        dst = filename

                        if expand_filename:
                            filename, dst = expand_filename(dirname, filename)

                        dst = os.path.join(zipfile_home, name, dst)

                        if not os.path.isdir(dst):
                            os.makedirs(dst, exist_ok = True)

                        shutil.copyfile(os.path.join(dirname, filename), dst)
        except Exception as e:
            print(e)

            return False

    return True

def metric_start(name, module_name = None, night = True):
    cmdline = None

    if not module_name:
        module_name = ''

    if os.environ.get('METRIC'):
        id = metric_id(name, module_name)

        if id:
            if night:
                hour = datetime.datetime.now().hour

                if 0 <= hour <=8 or hour >= 22:
                    cmdline = 'curl --data "action=buildstart&project=%s&buildtype=night&item=%s" %s' % (id, module_name, const.HTTP_METRIC)
            else:
                cmdline = 'curl --data "action=buildstart&project=%s&buildtype=CI&item=%s" %s' % (id, module_name, const.HTTP_METRIC)

    if cmdline:
        lines = []

        cmd = command.command()

        for line in cmd.command(cmdline):
            lines.append(line)

            print(line)

        if cmd.result():
            return ''.join(lines[2:]).strip()
        else:
            return None
    else:
        return None

def metric_end(id, status):
    if id:
        if status:
            success = 'success'
        else:
            success = 'failed'

        cmdline = 'curl --data "action=buildend&buildid=%s&buildresult=%s" %s' % (id, success, const.HTTP_METRIC)

        cmd = command.command()

        for line in cmd.command(cmdline):
            print(line)

# ----------------------------------------------------------

def metric_id(name, module_name = None):
    if name == 'bn':
        if module_name in ('interface', 'platform', 'necommon', 'uca', 'sdh', 'ptn'):
            return const.METRIC_ID_BN_IPTN
        elif module_name in ('ptn2', 'ip'):
            return const.METRIC_ID_BN_IPTN_NJ
        elif module_name in ('e2e'):
            return const.METRIC_ID_BN_E2E
        elif module_name in ('xmlfile', 'nbi'):
            return const.METRIC_ID_BN_NBI
        elif module_name in ('wdm'):
            return const.METRIC_ID_BN_OTN
        else:
            return None
    elif name == 'stn':
        return const.METRIC_ID_STN
    elif name == 'umebn':
        return const.METRIC_ID_UMEBN
    elif name == 'sdno':
        return const.METRIC_ID_SDNO
    else:
        return None
