import collections
import datetime
import glob
import json
import os
import os.path
import platform
import re
import shutil
import tarfile
import tempfile
import xml.etree.ElementTree
import zipfile

from pyant import command, git, maven, password
from pyant.app import const
from pyant.builtin import os as builtin_os

__all__ = (
    'check', 'package', 'package_home', 'artifactory',
    'dashboard', 'dashboard_monitor', 'dashboard_jenkins_cli',
    'metric_start', 'metric_end'
)

def check(xpath = None, ignores = None, gb2312 = False):
    if not xpath:
        xpath = '*'

    if ignores:
        if isinstance(ignores, str):
            ignores = (ignores,)

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

        file = builtin_os.normpath(file)

        for name in ('/target/', '/output/'):
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
def package(version, xpath = None, type = None, expand_filename = None, cross_platform = True):
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
            print('error: parse xml file fail: %s' % os.path.abspath(file))

            return False

        for hash, _xpath in ((packages, 'packages/package'), (copies, 'copies/copy')):
            for e in tree.findall(builtin_os.join(type, _xpath)):
                name = e.get('name')
                dirname = e.get('dirname')
                dest = e.get('dest')

                if dest in (None, '.'):
                    dest = ''

                if name and dirname:
                    name = builtin_os.normpath(name.strip())
                    dirname = builtin_os.normpath(os.path.join(os.path.dirname(file), dirname.strip()))
                    dest = builtin_os.normpath(dest.strip())

                    if os.path.isdir(dirname):
                        if name not in hash:
                            hash[name] = collections.OrderedDict()

                        with builtin_os.chdir(dirname) as chdir:
                            for element in e.findall('file'):
                                element_name = element.get('name')

                                if element_name:
                                    element_name = element_name.strip()

                                    if dirname not in hash[name]:
                                        hash[name][dirname] = collections.OrderedDict()

                                    if dest not in hash[name][dirname]:
                                        hash[name][dirname][dest] = []

                                    found = False

                                    for path in glob.iglob(element_name, recursive = True):
                                        found = True

                                        if os.path.isfile(path):
                                            hash[name][dirname][dest].append(path)
                                        elif os.path.isdir(path):
                                            for filename in glob.iglob(os.path.join(path, '**/*'), recursive = True):
                                                if os.path.isfile(filename):
                                                    if filename not in hash[name][dirname][dest]:
                                                        hash[name][dirname][dest].append(filename)
                                        else:
                                            pass

                                    if not found:
                                        print('no such file or directory: %s' % os.path.abspath(element_name))

                            for element in e.findall('ignore'):
                                element_name = element.get('name')

                                if element_name:
                                    element_name = element_name.strip()

                                    if dirname in hash[name]:
                                        if dest in hash[name][dirname]:
                                            found = False

                                            for path in glob.iglob(element_name, recursive = True):
                                                found = True

                                                if os.path.isfile(path):
                                                    if path in hash[name][dirname][dest]:
                                                        hash[name][dirname][dest].remove(path)
                                                elif os.path.isdir(path):
                                                    for filename in glob.iglob(os.path.join(path, '**/*'), recursive = True):
                                                        if os.path.isfile(filename):
                                                            if filename in hash[name][dirname][dest]:
                                                                hash[name][dirname][dest].remove(filename)
                                                else:
                                                    pass

                                            if not found:
                                                print('no such file or directory: %s' % os.path.abspath(element_name))
                    else:
                        print('no such directory: %s' % dirname)

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
                            if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib', '.manifest'):
                                continue

                            if not cross_platform:
                                if platform.system().lower() in ('windows'):
                                    if os.path.splitext(filename)[-1] in ('.so', '.sh'):
                                        if os.path.splitext(filename)[-1] in ('.so'):
                                            if 'ruby/' not in builtin_os.normpath(filename):
                                                continue
                                        else:
                                            continue
                                else:
                                    if os.path.splitext(filename)[-1] in ('.exe', '.dll', '.bat'):
                                        continue

                            if os.path.isfile(os.path.join(dirname, filename)):
                                arcname = None

                                if expand_filename:
                                    filename, arcname = expand_filename(version, dirname, filename, type)

                                zip.write(os.path.join(dirname, filename), builtin_os.normpath(os.path.join(dest, arcname)))
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

                        if not cross_platform:
                            if platform.system().lower() in ('windows'):
                                if os.path.splitext(filename)[-1] in ('.so', '.sh'):
                                    if os.path.splitext(filename)[-1] in ('.so'):
                                        if 'ruby/' not in builtin_os.normpath(filename):
                                            continue
                                    else:
                                        continue
                            else:
                                if os.path.splitext(filename)[-1] in ('.dll', '.bat'):
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

