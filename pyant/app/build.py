import collections
import datetime
import glob
import xml.etree.ElementTree

from pyant import command
from pyant.app import const
from pyant.builtin import os as builtin_os

__all__ = ['check', 'metric_start', 'metric_end']

def check(home, xpath = None, ignores = None):
    if not xpath:
        xpath = '*'

    if ignores:
        if not isinstance(ignores, list):
            ignores = [ignores]

    if os.path.isdir(home):
        map = collections.OrderedDict()

        with builtin_os.chdir(home) as dir:
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
    else:
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
