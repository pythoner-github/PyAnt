import collections
import datetime
import glob
import os
import os.path
import re
import shutil
import tarfile
import tempfile
import xml.etree.ElementTree
import zipfile

from pyant import command
from pyant.app import const
from pyant.builtin import os as builtin_os

__all__ = ['check', 'package', 'package_home', 'artifactory', 'metric_start', 'metric_end']

def check(xpath = None, ignores = None, gb2312 = False):
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
#          <package name = '...' dirname = '...' dest = '...'>
#            <file name='...'/>
#            <ignore name='...'/>
#          </package>
#
#          <package name = '...' dirname = '...' dest = '...'>
#            <file name='...'/>
#            <ignore name='...'/>
#          </package>
#        </packages>
#
#        <copies>
#          <copy name = '...' dirname = '...' dest = '...'>
#            <file name='...'/>
#            <ignore name='...'/>
#          </copy>
#
#          <copy name = '...' dirname = '...' dest = '...'>
#            <file name='...'/>
#            <ignore name='...'/>
#          </copy>
#        </copies>
#      </type>
#    </install>
def package(version, xpath = None, type = None, expand_filename = None):
    if not xpath:
        xpath = '*/installdisk/installdisk.xml'

    if not type:
        type = '*'

    zipfile_home = package_home(version)

    shutil.rmtree(zipfile_home, ignore_errors = True)
    os.makedirs(zipfile_home, exist_ok = True)

    packages = {}
    copies = {}

    for file in glob.iglob(xpath, recursive = True):
        try:
            tree = xml.etree.ElementTree.parse(file)
        except:
            tree = xml_etree_with_encoding(file, 'gb2312')

            if tree is None:
                print('error: parse xml file fail: %s' % os.path.abspath(file))

                return False

        for e in tree.findall('/'.join((type, 'packages/package'))):
            name = e.get('name')
            dirname = e.get('dirname')
            dest = e.get('dest')

            if dest in (None, '.'):
                dest = ''

            if name and dirname:
                ############################################
                if not os.path.isdir(os.path.join(os.path.dirname(file), dirname.strip())):
                    dirname = os.path.join('..', dirname)
                ############################################

                name = name.strip()
                dirname = os.path.normpath(os.path.join(os.path.dirname(file), dirname.strip()))
                dest = dest.strip()

                if os.path.isdir(dirname):
                    if name not in packages:
                        packages[name] = collections.OrderedDict()

                    with builtin_os.chdir(dirname) as chdir:
                        for element in e.findall('file'):
                            element_name = element.get('name')

                            if element_name:
                                element_name = element_name.strip()

                                if dirname not in packages[name]:
                                    packages[name][dirname] = collections.OrderedDict()

                                if dest not in packages[name][dirname]:
                                    packages[name][dirname][dest] = []

                                if os.path.isfile(element_name):
                                    packages[name][dirname][dest].append(element_name)
                                elif os.path.isdir(element_name):
                                    for filename in glob.iglob(os.path.join(element_name, '**/*'), recursive = True):
                                        if os.path.isfile(filename):
                                            packages[name][dirname][dest].append(filename)
                                else:
                                    for filename in glob.iglob(element_name, recursive = True):
                                        if os.path.isfile(filename):
                                            packages[name][dirname][dest].append(filename)

                        for element in e.findall('ignore'):
                            element_name = element.get('name')

                            if element_name:
                                element_name = element_name.strip()

                                if dirname in packages[name]:
                                    if dest in packages[name][dirname]:
                                        if os.path.isfile(element_name):
                                            if element_name in packages[name][dirname][dest]:
                                                packages[name][dirname][dest].remove(element_name)
                                        elif os.path.isdir(element_name):
                                            for filename in glob.iglob(os.path.join(element_name, '**/*'), recursive = True):
                                                if os.path.isfile(filename):
                                                    if filename in packages[name][dirname]:
                                                        packages[name][dirname][dest].remove(filename)
                                        else:
                                            for filename in glob.iglob(element_name, recursive = True):
                                                if os.path.isfile(filename):
                                                    if filename in packages[name][dirname]:
                                                        packages[name][dirname][dest].remove(filename)

        for e in tree.findall('/'.join((type, 'copies/copy'))):
            name = e.get('name')
            dirname = e.get('dirname')
            dest = e.get('dest')

            if dest in (None, '.'):
                dest = ''

            if name and dirname:
                name = name.strip()
                dirname = os.path.normpath(os.path.join(os.path.dirname(file), dirname.strip()))
                dest = dest.strip()

                if os.path.isdir(dirname):
                    if name not in copies:
                        copies[name] = collections.OrderedDict()

                    with builtin_os.chdir(dirname) as chdir:
                        for element in e.findall('file'):
                            element_name = element.get('name')

                            if element_name:
                                element_name = element_name.strip()

                                if dirname not in copies[name]:
                                    copies[name][dirname] = collections.OrderedDict()

                                if dest not in copies[name][dirname]:
                                    copies[name][dirname][dest] = []

                                if os.path.isfile(element_name):
                                    copies[name][dirname][dest].append(element_name)
                                elif os.path.isdir(element_name):
                                    for filename in glob.iglob(os.path.join(element_name, '**/*'), recursive = True):
                                        if os.path.isfile(filename):
                                            copies[name][dirname][dest].append(filename)
                                else:
                                    for filename in glob.iglob(element_name, recursive = True):
                                        if os.path.isfile(filename):
                                            copies[name][dirname][dest].append(filename)

                        for element in e.findall('ignore'):
                            element_name = element.get('name')

                            if element_name:
                                element_name = element_name.strip()

                                if dirname in copies[name]:
                                    if dest in copies[name][dirname]:
                                        if os.path.isfile(element_name):
                                            if element_name in copies[name][dirname][dest]:
                                                copies[name][dirname][dest].remove(element_name)
                                        elif os.path.isdir(element_name):
                                            for filename in glob.iglob(os.path.join(element_name, '**/*'), recursive = True):
                                                if os.path.isfile(filename):
                                                    if filename in copies[name][dirname]:
                                                        copies[name][dirname][dest].remove(filename)
                                        else:
                                            for filename in glob.iglob(element_name, recursive = True):
                                                if os.path.isfile(filename):
                                                    if filename in copies[name][dirname]:
                                                        copies[name][dirname][dest].remove(filename)

    for name, dirname_info in packages.items():
        try:
            zipname = os.path.join(zipfile_home, '%s_%s.zip' % (name, version))

            if not os.path.isdir(os.path.dirname(zipname)):
                os.makedirs(os.path.dirname(zipname), exist_ok = True)

            with zipfile.ZipFile(zipname, 'w') as zip:
                for line in ('$ zipfile: %s' % zip.filename, '  in (' + os.getcwd() + ')'):
                    print(line)

                for dirname, dest_info in dirname_info.items():
                    for dest, filename_list in dest_info.items():
                        for filename in filename_list:
                            if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib'):
                                continue

                            if os.path.isfile(os.path.join(dirname, filename)):
                                arcname = None

                                if expand_filename:
                                    filename, arcname = expand_filename(version, dirname, filename, type)

                                zip.write(os.path.join(dirname, filename), os.path.join(dest, arcname))
        except Exception as e:
            print(e)

            return False

    for name, dirname_info in copies.items():
        try:
            for line in ('$ copy: %s' % name, '  in (' + os.getcwd() + ')'):
                print(line)

            for dirname, dest_info in dirname_info.items():
                for dest, filename_list in dest_info.items():
                    for filename in filename_list:
                        if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib'):
                            continue

                        if os.path.isfile(os.path.join(dirname, filename)):
                            dst = filename

                            if expand_filename:
                                filename, dst = expand_filename(version, dirname, filename, type)

                            dst = os.path.join(zipfile_home, name, dest, dst)

                            if not os.path.isdir(os.path.dirname(dst)):
                                os.makedirs(os.path.dirname(dst), exist_ok = True)

                            shutil.copyfile(os.path.join(dirname, filename), dst)
        except Exception as e:
            print(e)

            return False

    return True