def artifactory(path, generic_path, generic_base_list = None, suffix = None):
    if os.path.isdir(path):
        with builtin_os.tmpdir(tempfile.mkdtemp(), False) as tmpdir:
            if generic_base_list:
                # download

                if isinstance(generic_base_list, str):
                    generic_base_list = (generic_base_list,)

                for generic_base_file in generic_base_list:
                    artifact_path = builtin_os.join(const.ARTIFACT_HTTP, generic_base_file)

                    cmdline = 'curl -k -H "X-JFrog-Art-Api: %s" -O "%s"' % (const.ARTIFACT_APIKEY, artifact_path)
                    display_cmd = 'curl -k -H "X-JFrog-Art-Api: %s" -O "%s"' % (password.password(const.ARTIFACT_APIKEY), artifact_path)

                    cmd = command.command()

                    for line in cmd.command(cmdline, display_cmd = display_cmd):
                        print(line)

                    if not cmd.result():
                        return False

                    try:
                        with tarfile.open(os.path.basename(generic_base_file)) as tar:
                            tar.extractall('installation')
                    except Exception as e:
                        print(e)

                        return False

            dst = os.path.join(os.getcwd(), 'installation')

            with builtin_os.chdir(path) as chdir:
                try:
                    for file in glob.iglob('**/*', recursive = True):
                        filename = os.path.join(dst, file)

                        if os.path.isfile(file):
                            if not os.path.isdir(os.path.dirname(filename)):
                                os.makedirs(os.path.dirname(filename), exist_ok = True)

                            shutil.copyfile(file, filename)
                except Exception as e:
                    print(e)

                    return False

            if suffix:
                tarname = '%s%s.tar.gz' % (os.path.basename(path), suffix)
            else:
                tarname = '%s.tar.gz' % os.path.basename(path)

            try:
                with tarfile.open(tarname, 'w:gz') as tar:
                    tar.add('installation')
            except Exception as e:
                print(e)

                return False

            # upload

            artifact_file = builtin_os.join(const.ARTIFACT_HTTP, generic_path, tarname)

            cmdline = 'curl -k -H "X-JFrog-Art-Api: %s" -T "%s" "%s"' % (const.ARTIFACT_APIKEY, tarname, artifact_file)
            display_cmd = 'curl -k -H "X-JFrog-Art-Api: %s" -T "%s" "%s"' % (password.password(const.ARTIFACT_APIKEY), tarname, artifact_file)

            cmd = command.command()

            for line in cmd.command(cmdline, display_cmd = display_cmd):
                print(line)

            if not cmd.result():
                return False

            return True
    else:
        return False

