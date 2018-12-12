import collections
import datetime
import glob
import os
import os.path
import re
import shutil
import tempfile
import time
import zipfile

from lxml import etree

from pyant import git
from pyant.app import const, __build__
from pyant.builtin import __os__, __string__

__all__ = ('build',)

class build(__build__):
    def __init__(self):
        artifact_repos = {
            'snapshot'  : 'U31R22-snapshot-generic',
            'alpha'     : 'U31R22-alpha-generic',
            'release'   : 'U31R22-release-generic'
        }

        super().__init__(
            'bn',
            const.BN_REPOS,
            artifact_repos
        )

        self.type = 'ems'
        self.repos_devtools = const.SSH_GIT

    def update(self, module, branch = None):
        if module:
            if module in self.repos:
                path = os.path.basename(self.repos[module])

                if os.path.isdir(path):
                    if os.path.isfile(os.path.join(path, '.git/index.lock')):
                        time.sleep(30)

                        return True
                    else:
                        return git.pull(path, revert = True)
                else:
                    return git.clone(self.repos[module], path, branch)
            elif module in ('devtools', ):
                return self.update_devtools(branch)
            else:
                print('module name not found in %s' % str(tuple(self.repos.keys())))

                return False
        else:
            status = True

            for module in self.repos:
                if not self.update(module, branch):
                    status = False

            if not self.update_devtools(branch):
                status = False

            return status

    def compile_pom(self, cmd = None, file = None):
        return super().compile_pom(cmd, 'U31R22_PLATFORM/pom/pom.xml')

    def compile(self, module, cmd = None, clean = False, retry_cmd = None, dirname = None, lang = None):
        if module:
            if module in list(self.repos.keys()) + ['wdm1', 'wdm2', 'wdm3']:
                self.environ(lang)

                if lang in ('cpp', ):
                    if not dirname:
                        dirname = 'code_c/build'
                else:
                    if not dirname:
                        dirname = 'code/build'

                if module in ('wdm1', 'wdm2', 'wdm3'):
                    self.path = os.path.basename(self.repos['wdm'])
                else:
                    self.path = os.path.basename(self.repos[module])

                return super().compile(cmd, clean, retry_cmd, dirname, lang)
            else:
                print('module name not found in %s' % str(tuple(self.repos.keys())))

                return False
        else:
            status = True

            for module in self.repos:
                if not self.compile(module, cmd, clean, retry_cmd, dirname, lang):
                    status = False

            return status

    def package(self, version, type = None):
        if not type:
            type = self.type

        type = type.strip().lower()

        if not super().package(version, type):
            return False

        if self.__package__(version, None, type, self.expand_filename):
            if os.environ.get('ARTIFACT'):
                artifact = __string__.vars_expand(
                    os.environ['ARTIFACT'],
                    {'datetime': datetime.datetime.now().strftime('%Y%m%d')}
                )
            else:
                if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
                    artifact = self.artifact_repos['snapshot']
                else:
                    artifact = self.artifact_repos['alpha']

            suffix = '-%s' % __os__.osname()

            if type not in ('ems',):
                suffix += '_%s' % type

            if type in ('lct',):
                filenames = (
                    os.path.join(self.artifact_repos['release'], 'bn/LCT/%s_en.tar.gz' % os.environ['UEP_INSTALL']),
                    os.path.join(self.artifact_repos['release'], 'bn/LCT/%s_zh.tar.gz' % os.environ['UEP_INSTALL'])
                )
            else:
                filenames = ((
                    os.path.join(self.artifact_repos['release'], 'bn/%s/%s.tar.gz' % (type.upper(),  os.environ['UEP_INSTALL'])),
                    os.path.join(self.artifact_repos['release'], 'bn/%s/%s_extend.tar.gz' % (type.upper(),  os.environ['UEP_INSTALL']))
                ),)

            if type in ('su31', 'su31nm', 'su31-e2e', 'su31-nme2e'):
                targz = True
                tarpath = 'umebn_%s/installation' % type
            else:
                targz = False
                tarpath = None

            for filename in filenames:
                if not self.__artifactory__(
                    self.package_home(version, type),
                    os.path.join(artifact, version.replace(' ', '')),
                    filename,
                    suffix,
                    targz,
                    tarpath
                ):
                    return False

            return True

        return False

    def update_package(self, version, type = None):
        if not type:
            type = self.type

        type = type.strip().lower()

        if self.__package__(version, '*/installdisk/updatedisk.xml', type, self.expand_filename):
            if version.endswith(datetime.datetime.now().strftime('%Y%m%d')):
                artifact = self.artifact_repos['snapshot']
            else:
                artifact = self.artifact_repos['alpha']

            suffix = '-update-%s' % __os__.osname()

            if type not in ('ems',):
                suffix += '_%s' % type

            filename = (
                os.path.join(self.artifact_repos['release'], 'bn/UPDATE/%s/%s.tar.gz' % (type.upper(),  os.environ['UEP_INSTALL'])),
                os.path.join(self.artifact_repos['release'], 'bn/UPDATE/%s/%s_extend.tar.gz' % (type.upper(),  os.environ['UEP_INSTALL']))
            )

            if not self.__artifactory__(
                self.package_home(version, type),
                os.path.join(artifact, version.replace(' ', '')),
                filename,
                suffix,
                False
            ):
                return False

            return True

        return False

    def environ(self, lang = None):
        if os.environ.get('UEP_VERSION'):
            if not os.environ.get('POM_UEP_VERSION'):
                os.environ['POM_UEP_VERSION'] = os.environ['UEP_VERSION'].upper()

                print('export POM_UEP_VERSION=%s' % os.environ['POM_UEP_VERSION'])

        if not os.environ.get('DEVTOOLS_ROOT'):
            if os.path.isdir('DEVTOOLS'):
                os.environ['DEVTOOLS_ROOT'] = __os__.abspath('DEVTOOLS')

        if lang == 'cpp':
            if os.environ.get('DEVTOOLS_ROOT'):
                if os.path.isdir(os.path.join(os.environ['DEVTOOLS_ROOT'], 'vc/bin')):
                    os.environ['PATH'] = ';'.join((__os__.join(os.environ['DEVTOOLS_ROOT'], 'vc/bin'), os.environ['PATH']))

            if not os.environ.get('INTERFACE_OUTPUT_HOME'):
                path = os.path.basename(self.repos['interface'])

                if os.path.isdir(path):
                    os.environ['INTERFACE_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('PLATFORM_OUTPUT_HOME'):
                path = os.path.basename(self.repos['platform'])

                if os.path.isdir(path):
                    os.environ['PLATFORM_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('NECOMMON_OUTPUT_HOME'):
                path = os.path.basename(self.repos['necommon'])

                if os.path.isdir(path):
                    os.environ['NECOMMON_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('E2E_OUTPUT_HOME'):
                path = os.path.basename(self.repos['e2e'])

                if os.path.isdir(path):
                    os.environ['E2E_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('UCA_OUTPUT_HOME'):
                path = os.path.basename(self.repos['uca'])

                if os.path.isdir(path):
                    os.environ['UCA_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('NAF_OUTPUT_HOME'):
                path = os.path.basename(self.repos['nbi'])

                if os.path.isdir(path):
                    os.environ['NAF_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('SDH_OUTPUT_HOME'):
                path = os.path.basename(self.repos['sdh'])

                if os.path.isdir(path):
                    os.environ['SDH_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

            if not os.environ.get('WDM_OUTPUT_HOME'):
                path = os.path.basename(self.repos['wdm'])

                if os.path.isdir(path):
                    os.environ['WDM_OUTPUT_HOME'] = __os__.join(os.path.abspath(path), 'code_c/build/output')

    # ------------------------------------------------------

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
    def __package__(self, version, xpath = None, type = None, expand_filename = None):
        if not xpath:
            xpath = '*/installdisk/installdisk.xml'

        if not type:
            type = self.type

        zipfile_home = self.package_home(version, type)
        tmpdir = tempfile.mkdtemp()

        try:
            shutil.rmtree(zipfile_home)
        except:
            pass

        if type in ('su31', 'su31nm', 'su31-e2e', 'su31-nme2e'):
            zipfile_home = os.path.join(zipfile_home, 'installation')

        os.makedirs(zipfile_home, exist_ok = True)

        packages = {}
        copies = {}
        vars = {}

        for file in glob.iglob(xpath, recursive = True):
            try:
                tree = etree.parse(file, etree.XMLParser(strip_cdata=False))
            except:
                print('error: parse xml file fail: %s' % os.path.abspath(file))

                return False

            vars[file] = {
                'os': __os__.osname()
            }

            for e in tree.findall('%s/opts/attr' % type):
                name = e.get('name', '').strip()
                value = ''

                for element in e.findall('value'):
                    value = element.text.strip()

                    if '<![CDATA[' in etree.tostring(element, encoding='utf-8').decode('utf-8'):
                        pass

                    break

                filenames = []

                for element in e.findall('files/file'):
                    filename = element.get('name', '').strip()

                    if filename == '.':
                        filenames.append(file)
                    else:
                        for _filename in glob.iglob(os.path.join(os.path.dirname(file), filename), recursive = True):
                            filenames.append(os.path.normpath(_filename))

                if not filenames:
                    filenames.append(file)

                for filename in filenames:
                    if not vars.get(filename):
                        vars[filename] = {}

                    vars[filename][name] = value

            for hash, _xpath in ((packages, 'packages/package'), (copies, 'copies/copy')):
                for e in tree.findall(__os__.join(type, _xpath)):
                    name = e.get('name')
                    dirname = e.get('dirname')
                    dest = e.get('dest', '')
                    ver = e.get('version', version)

                    if dest in ('', '.'):
                        dest = ''

                    if name and dirname:
                        _vars = vars.get(file)

                        name = __os__.normpath(__string__.vars_expand(name.strip(), _vars))
                        dirname = __os__.normpath(os.path.join(os.path.dirname(file), __string__.vars_expand(dirname.strip(), _vars)))
                        dest = __os__.normpath(__string__.vars_expand(dest.strip(), _vars))
                        ver = __os__.normpath(__string__.vars_expand(ver.strip(), _vars))

                        if _xpath == 'packages/package':
                            name = '%s_%s' % (name, ver.replace(' ', ''))

                        if os.path.isdir(dirname):
                            if name not in hash:
                                hash[name] = collections.OrderedDict()

                            with __os__.chdir(dirname) as chdir:
                                for element in e.findall('file'):
                                    element_name = element.get('name')
                                    element_dest = element.get('dest', '')

                                    if element_name:
                                        element_name = os.path.normpath(__string__.vars_expand(element_name.strip(), _vars))
                                        element_dest = os.path.normpath(__string__.vars_expand(element_dest.strip(), _vars))

                                        if element_dest in ('', '.'):
                                            element_dest = element_name

                                        if dirname not in hash[name]:
                                            hash[name][dirname] = collections.OrderedDict()

                                        if dest not in hash[name][dirname]:
                                            hash[name][dirname][dest] = {}

                                        found = False

                                        if os.path.isfile(element_name):
                                            found = True

                                            hash[name][dirname][dest][element_dest] = element_name
                                        elif os.path.isdir(element_name):
                                            found = True

                                            with __os__.chdir(element_name) as _chdir:
                                                for filename in glob.iglob('**/*', recursive = True):
                                                    if os.path.isfile(filename):
                                                        hash[name][dirname][dest][os.path.join(element_dest, filename)] = os.path.join(element_name, filename)
                                        else:
                                            for path in glob.iglob(element_name, recursive = True):
                                                found = True

                                                if os.path.isfile(path):
                                                    hash[name][dirname][dest][path] = path
                                                elif os.path.isdir(path):
                                                    with __os__.chdir(path) as _chdir:
                                                        for filename in glob.iglob('**/*', recursive = True):
                                                            if os.path.isfile(filename):
                                                                hash[name][dirname][dest][os.path.join(path, filename)] = os.path.join(path, filename)
                                                else:
                                                    pass

                                        if not found:
                                            print('no such file or directory: %s' % os.path.abspath(element_name))

                                for element in e.findall('ignore'):
                                    element_name = element.get('name')

                                    if element_name:
                                        element_name = os.path.normpath(element_name.strip())

                                        if dirname in hash[name]:
                                            if dest in hash[name][dirname]:
                                                found = False

                                                for path in glob.iglob(element_name, recursive = True):
                                                    found = True

                                                    if os.path.isfile(path):
                                                        if path in hash[name][dirname][dest]:
                                                            del hash[name][dirname][dest][path]
                                                    elif os.path.isdir(path):
                                                        for filename in glob.iglob(os.path.join(path, '**/*'), recursive = True):
                                                            if os.path.isfile(filename):
                                                                if filename in hash[name][dirname][dest]:
                                                                    del hash[name][dirname][dest][filename]
                                                    else:
                                                        pass

                                                if not found:
                                                    print('no such file or directory: %s' % os.path.abspath(element_name))
                        else:
                            print('no such directory: %s' % dirname)

        for name, dirname_info in packages.items():
            zipinfo = collections.OrderedDict()

            for dirname, dest_info in dirname_info.items():
                for dest, filename_info in dest_info.items():
                    for destname, filename in filename_info.items():
                        if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib', '.manifest'):
                            continue

                        if __os__.osname() in ('windows', 'windows-x64'):
                            if os.path.splitext(filename)[-1] in ('.so', '.sh'):
                                if os.path.splitext(filename)[-1] in ('.so', ):
                                    if 'ruby/' not in __os__.normpath(filename):
                                        continue
                                else:
                                    continue
                        else:
                            if os.path.splitext(filename)[-1] in ('.exe', '.dll', '.bat'):
                                continue

                        if os.path.isfile(os.path.join(dirname, filename)):
                            arcname = destname
                            srcname = os.path.join(dirname, filename)

                            if expand_filename:
                                srcname, arcname = expand_filename(version, srcname, destname, type, tmpdir, vars.get(os.path.normpath(os.path.join(dirname, filename))))

                            if type in ('upgrade', ):
                                srcname = self.upgrade_expand_filename(srcname, tmpdir)

                            zipinfo[__os__.normpath(os.path.join(dest, arcname))] = srcname

            try:
                zipname = os.path.join(zipfile_home, '%s.zip' % name)

                if not os.path.isdir(os.path.dirname(zipname)):
                    os.makedirs(os.path.dirname(zipname), exist_ok = True)

                with zipfile.ZipFile(zipname, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
                    for line in ('$ zipfile: %s' % zip.filename, '  in (' + os.getcwd() + ')'):
                        print(line)

                    for arcname, filename in zipinfo.items():
                        zip.write(filename, arcname)
            except Exception as e:
                print(e)

                try:
                    shutil.rmtree(tmpdir)
                except:
                    pass

                return False

        for name, dirname_info in copies.items():
            try:
                for line in ('$ copy: %s' % name, '  in (' + os.getcwd() + ')'):
                    print(line)

                for dirname, dest_info in dirname_info.items():
                    for dest, filename_info in dest_info.items():
                        for destname, filename in filename_info.items():
                            if os.path.splitext(filename)[-1] in ('.debuginfo', '.pdb', '.exp', '.lib'):
                                continue

                            if __os__.osname() in ('windows', 'windows-x64'):
                                if os.path.splitext(filename)[-1] in ('.so', '.sh'):
                                    if os.path.splitext(filename)[-1] in ('.so',):
                                        if 'ruby/' not in __os__.normpath(filename):
                                            continue
                                    else:
                                        continue
                            else:
                                if os.path.splitext(filename)[-1] in ('.dll', '.bat'):
                                    continue

                            if os.path.isfile(os.path.join(dirname, filename)):
                                dst = destname
                                src = os.path.join(dirname, filename)

                                if expand_filename:
                                    src, dst = expand_filename(version, src, destname, type, tmpdir, vars.get(os.path.normpath(os.path.join(dirname, filename))))

                                dst = os.path.join(zipfile_home, name, dest, dst)

                                if not os.path.isdir(os.path.dirname(dst)):
                                    os.makedirs(os.path.dirname(dst), exist_ok = True)

                                shutil.copyfile(src, dst)
            except Exception as e:
                print(e)

                try:
                    shutil.rmtree(tmpdir)
                except:
                    pass

                return False

        try:
            shutil.rmtree(tmpdir)
        except:
            pass

        install_sh = os.path.join(zipfile_home, '../install.sh')

        if os.path.isfile(install_sh):
            lines = []

            with open(install_sh, 'r', encoding = 'utf-8') as f:
                for line in f:
                    line = line.rstrip()

                    if '${u31_version}' in line:
                        line = line.replace('${u31_version}', version)

                    lines.append(line)

            with open(install_sh, 'w', encoding = 'utf-8') as f:
                f.write('\n'.join(lines))

        return True

    def update_devtools(self, branch = None):
        if __os__.osname() == 'linux':
            url = __os__.join(self.repos_devtools, 'U31R22_DEVTOOLS_LINUX')
        elif __os__.osname() == 'solaris':
            url = __os__.join(self.repos_devtools, 'U31R22_DEVTOOLS_SOLARIS')
        elif __os__.osname() == 'windows-x64':
            url = __os__.join(self.repos_devtools, 'U31R22_DEVTOOLS_WINDOWS-x64')
        else:
            url = __os__.join(self.repos_devtools, 'U31R22_DEVTOOLS_WINDOWS')

        path = 'DEVTOOLS'

        if os.path.isdir(path):
            if os.path.isfile(os.path.join(path, '.git/index.lock')):
                time.sleep(30)

                return True
            else:
                return git.pull(path, revert = True)
        else:
            return git.clone(url, path, branch)

    def expand_filename(self, version, name, destname, type, tmpdir, vars = None):
        dst = destname

        if vars:
            lines = None
            encoding = None

            with open(name, 'rb') as f:
                str = f.read()

                for enc in ('utf-8', 'cp936'):
                    try:
                        str = str.decode(enc)

                        lines = []
                        encoding = enc

                        for line in str.splitlines():
                            lines.append(__string__.vars_expand(line.rstrip(), vars))

                        break
                    except:
                        pass

            if lines:
                name = os.path.join(tmpdir, __os__.tmpfilename(), os.path.basename(name))
                os.makedirs(os.path.dirname(name), exist_ok = True)

                with open(name, 'w', encoding = encoding) as f:
                    f.write('\n'.join(lines))

        dst = dst.replace('ums-nms', 'ums-client').replace('ums-lct', 'ums-client')

        if os.path.basename(name) in ('ppuinfo.xml', 'pmuinfo.xml', 'u3backup.xml', 'u3backupme.xml', 'dbtool-config.xml', 'package-update-info.xml'):
            try:
                tree = etree.parse(name)

                if os.path.basename(name) in ('ppuinfo.xml', 'pmuinfo.xml'):
                    if version:
                        for e in tree.findall('info'):
                            e.set('version', version)
                            e.set('display-version', version)
                elif os.path.basename(name) in ('u3backup.xml', 'u3backupme.xml'):
                    if version:
                        for e in tree.findall('version'):
                            e.text = version
                elif os.path.basename(name) in ('dbtool-config.xml',):
                    for e in tree.findall('ems_type'):
                        e.text = type
                elif os.path.basename(name) in ('package-update-info.xml',):
                    tree.getroot().set('package-name', tree.getroot().get('package-name').replace(' -B', '-B').replace(' ', '_'))
                else:
                    pass

                tree.write(name, encoding='utf-8', pretty_print=True, xml_declaration=True)
            except:
                pass

        return (name, dst)

    def upgrade_expand_filename(self, name, tmpdir):
        if re.search(r'ums-server\/procs\/ppus\/bn\.ppu\/bn-ptn\.pmu\/.*\/ican-adaptercmdcode-config.*\.xml$', name):
            try:
                tree = etree.parse(name)

                for e in tree.findall('commandCode'):
                    cmdcode = e.get('cmdCode')

                    if cmdcode == '88224':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ican.emf.subnet.process.TDoNothingProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    elif cmdcode == '80724':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('needMutex')
                        element.text = 'false'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ican.emf.subnet.process.TCreateMEProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    elif cmdcode == '84205':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')
                        e.append(element)
                    elif cmdcode == '81300':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('cmdType')
                        element.set('overTime', '30')
                        element.text = 'S'
                        e.append(element)

                        element = etree.Element('needMutex')
                        element.text = 'false'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')
                        e.append(element)
                    elif cmdcode == '80702':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('needMutex')
                        element.text = 'false'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ums.bn.mecopy.emf.process.BeginCopyMEDataProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ums.bn.mecopy.emf.process.EndCopyMEDataProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    elif cmdcode == '80703':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('needMutex')
                        element.text = 'true'
                        e.append(element)

                        element = etree.Element('supportOffline')
                        element.text = 'true'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ums.bn.ne.emf.uploadDownload.ptn9000.process.TMESetPreCheckProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ican.emf.subnet.process.TModifyMEProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'com.zte.ican.emf.subnet.process.TPublishModifyMEProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    else:
                        pass

                name = os.path.join(tmpdir, __os__.tmpfilename())
                tree.write(name, encoding='utf-8', pretty_print=True, xml_declaration=True)
            except:
                pass
        elif re.search(r'ums-server\/procs\/ppus\/bn\.ppu\/(bn-mstp|bn-wdm)\.pmu\/.*\/ican-adaptercmdcode-config.*\.xml$', name):
            try:
                tree = etree.parse(name)

                for e in tree.findall('commandCode'):
                    cmdcode = e.get('cmdCode')

                    if cmdcode == '80724':
                        for element in e.getchildren():
                            e.remove(element)

                        element = etree.Element('needMutex')
                        element.text = 'true'
                        e.append(element)

                        element = etree.Element('prcessMgr')
                        element.set('mgrName', 'ProcessMgr')

                        process_node_element = etree.Element('processNode')
                        process_name_element = etree.Element('processName')
                        process_name_element.text = 'CCreateMEProcess'
                        process_node_element.append(process_name_element)
                        element.append(process_node_element)

                        e.append(element)
                    else:
                        pass

                name = os.path.join(tmpdir, __os__.tmpfilename())
                tree.write(name, encoding='utf-8', pretty_print=True, xml_declaration=True)
            except:
                pass
        else:
            pass

        return name

    def metric_id(self, module_name = None):
        if module_name in ('interface', 'platform', 'necommon', 'uca', 'sdh', 'ptn'):
            return const.METRIC_ID_BN_ITN
        elif module_name in ('ptn2',):
            return const.METRIC_ID_BN_IPN
        elif module_name in ('e2e',):
            return const.METRIC_ID_BN_E2E
        elif module_name in ('xmlfile', 'nbi', 'inventory'):
            return const.METRIC_ID_BN_NBI
        elif module_name in ('wdm',):
            return const.METRIC_ID_BN_OTN
        else:
            return None