def package_home(version):
    return os.path.abspath(os.path.join('../zipfile', version))

def artifactory(path, generic_path, generic_base_path = None):
    if os.path.isdir(path):
        with builtin_os.tmpdir(tempfile.mkdtemp(), False) as tmpdir:
            if generic_base_path:
                # download

                artifact_path = os.path.join(const.ARTIFACT_HTTP, generic_base_path)
                cmdline = 'curl -H "%s" -O "%s"' % (const.ARTIFACT_APIKEY, artifact_path)

                cmd = command.command()

                for line in cmd.command(cmdline, display_cmd = 'artifact download: %s' % artifact_path):
                    print(line)

                if not cmd.result():
                    return False

                try:
                    with tarfile.open(os.path.basename(generic_base_path)) as tar:
                        tar.extractall('installation')
                except Exception as e:
                    print(e)

                    return False

            dst = os.path.join(os.getcwd(), 'installation')

            with builtin_os.chdir(path) as chdir:
                try:
                    for file in glob.iglob('**/*', recursive = True):
                        filename = os.path.join(dst, file)

                        if not os.path.isdir(os.path.dirname(filename)):
                            os.makedirs(os.path.dirname(filename), exist_ok = True)

                        shutil.copyfile(file, filename)
                except Exception as e:
                    print(e)

                    return False

            try:
                with tarfile.open('%s.tar.gz' % os.path.basename(path), 'w:gz') as tar:
                    tar.add('installation')
            except Exception as e:
                print(e)

                return False

            # upload

            artifact_path = os.path.join(const.ARTIFACT_HTTP, generic_path)
            cmdline = 'curl -u%s:%s -T "%s" "%s"' % (
                const.ARTIFACT_USERNAME, const.ARTIFACT_ENCRYPTED_PASSWORD,
                '%s.tar.gz' % os.path.basename(path), artifact_path
            )

            cmd = command.command()

            for line in cmd.command(cmdline, display_cmd = 'artifact upload: %s' % artifact_path):
                print(line)

            if not cmd.result():
                return False

            return True
    else:
        return False

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