def dashboard(paths, ignores = None, gb2312 = False):
    if isinstance(paths, str):
        paths = tuple(path.strip() for path in paths.split(','))
    else:
        paths = tuple(paths)

    file = os.path.join('../json', '%s.dashboard' % os.path.basename(os.getcwd()))

    if os.path.isfile(file):
        try:
            with open(file, encoding = 'utf8') as f:
                _paths = []

                for path in json.load(f):
                    if path not in paths:
                        _paths.append(path)

                paths = tuple(_paths) + paths
        except Exception as e:
            print(e)

    errors = []

    # compile

    head('compile')

    for path in paths:
        if os.path.isdir(path):
            with builtin_os.chdir(path) as chdir:
                mvn = maven.maven()
                mvn.clean()

                if 'code_c/' in builtin_os.normpath(path):
                    cmdline = 'mvn deploy -fn -U -Djobs=5'
                    lang = 'cpp'
                else:
                    cmdline = 'mvn deploy -fn -U'
                    lang = None

                if not mvn.compile(cmdline, None, lang):
                    errors.append(path)

    # check

    head('check')

    for path in paths:
        if os.path.isdir(path):
            if not check(path, ignores, gb2312):
                if path not in errors:
                    errors.append(path)

    if errors:
        os.makedirs(os.path.dirname(file), exist_ok = True)

        try:
            with open(file, 'w', encoding = 'utf8') as f:
                json.dump(errors, f)
        except Exception as e:
            print(e)

        return False
    else:
        return True

# path:
#   (authors, paths)
def dashboard_monitor(paths, expand_dashboard = None):
    rev = {}

    if os.path.isfile('change.rev'):
        try:
            with open('change.rev', encoding = 'utf8') as f:
                rev = json.load(f)
        except Exception as e:
            print(e)

    changes = collections.OrderedDict()
    changes_rev = collections.OrderedDict()

    for path in paths:
        if os.path.isdir(os.path.join(path, '.git')):
            with builtin_os.chdir(path) as chdir:
                if path in rev.keys():
                    arg = '--stat=256 %s..HEAD' % rev[path][:6]

                    logs = git.log(None, arg)

                    if logs:
                        authors = []
                        _paths = []

                        for log in logs:
                            if log['changes']:
                                if log['author'] not in authors:
                                    authors.append(log['author'])

                                for k, v in log['changes'].items():
                                    for file in v:
                                        if expand_dashboard:
                                            filenames = expand_dashboard(path, file)

                                            if isinstance(filenames, str):
                                                filenames = (filenames,)
                                        else:
                                            filenames = (file,)

                                        for filename in filenames:
                                            dir = pom_path(filename)

                                            if dir:
                                                if dir not in _paths:
                                                    _paths.append(dir)

                        if _paths:
                            changes[path] = (authors, _paths)

                        changes_rev[path] = logs[-1]['revision']
                    else:
                        changes_rev[path] = rev[path]
                else:
                    info = git.info()

                    if info:
                        changes_rev[path] = info['revision']

    try:
        with open('change.rev', 'w', encoding = 'utf8') as f:
            json.dump(changes_rev, f)
    except Exception as e:
        print(e)

    print()
    print('*' * 40)

    for path, (authors, paths) in changes.items():
        print(path, (authors, paths))

    print('*' * 40)
    print()

    return changes

def dashboard_jenkins_cli(jobname, authors, paths):
    cmdline = 'java -jar "%s" -s %s build --username %s --password %s "%s" -p authors="%s" -p paths="%s"' % (
        const.JENKINS_CLI, const.JENKINS_HTTP, const.JENKINS_USERNAME, const.JENKINS_PASSWORD,
        jobname, ','.join(authors), ','.join(paths))

    display_cmd = 'java -jar "%s" -s %s build --username %s --password %s "%s" -p authors="%s" -p paths="%s"' % (
        const.JENKINS_CLI, const.JENKINS_HTTP, password.password(const.JENKINS_USERNAME), password.password(const.JENKINS_PASSWORD),
        jobname, ','.join(authors), ','.join(paths))

    for line in ('$ ' + display_cmd, '  in (' + os.getcwd() + ')'):
        print(line)

    # cmd = command.command()

    # for line in cmd.command(cmdline, display_cmd = display_cmd):
    #    print(line)

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

def pom_path(path):
    if not path:
        return None

    if os.path.isdir(path):
        if os.path.isfile(os.path.join(path, 'pom.xml')):
            return path

    return pom_path(os.path.dirname(path))

def head(string):
    print('*' * 40)

    if len(string) > 38:
        print('*' + string)
    else:
        size = (38 - len(string)) // 2

        print('*' + ' ' * size + string + ' ' * (38 - len(string) - size) + '*')

    print('*' * 40)
    print()
